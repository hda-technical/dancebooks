#!/usr/bin/env python3
# coding: utf-8

import http.client
import logging
import os.path
import random

import flask
import flask_babel

from config import config
import const
import bib_parser
import search
import messenger
import utils
import utils_flask

if (not os.path.exists("templates")):
	raise RuntimeError("Should run from root folder")

items, item_index = bib_parser.BibParser().parse_folder(config.parser.bibdata_dir)

langids = sorted(langid for langid in item_index["langid"].keys() if not langid.startswith("!"))
source_files = sorted(item_index["source_file"].keys())
booktypes = sorted(item_index["booktype"].keys())
markdown_cache = utils.MarkdownCache()

debug_mode = False

flask_app = flask.Flask(__name__)
flask_app.config["BABEL_DEFAULT_LOCALE"] = utils.first(config.www.languages)
flask_app.config["USE_EVALEX"] = False
babel_app = flask_babel.Babel(flask_app)

flask_app.jinja_env.trim_blocks = True
flask_app.jinja_env.lstrip_blocks = True
flask_app.jinja_env.keep_trailing_newline = False

#filling jinja filters
flask_app.jinja_env.filters["author_link"] = utils_flask.make_author_link
flask_app.jinja_env.filters["keyword_link"] = utils_flask.make_keyword_link
flask_app.jinja_env.filters["as_set"] = utils_flask.as_set
flask_app.jinja_env.filters["translate_language"] = utils_flask.translate_language
flask_app.jinja_env.filters["translate_booktype"] = utils_flask.translate_booktype
flask_app.jinja_env.filters["translate_keyword_category"] = utils_flask.translate_keyword_cat
flask_app.jinja_env.filters["translate_keyword_ref"] = utils_flask.translate_keyword_ref
flask_app.jinja_env.filters["is_url_self_served"] = utils.is_url_self_served
flask_app.jinja_env.filters["format_date"] = utils_flask.format_date
flask_app.jinja_env.filters["format_catalogue_code"] = utils_flask.format_catalogue_code
flask_app.jinja_env.filters["format_item_id"] = utils_flask.format_item_id
flask_app.jinja_env.filters["format_transcription_url"] = utils_flask.format_transcription_url
flask_app.jinja_env.filters["format_guid_for_rss"] = utils_flask.format_guid_for_rss
flask_app.jinja_env.filters["format_transcribed_by"] = utils_flask.format_transcribed_by


def jinja_self_served_url_size(url, item):
	file_name, file_size = utils.get_file_info_from_url(url, item)
	return utils.pretty_print_file_size(file_size)

flask_app.jinja_env.filters["self_served_url_size"] = jinja_self_served_url_size

#filling jinja global variables
flask_app.jinja_env.globals["config"] = config
flask_app.jinja_env.globals["utils"] = utils

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
		getattr(flask.g, "lang", None) or
		flask.request.accept_languages.best_match(config.www.languages)
	)
	if lang in config.www.languages:
		return lang
	else:
		return utils.first(config.www.languages)


@flask_app.route("/secret-cookie", methods=["GET"])
@utils_flask.log_exceptions()
def secret_cookie():
	response = flask.make_response(flask.redirect("/"))
	response.set_cookie(
		config.www.secret_cookie_key,
		value=config.www.secret_cookie_value,
		max_age=const.SECONDS_IN_YEAR,
		httponly=True
	)
	return response


@flask_app.route("/ui-lang/<string:lang>", methods=["GET"])
@utils_flask.log_exceptions()
def choose_ui_lang(lang):
	next_url = flask.request.referrer or "/"
	if lang in config.www.languages:
		response = flask.make_response(flask.redirect(next_url))
		response.set_cookie(
			"lang",
			value=lang,
			max_age=const.SECONDS_IN_YEAR,
			httponly=True
		)
		return response
	else:
		flask.abort(http.client.NOT_FOUND, "Language isn't available")


@flask_app.route("/", methods=["GET"])
@utils_flask.log_exceptions()
@utils_flask.check_secret_cookie("show_secrets")
def root(show_secrets):
	return flask.render_template(
		"index.html",
		entry_count=len(items),
		show_secrets=(show_secrets or debug_mode)
	)


@flask_app.route("/search", methods=["GET"])
@flask_app.route("/basic-search", methods=["GET"])
@flask_app.route("/advanced-search", methods=["GET"])
@flask_app.route("/all-fields-search", methods=["GET"])
@utils_flask.check_secret_cookie("show_secrets")
@utils_flask.log_exceptions()
def search_items(show_secrets):
	request_args = {
		key: value.strip()
		for key, value
		in flask.request.values.items()
		if value and (key in config.www.search_params)
	}
	request_keys = set(request_args.keys())

	order_by = flask.request.values.get("orderBy", const.DEFAULT_ORDER_BY)
	if order_by not in config.www.order_by_keys:
		flask.abort(http.client.BAD_REQUEST, "Key {order_by} is not supported for ordering".format(
			order_by=order_by
		))

	#if request_args is empty, we should render empty search form
	if len(request_args) == 0:
		flask.abort(http.client.BAD_REQUEST, "No search parameters specified")

	found_items = set(items)

	for index_to_use in (config.www.indexed_search_params & request_keys):

		value_to_use = request_args[index_to_use]

		if (
			(index_to_use in config.parser.list_params) or
			(index_to_use in config.parser.keyword_list_params)
		):
			values_to_use = utils.strip_split_list(value_to_use, ",")
		else:
			values_to_use = [value_to_use]

		for value in values_to_use:
			if index_to_use == "availability":
				value = bib_parser.Availability(value)
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
		flask.abort(http.client.BAD_REQUEST, "Some of the search parameters are wrong: {0}".format(ex))

	found_items = list(sorted(
		filter(search.and_(searches), found_items),
		key=bib_parser.BibItem.key_to_key_func(order_by)
	))

	format = flask.request.values.get("format", "html")
	if (format == "html"):
		return flask.render_template(
			"search.html",
			found_items=found_items,
			show_secrets=(show_secrets or debug_mode)
		)
	elif (format == "csv"):
		response = flask.make_response(utils.render_to_csv(found_items))
		response.headers["Content-Type"] = "text/csv"
		response.headers["Content-Disposition"] = "attachment;filename=search_results.csv"
		return response
	else:
		flask.abort(
			http.client.BAD_REQUEST,
			"Unsupported output format {format}".format(
				format=format
			)
		)


@flask_app.route("/books/<string:book_id>", methods=["GET"])
@utils_flask.check_id_redirections("book_id")
@utils_flask.check_secret_cookie("show_secrets")
@utils_flask.log_exceptions()
def get_book(book_id, show_secrets):
	items = item_index["id"].get(book_id, None)
	if items is None:
		flask.abort(http.client.NOT_FOUND, "Book with id {book_id} was not found".format(book_id=book_id))

	item = utils.first(items)
	captcha_key = random.choice(list(config.www.secret_questions.keys()))

	return flask.render_template(
		"book.html",
		item=item,
		show_secrets=(show_secrets or debug_mode),
		captcha_key=captcha_key
	)


@flask_app.route("/books/<string:book_id>/pdf/<int:index>", methods=["GET"])
@utils_flask.check_id_redirections("book_id")
@utils_flask.log_exceptions()
def get_book_pdf(book_id, index):
	"""
	TODO: I'm a huge method that isn't easy to read
	Please, refactor me ASAP
	"""
	utils_flask.require(index > 0, http.client.NOT_FOUND, "Param index should be positive number")

	items = item_index["id"].get(book_id, None)
	if items is None:
		flask.abort(http.client.NOT_FOUND, "Book with id {book_id} was not found".format(
			book_id=book_id
		))
	item = utils.first(items)

	request_uri = flask.request.path
	item_urls = item.get("url") or set()
	filenames = item.get("filename")
	is_url_valid = (
		(request_uri in item_urls) and
		utils.is_url_local(request_uri) and
		utils.is_url_self_served(request_uri) and
		index <= len(filenames)
	)
	utils_flask.require(is_url_valid, http.client.NOT_FOUND, "Book with id {book_id} is not available for download".format(
		book_id=book_id
	))

	filename = filenames[index - 1]
	#filenames start from slash, trimming it
	pdf_full_path = os.path.join(config.www.elibrary_dir, filename[1:])

	if not os.path.isfile(pdf_full_path):
		message = "Item {book_id} metadata is wrong: file for url {rel_url} is missing".format(
			book_id=book_id,
			rel_url=request_url_production
		)
		logging.error(message)
		flask.abort(http.client.INTERNAL_SERVER_ERROR, message)

	logging.info("Sending pdf file: {pdf_full_path}".format(
		pdf_full_path=pdf_full_path
	))
	if config.unittest_mode:
		#using send_file in unittest mode causes ResourceWarning due to unclosed file
		response = flask.make_response("SOME_BINARY_PDF_LIKE_DATA")
		response.headers["Content-Type"] = "application/pdf"
		response.headers["Content-Disposition"] = "attachment"
		return response
	else:
		basename = os.path.basename(pdf_full_path)
		return flask.send_file(
			pdf_full_path,
			as_attachment=True,
			attachment_filename=basename
		)


@flask_app.route("/books/<string:item_id>/transcription", methods=["GET"])
@utils_flask.check_id_redirections("item_id")
@utils_flask.log_exceptions()
def get_book_markdown(item_id):
	items = item_index["id"].get(item_id)
	if items is None:
		flask.abort(
			http.client.NOT_FOUND,
			"Item with id {item_id} was not found".format(item_id=item_id)
		)

	item = utils.first(items)
	transcription = item.get("transcription")
	if transcription is None:
		flask.abort(
			http.client.NOT_FOUND,
			"Transcription for item {item_id} is not available".format(
				item_id=item_id
			)
		)

	markdown_file = os.path.join(
		config.parser.markdown_dir,
		transcription
	)
	return flask.render_template(
		"markdown.html",
		markdown_data=markdown_cache.get(markdown_file),
		item=item
	)


@flask_app.route("/books/<string:book_id>", methods=["POST"])
@utils_flask.jsonify()
@utils_flask.log_exceptions()
@utils_flask.check_captcha()
def edit_book(book_id):
	items = item_index["id"].get(book_id, None)

	if items is None:
		flask.abort(http.client.NOT_FOUND, "Book with id {id} was not found".format(id=id))

	message = utils_flask.extract_string_from_request("message")
	from_name = utils_flask.extract_string_from_request("name")
	from_email = utils_flask.extract_email_from_request("email")

	if not all([message, from_name, from_email]):
		flask.abort(http.client.BAD_REQUEST, "Empty values aren't allowed")

	item = utils.first(items)
	message = messenger.ErrorReport(item, from_email, from_name, message)
	message.send()

	return {"message": flask_babel.gettext("interface:report:thanks")}


@flask_app.route("/books/<string:book_id>/keywords", methods=["POST"])
@utils_flask.jsonify()
@utils_flask.log_exceptions()
@utils_flask.check_captcha()
def edit_book_keywords(book_id):
	items = item_index["id"].get(book_id, None)

	if items is None:
		flask.abort(http.client.NOT_FOUND, "Book with id {id} was not found".format(id=id))

	suggested_keywords = utils_flask.extract_keywords_from_request("keywords")
	from_name = utils_flask.extract_string_from_request("name")
	from_email = utils_flask.extract_email_from_request("email")

	if not all([suggested_keywords, from_name, from_email]):
		flask.abort(http.client.BAD_REQUEST, "Empty values aren't allowed")

	item = utils.first(items)
	message = messenger.KeywordsSuggest(item, from_email, from_name, suggested_keywords)
	message.send()

	return {"message": flask_babel.gettext("interface:report:thanks")}


@flask_app.route("/options", methods=["GET"])
@utils_flask.jsonify()
@utils_flask.log_exceptions()
def get_options():
	opt_languages = [
		(langid, utils_flask.translate_language(langid))
		for langid in langids
	]

	opt_keywords = [
		(
			category,
			{
				"translation": utils_flask.translate_keyword_cat(category),
				"keywords": category_keywords
			}
		)
		for category, category_keywords in config.parser.category_keywords.items()
	]

	opt_booktypes = [
		(booktype, utils_flask.translate_booktype(booktype))
		for booktype in booktypes
	]

	opt_source_files = [
		(source_file, source_file)
		for source_file in source_files
	]

	return {
		"languages": opt_languages,
		"keywords": opt_keywords,
		"source_files": opt_source_files,
		"booktypes": opt_booktypes
	}


@flask_app.route("/rss/books", methods=["GET"])
@utils_flask.log_exceptions()
def rss_redirect():
	lang = get_locale()
	return flask.redirect("/rss/{lang}/books".format(
		lang=lang
	))


@flask_app.route("/rss/<string:lang>/books", methods=["GET"])
@utils_flask.log_exceptions()
def get_books_rss(lang):
	if lang in config.www.languages:
		#setting attribute in flask.g so it cat be returned by get_locale call
		setattr(flask.g, "lang", lang)
	else:
		flask.abort(http.client.NOT_FOUND, "Language isn't available")

	response = flask.make_response(flask.render_template(
		"rss/books.xml",
		item_index=item_index["added_on"]
	))
	response.content_type = "application/rss+xml; charset=utf-8"
	return response


@flask_app.route("/<path:filename>", methods=["GET"])
@utils_flask.log_exceptions()
def everything_else(filename):
	if os.path.isfile(os.path.join("templates/static", filename)):
		return flask.render_template("static/" + filename)
	elif os.path.isfile(os.path.join("static", filename)):
		return flask_app.send_static_file(filename)
	else:
		flask.abort(http.client.NOT_FOUND, flask.request.base_url)


@flask_app.route("/ping", methods=["GET"])
def ping():
	return "OK"


# Setting up some custom error handlers
for code in (
	http.client.BAD_REQUEST,
	http.client.FORBIDDEN,
	http.client.NOT_FOUND,
	http.client.INTERNAL_SERVER_ERROR
):
	flask_app.errorhandler(code)(utils_flask.http_exception_handler)

flask_app.errorhandler(Exception)(utils_flask.http_exception_handler)

if __name__ == "__main__":
	debug_mode = True
	flask_app.run(host="0.0.0.0")

