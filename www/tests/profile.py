#!/usr/bin/env python
# coding: utf-8

import cProfile
import io
import os.path
import pstats

from main import APP_PREFIX
from main import app, parser_options
from parser import BibParser

client = app.test_client()

def all_profile():
	profiler = cProfile.Profile()
	profiler.enable()

	client.get(APP_PREFIX + "/all.html")
	
	profiler.disable()
	string_io = io.StringIO()
	stats = pstats.Stats(profiler, stream=string_io).sort_stats("time")
	stats.print_stats()
	print(string_io.getvalue())


def parsing_profile():
	parser = BibParser(parser_options)
	
	profiler = cProfile.Profile()
	profiler.enable()

	parser.parse_folder(os.path.abspath("../bib"))

	profiler.disable()
	string_io = io.StringIO()
	stats = pstats.Stats(profiler, stream=string_io).sort_stats("time")
	stats.print_stats()
	print(string_io.getvalue())


def search_profile():
	profiler = cProfile.Profile()
	profiler.enable()

	client.get("/bib/index.html?"
		"title=Dance&"
		"author=Wil&"
		"year_from=1000&"
		"year_to=2000")

	profiler.disable()
	string_io = io.StringIO()
	stats = pstats.Stats(profiler, stream=string_io).sort_stats("time")
	stats.print_stats()
	print(string_io.getvalue())


if __name__ == "__main__":
	#all_profile()
	#parsing_profile()
	#search_profile()
	pass
