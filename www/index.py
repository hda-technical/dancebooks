import parser

def create_index(items: [parser.BibItem], keys: [str]):
	"""
	Creates index for a given list of BibItems.
	Returns {key: {possible value: set([BibItem])}} dictionary
	"""
	def append_to_subindex(subindex, item, value):
		"""
		Appends an item to subindex. Changes subindex.
		"""
		if isinstance(value, (list, set)):
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
					
	index = dict()
	for key in keys:
		index[key] = dict()

	for key in keys:
		subindex = index[key]
		for item in items:
			value = item.get(key)
			if value is not None:
				if key == "keywords":
					print("Adding {value} to keyword index".format(value=value))
				append_to_subindex(subindex, item, value)

	return index
