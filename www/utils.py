import codecs
import cProfile
import functools
from http import client as httpclient
import io
import os
import fnmatch
import pstats
import re
from urllib import parse as urlparse

from config import config
import const
import search

def strip_split_list(value: str, sep: str) -> [str]:
	"""
	Splits string on a given separator, strips spaces from resulting words
	"""
	return [word.strip() for word in value.split(sep)]


LATEX_GROUPING_REGEXP = re.compile(r"(\s|^)\{([^\s]*)\}(\s|$)")
LATEX_URL_REGEXP = re.compile(r"\\url\{([^\s]*)\}")
LATEX_PARENCITE_REGEXP = re.compile(r"\\parencite\{([a-z_\d]*)\}")
PARENCITE_SUBST = r'[<a href="{0}/\1">\1</a>]'.format(config.www.app_prefix + "/book")
def parse_latex(value: str) -> str:
	"""
	Attempts to remove LaTeX formatting from string
	"""
	if isinstance(value, str):
		value = value.replace(r"\&", "&")
		value = LATEX_GROUPING_REGEXP.sub(r"\1\2\3", value)
		value = LATEX_URL_REGEXP.sub(r'<a href="\1">\1</a>', value)
		value = LATEX_PARENCITE_REGEXP.sub(PARENCITE_SUBST, value)
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

def extract_metadata_from_file(path: str) -> {"str": str}:
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
		"year": (year_from, year_to),
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
	
	
def create_search_from_metadata(metadata: {"str": str}) -> callable:
	"""
	Creates callable applicable to an item, 
	checing if this item match given metadata
	"""
	langid = metadata["langid"]
	year = metadata["year"]
	title = metadata["title"]
	author = metadata.get("author", None)
	tome = metadata.get("tome", None)
	edition = metadata.get("edition", None)
	part = metadata.get("part", None)
	#keywords = metadata.get("keywords", None)
	
	title_regexp = re.compile("^" + re.escape(title))
	
	search_for_langid = search.search_for_eq("langid", langid)
	search_for_year = search.and_([
		search.search_for("year_from", year[0]),
		search.search_for("year_to", year[1])
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
	
	
def all_or_none(iterable: "iterable") -> (bool, str):
	return all(iterable) or not any(iterable)

	
def head_request(scheme: str, host: str, path: str) -> int:
	"""
	Performs HTTP head request and returns response code
	"""
	if (scheme == "http"):
		connection = httpclient.HTTPConnection(host)
	elif (scheme == "https"):
		connection = httpclient.HTTPSConnection(host)
	else:
		raise ValueError("Scheme {scheme} is not supported".format(
			scheme=scheme
		))
	connection.request("HEAD", urlparse.quote(path))
	response = connection.getresponse()
	return response.status, response.reason



def is_url_valid(url: str, check_head: bool = False) -> (bool, str):
	"""
	Validates urls.
	Returns tuple containing validation result and error message
	"""
	try:
		parse_result = urlparse.urlparse(url)
		if len(parse_result.scheme) == 0:
			return False, "Scheme isn't specified"
		elif len(parse_result.netloc) == 0:
			return False, "Netloc isn't specified"
		elif len(parse_result.fragment) != 0:
			return False, "Fragments aren't allowed"
		
		if check_head:
			code, reason = head_request(
				parse_result.scheme,
				parse_result.hostname,
				parse_result.path
			)
			if code not in const.VALID_HTTP_CODES:
				return False, "HTTP HEAD request returned code {code}: {reason}".format(
					code=code,
					reason=reason
				)
	except Exception as ex:
		return False, "Exception occured: {ex}".format(
			ex=ex
		)
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

