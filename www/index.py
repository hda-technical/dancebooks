import collections

class Index(object):
	def __init__(self, cfg, items):
		self.cfg = cfg
		self.update(items) 

	def __getitem__(self, key):
		return self._dict[key]

	def update(self, items):
		"""
		Creates index for a given list of BibItems.
		Returns {key: {possible value: set([BibItem])}} dictionary
		"""
		def append_to_subindex(subindex, item, value):
			"""
			Appends an item to subindex
			"""
			if isinstance(value, list):
				for subvalue in value:
					subindex[subvalue].add(item)
			else:
				subindex[value].add(item)
	
		dict_creator = lambda: collections.defaultdict(set)
		self._dict = collections.defaultdict(dict_creator)
		for key in self.cfg.www.index_params:
			subindex = self._dict[key]
			for item in items:
				value = item.get(key)
				if value is not None:
					append_to_subindex(subindex, item, value)
