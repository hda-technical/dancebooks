import collections
import logging

from config import config

class Index(object):
	def __init__(self, items):
		self.update(items)

	def __getitem__(self, key):
		return self._dict[key]

	def update(self, items):
		"""
		Creates index for a given list of BibItems.
		Returns {key: {possible value: set([BibItem])}} dictionary
		"""
		def check_value(subindex, item, key, value):
			if (
				(key in config.www.index_unique_params) and
				(value in subindex)
			):
				logging.error("Value {value} is not unique for unique index by {key}".format(
					value=value,
					key=key
				))


		def append_to_subindex(subindex, item, key, value):
			"""
			Appends an item to subindex
			"""
			if (
				isinstance(value, list) or
				isinstance(value, set)
			):
				for subvalue in value:
					check_value(subindex, item, key, subvalue)
					subindex[subvalue].add(item)
			else:
				check_value(subindex, item, key, value)
				subindex[value].add(item)

		dict_creator = lambda: collections.defaultdict(set)
		self._dict = collections.defaultdict(dict_creator)
		for key in config.www.index_params:
			subindex = self._dict[key]
			for item in items:
				value = item.get(key)
				if value is not None:
					append_to_subindex(subindex, item, key, value)
