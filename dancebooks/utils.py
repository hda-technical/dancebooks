import codecs
import copy
import cProfile
import csv
import functools
import http.client
import io
import itertools
import logging
import os
import os.path
import pstats
import re
from urllib import parse as urlparse

import requests

from dancebooks.config import config
from dancebooks import const
from dancebooks import search

SELF_SERVED_PATTERN = r"/books/(?P<item_id>[\w_]+)"

SELF_SERVED_URL_PATTERN = (
	SELF_SERVED_PATTERN +
	r"/pdf/(?P<pdf_index>\d+)"
)
SELF_SERVED_URL_REGEXP = re.compile(SELF_SERVED_URL_PATTERN)

SELF_SERVED_TRANSCRIPTION_PATTERN = (
	SELF_SERVED_PATTERN +
	r"/transcription/(?P<transcription_index>\d+)"
)
SELF_SERVED_TRANSCRIPTION_REGEXP = re.compile(SELF_SERVED_TRANSCRIPTION_PATTERN)

def strip_split_list(value, sep):
	"""
	Splits string on a given separator, strips spaces from resulting words
	"""
	return list(
		filter(
			None,
			(word.strip() for word in value.split(sep))
		)
	)


def require(condition, ex):
	"""
	Raises ex if condition is False.
	Just a piece of syntax sugar
	"""
	if (not condition):
		raise ex


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

			result = func(*args, **kwargs)

			profiler.disable()
			string_io = io.StringIO()
			stats = pstats.Stats(profiler, stream=string_io).sort_stats(sort)
			stats.print_stats(limits)
			print(string_io.getvalue())
			return result
		return wrapper
	return profile_decorator


def search_in_folder(path, filter, excludes={}):
	"""
	Iterates over folder yielding files matching pattern
	"""
	results = []
	for entry in os.scandir(path):
		abspath = os.path.join(path, entry.name)
		if filter(abspath):
			results.append(abspath)
		elif entry.is_dir() and entry.name not in excludes:
			results += search_in_folder(abspath, filter, excludes)
	return results


class FileMetadata(dict):
	def __init__(self):
		self.incomplete = False


def extract_metadata_from_file(path):
	"""
	Extracts dictionary with the following fields:

	* year (interval)
	* language (string)
	* author ([string])
	* title (string)
	* volume (integer)
	* number (string)
	* edition (integer)
	* part (integer)
	* keywords ([string])
	"""
	basename = os.path.basename(path)
	match = const.FILENAME_REGEXP.match(basename)
	if not match:
		raise ValueError(f"Filename {basename} does not match FILENAME_REGEXP")

	year = match.group("year")
	year_from = int(year.replace("-", "0"))
	year_to = int(year.replace("-", "9"))

	result = FileMetadata()
	result["year_from"] = year_from
	result["year_to"] = year_to
	result["langid"] = const.SHORT_LANG_MAP[match.group("langid")]

	PLAIN_PARAMS = {"volume", "edition", "part", "title"}
	for param in PLAIN_PARAMS:
		value = match.group(param)
		if value is None:
			continue
		if param in config.parser.int_params:
			result[param] = int(value)
		else:
			result[param] = value

	if number := match.group("number1"):
		result["number"] = number.lstrip("0")
	if number := match.group("number2"):
		result["number"] = number.lstrip("0")

	author = match.group("author")
	if author := match.group("author"):
		result["author"] = strip_split_list(author, ",")

	if keywords := match.group("keywords"):
		result["keywords"] = set()
		for keyword in strip_split_list(keywords, ","):
			if keyword.startswith("incomplete "):
				result.incomplete = True
				keyword = keyword[len("incomplete ")]
			# no else, as 'incomplete NLR copy' is a valid keyword
			if keyword.endswith(" copy"):
				for owner in config.parser.bookkeepers:
					if keywords.startswith(owner):
						result["owner"] = owner
			else:
				result["keywords"].add(keyword)
	return result


def make_searches_from_metadata(metadata):
	"""
	Creates dict: {
		search_alias_key: callable applicable to an item
	},
	checking if this item match given metadata
	"""
	result = {}


	if edition := metadata.get("edition"):
		result["edition"] = search.search_for_eq("edition", edition)

	if part := metadata.get("part"):
		result["part"] = search.search_for_eq("part", part)

	if number := metadata.get("number"):
		result["number"] = search.or_([
			search.search_for_eq("number", number),
			search.search_for_eq("serial_number", number)
		])

	subset_searches = ["langid"]
	for search_key in subset_searches:
		search_value = metadata.get(search_key)
		if search_value is None:
			continue
		result[search_key] = search.search_for_any(
			search_key,
			search_value
		)

	synonym_searches = ["author"]
	for search_key in synonym_searches:
		search_value = metadata.get(search_key)
		if search_value is None:
			continue
		synonym_keys = config.www.search_synonyms.get(search_key) + [search_key]
		result[search_key] = search.search_for_synonyms(synonym_keys, search_value)

	date_searches = ["year_from", "year_to"]
	for search_key in date_searches:
		search_value = metadata.get(search_key)
		if search_value is None:
			continue
		result[search_key] = search.search_for(
			search_key,
			search_value
		)

	synonym_prefix_searches = ["title"]
	for search_key in synonym_prefix_searches:
		search_value = metadata.get(search_key)
		if search_value is None:
			continue
		synonym_keys = config.www.search_synonyms.get(search_key) + [search_key]
		regexp = re.compile("^" + re.escape(search_value))
		result[search_key] = search.or_([
			search.search_for_string_regexp(synonym, regexp)
			for synonym in synonym_keys
		])

	volume = metadata.get("volume")
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


def is_url_self_served(url):
	return "/pdf/" in url


def is_url_local(url):
	return url.startswith("/")


def get_file_info_from_url(url, item):
	"""
	Returns tuple (file_name, file_size)
	"""
	match = SELF_SERVED_URL_REGEXP.match(url)
	require(
		match,
		ValueError(f"Received url ({url}) doesn't match SELF_SERVED_URL_REGEXP")
	)
	extracted_id = match.group("item_id")
	extracted_index = int(match.group("pdf_index")) - 1
	require(
		extracted_id == item.id,
		ValueError(f"Extracted item_id ({extracted_id}) doesn't match item id ({item.id}")
	)
	require(
		(extracted_index >= 0) and (extracted_index < len(item.get("filename"))),
		ValueError(f"Extracted pdf index ({extracted_index}) isn't in filename list boundaries")
	)
	return (
		item.get("filename")[extracted_index],
		item.get("filesize")[extracted_index]
	)


def is_url_valid(url, item):
	"""
	Validates urls by a number of checks
	"""
	if is_url_local(url):
		return True
	split = urlparse.urlsplit(url)
	if split.scheme not in ("http", "https"):
		logging.debug(f"Scheme {split.scheme!r} is wrong")
		return False
	if not split.netloc:
		logging.debug("Network location isn't specified")
		return False

	host = split.hostname

	# normalize host
	host_normailized = host.removeprefix("www.")

	# validating blocked domains
	if host_normailized in config.parser.blocked_domains:
		logging.debug(f"{host=} is blocked")
		return False

	if re := const.URL_REGEXPS.get(host):
		match = re.match(url)
		if not match:
			logging.debug(f"URL {url} should match {re.pattern}")
			return False

	# validating domains blocked for insecure (http) access
	# FIXME: this is a deprecated solution for the case, rewrite using URL_REGEXP
	if (
		(host in config.parser.blocked_domains_http) and
		(split.scheme == "http")
	):
		logging.debug(f"{host=} is blocked for insecure access")
		return False

	return True


def is_url_accessible(url, item, method="HEAD"):
	"""
	Checks url accessibility via HTTP request.
	Tries to perform HTTP HEAD request, and if it fails with
	status=405 (method not allowed) retries it with HTTP GET
	"""
	if is_url_self_served(url):
		return True

	RETRIES = 3
	HEADERS = {
		"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:51.0) Gecko/20100101 Firefox/51.0"
	}

	try:
		for n_try in range(RETRIES):
			if method == "HEAD":
				response = requests.head(url, allow_redirects=False, verify=True, headers=HEADERS)
			elif method == "GET":
				response = requests.get(url, allow_redirects=False, verify=True, headers=HEADERS)
			else:
				raise ValueError(f"Unexpected method {method}")
			if response.status_code not in (
				http.client.INTERNAL_SERVER_ERROR,
				http.client.SERVICE_UNAVAILABLE
			):
				#retrying in case of server error
				#retrying in
				break
	except Exception as ex:
		logging.debug(f"HTTP request for {url} raised an exception: {ex!r}")
		return False
	if (
		# some libraries (e. g. lib.ugent.be return strange errors for HEAD requests
		(response.status_code in (
			http.client.FORBIDDEN,
			http.client.NOT_FOUND,
			http.client.METHOD_NOT_ALLOWED
		)) and
		(method == "HEAD")
	):
		return is_url_accessible(url, item, method="GET")
	is_valid = (
		(response.status_code in const.VALID_HTTP_CODES) or
		(
			(response.status_code == http.client.MOVED_PERMANENTLY) and
			(urlparse.urlsplit(url).hostname in config.parser.domains_allowed_301)
		)
	)
	if not is_valid:
		logging.debug(f"HTTP request for {url} returned code {response.status_code}: {response.reason}")
		return False

	return True


YEAR_REGEXP = re.compile(r"(?P<year_from>\d+)(?:[-–—]+(?P<year_to>\d+)(?P<circa>\?)?)?")
def parse_year(year):
	"""
	Returns (year_from, year_to, circa) tuple
	"""
	match = YEAR_REGEXP.match(year)
	if not match:
		raise ValueError(f"Failed to parse year {year}")

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
	Returns first item in a container
	"""
	return next(iter(iterable))


def batched(iterable, size):
	"""
	Batches input iterable, producing batches of size (or less) items
	"""
	sourceiter = iter(iterable)
	while True:
		batchiter = itertools.islice(sourceiter, size)
		# When sourceiter becames empty,
		# islice returns empty iterator (without raising StopIteration)
		#
		# Invoking next on batchiter in order to raise StopIteration when needed
		yield [next(batchiter)] + list(batchiter)


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


def pretty_print_file_size(size):
	"""
	Returns string containing pretty printed file size
	"""
	unit_index = 0
	while (size > const.FILE_SIZE_EXPONENT):
		unit_index += 1
		size /= const.FILE_SIZE_EXPONENT
	unit = const.FILE_SIZE_UNITS[unit_index]
	return f"{size:0.1f} {unit}"


def isfile_case_sensitive(abspath):
	"""
	Checks if file exists using case-sensitive path.
	Makes sense only on Windows / Cygwin
	"""
	if not os.path.isfile(abspath):
		return False
	path = copy.copy(abspath)
	while path != '/':
		path, basename = os.path.split(path)
		if basename not in os.listdir(path):
			return False
	return True


def render_to_csv(items):
	fields = ["author", "title", "edition", "location", "year", "url"]
	stream = io.StringIO()
	writer = csv.DictWriter(stream, fieldnames=fields)
	writer.writeheader()
	for item in items:
		writer.writerow({
			field: item.get_as_string(field) or ""
			for field in fields
		})
	return stream.getvalue()


def get_last_name(fullname):
	return fullname.split()[-1]


def make_cite_label(item):
	"""
	Returns citation label formatted according to GOST-2008
	bibliography style in square brackets
	"""
	shorthand = item.get("shorthand")
	author = item.get_heuristical_authors()
	year = item.get("year")
	langid = item.get("langid")
	if (author is None) and (shorthand is None):
		raise ValueError("Can't make cite label without author or shorthand")
	if shorthand:
		return f"[{shorthand}, {year}]"
	elif len(author) <= const.MAX_AUTHORS_IN_CITE_LABEL:
		### WARN: this code doesn't process repeated surnames in any way
		surnames = ", ".join(map(get_last_name, author))
		return f"[{surnames}, {year}]"
	else:
		if langid == "russian":
			postfix = "и др."
		else:
			postfix = "et al."
		surnames = ", ".join(map(get_last_name, author[0:const.MAX_AUTHORS_IN_CITE_LABEL]))
		return f"[{surnames}, {postfix}, {year}]"


def make_html_cite(item):
	"""
	Returns full citation, formatted according to some simple style
	"""
	result = ""
	author = item.get_heuristical_authors()
	langid = item.get("langid")
	title = item.get("title") or item.get("incipit")
	location = item.get("location")
	booktitle = item.get("booktitle")
	journaltitle = item.get("journaltitle")
	number = item.get("number")
	year = item.get("year")
	if author:
		result += "<em>"
		result += ", ".join(author[0:const.MAX_AUTHORS_IN_CITE_LABEL])
		if len(author) > const.MAX_AUTHORS_IN_CITE_LABEL:
			result += " "
			result += "и др." if langid == "russian" else "et al."
		result += "</em>"
	result += " "
	result += title
	if booktitle is not None:
		result += " // " + booktitle
	if journaltitle is not None:
		result += " // " + journaltitle
		if number is not None:
			result += " №" + str(number)
	result += ". "
	if location:
		#location is a list
		result += ", ".join(location)
		result += ", "
	result += year
	result += ". "
	result += f'<a href="/books/{item.id}">https://{config.www.app_domain}/books/{item.id}</a>'
	return result


from pytrovich.detector import PetrovichGenderDetector
from pytrovich.enums import Case, Gender, NamePart
from pytrovich.maker import PetrovichDeclinationMaker

PYTR_DETECTOR = PetrovichGenderDetector()
PYTR_DECLINATOR = PetrovichDeclinationMaker()
PREDEFINED_SURNAMES_PYTROVICH = {
	("Бонч", Gender.MALE): "Бонч",
	("Бонч", Gender.FEMALE): "Бонч",
}

def make_genitive(nominative):

	def has_cyrillic(text):
		return bool(re.search('[\u0400-\u04FF]', text))

	def decline_first_name(name, *, gender):
		return PYTR_DECLINATOR.make(NamePart.FIRSTNAME, gender, Case.GENITIVE, name)

	def decline_middle_name(name, *, gender):
		return PYTR_DECLINATOR.make(NamePart.MIDDLENAME, gender, Case.GENITIVE, name)

	def decline_last_name(last, *, gender):
		parts = []
		# handle doubled last-names
		for part in last.split('-'):
			if predefined := PREDEFINED_SURNAMES_PYTROVICH.get((part, gender)):
				parts.append(predefined)
			else:
				declined = PYTR_DECLINATOR.make(NamePart.LASTNAME, gender, Case.GENITIVE, part)
				parts.append(declined)
		return "-".join(parts)

	if not has_cyrillic(nominative):
		return nominative

	lexemes = nominative.split()
	if len(lexemes) == 1:
		# only {lastname}
		gender = PYTR_DETECTOR.detect(lastname=lexemes[0])
		last = decline_last_name(lexemes[0], gender=gender)
		return last
	elif len(lexemes) == 2:
		# {firstname} {lastname}
		gender = PYTR_DETECTOR.detect(firstname=lexemes[0])
		first = decline_first_name(lexemes[0], gender=gender)
		last = decline_last_name(lexemes[1], gender=gender)
		return f"{first} {last}"
	elif len(lexemes) == 3:
		# {firstname} {middlename} {lastname}
		gender = PYTR_DETECTOR.detect(firstname=lexemes[0])
		first = decline_first_name(lexemes[0], gender=gender)
		middle = decline_middle_name(lexemes[1], gender=gender)
		last = decline_last_name(lexemes[2], gender=gender)
		return f"{first} {middle} {last}"
	else:
		raise ValueError(f"Unsupported name length for {nominative}")
