#!/bin/python

import markdown2
import codecs
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-i", "--input", dest="inputFilename", help="Read markdown from FILE", metavar="FILE")
parser.add_option("-o", "--output", dest="outputFilename", help="Write xhtml to FILE", metavar="FILE")
(options, args) = parser.parse_args()

html = markdown2.markdown_path(options.inputFilename)
html = u"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
		<title>python_markdown2.py</title>
	</head>
	<body>
		""" + html + u"""
	</body>
</html>
"""

with codecs.open(options.outputFilename, "w", encoding="utf-8") as outputFile:
	outputFile.write(html)
