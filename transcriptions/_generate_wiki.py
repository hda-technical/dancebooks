#!/usr/bin/env python
#coding: utf-8
import os.path
import sys

WIKI_PAGE = "wiki/Transcriptions.md"
URL_PREFIX = "https://github.com/georgthegreat/dancebooks-bibtex/blob/dev/"

with open(WIKI_PAGE, "w") as wiki_file:
	for tr in sorted(sys.argv[1:]):
		pretty_name, ext =  os.path.splitext(os.path.basename(tr.replace("_", " ")))
		item_string = "* [{link}]({prefix}{name})\n".format(
			link = pretty_name,
			prefix = URL_PREFIX,
			name = tr)
		wiki_file.write(item_string)	
