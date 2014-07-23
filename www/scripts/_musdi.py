#!/usr/bin/env python3
#coding: utf-8
import os.path
import re
import sys
import subprocess

import opster

import index
import bib_parser
import utils

items = bib_parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.Index(items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

MUSDI_SCHEMA = "http"
MUSDI_HOST = "hdl.loc.gov"
MUSDI_PATH_PREFIX = "/loc.music/musdi"
MUSDI_PREFIX = MUSDI_SCHEMA + "://" + MUSDI_HOST + MUSDI_PATH_PREFIX
MUSDI_REGEXP = re.compile(re.escape(MUSDI_PREFIX) + "\.(\d+)")
WRONG_HANDLE_STRING = "<title>Handle Problem Report (Library of Congress)</title>"

@opster.command()
def main():
	numbers = set()
	for item in items:
		url = item.get("url") or ""
		for signle_url in url:
			match = MUSDI_REGEXP.match(signle_url)
			if match:
				number = match.group(1)
				numbers.add(int(number))
	
	max_number = max(numbers)
	expected_numbers = set(range(1, int(max_number)))
	print("Max number is {0}".format(max_number))
	
	for number in sorted(expected_numbers - numbers):
		code, reason, data = utils.request(
			MUSDI_SCHEMA, 
			MUSDI_HOST, 
			"{0}.{1:03d}".format(MUSDI_PATH_PREFIX, number),
			"GET"
		)
		if WRONG_HANDLE_STRING not in data:
			print("{0}.{1:03d}".format(MUSDI_PREFIX, number))
	
if __name__ == "__main__":
	main.command()
