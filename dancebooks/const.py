import http.client
import re

#Two-letter country codes mapped to list of corresponding langid
#
#Most of the codes are defined in `ISO 3166-1 alpha-2` standard.
#See: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
SHORT_LANG_MAP = {
	"ar": ["spanish"],
	"at": ["german", "french", "italian"],
	"au": ["english"],
	"ca": ["english", "french"],
	"ch": ["french"],
	"cl": ["spanish"],
	"cz": ["czech", "german"],
	"de": ["german", "french"],
	"dk": ["danish"],
	"en": ["english", "latin"],
	"es": ["spanish"],
	"fi": [
		"finnish",
		# Swedish was the only official language of Finland until 1863.
		# See https://en.wikipedia.org/wiki/Finland_Swedish for details
		"swedish",
	],
	"fr": ["french", "latin"],
	"ie": ["english"],
	"it": ["italian", "french"],
	"lt": ["latvian"],
	"nl": ["dutch", "german", "french"],
	"pl": ["french", "polish"],
	"pt": ["portuguese"],
	"ru": ["russian", "french", "german"],
	"sc": ["english"],
	"si": ["slovenian", "english", "german"],
	"sw": ["swedish"],
	"ua": ["ukrainian"],
	"us": ["english"],
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
		"italian",
	},
	"canadian.bib": {
		"english",
		"french",
	},
	"chilean.bib": {
		"spanish",
	},
	"czech.bib": {
		"czech",
		"german",
	},
	"danish.bib": {
		"danish",
	},
	"dutch.bib": {
		"dutch",
		"french",
		"german",
	},
	"english.bib": {
		"english",
		"latin",
	},
	"finnish.bib": {
		"finnish",
		"swedish",
	},
	"french.bib": {
		"french",
		"latin",
	},
	"german.bib": {
		"german",
		"english",
		"french"
	},
	"italian.bib": {
		"french",
		"italian",
		"latin",
	},
	"mexican.bib": {
		"spanish",
	},
	"polish.bib": {
		"polish",
		"french",
	},
	"portuguese.bib": {
		"portuguese",
	},
	"russian.bib": {
		"german",
		"french",
		"latvian",
		"russian",
		"ukrainian",
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
METADATA_PATTERN = r"(?:incomplete|[\w\s\-\&\+\.']+ copy)"
FILENAME_PATTERN = (
	#year: digits can be replaced by dashes
	r"\[(?P<year>[\d\-]+), "
	#lang: two-letter code
	r"(?P<langid>\w{2})\] "
	#author: optional, can contain
	#   spaces (Thomas Wilson),
	#   dots (N. Malpied),
	#   commas (Louis Pecour, Jacques Dezais)
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
		r"(?:, number (?P<number>[\w\- ]+))|"
		r"(?:, édition (?P<edition>\d+))|"
		r"(?:, partie (?P<part>\d+))|"
		r"(?: \((?P<keywords>" + METADATA_PATTERN + r"(?:, " + METADATA_PATTERN + r")*)\))"
	r")*"
	#extension: .pdf (facsimiles) or .md (transcriptions) or empty (backup folders)
	r"(\.pdf|\.md|)"
	"$"
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
	#Printed books in Little-Marsh's "La danse noble"
	r"(LittleMarsh:\*?\[?c?\d{4}\]?-\w{3})|"
	#Manuscripts in Little-Marsh's "La danse noble"
	r"(LittleMarsh:Ms-\d{2})|"
	#Wilhelm Gottlieb Becker's Taschenbüchern in Lange's "Modetänze um 1800"
	r"(Lange:\d{4}(, I{1,2})?)|"
	r"(Smith:[\[\]A-Za-z\d]+)|"
	r"(Gallo:[A-Za-z']{1,3})|"
	r"(Marrocco:[A-Z\d, ]+)"
)
CATALOGUE_REGEXP = re.compile(CATALOGUE_PATTERN)
#map [catalogue type] -> (catalogue id, catalogue title)
CATALOGUE_MAP = {
	"Lancelot": ("lancelot_1996", "F. Lancelot. La belle danse"),
	"LittleMarsh": ("little_1992", "M. E. Little, C. G. Marsh. La danse noble"),
	"Lange": ("lange_1984", "E. Lange, K.-H. Lange. Modetänze um 1800"),
	"Smith": ("smith_1995", "A. W. Smith. Fifteenth Century Dance and Music"),
	"Gallo": ("gallo_1979_balare", "F. A. Gallo. Il 'Balare Lombardo'"),
	"Marrocco": ("marrocco_1981_inventory", "Inventory of 15th century Bassedanze")
}

VALID_HTTP_CODES = {
	#general OK
	http.client.OK,
	#used by books.google.com
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
BABEL_KEYWORD_CATEGORY_PREFIX = "search:keywords:category:"
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

MAX_AUTHORS_IN_CITE_LABEL = 2

CSS_CLASS_STRIKETHROUGH = "strikethrough"
CSS_CLASS_SUBSCRIPT = "subscript"
CSS_CLASS_SUPERSCRIPT = "superscript"
CSS_CLASS_SMALLCAPS = "smallcaps"
CSS_CLASS_PAGE_NUMBER = "page_number"
CSS_CLASS_NOTE = "note"
CSS_CLASS_NOTE_ANCHOR = "note_anchor"

SIZE_DELIMETER = "x"
