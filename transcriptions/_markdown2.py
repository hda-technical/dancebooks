#!/bin/python

import markdown2
import codecs
import optparse
import os.path
import sys

dirname = os.path.dirname(__file__)
resetCssFile = open(dirname + "/_reset.css")
styleCssPath = dirname + "/_style.css"

usage = u"Usage: %prog [options]"

parser = optparse.OptionParser(usage=usage)
parser.add_option(u"-i", u"--input", dest=u"inputFilename", help=u"Read markdown from FILE", metavar=u"FILE")
parser.add_option(u"-o", u"--output", dest=u"outputFilename", help=u"Write xhtml to FILE", metavar=u"FILE")
parser.add_option(u"-c", u"--css", dest=u"cssFilename", default=styleCssPath, help=u"Read css from FILE", metavar=u"FILE")
(options, args) = parser.parse_args()

if ((options.inputFilename is None) or (not os.path.isfile(options.inputFilename))):
	print "Error: input file is not defined\n"
	sys.exit(1)
	
if (options.outputFilename is None):
	print "Error: output file is not defined\n"
	sys.exit(1)
	
if ((options.cssFilename is None) or (not os.path.isfile(options.cssFilename))):
	print "Error: style file is not defined\n"
	sys.exit(1)

title = os.path.basename(options.inputFilename)
title = unicode(os.path.splitext(title)[0], u"utf-8")

styleCssFile = open(options.cssFilename)
css = resetCssFile.read() + styleCssFile.read()
css = unicode(css, u"utf-8")

html = markdown2.markdown_path(options.inputFilename)
html = u"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
		<title>""" + title + u"""</title>
		<style type="text/css">
			""" + css + u"""
		</style>
	</head>
	<body>
		""" + html + u"""
	</body>
</html>
"""

outputFile = codecs.open(options.outputFilename, u"w", encoding=u"utf-8")
outputFile.write(html)
