import cProfile, pstats, io
import functools
import re

import jinja2

import constants

def strip_split_list(value, sep):
	"""
	Splits string on a given sep(arator), strips spaces from resulting words
	"""
	return [word.strip() for word in value.split(sep)]


LATEX_GROUPING_RE = re.compile(r"(\s|^)\{([^\s]*)\}(\s|$)")
LATEX_URL_RE = re.compile(r"\\url\{([^\s]*)\}")
LATEX_PARENCITE_RE = re.compile(r"\\parencite\{([a-z_\d]*)\}")
PARENCITE_SUBST = r'[<a href="{0}/\1">\1</a>]'.format(constants.BOOK_PREFIX)
def parse_latex(value):
	"""
	Attempts to remove LaTeX formatting from string
	"""
	if isinstance(value, str):
		value = value.replace(r"\&", "&")
		value = LATEX_GROUPING_RE.sub(r"\1\2\3", value)
		value = LATEX_URL_RE.sub(r'<a href="\1">\1</a>', value)
		value = LATEX_PARENCITE_RE.sub(PARENCITE_SUBST, value)
		return value
	else:
		return value


class MemoryCache(jinja2.BytecodeCache):

	def __init__(self):
		self.cache = dict()

	def load_bytecode(self, bucket):
		if bucket.key in self.cache:
			bucket.bytecode_from_string(self.cache[bucket.key])
	
	def dump_bytecode(self, bucket):
		self.cache[bucket.key] = bucket.bytecode_to_string()


def profile(sort="time"):
	"""
	Decorator to make profiling easy
	"""
	def profile_decorator(func):
		"""
		Real decorator to be returned
		"""
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			profiler = cProfile.Profile()
			profiler.enable()

			func(*args, **kwargs)

			profiler.disable()
			string_io = io.StringIO()
			stats = pstats.Stats(profiler, stream=string_io).sort_stats(sort)
			stats.print_stats(50)
			print(string_io.getvalue())
		return wrapper
	return profile_decorator
