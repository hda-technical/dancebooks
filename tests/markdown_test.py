#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from dancebooks import markdown as md


def render(markup):
	rd = md.make_transcription_renderer()
	return rd.convert(markup)

def test_italic():
	input = "_Italic_"
	assert render(input) == "<p><em>Italic</em></p>"
	