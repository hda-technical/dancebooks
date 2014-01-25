import cProfile
import functools
import io
import os
import fnmatch
import pstats
import re
from urllib import parse as urlparse

import constants
import search

def strip_split_list(value: str, sep: str) -> [str]:
	"""
	Splits string on a given separator, strips spaces from resulting words
	"""
	return [word.strip() for word in value.split(sep)]


LATEX_GROUPING_REGEXP = re.compile(r"(\s|^)\{([^\s]*)\}(\s|$)")
LATEX_URL_REGEXP = re.compile(r"\\url\{([^\s]*)\}")
LATEX_PARENCITE_REGEXP = re.compile(r"\\parencite\{([a-z_\d]*)\}")
PARENCITE_SUBST = r'[<a href="{0}/\1">\1</a>]'.format(constants.BOOK_PREFIX)
def parse_latex(value: str) -> str:
	"""
	Attempts to remove LaTeX formatting from string
	"""
	if isinstance(value, str):
		value = value.replace(r"\&", "&")
		value = LATEX_GROUPING_REGEXP.sub(r"\1\2\3", value)
		#requires autoescape to be turned off
		#but this is a break in is security wall
		#value = LATEX_URL_REGEXP.sub(r'<a href="\1">\1</a>', value)
		#value = LATEX_PARENCITE_REGEXP.sub(PARENCITE_SUBST, value)
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

#any of [incomplete, commentary, translation, facsimile]
METADATA_PATTERN = r"(?:(?:incomplete)|(?:commentary)|(?:translation)|(?:facsimile)|(?:transcription))"
FILANAME_PATTERN = (
	#year: digits can be replaced by dashes
	r"\[(?P<year>[\d\-]+), "
	#lang: two-letter code
	r"(?P<lang>\w{2})\] "
	#author: optional, can contain 
	#   spaces (Thomas Wilson),
	#   dots (N. Malpied),
	#   commas (Louis Pecour, Jacque Dezais)	
	#(question mark at the end makes regexp non-greedy)
	r"(?:(?P<author>[\w\s\.,'\-]+?) - )?"
	#title: sequence of words, digits, spaces, punctuation
	#(question mark at the end makes regexp non-greedy)
	r"(?P<title>[\w\d\s',\.\-–—&«»‹›„”№\(\)]+?)"
	#metadata: optional sequence of predefined values
	#   tome (, tome 2)
	#   edition (, edition 10)
	#   part(, partie 1)
	#	comma-separated list of METADATA_PATTERN in parentheses
	#   (something copy) — for books with multiple different copies known 
	r"(?:"
		r"(?:, tome (?P<tome>\d+))|"
		r"(?:, édition (?P<edition>\d+))|"
		r"(?:, partie \d+)|"
		r"(?: \(" + METADATA_PATTERN + r"(?:, " + METADATA_PATTERN + r")*\))|"
		r"(?: \([\w]+ copy\))"
	r")*"
	#extension: .pdf
	r"\.pdf"
)
FILENAME_REGEXP = re.compile(FILANAME_PATTERN)	
def extract_metadata_from_file(path: str) -> {"str": str}:
	"""
	Extracts dictionary contating the following fields:
	
	* year (interval)
	* language (string)
	* author ([string])
	* title (string)
	* tome (integer)
	* edition (integer)
	"""
	basename = os.path.basename(path)
	match = FILENAME_REGEXP.match(basename)
	if not match:
		raise ValueError("Filename {path} didn't match FILENAME_REGEXP".format(
			path=path
		))

	year = match.group("year")
	year_from = int(year.replace("-", "0"))
	year_to = int(year.replace("-", "9"))
	
	result = {
		"year": (year_from, year_to),
		"lang": constants.SHORT_LANG_MAP[match.group("lang")],
		"title": match.group("title")
	}
	
	author = match.group("author")
	if author is not None:
		result["author"] = strip_split_list(author, constants.OUTPUT_LISTSEP)
		
	tome = match.group("tome")
	if tome is not None:
		result["tome"] = int(tome)
	
	edition = match.group("edition")
	if edition is not None:
		result["edition"] = int(edition)
		
	return result
	
	
def create_search_from_metadata(metadata: {"str": str}) -> callable:
	"""
	Creates callable applicable to an item, 
	checing if this item match given metadata
	"""
	lang = metadata["lang"]
	year = metadata["year"]
	title = metadata["title"]
	author = metadata.get("author", None)
	tome = metadata.get("tome", None)
	edition = metadata.get("edition", None)
	
	title_regexp = re.compile("^" + re.escape(title))
	
	search_for_lang = search.search_for_eq("langid", lang)
	search_for_year = search.search_for_year(*year)
	
	search_for_itemtitle = search.search_for_string_regexp("title", title_regexp)
	search_for_booktitle = search.search_for_string_regexp("booktitle", title_regexp)
	search_for_title = search.or_([search_for_itemtitle, search_for_booktitle])
	
	searches = [
		search_for_lang,
		search_for_year,
		search_for_title,
	]
	
	if author is not None:
		search_for_author = search.search_for_iterable_set_exact(
			"author", 
			set(author)
		)
		searches.append(search_for_author)
	
	if tome is not None:
		search_for_volume = search.search_for_optional_eq(
			"volume",
			tome
		)
		search_for_volumes = search.search_for_integer_ge(
			"volumes",
			tome
		)
		searches.append(search.or_([search_for_volume, search_for_volumes]))
	
	if edition is not None:
		search_for_edition = search.search_for_eq(
			"edition",
			edition
		)
		searches.append(search_for_edition)
		
	return search.and_(searches)
	
	
def all_or_none(iterable: "iterable") -> bool:
	return all(iterable) or not any(iterable)
	

def is_url_valid(url: str) -> (bool, str):
	"""
	Validates urls.
	Returns tuple containing validation result and error message
	"""
	parse_result = urlparse.urlparse(url)
	if len(parse_result.scheme) == 0:
		return False, "Scheme isn't specified"
	elif len(parse_result.netloc) == 0:
		return False, "Netloc isn't specified"
	elif len(parse_result.fragment) != 0:
		return False, "Fragments aren't allowed"
	else:
		return True, "URL is correct"
	
	
ISBN_REGEXP = re.compile("[^\dX]")
def is_isbn_valid(isbn: str) -> (bool, str):
	"""
	Validates ISBN-10 and ISBN-13.
	Returns tuple containing validation result and error message
	"""
	def check_digit_isbn_10(isbn: str) -> str:
		sum = 0
		length = len(isbn)
		if length != 9:
			raise RuntimeError("Input should contain exactly 9 digits")
		for i in range(length):
			c = int(isbn[i])
			w = i + 1
			sum += w * c
		r = sum % 11
		return (str(r) if (r != 10) else "X")
	
	def check_digit_isbn_13(isbn: str) -> str:
		sum = 0
		length = len(isbn)
		if length != 12:
			raise RuntimeError("Input should control exactly 12 digits")
		for i in range(length):
			c = int(isbn[i])
			w = 3 if (i % 2 != 0) else 1
			sum += w * c
		r = 10 - (sum % 10)
		return str(r % 10)

	#function starts here
	isbn_clear = ISBN_REGEXP.sub("", isbn)
	length = len(isbn_clear)
	check, isbn_clear = isbn_clear[-1], isbn_clear[:-1]
	
	if length == 10:
		right_check = check_digit_isbn_10(isbn_clear)
	elif length == 13:
		right_check = check_digit_isbn_13(isbn_clear)
	else:
		return False, "ISBN is neither ISBN-10 or ISBN-13"
	
	if check != right_check:
		return False, "ISBN check digit is incorrect (should be {0})".format(
			right_check
		)
	
	return True, "ISBN is correct"