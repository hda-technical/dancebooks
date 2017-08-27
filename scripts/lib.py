#!/usr/bin/env python3

import json
import math
import os
import re
import subprocess
import shutil

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

def get_json(*args, **kwargs):
	"""
	Returns parsed JSON object received via HTTP GET request
	"""
	response = requests.get(*args, headers=HEADERS, **kwargs)
	if response.status_code == 200:
		return json.loads(response.content)
	else:
		raise ValueError(f"While getting {args[0]}: JSON with code 200 was expected. Got {response.status_code}")
	
	
def get_binary(output_filename, *args, **kwargs):
	"""
	Writes binary data received via HTTP GET request to output_filename
	"""
	request = requests.get(*args, stream=True, headers=HEADERS, **kwargs)
	with open(output_filename, "wb") as file:
		for chunk in request.iter_content(BLOCK_SIZE):
			file.write(chunk)
	
	
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
	

def sew_tiles_with_montage(folder, output_file, tiles_number_x, tiles_number_y, tile_size):
	"""
	Invokes montage tool from ImageMagick package to sew tiles together
	"""
	subprocess.check_call([
		"montage",
		f"{folder}/*",
		"-mode", "Concatenate",
		"-geometry", f"{tile_size}x{tile_size}>",
		"-tile", f"{tiles_number_x}x{tiles_number_y}",
		output_file
	])
	subprocess.check_call([
		"convert",
		output_file,
		"-trim",
		output_file
	])


def download_image_from_iip(fastcgi_url, files_root, page_metadata, output_filename):
	TILE_SIZE = 256
	width = int(page_metadata["d"][-1]["w"])
	height = int(page_metadata["d"][-1]["h"])
	pyramide_height = page_metadata["m"]
	remote_filename = os.path.join(files_root, page_metadata["f"])
	tmp_folder = "tmp"
	os.makedirs(tmp_folder, exist_ok=True)
	tiles_number_x = math.ceil(width / TILE_SIZE)
	tiles_number_y = math.ceil(height / TILE_SIZE)
	print(f"Going to download {tiles_number_x}x{tiles_number_y} tiled image")
	for tile_number in range(tiles_number_x * tiles_number_y):
		tile_number_x = tile_number % tiles_number_x
		tile_number_y = int(tile_number / tiles_number_x)
		tile_file = os.path.join(tmp_folder, f"{tile_number_y:08d}_{tile_number_x:08d}.jpg")
		get_binary(
			tile_file,
			fastcgi_url,
			#WARN: passing parameters as string in order to send them in urldecoded form 
			#(iip does not support urlencoded parameters)
			params=f"FIF={remote_filename}&JTL={pyramide_height},{tile_number}"
		)
	sew_tiles_with_montage(tmp_folder, output_filename, tiles_number_x, tiles_number_y, TILE_SIZE)
	shutil.rmtree(tmp_folder)
	
	
def download_book_from_iip(metadata_url, fastcgi_url, output_folder, files_root):
	"""
	Downloads book served by IIPImage fastcgi servant.
	API is documented here:
	http://iipimage.sourceforge.net/documentation/protocol/
	"""
	metadata = get_json(metadata_url)
	pages_number = len(metadata["pgs"])
	print(f"Going to download {pages_number} pages")
	for page_number, page_metadata in enumerate(metadata["pgs"]):
		output_filename = make_output_filename(output_folder, prefix="", page_number=page_number, extension="bmp")
		if os.path.isfile(output_filename):
			continue
		download_image_from_iip(fastcgi_url, files_root, page_metadata, output_filename)

		
def download_image_from_iiif(canvas_metadata, output_filename):
	"""
	Downloads single image via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	id = canvas_metadata["images"][-1]["resource"]["service"]["@id"]
	metadata = get_json(f"{id}/info.json")
	tile_size = metadata["tiles"][0]["width"]
	width = metadata["width"]
	height = metadata["height"]
	tmp_folder = "tmp"
	os.makedirs(tmp_folder, exist_ok=True)
	tiles_number_x = math.ceil(width / tile_size)
	tiles_number_y = math.ceil(height / tile_size)
	for tile_x in range(0, tiles_number_x):
		for tile_y in range(0, tiles_number_y):
			tile_file = os.path.join(tmp_folder, f"{tile_y:08d}_{tile_x:08d}.jpg")
			left = tile_size * tile_x
			top = tile_size * tile_y
			tile_width = min(width - left, tile_size)
			tile_height = min(height - top, tile_size)
			get_binary(
				tile_file,
				f"{id}/{left},{top},{tile_width},{tile_height}/{min(tile_width, tile_height)},/0/native.jpg"
			)
	sew_tiles_with_montage(tmp_folder, output_filename, tiles_number_x, tiles_number_y, tile_size)
	shutil.rmtree(tmp_folder)
	

def download_book_from_iiif(manifest_url, output_folder):
	"""
	Downloads entire book via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	manifest = get_json(manifest_url)
	canvases = manifest["sequences"][0]["canvases"]
	for page_number, canvas_metadata in enumerate(canvases):
		output_filename = make_output_filename(output_folder, prefix="", page_number=page_number, extension="bmp")
		download_image_from_iiif(canvas_metadata, output_filename)

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
def vatlib(
	book_id=("b", "", "Id of the book to be downloaded (e. g. 'MSS_Cappon.203')")
):
	"""
	Downloads book from http://digi.vatlib.it/
	"""
	manifest_url = f"http://digi.vatlib.it/iiif/{book_id}/manifest.json"
	output_folder = make_output_folder("vatlib", book_id)
	download_book_from_iiif(manifest_url, output_folder)


@opster.command()
def prlib(
	book_id=("b", "", "Book id to be downloaded (e. g. '20596C08-39F0-4E7C-92C3-ABA645C0E20E')")
):
	"""
	Downloads book from https://www.prlib.ru/
	"""
	output_folder = make_output_folder("prlib", book_id)
	metadata_url = f"http://content.beta.prlib.ru/out_metadata/{book_id}/{book_id}.json"
	files_root = f"/var/data/out_files/{book_id}"
	fastcgi_url = "http://content.beta.prlib.ru/fcgi-bin/iipsrv.fcgi"
	download_book_from_iip(
		metadata_url=metadata_url, 
		fastcgi_url=fastcgi_url, 
		files_root=files_root, 
		output_folder=output_folder
	)

			
@opster.command()
def googleBooks(
	book_id=("b", "", "Book id to be downloaded")
):
	"""
	Downloads freely-available book from Google Books service (image by image)
	Useful when freely-available pdf file has poor quality (such case is quite rare).
	"""
	if len(book_id) == 0:
		raise RuntimeError("book_id is mandatory")
	BASE_URL = "https://books.google.com/books"
	STARTING_PAGE_ID = "PA1"
	PAGE_ID_REGEXP = re.compile(
		r"(?P<page_group>PP|PA)(?P<page_number>\d+)"
	)
	
	#making basic request to get the list of page identifiers
	json_obj = get_json(
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
		pages_data = get_json(
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
			get_binary(
				output_filename,
				page_data["src"]
			)
			pages.discard(page_data["pid"])
	
	
if __name__ == "__main__":
	opster.dispatch()