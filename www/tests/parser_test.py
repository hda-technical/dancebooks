# coding: utf-8

from nose.tools import eq_, ok_

from parser import BibParser
from parser import YEAR_FROM_PARAM, YEAR_TO_PARAM
import search

TEST_OPTIONS = {
	BibParser.LISTSEP : "|", 
	BibParser.NAMESEP : "|", 
	BibParser.KEYWORDSEP : ",",
	BibParser.SCANFIELDS : set(["langid", "keywords"])
}

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
	parser = BibParser(TEST_OPTIONS)
	items = parser.parse_string(TEST_ITEMS)
	
	languages = set(parser.get_scanned_fields("langid"))
	keywords = set(parser.get_scanned_fields("keywords"))

	eq_(len(items), 2)
	eq_(languages, EXPECTED_LANGUAGES)
	eq_(keywords, EXPECTED_KEYWORDS)


def search_items_test():
	"""
	Tests if parsed items can be searched by a bunch of parameters
	"""
	parser = BibParser(TEST_OPTIONS)
	items = parser.parse_string(TEST_ITEMS)

	author_search = search.search_for_iterable("author", "Петров")
	filtered_items = filter(author_search, items)
	eq_(len(list(filtered_items)), 1)

	search_values = {YEAR_FROM_PARAM: "1825"}
	year_search = search.search_for_year("year", search_values)
	filtered_items = filter(year_search, items)
	eq_(len(list(filtered_items)), 1)

	search_values = {YEAR_FROM_PARAM: "1500", YEAR_TO_PARAM: "1900"}
	year_interval_search = search.search_for_year("year", search_values)
	filtered_items = filter(year_interval_search, items)
	eq_(len(list(filtered_items)), 2)
	
	keyword_search = search.search_for_iterable_set("keywords", 
		set(["grumbling"]))
	filtered_items = filter(keyword_search, items)
	eq_(len(list(filtered_items)), 1)

	keyword_search = search.search_for_iterable_set("keywords", 
		set(["cinquecento", "historical dance"]))
	filtered_items = filter(keyword_search, items)
	eq_(len(list(filtered_items)), 1)
	
	
def app_test():
	from main import app, APP_PREFIX
	client = app.test_client()

	rq = client.get(APP_PREFIX, follow_redirects = True)
	eq_(rq.status_code, 200)

	rq = client.get(APP_PREFIX + "/index.html")
	eq_(rq.status_code, 200)

	rq = client.get(APP_PREFIX + "/index.html?"
		"author=Wilson&"
		"title=Ecossoise&"
		"year_from=1800&"
		"year_to=1900")
	eq_(rq.status_code, 200)

	rq = client.get(APP_PREFIX + "/all.html")
	eq_(rq.status_code, 200)
	
