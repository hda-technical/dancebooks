#!/usr/bin/env python3
import concurrent.futures
import datetime
import json
import multiprocessing
import logging
import os
import re
import subprocess

import opster
from stdnum import isbn
from stdnum import issn

from config import config
import const
import bib_parser
import utils

items, item_index = bib_parser.BibParser().parse_folder(config.parser.bibdata_dir)

#filename for storing previous validation state
DATA_JSON_FILENAME = "_validate.json"
DATA_FIELDS = {
	"added_on",
	"altauthor",
	"annotation",
	"author",
	"booktitle",
	"booktype",
	"catalogue",
	"cite_label",
	"commentator",
	"compiler",
	"crossref",
	"day",
	"edition",
	"editor",
	"filename",
	"id",
	"incipit",
	"institution",
	"isbn",
	"issn",
	"journaltitle",
	"keywords",
	"langid",
	"library",
	"library_code",
	"library_location",
	"location",
	"magic_const",
	"month",
	"number",
	"origauthor",
	"origlanguage",
	"pages",
	"part",
	"plate_number",
	"pseudo_author",
	"publisher",
	"series",
	"shorthand",
	"source",
	"title",
	"type",
	"transcription",
	"translator",
	"type",
	"url",
	"volume",
	"volumes",
	"year",
}

ANCILLARY_FIELDS = {
	"all_fields",
	"availability",
	"filesize",
	"source_file",
	"source_line",
	"useful_keywords",
	"year_circa",
	"year_from",
	"year_to",
}

ALLOWED_FIELDS = (ANCILLARY_FIELDS | DATA_FIELDS)

MULTIENTRY_BOOKTYPES = {
	"article",
	"proceedings",
	"inproceedings",
	"collection",
	"incollection"
}

PARTIAL_BOOKTYPES = {
	"article",
	"inproceedings",
	"incollection",
	"inbook"
}

def fetch_added_on_from_git():
	BLAME_REGEXP = re.compile(
		#commit hash
		r"^[\^0-9a-z]+\s+"
		#filename
		r"[^\s]*?\s+"
		#committer's name
		r"\([A-Za-z\-\s\\]*?\s+"
		#commit date
		r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
		#commit time
		r"[\d:]+\s+"
		#commit time zone
		r"[+\d]+\s+"
		#line numberq
		r"\d+\)\s+"
		#item id
		r"(?P<id>[a-z_\d]+),\s*$"
	)
	def blame_file(path):
		data = subprocess.check_output([
			"git",
			"blame",
			#WARN: using show-name to guarantee output format
			"--show-name",
			#no such option in "git blame" on trusty
			#"--no-progress",
			path
		]).decode()
		result = dict()
		for line in data.split("\n"):
			match = BLAME_REGEXP.search(line)
			if not match:
				continue
			item_id = match.group("id")
			date = datetime.datetime.strptime(
				match.group("date"),
				config.parser.date_format
			)
			result[item_id] = date
		return result

	result = dict()
	for entry in os.listdir(config.parser.bibdata_dir):
		entry_path = os.path.join(config.parser.bibdata_dir, entry)
		result.update(blame_file(entry_path))
	return result


def fetch_filelist_from_fs():
	EXCLUDED_FOLDERS = {
		"Ancillary sources (not in bibliography)",
		"Leaflets (not in bibliography)"
	}
	trim_root = lambda path: path[len(config.www.elibrary_dir):]
	return set(map(
		trim_root,
		utils.files_in_folder(config.www.elibrary_dir, "*.pdf", excludes=EXCLUDED_FOLDERS)
	))


#executed once per validation run
def update_validation_data(
	errors,
	ignore_missing_ids,
	ignore_added_errors
):
	"""
	Checks if no book_ids were lost since
	the last validation run on this machine.
	Overwrites known ids if no losses were detected
	"""
	validation_data = {
		"ids": set(),
		"errors": dict()
	}
	previous_data_exists = os.path.exists(DATA_JSON_FILENAME)
	if previous_data_exists:
		with open(DATA_JSON_FILENAME, "r") as validation_data_file:
			try:
				validation_data = json.loads(validation_data_file.read())
			except ValueError:
				#when no JSON object could be decoded,
				#validation data shouldn't be updated
				pass

	current_ids = set(item_index["id"].keys())
	old_ids = set(validation_data["ids"])
	changed_ids = old_ids - current_ids
	known_redirections = set(config.www.id_redirections.keys())
	#ids that were lost due to renaming
	lost_ids = changed_ids - known_redirections
	#ids that exist in files, and are also present in id_redirections
	found_ids = current_ids & known_redirections

	old_errors = set(validation_data["errors"])
	new_errors = set(errors.keys())
	added_errors = new_errors - old_errors
	if len(added_errors) > 0:
		logging.error("Following new erroneous entries were introduced")
		for erroneous_id in added_errors:
			logging.error("    " + str(erroneous_id))
			for error_text in errors[erroneous_id]:
				logging.error("        " + error_text)

	if len(found_ids) > 0:
		logging.error("Following book ids are present in files and in id_redirections:")
		for found_id in found_ids:
			logging.error("    " + found_id)

	if len(lost_ids) > 0:
		#some ids were lost
		#printing them without updating validation_data_file
		logging.warning("Following book ids were lost")
		for lost_id in lost_ids:
			logging.warning("    " + lost_id)

	if (not previous_data_exists) or (lost_ids and ignore_missing_ids):
		validation_data["ids"] = list(current_ids)
	if (not previous_data_exists) or (new_errors and ignore_added_errors):
		validation_data["errors"] = list(new_errors)
	with open(DATA_JSON_FILENAME, "w") as validation_data_file:
		validation_data_file.write(json.dumps(validation_data))


def validate_periodical_filename(filename, item, errors):
	if filename.endswith(".md"):
		return
	booktype = item.get("booktype")

	is_periodical_booktype = booktype in ("article", "periodical")
	is_periodical_filename = filename.startswith("/Periodical/")
	if not is_periodical_filename:
		return

	if not all([
		is_periodical_booktype,
		is_periodical_filename
	]):
		errors.add("Only articles should be stored in '/Periodical' subfolder")


def validate_short_desription_filename(filename, item, errors):
	if filename.endswith(".md"):
		return
	keywords = item.get("keywords") or []
	if filename.startswith("/Short descriptions/"):
		if "dance description: short" not in keywords:
			errors.add("Only 'dance description: short' tagged items should be stored in '/Short descriptions' subfolder")


def validate_etiquette_filename(filename, item, errors):
	if filename.endswith(".md"):
		return
	keywords = item.get("keywords") or []
	if filename.startswith("/Etiquette/"):
		if "etiquette" not in keywords:
			errors.add("Only 'etiquette' tagged items should be stored in '/Etiquette' subfolder")


def validate_single_filename(abspath, filename, item, errors):
	"""
	Checks if file is accessible and matches item metadata
	"""

	if not os.path.isfile(abspath):
		errors.add("File [{abspath}] is not accessible".format(
			abspath=abspath
		))
	if not utils.isfile_case_sensitive(abspath):
		errors.add("File [{abspath}] is not accessible in case-sensitive mode".format(
			abspath=abspath
		))

	booktype = item.get("booktype")
	validate_periodical_filename(filename, item, errors)
	validate_short_desription_filename(filename, item, errors)
	validate_etiquette_filename(filename, item, errors)

	if booktype in MULTIENTRY_BOOKTYPES:
		return
	metadata = utils.extract_metadata_from_file(filename)

	#validating optional author, edition, tome
	#in case when item specifies value, but filename does not
	optional_meta_fields = [
		"author"
	]
	if booktype:
		optional_meta_fields += [
			"edition",
			"volume",
			#For serial books, no number is present in metadata
			#Temporary disable check here
			#"number",
			"part"
		]

	for meta_field in optional_meta_fields:
		if (
			(item.has(meta_field)) and
			(meta_field not in metadata)
		):
			errors.add("Field {meta_field} is not specified in filename [{filename}]".format(
				meta_field=meta_field,
				filename=filename
			))

	meta_keywords = metadata.get("keywords", {})
	source_file = item.get("source_file")
	if (
		(const.META_INCOMPLETE in meta_keywords) and
		(source_file != "_problems.bib")
	):
		errors.add("Incomplete entries should be stored in _problems.bib")

	searches = utils.make_searches_from_metadata(metadata)
	for search_key, search_func in searches.items():
		if not search_func(item):
			errors.add(
				"Item is not searchable by {search_key} extracted from filename {abspath}.\n"
				"    Item has: {item_value}\n"
				"    Search has: {search_value}".format(
				search_key=search_key,
				item_value=item.get(search_key),
				search_value=metadata[search_key],
				abspath=abspath
			))


#single parameter group validations (executed once per entry)
def validate_id(item, errors):
	"""
	Checks item for id presence and validity
	Raises ValueError if no id present
	"""
	item_id = item.id()
	utils.require(
		item_id is not None,
		ValueError("Some items do not own the id")
	)
	if not const.ID_REGEXP.match(item_id):
		errors.add("Item id doesn't match ID_REGEXP")
	if len(item_index["id"][item_id]) != 1:
		errors.add("Item id is not unique")


def validate_parser_generated_fields(item, errors):
	"""
	Checks presence of the following fields:
	* booktype
	* source
	* year_from
	* year_to
	* year_circa
	"""
	OBLIGATORY_FIELDS = ["booktype", "source", "year_from", "year_to", "year_circa"]
	for field in OBLIGATORY_FIELDS:
		if not item.has(field):
			errors.add("Parser hasn't generated obligatory field {field}".format(
				field=field
			))


def validate_obligatory_fields(item, errors):
	"""
	Checks presence of the following fields:
	* langid
	* year
	* title
	* added_on
	"""
	OBLIGATORY_FIELDS = ["langid", "year", "added_on"]
	for field in OBLIGATORY_FIELDS:
		if not item.has(field):
			errors.add("Obligatory field {field} is missing".format(
				field=field
			))


def validate_allowed_fields(item, errors):
	"""
	Checks if all fields of an item are allowed
	"""
	diff = item.fields() - ALLOWED_FIELDS
	if len(diff) > 0:
		errors.add("Fields {fields!r} aren't allowed".format(
			fields=diff
		))


def validate_translation_fields(item, errors):
	"""
	Checks that translation entries should have the following fields:
	* origlanguage
	* origauthor
	* translator
	"""
	TRANSLATION_FIELDS = ["origlanguage", "translator"]
	TRANSLATION_OBLIGATORY_FIELDS = ["origauthor", "translator", "origlanguage"]
	is_translation = False
	for field in TRANSLATION_FIELDS:
		if item.has(field):
			is_translation = True
			break
	if not is_translation:
		return

	for field in TRANSLATION_OBLIGATORY_FIELDS:
		if not item.has(field):
			errors.add("Field {field} is required for translations".format(
				field=field
			))


def validate_shorthand(item, errors):
	"""
	Checks that either author or shorthand should be present
	"""
	MAX_SHORTHAND_LENGTH = 25
	author = item.get("author")
	pseudo_author = item.get("pseudo_author")
	compiler = item.get("compiler")
	shorthand = item.get("shorthand")
	if not any([author, compiler, pseudo_author, shorthand]):
		errors.add("Shorthand is missing")

	if shorthand and (len(shorthand) > MAX_SHORTHAND_LENGTH):
		errors.add("Shorthand is oversized (max length is {max_length})".format(
			max_length=MAX_SHORTHAND_LENGTH
		))


def validate_title_starts_from_shorthand(item, errors):
	"""
	Checks if title starts from shorthand
	"""
	title = item.get("title") or item.get("incipit")
	shorthand = item.get("shorhand")
	if (shorthand is None):
		return
	if not title.startswith(shorthand):
		errors.add("Title should begin with shorthand")


def validate_isbn(item, errors):
	"""
	Checks ISBN for validity.
	Will accept both ISBN-10 and ISBN-13 formats
	"""
	isbn_list = item.get("isbn")
	if isbn_list is None:
		return
	for idx, single_isbn in enumerate(isbn_list):
		if not isbn.is_valid(single_isbn):
			errors.add("ISBN #{idx} isn't valid".format(
				idx=idx
			))
			continue
		formatted = isbn.format(single_isbn)
		if (formatted != single_isbn):
			errors.add("ISBN #{idx} ({single_isbn}) should be reformatted to {formatted}".format(
				idx=idx,
				single_isbn=single_isbn,
				formatted=formatted
			))
		if (isbn.isbn_type(single_isbn) != 'ISBN13'):
			errors.add("ISBN-10 #{idx} ({single_isbn}) should be reformatted to ISBN-13 {formatted}".format(
				idx=idx,
				single_isbn=single_isbn,
				formatted=isbn.to_isbn13(single_isbn)
			))


def validate_issn(item, errors):
	"""
	Checks ISSN for validity
	"""
	issn_list = item.get("issn")
	if issn_list is None:
		return
	for idx, single_issn in enumerate(issn_list):
		if not issn.is_valid(single_issn):
			errors.add("ISSN #{idx} isn't valid".format(
				idx=idx
			))
		formatted = issn.format(single_issn)
		if (formatted != single_issn):
			errors.add("ISSN #{idx} ({single_issn}) should be reformatted to {formatted}".format(
				idx=idx,
				single_issn=single_issn,
				formatted=formatted
			))


def validate_booktype(item, errors):
	"""
	Checks if booktype belongs to a valid list.
	Performs extra checks for field presence based on booktype
	"""
	VALID_BOOKTYPES = {
		"article",
		"periodical",

		"book",
		"inbook",
		"mvbook",

		"proceedings",
		"inproceedings",

		"reference",
		"mvreference",

		"collection",
		"incollection",

		"thesis",
		"unpublished",
	}
	#volumes tag should be present for these booktypes
	MULTIVOLUME_BOOKTYPES = {"mvbook", "mvreference"}

	booktype = item.get("booktype")
	if booktype is None:
		return

	if (booktype not in VALID_BOOKTYPES):
		errors.add("Booktype {booktype} invalid".format(
			booktype=booktype
		))

	if (booktype in MULTIVOLUME_BOOKTYPES):
		volumes = item.get("volumes")
		if volumes is None:
			errors.add("Field volumes expected for booktype {booktype}".format(
				booktype=booktype
			))

	if (booktype == "article"):
		journaltitle = item.get("journaltitle")
		if journaltitle is None:
			errors.add("Field journaltitle expected for booktype {booktype}".format(
				booktype=booktype
			))
	if (booktype in ("inproceedings", "inbook")):
		booktitle = item.get("booktitle")
		if booktitle is None:
			errors.add("Field booktitle expected for booktype {booktype}".format(
				booktype=booktype
			))
	if (booktype == "thesis"):
		thesis_type = item.get("type")
		if thesis_type is None:
			errors.add("Field type expected for booktype {booktype}".format(
				booktype=booktype
			))
		institution = item.get("institution")
		if institution is None:
			errors.add("Field institution  expected for booktype {booktype}".format(
				booktype=booktype
			))


def validate_catalogue_code(item, errors):
	"""
	Checks if catalogue code againts
	"""
	catalogue = item.get("catalogue")
	if (catalogue is None):
		return
	for single_code in catalogue:
		if not const.CATALOGUE_REGEXP.match(single_code):
			errors.add("Catalogue code {single_code} doesn't match CATALOGUE_REGEXP".format(
				single_code=single_code
			))


def validate_library_fields(item, errors):
	"""
	Checks if library-related params with storage specifications
	are available for @unpublished
	"""
	booktype = item.get("booktype");
	if (booktype != "unpublished"):
		return
	REQUIRED_FIELDS = [
		"library",
		"library_location",
		"library_code"
	];
	for field in REQUIRED_FIELDS:
		if not item.has(field):
			errors.add("Field {field} is missing".format(
				field=field
			))


def validate_commentator(item, errors):
	"""
	Checks if "commentary" keyword is present
	in case of known commentator
	"""
	commentator = item.get("commentator")
	keywords = set(item.get("keywords") or {})

	has_comments = (
		(commentator is not None) or
		("commentary" in keywords)
	)

	if has_comments:
		if ("commentary" not in keywords):
			errors.add("Keyword commentary is missing")
		if commentator is None:
			errors.add("Field commentator expected")


def validate_url_validity(item, errors):
	"""
	Checks url for validity
	"""
	url = item.get("url")
	item_id = item.get("id")
	if url is None:
		return
	for number, single_url in enumerate(url):
		if not utils.is_url_valid(single_url, item):
			errors.add("Field url with value [{single_url}] and number {number} is wrong".format(
				single_url=single_url,
				number=number
			))

		if not utils.is_url_self_served(single_url, item):
			continue

		match = utils.SELF_SERVED_URL_REGEXP.match(single_url)
		if not match:
			errors.add("Self served url [{single_url}] doesn't match SELF_SERVED_URL_REGEXP".format(
				single_url=single_url
			))
			continue
		if (match.group("item_id") != item_id):
			errors.add("Wrong item_id specified in self-served url")
			continue

		single_filename, single_filesize = utils.get_file_info_from_url(single_url, item)
		metadata = utils.extract_metadata_from_file(single_filename)
		owners = metadata.get("owner").split("+")
		if not owners:
			errors.add("Owner specification expected for self-served url #{number} (url={url}, filename={filename})".format(
				number=number,
				url=single_url,
				filename=single_filename
			))
			continue
		for owner in owners:
			owner_fullname = config.parser.bookkeepers.get(owner)
			if owner_fullname:
				annotation = item.get("annotation")
				if (
					(not annotation) or
					(owner_fullname not in annotation)
				):
					errors.add("Owner fullname ({owner_fullname}) should be present in annotation".format(
						owner_fullname=owner_fullname
					))


def validate_url_accessibility(item, errors):
	"""
	Checks url for accessibility
	"""
	url = item.get("url")
	if url is None:
		return
	for number, single_url in enumerate(url):
		if not utils.is_url_accessible(single_url, item):
			errors.add("Field url with value [{single_url}] and number {number} is unaccessible".format(
				single_url=single_url,
				number=number
			))


def validate_transcription_filename(item, errors):
	"""
	Checks if transcription is valid, accessible and named correctly
	"""
	transcription = item.get("transcription")
	if transcription is None:
		return

	abspath = os.path.join(config.parser.markdown_dir, transcription)
	validate_single_filename(
		abspath,
		transcription,
		item,
		errors
	)


def validate_location(item, errors):
	"""
	Checks that location must be present in case of publisher presence
	"""
	location = item.get("location")
	publisher = item.get("publisher")
	if (
		(publisher is not None) and
		(location is None)
	):
		errors.add("Location should be present when publisher is known")


def validate_partial_fields(item, errors):
	"""
	Checks if pages field matches PAGES_REGEX
	"""
	PARTIAL_FIELDS = {
		"pages": const.PAGES_REGEXP,
		"crossref": None
	}
	booktype = item.get("booktype")
	is_partial = (booktype in PARTIAL_BOOKTYPES)

	for field, regexp in PARTIAL_FIELDS.items():
		value = item.get(field)
		if value is None:
			continue
		if not is_partial:
			errors.add("Field {field} is not allowed for booktype {booktype}".format(
				field=field,
				booktype=booktype
			))
		if (regexp is not None) and not regexp.match(value):
			errors.add("Field {field}={value} doesn't match format regexp".format(
				field=field,
				value=value
			))


def validate_volume(item, errors):
	"""
	Checks volume and volumes parameters for validity
	"""
	volume = item.get("volume")
	volumes = item.get("volumes")
	if volume is not None:
		if volume <= 0:
			errors.add("Field volume can't be negative")
	if volumes is not None:
		if volumes <= 1:
			errors.add("Field volumes should be 2 or more (got {volumes})".format(
				volumes=volumes
			))
	if (
		(volume is not None) and
		(volumes is not None)
	):
		if (volume > volumes):
			errors.add("Field volume ({volume}) can't exceed field volumes ({volumes})".format(
				volume=volume,
				volumes=volumes
			))


def validate_series(item, errors):
	"""
	Checks series and number parameters for validity
	"""
	#perdiodical booktypes may also have number field,
	#through they aren't serial entries
	PERIODICAL_BOOKTYPES = {
		"periodical",
		"article"
	}
	booktype = item.get("booktype")
	if booktype in PERIODICAL_BOOKTYPES:
		return
	SERIAL_FIELDS = ["series"]
	is_serial = False
	for field in SERIAL_FIELDS:
		if item.has(field):
			is_serial = True
			break
	if not is_serial:
		return
	OBLIGATORY_SERIAL_FIELDS = ["series", "number"]
	for field in OBLIGATORY_SERIAL_FIELDS:
		if not item.has(field):
			errors.add("Field {field} expected for serial books".format(
				field=field
			))


def validate_edition(item, errors):
	"""
	Checks if edition points to a reissue (i. e. not first edition)
	"""
	edition = item.get("edition")
	if edition is None:
		return
	if edition <= 1:
		errors.add("Field edition should be 2 or more (got {edition})".format(
			edition=edition
		))


def validate_keywords(item, errors):
	"""
	Checks keywords for their allowness and correct inheritance
	"""
	keywords = set(item.get("keywords") or {})
	if keywords is None:
		return

	unallowed_keywords = (keywords - config.parser.keywords)
	for keyword in unallowed_keywords:
		errors.add("Keyword [{keyword}] is unallowed".format(
			keyword=keyword
		))
	for keyword in keywords:
		parent_keyword = utils.extract_parent_keyword(keyword)
		if parent_keyword not in keywords:
			errors.add("Parent keyword [{parent_keyword} is missing for keyword [{keyword}]".format(
				parent_keyword=parent_keyword,
				keyword=keyword
			))
	if ("useless" in keywords) and (len(keywords) != 1):
		errors.add("Keyword [useless] can't be combined with other keywords")


def validate_filename(item, errors):
	"""
	Checks filename against various tests
	"""
	NOT_DIGITIZED_KEYWORD = "not digitized"
	filename = item.get("filename")

	booktype = item.get("booktype")
	if booktype in MULTIENTRY_BOOKTYPES:
		return

	keywords = set(item.get("keywords") or {})
	if filename is None:
		if (NOT_DIGITIZED_KEYWORD not in keywords):
			errors.add("Keyword {keyword} should be specified".format(
				keyword=NOT_DIGITIZED_KEYWORD
			))
		return
	else:
		if (NOT_DIGITIZED_KEYWORD in keywords):
			errors.add("Keyword {keyword} shouldn't be specified".format(
				keyword=NOT_DIGITIZED_KEYWORD
			))
	for single_filename in filename:
		#filename starts with slash - trimming it
		abspath = os.path.join(config.www.elibrary_dir, single_filename[1:])
		validate_single_filename(abspath, single_filename, item, errors)


def validate_source_file(item, errors):
	"""
	Checks if source file language matches item language
	"""
	MULTILANG_FILES = {
		"_antidance.bib",
		"_collection.bib",
		"_periodical.bib",
		"_periodical-modern.bib",
		"_problems.bib",
		"_references.bib",
		"proceedings-dhds.bib",
		"proceedings-rothenfelser.bib",
		"proceedings-spb.bib",
	}
	source_file = item.get("source_file")
	langid = item.get("langid")
	if source_file in MULTILANG_FILES:
		return

	source_langs = const.LONG_LANG_MAP[source_file]
	if langid not in source_langs:
		errors.add("Item language {item_lang} doesn't match any of source file languages ({source_langs})".format(
			item_lang=langid,
			source_langs=", ".join(source_langs)
		))


def validate_added_on(item, git_added_on, errors):
	git_date = git_added_on[item.id()]
	item_date = item.get("added_on")
	if item_date != git_date:
		errors.add("Item added_on is {item_date}, while git suggests {git_date}".format(
			item_date=item_date,
			git_date=git_date
		))


def validate_item(item, git_added_on, make_extra_checks):
	errors = set()
	validate_id(item, errors)
	validate_parser_generated_fields(item, errors)
	validate_obligatory_fields(item, errors)
	validate_allowed_fields(item, errors)
	validate_translation_fields(item, errors)
	validate_transcription_filename(item, errors)
	validate_catalogue_code(item, errors)
	validate_library_fields(item, errors)
	validate_shorthand(item, errors)
	validate_isbn(item, errors)
	validate_issn(item, errors)
	validate_booktype(item, errors)
	validate_commentator(item, errors)
	validate_url_validity(item, errors)
	validate_volume(item, errors)
	validate_series(item, errors)
	validate_keywords(item, errors)
	validate_filename(item, errors)
	validate_source_file(item, errors)
	validate_partial_fields(item, errors)
	validate_added_on(item, git_added_on, errors)
	if make_extra_checks:
		validate_title_starts_from_shorthand(item, errors)
		validate_url_accessibility(item, errors)
	return errors


def validate_items(items, git_added_on, make_extra_checks):
	result = dict()
	for item in items:
		errors = validate_item(item, git_added_on, make_extra_checks)
		if errors:
			result[item.id()] = errors
	return result


@opster.command()
def main(
	make_extra_checks=("", False, "Add some extra checks"),
	log_all_errors=("", False, "Log all errors, not only newly introduced ones"),
	ignore_missing_ids=("", False, "Update validation data even when some ids were lost"),
	ignore_added_errors=("", False, "Update validation data even when new errors were introduced"),
):
	"""
	Validates bibliography over a bunch of rules
	"""
	logging.info("Fetching added_on from git")
	git_added_on = fetch_added_on_from_git()
	logging.info("Fetching list of pdf from filesystem")
	physically_stored = fetch_filelist_from_fs()

	for item in items:
		filename = item.get("filename")
		if not filename:
			continue
		for file in filename:
			physically_stored.discard(file)
	for path in physically_stored:
		logging.warn("Unreferenced file found in {elibrary}: {path}".format(
			elibrary=config.www.elibrary_dir,
			path=path
		))

	logging.info("Going to process {0} items".format(len(items)))
	executor = concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())
	futures = {
		executor.submit(validate_items, items_batch, git_added_on, make_extra_checks): None
		for items_batch in utils.batched(items, 100)
	}

	erroneous_items = dict()
	for future in concurrent.futures.as_completed(futures):
		try:
			result = future.result()
			for item_id, errors in result.items():
				if not errors:
					continue
				erroneous_items[item_id] = errors
				if log_all_errors:
					for error in errors:
						logging.debug("Errors for {item_id}: {error}".format(
							item_id=item_id,
							error=error
						))
		except Exception as ex:
			logging.exception("Exception while validating {item_id} ({source}): {ex}".format(
				item_id=item_id,
				source=item.source(),
				ex=ex
			))

	update_validation_data(
		erroneous_items,
		ignore_missing_ids,
		ignore_added_errors
	)
	if erroneous_items:
		logging.warning("Found {items_count} erroneous items".format(
			items_count=len(erroneous_items)
		))


if __name__ == "__main__":
	main.command()
