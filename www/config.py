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
		if "Email" not in params:
			raise ValueError("Email param wasn't found")
		self.email = params["Email"]

		if "Name" not in params:
			raise ValueError("Name param wasn't found")
		self.name = params["Name"]


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
