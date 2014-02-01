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
					if subvalue in subindex:
						subindex[subvalue].add(item)
					else:
						subindex[subvalue] = set([item])
			else:
				if value in subindex:
					subindex[value].add(item)
				else:
					subindex[value] = set([item])
						
		self._dict = dict()
		for key in self.cfg.www.index_params:
			self._dict[key] = dict()

		for key in self.cfg.www.index_params:
			subindex = self._dict[key]
			for item in items:
				value = item.get(key)
				if value is not None:
					append_to_subindex(subindex, item, value)
