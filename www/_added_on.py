#!/usr/bin/env python3
#coding: utf-8
import os.path
import re
import subprocess

import opster

from config import config
import index
import bib_parser

items = bib_parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.Index(items)
for item in items:
	item.finalize_item_set(item_index)
item_index.update(items)

items_filter = lambda item: item.get("filename") is None
items = list(filter(items_filter, items))

BLAME_REGEXP = re.compile(
	r"^[\^0-9a-z]+\s+"
	r"[^\s]*?\s+"
	r"\([A-Za-z\-\s\\]*?\s+"
	r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
	r"[\d:]+\s+"
	r"[+\d]+\s+"
	r"\d+\)\s+"
	r"(?P<id>[a-z_\d]+),\s*$"
)

def process_file(path):
	data = subprocess.check_output(
		"git blame -f {path} | grep -P '\t[a-z\_\d]+,'".format(
			path=path
		),
		shell=True)\
		.decode()

	for line in data.split("\n"):
		#ignoring empty lines
		if not line:
			continue

		match = BLAME_REGEXP.search(line)
		if not match:
			print(line)
			raise ValueError("Received string doesn't match BLAME_REGEXP")

		date = match.group("date")
		id = match.group("id")

		#ignoring items with added_on already set
		item = list(item_index["id"][id])[0]
		item_added_on = item.added_on()
		if item_added_on is not None:
			if date != item_added_on:
				print("Item {id} ({source}) has incorrect added_on {added_on}, but should be {correct_added_on}".format(
					id=item.id(),
					source=item.source(),
					added_on=item.added_on(),
					correct_added_on=date
				))
				print("added_on = {{{date}}}".format(date=date))
			continue

		print("Item {id} ({source}) was added on {date}".format(
			id=item.id(),
			source=item.source(),
			date=date
		))
		print("added_on = {{{date}}}".format(date=date))


@opster.command()
def main():
	files = [
		os.path.join(config.parser.bibdata_dir, file)
		for file in os.listdir(config.parser.bibdata_dir)
		if file.endswith(".bib")
	]
	for file in files:
		process_file(file)

if __name__ == "__main__":
	main.command()
