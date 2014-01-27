#web app options
APP_PREFIX = "/bib"
BOOK_PREFIX = APP_PREFIX + "/book"

#options actual for parsing
#parameters containing lists
LIST_PARAMS = set(["location", "isbn", "origlanguage", "filename"])
#parameters containing names
NAME_PARAMS = set(["author", "publisher", "translator"])
GENERAL_SEP = "|"

#parameters containing keywords
KEYWORD_PARAMS = set(["keywords"])
KEYWORD_SEP = ","

#parameters containing integers
INT_PARAMS = set(["volume", "volumes", "edition", "part", "number"])

#union of all the above
MULTI_VALUE_PARAMS = LIST_PARAMS | NAME_PARAMS | KEYWORD_PARAMS

#indices to be created
INDEX_KEYS = set(["id", "langid", "keywords", "filename"])

#options actual for searching
#available search keys
AVAILABLE_SEARCH_KEYS = set([
	"author", "title", "langid", "publisher", "location", "keywords"
])
INDEXED_SEARCH_KEYS = AVAILABLE_SEARCH_KEYS & INDEX_KEYS
NONINDEXED_SEARCH_KEYS = AVAILABLE_SEARCH_KEYS - INDEX_KEYS

#parameters for year searching
YEAR_PARAM = "year"
YEAR_TO_PARAM = "year_to"
YEAR_FROM_PARAM = "year_from"

#options actual for output
#output list separator
OUTPUT_LISTSEP = ", "

#languages, supported by this website
LANGUAGES = ["en", "ru"]

BUG_REPORT_EMAIL = "georgthegreat@gmail.com"
BUG_REPORT_NAME = "Yuriy Chernyshov"
BUG_REPORT_SMTP_HOST = "smtp.yandex.ru"
BUG_REPORT_SMTP_PORT = 587

#two-letter country codes mapped to langid
SHORT_LANG_MAP = {
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
	"us": "english"
}

#country as adjective mapped to langid
LONG_LANG_MAP = {
	"american": "english",
	"australian": "english",
	"austrian": "german",
	"canadian": "english",
	"czech": "czech",
	"danish": "danish",
	"english": "english",
	"french": "french",
	"german": "german",
	"italian": "italian",
	"mexican": "spanish",
	"polish": "polish",
	"portuguese": "portuguese",
	"russian": "russian",
	"spanish": "spanish"
}

