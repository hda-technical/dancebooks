# coding: utf-8
import re

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
		
	
def search_for(cfg, key, value):
	"""
	Creates filter for a given key.
	Returns None if something is bad
	"""
	if key in cfg.parser.multivalue_params:
		return search_for_iterable(key, value)
	elif key in cfg.parser.date_start_params:
		#generating end key
		extra_key = key[:-len(cfg.parser.date_start_suffix)] + \
			cfg.parser.date_end_suffix
		return search_for_integer_ge(extra_key, int(value))
	elif key in cfg.parser.date_end_params:
		#generating start key
		extra_key = key[:-len(cfg.parser.date_end_suffix)] + \
			cfg.parser.date_start_suffix
		return search_for_integer_le(extra_key, int(value))
	else:
		print("Creating search for string {key} with value {value}".format(key=key, value=value))
		return search_for_string(key, value)
