#!/usr/bin/env python
#coding: utf-8
import optparse
import os.path
import re
import sys

import constants
import parser
import search
import utils

MAX_OUTPUT_COUNT = 100

bib_parser = parser.BibParser()
items = bib_parser.parse_folder(os.path.abspath("../bib"))
languages = sorted(bib_parser.get_scanned_fields("langid"))

language_map = {
	"au": "english",
	"cz": "czech",
	"de": "german",
	"dk": "danish",
	"en": "english",
	"es": "spanish",
	"fr": "french",
	"ie": "english",
	"it": "italian",
	"pl": "polish",
	"pt": "portuguese",
	"ru": "russian",
	"sc": "english",
	"us": "english"
}

usage = "Usage: %prog [options]"

opt_parser = optparse.OptionParser(usage=usage)
opt_parser.add_option("-r", "--root", dest="root", help="E-library root FOLDER", metavar="FOLDER")
(options, args) = opt_parser.parse_args()

if options.root is None:
	print("Root folder must be specified")
	sys.exit(1)

options.root = os.path.abspath(options.root)

#filename in database is relative, but begins from /
file_modifier = lambda file_, root=options.root: os.path.join(root, file_[1:])
filenames = set(map(file_modifier, bib_parser.get_scanned_fields("filename")))

items_filter = lambda item: item.get("filename") is None
files_filter = lambda file_: file_ not in filenames

excluded_folders = set(["Ancillary sources (not in bibliography)", "Leaflets (not in bibliography)"])
files = utils.files_in_folder(options.root, "*.pdf", excludes=excluded_folders)

files = list(filter(files_filter, files))
items = list(filter(items_filter, items))

#any of [incomplete, commentary, translation, facsimile]
meta_pattern = r"(?:(?:incomplete)|(?:commentary)|(?:translation)|(?:facsimile)|(?:transcription))"
file_pattern = (
	#year: digits can be replaced by dashes
	r"\[(?P<year>[\d-]+), "
	#lang: two-letter code
	r"(?P<lang>[a-z]{2})\] "
	#author: optional, can contain 
	#   spaces (Thomas Wilson),
	#   dots (N. Malpied), 
	#   commas (Louis Pécour, Jacque Dezais)	
	#(question mark at the end makes regexp non-greedy)
	r"(?:(?P<author>[\w\s\.,'\-]+?) - )?"
	#title: sequence of words, digits, spaces, punctuation
	#(question mark at the end makes regexp non-greedy)
	r"(?P<title>[\w\d\s',\.\-–—&«»‹›„”№\(\)]+?)"
	#metadata: optional sequence of predefined values
	#   tome (, tome 2)
	#   edition (, édition 10)
	#	comma-separated list of meta_pattern in parentheses
	#   (something copy) — for books with multiple different copies known 
	r"(?:"
		r"(?:, tome \d+)|"
		r"(?:, édition \d+)|"
		r"(?: \(" + meta_pattern + r"(?:, " + meta_pattern + r")*\))|"
		r"(?: \([\w]+ copy\))"
	r")*"
	#extension: .pdf
	r"\.pdf"
)
file_re = re.compile(file_pattern)

print("Going to process {0} items".format(len(items)))
print("Going to process {0} files".format(len(files)))
output_count = 0
output_dict = dict()
for file_ in files:
	basename = os.path.basename(file_)
	relpath = "/" + os.path.relpath(file_, options.root)
	match = file_re.match(basename)
	if not match:
		print("File {0} didn't match the regexp".format(relpath))
		sys.exit(1)
		
	year = match.group("year")
	lang = language_map[match.group("lang")]
	author = match.group("author")
	title = match.group("title")
	
	year_from = year.replace("-", "0")
	year_to = year.replace("-", "9")
	title_regexp = re.compile("^" + re.escape(title))
	
	search_for_lang = search.search_for_string_exact("langid", lang)
	search_for_year = search.search_for_year(year_from, year_to)
	search_for_title = search.search_for_string_regexp("title", title_regexp)
	search_for_author = search.search_for_iterable_set(
		"author", 
		set(utils.strip_split_list(author, constants.OUTPUT_LISTSEP))
	) if author else search.search_true()
	
	searches = [
		search_for_lang,
		search_for_year,
		search_for_title,
		search_for_author
	]
	
	found_items = list(filter(search.and_(searches), items))
	found_count = len(found_items)
	if found_count == 0:
		print("Nothing found for file '{relpath} ({year}, {lang}, {author}, {title})'".format(
			relpath=relpath,
			year=year,
			lang=lang,
			author=author,
			title=title
		))
	elif found_count == 1:
		item = found_items[0]
		if item in output_dict:
			output_dict[item].add(relpath)
		else:
			output_dict[item] = set([relpath])
	else:
		source_getter = lambda item: item.source()
		print("Found multiple items for '{relpath}':\n\t{sources}".format(
			sources=list(map(source_getter, found_items)),
			relpath=relpath
		))
	
	output_count += 1
	if output_count >= MAX_OUTPUT_COUNT:
		print("Reached maxcount. Exiting")
		break

sort_key = lambda pair: pair[0].source()		
for item, paths in sorted(output_dict.items(), key=sort_key):
	print("Filename for {id} ({source}):".format(
		id=item.id(),
		source=item.source(),
	))
	print("filename = {{{relpath}}}".format(
		relpath=" {0} ".format(constants.LISTSEP).join(sorted(paths))
	))