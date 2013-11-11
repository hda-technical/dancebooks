import re

from parser import BibParser
from parser import LIST_PARAMS, NAME_PARAMS, KEYWORD_PARAMS, \
					YEAR_PARAM, YEAR_FROM_PARAM, YEAR_TO_PARAM

from interval import Interval

def search_for_string(key, value):
	"""
	Creates filter for string (searches for substrings)
	"""
	regexp = re.compile(re.escape(value), flags = re.IGNORECASE)
	return lambda item, key = key, regexp = regexp: \
					item.get(key) and \
					regexp.search(item.get(key))


def search_for_string_exact(key, value):
	"""
	Creates filter for string (searches for exact match)
	"""
	return lambda item, key = key, value = value: \
					item.get(key) == value


def search_for_iterable(key, value):
	"""
	Creates filter for iterable(string) (searches for substrings)
	"""
	regexp = re.compile(re.escape(value), flags = re.IGNORECASE)
	return lambda item, key = key, regexp = regexp: \
					item.get(key) and \
					any([regexp.search(word) for word in 
						item.get(key)])


def search_for_iterable_set(key, value):
	"""
	Creates filter for iterable (string) (searches for subset match)
	"""
	return lambda item, key = key, value = value: \
					item.get(key) and \
					item.get(key).issuperset(value)


def search_for_year(key, values):
	"""
	Generates filter for year intervals.
	"""
	year_from = values.get(YEAR_FROM_PARAM, "")
	year_to = values.get(YEAR_TO_PARAM, "")
	
	if len(year_from) == 0:
		year_from = year_to

	if len(year_to) == 0:
		year_to = year_from

	if (len(year_from) == 0) and (len(year_to) == 0):
		return None
	else:
		year_from = int(year_from)
		year_to = int(year_to)
		if (year_to < year_from):
			return search_empty()

		interval = Interval(year_from, year_to)
	
	return lambda item, interval = interval: \
					item.published_between(interval)

def search_empty():
	"""
	Generates search always returning False
	"""
	return lambda item: False


def search_for(key, values, possible_values = None):
	"""
	Creates filter for a given key.
	Return None if something is bad
	"""
	if (key == YEAR_FROM_PARAM) or \
	   (key == YEAR_TO_PARAM):
	   return None

	if (key in LIST_PARAMS) or (key in NAME_PARAMS):
		prepared_values = set([values[key]])
		if possible_values is not None and \
			not prepared_values.issubset(possible_values):
			return search_empty()
			
		return search_for_iterable(key, values[key])
	elif (key in KEYWORD_PARAMS):
		prepared_values = set(BibParser.strip_split_list(values[key], ","))
		if possible_values is not None and \
			not prepared_values.issubset(possible_values):
			return search_empty()
			
		return search_for_iterable_set(key, prepared_values)
	elif (key == YEAR_PARAM):
		return search_for_year(key, values)
	else:
		prepared_values = set([values[key]])
		if possible_values is not None and \
			not prepared_values.issubset(possible_values):
			return search_empty()
		return search_for_string(key, values[key])
