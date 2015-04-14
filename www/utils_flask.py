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
		logging.warning("While processing {request_url} HTTP {code} error occurred: {msg}".format(
			request_url=flask.request.base_url,
			code=ex.code,
			msg=ex.description
		))
		render = flask.render_template("error.html", error=ex)
		response = flask.make_response(render, ex.code)

	elif isinstance(ex, Exception):
		logging.exception("While processing {request_url} unhandled exception ocurred: {ex}".format(
			request_url=flask.request.base_url,
			ex=ex
		))
		render = flask.render_template("error.html", error=ex)
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
				flask.abort(http.client.FORBIDDEN, babel.gettext("errors:missing:captcha-key"))

			if captcha_answer is None:
				flask.abort(http.client.FORBIDDEN, babel.gettext("errors:missing:captcha-answer"))

			if captcha_key not in config.www.secret_questions:
				flask.abort(http.client.FORBIDDEN, babel.gettext("errors:wrong:captcha-key"))

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
				logging.exception("While processing {request_url} unhandled exception ocurred: {ex}".format(
					request_url=flask.request.base_url,
					ex=ex
				))
				data = {"message": ex.description}
				code = ex.code;
				response = flask.make_response(
					json.dumps(data, ensure_ascii=False),
					code
				)
			except Exception as ex:
				logging.exception("While processing {request_url} unhandled exception ocurred: {ex}".format(
					request_url=flask.request.base_url,
					ex=ex
				))
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

def as_set(value):
	return set(value)

def translate_language(langid):
	return babel.gettext(const.BABEL_LANG_PREFIX + langid)

def translate_booktype(booktype):
	return babel.gettext(const.BABEL_BOOKTYPE_PREFIX + booktype)

def translate_keyword_cat(category):
	return babel.gettext(const.BABEL_KEYWORD_CATEGORY_PREFIX + category)

def translate_keyword_ref(keyword):
	#colon should be remove, spaces should be replaces with dashes
	key = keyword.replace(":", "").replace(" ", "-")
	return babel.gettext(const.BABEL_KEYWORD_REF_PREFIX + key)

#functions to be registered in jinja: end


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
			babel.gettext("errors:missing:" + param_name.replace("_", "-"))
		)
	if result is default:
		return result
	return result


def extract_int_from_request(param_name, default=_DefaultValueInt):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueInt:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)
	if result is default:
		return result

	try:
		return int(result)
	except Exception:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)


def extract_json_from_request(param_name, default=_DefaultValueJson):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueJson:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)
	if result is default:
		return result

	try:
		return json.loads(result)
	except Exception:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)


def extract_list_from_request(param_name, default=_DefaultValueList):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueList:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)
	if result is default:
		return result

	try:
		return utils.strip_split_list(result,",")
	except Exception:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)


def extract_keywords_from_request(param_name, default=_DefaultValueKeywords):
	"""
	Extracts keywords, validates them according to config,
	inserts parent keywords if needed.
	Returns alphabetically sorted list of keywords.
	"""
	result = extract_list_from_request(param_name, default)
	if result is _DefaultValueKeywords:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)
	if result is default:
		return result

	result_keywords = set()
	for keyword in result:
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


EMAIL_REGEXP = re.compile(".*@.*")
def extract_email_from_request(param_name, default=_DefaultValueEmail):
	result = extract_string_from_request(param_name, default)
	if result is _DefaultValueEmail:
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)
	if result is default:
		return result

	if not EMAIL_REGEXP.match(result):
		flask.abort(
			http.client.BAD_REQUEST,
			babel.gettext("errors:wrong:" + param_name.replace("_", "-"))
		)
	return result


#parsing parameter helpers: end
class MemoryCache(jinja2.BytecodeCache):
	def __init__(self):
		self.cache = dict()

	def load_bytecode(self, bucket):
		if bucket.key in self.cache:
			bucket.bytecode_from_string(self.cache[bucket.key])

	def dump_bytecode(self, bucket):
		self.cache[bucket.key] = bucket.bytecode_to_string()
