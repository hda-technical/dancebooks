import email
import email.mime
import email.mime.text
import logging
import smtplib

import flask

from config import config

class BasicMessage(object):
	"""
	Basic message class capable of sending
	string replresentation of the self
	"""
	def send(self):
		try:
			msg = email.mime.text.MIMEText(str(self), "html")
			msg["From"] = email.utils.formataddr((
				self.from_name,
				self.from_addr
			))
			msg["To"] = email.utils.formataddr((
				config.bug_report.to_name,
				config.bug_report.to_addr
			))
			msg["Subject"] = self.subject()
			msg["Content-Type"] = "text/html"

			recipients = [config.bug_report.to_addr]

			#do not send data in unittest mode
			if config.unittest:
				return

			smtp = smtplib.SMTP(config.smtp.host, config.smtp.port)
			smtp.starttls()
			if config.smtp.user and config.smtp.password:
				smtp.login(config.smtp.user, config.smtp.password)
			smtp.sendmail(config.smtp.email, recipients, msg.as_string())

		except Exception as ex:
			logging.exception("Messenger: exception occured. {ex}".format(
				ex=ex
			))
			raise


class ErrorReport(BasicMessage):
	def __init__(self, book, from_addr, from_name, text):
		self.book = book
		self.from_addr = from_addr
		self.from_name = from_name
		self.text = text

	def __str__(self):
		return flask.render_template(
			"components/message-error-report.html",
			base_url="http://{app_domain}{book_prefix}".format(
				app_domain=config.www.app_domain,
				book_prefix=config.www.app_prefix + "/books"
			),
			book=self.book,
			from_name=self.from_name,
			from_addr=self.from_addr,
			text=self.text
		)

	def subject(self):
		return "dancebooks: Error reports for {id}".format(id=self.book.id())


class KeywordsSuggest(BasicMessage):
	def __init__(self, book, from_addr, from_name, keywords):
		self.book = book
		self.from_addr = from_addr
		self.from_name = from_name
		self.rendered_keywords = " | ".join(keywords)

	def __str__(self):
		return flask.render_template(
			"components/message-keywords-suggest.html",
			base_url="http://{app_domain}{book_prefix}".format(
				app_domain=config.www.app_domain,
				book_prefix=config.www.app_prefix + "/books"
			),
			book=self.book,
			from_name=self.from_name,
			from_addr=self.from_addr,
			rendered_keywords=self.rendered_keywords
		)

	def subject(self):
		return "dancebooks: Keywords suggestion for {id}".format(id=self.book.id())

