#!/usr/bin/env python3
# coding: utf-8
import os.path

import opster

from config import config
import main
import bib_parser
import utils

client = main.flask_app.test_client()

@utils.profile()
def all_profile():
	client.get(config.www.app_prefix + "/all.html")
	

@utils.profile
def parsing_profile():
	bib_parser.BibParser().parse_folder(os.path.abspath("../bib"))


@utils.profile
def search_profile():
	client.get(config.www.app_prefix + "/index.html?"
		"title=Dance&"
		"author=Wil&"
		"year_from=1000&"
		"year_to=2000")


@opster.command()
def main():
	"""
	Profiles some parts of a www-module
	"""
	all_profile()
	#parsing_profile()
	#search_profile()


if __name__ == "__main__":
	main()
