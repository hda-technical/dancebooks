#!/usr/bin/env python3

import os
import sys
import textwrap
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from dancebooks import markdown as md


def render(markup):
	rd = md.make_transcription_renderer()
	return rd.convert(markup.strip())


def dedent(text):
	return textwrap.dedent(text.strip())


def test_header():
	input = "## Level Two Heading"
	assert render(input) == "<h2>Level Two Heading</h2>"

	input = "\n".join([
		"# Wrapped",
		"Header",
	])
	assert render(input) == "<h1>Wrapped\nHeader</h1>"

	input = "\n".join([
		"# Header 1",
		"## Header 2",
		"### Header 3",
	])
	assert render(input) == '\n'.join([
		"<h1>Header 1</h1>",
		"<h2>Header 2</h2>",
		"<h3>Header 3</h3>",
	])


def test_italic():
	input = "_Italic_"
	assert render(input) == '<p><em>Italic</em></p>'


def test_strikethrough():
	input = "~~Strike through~~"
	assert render(input) == '<p><span class="strikethrough">Strike through</span></p>'


def test_superscript():
	input = "^Super script^"
	assert render(input) == '<p><sup>Super script</sup></p>'


def test_subscript():
	input = "↓Sub script↓"
	assert render(input) == '<p><span class="subscript">Sub script</span></p>'


def test_small_caps():
	input = "!!Small caps!!"
	assert render(input) == '<p><span class="smallcaps">Small caps</span></p>'

	input = "S!!mall!! caps in the M!!iddle!!"
	assert render(input) == '<p>S<span class="smallcaps">mall</span> caps in the M<span class="smallcaps">iddle</span></p>'


def test_page_number():
	input = "{42} Start of page 42"
	assert render(input) == '<p><span class="page_number">42</span> Start of page 42</p>'

	input = "text from page 41 {42} Start of page 42"
	assert render(input) == '<p>text from page 41 <span class="page_number">42</span> Start of page 42</p>'

	input = "### {42} Header on page 42"
	assert render(input) == '<h3><span class="page_number">42</span> Header on page 42</h3>'


def test_hyphen():
	input = \
"""
Preservable hyphen-separated text
"""
	assert render(input) == '<p>Preservable hyphen-separated text</p>'

	input = \
"""
Removable hyphen[-]
separated text
"""
	assert render(input) == '<p>Removable hyphenseparated text</p>'

	input = \
"""
Forgotten hyphen[-?]
separated text
"""

	assert render(input) == '<p>Forgotten hyphenseparated text</p>'


def test_guess():
	input = \
"""
fac[e?]
th[en?]
stil[l?]
[hands?]
plac[es?]
an[d go?]
"""

	assert render(input) == """
<p>fac[e]
th[en]
stil[l]
[hands]
plac[es]
an[d go]</p>
""".strip()


def test_combinations():
	input = \
"""
### Hyphenated multi[-]
    line header with multi-lingual gu[es?]ses
"""
	assert render(input) == '<h3>Hyphenated multiline header with multi-lingual gu[es]ses</h3>'
