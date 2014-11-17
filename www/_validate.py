#!/usr/bin/env python3
import os.path
import re
import sys

import opster

from config import config
import const
import index
import bib_parser
import utils

items = bib_parser.BibParser().parse_folder(os.path.abspath("../bib"))
item_index = index.Index(items)
for item in items:
	item.process_crossrefs(item_index)
item_index.update(items)

languages = sorted(item_index["langid"].keys())

@opster.command()
def main(
	strict=("", False, "Add some extra checks (includes HTTP HEAD requests)")
):
	"""
	Validates bibliography over a bunch of rules
	"""
	if not os.path.isdir(config.www.elibrary_root):
		print("root folder '{elibrary_root}' is inaccessible".format(
			elibrary_root=config.www.elibrary_root
		))
		sys.exit(1)

	print("Going to process {0} items".format(len(items)))

	SOURCE_REGEXP = re.compile("(?P<basename>[_\-\w\.]+).bib:\d+")
	ID_REGEXP = re.compile("[a-z][a-z_0-9]+")
	MULTILANG_FILES = {"proceedings-spb", "proceedings-rothenfelser", "_problems"}
	VALID_BOOKTYPES = {
		"book",
		"mvbook",
		"inproceedings",
		"proceedings",
		"reference",
		"mvreference",
		"periodical",
		"unpublished",
		"thesis",
		"article"
	}
	NON_MULTIVOLUME_BOOKTYPES = {"article", "periodical"}
	MULTIVOLUME_BOOKTYPES = {"mvbook", "mvreference"}

	#don't validate filename for the given entrytypes
	MULTIENTRY_BOOKTYPES = {"proceedings", "inproceedings"}
	SHORTHAND_LIMIT = 25

	PERIODICAL_BOOKTYPES = {"periodical"}

	UNPUBLISHED_NOTE_PREFIX = "Unpublished manuscript"

	ALLOWED_KEYWORDS = {
		#baroque related tags (XVII–XVIII century)
		"galliard",
		"saraband",
		"courant",
		"minuet",
		"gavotte",
		"allemande",
		"landler",
		"perigourdine",
		#country dance related tags
		"cotillon: 18th century",
		"cotillon: douze",
		"cotillon: seize",
		"cotillon: doppel-quadrille",
		"cotillon: vingt-quatre",
		"anglaise",
		"anglaise: francaise",
		"anglaise: matredour",
		"anglaise: money musk",
		"anglaise: pop goes the weasel",
		"ecossaise",
		"ecossaise: two columns",
		"swedish dance",
		"tempete",
		"circle",
		"sir roger de coverly",
		"la boulanger",
		"rustic reel",
		"spanish dance",
		#19th century related tags
		"minuet",
		"grossfater",
		"allemande",
		"landler",
		"bogentanz",
		"monferine",
		"quadrille",
		"quadrille: contredanse",
		"quadrille: first set",
		"quadrille: lancers",
		"quadrille: caledonians",
		"quadrille: prince imperial",
		"quadrille: varietes parisiennes",
		"waltz",
		"waltz: trois temps",
		"waltz: sautese",
		"waltz: deux temps",
		"waltz: new trois temps",
		"waltz: boston",
		"waltz: hesitation",
		"waltz: glide",
		"waltz: five steps",
		"mazurka",
		"polonaise",
		"cotillon: 19th century",
		"fandango",
		"galop",
		"polka",
		"polka-mazurka",
		"redowa",
		"schottische",
		"hongroise",
		"sequence",
		"tango",
		"character dance",
		"promiscuous figures",
		"march",
		"stage dance",
		"folk dance",
		"folk dance: country bumpkin",
		#20th century related tags
		"one-step",
		"two-step",
		"three-step",
		"foxtrot",
		"tango",
		"waltz",
		"waltz: hesitation",
		"waltz: boston",
		"waltz: canter",
		"half and half",
		"animal dance",
		"animal dance: grizzly bear",
		"animal dance: turkey trot",
		"castle walk",
		"sequence",
		"mixer dance",
		"cakewalk",
		"swing",
		#extra tags
		"antidance",
		"belles-lettres",
		"commentary",
		"dance description",
		"dance instruction",
		"essay",
		"etiquette",
		"facsimile",
		"first edition",
		"libretto",
		"markdown",
		"memoirs",
		"music",
		"not digitized",
		"reissue",
		"research",
		"steps",
		"transcription",
		"useless",
	}

	erroneous_entries = 0
	errors_count = 0
	for item in items:
		errors = []
		#datamodel validation
		author = item.get("author")
		booktype = item.get("booktype").lower()
		booktitle = item.get("booktitle")
		commentator = item.get("commentator")
		crossref = item.get("crossref")
		edition = item.get("edition")
		filename = item.get("filename")
		id = item.get("id")
		isbn = item.get("isbn")
		institution = item.get("institution")
		journaltitle = item.get("journaltitle")
		keywords = set(item.get("keywords") or {})
		langid = item.get("langid")
		location = item.get("location")
		note = item.get("note")
		number = item.get("number")
		origlanguage = item.get("origlanguage")
		origauthor = item.get("origauthor")
		publisher = item.get("publisher")
		series = item.get("series")
		shorthand = item.get("shorthand")
		source = item.get("source")
		title = item.get("title")
		translator = item.get("translator")
		type = item.get("type")
		url = item.get("url")
		volume = item.get("volume")
		volumes = item.get("volumes")
		year = item.get("year")
		year_from = item.get("year_from")
		year_to = item.get("year_to")
		year_circa = item.get("year_circa")
		added_on = item.get("added_on")

		match = SOURCE_REGEXP.match(source)
		if not match:
			raise RuntimeError("Failed to parse 'source' for item ({id})".format(
				id=id
			))
		source_basename = match.group("basename")

		parser_obligatory = [id, booktype, source, year_from, year_to, year_circa]
		none_checker = lambda obj: obj is not None
		if not all(map(none_checker, parser_obligatory)):
			raise RuntimeError("Parser hasn't generated all required auxiliary fields {fields}".format(
				fields=parser_obligatory
			))
			
		if not ID_REGEXP.match(id):
			errors.append("Id {id} doesn't match ID_REGEXP".format(
				id=id
			))

		general_obligatory = [langid, year, title, added_on]
		if not all(general_obligatory):
			errors.append("Item doesn't define one of [langid, year, title, added_on]")


		translation_obligatory = [origlanguage, translator]
		if any(translation_obligatory):
			if not all(translation_obligatory):
				errors.append("[origlanguage, translator] must be present for translations")

			if not origauthor:
				errors.append("'origauthor' must be present for translations")

		series_obligatory = [series, number]
		if not utils.all_or_none(series_obligatory) and (booktype not in PERIODICAL_BOOKTYPES):
			errors.append("All of [series, number] must be present for serial books")

		if not any([author, shorthand]):
			errors.append("'author' or 'shorthand' must be present")

		if (publisher is not None) and (location is None):
			errors.append("If publisher present, location must be present")

		#booktype validation
		booktype = booktype.lower()
		if booktype not in VALID_BOOKTYPES:
			errors.append("Invalid booktype ({booktype})".format(
				booktype=booktype
			))

		if (booktype not in NON_MULTIVOLUME_BOOKTYPES):
			if (volume is not None) and (volumes is None):
				errors.append("If volume present, volumes must be present")

		if (booktype in MULTIVOLUME_BOOKTYPES):
			if volumes is None:
				errors.append("volumes must be present for @{0}".format(booktype))

		if (booktype == "article"):
			if journaltitle is None:
				errors.append("journaltitle must be present for @article")

		if (booktype == "inproceedings"):
			if booktitle is None:
				errors.append("booktitle must be present for @inprocessing")

		if (booktype == "thesis"):
			if type is None:
				errors.append("type must be present for @thesis")
			if institution is None:
				errors.append("institution must be present for @thesis")

		#data validation
		#author validation empty

		#booktitle validation empty
		
		if crossref:
			referenced_title = utils.first(item_index["id"][crossref]).get("title")
			if booktitle != referenced_title:
				errors.append("booktitle doesn't match referenced book title")

		#commentator
		if commentator is not None:
			if (keywords is None) or ("commentary" not in keywords):
				errors.append("Keywords should contain 'commentary' when commentator specified")

		#filename validation
		if edition is not None:
			#edition should be greater than 1
			if edition <= 1:
				errors.append("Wrong edition {edition}".format(
					edition=edition
				))

		if volume is not None:
			#volume should be positive integer
			if volume <= 0:
				errors.append("Wrong volume {volume}".format(
					volume=volume
				))
			if volumes is not None:
				if volume > volumes:
					errors.append("Volume ({volume}) can't be greater than volumes ({volumes})".format(
						volume=volume,
						volumes=volumes
					))

		#filename validation
		if (filename is not None) and (booktype not in MULTIENTRY_BOOKTYPES):
			for filename_ in filename:
				#filename starts with "/" which will mix os.path.join up
				abspath = os.path.join(config.www.elibrary_root, filename_[1:])
				#each filename should be accessible
				if not os.path.isfile(abspath):
					errors.append("File {filename_} is not accessible".format(
						filename_=filename_
					))

				#item should be searchable by its filename metadata
				metadata = utils.extract_metadata_from_file(filename_)

				#validating optional author, edition, tome
				#in case when item specifies value, but filename doesn't
				if not utils.all_or_none([metadata.get("author", None), author]):
					errors.append("File {filename_} and entry have different author specifications".format(
						filename_=filename_
					))

				if not utils.all_or_none([metadata.get("edition", None), edition]):
					errors.append("File {filename_} and entry have different edition specifications".format(
						filename_=filename_
					))

				if not utils.all_or_none([metadata.get("tome", None), any([volume, volumes])]):
					errors.append("File {filename_} and entry have different volume specifications".format(
						filename_=filename_
					))

				if not utils.all_or_none([metadata.get("number", None), number]) and not series:
					errors.append("File {filename_} and entry have different number specifications".format(
						filename_=filename_
					))

				meta_keywords = metadata.get("keywords", None)
				if meta_keywords is not None:
					if ("incomplete" in meta_keywords) and (source_basename != "_problems"):
						errors.append("Incomplete books should be stored in _problems.bib")
					meta_keywords.discard("incomplete")

					if len(meta_keywords) > 0:
						if keywords is None:
							errors.append("No keywords specified (should be {meta_keywords}".format(
								meta_keywords=meta_keywords
							))
						elif not keywords >= meta_keywords:
							errors.append("Item keywords {keywords} do not match metadata keywords {meta_keywords}".format(
								keywords=keywords,
								meta_keywords=meta_keywords
							))

				search_ = utils.create_search_from_metadata(metadata)
				if not search_(item):
					errors.append(
"""
File {filename_} is not searchable by extracted params
	extracted author: {author},
	extracted title: {title},
	extracted year_from: {year_from},
	extracted year_to: {year_to}
""".format(
	filename_=filename_,
	author=metadata.get("author", ""),
	title=metadata.get("title", ""),
	year_from=metadata.get("year_from", ""),
	year_to=metadata.get("year_to", "")
))
		#id validation empty
		if len(item_index["id"][id]) != 1:
			errors.append("Id is not unique")

		#isbn validation
		if isbn is not None:
			for isbn_ in isbn:
				correct, msg = utils.is_isbn_valid(isbn_)
				if not correct:
					errors.append("ISBN {isbn_} isn't valid: {msg}".format(
						isbn_=isbn_,
						msg=msg
					))

		#institution validation empty

		#journaltitle validation empty

		#keywords validation
		if (keywords is not None):
			unallowed_keywords = (keywords - ALLOWED_KEYWORDS)
			if unallowed_keywords:
				errors.append("Entry has unallowed keywords: {keywords}".format(
					keywords=unallowed_keywords
				))
			if ("commentary" in keywords) and not commentator:
				errors.append("When 'commentary' keyword specified, commentator should be present")
			for keyword in keywords:
				colon_pos = keyword.find(":")
				if colon_pos != -1:
					parent_keyword = keyword[:colon_pos]
					if (
						(parent_keyword in ALLOWED_KEYWORDS) and
						(not parent_keyword in keywords)
					):
						errors.append("Parent keyword {parent_keyword} for keyword {keyword} is missing".format(
							parent_keyword=parent_keyword,
							keyword=keyword
						))
			if ("useless" in keywords) and (len(keywords) != 1):
				errors.append("'useless' keywords can't be combined with any other keywords")

		#langid validation
		if source_basename not in MULTILANG_FILES:
			source_langs = const.LONG_LANG_MAP[source_basename]
			#item language should match any of source languages
			if langid not in source_langs:
				errors.append("Source languages {source_langs} doesn't match item language ({langid})".format(
					source_langs=list(source_langs),
					langid=langid
				))
		#location validation empty

		#note validation
		note_unpublished = (note is not None) and (note.startswith(UNPUBLISHED_NOTE_PREFIX))
		booktype_unpublished = (booktype == "unpublished")
		if not utils.all_or_none([note_unpublished, booktype_unpublished]):
			errors.append("For unpublished books, note should begin with [{note_prefix}] and booktype should be {booktype}".format(
				booktype="unpublished",
				note_prefix=UNPUBLISHED_NOTE_PREFIX
			))


		#number validation empty

		#publisher validation empty

		#series validation empty

		#shorthand validation empty
		if shorthand is not None:
			length = len(shorthand)
			if length > SHORTHAND_LIMIT:
				errors.append("The length of shorthand ({length}) should not exceed limit ({limit})".format(
					length=length,
					limit=SHORTHAND_LIMIT
				))
			if strict and not author and (not title.startswith(shorthand)):
				errors.append("Title ({title}) should begin with from shorthand ({shorthand})".format(
					title=title,
					shorthand=shorthand
				))

		#source validation empty

		#title validation empty
		if title is not None:
			if ("  " in title):
				errors.append("Consecutive spaces in title")
			if ("\t" in title):
				errors.append("Tabs in title")
			if title.startswith(" ") or title.endswith(" "):
				errors.append("Title isn't stripped")

		#type validation empty

		#url validation empty
		if url is not None:
			for signle_url in url:
				correct, msg = utils.is_url_valid(signle_url, strict)
				if not correct:
					errors.append("URL {signle_url} isn't valid: {msg}".format(
						signle_url=signle_url,
						msg=msg
					))

		#volume validation empty

		#volumes validation empty

		#year validation empty

		#printing errors
		if len(errors) > 0:
			erroneous_entries += 1
			errors_count += len(errors)
			print("Errors for {id} ({source})".format(
				id=id,
				source=source
			))
			for error in errors:
				print("    " + error)

	print("Found {entries} erroneous entries ({errors} errors)".format(
		entries=erroneous_entries,
		errors=errors_count
	))


if __name__ == "__main__":
	main.command()
