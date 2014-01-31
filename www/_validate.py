#!/usr/bin/env python3
import optparse
import os.path
import re
import sys

import config
import index
import parser
import utils

MAX_OUTPUT_COUNT = 100

cfg = config.Config("../configs/www.cfg")

items = parser.BibParser(cfg).parse_folder(os.path.abspath("../bib"))
item_index = index.Index(cfg, items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

languages = sorted(item_index["langid"].keys())

usage = "Usage: %prog [options]"

opt_parser = optparse.OptionParser(usage=usage)
opt_parser.add_option("-r", "--root", dest="root", help="E-library root FOLDER", metavar="FOLDER")
(options, args) = opt_parser.parse_args()

if options.root is None:
	print("Root folder must be specified")
	sys.exit(1)

options.root = os.path.abspath(options.root)

print("Going to process {0} items".format(len(items)))

SOURCE_REGEXP = re.compile("(?P<basename>[_\-\w\.]+).bib:\d+")
MULTILANG_FILES = set(["proceedings-spb", "proceedings-rothenfelser", "_missing", "_problems"])
VALID_BOOKTYPES = set([
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
])
NON_MULTIVOLUME_BOOKTYPES = set(["article", "periodical"])
MULTIVOLUME_BOOKTYPES = set(["mvbook", "mvreference"])
SHORTHAND_LIMIT = 25

#country as adjective mapped to langid
LONG_LANG_MAP = {
	"american": "english",
	"australian": "english",
	"austrian": "german",
	"canadian": "english",
	"czech": "czech",
	"danish": "danish",
	"english": "english",
	"french": "french",
	"german": "german",
	"italian": "italian",
	"mexican": "spanish",
	"polish": "polish",
	"portuguese": "portuguese",
	"russian": "russian",
	"spanish": "spanish"

}
erroneous_entries = 0
for item in items:
	errors = []
	#datamodel validation
	author = item.get("author")
	booktype = item.get("booktype")
	booktitle = item.get("booktitle")
	edition = item.get("edition")
	filename = item.get("filename")
	id = item.get("id")
	isbn = item.get("isbn")
	institution = item.get("institution")
	journaltitle = item.get("journaltitle")
	langid = item.get("langid")
	location = item.get("location")
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
	
	match = SOURCE_REGEXP.match(source)
	if not match:
		raise RuntimeError("Failed to parse 'source' for item ({id})".format(
			id=id
		))
	source_basename = match.group("basename")
	
	parser_obligatory = [id, booktype, source]
	if not all(parser_obligatory):
		raise RuntimeError("Parser hasn't generated all required auxiliary fields ([id, booktype, source])")
	
	general_obligatory = [langid, year, title]
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
	
	#booktype validated above
	
	#booktitle validation empty
	
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
	if filename is not None:
		for filename_ in filename:
			#filename starts with "/" which will mix os.path.join up
			abspath = os.path.join(options.root, filename_[1:])
			#each filename should be accessible
			if not os.path.isfile(abspath):
				errors.append("File {filename_} is not accessible".format(
					filename_=filename_
				))
				
			#item should be searchable by its filename metadata
			metadata = utils.extract_metadata_from_file(filename_)
			
			#validating optional author, edition, tome
			#in case when item specifies value, but filename doesn't
			if (metadata.get("author", None) is not None) and (author is None):
				errors.append("File {filename_} specifies author, but entry doesn't".format(
					filename_=filename_
				))
				
			if (metadata.get("edition", None) is not None) and (edition is None):
				errors.append("File {filename_} specifies edition, but entry doesn't".format(
					filename_=filename_
				))
				
			if (metadata.get("tome", None) is not None) and (volumes is None) and (volume is None):
				errors.append("File {filename_} specifies volume, but entry doesn't".format(
					filename_=filename_
				))
			
			keywords = metadata.get("keywords", None)
			if source_basename == "_problems" and keywords is not None:
				if "incomplete" not in keywords:
					errors.append("Incomplete books should be stored in _problems.bib")
			
			search_ = utils.create_search_from_metadata(cfg, metadata)
			if not search_(item):
				errors.append("File {filename_} is not searchable by extracted params".format(
					filename_=filename_
				))
	
	#id validation empty
	
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
	
	#langid validation
	if source_basename not in MULTILANG_FILES:
		source_lang = LONG_LANG_MAP[source_basename]
		#item language should match source language
		if langid != source_lang:
			errors.append("Source language ({source_lang}) doesn't match item language ({langid})".format(
				source_lang=source_lang,
				langid=langid
			))
	#location validation empty
	
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
	
	#translator validation empty
	
	#type validation empty
	
	#url validation empty
	if url is not None:
		correct, msg = utils.is_url_valid(url)
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
		print("Errors for {id} ({source})".format(
			id=id,
			source=source
		))
		for error in errors:
			print("    " + error)
	
print("Found {count} erroneous entries".format(
	count=erroneous_entries
))
