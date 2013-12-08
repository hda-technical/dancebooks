# coding: utf-8
import codecs
from fnmatch import fnmatch
import os.path
import re

import constants
import utils
	
class BibItem(object):
	"""
	Class for bibliography item representation
	"""
	def __init__(self):
		self.__params__ = {}
		self.__year_interval__ = None

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

	def note(self):
		return self.get_as_string("note")

	def annotation(self):
		return self.get_as_string("annotation")

	#not-implemented params
	#
	#type (thesis type)
	#institution
	#isbn
	#pages
	#crossref
	#booktitle
	#origlanguage

	# search helpers
	YEAR_RE = re.compile(r"(?P<start>\d+)([-–—]+(?P<end>\d+)\?)?")
	def published_between(self, search_interval):
		if self.__year_interval__ is None:
			# parsing year field
			match = self.YEAR_RE.match(self.year())
			if match:
				start = int(match.group("start"))
				end = int(match.group("end") or start)
				self._year_interval = (start, end)
			else:
				return False
		
		return (
			self._year_interval[0] <= search_interval[0] <= self._year_interval[1] or
			self._year_interval[0] <= search_interval[1] <= self._year_interval[1] or
			search_interval[0] <= self._year_interval[0] <= search_interval[1] or
			search_interval[0] <= self._year_interval[1] <= search_interval[1]
			)
	
	# getters / setters
	def get_as_string(self, key):
		if key in self.__params__:
			value = self.__params__[key]
			if key in constants.MULTI_VALUE_PARAMS:
				return constants.OUTPUT_LISTSEP.join(value)
			else:
				return value
		else:
			return None

	def get(self, key, value = None, as_string = True):
		if key in self.__params__:
			return self.__params__[key]
		else:
			return None
			
	def set(self, key, value):
		self.__params__[key] = value


class BibParser(object):
	"""
	Class for parsing .bib files, folders and multiline strings
	"""
	# static parser constants
	ITEM_OPEN_PARENTHESIS = set(["{", "("])
	FIELD_SEP = ","
	PARAM_KEY_VALUE_SEP = "="
	
	STATE = \
		(S_NO_ITEM, S_ITEM_TYPE, S_ITEM_NO_ID, S_PARAM_KEY, S_PARAM_VALUE, S_PARAM_READ) = \
		(0,         1,           2,            3,           4,             5)

	def __init__(self):
		"""
		Default ctor
		"""
		self.scanned_fields = dict()
		for scan_field in constants.SCAN_FIELDS:
			self.scanned_fields[scan_field] = set()
			
		self.state = self.S_NO_ITEM
		self.reset_lexeme()

	def get_scanned_fields(self, key):
		return self.scanned_fields[key]
		
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

	def raise_error(self, c, line_in_file, char_in_line):
		"""
		Raises human-readable Exception based on parser state and current file position
		"""
		raise Exception("While {0}: wrong syntax at char [{1}] (line {2}, #{3})"\
				.format(self.state_string(), c, line_in_file, char_in_line))

	def reset_lexeme(self):
		"""
		Resets some internal parser variables.
		Shouldn't be called from the outside
		"""
		self.lexeme = ""
		self.lexeme_started = False
		self.lexeme_finished = False
		self.parenthesis_depth = 0
		self.closing_param_parenthesis = ""

	def set_item_param(self, item, key, value):
		"""
		Sets item param, applying additional conversion if needed.
		"""
		value = utils.parse_latex(value)
		
		if key in constants.LIST_PARAMS:
			value = utils.strip_split_list(value, constants.LISTSEP)
		elif key in constants.NAME_PARAMS:
			value = utils.strip_split_list(value, constants.NAMESEP)
		elif key in constants.KEYWORD_PARAMS:
			value = set(utils.strip_split_list(value, constants.KEYWORDSEP))
		item.set(key, value)

		if key in self.scanned_fields:
			if isinstance(value, set):
				self.scanned_fields[key] |= value
			else:
				self.scanned_fields[key].add(value)

	def parse_folder(self, path):
		"""
		Parses all .bib files in given folder.
		Returns list containing all items found
		"""
		if not os.path.isdir(path):
			raise Exception("Path to folder expected")

		items = []
		for filename in os.listdir(path):
			if fnmatch(filename, "*.bib"):
				parsed_items = self.parse_file(os.path.join(path, filename))
				if parsed_items is not None:
					items.extend(parsed_items)
		return items
		
	def parse_file(self, path):
		"""
		Parses file at given path, handling utf-8-bom correctly.
		@returns list of parsed BibItem
		"""
		if not os.path.isfile(path):
			raise Exception("Path to file expected")
		
		with open(path, "r+b") as input_file:
			str_data = input_file.read()
			#trimming utf-8 byte order mark
			if str_data.startswith(codecs.BOM_UTF8):
				str_data = str_data[len(codecs.BOM_UTF8):].decode()
			else:
				print("Warning: File at {0} is not in utf-8".format(path))
				str_data = str_data.decode()
				
			try:
				source_file = os.path.basename(path)
				items = self.parse_string(str_data)
				for item in items:
					self.set_item_param(item, "source", "{file}:{line}".format(
						file=source_file, line=item.get("source")))
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
		line_in_file = 1
		char_in_line = 1
		for index in range(len(str_data)):
			c = str_data[index]
			if c == os.linesep:
				line_in_file += 1
				char_in_line = 0
			else:
				char_in_line += 1
				
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
				elif c in self.ITEM_OPEN_PARENTHESIS and (self.lexeme_started or self.lexeme_finished):
					self.closing_parenthesis = ("}" if c == "{" else ")")
					self.set_item_param(item, "booktype", self.lexeme)
					self.set_item_param(item, "source", line_in_file)

					self.state = self.S_ITEM_NO_ID
					self.reset_lexeme()
				else:
					self.raise_error(c, line_in_file, char_in_line)

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
					self.reset_lexeme()
				else:
					self.raise_error(c, line_in_file, char_in_line)

			elif self.state == self.S_PARAM_KEY:
				if c.isspace():
					if self.lexeme_started:
						self.lexeme_finished = True
				elif c.isalnum() and (not self.lexeme_finished):
					self.lexeme += c
					self.lexeme_started = True
				elif c == self.PARAM_KEY_VALUE_SEP and (self.lexeme_started or self.lexeme_finished):
					self.key = self.lexeme

					self.state = self.S_PARAM_VALUE
					self.reset_lexeme()
				else:
					self.raise_error(c, line_in_file, char_in_line)

			elif self.state == self.S_PARAM_VALUE:
				if c.isspace():
					#any space character sequence is considered as a single space
					if self.lexeme_started:
						#only values without spaces can be written without spaces
						if self.closing_param_parenthesis == "":
							self.set_item_param(item, self.key, self.lexeme)

							self.state = self.S_PARAM_READ
							self.key = ""
							self.reset_lexeme()
						else:
							if not self.lexeme.endswith(" "):
								self.lexeme += " "
				elif (c == self.FIELD_SEP) and self.lexeme_started and self.closing_param_parenthesis == "":
					#only values without spaces can be written without spaces
					self.set_item_param(item, self.key, self.lexeme)

					self.state = self.S_PARAM_KEY
					self.key = ""
					self.reset_lexeme()
				elif (c == self.closing_parenthesis) and self.lexeme_started and self.closing_param_parenthesis == "":					
					self.set_item_param(item, self.key, self.lexeme)
					items.append(item)
					item = BibItem()
					
					self.state = self.S_NO_ITEM
					self.key = ""
					self.reset_lexeme()
				elif c == "{":
					if self.lexeme_started:
						self.parenthesis_depth += 1
						self.lexeme += c
					else:
						self.closing_param_parenthesis = "}"
						self.lexeme_started = True
				elif c == "}":
					if self.parenthesis_depth > 0:
						self.parenthesis_depth -= 1
						self.lexeme += c
					else:
						self.set_item_param(item, self.key, self.lexeme)

						self.state = self.S_PARAM_READ
						self.key = ""
						self.reset_lexeme()
				elif c.isprintable():
					self.lexeme_started = True
					self.lexeme += c
				else:
					self.raise_error(c, line_in_file, char_in_line)

			elif self.state == self.S_PARAM_READ:
				if c.isspace():
					pass
				elif c == self.closing_parenthesis:
					items.append(item)
					item = BibItem()
					self.state = self.S_NO_ITEM
				elif c == self.FIELD_SEP:
					self.state = self.S_PARAM_KEY
				else:
					self.raise_error(c, line_in_file, char_in_line)

			else:
				self.raise_error(c, line_in_file, char_in_line)
		
		#giant for cycle ends here
		return items
