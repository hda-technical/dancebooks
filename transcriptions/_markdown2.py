#!/usr/bin/env python3

import codecs
import optparse
import os.path
import sys

import markdown2

dirname = os.path.dirname(__file__)
reset_css_file = open(os.path.join(dirname, "_reset.css"))
style_css_path = os.path.join(dirname, "_style.css")

usage = "Usage: %prog [options]"

parser = optparse.OptionParser(usage=usage)
parser.add_option("-i", "--input", dest="input_filename", help="Read markdown from FILE", metavar="FILE")
parser.add_option("-o", "--output", dest="output_filename", help="Write xhtml to FILE", metavar="FILE")
parser.add_option("-c", "--css", dest="css_filename", default=style_css_path, help="Read css from FILE", metavar="FILE")
(options, args) = parser.parse_args()

if (options.input_filename is None) or (not os.path.isfile(options.input_filename)):
	print("Error: input file is not defined\n")
	sys.exit(1)
	
if options.output_filename is None:
	print("Error: output file is not defined\n")
	sys.exit(1)
	
if (options.css_filename is None) or (not os.path.isfile(options.css_filename)):
	print("Error: style file is not defined\n")
	sys.exit(1)

title = os.path.basename(options.input_filename)
title = os.path.splitext(title)[0]

style_css_file = open(options.css_filename)
css = reset_css_file.read() + style_css_file.read()

with open(options.input_filename, "r+b") as input_file:
	markdown = input_file.read()
	#trimming utf-8 byte order mark
	if markdown.startswith(codecs.BOM_UTF8):
		markdown = markdown[len(codecs.BOM_UTF8):]

html = markdown2.markdown(markdown)
html = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
		<title>""" + title + """</title>
		<style type="text/css">
			""" + css + """
		</style>
	</head>
	<body>
		""" + html + """
	</body>
</html>
"""

output_file = codecs.open(options.output_filename, "w", encoding="utf-8")
output_file.write(html)
