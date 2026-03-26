import os
import re
import sys
# import spacy
from nltk import tokenize
# https://github.com/adbar/simplemma
from simplemma import lemmatize, simple_tokenizer, text_lemmatizer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks.config import config
from dancebooks import bib_parser
from dancebooks import utils
import os.path

# Language mapping for each .bib file (used for lemmatization)
lang_map = {
	"american.bib": {
		"en",
		"fr",
	},
	"argentine.bib": {
		"es",
		"pt",
	},
	"australian.bib": {
		"en",
	},
	"austrian.bib": {
		"de",
		"fr",
		"it",
	},
	"belgian.bib": {
		"fr",
	},
	"canadian.bib": {
		"en",
		"fr",
	},
	"chilean.bib": {
		"es",
	},
	"czech.bib": {
		"cs",
		"de",
	},
	"danish.bib": {
		"da",
	},
	"dutch.bib": {
		"nl",
		"en",
		"fr",
		"de",
	},
	"english.bib": {
		"en",
        "fr",
		"la",
	},
	"estonian.bib": {
		"et",
	},
	"finnish.bib": {
		"fi",
		"sv",
		"de",
		"fr",
	},
	"french.bib": {
		"fr",
		"la",
	},
	"german.bib": {
		"de",
		"en",
		"fr"
	},
	"italian.bib": {
		"it",
		"fr",
		"la",
	},
	"latvian.bib": {
		"lv",
		"ru",
	},
	"mexican.bib": {
		"es",
	},
	"norwegian.bib": {
		"nb",
	},
	"polish.bib": {
		"pl",
		"fr",
	},
	"portuguese.bib": {
		"pt",
	},
	"russian.bib": {
		"ru",
		"de",
		"fr",
		"lv",
		"uk",
	},
	"spanish.bib": {
		"es",
	},
	"swedish.bib": {
		"sv",
		"fr",
	},
	"swiss.bib": {
		"de",
		"fr",
	},
}

def parse_folder_into_json(path, param_list=None, sep=" "):
	"""
	Parses all .bib files in given folder and returns a nested dict.

	The returned value has the structure::

		{
		    filename1: {item_id1: data_string1,
		                item_id2: data_string2,
		                ...},
		    filename2: {...},
		    ...
		}

	Each `data_string` is constructed from the parameters listed in
	*param_list* (by default ``[]`` which means use all available fields) using
	:func:`item_data_tuple`.

	:param path: directory containing .bib files
	:param param_list: list of bib parameters to include in the string
	:param sep: separator to join multiple values
	:returns: dictionary as described above
	"""

	if not os.path.isdir(path):
		raise Exception("Path to folder expected")

	# find files in folder
	files = utils.search_in_folder(path, lambda p: p.endswith(".bib"))
	result = {}

	for filename in files:
		fullpath = os.path.join(path, filename)
		items = bib_parser.BibParser()._parse_file(fullpath)
		for item in items:
			item.finalize()
		key = os.path.basename(filename)

		# if no specific param_list provided, use all fields for each item
		if param_list is None:
			# collect all field names seen in this file
			fieldset = set()
			for item in items:
				fieldset.update(item.fields())
			current_list = sorted(fieldset)
		else:
			current_list = param_list

		result[key] = items_to_data_dict(items, current_list, sep)

	return result

def item_data_tuple(item, param_list, sep=" "):
    """
	Return (item_id, joined_info_string).

    The returned string is a space-separated concatenation of each parameter's
    value (as string) from *param_list* in the given order. Missing/empty
    values are skipped.
    """

    values = []
    for param in param_list:
        value = item.get_as_string(param)
        if value:
            values.append(value)
    return (item.id, sep.join(values))


def items_to_data_dict(items, param_list, sep=" "):
    """
	Return a dict mapping item.id -> data string.

    The data string is built using :func:`item_data_tuple` for each item.
    """

    return {item_id: data for item_id, data in (item_data_tuple(item, param_list, sep) for item in items)}


def clean_for_lemmatizer(text):
    """ 
	Keep only word-like sequences of length >= 3.

    This is applied **before** calling :func:`text_lemmatizer`.
    """

    return " ".join(re.findall(r"\w{4,}", text))


def lemmatize_with_cleaning(text, lang):
    """
	Lemmatize text after applying a pre-cleaning regex filter.
	"""

    cleaned = clean_for_lemmatizer(text)
    tokens = simple_tokenizer(cleaned)
    lemmatized = []
    for token in tokens:
        current = token
        for l in lang:
            current = lemmatize(current, l)
        lemmatized.append(current)
    return lemmatized


# if __name__ == "__main__":
#     param_list = ['title',
#                   'author',
#                   'altauthor',
#                   'booktitle',
#                   'incipit',
#                   'journaltitle',
#                   'keywords',
#                   'langid', 
#                   'location',
#                   'origauthor',
#                   'origlanguage',
#                   'pseudo_author',
#                   'translator',
#                   'type']

#     folder_data = parse_folder_into_json(config.parser.bibdata_dir, param_list)

#     some_file = "russian.bib"
#     some_id = "dmitrevskiy_1808_handwritten"

#     # preprocessing + lemmatization example
#     doc = lemmatize_with_cleaning(folder_data[some_file][some_id], lang=("ru", "en"))
#     print(doc)

#     ru_data = folder_data["russian.bib"]
#     for item_id, text in ru_data.items():
#         text = lemmatize_with_cleaning(text, lang=("ru", "en"))
#         print(f"{item_id}: {text}")




