import codecs
import cProfile
import functools
import io
import os
import fnmatch
import pstats
import re
from urllib import parse as urlparse

import requests

from config import config
import const
import search

def strip_split_list(value, sep):
	"""
	Splits string on a given separator, strips spaces from resulting words
	"""
	return [word.strip() for word in value.split(sep)]


LATEX_REPLACEMENTS = [
	#\url{href}
	(
		re.compile(r"\\url\{([^\s]*)\}"),
		r'<a href="\1">\1</a>'
	),
	#\parencite{book_id}
	(
		re.compile(r"\\parencite\{([a-z_\d]*)\}"),
		r'<a href="{0}/\1">\1</a>'.format(
			config.www.app_prefix + "/book"
		)
	),
	#ampersand escapements
	(
		re.compile(r"\\&"),
		"&"
	),
	#parentheses
	(
		re.compile(r"\{([^\{\}]*)\}"),
		r"\1"
	)
]

def parse_latex(value):
	"""
	Attempts to remove LaTeX formatting from string
	"""
	if isinstance(value, str):
		for regexp, subst in LATEX_REPLACEMENTS:
			value = regexp.sub(subst, value)
		return value
	else:
		return value


def profile(sort="time", limits=50):
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


def files_in_folder(path, pattern, excludes={}):
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

def extract_metadata_from_file(path):
	"""
	Extracts dictionary contating the following fields:
	
	* year (interval)
	* language (string)
	* author ([string])
	* title (string)
	* tome (integer)
	* edition (integer)
	* part (integer)
	* keywords ([string])
	"""
	basename = os.path.basename(path)
	match = const.FILENAME_REGEXP.match(basename)
	if not match:
		raise ValueError("Filename {path} didn't match FILENAME_REGEXP".format(
			path=path
		))

	year = match.group("year")
	year_from = int(year.replace("-", "0"))
	year_to = int(year.replace("-", "9"))
	
	result = {
		"year_from": year_from, 
		"year_to": year_to,
		"langid": const.SHORT_LANG_MAP[match.group("langid")],
		"title": match.group("title")
	}
	
	author = match.group("author")
	if author is not None:
		result["author"] = strip_split_list(author, ",")
		
	tome = match.group("tome")
	if tome is not None:
		result["tome"] = int(tome)
	
	edition = match.group("edition")
	if edition is not None:
		result["edition"] = int(edition)
	
	part = match.group("part")
	if part is not None:
		result["part"] = int(part)
	
	keywords = match.group("keywords")
	if keywords is not None:
		result["keywords"] = set(strip_split_list(keywords, ","))
	
	return result
	
	
def create_search_from_metadata(metadata):
	"""
	Creates callable applicable to an item, 
	checing if this item match given metadata
	"""
	langid = metadata["langid"]
	year_from = metadata["year_from"]
	year_to = metadata["year_to"]
	title = metadata["title"]
	author = metadata.get("author", None)
	tome = metadata.get("tome", None)
	edition = metadata.get("edition", None)
	part = metadata.get("part", None)
	#keywords = metadata.get("keywords", None)
	
	title_regexp = re.compile("^" + re.escape(title))
	
	search_for_langid = search.search_for_eq("langid", langid)
	search_for_year = search.and_([
		search.search_for("year_from", year_from),
		search.search_for("year_to", year_to)
	])
	
	search_for_itemtitle = search.search_for_string_regexp("title", title_regexp)
	search_for_booktitle = search.search_for_string_regexp("booktitle", title_regexp)
	search_for_title = search.or_([search_for_itemtitle, search_for_booktitle])
	
	searches = [
		search_for_langid,
		search_for_year,
		search_for_title,
	]
	
	if author is not None:
		search_for_author = search.search_for_eq(
			"author", 
			author
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
		
	if part is not None:
		search_for_part = search.search_for_eq(
			"part",
			part
		)
		searches.append(search_for_part)

	#keywords aren't counted
	
	return search.and_(searches)
	
	
def all_or_none(iterable):
	return all(iterable) or not any(iterable)
	

def is_url_valid(url, check_head=False):
	"""
	Validates urls.
	Returns tuple containing validation result and error message
	"""
	try:
		split_result = urlparse.urlsplit(url)
		if len(split_result.scheme) == 0:
			return False, "Scheme isn't specified"
		elif len(split_result.netloc) == 0:
			return False, "Netloc isn't specified"
		elif len(split_result.fragment) != 0:
			return False, "Fragments aren't allowed"
		
		if check_head:
			response = requests.head(url, allow_redirects=False, verify=False)
			if (response.status_code not in const.VALID_HTTP_CODES):
				return False, "HTTP HEAD request returned code {code}: {reason}".format(
					code=response.status_code,
					reason=response.reason
				)
	except Exception as ex:
		return False, "Exception occured: {ex}".format(
			ex=ex
		)
	return True, "URL is correct"
		
ISBN_REGEXP = re.compile("[^\dX]")
def is_isbn_valid(isbn):
	"""
	Validates ISBN-10 and ISBN-13.
	Returns tuple containing validation result and error message
	"""
	def check_digit_isbn_10(isbn):
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
	
	def check_digit_isbn_13(isbn):
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
	
YEAR_REGEXP = re.compile(r"(?P<year_from>\d+)(?:[-–—]+(?P<year_to>\d+)(?P<circa>\?)?)?")
def parse_year(year):
	"""
	Returns (year_from, year_to, circa) tuple
	"""
	match = YEAR_REGEXP.match(year)
	if not match:
		raise ValueError("Failed to parse year {year}".format(year=year))
	
	year_from = match.group("year_from")
	year_from = int(year_from)
	
	year_to = match.group("year_to")
	if year_to is not None:
		year_to = int(year_to)
	else:
		year_to = year_from
	
	circa = match.group("circa") is not None
	
	return (year_from, year_to, circa)

	
def read_utf8_file(path):
	with open(path, "r+b") as input_file:
		data = input_file.read()
		#trimming utf-8 byte order mark
		if data.startswith(codecs.BOM_UTF8):
			return data[len(codecs.BOM_UTF8):].decode()
		else:
			return data.decode()

