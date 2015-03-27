#!/usr/bin/env python3
import collections
import json
import logging
import os.path

import opster

from config import config
import const
import index
import bib_parser
import utils

items = bib_parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.Index(items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

languages = sorted(item_index["langid"].keys())

ERROR_PREFIX = "validation:error:"
#filename for storing previous validation state
DATA_JSON_FILENAME = "_validate.json"

#executed once per validation run
def update_validation_data(ignore_missing_ids):
	"""
	Checks if no book_ids were lost since
	the last validation run on this machine.
	Overwrites known ids if no losses were detected
	"""
	validation_data = {
		"ids": set(),
		"errors": dict()
	}
	if (os.path.exists(DATA_JSON_FILENAME)):
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
	if ((len(lost_ids) == 0) or ignore_missing_ids):
		#no ids were lost
		#updating validation data
		validation_data["ids"] = list(current_ids)

	with open(DATA_JSON_FILENAME, "w") as validation_data_file:
		validation_data_file.write(json.dumps(validation_data))



#single parameter group validations (executed once per entry)
def check_id(item, errors):
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


def check_parser_generated_fields(item, errors):
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
		if item.get(field) is None:
			errors.add("Parser hasn't generated obligatory field {field}".format(
				field=field
			))


def check_obligatory_fields(item, errors):
	"""
	Checks presence of the following fields:
	* langid
	* year
	* title
	* added_on
	"""
	OBLIGATORY_FIELDS = ["langid", "year", "title", "added_on"]
	for field in OBLIGATORY_FIELDS:
		if item.get(field) is None:
			errors.add("Obligatory field {field} is missing".format(
				field=field
			))


def check_translation_fields(item, errors):
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
		if item.get(field) is not None:
			is_translation = True
			break
	if not is_translation:
		return

	for field in TRANSLATION_OBLIGATORY_FIELDS:
		if item.get(field) is None:
			errors.add("Field {field} is required for translations".format(
				field=field
			))


def check_shorthand(item, errors):
	"""
	Checks that either author or shorthand should be present
	"""
	MAX_SHORTHAND_LENGTH = 25
	author = item.get("author")
	shorthand = item.get("shorthand")
	if (
		(author is None) and
		(shorthand is None)
	):
		errors.add("Shorthand is missing")

	if (
		(shorthand is not None) and
		(len(shorthand) > MAX_SHORTHAND_LENGTH)
	):
		errors.add("Shorthand is oversized (max length is {max_length})".format(
			max_length=MAX_SHORTHAND_LENGTH
		))


def check_title_starts_from_shorthand(item, errors):
	"""
	Checks if title starts from shorthand
	"""
	title = item.get("title")
	shorthand = item.get("shorhand")
	if (shorthand is None):
		return
	if not title.startswith(shorthand):
		errors.add("Title should begin with shorthand")


def check_isbn(item, errors):
	"""
	Checks ISBN for validity.
	Will accept both ISBN-10 and ISBN-13 formats
	"""
	isbn_list = item.get("isbn")
	if isbn_list is None:
		return
	for isbn in isbn_list:
		correct, error = utils.is_isbn_valid(isbn)
		if not correct:
			errors.add("Isbn isn't valid" + error)


def check_booktype(item, errors):
	"""
	Checks if booktype belongs to a valid list.
	Performs extra checks for field presence based on booktype
	"""
	VALID_BOOKTYPES = {
		"article",
		"book",
		"inproceedings",
		"mvbook",
		"mvreference",
		"periodical",
		"proceedings",
		"reference",
		"thesis",
		"unpublished",
	}
	#volumes tag should be present for these booktypes
	MULTIVOLUME_BOOKTYPES = {"mvbook", "mvreference"}
	UNPUBLISHED_NOTE_PREFIX = "Unpublished manuscript"

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
	if (booktype == "inproceedings"):
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

	if (booktype == "unpublished"):
		note = item.get("note")
		if note is None:
			errors.add("Field note expected for booktype {booktype}".format(
				booktype=booktype
			))
		else:
			if not note.startswith(UNPUBLISHED_NOTE_PREFIX):
				errors.add("Field note should start with \"{prefix}\" for booktype {booktype}".format(
					prefix=UNPUBLISHED_NOTE_PREFIX,
					booktype=booktype
				))


def check_commentator(item, errors):
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


def check_url_validity(item, errors):
	"""
	Checks url for validity
	"""
	url = item.get("url")
	item_id = item.get("id")
	if url is not None:
		for number, single_url in enumerate(url):
			if not utils.is_url_valid(single_url, item):
				errors.add("Field url with value [{single_url}] and number {number} is wrong".format(
					single_url=single_url,
					number=number
				))

			match = utils.SELF_SERVED_URL_REGEXP.match(single_url)
			if match:
				if (match.group("item_id") != item_id):
					errors.add("Wrong item_id specified in self-served url")
				else:
					single_filename, single_filesize = utils.get_file_info_from_url(single_url, item)
					metadata = utils.extract_metadata_from_file(single_filename)
					if (
						("keywords" not in metadata) or
						(const.META_HAS_OWNER not in metadata["keywords"])
					):
						errors.add("Owner specification expected for self-served url number {number}".format(
							number=number
						))


def check_url_accessibility(item, errors):
	"""
	Checks url for accessibility
	"""
	url = item.get("url")
	if url is not None:
		for number, single_url in enumerate(url):
			if not utils.is_url_accessible(single_url, item):
				errors.add("Field url with value [{single_url}] and number {number} is unaccessible".format(
					single_url=single_url,
					number=number
				))


def check_transcription_fields(item, errors):
	"""
	Checks if transcription file exists and
	can be served upon request
	"""
	item_id = item.get("id")
	TRANSLATION_FIELDS = ["transcription_url", "transcription_filename"]
	has_transcription = False
	for field in TRANSLATION_FIELDS:
		if item.has(field):
			has_transcription = True

	if not has_transcription:
		return

	for field in TRANSLATION_FIELDS:
		if not item.has(field):
			errors.add("Field {field} is require for transcriptions".format(
				field=field
			))
			return

	transcription_url = item.get("transcription_url")
	transcription_filename = item.get("transcription_filename")
	for single_url in transcription_url:
		match = utils.SELF_SERVED_TRANSCRIPTION_REGEXP.match(single_url)
		if not match:
			errors.add("Transcription url {single_url} doesn't match SELF_SERVED_TRANSCRIPTION_REGEXP".format(
				single_url=single_url
			))
			continue
		if item_id != match.group("item_id"):
			errors.add(
				"Trancscription url {single_url} isn't valid. "
				"Extracted id {extracted_id} doesn't match item_id {item_id}".format(
					single_url=single_url,
					extracted_id=match.group("item_id"),
					item_id=item_id
				)
			)

		if (int(match.group("transcription_index")) - 1) > len(transcription_url):
			errors.add("Transcription index is too large in {single_url}".format(
				single_url=single_url
			))

	for single_filename in transcription_filename:
		abspath = os.path.join(config.parser.markdown_dir, single_filename)
		if not os.path.isfile(abspath):
			errors.add("Transcription file [{abspath}] is not accessible".format(
				abspath=abspath
			))
		if not utils.isfile_case_sensitive(abspath):
			errors.add("Transcription file [{abspath}] is not accessible in case-sensitive mode".format(
				abspath=abspath
			))


def check_location(item, errors):
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


def check_volume(item, errors):
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


def check_series(item, errors):
	"""
	Checks series and number parameters for validity
	"""
	#perdiodical booktypes may also have number field,
	#through they aren't serial entries
	PERIODICAL_BOOKTYPES = {"periodical"}
	booktype = item.get("booktype")
	if booktype in PERIODICAL_BOOKTYPES:
		return
	SERIAL_FIELDS = ["series", "number"]
	is_serial = False
	for field in SERIAL_FIELDS:
		if item.get(field) is not None:
			is_serial = True
			break
	if not is_serial:
		return
	for field in SERIAL_FIELDS:
		if item.get(field) is None:
			errors.add("Field {field} expected for serial books".format(
				field=field
			))


def check_edition(item, errors):
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


def check_keywords(item, errors):
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
		errors.add("Keyword [useless] can't be combined with other keywprds")


def check_filename(item, errors):
	"""
	Checks filename against various tests
	"""
	MULTIENTRY_BOOKTYPES = {"proceedings", "inproceedings"}
	booktype = item.get("booktype")
	filename = item.get("filename")
	keywords = set(item.get("keywords") or {})
	if booktype in MULTIENTRY_BOOKTYPES:
		return
	if filename is None:
		if ("not digitized" not in keywords):
			errors.add("Keyword [not digitized] should be specified")
		return

	for single_filename in filename:
		#filename starts with slash - trimming it
		abspath = os.path.join(config.www.elibrary_dir, single_filename[1:])
		if not os.path.isfile(abspath):
			errors.add("File [{abspath}] is not accessible".format(
				abspath=abspath
			))
		if not utils.isfile_case_sensitive(abspath):
			errors.add("File [{abspath}] is not accessible in case-sensitive mode".format(
				abspath=abspath
			))
		metadata = utils.extract_metadata_from_file(single_filename)

		#validating optional author, edition, tome
		#in case when item specifies value, but filename does not
		optional_meta_fields = [
			"author",
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
					filename=single_filename
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
					"Item is not searchable by {search_key}.\n"
					"    Item has: {item_value}\n"
					"    Search has: {search_value}".format(
					search_key=search_key,
					item_value=item.get(search_key),
					search_value=metadata[search_key]
				))


def check_source_file(item, errors):
	"""
	Checks if source file language matches item language
	"""
	MULTILANG_FILES = {
		"proceedings-spb.bib",
		"proceedings-rothenfelser.bib",
		"_problems.bib"
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


@opster.command()
def main(
	make_extra_checks=("", False, "Add some extra checks"),
	ignore_missing_ids=("", False, "Update validation data even when some ids were lost")
):
	"""
	Validates bibliography over a bunch of rules
	"""
	logging.info("Going to process {0} items".format(len(items)))

	error_storage = collections.OrderedDict()
	#don't validate filename for the given entrytypes
	for item in items:
		errors = set()
		try:
			check_id(item, errors)
			check_parser_generated_fields(item, errors)
			check_obligatory_fields(item, errors)
			check_translation_fields(item, errors)
			check_transcription_fields(item, errors)
			check_shorthand(item, errors)
			check_isbn(item, errors)
			check_booktype(item, errors)
			check_commentator(item, errors)
			check_url_validity(item, errors)
			check_volume(item, errors)
			check_series(item, errors)
			check_keywords(item, errors)
			check_filename(item, errors)
			check_source_file(item, errors)
			if make_extra_checks:
				check_title_starts_from_shorthand(item, errors)
				check_url_accessibility(item, errors)
		except Exception as ex:
			logging.exception("Exception while validating {item_id} ({source}): {ex}".format(
				item_id=item.id(),
				source=item.source(),
				ex=ex
			))
			continue

		if (len(errors) > 0):
			error_storage[item] = errors
			logging.debug("Errors for {item_id} ({source}):".format(
				item_id=item.id(),
				source=item.source()
			))
			for error in errors:
				logging.debug("    " + error)

	update_validation_data(ignore_missing_ids)
	logging.warning("Found {number} erroneous entries".format(
		number=len(error_storage)
	))


if __name__ == "__main__":
	main.command()
