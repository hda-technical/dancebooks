#!/usr/bin/env python3
# coding: utf-8

import os.path

from flask import Flask, render_template, abort, request, redirect

from parser import BibParser

parser = BibParser()
items = parser.parse_folder(os.path.abspath("../bib"))

APP_PREFIX = "/bib"

app = Flask(__name__)

app.debug = True
app.jinja_env.trim_blocks = True
	
AVAILABLE_SEARCHES = ["author", "title", "hyphenation", "publisher", "location"]

if (not os.path.exists("templates")):
	print("Should run from root folder")
	sys.exit()


@app.route(APP_PREFIX + "/")
def redirect_root():
	return redirect(APP_PREFIX + "/index.html")
	

@app.route(APP_PREFIX + "/index.html")
def root():
	search_params = dict()
	for search_key in AVAILABLE_SEARCHES:
		search_param = request.args.get(search_key, None)
		# argument can be missing or be empty
		# both cases should be ignored during search
		if (search_param is not None) and (len(search_param) > 0):
			search_params[search_key] = search_param
	
	if (len(search_params) == 0):
		return render_template("index.html", items=items)

	found_items = items
	for (key, value) in search_params.items():
		print("Searching with " + str((key, value)))
		print("Items before filter: " + str(len(found_items)))
		filter_func = lambda item: \
						     item.param(key) is not None and \
						     item.param(key).find(value) != -1
		found_items = [item for item in found_items if filter_func(item)]
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
