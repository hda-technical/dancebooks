import logging
import os.path
import re
import threading
import xml.etree.ElementTree as xml
from urllib import parse as urlparse

import markdown

from dancebooks import const
from dancebooks import utils


CSS_CLASS_STRIKETHROUGH = "strikethrough"
CSS_CLASS_SUBSCRIPT = "subscript"
CSS_CLASS_SUPERSCRIPT = "superscript"
CSS_CLASS_SMALLCAPS = "smallcaps"
CSS_CLASS_PAGE_NUMBER = "page_number"
CSS_CLASS_NOTE = "note"
CSS_CLASS_NOTE_ANCHOR = "note_anchor"


class _MtRenderer:
	"""
	Wraps markdown.Markdown object and locks it for thread-safety purposes
	"""
	def __init__(self, md_renderer):
		self._lock = threading.Lock()
		self._renderer = md_renderer

	def convert(self, markup):
		with self._lock:
			self._renderer.reset()
			return self._renderer.convert(markup)


def make_transcription_renderer():
	renderer = markdown.Markdown(
		extensions=[
			"markdown.extensions.tables",
		],
		output_format="xhtml5"
	)
	renderer.inlinePatterns.register(MarkdownPageNumber(), name="page_number", priority=-1)
	renderer.inlinePatterns.register(MarkdownSmallCaps(), name="smallcaps", priority=-2)
	renderer.inlinePatterns.register(MarkdownStrikethrough(), name="strikethrough", priority=-3)
	renderer.inlinePatterns.register(MarkdownSubscript(), name="subscript", priority=-4)
	renderer.inlinePatterns.register(MarkdownSuperscript(), name="superscript", priority=-5)
	renderer.inlinePatterns.register(MarkdownHyphen(), name="hyphen", priority=-6)
	renderer.inlinePatterns.register(MarkdownGuess(), name="guess", priority=-7)

	renderer.parser.blockprocessors.deregister("hashheader")
	renderer.parser.blockprocessors.register(
		WrappedHashHeaderProcessor(renderer.parser),
		name="wrapped_hash_header",
		priority=1000,
	)
	renderer.parser.blockprocessors.register(
		MarkdownAlignRight(renderer.parser),
		name="align_right",
		priority=1001,
	)
	renderer.parser.blockprocessors.register(
		MarkdownNote(renderer.parser),
		name="note",
		priority=1002,
	)
	return _MtRenderer(renderer)


def make_note_renderer(index):
	renderer = markdown.Markdown(
		output_format="xhtml5"
	)
	renderer.inlinePatterns.register(MarkdownCite(index), name="cite", priority=-1)
	return _MtRenderer(renderer)


class MarkdownCache:
	"""
	Class capable of caching markdown files in compiled HTML form
	(ready to be sent to client).

	Tracks file changing and recompiles files when necessary
	"""
	def __init__(self):
		#dict: file abspath -> (source file mtime, compiled html data)
		self._cache = dict()
		self._cache_lock = threading.Lock()
		self._renderer = make_transcription_renderer()

	def get(self, abspath):
		"""
		Main entry point of the function.
		abspath is path to be read and compiled
		"""
		with self._cache_lock:
			modified_at = os.path.getmtime(abspath)
			rendered_at, rendered_data = self._cache.get(abspath, (None, None))
			if (
				(rendered_at is not None) and
				(modified_at <= rendered_at)
			):
				return rendered_data
		rendered_data = self.render_from_file(abspath)
		with self._cache_lock:
			self._cache[abspath] = (modified_at, rendered_data)
		return rendered_data

	def render_from_str(self, raw_data):
		return self._renderer.convert(raw_data)

	def render_from_file(self, abspath):
		"""
		Helper function for performing compilation
		of a markdown file to HTML
		"""
		raw_data = utils.read_utf8_file(abspath)
		return self.render_from_str(raw_data)


class MarkdownCite(markdown.inlinepatterns.Pattern):
	def __init__(self, index):
		super().__init__(r"\[(?P<id>[a-z0-9_]+)\]")
		self._index = index

	def handleMatch(self, m):
		a = xml.Element("a")
		id = m.group("id")
		a.set("href", f"/books/{id}")
		try:
			item = utils.first(self._index["id"][id])
		except StopIteration:
			logging.error(f"Could not find index entry for id={id}")
			raise
		a.text = item.get("cite_label")
		return a


class MarkdownPageNumber(markdown.inlinepatterns.Pattern):
	def __init__(self):
		super().__init__(r"\{(?P<page_number>[^\{\}]+)\}")

	def handleMatch(self, m):
		span = xml.Element("span")
		span.set("class", CSS_CLASS_PAGE_NUMBER)
		span.text = m.group("page_number")
		return span


class MarkdownStrikethrough(markdown.inlinepatterns.Pattern):
	"""
	Marks the text enclosed into doubled tildas as strikethrough,
	thus emulating the syntax of github flavoured markdown:
	https://help.github.com/articles/basic-writing-and-formatting-syntax/
	"""
	def __init__(self):
		super().__init__(r"\~\~(?P<strikethrough>[^\~]+)\~\~")

	def handleMatch(self, m):
		span = xml.Element("span")
		span.set("class", CSS_CLASS_STRIKETHROUGH)
		span.text = m.group("strikethrough")
		return span


class MarkdownSuperscript(markdown.inlinepatterns.Pattern):
	"""
	Marks the text enclosed into ^ as superscript
	"""
	def __init__(self):
		super().__init__(r"\^(?P<superscript>[^\^]+)\^")

	def handleMatch(self, m):
		element = xml.Element("sup")
		element.text = m.group("superscript")
		return element


class MarkdownSubscript(markdown.inlinepatterns.Pattern):
	"""
	Marks the text enclosed into ↓ (U+2193) as subscript
	"""
	def __init__(self):
		super().__init__(r"↓(?P<subscript>[^↓]+)↓")

	def handleMatch(self, m):
		span = xml.Element("span")
		span.set("class", CSS_CLASS_SUBSCRIPT)
		span.text = m.group("subscript")
		return span


class MarkdownSmallCaps(markdown.inlinepatterns.Pattern):
	"""
	Marks the text enclosed into doubled exclamation mark as small caps.
	The syntax was suggested in one of the pandoc issues:
	https://github.com/jgm/pandoc/issues/2761
	"""
	def __init__(self):
		super().__init__(r"!!(?P<smallcaps>[^!]+)!!")

	def handleMatch(self, m):
		span = xml.Element("span")
		span.set("class", CSS_CLASS_SMALLCAPS)
		span.text = m.group("smallcaps")
		return span


class MarkdownHyphen(markdown.inlinepatterns.Pattern):
	"""
	Handles hyphenation signs.
	At the time, removes both
	* `[-]` Represents printed hyphen. These are kept in the transcription to make typed text match the printed one
	* `[-?]` Represents missing hyphen. These are kept in the transcription to make typ
	"""
	def __init__(self):
		super().__init__(
			r"("
				r"(?P<preservable>-)|"
				r"(?P<removable>\[-\])|"
				r"(?P<forgotten>\[-\?\])"
			r")"
			r"\s*\r?\n\s*"
		)

	def handleMatch(self, m):
		if m["preservable"]:
			# preserve the hyphen
			return "-"
		else:
			# remove non-meaning hyphen
			return ""


class MarkdownGuess(markdown.inlinepatterns.Pattern):
	"""
	Handles parts of the text guesses during transcription
	Renders `fa[ce?]` as `fa[ce]`.
	"""
	def __init__(self):
		super().__init__(r"\[(?P<guess>[\w\s]+)\?\]")

	def handleMatch(self, m):
		guess = m["guess"]
		return f"[{guess}]"


class MarkdownAlignRight(markdown.blockprocessors.BlockProcessor):
	"""
	Marks paragraphs starting from `>>` symbols with style="text-align: right"
	"""
	MARKER = ">>"

	def test(self, parent, block):
		return block.startswith(self.MARKER)

	def run(self, parent, blocks):
		block = blocks.pop(0)
		p = xml.Element("p")
		p.set("style", "text-align: right")
		p.text = block[len(self.MARKER):].strip()
		parent.append(p)
		#WARN:
		#Consider current block as processed
		#This might be not the desired behaviour
		return True


class WrappedHashHeaderProcessor(markdown.blockprocessors.BlockProcessor):
	"""
	Process hash-prefixed headers,
	but considers lines in the same paragraph
	to be continue the header, rather than to begin a new paragraph.

	Based on the original python-markdown implementation.
	"""

	# Detect a header at start of any line in block
	RE = re.compile(r"^(?P<level>#{1,6})(?P<header>(?:\\.|[^\\])*?)#*(?:\n|$)")

	def test(self, parent, block):
		return bool(self.RE.search(block))

	def run(self, parent, blocks):
		block = blocks.pop(0)
		m = self.RE.search(block)
		wrapped = block[m.end():]
		# Create header using named groups from RE
		h = xml.SubElement(parent, "h%d" % len(m.group("level")))
		h.text = m.group("header").strip()
		if wrapped:
			h.text += "\n"
			h.text += wrapped


class MarkdownNote(markdown.blockprocessors.BlockProcessor):
	"""
	Marks any text placed into square brackets as a note.
	Works as follows:
	TODO: FILL ME IN
	"""
	NOTE_NUMBER_PLACEHOLDER = "%NOTE_NUMBER%"
	START = "[["
	START_MARK_LENGTH = len(START)
	END = "]]"
	END_MARK_LENGTH = len(END)
	FOOTNOTE_TAGS = ["blockquote", "h3", "p"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._markdown = markdown.Markdown(
			output_format="xhtml5"
		)
		self._markdown.inlinePatterns.register(MarkdownStrikethrough(), name="strikethough", priority=-1)
		self._markdown.inlinePatterns.register(MarkdownSuperscript(), name="superscript", priority=-2)
		self.reset()

	def reset(self):
		self._next_note_number = 1

	def test(self, parent, block):
		start_pos = block.find(self.START)
		return (start_pos != -1)

	def run(self, parent, blocks):
		raw_block = blocks.pop(0)
		processed_block = ""
		# set initial value to -len(self.END) in order
		# to avoid skipping text from the starting block below
		start_pos = raw_block.find(self.START)
		end_pos = None
		# external cycle allowing to handle multiple footnotes is a single block
		while (start_pos != -1):
			#this text does not belong to footnote and should not be handled
			processed_block += raw_block[0 if end_pos is None else (end_pos + self.END_MARK_LENGTH):start_pos]
			end_pos = raw_block.find(self.END, start_pos + self.START_MARK_LENGTH)
			if end_pos != -1:
				raw_footnote = raw_block[start_pos + len(self.START):end_pos]
			else:
				# No ending mark in this block.
				# Continue with popping next blocks
				raw_footnote = self.looseDetab(raw_block[start_pos + self.START_MARK_LENGTH:])
				while (
					blocks and
					end_pos == -1 and
					# check the start of the block in order
					# to stop on the first detabbeb block
					# instead of breaking the whole markup if single block is wrong
					(blocks[0].startswith('\t') or blocks[0].startswith(' ' * self.tab_length))
				):
					# footnote is split across several blocks
					# looking for the ending mark
					raw_block = blocks.pop(0)
					end_pos = raw_block.find(self.END)
					#Restore block structure which was lost during blocks parsing
					raw_footnote += "\n\n"
					if end_pos == -1:
						# ending mark was not found yet
						# taking entire block into footnote
						raw_footnote += self.looseDetab(raw_block)
					else:
						# ending mark found
						raw_footnote += self.looseDetab(raw_block[:end_pos])
			processed_block += self.handle_footnote(raw_footnote)
			start_pos = raw_block.find(self.START, end_pos + self.END_MARK_LENGTH)

		if len(raw_block) > end_pos + self.END_MARK_LENGTH:
			#handling the remaining of the block, if any
			processed_block += raw_block[end_pos + self.END_MARK_LENGTH:]
		blocks.insert(0, processed_block)
		#WARN: returning False in order to process current block with the other block parsers
		return False

	def handle_footnote(self, footnote_string):
		self._markdown.reset()
		converted_note = self._markdown.convert(footnote_string)
		# adding current footnote number to the first tag of converted footnote
		converted_note = converted_note.replace('>', '>' + str(self._next_note_number) + ". ", 1)

		#WARN:
		#    Removing line breaks from converted note
		#    in order to place entire footnote into singlge markdown block.
		#    At the time (Markdown=2.6.11) the following markup
		#    is being parsed into two blocks (one header, one text):
		#	 ```
		#    ### Test header
		#    test text
		converted_note = converted_note.replace('\n', '')

		for tag in self.FOOTNOTE_TAGS:
			#block elements are not allowed inside <p> elements
			#replacing them with span with corresponding classes
			#in order to handle them with some css tricks
			converted_note = converted_note\
				.replace("<" + tag + ">", '<span class="' + tag + '">')\
				.replace("</" + tag + ">", "</span>")

		raw_html = (
			f"<span class='{CSS_CLASS_NOTE_ANCHOR}'>{self._next_note_number}</span>"
			f"<span class='{CSS_CLASS_NOTE}'>{converted_note}</span>"
		)
		self._next_note_number += 1
		return raw_html
