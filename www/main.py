#!/usr/bin/env python3
# coding: utf-8
import datetime
import http.client
import logging
import os.path
import random
import sys
from urllib import parse as urlparse

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
source_files = sorted(item_index["source_file"].keys())

flask_app = flask.Flask(__name__)
flask_app.config["BABEL_DEFAULT_LOCALE"] = config.www.languages[0]
flask_app.config["USE_EVALEX"] = False
babel_app = babel.Babel(flask_app)

flask_app.jinja_env.trim_blocks = True
flask_app.jinja_env.lstrip_blocks = True
flask_app.jinja_env.keep_trailing_newline = False
flask_app.jinja_env.bytecode_cache = utils_flask.MemoryCache()

#filling jinja filters
flask_app.jinja_env.filters["author_link"] = utils_flask.jinja_author_link
flask_app.jinja_env.filters["keyword_link"] = utils_flask.jinja_keyword_link
flask_app.jinja_env.filters["as_set"] = utils_flask.jinja_as_set
flask_app.jinja_env.filters["translate_language"] = utils_flask.jinja_translate_language
flask_app.jinja_env.filters["translate_keyword_category"] = utils_flask.jinja_translate_keyword_category
flask_app.jinja_env.filters["translate_keyword_ref"] = utils_flask.jinja_translate_keyword_ref
flask_app.jinja_env.filters["is_url_self_served"] = utils.is_url_self_served

def jinja_self_served_url_size(url, item):
	file_name, file_size = utils.get_file_info_from_url(url, item)
	return utils.pretty_print_file_size(file_size)

flask_app.jinja_env.filters["self_served_url_size"] = jinja_self_served_url_size

#filling jinja global variables
flask_app.jinja_env.globals["config"] = config

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
	response = flask.make_response(flask.redirect(config.www.app_prefix))
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


@flask_app.route(config.www.books_path, methods=["GET"])
@utils_flask.check_secret_cookie()
def show_all(show_secrets):
	return flask.render_template(
		"all.html",
		items=items,
		show_secrets=show_secrets
	)


@flask_app.route(config.www.books_path + "/<string:book_id>", methods=["GET"])
@utils_flask.check_secret_cookie()
def get_book(book_id, show_secrets):
	if book_id in config.www.id_redirections:
		return flask.redirect(
			"{books_path}/{new_id}".format(
				books_path=config.www.books_path,
				new_id = config.www.id_redirections[book_id]
			),
			code=http.client.MOVED_PERMANENTLY
		)

	items = item_index["id"].get(book_id, None)

	if items is None:
		flask.abort(404, "Book with id {book_id} was not found".format(book_id=book_id))
	elif len(items) != 1:
		message = "Multiple entries with id {book_id}".format(
			book_id=book_id
		)
		logging.error(message)
		flask.abort(500, message)

	item = utils.first(items)
	captcha_key = random.choice(config.www.secret_question_keys)

	return flask.render_template(
		"book.html",
		item=item,
		show_secrets=show_secrets,
		captcha_key=captcha_key
	)


@flask_app.route(config.www.app_prefix + "/books/<string:book_id>/pdf/<int:index>", methods=["GET"])
def get_book_pdf(book_id, index):
	items = item_index["id"].get(book_id, None)

	if (index <= 0):
		flask.abort(400, "Param index should be positive number")

	if items is None:
		flask.abort(404, "Book with id {book_id} was not found".format(
			book_id=book_id
		))
	elif len(items) != 1:
		message = "Multiple entries with id {book_id}".format(
			book_id=book_id
		)
		logging.error(message)
		flask.abort(500, message)

	item = utils.first(items)
	if (
		flask.request.base_url not in item.get("url") or
		not utils.is_url_self_served(flask.request.base_url)
	):
		flask.abort(404, "Book with id {book_id} isn't available for download".format(
			book_id=book_id
		))
	file_name, file_size = utils.get_file_info_from_url(flask.request.base_url, item)
	#filenames start from slash, trimming it
	pdf_full_path = os.path.join(config.www.elibrary_root, file_name[1:])

	if not os.path.isfile(pdf_full_path):
		message = "Item {book_id} metadata is wrong: file for url {rel_url} is missing".format(
			book_id=book_id,
			rel_url=flask.request.base_url
		)
		logging.error(message)
		flask.abort(500, message)

	logging.debug("Sending pdf file: {pdf_full_path}".format(
		pdf_full_path=pdf_full_path
	))
	response = flask.make_response(flask.send_file(pdf_full_path))
	response.headers["Content-Disposition"] = \
		"attachment; " \
		"filenane={ascii_filename};" \
		"filename*=UTF-8''{utf_filename}".format(
		ascii_filename="book.pdf",
		utf_filename=urlparse.quote(os.path.basename(pdf_full_path))
	)
	return response


@flask_app.route(config.www.app_prefix + "/books/<string:book_id>", methods=["POST"])
@utils_flask.jsonify()
@utils_flask.check_captcha()
def edit_book(book_id):
	items = item_index["id"].get(book_id, None)

	if items is None:
		flask.abort(404, "Book with id {id} was not found".format(id=id))
	elif len(items) != 1:
		message = "Multiple entries with id {id}".format(
			id=id
		)
		logging.error(message)
		flask.abort(500, message)

	message = utils_flask.extract_string_from_request("message")
	from_name = utils_flask.extract_string_from_request("name")
	from_email = utils_flask.extract_email_from_request("email")

	if not all([message, from_name, from_email]):
		flask.abort(400, "Empty values aren't allowed")

	item = utils.first(items)
	message = messenger.ErrorReport(item, from_email, from_name, message)
	message.send()

	return {"message": babel.gettext("interface:report:thanks")}


@flask_app.route(config.www.app_prefix + "/books/<string:book_id>/keywords", methods=["POST"])
@utils_flask.jsonify()
@utils_flask.check_captcha()
def edit_book_keywords(book_id):
	items = item_index["id"].get(book_id, None)

	if items is None:
		flask.abort(404, "Book with id {id} was not found".format(id=id))
	elif len(items) != 1:
		message = "Multiple entries with id {id}".format(
			id=id
		)
		logging.error(message)
		flask.abort(500, message)

	suggested_keywords = utils_flask.extract_keywords_from_request("keywords")
	from_name = utils_flask.extract_string_from_request("name")
	from_email = utils_flask.extract_email_from_request("email")

	if not all([suggested_keywords, from_name, from_email]):
		flask.abort(400, "Empty values aren't allowed")

	item = utils.first(items)
	message = messenger.KeywordsSuggest(item, from_email, from_name, suggested_keywords)
	message.send()

	return {"message": babel.gettext("interface:report:thanks")}


@flask_app.route(config.www.app_prefix + "/options", methods=["GET"])
@utils_flask.jsonify()
def get_options():
	opt_languages = [
		(langid, utils_flask.jinja_translate_language(langid))
		for langid in langids
	]

	opt_keywords = [
		(
			category,
			{
				"translation": utils_flask.jinja_translate_keyword_category(category),
				"keywords": category_keywords
			}
		)
		for category, category_keywords in config.parser.category_keywords.items()
	]

	opt_source_files = source_files

	return {
		"languages": opt_languages,
		"keywords": opt_keywords,
		"source_files": opt_source_files
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
		flask.abort(404, "No such file: {filename}".format(
			filename=filename
		))
	if (os.path.isfile("templates/static/" + filename)):
		return flask.render_template("static/" + filename)
	elif (os.path.isfile("static/" + filename)):
		return flask_app.send_static_file(filename)
	else:
		flask.abort(404, "No such file: {filename}".format(
			filename=filename
		))


if __name__ == "__main__":
	flask_app.run(host="0.0.0.0")
else:
	for code in werkzeug.HTTP_STATUS_CODES:
		#registering only required code
		if http.client.BAD_REQUEST <= code:
			flask_app.errorhandler(code)(utils_flask.xml_exception_handler)
	flask_app.errorhandler(Exception)(utils_flask.xml_exception_handler)

