import email
import email.mime
import email.mime.text
import smtplib
import queue
import threading

class Message(object):
	def __init__(self, book_id, from_addr, from_name, text):
		self.from_addr = from_addr
		self.from_name = from_name
		self.text = text
		self.book_id = book_id


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

	@staticmethod
	def format_messages(messages):
		data = dict()
		for message in messages:
			if message.book_id in data:
				data[message.book_id].append(message)
			else:
				data[message.book_id] = [message]

		message_text = "" 
		for book_id in data:
			message_part = "Bug report for book {book_id}:\n".format(book_id=book_id)
			for message in data[book_id]:
				message_part += "From: {from_name} <{from_addr}>\n{text}\n\n".format(
					from_name=message.from_name,
					from_addr=message.from_addr,
					text=message.text
				)
				message_text += message_part
		return message_text


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

			message_text = self.format_messages(messages)
			messages = []

			msg = email.mime.text.MIMEText(message_text)
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
			
