#!/usr/bin/env python3

import json
import os
import re

import opster
import requests

BLOCK_SIZE = 4096
USER_AGENT = "User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64; rv:37.0) Gecko/20100101 Firefox/37.0"
HEADERS = {
	"User-Agent": USER_AGENT
}

###################
#UTILITY FUNCTIONS 
###################

def json_get_request(*args, **kwargs):
	"""
	Returns parsed JSON object received via HTTP GET request
	"""
	rq = requests.get(*args, headers=HEADERS, **kwargs)
	return json.loads(rq.text)
	
	
def binary_get_request(output_filename, *args, **kwargs):
	"""
	Writes binary data received via HTTP GET request to output_filename
	"""
	rq = requests.get(*args, stream=True, headers=HEADERS, **kwargs)
	with open(output_filename, "wb") as fd:
		for chunk in rq.iter_content(BLOCK_SIZE):
			fd.write(chunk)
	
	
def make_output_folder(downloader, book_id):
	folder_name = "{downloader}_{book_id}".format(
		downloader=downloader,
		book_id=book_id
	)
	os.makedirs(folder_name, exist_ok=True)
	return folder_name
		

def make_output_filename(output_folder, prefix, page_number, extension):
	return os.path.join(
		output_folder,
		"{prefix}{page_number:08}.{extension}".format(
			prefix=prefix,
			page_number=page_number,
			extension=extension
		)
	)

###################
#LIBRARY DEPENDENT FUNCTIONS 
###################	

###################
#FILE BASED DOWNLOADERS
###################	

###################
#PAGE BASED DOWNLOADERS
###################	
			
@opster.command()
def googleBooks(
	book_id=("b", "", "Book id to be downloaded")
):
	"""
	Download freely-available book from Google Books service (image by image)
	"""
	if len(book_id) == 0:
		raise RuntimeError("book_id is mandatory")
	BASE_URL = "https://books.google.com/books"
	STARTING_PAGE_ID = "PA1"
	PAGE_ID_REGEXP = re.compile(
		r"(?P<page_group>PP|PA)(?P<page_number>\d+)"
	)
	
	#making basic request to get the list of page identifiers
	json_obj = json_get_request(
		BASE_URL,
		params={
			"id": book_id,
			"pg": STARTING_PAGE_ID,
			"jscmd": "click3"
		}
	)

	pages = set()
	for obj in json_obj["page"]:
		pages.add(obj["pid"])
	output_folder = make_output_folder("googleBooks", book_id)
	while len(pages) > 0:
		pages_data = json_get_request(
			BASE_URL,
			params={
				"id": book_id,
				"pg": pages.pop(),
				"jscmd": "click3"
			}
		)
		for page_data in pages_data["page"]:
			page_id = page_data["pid"]
			#src will only be returned for some pages (currently, 5)
			if "src" not in page_data:
				continue
			
			match = PAGE_ID_REGEXP.match(page_id)
			if match is None:
				raise RuntimeError("regexp match failed")
				
			output_filename = make_output_filename(
				output_folder,
				"!pp" if (match.group("page_group") == "PP") else "pa",
				int(match.group("page_number")),
				"jpg"
			)
			binary_get_request(
				output_filename,
				page_data["src"]
			)
			pages.discard(page_data["pid"])
	
	
if __name__ == "__main__":
	opster.dispatch()