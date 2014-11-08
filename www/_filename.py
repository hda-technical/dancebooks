#!/usr/bin/env python3
#coding: utf-8
import os.path
import sys

import opster

from config import config
import index
import bib_parser
import utils

MAX_OUTPUT_COUNT = 100
EXCLUDED_FOLDERS = {
	"Ancillary sources (not in bibliography)", 
	"Leaflets (not in bibliography)"
}

items = bib_parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.Index(items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

items_filter = lambda item: item.get("filename") is None
items = list(filter(items_filter, items))

languages = sorted(item_index["langid"].keys())

@opster.command()
def main(
	max_count=("c", 100, "Maximum count of filenames to display")
):
	if not os.path.isdir(config.www.elibrary_root):
		print("root folder '{elibrary_root}' is inaccessible".format(
			elibrary_root=config.www.elibrary_root
		))
		sys.exit(1)

	#filename in database is relative, but begins from /
	file_modifier = lambda file_, root=config.www.elibrary_root: os.path.join(root, file_[1:])
	filenames = set(map(file_modifier, item_index["filename"].keys()))
	
	files = utils.files_in_folder(config.www.elibrary_root, "*.pdf", excludes=EXCLUDED_FOLDERS)
	
	files_filter = lambda file_: file_ not in filenames
	files = list(filter(files_filter, files))
	
	print("Going to process {0} items".format(len(items)))
	print("Going to process {0} files".format(len(files)))
	output_count = 0
	output_dict = dict()
	for file_ in files:
		relpath = "/" + os.path.relpath(file_, config.www.elibrary_root)
			
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
		if output_count >= max_count:
			print("Reached maxcount. Exiting")
			break

	sort_key = lambda pair: pair[0].source()		
	for item, paths in sorted(output_dict.items(), key=sort_key):
		print("Filename for {id} ({source}):".format(
			id=item.id(),
			source=item.source(),
		))
		print("filename = {{{relpath}}}".format(
			relpath=" {0} ".format(config.parser.list_sep).join(sorted(paths))
		))

	sort_key = lambda item: item.source()
	if len(items) < max_count:
		for item in sorted(items, key=sort_key):
			print("Item isn't digitized: {id} ({source})".format(
				id=item.id(),
				source=item.source()))


if __name__ == "__main__":
	main.command()
