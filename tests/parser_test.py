#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dancebooks import bib_parser
from dancebooks import const
from dancebooks import index
from dancebooks import search
from dancebooks import utils

TEST_ITEMS = \
r"""
@book(
	id_1,
	author = {Henry Eight | Anne Boleyn | Catherine of Aragon},
	title = {Six Wifes of Henry Eight. Some Words \& Letters \& Other Stuff Here},
	langid = {english},
	location = {London},
	year = {1491—1547?},
	url = {http://example.com},
	keywords = {renaissance | cinquecento | historical dance}
)

@book(
	id_2,
	author = {Людовик Петровский | Николай Проклович Петров},
	title = {Побрюзжим на досуге},
	langid = {russian},
	location = {Москва | Одесса},
	year = {1825},
	keywords = {grumbling | historical dance}
)
"""

EXPECTED_LANGUAGES = set(["russian", "english"])
EXPECTED_KEYWORDS = set([
	"renaissance",
	"cinquecento",
	"grumbling",
	"historical dance",
	"!cinquecento",
	"!renaissance",
	"!grumbling",
])


def test_parse_string():
	"""
	Tests if string can be succesfully parsed by BibParser
	"""
	items = bib_parser.BibParser()._parse_string(TEST_ITEMS)
	item_index = index.Index(items)

	languages = set(langid for langid in item_index["langid"].keys() if not langid.startswith("!"))
	keywords = set(item_index["keywords"].keys())

	assert languages == EXPECTED_LANGUAGES
	assert keywords == EXPECTED_KEYWORDS

	item1 = next(iter(item_index["id"]["id_1"]))
	assert '{' not in item1.title
	assert '}' not in item1.title


def test_search_items():
	"""
	Tests if parsed items can be searched by a bunch of parameters
	"""
	items = bib_parser.BibParser()._parse_string(TEST_ITEMS)
	item_index = index.Index(items)

	author_search = search.search_for_iterable("author", "Петров")
	filtered_items = filter(author_search, items)
	assert len(list(filtered_items)) == 1

	# testing exact match
	year_search = search.and_([
		search.search_for("year_from", 1825),
		search.search_for("year_to", 1825)
	])
	filtered_items = filter(year_search, items)
	assert len(list(filtered_items)) == 1

	# testing partial intersection
	year_search = search.and_([
		search.search_for("year_from", 1500),
		search.search_for("year_to", 1600)
	])
	filtered_items = filter(year_search, items)
	assert len(list(filtered_items)) == 1

	# testing inner containment
	year_search = search.and_([
		search.search_for("year_from", 1499),
		search.search_for("year_to", 1501)
	])
	filtered_items = filter(year_search, items)
	assert len(list(filtered_items)) == 1

	# testing outer containment
	year_search = search.and_([
		search.search_for("year_from", 1400),
		search.search_for("year_to", 1600)
	])
	filtered_items = filter(year_search, items)
	assert len(list(filtered_items)) == 1

	filtered_items = item_index["keywords"]["grumbling"]
	assert len(list(filtered_items)) == 1

	filtered_items = \
		item_index["keywords"]["cinquecento"] & \
		item_index["keywords"]["historical dance"]
	assert len(list(filtered_items)) == 1


def test_inverted_index_search():
	items = bib_parser.BibParser()._parse_string(TEST_ITEMS)
	item_index = index.Index(items)

	DIRECT_KEY = "cinquecento"
	INVERTED_KEY = const.INVERTED_INDEX_KEY_PREFIX + DIRECT_KEY
	subindex = item_index["keywords"]

	assert DIRECT_KEY in subindex
	assert INVERTED_KEY in subindex
	filtered_items = item_index["keywords"][INVERTED_KEY]

	assert len(filtered_items) == 1
	assert utils.first(filtered_items).id == "id_2"


def test_cite_formatting():
	items = bib_parser.BibParser()._parse_string(TEST_ITEMS)
	assert utils.make_html_cite(items[-1]) == (
		"<em>Людовик Петровский, Николай Проклович Петров</em> "
		"Побрюзжим на досуге. "
		"Москва, Одесса, "
		"1825. "
		'<a href="/books/id_2">https://bib.hda.org.ru/books/id_2</a>'
	)
