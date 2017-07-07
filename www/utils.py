import codecs
import copy
import cProfile
import csv
import fnmatch
import functools
import http.client
import io
import itertools
import logging
import os
import os.path
import pstats
import re
import threading
from urllib import parse as urlparse

import markdown
import pymorphy2
import requests

from config import config
import const
import search

SELF_SERVED_PATTERN = (
	"https://" +
	re.escape(config.www.app_domain_production) +
	re.escape(config.www.books_prefix) +
	r"/(?P<item_id>[\w_]+)"
)

SELF_SERVED_URL_PATTERN = (
	SELF_SERVED_PATTERN +
	"/pdf/(?P<pdf_index>\d+)"
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
	return [word.strip() for word in value.split(sep)]


def require(condition, ex):
	"""
	Raises ex if condition is False.
	Just a piece of syntax sugar
	"""
	if (not condition):
		raise ex


LATEX_UNPARSABLE_REGEXPS = [
	(
		re.compile(r"[^\\]&"),
		"Unescaped ampersands"
	),
	(
		re.compile(r"\\(?!(flat|&))"),
		"Unsupported latex command"
	)
]

LATEX_REPLACEMENTS = [
	(
		re.compile(r"\$\\flat\$"),
		r"♭"
	),
	#ampersand escapements
	(
		re.compile(r"\\&"),
		"&"
	)
]


def validate_latex(item, key, value):
	"""
	Checks if LaTeX marked up string can be parsed by pdflatex
	"""
	item_id = item.get("id")
	for regexp, what in LATEX_UNPARSABLE_REGEXPS:
		if regexp.search(value):
			logging.warning(
				"While parsing LaTeX for {key} of {item_id} got {what}".format(
					key=key,
					item_id=item_id,
					what=what
				)
			)


def parse_latex(value):
	"""
	Attempts to remove LaTeX formatting from string
	"""
	for regexp, subst in LATEX_REPLACEMENTS:
		value = regexp.sub(subst, value)
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

			result = func(*args, **kwargs)

			profiler.disable()
			string_io = io.StringIO()
			stats = pstats.Stats(profiler, stream=string_io).sort_stats(sort)
			stats.print_stats(limits)
			print(string_io.getvalue())
			return result
		return wrapper
	return profile_decorator


def files_in_folder(path, pattern, excludes={}):
	"""
	Iterates over folder yielding files matching pattern
	"""
	result_files = set()

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
				result_files.add(os.path.join(root, file_))

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
		raise ValueError("Filename {basename} does not match FILENAME_REGEXP".format(
			basename=basename
		))

	year = match.group("year")
	year_from = int(year.replace("-", "0"))
	year_to = int(year.replace("-", "9"))

	result = {
		"year_from": year_from,
		"year_to": year_to,
		"langid": const.SHORT_LANG_MAP[match.group("langid")]
	}

	PLAIN_PARAMS = {"volume", "edition", "part", "number", "title"}
	for param in PLAIN_PARAMS:
		value = match.group(param)
		if value is None:
			continue
		if (param in config.parser.int_params) and value.isdecimal():
			result[param] = int(value)
		else:
			result[param] = value

	author = match.group("author")
	if (author is not None):
		result["author"] = strip_split_list(author, ",")

	keywords = match.group("keywords")
	if keywords is not None:
		result["keywords"] = set()
		for keyword in strip_split_list(keywords, ","):
			if (keyword.endswith(" copy")):
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

	edition = metadata.get("edition")
	if edition is not None:
		result["edition"] = search.search_for_eq("edition", edition)
	part = metadata.get("part")
	if part is not None:
		result["part"] = search.search_for_eq("part", part)
	number = metadata.get("number")
	if number is not None:
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
		search_value = metadata.get(search_key, None)
		if search_value is None:
			continue
		synonym_keys = config.www.search_synonyms.get(search_key) + [search_key]
		result[search_key] = search.search_for_synonyms(synonym_keys, search_value)

	date_searches = ["year_from", "year_to"]
	for search_key in date_searches:
		search_value = metadata.get(search_key, None)
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
	split = urlparse.urlsplit(url)
	return (
		(split.hostname == config.www.app_domain_production) and
		("/pdf/" in split.path)
	)


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
		logging.debug("Scheme isn't specified")
		return False
	elif len(split_result.netloc) == 0:
		logging.debug("Network location isn't specified")
		return False
	elif len(split_result.fragment) != 0:
		logging.debug("Fragments aren't allowed")
		return False

	#validating blocked domains
	for blocked_domain in config.parser.blocked_domains:
		if split_result.hostname.endswith(blocked_domain):
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


def is_url_accessible(url, item, method="HEAD"):
	"""
	Checks url accessibility via HTTP request.
	Tries to perform HTTP HEAD request, and if it fails with
	status=405 (method not allowed) retries it with HTTP GET
	"""
	if is_url_self_served(url, item):
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
				raise ValueError("Unexpected method {method}".format(method=method))
			if response.status_code not in (
				http.client.INTERNAL_SERVER_ERROR,
				http.client.SERVICE_UNAVAILABLE
			):
				#retrying in case of server error
				#retrying in
				break
	except Exception as ex:
		logging.debug("HTTP request for {url} raised an exception: {ex}".format(
			url=url,
			ex=ex
		))
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
		logging.debug("HTTP request for {url} returned code {code}: {reason}".format(
			url=url,
			code=response.status_code,
			reason=response.reason
		))
		return False

	return True


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


class MarkdownCache(object):
	"""
	Class capable of caching markdown files in compiled HTML form
	(ready to be sent to client).

	Tracks file changing and recompiles files when necessary
	"""
	def __init__(self):
		self._lock = threading.Lock()
		#dict: file abspath -> (source file mtime, compiled html data)
		self._cache = dict()
		self._converter = markdown.Markdown(
			extensions=[
				"markdown.extensions.footnotes",
				"markdown.extensions.tables",
				"superscript",
				MarkdownPageNumberExtension()
			],
			extension_configs={
				"markdown.extensions.footnotes": {
					"PLACE_MARKER": "///Footnotes///",
					"BACKLINK_TEXT": "↑",
				}
			},
			output_format="xhtml5"
		)

	def get(self, abspath):
		"""
		Main entry point of the function.
		abspath is path to be read and compiled
		"""
		with self._lock:
			modified_at = os.path.getmtime(abspath)
			compiled_at, compiled_data = self._cache.get(abspath, (None, None))
			if (
				(compiled_at is not None) and
				(modified_at <= compiled_at)
			):
				return compiled_data
		compiled_data = self.compile(abspath)
		with self._lock:
			self._cache[abspath] = (modified_at, compiled_data)
		return compiled_data

	def compile(self, abspath):
		"""
		Helper function for performing compilation
		of a markdown file to HTML
		"""
		self._converter.reset()
		raw_data = read_utf8_file(abspath)
		return self._converter.convert(raw_data)


class MarkdownCiteProcessor(markdown.inlinepatterns.Pattern):
	def __init__(self, index):
		super().__init__(r"\[(?P<id>[a-z0-9_]+)\]")
		self._index = index

	def handleMatch(self, m):
		a = markdown.util.etree.Element("a")
		id = m.group("id")
		a.set("href", "/books/{id}".format(id=id))
		item = first(self._index["id"][id])
		a.text = item.get("cite_label")
		return a


class MarkdownCiteExtension(markdown.extensions.Extension):
	def __init__(self, index):
		self._index = index

	def extendMarkdown(self, md, md_globals):
		md.inlinePatterns.add("cite_reference", MarkdownCiteProcessor(self._index), '_end')


class MarkdownPageNumber(markdown.inlinepatterns.Pattern):
	def __init__(self):
		super().__init__(r"\{(?P<number>[^\{\}]+)\}")

	def handleMatch(self, m):
		span = markdown.util.etree.Element("span")
		span.set("class", const.PAGE_NUMBER_CSS_CLASS)
		span.text = m.group("number")
		return span


class MarkdownStikethrough(markdown.inlinepatterns.Pattern):
	def __init__(self):
		super().__init__(r"\~\~(?P<stokeout>[^\~]+)\~\~")

	def handleMatch(self, m):
		span = markdown.util.etree.Element("span")
		span.set("style", "text-decoration: line-through;")
		span.text = m.group("stokeout")
		return span


class MarkdownPageNumberExtension(markdown.extensions.Extension):
	def extendMarkdown(self, md, md_globals):
		md.inlinePatterns.add("page_number", MarkdownPageNumber(), '_end')
		md.inlinePatterns.add("strikethough", MarkdownStikethrough(), '_end')


def get_last_name(fullname):
	return fullname.split()[-1]


def make_cite_label(item):
	"""
	Returns citation label formatted according to GOST-2008
	bibliography style in square brackets
	"""
	shorthand = item.get("shorthand")
	author = item.get("author") or item.get("pseudo_author") or item.get("compiler")
	year = item.get("year")
	langid = item.get("langid")
	if (author is None) and (shorthand is None):
		raise ValueError("Can't make cite label without author or shorthand")
	if shorthand is not None:
		return '[{shorthand}, {year}]'.format(
			shorthand=shorthand,
			year=year
		)
	elif len(author) <= const.MAX_AUTHORS_IN_CITE_LABEL:
		### WARN: this code doesn't process repeated surnames in any way
		return '[{surnames}, {year}]'.format(
			surnames=", ".join(map(get_last_name, author)),
			year=year
		)
	else:
		if langid == "russian":
			postfix = "и др."
		else:
			postfix = "et al."
		return "[{surnames}, {postfix}, {year}]".format(
				surnames=", ".join(map(get_last_name, author[0:const.MAX_AUTHORS_IN_CITE_LABEL])),
				postfix=postfix,
				year=year
			)


def make_html_cite(item):
	"""
	Returns full citation, formatted according to some simple style
	"""
	result = ""
	author = item.get("author")
	langid = item.get("langid")
	title = item.get("title") or item.get("incipit")
	location = item.get("location")
	booktitle = item.get("booktitle")
	journaltitle = item.get("journaltitle")
	number = item.get("number")
	year = item.get("year")
	if author is not None:
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
	result += '<a href="{prefix}/{item_id}">{scheme}{domain}{prefix}/{item_id}</a>'.format(
		scheme="https://",
		domain=config.www.app_domain_production,
		prefix=config.www.books_prefix,
		item_id=item.id()
	)
	return result


morph_analyzer = pymorphy2.MorphAnalyzer()
def make_genitive(nominative):
	"""
	Accepts name in nominanive case, returns genivive case for it
	"""
	def process_lexeme(lexeme, gender):
		#NB: pymorphy can't process this specific surname properly.
		#    This crutch is intended to solve the problem.
		if lexeme == "Стратилатов":
			return ("Стратилатова", gender)
		variants = morph_analyzer.parse(lexeme)
		for variant in variants:
			if "nomn" in variant.tag:
				tags = {"gent"}
				if gender is not None:
					tags.add(gender)
				inflected = variant.inflect(tags).word
				if lexeme[0].isupper():
					return (inflected.capitalize(), variant.tag.gender)
				else:
					return (inflected, variant.tag.gender)
		#fall back to defaults when no matching variants were found
		return (lexeme, "masc")

	#special trick with gender definition is required for
	gender = None
	processed = []
	#pymorphy2 doesn't handle entire phrases - splitting into individual words
	for lexeme in nominative.split():
		#even though hyphen-separate surnames can be inflected properly without being split,
		#one needs to handle them individually in order to capitalize them
		sublexemes = lexeme.split('-')
		inflected_sublexemes = []
		for sublexeme in sublexemes:
			inflected_sublexeme, guessed_gender = process_lexeme(sublexeme, gender)
			if gender is None:
				gender = guessed_gender
			inflected_sublexemes.append(inflected_sublexeme)
		processed.append('-'.join(inflected_sublexemes))
	return " ".join(processed)
