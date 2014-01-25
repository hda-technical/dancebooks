#!/usr/bin/env python3
#coding: utf-8
import optparse
import os.path
import sys

import constants
import index
import parser
import utils

MAX_OUTPUT_COUNT = 100

items = parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.create_index(items, constants.INDEX_KEYS)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items, constants.INDEX_KEYS)

languages = sorted(item_index["langid"].keys())

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
filenames = set(map(file_modifier, item_index["filename"].keys()))

items_filter = lambda item: item.get("filename") is None
files_filter = lambda file_: file_ not in filenames

excluded_folders = set(["Ancillary sources (not in bibliography)", "Leaflets (not in bibliography)"])
files = utils.files_in_folder(options.root, "*.pdf", excludes=excluded_folders)

files = list(filter(files_filter, files))
items = list(filter(items_filter, items))

print("Going to process {0} items".format(len(items)))
print("Going to process {0} files".format(len(files)))
output_count = 0
output_dict = dict()
for file_ in files:
	relpath = "/" + os.path.relpath(file_, options.root)
		
	metadata = utils.extract_metadata_from_file(file_)	
	item_search = utils.create_search_from_metadata(metadata)
	
	found_items = list(filter(item_search, items))
	found_count = len(found_items)
	if found_count == 0:
		print("Nothing found for file '{relpath}'".format(
			relpath=relpath,
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
		relpath=" {0} ".format(constants.GENERAL_SEP).join(sorted(paths))
	))

sort_key = lambda item: item.source()
if len(items) < MAX_OUTPUT_COUNT:
	for item in sorted(items, key=sort_key):
		print("Item isn't digitized: {id} ({source})".format(
			id=item.id(),
			source=item.source()))
