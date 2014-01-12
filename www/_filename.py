#!/usr/bin/env python
# coding: utf-8
import os.path
import glob

import parser

bib_parser = parser.BibParser()
items = bib_parser.parse_folder(os.path.abspath("../bib"))
languages = sorted(bib_parser.get_scanned_fields("langid"))

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

options.root = os.path.abspath(options.root)

print(options.root)