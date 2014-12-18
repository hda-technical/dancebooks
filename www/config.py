import collections
import configparser
import functools
import json
import logging.config
import os
import subprocess

import const


class SmtpConfig(object):
	def __init__(self, params):
		if "host" not in params:
			raise ValueError("host param wasn't found")
		self.host = params["host"]

		if "port" not in params:
			raise ValueError("port param wasn't found")
		self.port = int(params["port"])

		if "user" not in params:
			raise ValueError("user param wasn't found")
		self.user = params["user"]

		if "password" not in params:
			raise ValueError("password param wasn't found")
		self.password = params["password"]

		if "email" not in params:
			raise ValueError("email param wasn't found")
		self.email = params["email"]


class BugReportConfig(object):
	def __init__(self, params):
		if "to_addr" not in params:
			raise ValueError("to_addr param wasn't found")
		self.to_addr = params["to_addr"]

		if "to_name" not in params:
			raise ValueError("to_name param wasn't found")
		self.to_name = params["to_name"]


class ParserConfig(object):
	def __init__(self, params):
		if "list_sep" not in params:
			raise ValueError("list_sep param wasn't found")
		self.list_sep = params["list_sep"]

		if "list_params" not in params:
			raise ValueError("list_params param wasn't found")
		self.list_params = set(json.loads(params["list_params"]))

		if "int_params" not in params:
			raise ValueError("int_params param wasn't found")
		self.int_params = set(json.loads(params["int_params"]))

		if "year_params" not in params:
			raise ValueError("year_params param wasn't found")
		self.year_params = set(json.loads(params["year_params"]))

		if "date_params" not in params:
			raise ValueError("date_params param wasn't found")
		self.date_params = set(json.loads(params["date_params"]))

		if "bool_params" not in params:
			raise ValueError("bool_params param wasn't found")
		self.bool_params = set(json.loads(params["bool_params"]))

		if "date_format" not in params:
			raise ValueError("date_format param wasn't found")
		self.date_format = params["date_format"]

		if "blocked_domains" not in params:
			raise ValueError("blocked_domains param wasn't found")
		self.blocked_domains = set(json.loads(params["blocked_domains"]))

		#keywords param is loaded from a single config value,
		#but is splitted into a number of config fields with predictable meaning
		if "keywords" not in params:
			raise ValueError("keywords param wasn't found")
		keywords = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(params["keywords"])
		self.keywords = set()
		self.category_keywords = collections.defaultdict(list)
		self.keywords_with_ref = []
		for category, cat_keywords in keywords.items():
			for keyword, has_reference in cat_keywords.items():
				#iterating through (keywords, has_reference) tuples
				self.keywords.add(keyword)
				self.category_keywords[category].append(keyword)
				if has_reference:
					self.keywords_with_ref.append(keyword)

		#suffixes parsing
		if "start_suffix" not in params:
			raise ValueError("start_suffix param wasn't found")
		self.start_suffix = params["start_suffix"]

		if "end_suffix" not in params:
			raise ValueError("end_suffix param wasn't found")
		self.end_suffix = params["end_suffix"]

		if "circa_suffix" not in params:
			raise ValueError("circa_suffix param wasn't found")
		self.circa_suffix = params["circa_suffix"]

		#generating additional params
		suffix_adder = lambda string, suffix: string + suffix
		self.year_start_params = set(map(
			functools.partial(suffix_adder, suffix=self.start_suffix),
			self.year_params
		))

		self.year_end_params = set(map(
			functools.partial(suffix_adder, suffix=self.end_suffix),
			self.year_params
		))

		self.date_start_params = set(map(
			functools.partial(suffix_adder, suffix=self.start_suffix),
			self.date_params
		))

		self.date_end_params = set(map(
			functools.partial(suffix_adder, suffix=self.end_suffix),
			self.date_params
		))


class WwwConfig(object):
	def __init__(self, params):
		if "app_domain" not in params:
			raise ValueError("app_domain param wasn't found")
		self.app_domain = params["app_domain"]

		if "app_prefix" not in params:
			raise ValueError("app_prefix param wasn't found")
		self.app_prefix = params["app_prefix"]

		self.books_url = "https://" + self.app_domain + self.app_prefix + "/books"
		self.basic_search_url = self.app_prefix + "/basic-search"
		self.advanced_search_url = self.app_prefix + "/advanced-search"
		self.all_fields_search_url = self.app_prefix + "/all-fields-search"

		if "search_params" not in params:
			raise ValueError("search_params param wasn't found")
		self.search_params = set(json.loads(params["search_params"]))

		if "search_synonyms" not in params:
			raise ValueError("search_synonyms params wasn't found")
		self.search_synonyms = json.loads(params["search_synonyms"])

		if "index_params" not in params:
			raise ValueError("index_params param wasn't found")
		self.index_params = set(json.loads(params["index_params"]))

		self.indexed_search_params = self.search_params & self.index_params
		self.nonindexed_search_params = self.search_params - self.index_params

		if "languages" not in params:
			raise ValueError("languages param wasn't found")
		self.languages = json.loads(params["languages"])

		if "secret_cookie_key" not in params:
			raise ValueError("secret_cookie_key wasn't found")
		self.secret_cookie_key = params["secret_cookie_key"]

		if "secret_cookie_value" not in params:
			raise ValueError("secret_cookie_value wasn't found")
		self.secret_cookie_value = params["secret_cookie_value"]

		if "date_formats" not in params:
			raise ValueError("date_formats param wasn't found")
		self.date_formats = json.loads(params["date_formats"])

		if "order_by_keys" not in params:
			raise ValueError("order_by_keys param wasn't found")
		self.order_by_keys = set(json.loads(params["order_by_keys"]))

		if "elibrary_root" not in params:
			raise ValueError("elibrary_root param wasn't found")
		self.elibrary_root = params["elibrary_root"]

		if "secret_question_keys" not in params:
			raise ValueError("secret_question_keys param wasn't found")
		self.secret_question_keys = json.loads(params["secret_question_keys"])

		if "secret_question_answers" not in params:
			raise ValueError("secret_question_answers param wasn't found")
		secret_question_answers = json.loads(params["secret_question_answers"])

		self.secret_questions = {
			key: answer
			for key, answer in zip(
				self.secret_question_keys,
				secret_question_answers
			)
		}

class Config(object):
	@staticmethod
	def get_params(config, fallback, section):
		params = dict()
		if (fallback is not None) and (section in fallback):
			params.update(fallback[section])
		if section in config:
			params.update(config[section])
		return params

	def __init__(self, path):
		config = configparser.ConfigParser(interpolation=None)
		config.read(path)

		fallback = None
		if "DEFAULT" in config:
			if "fallback" in config["DEFAULT"]:
				path = os.path.join(
					os.path.dirname(path),
					config["DEFAULT"]["fallback"]
				)
				fallback = configparser.ConfigParser()
				fallback.read(path)
		self.smtp = SmtpConfig(Config.get_params(config, fallback, "SMTP"))
		self.bug_report = BugReportConfig(Config.get_params(config, fallback, "BUG_REPORT"))
		self.parser = ParserConfig(Config.get_params(config, fallback, "PARSER"))
		self.www = WwwConfig(Config.get_params(config, fallback, "WWW"))

		self.version = subprocess.check_output(
			"git log | "
			"head -n 1 | "
			"cut -f 2 -d ' '",
			shell=True
		).decode().strip()


def setup_logging(config_path):
	logging.config.fileConfig(config_path)

config_path = os.environ.get(const.ENV_CONFIG, None)
if config_path is None:
	raise RuntimeError(
		"Config was not found. "
		"Please, specify {env_var} environment variable".format(
			env_var=const.ENV_CONFIG
		)
	)
config = Config(config_path)

config_path = os.environ.get(const.ENV_LOGGING_CONFIG, None)
if config_path is None:
	raise RuntimeError(
		"Logging config was not found. "
		"Please, specify {env_var} environment variable".format(
			env_var=const.ENV_LOGGING_CONFIG
		)
	)
setup_logging(config_path)

