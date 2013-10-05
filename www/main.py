#!/usr/bin/env python3
# coding: utf-8

import os.path

from flask import Flask, render_template, abort, request, redirect
from interval import Interval

from parser import BibParser, YEAR_PARAM
from search import search_for, search_for_string_exact

parser_options = {
	BibParser.LISTSEP : "|", 
	BibParser.NAMESEP : "|", 
	BibParser.KEYWORDSEP : ",",
	BibParser.SCANFIELDS : set(["hyphenation", "keywords"])
}
parser = BibParser(parser_options)
items = parser.parse_folder(os.path.abspath("../bib"))
languages = sorted(parser.get_scanned_fields("hyphenation"))

APP_PREFIX = "/bib"

app = Flask(__name__)

app.jinja_env.trim_blocks = True
	
AVAILABLE_SEARCH_KEYS = [
	"author", "title", "hyphenation", "publisher", "location", "keywords"
	]

if (not os.path.exists("templates")):
	print("Should run from root folder")
	sys.exit()


@app.route(APP_PREFIX + "/")
def redirect_root():
	return redirect(APP_PREFIX + "/index.html")
	

@app.route(APP_PREFIX + "/index.html")
def root():
	filters = []
	search_params = dict()

	try:
		for search_key in AVAILABLE_SEARCH_KEYS:
			# argument can be missing or be empty
			# both cases should be ignored during search
			search_param = request.values.get(search_key, "")
			if len(search_param) > 0:
				if search_key in parser_options[BibParser.SCANFIELDS]:
					param_filter = search_for(search_key, request.values, 
						parser.get_scanned_fields(search_key))
				else:
					param_filter = search_for(search_key, request.values)
				if param_filter is not None:
					filters.append(param_filter)

		year_filter = search_for(YEAR_PARAM, request.values)
		if year_filter is not None:
			filters.append(year_filter)
	except:
		abort(400, "Some of search parameters are wrong")

	if not filters:
		return render_template("index.html", 
			items = items, 
			languages = languages)

	found_items = items
	for f in filters:
		found_items = [item for item in found_items if f(item)]

	return render_template("index.html", 
		found_items = found_items,
		search_params = request.args,
		languages = languages)


@app.route(APP_PREFIX + "/all.html")
def search():
	return render_template("all.html", items = items)


@app.route(APP_PREFIX + "/book/<string:id>")
def book(id):
	f = search_for_string_exact("id", id)
	found_items = [item for item in items if f(item)]
	if len(found_items) == 0:
		abort(404, "Book was not found")
	return render_template("book.html", items = found_items)


@app.route(APP_PREFIX + "/<path:filename>")
def everything_else(filename):
	if (os.path.isfile("templates/" + filename)):
		return render_template(filename)
	elif (os.path.isfile("static/" + filename)):
		return app.send_static_file(filename)
	else:
		abort(404)


if __name__ == "__main__":
	app.debug = True
	app.run(host="0.0.0.0")
