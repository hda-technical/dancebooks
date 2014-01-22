import cProfile
import functools
import io
import os
import fnmatch
import pstats
import re

import constants

def strip_split_list(value: str, sep: str) -> [str]:
	"""
	Splits string on a given separator, strips spaces from resulting words
	"""
	return [word.strip() for word in value.split(sep)]


LATEX_GROUPING_RE = re.compile(r"(\s|^)\{([^\s]*)\}(\s|$)")
LATEX_URL_RE = re.compile(r"\\url\{([^\s]*)\}")
LATEX_PARENCITE_RE = re.compile(r"\\parencite\{([a-z_\d]*)\}")
PARENCITE_SUBST = r'[<a href="{0}/\1">\1</a>]'.format(constants.BOOK_PREFIX)
def parse_latex(value: str) -> str:
	"""
	Attempts to remove LaTeX formatting from string
	"""
	if isinstance(value, str):
		value = value.replace(r"\&", "&")
		value = LATEX_GROUPING_RE.sub(r"\1\2\3", value)
		#requires autoescape to be turned off
		#but this is a break in is security wall
		#value = LATEX_URL_RE.sub(r'<a href="\1">\1</a>', value)
		#value = LATEX_PARENCITE_RE.sub(PARENCITE_SUBST, value)
		return value
	else:
		return value


def profile(sort: str = "time", limits: str or int = 50) -> callable:
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
			stats.print_stats(limits)
			print(string_io.getvalue())
		return wrapper
	return profile_decorator


def files_in_folder(path: str, pattern: str, excludes: set = set()):
	"""
	Iterates over folder yielding files matching pattern
	"""
	result_files = []
	
	for root, dirs, files in os.walk(path):
		skip = False
		
		#processing excludes
		for excl in excludes:
			excl_with_sep = "/" + excl
			if excl_with_sep in root:
				skip = True
		if skip:
			continue
		
		for file_ in files:
			if fnmatch.fnmatch(file_, pattern):
				result_files.append(os.path.join(root, file_))

	return result_files
