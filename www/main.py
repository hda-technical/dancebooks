#!/usr/bin/python3
# coding: utf-8

import os.path

#from flask import Flask, render_template, abort

from parser import BibParser

parser = BibParser()
items = parser.parse_folder(os.path.abspath("../bib"))

app = Flask(__name__)

app.debug = True
app.jinja_env.trim_blocks = True

if (not os.path.exists("templates")):
	print("Should run from root folder")
	sys.exit()
	
@app.route("/")
def root():
	return render_template("index.html", items=items)