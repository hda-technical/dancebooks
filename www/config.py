import configparser

class SmtpConfig(object):
	def __init__(self, params):
		if "Host" not in params:
			raise ValueError("Host param wasn't found")
		self.host = params["Host"]

		if "Port" not in params:
			raise ValueError("Port param wasn't found")
		self.port = int(params["Port"])

		if "User" not in params:
			raise ValueError("User param wasn't found")
		self.user = params["User"]

		if "Password" not in params:
			raise ValueError("Password param wasn't found")
		self.password = params["Password"]

		if "Email" not in params:
			raise ValueError("Email param wasn't found")
		self.email = params["Email"]


class BugReportConfig(object):
	def __init__(self, params):
		if "ToAddr" not in params:
			raise ValueError("ToAddr param wasn't found")
		self.to_addr = params["ToAddr"]

		if "ToName" not in params:
			raise ValueError("ToName param wasn't found")
		self.to_name = params["ToName"]
		
		if "FromAddr" not in params:
			raise ValueError("FromAddr param wasn't found")
		self.from_addr = params["FromAddr"]

		if "FromName" not in params:
			raise ValueError("FromName param wasn't found")
		self.from_name = params["FromName"]
		
		if "Timeout" not in params:
			raise ValueError("Timeout param wasn't found")
		self.timeout = int(params["Timeout"])

		if "MaxCount" not in params:
			raise ValueError("MaxCount param wasn't found")
		self.max_count = int(params["MaxCount"])


class Config(object):
	def __init__(self, path):
		config = configparser.ConfigParser()
		config.read(path)

		if "SMTP" not in config:
			raise ValueError("SMTP section wasn't found")
		self.smtp = SmtpConfig(config["SMTP"])

		if "BUG_REPORT" not in config:
			raise ValueError("BUG_REPORT section wasn't found")
		self.bug_report = BugReportConfig(config["BUG_REPORT"])
