import http.client
import functools
import json
import logging
import re

import flask
from flask.ext import babel
import jinja2
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
		logging.warn("HTTP {name} error occured: {msg}".format(
			name=ex.name,
			msg=ex.description
		))
		render = flask.render_template("error.html", error=ex)
		response = flask.make_response(render, ex.code)

	elif isinstance(ex, Exception):
		logging.exception("Unhandled exception: {ex}".format(
			ex=ex
		))
		render = flask.render_template("error.html", error=ex)
		response = flask.make_response(render, http.client.INTERNAL_SERVER_ERROR)

	return response


def check_secret_cookie():
	def real_decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			show_secrets = (
				flask.request.cookies.get(config.www.secret_cookie_key, "") ==
				config.www.secret_cookie_value
			)

			kwargs["show_secrets"] = show_secrets
			return func(*args, **kwargs)
		return wrapper
	return real_decorator


def check_captcha():
	def real_decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			captcha_key = extract_string_from_request("captcha_key")
			captcha_answer = extract_int_from_request("captcha_answer")

			if captcha_key not in config.www.secret_questions:
				flask.abort(http.client.BAD_REQUEST, babel.gettext("errors:wrong:captcha-key"))

			if captcha_answer != config.www.secret_questions[captcha_key]:
				flask.abort(http.client.FORBIDDEN, babel.gettext("errors:wrong:captcha-answer"))

			return func(*args, **kwargs)
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
				code = http.client.OK
				response = flask.make_response(
					json.dumps(data, ensure_ascii=False),
					code
				)
			except werkzeug.exceptions.HTTPException as ex:
				logging.exception(ex)
				data = {"message": ex.description}
				code = ex.code;
				response = flask.make_response(
					json.dumps(data, ensure_ascii=False),
					code
				)
			except Exception as ex:
				logging.exception(ex)
				data = {"message": "Internal Server Error"}
				code = http.client.INTERNAL_SERVER_ERROR
				response = flask.make_response(
					json.dumps(data, ensure_ascii=False),
					code
				)

			response.content_type = "application/json; charset=utf-8"
			return response


		return wrapper
	return real_decorator


#functions to be registered in jinja: begin
def jinja_author_link(author):
	return '<a href="{path}?author={author}">{author}</a>'.format(
		path=config.www.basic_search_url,
		author=author
	)


def jinja_keyword_link(keyword):
	return '<a href="{path}?keywords={keyword}">{keyword}</a>'.format(
		path=config.www.advanced_search_url,
		keyword=keyword
	)

def jinja_as_set(value):
	return set(value)

def jinja_translate_language(langid):
	return babel.gettext(const.BABEL_LANG_PREFIX + langid)

def jinja_translate_keyword_category(category):
	return babel.gettext(const.BABEL_KEYWORD_CATEGORY_PREFIX + category)

def jinja_translate_keyword_ref(keyword):
	#colon should be remove, spaces should be replaces with dashes
	key = keyword.replace(":", "").replace(" ", "-")
	return babel.gettext(const.BABEL_KEYWORD_REF_PREFIX + key)

def jinja_is_url_self_served(url):
	return utils.is_url_self_served(url)
#functions to be registered in jinja: end


#parsing parameter helpers: begin
class _DefaultValue(object):
	pass


def extract_string_from_request(param_name, default=_DefaultValue):
	param = flask.request.values.get(param_name, default)
	if param is _DefaultValue:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:missing:" + param_name.replace("_", "-"))
		)
	return param


EMAIL_REGEXP = re.compile(".*@.*")
def extract_email_from_request(param_name, default=_DefaultValue):
	result = extract_string_from_request(param_name, default)
	if not EMAIL_REGEXP.match(result):
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)
	return result


def extract_int_from_request(param_name, default=_DefaultValue):
	result = extract_string_from_request(param_name, default)
	try:
		return int(result)
	except Exception:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)


def extract_json_from_request(param_name, default=_DefaultValue):
	result = extract_string_from_request(param_name, default)
	try:
		return json.loads(result)
	except Exception:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)

def extract_list_from_request(param_name, default=_DefaultValue):
	result = extract_string_from_request(param_name, default)
	try:
		return utils.strip_split_list(result,",")
	except Exception:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)

def extract_keywords_from_request(param_name, default=_DefaultValue):
	"""
	Extracts keywords, validates them according to config,
	inserts parent keywords if needed.
	Returns alphabetically sorted list of keywords.
	"""
	parsed_keywords = extract_list_from_request(param_name, default)
	result_keywords = set()
	for keyword in parsed_keywords:
		if keyword not in config.parser.keywords:
			flask.abort(
				http.client.BAD_REQUEST,
				babel.gettext("errors:wrong:" + param_name.replace("_", "-")) +
					" " + keyword
			)
		result_keywords.add(keyword)
		parent_keyword = utils.extract_parent_keyword(keyword)
		result_keywords.add(parent_keyword)
	return sorted(result_keywords)
#parsing parameter helpers: end


class MemoryCache(jinja2.BytecodeCache):
	def __init__(self):
		self.cache = dict()

	def load_bytecode(self, bucket):
		if bucket.key in self.cache:
			bucket.bytecode_from_string(self.cache[bucket.key])

	def dump_bytecode(self, bucket):
		self.cache[bucket.key] = bucket.bytecode_to_string()
