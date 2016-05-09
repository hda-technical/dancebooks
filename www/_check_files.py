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
	item.finalize_item_set(item_index)
item_index.update(items)

items_filter = lambda item: item.get("filename") is None
items = list(filter(items_filter, items))

languages = sorted(item_index["langid"].keys())

@opster.command()
def main():
	if not os.path.isdir(config.www.elibrary_dir):
		print("root folder '{elibrary_dir}' is inaccessible".format(
			elibrary_dir=config.www.elibrary_dir
		))
		sys.exit(1)

	#filename in database is relative, but begins from /
	file_modifier = lambda file_, root=config.www.elibrary_dir: os.path.join(root, file_[1:])
	filenames = set(map(file_modifier, item_index["filename"].keys()))
	
	files = utils.files_in_folder(config.www.elibrary_dir, "*.pdf", excludes=EXCLUDED_FOLDERS)
	
	files_filter = lambda file_: file_ not in filenames
	files = list(filter(files_filter, files))
	
	for file in files:
		print(file)

if __name__ == "__main__":
	main.command()
