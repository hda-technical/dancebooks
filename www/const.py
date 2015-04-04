import http.client
import re

#two-letter country codes mapped to langid
SHORT_LANG_MAP = {
	"ar": "spanish",
	"au": "english",
	"ca": "english",
	"cz": "czech",
	"de": "german",
	"dk": "danish",
	"en": "english",
	"es": "spanish",
	"fr": "french",
	"ie": "english",
	"it": "italian",
	"pl": "polish",
	"pt": "portuguese",
	"ru": "russian",
	"sc": "english",
	"sw": "swedish",
	"us": "english",
}

#country as adjective mapped to langid
LONG_LANG_MAP = {
	"american.bib": {
		"english",
	},
	"argentine.bib": {
		"spanish",
		"portuguese",
	},
	"australian.bib": {
		"english",
	},
	"austrian.bib": {
		"german",
		"french",
	},
	"canadian.bib": {
		"english",
	},
	"czech.bib": {
		"czech",
	},
	"danish.bib": {
		"danish",
	},
	"english.bib": {
		"english",
	},
	"french.bib": {
		"french",
	},
	"german.bib": {
		"german",
	},
	"italian.bib": {
		"italian",
	},
	"mexican.bib": {
		"spanish",
	},
	"polish.bib": {
		"polish",
	},
	"portuguese.bib": {
		"portuguese",
	},
	"russian.bib": {
		"russian",
	},
	"spanish.bib": {
		"spanish",
	},
	"swedish.bib": {
		"swedish",
	},
}

META_INCOMPLETE = "incomplete"
META_HAS_OWNER = "has_owner"

#a structired pattern for file basename
METADATA_PATTERN = r"(?:incomplete|[\w\s\-\&\.']+ copy)"
FILENAME_PATTERN = (
	#year: digits can be replaced by dashes
	r"\[(?P<year>[\d\-]+), "
	#lang: two-letter code
	r"(?P<langid>\w{2})\] "
	#author: optional, can contain
	#   spaces (Thomas Wilson),
	#   dots (N. Malpied),
	#   commas (Louis Pecour, Jacque Dezais)
	#(question mark at the end makes regexp non-greedy)
	r"(?:(?P<author>[\w\s\.,'\-]+?) - )?"
	#title: sequence of words, digits, spaces, punctuation
	#(question mark at the end makes regexp non-greedy)
	r"(?P<title>[\w\d\s',\.\-–—&«»‹›„”“№!\?\(\);]+?)"
	#metadata: optional sequence of predefined values
	#   tome (, tome 2)
	#   edition (, edition 10)
	#   part(, partie 1)
	#	comma-separated list of METADATA_PATTERN in parentheses
	#   (something copy) — for books with multiple different copies known
	r"(?:"
		r"(?:, tome (?P<volume>\d+))|"
		r"(?:, number (?P<number>\d+))|"
		r"(?:, édition (?P<edition>\d+))|"
		r"(?:, partie (?P<part>\d+))|"
		r"(?: \((?P<keywords>" + METADATA_PATTERN + r"(?:, " + METADATA_PATTERN + r")*)\))"
	r")*"
	#extension: .pdf
	r"\.pdf"
)
FILENAME_REGEXP = re.compile(FILENAME_PATTERN)

ID_PATTERN = r"[a-z][a-z_0-9]+"
ID_REGEXP = re.compile(ID_PATTERN)

VALID_HTTP_CODES = {
	#general OK
	http.client.OK,
	#
	#adding http.client.MOVED_PERMANENTLY
	#considered as error here
	#
	#used by hdl.loc.gov
	http.client.FOUND,
	#used by hdl.handle.net
	http.client.SEE_OTHER,
	#used by uni-goettingen.de
	http.client.TEMPORARY_REDIRECT
}

ENV_CONFIG = "CONFIG"
ENV_LOGGING_CONFIG = "LOGGING_CONFIG"

DEFAULT_ORDER_BY = "year_from"

BABEL_LANG_PREFIX = "search:language:"
BABEL_KEYWORD_CATEGORY_PREFIX = "pages:keywords:category:"
BABEL_KEYWORD_REF_PREFIX = "pages:keywords:ref:"

#separator of keyword sublevels
KEYWORD_SEPARATOR = ":"

FILE_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
FILE_SIZE_EXPONENT = 1024
FILE_SIZE_PARAM = "filesize"

#libraries that've allowed
#to share their books via bib.hda.org.ru
KNOWN_LIBRARIES = {
	#Russian State Library (aka Leninka)
	"RSL",
	#National Library of Russia (aka Publichka)
	"NLR",
}

#users that've allowed
#to share their books via bib.hda.org.ru
KNOWN_BOOKKEEPERS = {
	"Bodhi",
	"Garold",
	"Georg",
	"Glorf",
	"Rostik",
}

SECONDS_IN_YEAR = 60 * 60 * 24 * 365
