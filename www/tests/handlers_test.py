#!/usr/bin/env python3
#coding: utf-8
import http.client
import json
import logging
import unittest

from config import config
import main

#normal book id, available for downloading pdf file of it
TEST_DOWNLOADABLE_BOOK_ID = "zarman_1905_russlav"
#normal book id, unavailable for download
TEST_UNDOWNLOADABLE_BOOK_ID = "wilson_1818_ecossoise"
#outdated book id, redirection to TEST_DOWNLOADABLE_BOOK_ID
TEST_OUTDATED_BOOK_ID = "zarman_1905"
#transcribed book id, transcription should be available
TEST_MARKDOWNED_BOOK_ID = "wilson_1824"
#not transcribed book id
TEST_NOT_MARKDOWNED_BOOK_ID = "cellarius_1848_russian"
#book with keywords "quadrille" and "polka" set
TEST_KEYWORDED_BOOK_ID = "glover_1846_lee_walker"

BOOK_IDS = [
	TEST_DOWNLOADABLE_BOOK_ID,
	TEST_UNDOWNLOADABLE_BOOK_ID,
	TEST_OUTDATED_BOOK_ID,
	TEST_MARKDOWNED_BOOK_ID,
	TEST_KEYWORDED_BOOK_ID
]

class TestHandlers(unittest.TestCase):
	"""
	Tests some of the handles to be accessible and return correct result
	"""
	def setUp(self):
		self.client = main.flask_app.test_client()

	def test_html_handlers(self):
		rq = self.client.get("/")
		self.assertEqual(rq.status_code, http.client.OK)

		rq = self.client.get("/ui-lang/ru")
		self.assertEqual(rq.status_code, http.client.FOUND)
		self.assertTrue("Set-Cookie" in rq.headers)

		for book_id in BOOK_IDS:
			logging.debug("Requesting book: {book_id}".format(
				book_id=book_id
			))
			rq = self.client.get(
				config.www.books_prefix + "/" + book_id,
				follow_redirects=True
			)
			self.assertEqual(rq.status_code, http.client.OK)

		rq = self.client.get(
			config.www.books_prefix + "/" + TEST_OUTDATED_BOOK_ID
		)
		self.assertEqual(rq.status_code, http.client.MOVED_PERMANENTLY)

	def test_search(self):
		#testing basic search
		rq = self.client.get("/basic-search", query_string={
			"author": "Wilson",
			"title": "Ecossoise",
		})
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertTrue(TEST_UNDOWNLOADABLE_BOOK_ID in rq.data.decode())

		#testing advanced search by multiple keywords
		rq = self.client.get("/advanced-search", query_string={
			"keywords": "quadrille, polka"
		})
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertTrue(TEST_KEYWORDED_BOOK_ID in rq.data.decode())

	def test_post_keywords_handler(self):
		#testing sending  correct data
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID + "/keywords",
			data = {
				"keywords": "music, dance description, quadrille: first set",
				"name": "Александр Сергеевич Пушкин",
				"email": "pushkin@lyceum.net",
				"captcha_key": "louis-naissanse",
				"captcha_answer": "1638",
			}
		)
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

		#testing submit without captcha authorization
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID + "/keywords",
			data = {
				"keywords": "music, dance description, quadrille: first set",
				"name": "Александр Сергеевич Пушкин",
				"email": "pushkin@lyceum.net",
			}
		)
		self.assertEqual(rq.status_code, http.client.FORBIDDEN)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

		#testing submit with invalid email
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID + "/keywords",
			data = {
				"keywords": "music, dance description, quadrille: first set",
				"name": "Александр Сергеевич Пушкин",
				"email": "spamers_go_away",
			}
		)
		self.assertEqual(rq.status_code, http.client.FORBIDDEN)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

		#testing submit with invalid keywords
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID + "/keywords",
			data = {
				"keywords": "music, dance description, quadrille: first set, long-and-probably-unallowed-keyword",
				"name": "Александр Сергеевич Пушкин",
				"email": "pushkin@lyceum.net",
				"captcha_key": "louis-naissanse",
				"captcha_answer": "1638",
			}
		)
		self.assertEqual(rq.status_code, http.client.BAD_REQUEST)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

	def test_post_bug_handler(self):
		#testing sending correct data
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID,
			data = {
				"message": "There is a problem with the book. Мой дядя самых честных правил",
				"name": "Александр Сергеевич Пушкин",
				"email": "pushkin@lyceum.net",
				"captcha_key": "louis-naissanse",
				"captcha_answer": "1638",
			}
		)
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

		#test sending correct data with redirect
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_OUTDATED_BOOK_ID,
			data = {
				"message": "There is a problem with the book. Мой дядя самых честных правил",
				"name": "Александр Сергеевич Пушкин",
				"email": "pushkin@lyceum.net",
				"captcha_key": "louis-naissanse",
				"captcha_answer": "1638",
			},
			follow_redirects=True
		)
		self.assertEqual(rq.status_code, http.client.NOT_FOUND)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

		#testing submit without captch authorization
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID,
			data = {
				"message": "There is a problem with the book. Мой дядя самых честных правил",
				"name": "Александр Сергеевич Пушкин",
				"email": "pushkin@lyceum.net",
			}
		)
		self.assertEqual(rq.status_code, http.client.FORBIDDEN)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

		#testing submit with invalid email
		rq = self.client.post(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID,

			data = {
				"message": "There is a problem with the book. Мой дядя самых честных правил",
				"name": "Александр Сергеевич Пушкин",
				"email": "spamers_go_away",
				"captcha_key": "louis-naissanse",
				"captcha_answer": "1638",
			}
		)
		self.assertEqual(rq.status_code, http.client.BAD_REQUEST)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("message" in data)

	def test_pdf_handlers(self):
		rq = self.client.get(
			config.www.books_prefix + "/" + TEST_DOWNLOADABLE_BOOK_ID + "/pdf/1",
			follow_redirects=True
		)
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertEqual(rq.content_type, "application/pdf")
		self.assertTrue("Content-Disposition" in rq.headers)

		rq = self.client.get(
			config.www.books_prefix + "/" + TEST_UNDOWNLOADABLE_BOOK_ID + "/pdf/1",
			follow_redirects=True
		)
		self.assertEqual(rq.status_code, http.client.NOT_FOUND)

		rq = self.client.get(
			config.www.books_prefix + "/" + TEST_OUTDATED_BOOK_ID + "/pdf/1",
			follow_redirects=True
		)
		self.assertEqual(rq.status_code, http.client.OK)

	def test_transcription_handlers(self):
		rq = self.client.get(
			config.www.books_prefix + "/" + TEST_MARKDOWNED_BOOK_ID + "/transcription",
			follow_redirects=True
		)
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertEqual(rq.content_type, "text/html; charset=utf-8")

		rq = self.client.get(
			config.www.books_prefix + "/" + TEST_NOT_MARKDOWNED_BOOK_ID + "/transcription",
			follow_redirects=True
		)
		self.assertEqual(rq.status_code, http.client.NOT_FOUND)

		#WARN: NO TEST FOR OUTDATED MARKDOWNED BOOK ID

	def test_json_handlers(self):
		rq = self.client.get("/options")
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertEqual(rq.content_type, "application/json; charset=utf-8")
		data = json.loads(rq.data.decode())
		self.assertTrue("keywords" in data)
		self.assertTrue("source_files" in data)
		self.assertTrue("languages" in data)

	def test_rss_handlers(self):
		rq = self.client.get("/rss/books")
		self.assertEqual(rq.status_code, http.client.FOUND)

		rq = self.client.get("/rss/en/books")
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertEqual(rq.content_type, "application/rss+xml; charset=utf-8")

		rq = self.client.get("/rss/ru/books")
		self.assertEqual(rq.status_code, http.client.OK)
		self.assertEqual(rq.content_type, "application/rss+xml; charset=utf-8")


if __name__ == "__main__":
	unittest.main()
