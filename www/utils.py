import codecs
import copy
import cProfile
import fnmatch
import functools
import io
import logging
import os
import pstats
import re
from urllib import parse as urlparse

import requests

from config import config
import const
import search

#can't move this to const.py due to cyclic references
SELF_SERVED_URL_PATTERN = (
	"https://" +
	re.escape(config.www.app_domain_production) +
	re.escape(config.www.books_prefix) +
	r"/(?P<item_id>[\w_]+)/pdf/(?P<pdf_index>\d+)"
)
SELF_SERVED_URL_REGEXP = re.compile(SELF_SERVED_URL_PATTERN)

def strip_split_list(value, sep):
	"""
	Splits string on a given separator, strips spaces from resulting words
	"""
	return [word.strip() for word in value.split(sep)]


def require(condition, ex):
	"""
	Raises ex if condition is False.
	Just a piece of syntax sugar
	"""
	if (not condition):
		raise ex


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
	* volume (integer)
	* number (integer)
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

	volume = match.group("volume")
	if volume is not None:
		result["volume"] = int(volume)

	edition = match.group("edition")
	if edition is not None:
		result["edition"] = int(edition)

	part = match.group("part")
	if part is not None:
		result["part"] = int(part)

	number = match.group("number")
	if number is not None:
		result["number"] = int(number)

	keywords = match.group("keywords")
	if keywords is not None:
		result["keywords"] = set()
		for keyword in strip_split_list(keywords, ","):
			if (keyword == const.META_INCOMPLETE):
				result["keywords"].add(const.META_INCOMPLETE)
			if (keyword.endswith(" copy")):
				owner = keyword.split()[0]
				if (
					(owner in const.KNOWN_LIBRARIES) or
					(owner in const.KNOWN_BOOKKEEPERS)
				):
					result["keywords"].add(const.META_HAS_OWNER)

	return result


def make_searches_from_metadata(metadata):
	"""
	Creates dict: {
		search_aliaskey: callable applicable to an item
	},
	checking if this item match given metadata
	"""
	result = {}

	equality_searches = ["author", "edition", "number", "part", "langid"]
	for search_key in equality_searches:
		search_value = metadata.get(search_key, None)
		if search_value is None:
			continue
		result[search_key] = search.search_for_eq(
			search_key,
			search_value
		)

	date_searches = ["year_from", "year_to"]
	for search_key in date_searches:
		search_value = metadata.get(search_key, None)
		result[search_key] = search.search_for(
			search_key,
			search_value
		)

	title = metadata["title"]
	title_regexp = re.compile("^" + re.escape(title))
	search_for_itemtitle = search.search_for_string_regexp("title", title_regexp)
	search_for_booktitle = search.search_for_string_regexp("booktitle", title_regexp)
	result["title"] = search.or_([search_for_itemtitle, search_for_booktitle])

	volume = metadata.get("volume", None)
	if volume is not None:
		search_for_volume = search.search_for_optional_eq(
			"volume",
			volume
		)
		search_for_volumes = search.search_for_integer_ge(
			"volumes",
			volume
		)
		result["volume"] = search.or_([search_for_volume, search_for_volumes])
	return result

def all_or_none(iterable):
	return all(iterable) or not any(iterable)


def is_url_self_served(url, item):
	match = SELF_SERVED_URL_REGEXP.match(url)
	if not match:
		return False
	extracted_id = match.group("item_id")
	return (extracted_id == item.id())


def get_file_info_from_url(url, item):
	"""
	Returns tuple (file_name, file_size)
	"""
	match = SELF_SERVED_URL_REGEXP.match(url)
	require(
		match,
		ValueError("Received url ({url}) doesn't match SELF_SERVED_URL_REGEXP".format(
			url=url
		))
	)
	extracted_id = match.group("item_id")
	extracted_index = int(match.group("pdf_index")) - 1
	require(
		extracted_id == item.id(),
		ValueError("Extracted item_id ({extracted}) doesn't match item id ({received}".format(
			extracted=extracted_id,
			received=item.id()
		))
	)
	require(
		(extracted_index >= 0) and (extracted_index < len(item.get("filename"))),
		ValueError("Extracted pdf index ({extracted_index}) isn't in filename list boundaries".format(
			extracted_index=extracted_index
		))
	)
	return (
		item.get("filename")[extracted_index],
		item.get("filesize")[extracted_index]
	)


def is_url_valid(url, item):
	"""
	Validates urls by a number of checks
	"""
	split_result = urlparse.urlsplit(url)
	if len(split_result.scheme) == 0:
		logging.debug("Schemes isn't specified")
		return False
	elif len(split_result.netloc) == 0:
		logging.debug("Network location isn't specified")
		return False
	elif len(split_result.fragment) != 0:
		logging.debug("Fragments aren't allowed")
		return False

	#validating blocked domains
	if split_result.hostname in config.parser.blocked_domains:
		logging.debug("Domain {hostname} is blocked".format(
			hostname=split_result.hostname
		))
		return False

	#validating domains blocked for insecure (http) access
	if (
		(split_result.hostname in config.parser.blocked_domains_http) and
		(split_result.scheme == "http")
	):
		logging.debug("Domain {hostname} is blocked for insecure access".format(
			hostname=split_result.hostname
		))
		return False

	return True


def is_url_accessible(url, item):
	"""
	Checks url accessibility via HTTP HEAD request
	"""
	if is_url_self_served(url, item):
		return True

	response = requests.head(url, allow_redirects=False, verify=True)
	if (response.status_code not in const.VALID_HTTP_CODES):
		logging.debug("HTTP HEAD request for url {url} returned code {code}: {reason}".format(
			url=url,
			code=response.status_code,
			reason=response.reason
		))

	return True


ISBN_REGEXP = re.compile("[^\dX]")
def is_isbn_valid(isbn):
	"""
	Validates ISBN-10 and ISBN-13.
	Returns tuple containing validation result and error message
	"""
	def check_digit_isbn_10(isbn):
		sum = 0
		require(
			len(isbn) == 9,
			RuntimeError("Input should contain exactly 9 digits")
		)
		for i, c in enumerate(isbn):
			w = i + 1
			sum += w * int(c)
		r = sum % 11
		return (str(r) if (r != 10) else "X")

	def check_digit_isbn_13(isbn):
		sum = 0
		require(
			len(isbn) == 12,
			RuntimeError("Input should control exactly 12 digits")
		)
		for i, c in enumerate(isbn):
			w = 3 if (i % 2 != 0) else 1
			sum += w * int(c)
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
		logging.debug("ISBN format is not known")
		return False

	if check != right_check:
		logging.debug("Check digit should be {right_check}".format(
			right_check=right_check
		))
		return False

	return True, ""

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
	with open(path, "rb") as input_file:
		data = input_file.read()
		#trimming utf-8 byte order mark
		if data.startswith(codecs.BOM_UTF8):
			return data[len(codecs.BOM_UTF8):].decode()
		else:
			return data.decode()


def first(iterable):
	"""
	Returns first item in a containter
	"""
	return next(iter(iterable))


def extract_parent_keyword(keyword):
	"""
	Extracts parent keyword from keyword.
	Returns input value if no KEYWORD_SEPARATOR was found
	"""
	colon_pos = keyword.find(":")
	if colon_pos != -1:
		parent_candidate = keyword[:colon_pos]
		if parent_candidate in config.parser.keywords:
			return parent_candidate
	#no parent can be extracted
	return keyword


def pretty_print_file_size(size_value):
	"""
	Returns string containing pretty printed file size
	"""
	size_unit_index = 0
	while (size_value > const.FILE_SIZE_EXPONENT):
		size_unit_index += 1
		size_value /= const.FILE_SIZE_EXPONENT
	return "{size:0.1f} {unit}".format(
		size=size_value,
		unit=const.FILE_SIZE_UNITS[size_unit_index]
	)


def isfile_case_sensitive(abspath):
	"""
	Checks if file exists using case-sensive path
	"""
	if not os.path.isfile(abspath):
		return False
	path = copy.copy(abspath)
	while path != '/':
		path, basename = os.path.split(path)
		if basename not in os.listdir(path):
			return False
	return True

