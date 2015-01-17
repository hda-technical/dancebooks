#!/usr/bin/env python
#coding: utf-8
import fnmatch
import os
import sys

import opster

import utils

@opster.command()
def main(
	folder=("d", "", "Folder with transcription files"),
	page=("p", "", "Output github wiki page (in markdown)"),
	url_prefix=("u", "", "URL prefix of the filenames")
):
	if (len(folder) == 0) or (not os.path.isdir(folder)):
		print("Folder should be specified")
		sys.exit(1)

	if len(page) == 0:
		print("Github page should be specified")
		sys.exit(1)

	with open(page, "w") as wiki_file:
		for tr in os.listdir(folder):
			if not fnmatch.fnmatch(tr, "*.md"):
				continue

			folder_basename = os.path.basename(folder)

			pretty_name, ext =  os.path.splitext(os.path.basename(tr.replace("_", " ")))
			item_string = "* [{link}]({prefix}{name})\n".format(
				link = pretty_name,
				prefix = url_prefix,
				name = tr)
			wiki_file.write(item_string)

if __name__ == "__main__":
	main.command()
