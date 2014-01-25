# coding: utf-8

from nose.tools import eq_ 

import constants
import index
import main
import parser
import search

client = main.app.test_client()

TEST_ITEMS = \
"""
@book(
	id_1,
	author = {Henry Eight | Anne Boleyn | Catherine of Aragon},
	title = {Six Wifes of Henry Eight},
	langid = {english},
	location = {London},
	year = {1491—1547?},
	url = {http://example.com},
	keywords = {renaissance, cinquecento, historical dance}
)

@book(
	id_2,
	author = {Людовик Петровский | Николай Проклович Петров},
	title = {Побрюзжим на досуге},
	langid = {russian},
	location = {Москва | Одесса},
	year = {1825},
	keywords = {grumbling, historical dance}
)
"""

EXPECTED_LANGUAGES = set(["russian", "english"])
EXPECTED_KEYWORDS = set(["renaissance", "cinquecento", "grumbling", "historical dance"])

def parse_string_test():
	"""
	Tests if string can be succesfully parsed by BibParser
	"""
	items = parser.BibParser().parse_string(TEST_ITEMS)
	item_index = index.create_index(items, constants.INDEX_KEYS)
	
	languages = set(item_index["langid"].keys())
	keywords = set(item_index["keywords"].keys())

	eq_(len(items), 2)
	eq_(languages, EXPECTED_LANGUAGES)
	eq_(keywords, EXPECTED_KEYWORDS)


def search_items_test():
	"""
	Tests if parsed items can be searched by a bunch of parameters
	"""
	items = parser.BibParser().parse_string(TEST_ITEMS)
	item_index = index.create_index(items, constants.INDEX_KEYS)

	author_search = search.search_for_iterable("author", "Петров")
	filtered_items = filter(author_search, items)
	eq_(len(list(filtered_items)), 1)

	year_search = search.search_for_year("1825", None)
	filtered_items = filter(year_search, items)
	eq_(len(list(filtered_items)), 1)

	year_interval_search = search.search_for_year("1500", "1900")
	filtered_items = filter(year_interval_search, items)
	eq_(len(list(filtered_items)), 2)
	
	filtered_items = item_index["keywords"]["grumbling"]
	eq_(len(list(filtered_items)), 1)

	filtered_items = \
		item_index["keywords"]["cinquecento"] & \
		item_index["keywords"]["historical dance"]
	eq_(len(list(filtered_items)), 1)
	
	
def app_test():
	rq = client.get(constants.APP_PREFIX, follow_redirects=True)
	eq_(rq.status_code, 200)

	rq = client.get(constants.APP_PREFIX + "/index.html")
	eq_(rq.status_code, 200)

	rq = client.get(constants.APP_PREFIX + "/index.html?"
		"author=Wilson&"
		"title=Ecossoise&"
		"year_from=1800&"
		"year_to=1900")
	eq_(rq.status_code, 200)

	rq = client.get(constants.APP_PREFIX + "/all.html")
	eq_(rq.status_code, 200)
	
