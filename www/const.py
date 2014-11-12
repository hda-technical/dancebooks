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
	"american": {
		"english",
	},
	"argentine": {
		"spanish",
		"portuguese",
	},
	"australian": {
		"english",
	},
	"austrian": {
		"german",
		"french",
	},
	"canadian": {
		"english",
	},
	"czech": {
		"czech",
	},
	"danish": {
		"danish",
	},
	"english": {
		"english",
	},
	"french": {
		"french",
	},
	"german": {
		"german",
	},
	"italian": {
		"italian",
	},
	"mexican": {
		"spanish",
	},
	"polish": {
		"polish",
	},
	"portuguese": {
		"portuguese",
	},
	"russian": {
		"russian",
	},
	"spanish": {
		"spanish",
	},
	"swedish": {
		"swedish",
	},
}

#a structired pattern for file basename
#any of [incomplete, commentary, translation, facsimile]
METADATA_PATTERN = r"(?:incomplete|commentary|translation|facsimile|transcription|[\w\s\-]+ copy)"
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
	r"(?P<title>[\w\d\s',\.\-–—&«»‹›„”№\(\);]+?)"
	#metadata: optional sequence of predefined values
	#   tome (, tome 2)
	#   edition (, edition 10)
	#   part(, partie 1)
	#	comma-separated list of METADATA_PATTERN in parentheses
	#   (something copy) — for books with multiple different copies known
	r"(?:"
		r"(?:, tome (?P<tome>\d+))|"
		r"(?:, number (?P<number>\d+))|"
		r"(?:, édition (?P<edition>\d+))|"
		r"(?:, partie (?P<part>\d+))|"
		r"(?: \((?P<keywords>" + METADATA_PATTERN + r"(?:, " + METADATA_PATTERN + r")*)\))"
	r")*"
	#extension: .pdf
	r"\.pdf"
)
FILENAME_REGEXP = re.compile(FILENAME_PATTERN)

VALID_HTTP_CODES = {
	#general OK
	http.client.OK,
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
