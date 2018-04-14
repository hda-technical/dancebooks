import collections
import configparser
import enum
import functools
import json
import logging.config
import os
import subprocess

import const

class WorkingMode(enum.Enum):
	Unittest="unittest"
	Development="development"
	Testing="testing"
	Production="production"

def get_config_value(
	key,
	params,
	transform=None,
	check=None
):
	"""
	Retrieves non-optional config field,
	transforming it of necessary
	"""
	if key not in params:
		raise ValueError("{key} param wasn't found".format(
			key=key
		))
	value = params[key]
	if transform is not None:
		value = transform(value)
	if check is not None:
		if not check(value):
			raise ValueError("Check failed for {key}={value}".format(
				key=key,
				value=value
			))
	return value


def extract_set_from_json(value):
	return set(json.loads(value))


def make_ordered_json_extractor():
	decoder = json.JSONDecoder(object_pairs_hook=collections.OrderedDict)
	return lambda value, decoder=decoder: decoder.decode(value)


class SmtpConfig(object):
	def __init__(self, params):
		self.host = get_config_value("host", params)
		self.port = get_config_value("port", params, transform=int)
		self.user = get_config_value("user", params)
		self.password = get_config_value("password", params)
		self.email = get_config_value("email", params)


class BugReportConfig(object):
	def __init__(self, params):
		self.to_addr = get_config_value("to_addr", params)
		self.to_name = get_config_value("to_name", params)


class ParserConfig(object):
	def __init__(self, params):
		#some directories
		self.bibdata_dir = get_config_value(
			"bibdata_dir",
			params,
			transform=os.path.abspath,
			check=os.path.isdir
		)
		self.markdown_dir = get_config_value(
			"markdown_dir",
			params,
			transform=os.path.abspath,
			check=os.path.isdir
		)

		#field type specification
		self.list_params = get_config_value("list_params", params, transform=extract_set_from_json)
		self.file_list_params = get_config_value("file_list_params", params, transform=extract_set_from_json)
		self.keyword_list_params = get_config_value("keyword_list_params", params, transform=extract_set_from_json)
		self.int_params = get_config_value("int_params", params, transform=extract_set_from_json)
		self.year_params = get_config_value("year_params", params, transform=extract_set_from_json)
		self.date_params = get_config_value("date_params", params, transform=extract_set_from_json)
		self.bool_params = get_config_value("bool_params", params, transform=extract_set_from_json)

		#other values
		self.list_sep = get_config_value("list_sep", params)
		self.date_format = get_config_value("date_format", params)
		self.blocked_domains = get_config_value("blocked_domains", params, transform=extract_set_from_json)
		self.blocked_domains_http = get_config_value("blocked_domains_http", params, transform=extract_set_from_json)
		self.domains_allowed_301 = get_config_value("domains_allowed_301", params, transform=extract_set_from_json)

		#keywords param is loaded from a single config value,
		#but is splitted into a number of config fields with predictable meaning
		keywords = get_config_value("keywords", params, transform=make_ordered_json_extractor())
		self.keywords = set()
		self.category_keywords = collections.OrderedDict()
		for category, cat_keywords in keywords.items():
			self.category_keywords[category] = list()
			for keyword in cat_keywords:
				self.keywords.add(keyword)
				self.category_keywords[category].append(keyword)

		self.bookkeepers = get_config_value("bookkeepers", params, transform=json.loads)

		#suffixes parsing
		self.start_suffix = get_config_value("start_suffix", params)
		self.end_suffix = get_config_value("end_suffix", params)
		self.circa_suffix = get_config_value("circa_suffix", params)

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
		#domains
		self.app_domain = get_config_value("app_domain", params)
		self.app_domain_production = get_config_value("app_domain_production", params)

		#paths
		self.books_prefix = "/books"
		self.basic_search_prefix = "/basic-search"
		self.advanced_search_prefix = "/advanced-search"
		self.all_fields_search_prefix = "/all-fields-search"

		self.search_params = get_config_value("search_params", params, transform=extract_set_from_json)
		self.search_synonyms = get_config_value("search_synonyms", params, transform=json.loads)
		self.index_params = get_config_value("index_params", params, transform=extract_set_from_json)
		self.inverted_index_params = get_config_value("inverted_index_params", params, transform=extract_set_from_json)
		self.index_unique_params = get_config_value(
			"index_unique_params",
			params,
			transform=extract_set_from_json,
			check=(lambda value, index_params=self.index_params: value.issubset(index_params))
		)
		self.indexed_search_params = self.search_params & self.index_params
		self.nonindexed_search_params = self.search_params - self.index_params
		self.languages = get_config_value("languages", params, transform=json.loads)
		self.date_formats = get_config_value("date_formats", params, transform=json.loads)
		self.order_by_keys = get_config_value("order_by_keys", params, transform=extract_set_from_json)
		self.elibrary_dir = get_config_value(
			"elibrary_dir",
			params,
			check=os.path.isdir
		)
		self.backup_dir = get_config_value(
			"backup_dir",
			params
		)

		#security params
		self.secret_cookie_key = get_config_value("secret_cookie_key", params)
		self.secret_cookie_value = get_config_value("secret_cookie_value", params)
		secret_question_keys = get_config_value("secret_question_keys", params, transform=json.loads)
		secret_question_answers = get_config_value("secret_question_answers", params, transform=json.loads)
		self.secret_questions = {
			key: answer
			for key, answer in zip(
				secret_question_keys,
				secret_question_answers
			)
		}

		self.id_redirections = get_config_value("id_redirections", params, transform=json.loads)

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
				fallback_path = os.path.join(
					os.path.dirname(path),
					config["DEFAULT"]["fallback"]
				)
				fallback = configparser.ConfigParser()
				fallback.read(fallback_path)
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

		cfg_basename = os.path.basename(path)
		m = const.CONFIG_REGEXP.match(cfg_basename)
		if m is None:
			raise ValueError("Config basename {basename} doesn't match CONFIG_REGEXP".format(
				basename=cfg_basename
			))
		self.working_mode = WorkingMode(m.group("mode"))


def setup_logging(config_path):
	logging.config.fileConfig(config_path)

config_path = os.environ.get(const.ENV_CONFIG, None)
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

