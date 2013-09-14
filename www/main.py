#!/usr/bin/env python3
# coding: utf-8

import os.path

from flask import Flask, render_template, abort, request, redirect
from interval import Interval

from parser import BibParser, SearchGenerator

parser = BibParser()
items = parser.parse_folder(os.path.abspath("../bib"))

APP_PREFIX = "/bib"

app = Flask(__name__)

app.debug = True
app.jinja_env.trim_blocks = True
	
AVAILABLE_SEARCHES_STRING = ["author", "title", "hyphenation", "publisher", "location"]

if (not os.path.exists("templates")):
	print("Should run from root folder")
	sys.exit()


@app.route(APP_PREFIX + "/")
def redirect_root():
	return redirect(APP_PREFIX + "/index.html")
	

def filter_for_year(search_params):
	"""
	Generates filter for filtering publishing year interval.
	Modifies search_params to include year-specific search parameters,
	so they can be returned to user.
	"""
	year_from = request.args.get("year_from", "")
	year_to = request.args.get("year_to", "")

	search_params["year_to"] = year_to
	search_params["year_from"] = year_from

	if len(year_from) == 0:
		year_from = year_to

	if len(year_to) == 0:
		year_to = year_from

	if (len(year_from) == 0) and (len(year_to) == 0):
		return None
	else:
		return SearchGenerator.year(Interval(int(year_from), int(year_to)))
	

@app.route(APP_PREFIX + "/index.html")
def root():
	filters = []
	search_params = dict()
	for search_key in AVAILABLE_SEARCHES_STRING:
		# argument can be missing or be empty
		# both cases should be ignored during search
		search_param = request.args.get(search_key, "")
		if len(search_param) > 0:
			filters.append(SearchGenerator.string(search_key, search_param))
			search_params[search_key] = search_param

	year_filter = filter_for_year(search_params)
	if year_filter is not None:
		filters.append(year_filter)

	if (len(filters) == 0):
		return render_template("index.html", items=items)

	found_items = items
	for f in filters:
		print("Items before filter: " + str(len(found_items)))
		found_items = [item for item in found_items if f(item)]
		print("Items after filter: " + str(len(found_items)))

	return render_template("index.html", 
		found_items=found_items,
		search_params=search_params)


@app.route(APP_PREFIX + "/all.html")
def search():
	return render_template("all.html", items=items)


@app.route(APP_PREFIX + "/<path:filename>")
def everything_else(filename):
	if (os.path.isfile("templates/" + filename)):
		return render_template(filename)
	elif (os.path.isfile("static/" + filename)):
		return app.send_static_file(filename)
	else:
		abort(404)


if __name__ == "__main__":
	app.run(host="0.0.0.0")
