# coding: utf-8
import http.client

from nose.tools import eq_, ok_

from config import config
import index
import main
import bib_parser
import search

client = main.flask_app.test_client()

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
EXPECTED_KEYWORDS = set(["renaissance", "cinquecento", "grumbling", "historical dance"])

def parse_string_test():
	"""
	Tests if string can be succesfully parsed by BibParser
	"""
	items = bib_parser.BibParser().parse_string(TEST_ITEMS)
	item_index = index.Index(items)
	for item in items:
		item.process_crossrefs(item_index)
	item_index.update(items)
	
	languages = set(item_index["langid"].keys())
	keywords = set(item_index["keywords"].keys())

	eq_(len(items), 2)
	eq_(languages, EXPECTED_LANGUAGES)
	eq_(keywords, EXPECTED_KEYWORDS)


def search_items_test():
	"""
	Tests if parsed items can be searched by a bunch of parameters
	"""
	items = bib_parser.BibParser().parse_string(TEST_ITEMS)
	item_index = index.Index(items)
	for item in items:
		item.process_crossrefs(item_index)
	item_index.update(items)

	author_search = search.search_for_iterable("author", "Петров")
	filtered_items = filter(author_search, items)
	eq_(len(list(filtered_items)), 1)

	#testing exact match
	year_search = search.and_([
		search.search_for("year_from", 1825),
		search.search_for("year_to", 1825)
	])
	filtered_items = filter(year_search, items)
	eq_(len(list(filtered_items)), 1)

	#testing partial intersection
	year_search = search.and_([
		search.search_for("year_from", 1500),
		search.search_for("year_to", 1600)
	])
	filtered_items = filter(year_search, items)
	eq_(len(list(filtered_items)), 1)
	
	#testing inner containment
	year_search = search.and_([
		search.search_for("year_from", 1499),
		search.search_for("year_to", 1501)
	])
	filtered_items = filter(year_search, items)
	eq_(len(list(filtered_items)), 1)
	
	#testing outer containment
	year_search = search.and_([
		search.search_for("year_from", 1400),
		search.search_for("year_to", 1600)
	])
	filtered_items = filter(year_search, items)
	eq_(len(list(filtered_items)), 1)
	
	filtered_items = item_index["keywords"]["grumbling"]
	eq_(len(list(filtered_items)), 1)

	filtered_items = \
		item_index["keywords"]["cinquecento"] & \
		item_index["keywords"]["historical dance"]
	eq_(len(list(filtered_items)), 1)
	
	
def app_test():
	rq = client.get(config.www.app_prefix, follow_redirects=True)
	eq_(rq.status_code, http.client.OK)

	rq = client.get(config.www.app_prefix + "?lang=ru")
	#eq_(rq.status_code, http.client.OK)
	ok_("Set-Cookie" in rq.headers)

	rq = client.get(config.www.app_prefix + "/index.html")
	eq_(rq.status_code, http.client.OK)

	rq = client.get(config.www.app_prefix + "/index.html?"
		"author=Wilson&"
		"title=Ecossoise&"
		"year_from=1800&"
		"year_to=1900")
	eq_(rq.status_code, http.client.OK)

	rq = client.get(config.www.app_prefix + "/all.html")
	eq_(rq.status_code, http.client.OK)
	
