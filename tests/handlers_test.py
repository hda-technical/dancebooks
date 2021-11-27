#!/usr/bin/env python3
#coding: utf-8

import http.client
import json
import logging
import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from www import main

#normal book id, available for downloading pdf file of it
DOWNLOADABLE_BOOK_ID = "zarman_1905_russlav"
#normal book id, unavailable for download
UNDOWNLOADABLE_BOOK_ID = "wilson_1818_ecossoise"
#outdated book id, redirection to DOWNLOADABLE_BOOK_ID
OUTDATED_BOOK_ID = "zarman_1905"
#transcribed book id, transcription should be available
MARKDOWNED_BOOK_ID = "wilson_1824"
#not transcribed book id
NOT_MARKDOWNED_BOOK_ID = "cellarius_1848_russian"
#book with keywords "quadrille" and "polka" set
KEYWORDED_BOOK_ID = "glover_1846_lee_walker"

BOOK_IDS = [
	DOWNLOADABLE_BOOK_ID,
	UNDOWNLOADABLE_BOOK_ID,
	OUTDATED_BOOK_ID,
	MARKDOWNED_BOOK_ID,
	KEYWORDED_BOOK_ID,
]

@pytest.fixture
def client():
	return main.flask_app.test_client()


def test_html_handlers(client):
	rq = client.get("/")
	assert rq.status_code == http.client.OK

	rq = client.get("/ui-lang/ru")
	assert rq.status_code == http.client.FOUND
	assert "Set-Cookie" in rq.headers

	for book_id in BOOK_IDS:
		logging.debug(f"Requesting book: {book_id}")
		rq = client.get(
			"/books/" + book_id,
			follow_redirects=True
		)
		assert rq.status_code == http.client.OK

	rq = client.get(
		"/books/" + OUTDATED_BOOK_ID
	)
	assert rq.status_code == http.client.MOVED_PERMANENTLY


def test_search(client):
	# testing basic search
	rq = client.get("/basic-search", query_string={
		"author": "Wilson",
		"title": "Ecossoise",
	})
	assert rq.status_code == http.client.OK
	assert UNDOWNLOADABLE_BOOK_ID in rq.data.decode()

	# testing advanced search by multiple keywords
	rq = client.get("/advanced-search", query_string={
		"keywords": "quadrille, polka"
	})
	assert rq.status_code == http.client.OK
	assert KEYWORDED_BOOK_ID in rq.data.decode()


def test_post_keywords_handler(client):
	# testing sending correct data
	rq = client.post(
		"/books/" + DOWNLOADABLE_BOOK_ID + "/keywords",
		data = {
			"keywords": "music, dance description, quadrille: first set",
			"name": "Александр Сергеевич Пушкин",
			"email": "pushkin@lyceum.net",
			"captcha_key": "louis-naissanse",
			"captcha_answer": "1638",
		}
	)
	assert rq.status_code == http.client.OK
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())
	assert "message" in data

	# testing submit without captcha authorization
	rq = client.post(
		"/books/" + DOWNLOADABLE_BOOK_ID + "/keywords",
		data = {
			"keywords": "music, dance description, quadrille: first set",
			"name": "Александр Сергеевич Пушкин",
			"email": "pushkin@lyceum.net",
		}
	)
	assert rq.status_code == http.client.FORBIDDEN
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data)
	assert "message" in data

	# testing submit with invalid email
	rq = client.post(
		"/books/" + DOWNLOADABLE_BOOK_ID + "/keywords",
		data = {
			"keywords": "music, dance description, quadrille: first set",
			"name": "Александр Сергеевич Пушкин",
			"email": "spamers_go_away",
		}
	)
	assert rq.status_code == http.client.FORBIDDEN
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())
	assert "message" in data

	# testing submit with invalid keywords
	rq = client.post(
		"/books/" + DOWNLOADABLE_BOOK_ID + "/keywords",
		data = {
			"keywords": "music, dance description, quadrille: first set, long-and-probably-unallowed-keyword",
			"name": "Александр Сергеевич Пушкин",
			"email": "pushkin@lyceum.net",
			"captcha_key": "louis-naissanse",
			"captcha_answer": "1638",
		}
	)
	assert rq.status_code == http.client.BAD_REQUEST
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())
	assert "message" in data


def test_post_bug_handler(client):
	# testing sending correct data
	rq = client.post(
		"/books/" + DOWNLOADABLE_BOOK_ID,
		data = {
			"message": "There is a problem with the book. Мой дядя самых честных правил",
			"name": "Александр Сергеевич Пушкин",
			"email": "pushkin@lyceum.net",
			"captcha_key": "louis-naissanse",
			"captcha_answer": "1638",
		}
	)
	assert rq.status_code == http.client.OK
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())
	assert "message" in data

	# test sending correct data with redirect
	rq = client.post(
		"/books/" + OUTDATED_BOOK_ID,
		data = {
			"message": "There is a problem with the book. Мой дядя самых честных правил",
			"name": "Александр Сергеевич Пушкин",
			"email": "pushkin@lyceum.net",
			"captcha_key": "louis-naissanse",
			"captcha_answer": "1638",
		},
		follow_redirects=True
	)
	assert rq.status_code == http.client.NOT_FOUND
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())
	assert "message" in data

	# testing submit without captch authorization
	rq = client.post(
		"/books/" + DOWNLOADABLE_BOOK_ID,
		data = {
			"message": "There is a problem with the book. Мой дядя самых честных правил",
			"name": "Александр Сергеевич Пушкин",
			"email": "pushkin@lyceum.net",
		}
	)
	assert rq.status_code == http.client.FORBIDDEN
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())
	assert "message" in data

	# testing submit with invalid email
	rq = client.post(
		"/books/" + DOWNLOADABLE_BOOK_ID,
		data = {
			"message": "There is a problem with the book. Мой дядя самых честных правил",
			"name": "Александр Сергеевич Пушкин",
			"email": "spamers_go_away",
			"captcha_key": "louis-naissanse",
			"captcha_answer": "1638",
		}
	)
	assert rq.status_code == http.client.BAD_REQUEST
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())
	assert "message" in data


def test_pdf_handlers(client):
	rq = client.get(
		"/books/" + DOWNLOADABLE_BOOK_ID + "/pdf/1",
		follow_redirects=True
	)
	assert rq.status_code == http.client.OK
	assert rq.content_type == "application/pdf"
	assert "Content-Disposition" in rq.headers

	rq = client.get(
		"/books/" + UNDOWNLOADABLE_BOOK_ID + "/pdf/1",
		follow_redirects=True
	)
	assert rq.status_code == http.client.NOT_FOUND

	rq = client.get(
		"/books/" + OUTDATED_BOOK_ID + "/pdf/1",
		follow_redirects=True
	)
	assert rq.status_code == http.client.OK


def test_transcription_handlers(client):
	rq = client.get(
		"/books/" + MARKDOWNED_BOOK_ID + "/transcription",
		follow_redirects=True
	)
	assert rq.status_code == http.client.OK
	assert rq.content_type == "text/html; charset=utf-8"

	rq = client.get(
		"/books/" + NOT_MARKDOWNED_BOOK_ID + "/transcription",
		follow_redirects=True
	)
	assert rq.status_code == http.client.NOT_FOUND

	# WARN: NO TEST FOR OUTDATED MARKDOWNED BOOK ID


def test_json_handlers(client):
	rq = client.get("/options")
	assert rq.status_code == http.client.OK
	assert rq.content_type == "application/json; charset=utf-8"
	data = json.loads(rq.data.decode())

	assert "keywords" in data
	assert "source_files" in data
	assert "languages" in data


def test_rss_handlers(client):
	rq = client.get("/rss/books")
	assert rq.status_code == http.client.FOUND

	rq = client.get("/rss/en/books")
	assert rq.status_code == http.client.OK
	assert rq.content_type == "application/rss+xml; charset=utf-8"

	rq = client.get("/rss/ru/books")
	assert rq.status_code == http.client.OK
	assert rq.content_type == "application/rss+xml; charset=utf-8"
