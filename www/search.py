# coding: utf-8
import datetime
import logging
import re

from config import config

def search_for_string(key, value):
	"""
	Creates filter for string (searches for substrings)
	"""
	regexp = re.compile(re.escape(value), flags = re.IGNORECASE)
	return lambda item, key=key, regexp=regexp: \
		item.get(key) and \
		regexp.search(item.get(key))


def search_for_string_regexp(key, regexp):
	"""
	Creates filter for string (searches for substring at the beginning)
	"""
	return lambda item, key=key, regexp=regexp: \
		item.get(key) and \
		regexp.search(item.get(key))


def search_for_iterable(key, value):
	"""
	Creates filter for iterable(string) (searches for substrings)
	"""
	regexp = re.compile(re.escape(value), flags=re.IGNORECASE)
	return lambda item, key=key, regexp=regexp: \
		item.get(key) and \
		any([regexp.search(word) for word in
			item.get(key)])


def search_for_synonyms(keys, values):
	"""
	Creates filter for iterable(string) (searches for exact match)
	@param keys: list of iterable to be searched for
	"""
	def search(item):
		search_values = set(values)
		item_values = set()
		for key in keys:
			item_values |= set(item.get(key) or [])
		return search_values.issubset(item_values)
	return search


def search_for_eq(key, value):
	"""
	Creates filter for exact match
	"""
	return lambda item, key=key, value=value: \
		item.get(key) and \
		item.get(key) == value


def search_for_optional_eq(key, value):
	"""
	Creates filter for exact match of optional value
	"""
	return lambda item, key=key, value=value: \
		item.get(key) == value if item.get(key) else True


def search_for_integer_ge(key, value):
	"""
	Creates filter for integer value (searches for greater or equal)
	"""
	if not isinstance(value, int):
		raise ValueError("Integer value expected")
	return lambda item, key=key, value=value: \
		item.get(key) and \
		item.get(key) >= value


def search_for_integer_le(key, value):
	"""
	Creates filter for integer value (searches for lesser or equal)
	"""
	if not isinstance(value, int):
		raise ValueError("Integer value expected")
	return lambda item, key=key, value=value: \
		item.get(key) and \
		item.get(key) <= value


def search_for_datetime_ge(key, value):
	"""
	Creates filter for datetime value (searches for greater or equal)
	"""
	if not isinstance(value, datetime.datetime):
		raise ValueError("datetime value expected")
	return lambda item, key=key, value=value: \
		item.get(key) and \
		item.get(key) >= value


def search_for_datetime_le(key, value):
	"""
	Creates filter for datetime value (searches for lesser or equal)
	"""
	if not isinstance(value, datetime.datetime):
		raise ValueError("datetime value expected")
	return lambda item, key=key, value=value: \
		item.get(key) and \
		item.get(key) <= value


def search_for_key_presence(key, value):
	"""
	Creates filter for key-presence lookup
	"""
	if not isinstance(value, bool):
		raise ValueError("bool value expected")
	return lambda item, key=key, value=value: \
		item.has(key) == value


def search_false():
	"""
	Generates search always returning False
	"""
	return lambda item: \
		False


def search_true():
	"""
	Generates search always returning True
	"""
	return lambda item: \
		True


def and_(searches):
	"""
	Generates search acting as boolean and of given searches
	"""
	return lambda item, searches=searches: \
		all([s(item) for s in searches])


def or_(searches):
	"""
	Generates search acting as boolean or of given searches
	"""
	return lambda item, searches=searches: \
		any([s(item) for s in searches])


def search_for(key, value):
	"""
	Creates filter for a given key.
	Returns None if something is bad
	"""
	def parse_datetime(value):
		#trying to parse value in multiple formats
		for date_format in config.www.date_formats:
			try:
				return datetime.datetime.strptime(value, date_format)
			except ValueError:
				pass
		raise ValueError("Unsupported datetime format")

	def simple_search_for(key, value):
		#should be checked on the very first place
		if key in config.parser.bool_params:
			if value not in {"true", "false"}:
				raise ValueError("Boolean value for {key} expected".format(
					key=key
				))
			return search_for_key_presence(key, (value == "true"))

		elif key in config.parser.list_params:
			return search_for_iterable(key, value)

		elif key in config.parser.year_start_params:
			#generating end key
			extra_key = key[:-len(config.parser.start_suffix)] + \
				config.parser.end_suffix
			return search_for_integer_ge(extra_key, int(value))

		elif key in config.parser.year_end_params:
			#generating start key
			extra_key = key[:-len(config.parser.end_suffix)] + \
				config.parser.start_suffix
			return search_for_integer_le(extra_key, int(value))

		elif key in config.parser.date_start_params:
			value = parse_datetime(value)
			#generating extra key
			extra_key = key[:-len(config.parser.start_suffix)]
			return search_for_datetime_ge(extra_key, value)

		elif key in config.parser.date_end_params:
			value = parse_datetime(value)
			#generating extra key
			extra_key = key[:-len(config.parser.end_suffix)]
			return search_for_datetime_le(extra_key, value)

		else:
			return search_for_string(key, value)

	synonyms = config.www.search_synonyms.get(key, [])
	synonyms.append(key)
	searches = [
		simple_search_for(synonym, value)
		for synonym in synonyms
	]
	return or_(searches)
