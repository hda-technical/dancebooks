import datetime
import http.client
import functools
import json
import logging
import re

import flask
import flask_babel
import werkzeug

from config import config
import const
import utils

def http_exception_handler(ex):
	"""
	Function converting Exception or HTTPException instance
	to HTML response
	"""
	if isinstance(ex, werkzeug.exceptions.HTTPException):
		render = flask.render_template("error.html", error=ex)
		response = flask.make_response(render, ex.code)

	elif isinstance(ex, Exception):
		httpEx = werkzeug.exceptions.HTTPException(description="Internal Server Error")
		httpEx.code = http.client.INTERNAL_SERVER_ERROR
		render = flask.render_template("error.html", error=httpEx)
		response = flask.make_response(render, http.client.INTERNAL_SERVER_ERROR)

	return response


def check_secret_cookie(param_name):
	"""
	Checks presence of secret cookie
	"""
	def real_decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			show_secrets = (
				flask.request.cookies.get(config.www.secret_cookie_key, "") ==
				config.www.secret_cookie_value
			)

			kwargs[param_name] = show_secrets
			return func(*args, **kwargs)
		return wrapper
	return real_decorator


def check_id_redirections(param_name):
	"""
	Checks if requested book_id is outdated,
	and redirects to the actual url
	"""
	def real_decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			old_id = kwargs[param_name]
			if old_id in config.www.id_redirections:
				new_id = config.www.id_redirections[old_id]
				new_url = re.sub(
					r"\/{old_id}".format(old_id=old_id),
					r"/{new_id}".format(new_id=new_id),
					flask.request.url
				)
				return flask.redirect(
					new_url,
					code=http.client.MOVED_PERMANENTLY
				)
			return func(*args, **kwargs)
		return wrapper
	return real_decorator


def check_captcha():
	def real_decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			captcha_key = extract_string_from_request("captcha_key", None)
			captcha_answer = extract_int_from_request("captcha_answer", None)

			if captcha_key is None:
				flask.abort(http.client.FORBIDDEN, translate_missing_error("captcha-key"))

			if captcha_answer is None:
				flask.abort(http.client.FORBIDDEN, translate_wrong_error("captcha-answer"))

			if captcha_key not in config.www.secret_questions:
				flask.abort(http.client.FORBIDDEN, translate_wrong_error("captcha-key"))

			if captcha_answer != config.www.secret_questions[captcha_key]:
				flask.abort(http.client.FORBIDDEN, translate_wrong_error("captcha-answer"))

			return func(*args, **kwargs)
		return wrapper
	return real_decorator


def make_json_response(obj, response_code):
	"""
	Dumps object to text,
	returns flask.Response object
	with correct Content-Type and response code
	"""
	response = flask.make_response(
		json.dumps(obj, ensure_ascii=False),
		response_code
	)
	response.content_type = "application/json; charset=utf-8"
	return response


def log_exceptions():
	"""
	Decorator for logging all the exceptions and reraising them
	"""
	def real_decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as ex:
				logging.exception("Exception occurred: {ex}".format(
					ex=ex
				))
				raise
		return wrapper
	return real_decorator


def jsonify():
	"""
	Decorator dumping response to json
	"""
	def real_decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			try:
				data = func(*args, **kwargs)
				return make_json_response(data, http.client.OK)

			except werkzeug.exceptions.HTTPException as ex:
				data = {"message": ex.description}
				return make_json_response(data, ex.code)

			except Exception as ex:
				data = {"message": "Internal Server Error"}
				return make_json_response(data, http.client.INTERNAL_SERVER_ERROR)

		return wrapper
	return real_decorator


#functions to be registered in jinja: begin
def make_author_link(author):
	return '<a href="{path}?author={author}">{author}</a>'.format(
		path=config.www.basic_search_prefix,
		author=author
	)


def make_keyword_link(keyword):
	return '<a href="{path}?keywords={keyword}">{keyword}</a>'.format(
		path=config.www.advanced_search_prefix,
		keyword=keyword
	)


def format_catalogue_code(single_code):
	cat_type, cat_code = single_code.split(const.CATALOGUE_SEPARATOR)
	item_id, title = const.CATALOGUE_MAP[cat_type];
	return '<a href="{prefix}/{item_id}">{title}</a>: {code}'.format(
		prefix=config.www.books_prefix,
		item_id=item_id,
		title=title,
		code=cat_code
	)


def format_transcription_url(item):
	return '<a href="{prefix}/{item_id}/transcription">https://{app_domain}{prefix}/{item_id}/transcription</a>'.format(
		app_domain=config.www.app_domain_production,
		prefix=config.www.books_prefix,
		item_id=item.id()
	)
	

def format_guid_for_rss(items):
	get_id = lambda item: item.id()
	return "|".join(map(get_id, sorted(items, key=get_id)))


def format_item_id(item_id):
	return '<a href="{prefix}/{item_id}">{item_id}</a>'.format(
		item_id=item_id,
		prefix=config.www.books_prefix
	)

def as_set(value):
	return set(value)


def translate_language(langid):
	return flask_babel.gettext(const.BABEL_LANG_PREFIX + langid)


def translate_booktype(booktype):
	return flask_babel.gettext(const.BABEL_BOOKTYPE_PREFIX + booktype)


def translate_keyword_cat(category):
	return flask_babel.gettext(const.BABEL_KEYWORD_CATEGORY_PREFIX + category)


def translate_keyword_ref(keyword):
	#colon should be remove, spaces should be replaces with dashes
	key = keyword.replace(":", "").replace(" ", "-")
	return flask_babel.gettext(const.BABEL_KEYWORD_REF_PREFIX + key)


def translate_missing_error(key):
	return flask_babel.gettext(const.BABEL_MISSING_ERROR_PREFIX + key.replace("_", "-"))


def translate_wrong_error(key):
	return flask_babel.gettext(const.BABEL_WRONG_ERROR_PREFIX + key.replace("_", "-"))


def translate_month(month):
	return flask_babel.gettext(const.BABEL_MONTH_PREFIX + "{month:02}".format(
		month=month
	))


def format_date(item):
	year = item.get("year");
	if item.get("year_circa"):
		return year
	#year_from == year_to == int(year) below
	year_from = item.get("year_from")
	month = item.get("month")
	day = item.get("day")

	if all([year_from, month, day]):
		date = datetime.date(year_from, month, day)
		return flask_babel.format_date(date, format="d MMMM y")
	elif all([year_from, month]):
		#babel is unable to format month correctly for Russian language
		#using own implementation here
		return (translate_month(month) + ", " + year)
	else:
		return year


#parsing parameter helpers: begin
class _DefaultValueString(object):
	pass


class _DefaultValueInt(object):
	pass


class _DefaultValueJson(object):
	pass


class _DefaultValueEmail(object):
	pass


class _DefaultValueList(object):
	pass


class _DefaultValueKeywords(object):
	pass


def extract_string_from_request(param_name, default=_DefaultValueString):
	result = flask.request.values.get(param_name, default)
	if result is _DefaultValueString:
		flask.abort(
			http.client.BAD_REQUEST,
			translate_missing_error(param_name)
		)
	if result is default:
		return result
	return result


def extract_int_from_request(param_name, default=_DefaultValueInt):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueInt:
		flask.abort(http.client.BAD_REQUEST, translate_wrong_error(param_name))
	if result is default:
		return result

	try:
		return int(result)
	except Exception:
		flask.abort(http.client.BAD_REQUEST, translate_wrong_error(param_name))


def extract_json_from_request(param_name, default=_DefaultValueJson):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueJson:
		flask.abort(http.client.BAD_REQUEST, translate_wrong_error(param_name))
	if result is default:
		return result

	try:
		return json.loads(result)
	except Exception:
		flask.abort(http.client.BAD_REQUEST, translate_wrong_error(param_name))


def extract_list_from_request(param_name, default=_DefaultValueList):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueList:
		flask.abort(http.client.BAD_REQUEST, translate_missing_error(param_name))
	if result is default:
		return result

	try:
		return utils.strip_split_list(result, ",")
	except Exception:
		flask.abort(http.client.BAD_REQUEST,translate_wrong_error(param_name))


def extract_keywords_from_request(param_name, default=_DefaultValueKeywords):
	"""
	Extracts keywords, validates them according to config,
	inserts parent keywords if needed.
	Returns alphabetically sorted list of keywords.
	"""
	result = extract_list_from_request(param_name, default)
	if result is _DefaultValueKeywords:
		flask.abort(http.client.BAD_REQUEST, translate_wrong_error(param_name))
	if result is default:
		return result

	result_keywords = set()
	for keyword in result:
		if keyword not in config.parser.keywords:
			flask.abort(
				http.client.BAD_REQUEST,
				translate_wrong_error(param_name) + keyword
			)
		result_keywords.add(keyword)
		parent_keyword = utils.extract_parent_keyword(keyword)
		result_keywords.add(parent_keyword)
	return sorted(result_keywords)


EMAIL_REGEXP = re.compile(".*@.*")
def extract_email_from_request(param_name, default=_DefaultValueEmail):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueEmail:
		flask.abort(http.client.BAD_REQUEST, translate_wrong_error(param_name))
	if result is default:
		return result

	if not EMAIL_REGEXP.match(result):
		flask.abort(http.client.BAD_REQUEST, translate_wrong_error(param_name))
	return result
