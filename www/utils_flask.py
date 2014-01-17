import jinja2



class MemoryCache(jinja2.BytecodeCache):
	def __init__(self):
		self.cache = dict()

	def load_bytecode(self, bucket):
		if bucket.key in self.cache:
			bucket.bytecode_from_string(self.cache[bucket.key])
	
	def dump_bytecode(self, bucket):
		self.cache[bucket.key] = bucket.bytecode_to_string()
