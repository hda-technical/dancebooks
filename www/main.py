#!/usr/bin/env python3
# coding: utf-8
import datetime
import json
import os.path
import sys

import flask
from flask.ext import babel

import config
import parser
import search
import index
import messenger
import utils
import utils_flask

if (not os.path.exists("templates")):
	print("Should run from root folder")
	sys.exit(1)

cfg = config.Config("../configs/www.cfg")

items = parser.BibParser(cfg).parse_folder(os.path.abspath("../bib"))
item_index = index.Index(cfg, items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

langid = sorted(item_index["langid"].keys())
keywords = sorted(item_index["keywords"].keys())

flask_app = flask.Flask(__name__)
flask_app.config["BABEL_DEFAULT_LOCALE"] = cfg.www.languages[0]
babel_app = babel.Babel(flask_app)

flask_app.jinja_env.trim_blocks = True
flask_app.jinja_env.bytecode_cache = utils_flask.MemoryCache()

msngr = messenger.Messenger(cfg)
EXPIRES = datetime.datetime(2100, 1, 1)

@babel_app.localeselector
def get_locale():
	"""
	Extracts locale from request
	"""
	lang = flask.request.cookies.get("lang", None)
	if (lang in cfg.www.languages):
		return lang
	else:	
		return flask.request.accept_languages.best_match(cfg.www.languages)


@flask_app.route(cfg.www.app_prefix + "/")
def redirect_root():
	desired_language = flask.request.values.get("lang", None)
	next_url = cfg.www.app_prefix + "/index.html"

	#if lang param is set, redirecting user back to the page he came from
	if (desired_language is not None) and \
		(desired_language in cfg.www.languages):
		referrer = flask.request.referrer
		if referrer is not None:
			next_url = referrer
		response = flask.make_response(flask.redirect(next_url))
		response.set_cookie("lang", value=desired_language, expires=EXPIRES)
		return response
	else:	
		return flask.redirect(next_url)


@flask_app.route(cfg.www.app_prefix + "/index.html")
def root():
	args_filter = lambda pair: len(pair[1]) > 0
	request_args = dict(filter(args_filter, flask.request.args.items()))
	request_keys = set(request_args.keys())

	#if request_args is empty, we should render empty search form
	if len(request_args) == 0:
		return flask.render_template("index.html", items=items)

	found_items = None

	for index_to_use in (cfg.www.indexed_search_params & request_keys):
		value_to_use = request_args[index_to_use]

		if index_to_use in cfg.parser.list_params:
			values_to_use = utils.strip_split_list(value_to_use, ",")
		else:
			values_to_use = [value_to_use]

		for value in values_to_use:
			indexed_items = set(item_index[index_to_use].get(value, set()))
			if found_items is None:
				found_items = indexed_items
			else:
				found_items &= indexed_items
	
	searches = []
	if found_items is None:
		#no index was applied
		found_items = items
	
	try:
		for search_key in (cfg.www.nonindexed_search_params & request_keys):
			# argument can be missing or be empty
			# both cases should be ignored during search
			search_param = request_args[search_key]
			if len(search_param) > 0:
				param_filter = search.search_for(cfg, search_key, search_param)
				if param_filter is not None:
					searches.append(param_filter)
	except Exception as ex:
		flask.abort(400, "Some of search parameters are wrong: {0}".format(ex))

	if len(searches) > 0:
		found_items = list(filter(search.and_(searches), found_items))

	return flask.render_template(
		"index.html", 
		found_items=found_items,
		search_params=request_args)


@flask_app.route(cfg.www.app_prefix + "/all.html")
def show_all():
	return flask.render_template("all.html", items=items)


@flask_app.route(cfg.www.app_prefix + "/book/<string:id>", methods=["GET"])
def get_book(id):
	items = item_index["id"].get(id, None)
	if items is None:
		flask.abort(404, "Book with id {id} was not found".format(id=id))
	elif len(items) != 1:
		flask.abort(500, "Multiple entries with id {id}".format(id=id))
	items = list(items)
	return flask.render_template("book.html", item=items[0])


@flask_app.route(cfg.www.app_prefix + "/book/<string:book_id>", methods=["POST"])
def edit_book(book_id):
	items = list(item_index["id"].get(book_id, None))
	message = flask.request.values.get("message", None)
	from_name = flask.request.values.get("name", None)
	from_email = flask.request.values.get("email", None)

	if items is None:
		flask.abort(404, "Book with id {id} was not found".format(id=id))
	elif len(items) != 1:
		flask.abort(500, "Multiple entries with id {id}".format(id=id))
	
	if message is None:
		flask.abort(400, "Got empty message")
	
	if from_name is None:
		flask.abort(400, "Got empty name")

	if from_email is None:
		flask.abort(400, "Got empty email")
	
	message = messenger.Message(book_id, from_email, from_name, message)
	msngr.send(message)

	data = {"result": "OK", "message": babel.gettext("thanks")}
	response = flask.make_response(json.dumps(data, ensure_ascii=False))
	response.headers["Content-Type"] = "application/json; charset=utf-8"
	return response


@flask_app.route(cfg.www.app_prefix + "/langid", methods=["GET"])
def get_languages():
	data = dict(zip(langid, map(babel.gettext, langid)))
	response = flask.make_response(json.dumps(data, ensure_ascii=False))

	response.headers["Content-Type"] = "application/json; charset=utf-8"
	return response


@flask_app.route(cfg.www.app_prefix + "/keywords", methods=["GET"])
def get_keywords():
	data = keywords
	response = flask.make_response(json.dumps(data, ensure_ascii=False))
	response.headers["Content-Type"] = "application/json; charset=utf-8"
	return response


@flask_app.route(cfg.www.app_prefix + "/<path:filename>")
def everything_else(filename):
	if (os.path.isfile("templates/" + filename)):
		return flask.render_template(filename)
	elif (os.path.isfile("static/" + filename)):
		return flask_app.send_static_file(filename)
	else:
		flask.abort(404, "No such file")


if __name__ == "__main__":
	flask_app.debug = True
	flask_app.run(host="0.0.0.0")
