import collections
import logging

from dancebooks.config import config
from dancebooks import const

class Index(object):
	def __init__(self, items):
		self.update(items)

	def __getitem__(self, key):
		return self._dict[key]

	def __contains__(self, key):
		return (key in self._dict)

	def update(self, items):
		"""
		Creates index for a given list of BibItems.
		Returns {key: {possible value: set([BibItem])}} dictionary
		"""
		def check_value(subindex, item, index_param, value):
			if (
				(index_param in config.www.index_unique_params) and
				(value in subindex)
			):
				logging.error(f"Value {value} is not unique for unique index by {index_param}")

		def append_to_subindex(subindex, item, index_param, value):
			"""
			Appends an item to subindex
			"""
			if (
				isinstance(value, list) or
				isinstance(value, set)
			):
				for subvalue in value:
					check_value(subindex, item, index_param, subvalue)
					subindex[subvalue].add(item)
			else:
				check_value(subindex, item, index_param, value)
				subindex[value].add(item)

		dict_creator = lambda: collections.defaultdict(set)
		self._dict = collections.defaultdict(dict_creator)
		for index_param in config.www.index_params:
			subindex = self._dict[index_param]
			for item in items:
				value = item.get(index_param)
				if value is not None:
					append_to_subindex(subindex, item, index_param, value)
		#inverted index SHOULD be filled after direct index fill
		for index_param in config.www.inverted_index_params:
			subindex = self._dict[index_param]
			keys = list(subindex.keys())
			for item in items:
				for key in keys:
					if (
						not item.has(index_param) or
						(key not in item.get(index_param))
					):
						inverted_key = const.INVERTED_INDEX_KEY_PREFIX + key
						append_to_subindex(subindex, item, index_param, inverted_key)
