#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dancebooks import bib_parser
from dancebooks import const
from dancebooks import index
from dancebooks import search
from dancebooks import utils

TEST_ITEMS = bib_parser.BibParser()._parse_string(
r"""
@book(
	tudor_1491,
	author = {Henry Eight of Tudor | Anne Boleyn | Catherine of Aragon},
	title = {Six Wives of Henry Eight. Some Words \& Letters \& Other Stuff Here},
	langid = {english},
	location = {London},
	year = {1491—1547?},
	url = {http://example.com},
	keywords = {renaissance | cinquecento | historical dance}
)

@book(
	petrovsky_1825,
	author = {Людовик Петровский | Николай Проклович Петров},
	pseudo_author = {Людвиг ван Бетховен},
	title = {Побрюзжим на досуге},
	langid = {russian},
	location = {Москва | Одесса},
	year = {1825},
	keywords = {grumbling | historical dance}
)

@book(
	raevsky_1896,
	pseudo_author = {Ф. В. Раевский},
	title = {Дирижёр через Ё},
	langid = {russian},
	location = {Санкт-Петербург},
	year = {1896}
)

@article(
	mayak_1924,
	author = {В. В. Маяковский},
	title = {В «Правде» пишется правда. В «Известиях» — известия},
	crossref = {pravda_1924},
	year = {1924}
)

@periodical(
	pravda_1924,
	shorthand = {Правда},
	title = {Правда},
	year = {1924},
	number = {1}
)
"""
)
SEARCH_INDEX = index.Index(TEST_ITEMS)

TUDOR_1491 = TEST_ITEMS[0]
PETROVSKY_1825 = TEST_ITEMS[1]
RAEVSKY_1896 = TEST_ITEMS[2]
MAYAK_1924 = TEST_ITEMS[3]


def test_indexing():
	"""
	Tests if string can be succesfully parsed by BibParser
	"""
	languages = set(langid for langid in SEARCH_INDEX["langid"].keys() if not langid.startswith("!"))
	keywords = set(SEARCH_INDEX["keywords"].keys())

	assert languages ==  {"russian", "english"}
	assert keywords == {
		"renaissance",
		"cinquecento",
		"grumbling",
		"historical dance",
		"!cinquecento",
		"!renaissance",
		"!grumbling",
		"!historical dance",
	}


def test_parsing():
	assert '{' not in TUDOR_1491.title
	assert '}' not in TUDOR_1491.title
	assert MAYAK_1924.get("crossref") == "pravda_1924"


def test_html_rendering():
	# FIXME: TODO
	pass


def test_search_items():
	"""
	Tests if parsed TEST_ITEMS can be searched by a bunch of parameters
	"""
	author_search = search.search_for_iterable("author", "Петров")
	filtered_items = filter(author_search, TEST_ITEMS)
	assert len(list(filtered_items)) == 1

	# testing exact match
	year_search = search.and_([
		search.search_for("year_from", 1825),
		search.search_for("year_to", 1825)
	])
	filtered_items = filter(year_search, TEST_ITEMS)
	assert len(list(filtered_items)) == 1

	# testing partial intersection
	year_search = search.and_([
		search.search_for("year_from", 1500),
		search.search_for("year_to", 1600)
	])
	filtered_items = filter(year_search, TEST_ITEMS)
	assert len(list(filtered_items)) == 1

	# testing inner containment
	year_search = search.and_([
		search.search_for("year_from", 1499),
		search.search_for("year_to", 1501)
	])
	filtered_items = filter(year_search, TEST_ITEMS)
	assert len(list(filtered_items)) == 1

	# testing outer containment
	year_search = search.and_([
		search.search_for("year_from", 1400),
		search.search_for("year_to", 1600)
	])
	filtered_items = filter(year_search, TEST_ITEMS)
	assert len(list(filtered_items)) == 1

	filtered_items = SEARCH_INDEX["keywords"]["grumbling"]
	assert len(list(filtered_items)) == 1

	filtered_items = \
		SEARCH_INDEX["keywords"]["cinquecento"] & \
		SEARCH_INDEX["keywords"]["historical dance"]
	assert len(list(filtered_items)) == 1


def test_inverted_index_search():
	DIRECT_KEY = "cinquecento"
	INVERTED_KEY = const.INVERTED_INDEX_KEY_PREFIX + DIRECT_KEY
	subindex = SEARCH_INDEX["keywords"]

	assert DIRECT_KEY in subindex
	assert INVERTED_KEY in subindex
	filtered_items = SEARCH_INDEX["keywords"][INVERTED_KEY]

	assert len(filtered_items) == 4
	assert {item.id for item in filtered_items} == {"petrovsky_1825", "raevsky_1896", "mayak_1924", "pravda_1924"}


def test_html_cite_formatting():
	assert utils.make_html_cite(PETROVSKY_1825) == (
		"<em>Людовик Петровский, Николай Проклович Петров</em> "
		"Побрюзжим на досуге. "
		"Москва, Одесса, "
		"1825. "
		'<a href="/books/petrovsky_1825">https://bib.hda.org.ru/books/petrovsky_1825</a>'
	)

	assert utils.make_html_cite(RAEVSKY_1896) == (
		"<em>Ф. В. Раевский</em> "
		"Дирижёр через Ё. "
		"Санкт-Петербург, "
		"1896. "
		'<a href="/books/raevsky_1896">https://bib.hda.org.ru/books/raevsky_1896</a>'
	)