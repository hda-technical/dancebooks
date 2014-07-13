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

XML_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>'

def xml_exception_handler(ex):
	"""
	Function converting Exception or HTTPException instance to xml response
	"""
	if isinstance(ex, werkzeug.exceptions.HTTPException):
		logging.warn("HTTP {name} error occured: {msg}".format(
			name=ex.name,
			msg=ex.description
		))
		xml_error = '{decl}\n<error code="{code}" description="{description}">{msg}</error>'.format(
			decl=XML_DECLARATION,
			code=ex.code,
			description=ex.name,
			msg=ex.description
		)
		response = flask.make_response(xml_error, ex.code)

	elif isinstance(ex, Exception):
		logging.exception("Unhandled exception: {ex}".format(
			ex=ex
		))
		xml_error = '{decl}\n<error code="{code}" description="{description}">{msg}</error>'.format(
			decl=XML_DECLARATION,
			code=500,
			description="Internal Server Error",
			msg=ex
		)
		response = flask.make_response(xml_error, 500)

	response.content_type = "text/xml; charset=utf-8"
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
				data = {"message": ex.description}
				code = ex.code;
				response = flask.make_response(
					json.dumps(data, ensure_ascii=False),
					code
				)
			except Exception as ex:
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


class _DefaultValue(object):
	pass


def extract_string_from_request(param_name, default=_DefaultValue):
	param = flask.request.values.get(param_name, default)
	if param is _DefaultValue:
		flask.abort(400, babel.gettext("errors:missing:" + param_name))
	return param


EMAIL_REGEXP = re.compile(".*@.*")
def extract_email_from_request(param_name, default=_DefaultValue):
	email = extract_string_from_request(param_name, default)
	if not EMAIL_REGEXP.match(email):
		flask.abort(400, babel.gettext("errors:wrong:email"))
	return email


class MemoryCache(jinja2.BytecodeCache):
	def __init__(self):
		self.cache = dict()

	def load_bytecode(self, bucket):
		if bucket.key in self.cache:
			bucket.bytecode_from_string(self.cache[bucket.key])

	def dump_bytecode(self, bucket):
		self.cache[bucket.key] = bucket.bytecode_to_string()
