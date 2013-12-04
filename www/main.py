#!/usr/bin/env python3
# coding: utf-8
import datetime
import os.path
import sys

import flask
from flask.ext import babel

import constants
import parser
import search

bib_parser = parser.BibParser()
items = bib_parser.parse_folder(os.path.abspath("../bib"))
languages = sorted(bib_parser.get_scanned_fields("langid"))

APP_PREFIX = "/bib"

flask_app = flask.Flask(__name__)
flask_app.config["BABEL_DEFAULT_LOCALE"] = "en"
babel_app = babel.Babel(flask_app)

flask_app.jinja_env.trim_blocks = True
	
if (not os.path.exists("templates")):
	print("Should run from root folder")
	sys.exit()


@babel_app.localeselector
def get_locale():
	"""
	Extracts locale from request
	"""
	lang = flask.request.cookies.get("lang", None)
	if (lang is not None) and \
		(lang in constants.LANGUAGES):
		return lang
	else:	
		return flask.request.accept_languages.best_match(constants.LANGUAGES)


@flask_app.route(APP_PREFIX + "/")
def redirect_root():
	desired_language = flask.request.values.get("lang", None)
	next_url = APP_PREFIX + "/index.html"

	#if lang param is set, redirecting user back to the page he came from
	if (desired_language is not None) and \
		(desired_language in constants.LANGUAGES):
		referrer = flask.request.referrer
		if referrer is not None:
			next_url = referrer
		response = flask.make_response(flask.redirect(next_url))
		response.set_cookie("lang", value=desired_language,  
			expires=datetime.datetime(2100, 1, 1))
		return response
	else:	
		return flask.redirect(next_url)


@flask_app.route(APP_PREFIX + "/index.html")
def root():
	filters = []

	try:
		for search_key in constants.AVAILABLE_SEARCH_KEYS:
			# argument can be missing or be empty
			# both cases should be ignored during search
			search_param = flask.request.args.get(search_key, "")
			if len(search_param) > 0:
				if search_key in constants.SCAN_FIELDS:
					param_filter = search.search_for(
						search_key, 
						flask.request.args, 
						bib_parser.get_scanned_fields(search_key))
				else:
					param_filter = search.search_for(search_key, flask.request.args)
				if param_filter is not None:
					filters.append(param_filter)

		year_filter = search.search_for(constants.YEAR_PARAM, flask.request.args)
		if year_filter is not None:
			filters.append(year_filter)
	except Exception as ex:
		flask.abort(400, "Some of search parameters are wrong: {0}".format(ex))

	if not filters:
		return flask.render_template("index.html", 
			items=items, 
			languages=languages)

	found_items = items
	for f in filters:
		found_items = filter(f, found_items)

	return flask.render_template("index.html", 
		found_items=list(found_items),
		search_params=flask.request.args,
		languages=languages)


@flask_app.route(APP_PREFIX + "/all.html")
def show_all():
	return flask.render_template("all.html", items=items)


@flask_app.route(APP_PREFIX + "/book/<string:id>")
def book(id):
	f = search.search_for_string_exact("id", id)
	found_items = [item for item in items if f(item)]
	if len(found_items) == 0:
		flask.abort(404, "Book was not found")
	return flask.render_template("book.html", item=found_items[0])


@flask_app.route(APP_PREFIX + "/<path:filename>")
def everything_else(filename):
	if (os.path.isfile("templates/" + filename)):
		return flask.render_template(filename)
	elif (os.path.isfile("static/" + filename)):
		return app.send_static_file(filename)
	else:
		flask.abort(404)


if __name__ == "__main__":
	flask_app.debug = True
	flask_app.run(host="0.0.0.0")

#backward compatibility stuff
app = flask_app	
