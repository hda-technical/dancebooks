#!/usr/bin/env python3
import datetime
import json
import logging
import os
import re
import subprocess
import sys

import click
import requests
from stdnum import isbn
from stdnum import issn

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks.config import config
from dancebooks import const
from dancebooks import bib_parser
from dancebooks import utils

items, item_index = bib_parser.BibParser().parse_folder(config.parser.bibdata_dir)

#filename for storing previous validation state
DATA_JSON_FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate.json")
DATA_FIELDS = {
	"added_on",
	"altauthor",
	"note",
	"author",
	"booktitle",
	"type",
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
	"provenance",
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
	"serial_number",
	"shorthand",
	"source",
	"title",
	"type",
	"transcriber",
	"transcription",
	"transcription_features",
	"transcription_note",
	"translator",
	"thesis_type",
	"url",
	"volume",
	"volumes",
	"year",
	"year_for",
}

ANCILLARY_FIELDS = {
	"all_fields",
	"availability",
	"filesize",
	"source_file",
	"source_line",
	"year_circa",
	"year_from",
	"year_to",
}

ALLOWED_FIELDS = (ANCILLARY_FIELDS | DATA_FIELDS)

# Entry types that can be nested in the other bibliographed entries
PARTIAL_ENTRY_TYPES = {
	# article -> periodical
	"article",
	# inproceeding -> proceedings
	"inproceedings",
	# incollection -> collection
	"incollection",
	# inbook -> book
	"inbook",
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
		#line number
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
	filter = lambda path: path.endswith(".bib")
	for path in utils.search_in_folder(config.parser.bibdata_dir, filter):
		result.update(blame_file(path))
	return result


def fetch_filelist_from_fs():
	if not os.path.isdir(config.www.elibrary_dir):
		return []
	FOLDERS_TO_VALIDATE = [
		"Library"
	]
	EXCLUDED_FOLDERS = {
		"Ancillary sources (not in bibliography)",
		"Leaflets (not in bibliography)",
	}
	trim_root = lambda path: os.path.relpath(path, start=config.www.elibrary_dir)
	filter = lambda path: os.path.isfile(path) and path.endswith(".pdf")
	stored_files = []
	for basename in FOLDERS_TO_VALIDATE:
		folder = os.path.join(config.www.elibrary_dir, basename)
		stored_files += list(
			map(
				trim_root,
				utils.search_in_folder(folder, filter, excludes=EXCLUDED_FOLDERS)
			)
		)
	return set(stored_files)


def fetch_backups_from_fs():
	assert os.path.isdir(config.www.backup_dir)
	trim_root = lambda path: os.path.relpath(path, start=config.www.backup_dir)
	filter = lambda path: const.FILENAME_REGEXP.match(os.path.basename(path))
	backups = set(
		trim_root(backup)
		for backup in utils.search_in_folder(config.www.backup_dir, filter)
	)
	return set(backups)


#executed once per validation run
def update_validation_data(
	errors,
	remove_missing_ids,
	store_new_errors
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
		with open(DATA_JSON_FILENAME, "r") as fp:
			try:
				validation_data = json.load(fp)
			except Exception:
				#when no JSON object could be decoded,
				#validation data shouldn't be updated
				pass

	current_ids = set(item_index["id"].keys())
	old_ids = set(validation_data["ids"])
	changed_ids = old_ids - current_ids

	for source, target in config.www.id_redirections.items():
		if target and target not in current_ids:
			logging.error(f"    Redirection of {source} refers to a non-existent id {target}")
	known_redirections = set(config.www.id_redirections.keys())
	#ids that were lost due to renaming
	lost_ids = changed_ids - known_redirections
	#ids that exist in files, and are also present in id_redirections
	found_ids = current_ids & known_redirections

	old_errors = set(validation_data["errors"])
	new_errors = set(errors.keys())
	added_errors = new_errors - old_errors
	if len(added_errors) > 0:
		logging.error(f"{len(added_errors)} new erroneous entries were introduced")
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

	if (not previous_data_exists) or (lost_ids and remove_missing_ids):
		validation_data["ids"] = list(current_ids)
	if (not previous_data_exists) or (new_errors and store_new_errors):
		validation_data["errors"] = list(new_errors)
	with open(DATA_JSON_FILENAME, "w") as fp:
		json.dump(validation_data, fp, indent=4)


def validate_periodical_filename(filename, item, errors):
	if filename.endswith(".md"):
		#periodical transcriptions are validated by this code too
		return
	type = item.get("type")

	is_periodical_type = type in ("article", "periodical")
	is_periodical_filename = filename.startswith("/Periodical/")
	if not is_periodical_filename:
		return

	if not all([
		is_periodical_type,
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
		errors.add(f"File [{abspath}] is not accessible")
	# Commented this out as this code path is extremely slow on WSL2
	# if not utils.isfile_case_sensitive(abspath):
		# errors.add(f"File [{abspath}] is not accessible in case-sensitive mode")

	type = item.get("type")
	validate_periodical_filename(filename, item, errors)
	validate_short_desription_filename(filename, item, errors)
	validate_etiquette_filename(filename, item, errors)

	metadata = utils.extract_metadata_from_file(filename)

	if item.has("edition") and "edition" not in metadata:
		errors.add(f"Field 'edition' is not specified in filename [{filename}]")

	if metadata.incomplete and (item.get("note") is None):
		errors.add("Incomplete entries must have lacunas described in the 'note' field")

	searches = utils.make_searches_from_metadata(metadata)
	for search_key, search_func in searches.items():
		if not search_func(item):
			errors.add(
				f"Item is not searchable by {search_key} extracted from filename {abspath}.\n"
				f"    Item has: {item.get(search_key)}\n"
				f"    Search has: {metadata[search_key]}"
			)


#single parameter group validations (executed once per entry)
def validate_id(item, errors):
	"""
	Checks item for id presence and validity
	Raises ValueError if no id present
	"""
	item_id = item.id
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
	* type
	* source
	* year_from
	* year_to
	* year_circa
	"""
	OBLIGATORY_FIELDS = ["type", "source", "year_from", "year_to", "year_circa"]
	for field in OBLIGATORY_FIELDS:
		if not item.has(field):
			errors.add(f"Parser hasn't generated obligatory field {field}")


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
			errors.add(f"Obligatory field {field} is missing")


def validate_allowed_fields(item, errors):
	"""
	Checks if all fields of an item are allowed
	"""
	diff = item.fields() - ALLOWED_FIELDS
	if len(diff) > 0:
		errors.add(f"Fields {diff!r} are not allowed")


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
			errors.add(f"Field {field} is required for translations")


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
		errors.add(f"Shorthand is oversized (max length is {MAX_SHORTHAND_LENGTH})")


def validate_isbn(item, errors):
	"""
	Checks ISBN for validity.
	Will accept both ISBN-10 and ISBN-13 formats
	"""
	isbn_list = item.get("isbn")
	if isbn_list is None:
		return
	for idx, single_isbn in enumerate(isbn_list):
		try:
			isbn.validate(single_isbn)
		except isbn.ValidationError as ex:
			errors.add(f"ISBN #{idx} ({single_isbn}) is not valid: {ex}")
			continue
		formatted = isbn.format(single_isbn)
		if (formatted != single_isbn):
			errors.add(f"ISBN #{idx} ({single_isbn}) should be reformatted to {formatted}")
		if (isbn.isbn_type(single_isbn) != 'ISBN13'):
			isbn13 = isbn.to_isbn13(single_isbn)
			errors.add(f"ISBN-10 #{idx} ({single_isbn}) should be reformatted to ISBN-13 {isbn13}")


def validate_issn(item, errors):
	"""
	Checks ISSN for validity
	"""
	issn_list = item.get("issn")
	if issn_list is None:
		return
	for idx, single_issn in enumerate(issn_list):
		if not issn.is_valid(single_issn):
			errors.add(f"ISSN #{idx} [{single_issn}] isn't valid")
		formatted = issn.format(single_issn)
		if (formatted != single_issn):
			errors.add(f"ISSN #{idx} [{single_issn}] should be reformatted to [{formatted}]")


def validate_type(item, errors):
	"""
	Checks if type belongs to a valid list.
	Performs extra checks for field presence based on type
	"""
	VALID_ENTRY_TYPES = {
		"article",
		"periodical",

		"book",
		"inbook",
		"mvbook",

		"proceedings",
		"mvproceedings",
		"inproceedings",

		"reference",
		"mvreference",

		"collection",
		"incollection",

		"thesis",
		"unpublished",
	}
	#volumes tag should be present for these types
	PERIODICAL_ENTRY_TYPES = {"periodical", "article"}

	type = item.get("type")
	if type is None:
		return

	if (type not in VALID_ENTRY_TYPES):
		errors.add(f"Entry type {type} is invalid")

	if (type == "article"):
		journaltitle = item.get("journaltitle")
		if journaltitle is None:
			errors.add(f"Field journaltitle expected for type {type}")
		pages = item.get("pages")
		if pages is None:
			errors.add(f"Field pages expected for type {type}")
	if (type in ("inproceedings", "inbook")):
		booktitle = item.get("booktitle")
		if booktitle is None:
			errors.add(f"Field booktitle expected for entry type {type}")
	if (type == "thesis"):
		thesis_type = item.get("thesis_type")
		if thesis_type is None:
			errors.add(f"Field thesis_type expected for entry type {type}")
		institution = item.get("institution")
		if institution is None:
			errors.add(f"Field institution expected for type {type}")

	if item.get("number"):
		if type not in PERIODICAL_ENTRY_TYPES:
			errors.add("Field number can only be set for periodicals")


def validate_catalogue_code(item, errors):
	"""
	Checks if catalogue code againts
	"""
	catalogue = item.get("catalogue")
	if (catalogue is None):
		return
	for single_code in catalogue:
		if not const.CATALOGUE_REGEXP.match(single_code):
			errors.add(f"Catalogue code {single_code} doesn't match CATALOGUE_REGEXP")


def validate_library_fields(item, errors):
	"""
	Checks if library-related params with storage specifications
	are available for @unpublished
	"""
	type = item.get("type");
	if (type != "unpublished"):
		return
	REQUIRED_FIELDS = [
		"library",
		"library_location",
		"library_code"
	];
	for field in REQUIRED_FIELDS:
		if not item.has(field):
			errors.add(f"Field {field} is missing")


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


def validate_url(item, errors):
	"""
	Checks url for validity
	"""
	url = item.get("url")
	item_id = item.get("id")
	if url is None:
		return
	for idx, single_url in enumerate(url):
		if not utils.is_url_valid(single_url, item):
			errors.add(f"Field url with value [{single_url}] and number #{idx} is wrong")

		if not utils.is_url_self_served(single_url):
			continue

		match = utils.SELF_SERVED_URL_REGEXP.match(single_url)
		if not match:
			errors.add(f"Self served url [{single_url}] doesn't match SELF_SERVED_URL_REGEXP")
			continue
		if (match.group("item_id") != item_id):
			errors.add("Wrong item_id specified in self-served url")
			continue

		single_filename, single_filesize = utils.get_file_info_from_url(single_url, item)
		metadata = utils.extract_metadata_from_file(single_filename)

		if (owners := metadata.get("owner")) is None:
			errors.add(f"Owner specification expected for self-served url #{idx} [{url}], stored at [{single_filename}]")
			continue
		for owner in owners.split("+"):
			owner_fullname = config.parser.bookkeepers.get(owner)
			if owner_fullname:
				note = item.get("note")
				if note is None:
					errors.add(f"Owner fullname ({owner_fullname}) should be present in note, but the note is missing")
				elif owner_fullname not in note:
					errors.add(f"Owner fullname ({owner_fullname}) should be present in note, but it is not")


def validate_url_accessibility(item, errors):
	"""
	Checks url for accessibility
	"""
	url = item.get("url")
	if url is None:
		return
	for idx, single_url in enumerate(url):
		if not utils.is_url_accessible(single_url, item):
			errors.add(f"url {single_url!r} at position {idx} is unaccessible")


def validate_transcription(item, errors):
	"""
	Checks if transcription is valid, accessible and named correctly
	"""
	transcription = item.get("transcription")
	if transcription is None:
		return

	transcriber = item.get("transcriber")
	if transcriber is None:
		errors.add(f"Transcribed entry must has transcriber specified")

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
	type = item.get("type")
	if type not in PARTIAL_ENTRY_TYPES:
		if (crossref := item.get("crossref")) is not None:
			errors.add(f"Entry of type {type} can not have crossref field")
		pages = item.get("pages")
		if (pages := item.get("pages")) is not None:
			errors.add(f"Entry of type {type} can not have pages field")


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
			errors.add(f"Field volumes should be 2 or more (got {volumes})")
	if (
		(volume is not None) and
		(volumes is not None)
	):
		if (volume > volumes):
			errors.add(f"Field volume ({volume}) can't exceed field volumes ({volumes})")


MONTH_REGEXP = re.compile(r"(?P<start>\d+)(-(?P<end>\d+))?")
def validate_month(item, errors):
	def validate_single(month):
		month = int(month)
		if (month < 1 or month > 12):
			errors.add(f"Month {month} should be in range 1..12")
			return
	month = item.get("month")
	if month is None:
		return
	match = MONTH_REGEXP.fullmatch(month)
	if not match:
		errors.add(f"Field month ({month}) does not match '{MONTH_REGEXP.pattern}'")
		return
	validate_single(match["start"])
	if (end := match["end"]) is not None:
		validate_single(end)


# WARN:
#	[mancini_1620_ballo] uses folio numeration, thus recto and verso suffixes are legal.
#	[wilson_1914_hesitation] and [wilson_1914_one_step] are taken from _The Atlanta Constitution_,
#	which uses block-based numeration. Thus capital letter suffixes are legal too.
PAGES_REGEXP = re.compile(r"(?P<start>\d+)[rvMF]?(-(?P<end>\d+)[rv]?)?")
def validate_pages(item, errors):
	pages = item.get("pages")
	if pages is None:
		return

	match = PAGES_REGEXP.fullmatch(pages)
	if not match:
		errors.add(f"Field pages ({pages}) does not match '{PAGES_REGEXP.pattern}'")
		return


def validate_series(item, errors):
	"""
	Checks series and number parameters for validity
	"""
	SERIAL_FIELDS = ["series"]
	is_serial = False
	for field in SERIAL_FIELDS:
		if item.has(field):
			is_serial = True
			break
	if not is_serial:
		return
	OBLIGATORY_SERIAL_FIELDS = ["series", "serial_number"]
	for field in OBLIGATORY_SERIAL_FIELDS:
		if not item.has(field):
			errors.add(f"Field {field} expected for serial books")


def validate_edition(item, errors):
	"""
	Checks if edition points to a reissue (i. e. not first edition)
	"""
	edition = item.get("edition")
	if edition is None:
		return
	if edition <= 1:
		errors.add(f"Field edition should be 2 or more (got {edition})")


def validate_keywords(item, errors):
	"""
	Checks keywords for their allowness and correct inheritance
	"""
	keywords = set(item.get("keywords") or {})
	if keywords is None:
		return

	unallowed_keywords = (keywords - config.parser.keywords)
	for keyword in unallowed_keywords:
		errors.add(f"Keyword [{keyword}] is unallowed")
	for keyword in keywords:
		parent_keyword = utils.extract_parent_keyword(keyword)
		if parent_keyword not in keywords:
			errors.add(f"Parent keyword [{parent_keyword} is missing for keyword [{keyword}]")
	if ("useless" in keywords) and (len(keywords) != 1):
		errors.add("Keyword [useless] can't be combined with other keywords")


def validate_filename(item, errors):
	"""
	Checks filename against various tests
	"""
	NOT_DIGITIZED_KEYWORD = "not digitized"
	filename = item.get("filename") or []
	crossref = item.get("crossref")

	type = item.get("type")

	keywords = set(item.get("keywords") or {})
	if not filename and not crossref:
		if (NOT_DIGITIZED_KEYWORD not in keywords):
			errors.add(f"Keyword {NOT_DIGITIZED_KEYWORD} should be specified")
		return
	else:
		if (NOT_DIGITIZED_KEYWORD in keywords):
			errors.add(f"Keyword {NOT_DIGITIZED_KEYWORD} shouldn't be specified")
	for single_filename in filename:
		abspath = os.path.join(config.www.elibrary_dir, single_filename)
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
		source_langs_string = ", ".join(source_langs)
		errors.add(f"Item language {langid} doesn't match any of source file languages ({source_langs_string})")


def validate_added_on(item, git_added_on, errors):
	git_date = git_added_on[item.id]
	item_date = item.get("added_on")
	if item_date != git_date:
		errors.add(f"Item added_on is {item_date}, while git suggests {git_date}")


def validate_note(item, errors):
	note = item.get("note")
	if note is None:
		return
	if note[-1] != '.':
		errors.add(f"Item note does not end with the dot")


def validate_item(item, git_added_on):
	errors = set()
	validate_id(item, errors)
	validate_parser_generated_fields(item, errors)
	validate_obligatory_fields(item, errors)
	validate_allowed_fields(item, errors)
	validate_translation_fields(item, errors)
	validate_transcription(item, errors)
	validate_catalogue_code(item, errors)
	validate_library_fields(item, errors)
	validate_shorthand(item, errors)
	validate_isbn(item, errors)
	validate_issn(item, errors)
	validate_type(item, errors)
	validate_commentator(item, errors)
	validate_url(item, errors)
	validate_volume(item, errors)
	validate_month(item, errors)
	validate_pages(item, errors)
	validate_series(item, errors)
	validate_keywords(item, errors)
	validate_filename(item, errors)
	validate_source_file(item, errors)
	validate_partial_fields(item, errors)
	validate_added_on(item, git_added_on, errors)
	return errors


def validate_items(items, git_added_on):
	result = dict()
	for item in items:
		errors = validate_item(item, git_added_on)
		if errors:
			result[item.id] = errors
	return result


def validate_backups():
	logging.info("Fetching list of backups from filesystem")
	backups = fetch_backups_from_fs()
	logging.info(f"Found {len(backups)} items in backup")

	logging.info(f"Fetching backup metadata from {config.www.backup_metadata_url}")
	metadata = requests.get(config.www.backup_metadata_url).json()
	logging.info(f"Fetched {len(metadata)} backups metadata")

	# keep only backups with type=s3
	# FIXME: upload remaining backups to s3
	metadata = [item for item in metadata if item["type"] == "s3"]

	for metadatum in metadata:
		backup_id = metadatum["id"]
		full_path = os.path.join(config.www.backup_dir, metadatum["path"])
		if not os.path.exists(full_path):
			logging.warning(f"Backup #{backup_id} at '{full_path}' does not exists")

	POSSIBLE_BACKUP_EXTENSIONS = [".pdf", ".tif"]
	strange_backups_number = 0
	for backup in backups:
		backup_without_extension = (
			#FIXME not that hacky way is required
			os.path.splitext(backup)[0]
			if backup.endswith(".tif") else
			backup
		)
		possible_library_paths = [
			os.path.join(
				config.www.elibrary_dir,
				backup_without_extension + ext
			)
			for ext in POSSIBLE_BACKUP_EXTENSIONS
		]
		found_in_library = any(map(os.path.isfile, possible_library_paths))
		if not found_in_library:
			strange_backups_number += 1
			logging.warning(f"Backup {config.www.backup_dir}/{backup} is not present in the library")
	if strange_backups_number > 0:
		logging.warning(f"Found {strange_backups_number} strange backups")


@click.command()
@click.option("--backups", "backups", is_flag=True, default=False, help="Validate backups (slow)")
@click.option("--urls", "urls", is_flag=True, default=False, help="Validate url field accessibility (slow)")
@click.option("--store-new-errors", "store_new_errors", is_flag=True, default=False, help="Store new errors and ignore them in the future")
@click.option("--remove-missing-ids", "remove_missing_ids", is_flag=True, default=False, help="Remove lost ids from persistent storage")
def main(*, backups, urls, store_new_errors, remove_missing_ids):
	"""
	Validates bibliography over a bunch of rules
	"""
	logging.info("Fetching added_on from git")
	git_added_on = fetch_added_on_from_git()
	logging.info("Fetching list of pdf from filesystem")
	physically_stored = fetch_filelist_from_fs()
	logging.info(f"Found {len(physically_stored)} physically stored items")
	if backups:
		validate_backups()

	for item in items:
		filename = item.get("filename")
		if not filename:
			continue
		for file in filename:
			physically_stored.discard(file)
	for path in physically_stored:
		logging.warning(f"Unreferenced file found in {config.www.elibrary_dir}: {path}")

	logging.info(f"Going to process {len(items)} items")
	erroneous_items = dict()
	for item in items:
		try:
			errors = validate_item(item, git_added_on)
			if urls:
				validate_url_accessibility(item, errors)
			if not errors:
				continue
			erroneous_items[item.id] = errors
		except Exception as ex:
			logging.exception(f"Exception while validating {item.id} ({item.source}): {ex}")

	update_validation_data(
		erroneous_items,
		remove_missing_ids,
		store_new_errors,
	)
	if erroneous_items:
		logging.warning(f"Found {len(erroneous_items)} erroneous items")


if __name__ == "__main__":
	main()
