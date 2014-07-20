#!/usr/bin/env python3
# coding: utf-8
import datetime
import http.client
import logging
import os.path
import sys

import flask
from flask.ext import babel
import werkzeug

from config import config
import const
import bib_parser
import search
import index
import messenger
import utils
import utils_flask

if (not os.path.exists("templates")):
	logging.error("Should run from root folder")
	sys.exit(1)

items = sorted(
	bib_parser.BibParser().parse_folder(os.path.abspath("../bib")),
	key=bib_parser.BibItem.key_to_key_func(const.DEFAULT_ORDER_BY)
)
item_index = index.Index(items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

langids = sorted(item_index["langid"].keys())
keywords = list(item_index["keywords"].keys())
source_files = sorted(item_index["source_file"].keys())

flask_app = flask.Flask(__name__)
flask_app.config["BABEL_DEFAULT_LOCALE"] = config.www.languages[0]
flask_app.config["USE_EVALEX"] = False
babel_app = babel.Babel(flask_app)

flask_app.jinja_env.trim_blocks = True
flask_app.jinja_env.bytecode_cache = utils_flask.MemoryCache()
flask_app.jinja_env.filters["author_link"] = utils_flask.jinja_author_link
flask_app.jinja_env.filters["keyword_link"] = utils_flask.jinja_keyword_link
flask_app.jinja_env.filters["as_set"] = utils_flask.jinja_as_set

EXPIRES = datetime.datetime.today() + datetime.timedelta(days=1000)

@flask_app.before_first_request
def initialize():
	logging.info("Starting up")

@babel_app.localeselector
def get_locale():
	"""
	Extracts locale from request
	"""
	lang = (
		flask.request.cookies.get("lang", None) or
		getattr(flask.g, "lang", None)
	)
	if lang in config.www.languages:
		return lang
	else:
		return flask.request.accept_languages.best_match(config.www.languages)


@flask_app.route(config.www.app_prefix + "/secret-cookie", methods=["GET"])
def secret_cookie():
	response = flask.make_response(flask.redirect(config.www.app_prefix + "/index.html"))
	response.set_cookie(
		config.www.secret_cookie_key,
		value=config.www.secret_cookie_value,
		expires=EXPIRES
	)
	return response


@flask_app.route(config.www.app_prefix + "/ui-lang/<string:lang>", methods=["GET"])
def choose_ui_lang(lang):
	next_url = flask.request.referrer or config.www.app_prefix
	if lang in config.www.languages:
		response = flask.make_response(flask.redirect(next_url))
		response.set_cookie("lang", value=lang, expires=EXPIRES)
		return response
	else:
		flask.abort(404, "Language isn't available")


@flask_app.route(config.www.app_prefix, methods=["GET"])
@utils_flask.check_secret_cookie()
def root(show_secrets):
	return flask.render_template(
		"index.html",
		entry_count=len(items),
		show_secrets=show_secrets
	)


@flask_app.route(config.www.app_prefix + "/search", methods=["GET"])
@flask_app.route(config.www.app_prefix + "/basic-search", methods=["GET"])
@flask_app.route(config.www.app_prefix + "/advanced-search", methods=["GET"])
@flask_app.route(config.www.app_prefix + "/all-fields-search", methods=["GET"])
@utils_flask.check_secret_cookie()
def search_items(show_secrets):
	request_args = {
		key:value.strip()
		for key, value
		in flask.request.values.items()
		if value and key in config.www.search_params
	}
	request_keys = set(request_args.keys())

	order_by = flask.request.values.get("orderBy", const.DEFAULT_ORDER_BY)
	if order_by not in config.www.order_by_keys:
		flask.abort(400, "Key {order_by} is not supported for ordering".format(
			order_by=order_by
		))

	#if request_args is empty, we should render empty search form
	if len(request_args) == 0:
		flask.abort(400, "No search parameters specified")

	found_items = set(items)

	for index_to_use in (config.www.indexed_search_params & request_keys):

		value_to_use = request_args[index_to_use]

		if index_to_use in config.parser.list_params:
			values_to_use = utils.strip_split_list(value_to_use, ",")
		else:
			values_to_use = [value_to_use]

		for value in values_to_use:
			indexed_items = set(item_index[index_to_use].get(value, set()))
			found_items &= indexed_items

	searches = []
	try:
		for search_key in (config.www.nonindexed_search_params & request_keys):
			# argument can be missing or be empty
			# both cases should be ignored during search
			search_param = request_args[search_key]

			if len(search_param) > 0:
				param_filter = search.search_for(search_key, search_param)
				if param_filter is not None:
					searches.append(param_filter)
	except Exception as ex:
		flask.abort(400, "Some of the search parameters are wrong: {0}".format(ex))

	found_items = list(sorted(
		filter(search.and_(searches), found_items),
		key=bib_parser.BibItem.key_to_key_func(order_by)
	))

	return flask.render_template(
		"search.html",
		found_items=found_items,
		show_secrets=show_secrets
	)


@flask_app.route(config.www.app_prefix + "/books", methods=["GET"])
@utils_flask.check_secret_cookie()
def show_all(show_secrets):
	return flask.render_template(
		"all.html",
		items=items,
		show_secrets=show_secrets
	)


@flask_app.route(config.www.app_prefix + "/books/<string:id>", methods=["GET"])
@utils_flask.check_secret_cookie()
def get_book(id, show_secrets):

	items = item_index["id"].get(id, None)

	if items is None:
		flask.abort(404, "Book with id {id} was not found".format(id=id))
	elif len(items) != 1:
		flask.abort(500, "Multiple entries with id {id}".format(id=id))
	item = next(iter(items))
	return flask.render_template(
		"book.html",
		item=item,
		show_secrets=show_secrets
	)


@flask_app.route(config.www.app_prefix + "/books/<string:book_id>", methods=["POST"])
@utils_flask.jsonify()
def edit_book(book_id):
	items = item_index["id"].get(book_id, None)

	if items is None:
		flask.abort(404, "Book with id {id} was not found".format(id=id))
	elif len(items) != 1:
		flask.abort(500, "Multiple entries with id {id}".format(id=id))

	message = utils_flask.extract_string_from_request("message")
	from_name = utils_flask.extract_string_from_request("name")
	from_email = utils_flask.extract_email_from_request("email")
	if not all([message, from_name, from_email]):
		flask.abort(400, "Empty values aren't allowed")

	message = messenger.Message(book_id, from_email, from_name, message)
	message.send()

	return {"message": babel.gettext("interface:report:thanks")}


@flask_app.route(config.www.app_prefix + "/options", methods=["GET"])
@utils_flask.jsonify()
@utils_flask.check_secret_cookie()
def get_options(show_secrets):
	languages = [
		(langid, babel.gettext(const.BABEL_LANG_PREFIX + langid))
		for langid in langids
	]

	return {
		"languages": languages,
		"keywords": keywords,
		"source_files": source_files
	}


@flask_app.route(config.www.app_prefix + "/rss/books", methods=["GET"])
def rss_redirect():
	lang = get_locale()
	return flask.redirect("{prefix}/rss/{lang}/books".format(
		prefix=config.www.app_prefix,
		lang=lang
	))


@flask_app.route(config.www.app_prefix + "/rss/<string:lang>/books", methods=["GET"])
def get_books_rss(lang):
	if lang in config.www.languages:
		#setting attribute in flask.g so it cat be returned by get_locale call
		setattr(flask.g, "lang", lang)
	else:
		flask.abort(404, "Language isn't available")

	response = flask.make_response(flask.render_template(
		"rss/books.xml",
		item_index=item_index["added_on"]
	))
	response.content_type = "application/rss+xml"
	return response


@flask_app.route(config.www.app_prefix + "/<path:filename>", methods=["GET"])
def everything_else(filename):
	if (filename.startswith("components")):
		flask.abort(404, "No such file")
	if (os.path.isfile("templates/static/" + filename)):
		return flask.render_template("static/" + filename)
	elif (os.path.isfile("static/" + filename)):
		return flask_app.send_static_file(filename)
	else:
		flask.abort(404, "No such file")


if __name__ == "__main__":
	flask_app.run(host="0.0.0.0")
else:
	for code in werkzeug.HTTP_STATUS_CODES:
		#registering only required code
		if http.client.BAD_REQUEST <= code:
			flask_app.errorhandler(code)(utils_flask.xml_exception_handler)
	flask_app.errorhandler(Exception)(utils_flask.xml_exception_handler)

