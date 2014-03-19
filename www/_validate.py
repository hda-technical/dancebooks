#!/usr/bin/env python3
import os.path
import re
import sys

import opster

import const
from config import config
import index
import parser
import utils

items = parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.Index(items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

languages = sorted(item_index["langid"].keys())

@opster.command()
def main(
	root=("r", "", "E-library root"),
	check_head=("", False, "Perform HTTP HEAD request to url values")
):
	"""
	Validates bibliography over a bunch of rules
	"""	
	if (len(root) == 0) or (not os.path.isdir(root)):
		print("Root folder is inaccessible")
		sys.exit(1)
		
	root = os.path.abspath(root)
	print("Going to process {0} items".format(len(items)))

	SOURCE_REGEXP = re.compile("(?P<basename>[_\-\w\.]+).bib:\d+")
	MULTILANG_FILES = {"proceedings-spb", "proceedings-rothenfelser", "_missing", "_problems"}
	VALID_BOOKTYPES = {
		"book",
		"mvbook",
		"inproceedings",
		"proceedings",
		"reference",
		"mvreference",
		"periodical",
		"unpublished",
		"thesis",
		"article"
	}
	NON_MULTIVOLUME_BOOKTYPES = {"article", "periodical"}
	MULTIVOLUME_BOOKTYPES = {"mvbook", "mvreference"}
	
	#don't validate filename for the given entrytypes
	MULTIENTRY_BOOKTYPES = {"proceedings", "inproceedings"}
	SHORTHAND_LIMIT = 25

	#magic constant
	LAST_ORIGINAL_YEAR = 1937
	NON_ORIGINAL_KEYWORDS = {"reissue", "research"}
	RESEARCH_BOOKTYPES = {"book", "mvbook"}
	
	UNPUBLISHED_NOTE_PREFIX = "Unpublished manuscript"

	erroneous_entries = 0
	errors_count = 0
	for item in items:
		errors = []
		#datamodel validation
		author = item.get("author")
		booktype = item.get("booktype")
		booktitle = item.get("booktitle")
		commentator = item.get("commentator")
		edition = item.get("edition")
		filename = item.get("filename")
		id = item.get("id")
		isbn = item.get("isbn")
		institution = item.get("institution")
		journaltitle = item.get("journaltitle")
		keywords = set(item.get("keywords")) if item.get("keywords") else None
		langid = item.get("langid")
		location = item.get("location")
		note = item.get("note")
		number = item.get("number")
		origlanguage = item.get("origlanguage")
		publisher = item.get("publisher")
		series = item.get("series")
		shorthand = item.get("shorthand")
		source = item.get("source")
		title = item.get("title")
		translator = item.get("translator")
		type = item.get("type")
		url = item.get("url")
		volume = item.get("volume")
		volumes = item.get("volumes")
		year = item.get("year")
		year_from = item.get("year_from")
		year_to = item.get("year_to")
		year_circa = item.get("year_circa")
		added_on = item.get("added_on")
		
		match = SOURCE_REGEXP.match(source)
		if not match:
			raise RuntimeError("Failed to parse 'source' for item ({id})".format(
				id=id
			))
		source_basename = match.group("basename")
		
		parser_obligatory = [id, booktype, source, year_from, year_to, year_circa]
		none_checker = lambda obj: obj is not None
		if not all(map(none_checker, parser_obligatory)):
			raise RuntimeError("Parser hasn't generated all required auxiliary fields {fields}".format(
				fields=parser_obligatory
			))
		
		general_obligatory = [langid, year, title, added_on]
		if not all(general_obligatory):
			errors.append("Item doesn't define one of [langid, year, title]")
		
		translation_obligatory = [origlanguage, translator]
		if not utils.all_or_none(translation_obligatory):
			errors.append("All of [origlanguage, translator] must be present for translations")
		
		series_obligatory = [series, number]
		if not utils.all_or_none(series_obligatory):
			errors.append("All of [series, number] must be present for serial books")
		
		if not any([author, shorthand]):
			errors.append("'author' or 'shorthand' must be present")
		
		if (publisher is not None) and (location is None):
			errors.append("If publisher present, location must be present")
		
		#booktype validation
		booktype = booktype.lower()
		if booktype not in VALID_BOOKTYPES:
			errors.append("Invalid booktype ({booktype})".format(
				booktype=booktype
			))
		
		if (booktype not in NON_MULTIVOLUME_BOOKTYPES):
			if (volume is not None) and (volumes is None):
				errors.append("If volume present, volumes must be present")
		
		if (booktype in MULTIVOLUME_BOOKTYPES):
			if volumes is None:
				errors.append("volumes must be present for @{0}".format(booktype))
		
		if (booktype == "article"):
			if journaltitle is None:
				errors.append("journaltitle must be present for @article")
		
		if (booktype == "inproceedings"):
			if booktitle is None:
				errors.append("bootitle must be present for @inprocessing")
		
		if (booktype == "thesis"):
			if url is None:
				errors.append("url must be present for @thesis")
			if type is None:
				errors.append("type must be present for @thesis")
			if institution is None:
				errors.append("institution must be present for @thesis")
		
		#data validation
		#author validation empty
		
		#booktitle validation empty
		
		#commentator
		if commentator is not None:
			if (keywords is None) or ("commentary" not in keywords):
				errors.append("Keywords should contain 'commentary' when commentator specified")
		
		#filename validation
		if edition is not None:
			#edition should be greater than 1
			if edition <= 1:
				errors.append("Wrong edition {edition}".format(
					edition=edition
				))
		
		if volume is not None:
			#volume should be positive integer
			if volume <= 0:
				errors.append("Wrong volume {volume}".format(
					volume=volume
				))
			if volumes is not None:
				if volume > volumes:
					errors.append("Volume ({volume}) can't be greater than volumes ({volumes})".format(
						volume=volume,
						volumes=volumes
					))
		
		#filename validation
		if (filename is not None) and (booktype not in MULTIENTRY_BOOKTYPES):
			for filename_ in filename:
				#filename starts with "/" which will mix os.path.join up
				abspath = os.path.join(root, filename_[1:])
				#each filename should be accessible
				if not os.path.isfile(abspath):
					errors.append("File {filename_} is not accessible".format(
						filename_=filename_
					))
					
				#item should be searchable by its filename metadata
				metadata = utils.extract_metadata_from_file(filename_)
				
				#validating optional author, edition, tome
				#in case when item specifies value, but filename doesn't
				if not utils.all_or_none([metadata.get("author", None), author]):
					errors.append("File {filename_} and entry have different author specifications".format(
						filename_=filename_
					))
					
				if not utils.all_or_none([metadata.get("edition", None), edition]):
					errors.append("File {filename_} and entry have different edition specifications".format(
						filename_=filename_
					))
					
				if not utils.all_or_none([metadata.get("tome", None), any([volume, volumes])]):
					errors.append("File {filename_} and entry have different volume specifications".format(
						filename_=filename_
					))
				
				meta_keywords = metadata.get("keywords", None)
				if meta_keywords is not None:
					if ("incomplete" not in meta_keywords) and (source_basename == "_problems"):
						errors.append("Incomplete books should be stored in _problems.bib")
					meta_keywords.discard("incomplete")
					
					if len(meta_keywords) > 0:
						if keywords is None:
							errors.append("No keywords specified (should be {meta_keywords}".format(
								meta_keywords=meta_keywords
							))
						elif not keywords >= meta_keywords:
							errors.append("Item keywords {keywords} do not match metadata keywords {meta_keywords}".format(
								keywords=keywords,
								meta_keywords=meta_keywords
							))
				
				search_ = utils.create_search_from_metadata(config, metadata)
				if not search_(item):
					errors.append("File {filename_} is not searchable by extracted params".format(
						filename_=filename_
					))
		
		#id validation empty
		if len(item_index["id"][id]) != 1:
			errors.append("Id is not unique")
			
		#isbn validation
		if isbn is not None:
			for isbn_ in isbn:
				correct, msg = utils.is_isbn_valid(isbn_)
				if not correct:
					errors.append("ISBN {isbn_} isn't valid: {msg}".format(
						isbn_=isbn_,
						msg=msg
					))
		
		#institution validation empty
		
		#journaltitle validation empty
		
		#keywords validation
		#if item was issued after LAST_ORIGINAL_YEAR, it should define keywords
		if True:
			if (year_from > LAST_ORIGINAL_YEAR) and (booktype in RESEARCH_BOOKTYPES):
				if (keywords is None) or (len(keywords & NON_ORIGINAL_KEYWORDS) == 0):
					errors.append("Item was issued after {last_year}, but keywords don't define any of {keywords}".format(
						last_year=LAST_ORIGINAL_YEAR,
						keywords=NON_ORIGINAL_KEYWORDS
					))
			if (keywords is not None):
				if ("translation" in keywords) and not all([translator, origlanguage]):
					errors.append("When 'translation' keyword specified, translator and origlanguage should be present")
				if ("commentary" in keywords) and not commentator:
					errors.append("When 'commentary' keyword specified, commentator should be present")
				
		#langid validation
		if source_basename not in MULTILANG_FILES:
			source_lang = const.LONG_LANG_MAP[source_basename]
			#item language should match source language
			if langid != source_lang:
				errors.append("Source language ({source_lang}) doesn't match item language ({langid})".format(
					source_lang=source_lang,
					langid=langid
				))
		#location validation empty
		
		#note validation
		note_unpublished = (note is not None) and (note.startswith(UNPUBLISHED_NOTE_PREFIX))
		booktype_unpublished = (booktype == "unpublished")
		if not utils.all_or_none([note_unpublished, booktype_unpublished]):
			errors.append("For unpublished books, note should begin with [{note_prefix}] and booktype should be {booktype}".format(
				booktype="unpublished",
				note_prefix=UNPUBLISHED_NOTE_PREFIX
			))
		
		
		#number validation empty
		
		#origlanguage validation empty
		
		#publisher validation empty
		
		#series validation empty
		
		#shorthand validation empty
		if shorthand is not None:
			length = len(shorthand)
			if length > SHORTHAND_LIMIT:
				errors.append("The length of shorthand ({length}) should not exceed limit ({limit})".format(
					length=length,
					limit=SHORTHAND_LIMIT
				))
			if (author is None) and (not title.startswith(shorthand)):
				errors.append("Title ({title}) should begin with from shorthand ({shorthand})".format(
					title=title,
					shorthand=shorthand
				))
		
		#source validation empty
		
		#title validation empty
		if title is not None:
			if ("  " in title):
				errors.append("Consecutive spaces in title")
			if ("\t" in title):
				errors.append("Tabs in title")
			if title.startswith(" ") or title.endswith(" "):
				errors.append("Title isn't stripped")
		
		#translator validation
		if translator is not None:
			if (keywords is None) or ("translation" not in keywords):
				errors.append("Keywords should contain 'translation' when 'translator' field specified")
				
		#type validation empty
		
		#url validation empty
		if url is not None:
			correct, msg = utils.is_url_valid(url, check_head)
			if not correct:
				errors.append("URL {url} isn't valid: {msg}".format(
					url=url,
					msg=msg
				))
			
		#volume validation empty
		
		#volumes validation empty
		
		#year validation empty
		
		#printing errors
		if len(errors) > 0:
			erroneous_entries += 1
			errors_count += len(errors)
			print("Errors for {id} ({source})".format(
				id=id,
				source=source
			))
			for error in errors:
				print("    " + error)
		
	print("Found {entries} erroneous entries ({errors} errors)".format(
		entries=erroneous_entries,
		errors=errors_count
	))

	
if __name__ == "__main__":
	main.command()
