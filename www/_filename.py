#!/usr/bin/env python
#coding: utf-8
import optparse
import os.path
import sys

import parser
import utils

bib_parser = parser.BibParser()
items = bib_parser.parse_folder(os.path.abspath("../bib"))
languages = sorted(bib_parser.get_scanned_fields("langid"))
filenames = bib_parser.get_scanned_fields("filename")

items_filter = lambda item: item.get("filename") is None
files_filter = lambda file_: file_ not in filenames

language_map = {
	"czech": ["cz"],
	"danish": ["dk"],
	"english": ["en", "us", "sc", "ie"],
	"french": ["fr"],
	"german": ["de"],
	"italian": ["it"],
	"polish": ["pl"],
	"portuguese": ["pt"],
	"russian": ["ru"],
	"spanish": ["es"]
}

usage = "Usage: %prog [options]"

opt_parser = optparse.OptionParser(usage=usage)
opt_parser.add_option("-r", "--root", dest="root", help="E-library root FOLDER", metavar="FOLDER")
(options, args) = opt_parser.parse_args()

if options.root is None:
	print("Root folder must be specified")
	sys.exit(1)

options.root = os.path.abspath(options.root)

files = utils.files_in_folder(options.root, "*.py")

files = list(filter(files_filter, files))
items = list(filter(items_filter, items))

print(len(files))
print(len(items))

