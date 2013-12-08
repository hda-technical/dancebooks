import re

def strip_split_list(value, sep):
	"""
	Splits string on a given sep(arator), strips spaces from resulting words
	"""
	return [word.strip() for word in value.split(sep)]


LATEX_GROUPING_RE = re.compile(r"(\s|^)\{([^\s]*)\}(\s|$)")
LATEX_URL_RE = re.compile(r"\\url\{([^\s]*)\}")
LATEX_PARENCITE_RE = re.compile(r"\\parencite\{([a-z_\d]*)\}")
PARENCITE_SUBST = r'[<a href="{0}/\1">\1</a>]'
def parse_latex(value):
	"""
	Attempts to remove LaTeX formatting from string
	"""
	if isinstance(value, str):
		value = value.replace(r"\&", "&")
		value = LATEX_GROUPING_RE.sub(r"\1\2\3", value)
		value = LATEX_URL_RE.sub(r'<a href="\1">\1</a>', value)
		value = LATEX_PARENCITE_RE.sub(PARENCITE_SUBST, value)
		return value
	else:
		return value
