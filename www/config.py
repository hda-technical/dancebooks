import configparser
import functools
import json
import os.path
import subprocess

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
		
		if "from_addr" not in params:
			raise ValueError("from_addr param wasn't found")
		self.from_addr = params["from_addr"]

		if "from_name" not in params:
			raise ValueError("from_name param wasn't found")
		self.from_name = params["from_name"]
		
		if "timeout" not in params:
			raise ValueError("timeout param wasn't found")
		self.timeout = int(params["timeout"])

		if "max_count" not in params:
			raise ValueError("max_count param wasn't found")
		self.max_count = int(params["max_count"])

		
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
		
		if "date_params" not in params:
			raise ValueError("date_params param wasn't found")
		self.date_params = set(json.loads(params["date_params"]))
		
		if "date_start_suffix" not in params:
			raise ValueError("date_start_suffix param wasn't found")
		self.date_start_suffix = params["date_start_suffix"]
		
		if "date_end_suffix" not in params:
			raise ValueError("date_end_suffix param wasn't found")
		self.date_end_suffix = params["date_end_suffix"]
		
		if "date_circa_suffix" not in params:
			raise ValueError("date_circa_suffix param wasn't found")
		self.date_circa_suffix = params["date_circa_suffix"]

		suffix_adder = lambda string, suffix: string + suffix
		self.date_start_params = set(map(
			functools.partial(suffix_adder, suffix=self.date_start_suffix),
			self.date_params
		))
		self.date_end_params = set(map(
			functools.partial(suffix_adder, suffix=self.date_end_suffix),
			self.date_params
		))
		

class WwwConfig(object):
	def __init__(self, params):
		if "app_prefix" not in params:
			raise ValueError("app_prefix param wasn't found")
		self.app_prefix = params["app_prefix"]
		
		if "search_params" not in params:
			raise ValueError("search_params param wasn't found")
		self.search_params = set(json.loads(params["search_params"]))
		
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

		if "secret_keywords" not in params:
			raise ValueError("secret_keywords wasn't found")
		self.secret_keywords = set(json.loads(params["secret_keywords"]))
		

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
		config = configparser.ConfigParser()
		config.read(path)
		
		fallback = None
		if "DEFAULT" in config:
			if "Fallback" in config["DEFAULT"]:
				path = os.path.join(
					os.path.dirname(path), 
					config["DEFAULT"]["Fallback"]
				)
				fallback = configparser.ConfigParser()
				fallback.read(path)

		self.smtp = SmtpConfig(Config.get_params(config, fallback, "SMTP"))
		self.bug_report = BugReportConfig(Config.get_params(config, fallback, "BUG_REPORT"))
		self.parser = ParserConfig(Config.get_params(config, fallback, "PARSER"))
		self.www = WwwConfig(Config.get_params(config, fallback, "WWW"))
		
		self.version = subprocess.check_output("git log | head -n 1 | cut -f 2 -d ' '", shell=True).decode().strip()
