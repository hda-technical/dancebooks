#!/usr/bin/env python3
#coding: utf-8
import datetime
import os
import re
import sys

import bs4 as soup
import requests

DOMAIN = "http://collections.lacma.org"
MIN_FILE_SIZE = 1024
MONTH_PATTERN = "|".join([
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December"
])
DATE_PATTERNS = [
	#April 1, 1813
	r"(?P<month>" + MONTH_PATTERN + r") (?P<day>\d{1,2}), (?P<year>\d{4})",
	#July 1807
	r"(?P<month>" + MONTH_PATTERN + r") (?P<year>\d{4})",
	#1809
	r"(?P<year>\d{4})",
	#early 19th century
	r"early (?P<century>\d{2})th century",
]
DATE_REGEXPS = list(map(re.compile, DATE_PATTERNS))
DATE_FORMATS = ["%B %d, %Y", "%B %Y", "%Y", None]


class OptionalDate(object):
	"""
	Represents date with lacunes
	"""
	FILLER = 'XX'
	def __init__(self, century=None, year=None, month=None, day=None):
		if (
			century is None and
			year is None
		):
			raise LogicError("Either century or year should be specified")
		if (century is not None):
			#in 19th century years begin from 18xx
			self.year_centinnel = "{0:02d}".format((century - 1))
			self.year_decimal = self.FILLER
			self.month = self.FILLER
			self.day = self.FILLER
		else:
			self.year_centinnel = "{0:02d}".format(int(year / 100))
			self.year_decimal = "{0:02d}".format(year % 100)
			self.month = ("{0:02d}".format(month) if month else self.FILLER)
			self.day = ("{0:02d}".format(day) if day else self.FILLER)
	
	def __str__(self):
		"""
		Formats as ISO string, filling gaps with X sign
		"""
		return '-'.join([
			self.year_centinnel + self.year_decimal,
			self.month,
			self.day
		])
			

class ImageDescription(object):
	def __init__(self, url, title, date):
		self.url_lq = url
		self.url_hq = self.url_lq + "/pub"
		self.title = title
		self.date = date
		
	def make_filename(self, ext):
		"""
		Computes filename taking into account 
		probable existence of different files
		with the same basenames
		"""
		idx = 1
		basename = str(self.date) + " " + self.title
		fullname = basename + "." + ext
		#for existent filenames — append prefixes 
		while os.path.isfile(fullname):
			idx += 1
			fullname = "{basename} #{idx:02d}.{ext}".format(
				basename=basename,
				idx=idx,
				ext=ext
			)
		if idx == 2:
			#when idx is equal to 2, 
			#we have to append idx == 1 to existent file
			os.rename(
				basename + "." + ext,
				basename + " " + "#01" + "." + ext,
			)
		return  fullname
	
	def download_and_save(self):
		resp = requests.head(self.url_hq)
		if int(resp.headers["Content-Length"]) > MIN_FILE_SIZE:
			resp = requests.get(self.url_hq)
			ext = "tif"
		else:
			resp = requests.get(self.url_lq)
			ext = "jpg"
			
		with open(self.make_filename(ext), "wb") as file:
			for chunk in resp.iter_content():
				file.write(chunk)
		
def parseContentsPage(html):
	bs = soup.BeautifulSoup(html, "html.parser")
	divs = bs.find_all("div", {"class": "art-image"})
	return list(map(
		lambda div: DOMAIN + div.find("a")["href"],
		divs
	))
	

def extractDate(string):
	"""
	Intellectually extracts optional date from string
	"""
	for idx, regexp in enumerate(DATE_REGEXPS):
		match = regexp.search(string)
		if match is not None:
			groups = match.groupdict()
			if "century" in groups:
				return OptionalDate(century=int(groups["century"]))
			else:
				dt = datetime.datetime.strptime(
					match.group(0), 
					DATE_FORMATS[idx]
				)
				return OptionalDate(
					year=dt.year,
					month=dt.month,
					day=(dt.day if "day" in groups else None)
				)
	raise ValueError("Can't extract date from: " + repr(string))
	

def downloadImage(imagePage):
	bs = soup.BeautifulSoup(
		requests.get(imagePage).text,
		"html.parser"
	);
	div = bs.find("div", {"class": "media-download-container"})
	url_lq = DOMAIN + div.find("a")["href"]
	title = bs.find("div", {"property": "dc:title"}).find("h1").text
	date = extractDate(next(iter(
		[
			node for node in
			bs.find("div", {"class": "group-right"}).contents
			if isinstance(node, str) and not node.isspace()
		]
	)))
	description = ImageDescription(url_lq, title, date)
	description.download_and_save()
	
if __name__ == '__main__':
	imagePages = parseContentsPage(sys.stdin.read())
	for imagePage in imagePages:
		downloadImage(imagePage)
	