#!/usr/bin/env python3
# coding: utf-8
import codecs
import optparse
import os.path
import sys

import markdown2
import opster

dirname = os.path.dirname(__file__)

@opster.command()
def main(
	input=("i", "", "Input (markdown) file"),
	output=("o", "", "Output (html) file"),
	css=("c", "", "Style (css) file")
):
	if not os.path.isfile(input):
		print("Error: input file is not defined\n")
		sys.exit(1)
	
	if len(output) ==  0:
		print("Error: output file is not defined\n")
		sys.exit(1)
	
	if not os.path.isfile(css):
		print("Error: style file is not defined\n")
		sys.exit(1)

	title = os.path.basename(input)
	title = os.path.splitext(title)[0]
	
	css_string = open(css, "r").read()

	with open(input, "r+b") as input_file:
		markdown = input_file.read()
		#trimming utf-8 byte order mark
		if markdown.startswith(codecs.BOM_UTF8):
			markdown = markdown[len(codecs.BOM_UTF8):]

	html = markdown2.markdown(markdown)
	html = \
"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
		<title>""" + title + """</title>
		<style type="text/css">
			{css}
		</style>
	</head>
	<body>
		{html}
	</body>
</html>""".format(
		css=css_string,
		html=html
	)

	output_file = codecs.open(output, "w", encoding="utf-8")
	output_file.write(html)
	
if __name__ == "__main__":
	main.command()
