#!/usr/bin/env python3
#coding: utf-8
import http.client
import json
import unittest

from config import config
import bib_parser
import const
import index
import search
import utils

TEST_ITEMS = \
r"""
@book(
	id_1,
	author = {Henry Eight | Anne Boleyn | Catherine of Aragon},
	title = {Six Wifes of Henry Eight. Some Words {\&} Letters {\&} Other Stuff Here},
	langid = {english},
	location = {London},
	year = {1491—1547?},
	url = {http://example.com},
	keywords = {renaissance | cinquecento | historical dance},
	annotation = {\url{http://example.com/description}}
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

class TestParser(unittest.TestCase):
	"""
	Tests if parser and basic search tools work as expected
	"""
	def test_parse_string(self):
		"""
		Tests if string can be succesfully parsed by BibParser
		"""
		items = bib_parser.BibParser().parse_string(TEST_ITEMS)
		item_index = index.Index(items)
		for item in items:
			item.finalize(item_index)
		item_index.update(items)

		languages = set(item_index["langid"].keys())
		keywords = set(item_index["keywords"].keys())

		self.assertEqual(len(items), 2)
		self.assertEqual(languages, EXPECTED_LANGUAGES)
		self.assertEqual(keywords, EXPECTED_KEYWORDS)

		item1 = next(iter(item_index["id"]["id_1"]))
		self.assertTrue('{' not in item1.title())
		self.assertTrue('}' not in item1.title())
		self.assertEqual(
			item1.annotation(),
			'<a href="http://example.com/description">http://example.com/description</a>'
		)

	def test_search_items(self):
		"""
		Tests if parsed items can be searched by a bunch of parameters
		"""
		items = bib_parser.BibParser().parse_string(TEST_ITEMS)
		item_index = index.Index(items)
		for item in items:
			item.finalize(item_index)
		item_index.update(items)

		author_search = search.search_for_iterable("author", "Петров")
		filtered_items = filter(author_search, items)
		self.assertEqual(len(list(filtered_items)), 1)

		#testing exact match
		year_search = search.and_([
			search.search_for("year_from", 1825),
			search.search_for("year_to", 1825)
		])
		filtered_items = filter(year_search, items)
		self.assertEqual(len(list(filtered_items)), 1)

		#testing partial intersection
		year_search = search.and_([
			search.search_for("year_from", 1500),
			search.search_for("year_to", 1600)
		])
		filtered_items = filter(year_search, items)
		self.assertEqual(len(list(filtered_items)), 1)

		#testing inner containment
		year_search = search.and_([
			search.search_for("year_from", 1499),
			search.search_for("year_to", 1501)
		])
		filtered_items = filter(year_search, items)
		self.assertEqual(len(list(filtered_items)), 1)

		#testing outer containment
		year_search = search.and_([
			search.search_for("year_from", 1400),
			search.search_for("year_to", 1600)
		])
		filtered_items = filter(year_search, items)
		self.assertEqual(len(list(filtered_items)), 1)

		filtered_items = item_index["keywords"]["grumbling"]
		self.assertEqual(len(list(filtered_items)), 1)

		filtered_items = \
			item_index["keywords"]["cinquecento"] & \
			item_index["keywords"]["historical dance"]
		self.assertEqual(len(list(filtered_items)), 1)
		
	def test_inverted_index_search(self):
		items = bib_parser.BibParser().parse_string(TEST_ITEMS)
		item_index = index.Index(items)
		for item in items:
			item.finalize(item_index)
		item_index.update(items)
		
		DIRECT_KEY = "cinquecento"
		INVERTED_KEY = const.INVERTED_INDEX_KEY_PREFIX + DIRECT_KEY
		subindex = item_index["keywords"]
		self.assertIn(DIRECT_KEY, subindex)
		self.assertIn(INVERTED_KEY, subindex)
		filtered_items = item_index["keywords"][INVERTED_KEY]
		self.assertEqual(len(filtered_items), 1)
		self.assertEqual(utils.first(filtered_items).id(), "id_2")


if __name__ == "__main__":
	unittest.main()
