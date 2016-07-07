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
#ln is currently unassigned according to https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
	"ln": "latin",
	"pl": "polish",
	"pt": "portuguese",
	"ru": "russian",
	"sc": "english",
	"sw": "swedish",
	"us": "english",
}

#filename mapped to langid
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
		"french"
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
		"latin"
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
	#extension: .pdf (facsimiles) or .md (transcriptions)
	r"\.(pdf|md)"
)
FILENAME_REGEXP = re.compile(FILENAME_PATTERN)

ID_PATTERN = r"[a-z][a-z_0-9]+"
ID_REGEXP = re.compile(ID_PATTERN)

PAGES_PATTERN = r"\d+(–\d+)?"
PAGES_REGEXP = re.compile(PAGES_PATTERN)

CATALOGUE_PATTERN = (
	#Printed books in Francine Lancelot's "La belle danse"
	r"(Lancelot:\d{4}\.\d)|"
	#Manuscripts in Francine Lancelot's "La belle danse"
	r"(Lancelot:Ms\d{2})|"
	#‹Ludus Pastorali› manuscript from Francine Lancelot's "La belle danse"
	r"(Lancelot:Addendum)|"
	#Printed books in Little-Mars's "La danse noble"
	r"(LittleMarsh:\*?\[?c?\d{4}\]?-\w{3})|"
	#Manuscripts in Little-Mars's "La danse noble"
	r"(LittleMarsh:Ms-\d{2})|"
	#Wilhelm Gottlieb Becker's Taschenbüchern in Lange's "Modetänze um 1800"
	r"(Lange:\d{4}(, I{1,2})?)"
)
CATALOGUE_REGEXP = re.compile(CATALOGUE_PATTERN)
#map [catalogue type] -> (catalogue id, catalogue title)
CATALOGUE_MAP = {
	"Lancelot": ("lancelot_1996", "F. Lancelot. La belle danse"),
	"LittleMarsh": ("little_1992", "M. E. Little, C. G. Marsh. La danse noble"),
	"Lange": ("lange_1984", "E. Lange, K.-H. Lange. Modetänze um 1800"),
}

CONFIG_PATTERN = r"dancebooks\.(?P<mode>\w+)\.conf"
CONFIG_REGEXP = re.compile(CONFIG_PATTERN)

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
BABEL_BOOKTYPE_PREFIX = "search:booktype:"
BABEL_KEYWORD_CATEGORY_PREFIX = "pages:keywords:category:"
BABEL_KEYWORD_REF_PREFIX = "pages:keywords:ref:"
BABEL_MISSING_ERROR_PREFIX = "errors:missing:"
BABEL_WRONG_ERROR_PREFIX = "errors:wrong:"
BABEL_MONTH_PREFIX = "common:month:"

#separator of keyword sublevels
KEYWORD_SEPARATOR = ":"
CATALOGUE_SEPARATOR = ":"

FILE_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
FILE_SIZE_EXPONENT = 1024
FILE_SIZE_PARAM = "filesize"

SECONDS_IN_YEAR = 60 * 60 * 24 * 365

INVERTED_INDEX_KEY_PREFIX = "!"
