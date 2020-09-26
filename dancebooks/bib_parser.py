# coding: utf-8
import concurrent.futures
import datetime
import enum
import logging
import multiprocessing
import os.path

import markdown

from dancebooks.config import config
from dancebooks import const
from dancebooks import index as search_index
from dancebooks import utils

class Availability(enum.Enum):
	Unavailable = "unavailable"
	AvailableElsewhere = "available-elsewhere"
	AvailableHere = "available-here"

	@staticmethod
	def from_url(single_url, item):
		if utils.is_url_self_served(single_url):
			return Availability.AvailableHere
		else:
			return Availability.AvailableElsewhere


class FinalizingContext:
	"""
	Contains objects required for finalizing parsed data set
	"""
	def __init__(self, index):
		self._markdown = markdown.Markdown(
			output_format="xhtml5"
		)
		self._markdown.inlinePatterns.add("cite", utils.MarkdownCite(index), "_end")

	def parse_markdown(self, data):
		self._markdown.reset()
		#erasing added <p> tags
		return self._markdown.convert(data)\
			.replace("<p>", "")\
			.replace("</p>", "")


class BibItem:
	"""
	Class representing a bibliography item
	"""
	KEY_TO_DEFAULT_VALUE = {
		"year_from": 0,
		"added_on": datetime.date(1970, 1, 1),
		"author": [],
		"location": [],
		"source": "",
		"series": "",
		"number": 0,
		"serial_number": 0
	}

	@staticmethod
	def key_to_key_func(key):
		default = BibItem.KEY_TO_DEFAULT_VALUE[key]
		return lambda item, key=key, default=default: item.get(key) or default

	def __init__(self):
		self._params = {
			"all_fields": "",
			"availability": set([Availability.Unavailable])
		}

	def __hash__(self):
		return hash(self.get("id"))

	# ancillary fields
	def booktype(self):
		return self.get_as_string("booktype")

	def id(self):
		return self.get_as_string("id")

	def source(self):
		return self.get_as_string("source")

	# data fields
	def author(self):
		return self.get_as_string("author")

	def shorthand(self):
		return self.get_as_string("shorthand")

	def title(self):
		return self.get_as_string("title")

	def incipit(self):
		return self.get_as_string("incipit")

	def publisher(self):
		return self.get_as_string("publisher")

	def series(self):
		return self.get_as_string("series")

	def number(self):
		return self.get_as_string("number")

	def edition(self):
		return self.get_as_string("edition")

	def volume(self):
		return self.get_as_string("volume")

	def volumes(self):
		return self.get_as_string("volumes")

	def location(self):
		return self.get_as_string("location")

	def year(self):
		return self.get_as_string("year")

	def keywords(self):
		return self.get_as_string("keywords")

	def url(self):
		return self.get_as_string("url")

	def filename(self):
		return self.get_as_string("filename")

	def note(self):
		return self.get_as_string("note")

	def added_on(self):
		return self.get_as_string("added_on")

	#not-implemented params
	#
	#type (thesis type)
	#institution
	#isbn
	#pages
	#crossref
	#booktitle
	#origlanguage
	#translator
	#commentator
	#editor

	@staticmethod
	def value_to_string(value, sep=","):
		if isinstance(value, str):
			return value
		elif isinstance(value, (list, set)):
			return (sep + " ").join(map(str, value))
		elif isinstance(value, datetime.datetime):
			return value.strftime(config.parser.date_format)
		else:
			return str(value)

	# getters / setters
	def get_as_string(self, key):
		if key in self._params:
			value = self._params[key]
			return BibItem.value_to_string(value)
		else:
			return None

	def get(self, key):
		return self._params.get(key, None)

	def has(self, key):
		return (key in self._params)

	def set(self, key, value):
		if key in self._params:
			raise RuntimeError(f"Can't set {key} twice for item {self.id()}")
		self._params[key] = value
		#TODO: move to finalize_item()
		self._params["all_fields"] += BibItem.value_to_string(value, "")
		#warning handling value in a dirty unconfigured way
		if key == "url":
			self._params["availability"] = set([
				Availability.from_url(single_url, self)
				for single_url in value
			])

	def params(self):
		return self._params

	def fields(self):
		return set(self._params.keys())

	def finalize_item(self):
		self.set("cite_label", utils.make_cite_label(self))

	def finalize_item_set(self, ctx):
		"""
		Method to be called once after parsing every entries.
		Processes crossref tag, merging _params of current entry and parent one
		"""
		note = self.get("note")
		if note is not None:
			#TODO: create converter once per item set, not once per item
			#parsing markdown and removing paragraph markup added by parser
			new_note = ctx.parse_markdown(note)\
				.replace("<p>", "")\
				.replace("</p>", "")
			self._params["note"] = new_note

		#crossref processing inherits some of the parameters
		#and therefore it should go last
		crossref = self.get("crossref")
		if crossref is not None:
			self._params["crossref"] = ctx.parse_markdown("[" + crossref + "]")\
				.replace("<p>", "")\
				.replace("</p>", "")

class ParserState(enum.Enum):
	NoItem = 0
	WaitingForType = 1
	WaitingForId = 2
	ReadingId = 3
	WaitingForCommaAfterId = 4
	WaitingForKey = 5
	ReadingKey = 6
	WaitingForEq = 7
	WaitingForParenthesis = 8
	ReadingValue = 9
	DoneReadingValue = 10


class BibParser:
	"""
	Class for parsing .bib files, folders and multiline strings
	"""

	def __init__(self):
		"""
		Default ctor
		"""
		self.state = ParserState.NoItem
		self.key = ""
		self.lexeme = ""

	def raise_error(self):
		"""
		Raises human-readable Exception based on parser state and current file position
		"""
		raise ValueError(f"In state={self.state}: wrong syntax at (line {self.line}, #{self.char})")

	def set_item_param(self, item, key, value):
		"""
		Sets item param, applying additional conversion if needed.
		"""
		try:
			if key in config.parser.list_params:
				value = utils.strip_split_list(value, config.parser.list_sep)
			elif key in config.parser.file_list_params:
				value = utils.strip_split_list(value, config.parser.list_sep)
				filesize_value = []
				for single_filename in value:
					abspath = os.path.join(config.www.elibrary_dir, single_filename)
					if os.path.isfile(abspath):
						filesize_value.append(os.path.getsize(abspath))
					else:
						logging.warn(f"File is not accessible: {abspath}")
						filesize_value.append(0)
				item.set(const.FILE_SIZE_PARAM, filesize_value)
			elif key in config.parser.keyword_list_params:
				value = utils.strip_split_list(value, config.parser.list_sep)
			elif (key in config.parser.int_params) and value.isdecimal():
				value = int(value)
			elif key in config.parser.year_params:
				(year_from, year_to, year_circa) = utils.parse_year(value)
				item.set(key + config.parser.start_suffix, year_from)
				item.set(key + config.parser.end_suffix, year_to)
				item.set(key + config.parser.circa_suffix, year_circa)
			elif key in config.parser.date_params:
				value = datetime.datetime.strptime(value, config.parser.date_format)

		except ValueError:
			self.raise_error()

		item.set(key, value)

	@staticmethod
	def parse_folder(path):
		"""
		Parses all .bib files in given folder.
		Returns a tuple (parsed_iten, search_index) containing all items found
		"""
		if not os.path.isdir(path):
			raise Exception("Path to folder expected")

		parsed_items = []
		files = utils.search_in_folder(path, lambda path: path.endswith(".bib"))
		executor = concurrent.futures.ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())
		futures = [
			executor.submit(
				BibParser()._parse_file,
				os.path.join(path, filename)
			)
			for filename in files
		]
		for future in futures:
			parsed_items += future.result()
		executor.shutdown()

		parsed_items = list(sorted(
			parsed_items,
			key=BibItem.key_to_key_func(const.DEFAULT_ORDER_BY)
		))
		item_index = search_index.Index(parsed_items)
		fin_ctx = FinalizingContext(item_index)
		for item in parsed_items:
			item.finalize_item_set(fin_ctx)
		item_index.update(parsed_items)
		return (parsed_items, item_index)

	def _parse_file(self, path):
		"""
		Parses file at given path, handling utf-8-bom correctly.
		@returns list of parsed BibItem
		"""
		if not os.path.isfile(path):
			raise Exception("Path to file expected")

		data = utils.read_utf8_file(path)
		try:
			source_file = os.path.basename(path)
			items = self._parse_string(data)
			for item in items:
				source_line = item.get("source_line")
				self.set_item_param(item, "source_file", source_file)
				self.set_item_param(item, "source", f"{source_file}:{source_line:04d}")
			return items
		except Exception as ex:
			raise Exception(f"While parsing {path}: {ex!r}")

	def _parse_string(self, data):
		"""
		Returns list of parsed BibItem
		"""
		item = BibItem()
		items = []
		self.line = 1
		self.char = 1
		for c in data:
			if c == os.linesep:
				self.line += 1
				self.char = 0
			else:
				self.char += 1

			if self.state == ParserState.NoItem:
				if c == "@":
					self.state = ParserState.WaitingForType
				#anything else is a comment

			elif self.state == ParserState.WaitingForType:
				if c.isspace():
					self.raise_error()
				elif c == '(':
					if not self.lexeme:
						#empty item type is not allowed
						self.raise_error()
					self.set_item_param(item, "booktype", self.lexeme.lower())
					self.set_item_param(item, "source_line", self.line)
					self.state = ParserState.WaitingForId
					self.lexeme = ""
				else:
					self.lexeme += c
			#TODO: add 'ReadingType' state

			elif self.state == ParserState.WaitingForId:
				if c.isspace():
					continue
				elif c.isidentifier():
					self.state = ParserState.ReadingId
					self.lexeme += c
				else:
					self.raise_error()

			elif self.state == ParserState.ReadingId:
				if c.isspace():
					self.set_item_param(item, "id", self.lexeme)
					self.state = ParserState.WaitingForCommaAfterId
					self.lexeme = ""
				elif c == ',':
					self.set_item_param(item, "id", self.lexeme)
					self.state = ParserState.WaitingForKey
					self.lexeme = ""
				else:
					self.lexeme += c

			elif self.state == ParserState.WaitingForCommaAfterId:
				if c.isspace():
					continue
				elif c == ',':
					self.state = ParserState.WaitingForKey
				else:
					self.raise_error()

			elif self.state == ParserState.WaitingForKey:
				if c.isspace():
					continue
				elif c.isidentifier():
					self.state = ParserState.ReadingKey
					self.lexeme += c
				else:
					self.raise_error()

			elif self.state == ParserState.ReadingKey:
				if c.isspace():
					self.state = ParserState.WaitingForEq
					self.key = self.lexeme
					self.lexeme = ""
				elif c == '=':
					self.state = ParserState.WaitingForParenthesis
					self.key = self.lexeme
					self.lexeme = ""
				else:
					self.lexeme += c

			elif self.state == ParserState.WaitingForEq:
				if c.isspace():
					continue
				elif c == '=':
					self.state = ParserState.WaitingForParenthesis
				else:
					self.raise_error()

			elif self.state == ParserState.WaitingForParenthesis:
				if c.isspace():
					continue
				elif c == '{':
					self.state = ParserState.ReadingValue
				else:
					self.raise_error()

			elif self.state == ParserState.ReadingValue:
				if c == '}':
					#WARN: value can be empty here in case of "key = {}" syntax
					self.set_item_param(item, self.key, self.lexeme)
					self.state = ParserState.DoneReadingValue
					self.key = ""
					self.lexeme = ""
				else:
					self.lexeme += c

			elif self.state == ParserState.DoneReadingValue:
				if c.isspace():
					continue
				elif c == ')':
					item.finalize_item()
					items.append(item)
					item = BibItem()
					self.state = ParserState.NoItem
				elif c == ',':
					self.state = ParserState.WaitingForKey
				else:
					self.raise_error()

			else:
				self.raise_error()

		#giant for cycle ends here
		return items
