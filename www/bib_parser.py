# coding: utf-8
import datetime
import logging
import os.path

from config import config
import const
import utils

class BibItem(object):
	"""
	Class for bibliography item representation
	"""
	KEY_TO_DEFAULT_VALUE = {
		"year_from": 0,
		"added_on": datetime.date(1970, 1, 1),
		"author": [],
		"location": [],
		"source": ""
	}

	@staticmethod
	def key_to_key_func(key):
		default = BibItem.KEY_TO_DEFAULT_VALUE[key]
		return lambda item, key=key, default=default: item.get(key) or default

	def __init__(self):
		self._params = {
			"all_fields": ""
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

	def annotation(self):
		return self.get_as_string("annotation")

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
			raise RuntimeError("Can't set the parameter '{key}' twice for item {id}".format(
				key=key,
				id=self._params.get("id", None)))
		self._params[key] = value
		self._params["all_fields"] += BibItem.value_to_string(value, "")

	def params(self):
		return self._params

	def process_crossrefs(self, index):
		"""
		Processes crossref tag, merges _params of currect entry and parent one
		"""
		crossref = self.get("crossref")
		if crossref is not None:
			parent = index["id"][crossref]
			if len(parent) == 0:
				raise ValueError("Crossref {crossref} was not found for item {id}".format(
					crossref=crossref,
					id=self.id()
				))
			parent = list(parent)[0]
			new_params = dict(parent.params())
			new_params.update(self._params)
			self._params = new_params


class BibParser(object):
	"""
	Class for parsing .bib files, folders and multiline strings
	"""
	ITEM_OPEN_BRACKET = "("
	ITEM_CLOSE_BRACKET = ")"
	FIELD_SEP = ","
	KEY_VALUE_SEP = "="

	STATE = \
		(S_NO_ITEM, S_ITEM_TYPE, S_ITEM_NO_ID, S_PARAM_KEY, S_PARAM_VALUE, S_PARAM_READ) = \
		(0,         1,           2,            3,           4,             5)

	def __init__(self):
		"""
		Default ctor
		"""
		self.state = self.S_NO_ITEM
		self._reset_lexeme()

	def state_string(self):
		"""
		Returns human-readable error message
		"""
		if self.state == self.S_NO_ITEM:
			return "looking for item"
		elif self.state == self.S_ITEM_TYPE:
			return "looking for item type"
		elif self.state == self.S_ITEM_NO_ID:
			return "looking for item id"
		elif self.state == self.S_PARAM_KEY:
			return "looking for parameter key"
		elif self.state == self.S_PARAM_VALUE:
			return "looking for parameter [{0}] value".format(self.key)
		elif self.state == self.S_PARAM_READ:
			return "looking for next parameter / item end"

	def raise_error(self):
		"""
		Raises human-readable Exception based on parser state and current file position
		"""
		raise ValueError("While {state}: wrong syntax at (line {line}, #{char})".format(
			state=self.state_string(),
			line=self.line,
			char=self.char
		))

	def _reset_lexeme(self):
		"""
		Resets some internal parser variables
		"""
		self.lexeme = ""
		self.lexeme_started = False
		self.lexeme_finished = False
		self.parenthesis_depth = 0
		self.lexeme_in_brackets = False

	def set_item_param(self, item, key, value):
		"""
		Sets item param, applying additional conversion if needed.
		"""
		value = utils.parse_latex(value)

		try:
			if key in config.parser.list_params:
				value = utils.strip_split_list(value, config.parser.list_sep)
			elif key in config.parser.file_list_params:
				value = utils.strip_split_list(value, config.parser.list_sep)
				filesize_value = []
				for single_filename in value:
					#filenames start from slash, trimming it
					abspath = os.path.join(config.www.elibrary_root, single_filename[1:])
					filesize_value.append(os.path.getsize(abspath))
				item.set(const.FILE_SIZE_PARAM, filesize_value)
			elif key in config.parser.int_params:
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

	def parse_folder(self, path):
		"""
		Parses all .bib files in given folder.
		Returns list containing all items found
		"""
		if not os.path.isdir(path):
			raise Exception("Path to folder expected")

		parsed_items = []
		files = utils.files_in_folder(path, "*.bib")
		for filename in files:
			parsed_items += self.parse_file(os.path.join(path, filename))
		return parsed_items

	def parse_file(self, path):
		"""
		Parses file at given path, handling utf-8-bom correctly.
		@returns list of parsed BibItem
		"""
		if not os.path.isfile(path):
			raise Exception("Path to file expected")

		data = utils.read_utf8_file(path)
		try:
			source_file = os.path.basename(path)
			items = self.parse_string(data)
			for item in items:
				self.set_item_param(item, "source_file", source_file)
				self.set_item_param(item, "source", "{source_file}:{source_line:04d}".format(
					source_file=source_file,
					source_line=item.get("source_line"))
				)
			return items
		except Exception as ex:
			raise Exception("While parsing {0}: {1}".format(path, ex))

	def parse_string(self, str_data):
		"""
		Parses utf-8 encoded string.
		@returns list of parsed BibItem
		"""
		item = BibItem()
		items = []
		self.line = 1
		self.char = 1
		for index in range(len(str_data)):
			c = str_data[index]
			if c == os.linesep:
				self.line += 1
				self.char = 0
			else:
				self.char += 1

			if self.state == self.S_NO_ITEM:
				if c == "@":
					self.state = self.S_ITEM_TYPE
				#anything else is a comment

			elif self.state == self.S_ITEM_TYPE:
				if c.isspace():
					if self.lexeme_started:
						self.lexeme_finished = True
				elif c.isalnum():
					self.lexeme += c
					self.lexeme_started = True
				elif c == self.ITEM_OPEN_BRACKET and (self.lexeme_started or self.lexeme_finished):
					self.set_item_param(item, "booktype", self.lexeme.lower())
					self.set_item_param(item, "source_line", self.line)

					self.state = self.S_ITEM_NO_ID
					self._reset_lexeme()
				else:
					self.raise_error()

			elif self.state == self.S_ITEM_NO_ID:
				if c.isspace():
					if self.lexeme_started:
						self.lexeme_finished = True
				elif (c.isalnum() or c == "_") and (not self.lexeme_finished):
					self.lexeme += c
					self.lexeme_started = True
				elif c == self.FIELD_SEP and (self.lexeme_started or self.lexeme_finished):
					self.set_item_param(item, "id", self.lexeme)

					self.state = self.S_PARAM_KEY
					self._reset_lexeme()
				else:
					self.raise_error()

			elif self.state == self.S_PARAM_KEY:
				if c.isspace():
					if self.lexeme_started:
						self.lexeme_finished = True
				elif (c.isalnum() or (c == "_")) and (not self.lexeme_finished):
					self.lexeme += c
					self.lexeme_started = True
				elif c == self.KEY_VALUE_SEP and (self.lexeme_started or self.lexeme_finished):
					self.key = self.lexeme

					self.state = self.S_PARAM_VALUE
					self._reset_lexeme()
				else:
					self.raise_error()

			elif self.state == self.S_PARAM_VALUE:
				if c == os.linesep and self.lexeme_started and self.lexeme_in_brackets:
					self.raise_error()
				elif c.isspace():
					#any space character sequence is considered as a single space
					if self.lexeme_started:
						#only values without spaces can be written without spaces
						if not self.lexeme_in_brackets:
							self.set_item_param(item, self.key, self.lexeme)

							self.state = self.S_PARAM_READ
							self.key = ""
							self._reset_lexeme()
						else:
							if not self.lexeme.endswith(" "):
								self.lexeme += " "
				elif (c == self.FIELD_SEP) and self.lexeme_started and (not self.lexeme_in_brackets):
					#values without spaces can be written without parentheses
					self.set_item_param(item, self.key, self.lexeme)

					self.state = self.S_PARAM_KEY
					self.key = ""
					self._reset_lexeme()
				elif (c == self.ITEM_CLOSE_BRACKET) and self.lexeme_started and (not self.lexeme_in_brackets):
					self.set_item_param(item, self.key, self.lexeme)
					items.append(item)
					item = BibItem()

					self.state = self.S_NO_ITEM
					self.key = ""
					self._reset_lexeme()
				elif c == "{":
					if self.lexeme_started:
						self.parenthesis_depth += 1
						self.lexeme += c
					else:
						self.lexeme_in_brackets = True
						self.lexeme_started = True
				elif c == "}":
					if self.parenthesis_depth > 0:
						self.parenthesis_depth -= 1
						self.lexeme += c
					else:
						self.set_item_param(item, self.key, self.lexeme)

						self.state = self.S_PARAM_READ
						self.key = ""
						self._reset_lexeme()
				elif c.isprintable():
					self.lexeme_started = True
					self.lexeme += c
				else:
					self.raise_error()

			elif self.state == self.S_PARAM_READ:
				if c.isspace():
					pass
				elif c == self.ITEM_CLOSE_BRACKET:
					items.append(item)
					item = BibItem()
					self.state = self.S_NO_ITEM
				elif c == self.FIELD_SEP:
					self.state = self.S_PARAM_KEY
				else:
					self.raise_error()

			else:
				self.raise_error()

		#giant for cycle ends here
		return items
