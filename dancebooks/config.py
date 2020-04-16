import collections
import functools
import logging.config
import os

import pyjson5

from dancebooks import const

class SmtpConfig:
	def __init__(self, params):
		self.host = params["host"]
		self.port = params["port"]
		self.user = params["user"]
		self.password = params["password"]
		self.email = params["email"]


class BugReportConfig:
	def __init__(self, params):
		self.to_addr = params["to_addr"]
		self.to_name = params["to_name"]


class ParserConfig:
	def __init__(self, params):
		#some directories
		repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
		self.bibdata_dir = os.path.join(repo_root, params["bibdata_dir"])
		self.markdown_dir = os.path.join(repo_root, params["markdown_dir"])

		#field type specification
		self.list_params = set(params["list_params"])
		self.file_list_params = set(params["file_list_params"])
		self.keyword_list_params = set(params["keyword_list_params"])
		self.int_params = set(params["int_params"])
		self.year_params = set(params["year_params"])
		self.date_params = set(params["date_params"])
		self.bool_params = set(params["bool_params"])

		#other values
		self.list_sep = params["list_sep"]
		self.date_format = params["date_format"]
		self.blocked_domains = set(params["blocked_domains"])
		self.blocked_domains_http = set(params["blocked_domains_http"])
		self.domains_allowed_301 = set(params["domains_allowed_301"])

		#keywords param is loaded from a single config value,
		#but is splitted into a number of config fields with predictable meaning
		keywords = params["keywords"]
		self.keywords = set()
		self.category_keywords = collections.OrderedDict()
		for category, cat_keywords in keywords.items():
			self.category_keywords[category] = list()
			for keyword in cat_keywords:
				self.keywords.add(keyword)
				self.category_keywords[category].append(keyword)

		self.bookkeepers = params["bookkeepers"]

		#suffixes parsing
		self.start_suffix = params["start_suffix"]
		self.end_suffix = params["end_suffix"]
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


class WwwConfig:
	def __init__(self, params):
		self.app_domain = params["app_domain"]

		self.search_params = set(params["search_params"])
		self.search_synonyms = params["search_synonyms"]
		self.index_params = set(params["index_params"])
		self.inverted_index_params = set(params["inverted_index_params"])
		self.index_unique_params = set(params["index_unique_params"])
		self.indexed_search_params = self.search_params & self.index_params
		self.nonindexed_search_params = self.search_params - self.index_params
		self.languages = params["languages"]
		self.date_formats = params["date_formats"]
		self.order_by_keys = set(params["order_by_keys"])
		self.elibrary_dir = params["elibrary_dir"]
		self.backup_dir = params["backup_dir"]
		self.backup_metadata_url = params["backup_metadata_url"]

		#security params
		self.secret_cookie_key = params["secret_cookie_key"]
		self.secret_cookie_value = params["secret_cookie_value"]
		self.secret_questions = params["secret_questions"]
		self.id_redirections = params["id_redirections"]


class DatabaseConfig:
	def __init__(self, params):
		self.host = params["host"]
		self.port = params["port"]
		self.user = params["user"]
		self.password = params["password"]
		self.database_name = params["database_name"]
		self.options = params["options"]

	@property
	def connection_string(self):
		#TODO: handle self.options
		return (
			f"host={self.host} port={self.port} "
			f"user={self.user} password={self.password} "
			f"dbname={self.database_name}"
		)

	@property
	def connection_url(self):
		return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database_name}"


class Config:
	def __init__(self, path):
		with open(path, "rt") as config_file:
			json_config = pyjson5.load(config_file)
		#handling secrets
		if "secrets" in json_config:
			secrets_path = os.path.join(os.path.dirname(path), json_config["secrets"])
			with open(secrets_path, "rt") as secrets_json_file:
				secrets_config = pyjson5.load(secrets_json_file)
			for key, value in secrets_config.items():
				if key in json_config:
					json_config[key].update(value)
				else:
					json_config[key] = value

		self.smtp = SmtpConfig(json_config["smtp"])
		self.bug_report = BugReportConfig(json_config["bug_report"])
		self.parser = ParserConfig(json_config["parser"])
		self.www = WwwConfig(json_config["www"])
		self.db = DatabaseConfig(json_config["db"])
		self.unittest_mode = "DANCEBOOKS_UNITTEST" in os.environ


def setup_logging(config_path):
	logging.config.fileConfig(config_path)

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs/dancebooks.json")
config = Config(config_path)

DEFAULT_LOGGING_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs/logger.development.conf")
logging_config_path = os.environ.get(const.ENV_LOGGING_CONFIG, DEFAULT_LOGGING_PATH)
setup_logging(logging_config_path)
