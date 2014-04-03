import email
import email.mime
import email.mime.text
import logging
import smtplib
import queue
import threading

class Message(object):
	def __init__(self, book_id, from_addr, from_name, text):
		self.from_addr = from_addr
		self.from_name = from_name
		self.text = text
		self.book_id = book_id

	def __str__(self):
		return (
			"Message for book {book_id} "
			"from {from_name} <{from_addr}>: {text}".format(
				book_id=self.book_id,
				from_name=self.from_name,
				from_addr=self.from_addr,
				text=self.text
			)
		)


class Messenger(object):
	"""
	Class capable of batch message-sending
	"""
	def __init__(self, cfg):
		self.cfg = cfg
		self.messages = queue.Queue()
		self.send_thread = threading.Thread(target=self.send_routine, daemon=True)
		self.send_thread.start()

	def teardown(self):
		self.messages.put(None)
		self.send_thread.join()

	def send(self, message):
		self.messages.put(message)

	def send_routine(self):
		messages = []
		shutdown = False
		while not shutdown:
			send_now = False
			try:
				message = self.messages.get(timeout=self.cfg.bug_report.timeout)
				if message is None:
					send_now = True
					shutdown = True
				else:
					messages.append(message)

				if len(messages) >= self.cfg.bug_report.max_count:
					send_now = True

			except queue.Empty:
				send_now = True

			if not send_now:
				continue
			
			if len(messages) == 0:
				continue

			logging.info("Messenger: going to send {count} messages".format(
				count=len(messages)
			))
			text = "\n\n".join(map(str, messages))
			messages = []
			

			try:
				msg = email.mime.text.MIMEText(text)
				msg["From"] = email.utils.formataddr((
					self.cfg.bug_report.from_name, 
					self.cfg.bug_report.from_addr
				))
				msg["To"] = email.utils.formataddr((
					self.cfg.bug_report.to_name, 
					self.cfg.bug_report.to_addr
				))
				msg["Subject"] = "[dancebooks-bibtex] Error reports".format(id=id)
				recipients = [self.cfg.bug_report.to_addr]

				smtp = smtplib.SMTP(self.cfg.smtp.host, self.cfg.smtp.port)
				if self.cfg.smtp.user and self.cfg.smtp.password:
					smtp.login(self.cfg.smtp.user, self.cfg.smtp.password)
				smtp.sendmail(self.cfg.smtp.email, recipients, msg.as_string())
		
			except Exception as ex:
				logging.exception("Messenger: exception occured. {ex}".format(
					ex=ex
				))
