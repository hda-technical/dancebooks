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
import index
import utils
import utils_flask

items = parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.create_index(items, constants.INDEX_KEYS)

languages = sorted(item_index["langid"].keys())
keywords = sorted(item_index["keywords"].keys())

flask_app = flask.Flask(__name__)
flask_app.config["BABEL_DEFAULT_LOCALE"] = "en"
babel_app = babel.Babel(flask_app)

flask_app.jinja_env.trim_blocks = True
flask_app.jinja_env.bytecode_cache = utils_flask.MemoryCache()
	
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


@flask_app.route(constants.APP_PREFIX + "/")
def redirect_root():
	desired_language = flask.request.values.get("lang", None)
	next_url = constants.APP_PREFIX + "/index.html"

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


@flask_app.route(constants.APP_PREFIX + "/index.html")
def root():
	#if request.args is empty, we should render empty search form
	if len(flask.request.args) == 0:
		return flask.render_template("index.html", items=items, languages=languages)

	found_items = None

	indices_to_use = constants.INDEXED_SEARCH_KEYS & set(flask.request.args.keys())
	for index_to_use in indices_to_use:
		value_to_use = flask.request.args[index_to_use]
		if len(value_to_use) == 0:
			continue

		if index_to_use in constants.MULTI_VALUE_PARAMS:
			values_to_use = utils.strip_split_list(value_to_use, constants.OUTPUT_LISTSEP)
		else:
			values_to_use = [value_to_use]

		for value in values_to_use:
			indexed_items = item_index[index_to_use].get(value, set([]))
			if found_items is None:
				found_items = indexed_items
			else:
				found_items &= indexed_items
	
	#index search returned empty result
	if found_items is None:
		return flask.render_template("index.html", 
			found_items=found_items,
			search_params=flask.request.args,
			languages=languages
		)

	searches = []
	try:
		for search_key in constants.NONINDEXED_SEARCH_KEYS:
			# argument can be missing or be empty
			# both cases should be ignored during search
			search_param = flask.request.args.get(search_key, "")
			if len(search_param) > 0:
				param_filter = search.search_for(search_key, flask.request.args)
				if param_filter is not None:
					searches.append(param_filter)

		year_filter = search.search_for(constants.YEAR_PARAM, flask.request.args)
		if year_filter is not None:
			searches.append(year_filter)
	except Exception as ex:
		flask.abort(400, "Some of search parameters are wrong: {0}".format(ex))

	found_items = list(filter(search.and_(searches), found_items))

	return flask.render_template("index.html", 
		found_items=found_items,
		search_params=flask.request.args,
		languages=languages
	)


@flask_app.route(constants.APP_PREFIX + "/all.html")
def show_all():
	return flask.render_template("all.html", items=items)


@flask_app.route(constants.BOOK_PREFIX + "/<string:id>")
def book(id):
	items = item_index["id"].get(id, None)
	if items is None:
		flask.abort(404, "Book with id {id} was not found".format(id=id))
	elif len(items) != 1:
		flask.abort(500, "Multiple entries with id {id}".format(id=id))
	return flask.render_template("book.html", item=items[0])


@flask_app.route(constants.APP_PREFIX + "/<path:filename>")
def everything_else(filename):
	if (os.path.isfile("templates/" + filename)):
		return flask.render_template(filename)
	elif (os.path.isfile("static/" + filename)):
		return flask_app.send_static_file(filename)
	else:
		flask.abort(404)


if __name__ == "__main__":
	flask_app.debug = True
	flask_app.run(host="0.0.0.0")

#backward compatibility stuff
app = flask_app	
