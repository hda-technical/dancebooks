import flask
import jinja2
import werkzeug


XML_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>'

def xml_exception_handler(ex):
	"""
	Function converting Exception or HTTPException instance to xml response
	"""
	if isinstance(ex, werkzeug.exceptions.HTTPException):
		xml_error = '{decl}\n<error code="{code}" description="{description}">{msg}</error>'.format(
			decl=XML_DECLARATION,
			code=ex.code,
			description=ex.name,
			msg=ex.description
		)
		response = flask.make_response(xml_error, ex.code)
	elif isinstance(ex, Exception):
		xml_error = '{decl}\n<error code="{code}" description="{description}">{msg}</error>'.format(
			decl=XML_DECLARATION,
			code=500,
			description="Internal Server Error",
			msg=ex
		)
		response = flask.make_response(xml_error, 500)

	response.content_type = "text/xml; charset=utf-8"
	return response
	

class MemoryCache(jinja2.BytecodeCache):
	def __init__(self):
		self.cache = dict()

	def load_bytecode(self, bucket):
		if bucket.key in self.cache:
			bucket.bytecode_from_string(self.cache[bucket.key])
	
	def dump_bytecode(self, bucket):
		self.cache[bucket.key] = bucket.bytecode_to_string()
