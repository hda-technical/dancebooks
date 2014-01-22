# coding: utf-8
import re

import constants
import utils

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


def search_for_string_exact(key, value):
	"""
	Creates filter for string (searches for exact match)
	"""
	return lambda item, key=key, value=value: \
					item.get(key) == value


def search_for_iterable(key, value):
	"""
	Creates filter for iterable(string) (searches for substrings)
	"""
	regexp = re.compile(re.escape(value), flags = re.IGNORECASE)
	return lambda item, key=key, regexp=regexp: \
					item.get(key) and \
					any([regexp.search(word) for word in 
						item.get(key)])


def search_for_iterable_set(key, value):
	"""
	Creates filter for iterable (string) (searches for subset match)
	"""
	return lambda item, key=key, value=value: \
					item.get(key) and \
					set(item.get(key)).issuperset(value)


def search_for_iterable_set_exact(key, value):
	"""
	Creates filter for iterable (string) (searches for subset match)
	"""
	return lambda item, key=key, value=value: \
					item.get(key) and \
					set(item.get(key)) == set(value)


def search_for_year(year_from, year_to):
	"""
	Generates filter for year intervals.
	"""
	if (not year_from) and (not year_to):
		return None
		
	if not year_from:
		year_from = year_to

	if not year_to:
		year_to = year_from

	year_from = int(year_from)
	year_to = int(year_to)
	if (year_to < year_from):
		return search_false()

	interval = (year_from, year_to)
	
	return lambda item, interval=interval: \
					item.published_between(interval)

					
def search_false():
	"""
	Generates search always returning False
	"""
	return lambda item: False
	
	
def search_true():
	"""
	Generates search always returning True
	"""
	return lambda item: True
	
	
def and_(searches):
	"""
	Generates search acting as boolean and of given searches
	"""
	return lambda item, searches=searches: all([s(item) for s in searches])
	
	
def or_(searches):
	"""
	Generates search acting as boolean or of given searches
	"""
	return lambda item, searches=searches: any([s(item) for s in searches])
	
	
def search_for(key, values, possible_values=None):
	"""
	Creates filter for a given key.
	Returnis None if something is bad
	"""
	if (key in constants.LIST_PARAMS) or (key in constants.NAME_PARAMS):
		prepared_values = set([values[key]])
		if possible_values is not None and \
			not prepared_values.issubset(possible_values):
			return search_false()
			
		return search_for_iterable(key, values[key])
	elif (key in constants.KEYWORD_PARAMS):
		prepared_values = set(utils.strip_split_list(values[key], ","))
		if possible_values is not None and \
			not prepared_values.issubset(possible_values):
			return search_false()
			
		return search_for_iterable_set(key, prepared_values)
	elif (key == constants.YEAR_PARAM):
		return search_for_year(
			values.get(constants.YEAR_FROM_PARAM, ""),
			values.get(constants.YEAR_TO_PARAM, "")
		)
	else:
		prepared_values = set([values[key]])
		if possible_values is not None and \
			not prepared_values.issubset(possible_values):
			return search_false()
		return search_for_string(key, values[key])
