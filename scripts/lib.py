#!/usr/bin/env python3

import functools
import json
import math
import os
import subprocess
import shutil
import time
import uuid
from xml.etree import ElementTree

import opster
import requests

BLOCK_SIZE = 4096
USER_AGENT = "User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64; rv:37.0) Gecko/20100101 Firefox/37.0"
HEADERS = {
	"User-Agent": USER_AGENT
}
TIMEOUT = 5

###################
#UTILITY FUNCTIONS
###################

def retry(retry_count, delay=0, delay_backoff=1):
	def actual_decorator(func):
		@functools.wraps(func)
		def do_retry(*args, **kwargs):
			retry_number = 0
			current_delay = delay
			try:
				return func(*args, **kwargs)
			except Exception as ex:
				if retry_number >= retry_count:
					raise RuntimeError(f"Failed to get results after {retry_number} retries")
				else:
					time.sleep(current_delay)
					current_delay *= delay_backoff
					retry_number += 1
		return do_retry
	return actual_decorator


@retry(retry_count=3)
def get_json(*args, **kwargs):
	"""
	Returns parsed JSON object received via HTTP GET request
	"""
	response = requests.get(*args, headers=HEADERS, timeout=TIMEOUT, **kwargs)
	if response.status_code == 200:
		return json.loads(response.content)
	else:
		raise ValueError(f"While getting {args[0]}: JSON with code 200 was expected. Got {response.status_code}")


@retry(retry_count=3)
def get_text(*args, **kwargs):
	response = requests.get(*args, headers=HEADERS, timeout=TIMEOUT, **kwargs)
	if response.status_code == 200:
		return response.content.decode("utf-8")
	else:
		raise ValueError(f"While getting {args[0]}: Code 200 was expected. Got {response.status_code}")


@retry(retry_count=3)
def get_binary(output_filename, url_or_request):
	"""
	Writes binary data received via HTTP GET request to output_filename
	Accepts both url as string and request.Requests
	"""
	response = requests.get(url_or_request, stream=True, headers=HEADERS, timeout=TIMEOUT)
	if response.status_code == 200:
		with open(output_filename, "wb") as file:
			for chunk in response.iter_content(BLOCK_SIZE):
				file.write(chunk)
	else:
		raise ValueError(f"While getting {args[0]}: Code 200 was expected. Got {response.status_code}")


def make_output_folder(downloader, book_id):
	folder_name = "{downloader}_{book_id}".format(
		downloader=downloader,
		book_id=book_id
	)
	os.makedirs(folder_name, exist_ok=True)
	return folder_name


def make_output_filename(base, page_number=None, extension="bmp"):
	if page_number is None:
		return f"{base}.{extension}"
	else:
		return os.path.join(base, f"{page_number:08}.{extension}")


def make_temporary_folder():
	return str(uuid.uuid4())


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


def download_and_sew_tiles(tiles_number_x, tiles_number_y, tile_size, url_maker, output_filename):
	"""
	Iterates over range(tiles_number_x) cross range(tiles_number_y),
	produces tile url via tile_url_maker invocation,
	saves sewn .bmp file to output_filename
	"""
	tmp_folder = make_temporary_folder()
	os.mkdir(tmp_folder)
	try:
		print(f"Going to download {tiles_number_x}x{tiles_number_y} tiled image in {tmp_folder}")
		for tile_x in range(tiles_number_x):
			for tile_y in range(tiles_number_y):
				tile_file = os.path.join(tmp_folder, f"{tile_y:08d}_{tile_x:08d}.jpg")
				get_binary(
					tile_file,
					url_maker(tile_x, tile_y)
				)
		sew_tiles_with_montage(tmp_folder, output_filename, tiles_number_x, tiles_number_y, tile_size)
	finally:
		if "KEEP_TEMP" not in os.environ:
			shutil.rmtree(tmp_folder)


class IIPMetadata(object):
	def __init__(self, tile_size, width, height, max_level):
		self.tile_size = tile_size
		self.width = width
		self.height = height
		self.max_level = max_level

	@staticmethod
	def from_json(json):
		tile_size = 256
		width = int(json["d"][-1]["w"])
		height = int(json["d"][-1]["h"])
		max_level = json["m"]
		return IIPMetadata(tile_size, width, height, max_level)

	@staticmethod
	def from_text(text):
		"""
		Parses the following text:
		```
		Max-size:3590 3507
		Tile-size:256 256
		Resolution-number:5
		```
		"""
		tile_size = None
		width = None
		height = None
		max_level = None
		for line in text.split('\n'):
			parts = line.split(':')
			if parts[0] == "Max-size":
				(width, height) = map(int, parts[1].split())
			elif parts[0] == "Tile-size":
				tile_size = int(parts[1].split()[0])
			elif parts[0] == "Resolution-number":
				max_level = int(parts[1]) - 1
			else:
				pass
		return IIPMetadata(tile_size, width, height, max_level)


def download_image_from_iip(fastcgi_url, remote_filename, metadata, output_filename):
	tiles_number_x = math.ceil(metadata.width / metadata.tile_size)
	tiles_number_y = math.ceil(metadata.height / metadata.tile_size)
	download_and_sew_tiles(
		tiles_number_x, tiles_number_y, metadata.tile_size,
		lambda tile_x, tile_y: requests.Request(
			fastcgi_url,
			#WARN: passing parameters as string in order to send them in urldecoded form
			#(iip does not support urlencoded parameters)
			params=f"FIF={remote_filename}&JTL={metadata.max_level},{tile_x * tile_y}",
		)
	);


def download_book_from_iip(metadata_url, fastcgi_url, output_folder, files_root):
	"""
	Downloads book served by IIPImage fastcgi servant.
	API is documented here:
	http://iipimage.sourceforge.net/documentation/protocol/
	"""
	metadata = get_json(metadata_url)["pgs"]
	print(f"Going to download {len(metadata)} pages")
	for page_number, page_metadata in enumerate(metadata):
		iip_page_metadata = IIPMetadata.from_json(page_metadata)
		remote_filename = os.path.join(files_root, page_metadata["f"])
		output_filename = make_output_filename(output_folder, page_number)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page_number:04d}")
			continue
		else:
			print(f"Downloading page #{page_number:04d}")
			download_image_from_iip(fastcgi_url, remote_filename, iip_page_metadata, output_filename)


def download_image_from_iiif(canvas_metadata, output_filename):
	"""
	Downloads single image via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	class UrlMaker(object):
		def __call__(self, tile_x, tile_y):
			left = tile_size * tile_x
			top = tile_size * tile_y
			tile_width = min(width - left, tile_size)
			tile_height = min(height - top, tile_size)
			return f"{id}/{left},{top},{tile_width},{tile_height}/{tile_width},{tile_height}/0/native.jpg"

	id = canvas_metadata["images"][-1]["resource"]["service"]["@id"]
	metadata = get_json(f"{id}/info.json")
	if "tiles" in metadata:
		# Served by e. g. vatlib servant
		tile_size = metadata["tiles"][0]["width"]
	else:
		# Served by e. g. gallica servant
		tile_size = 1024
	width = metadata["width"]
	height = metadata["height"]
	tiles_number_x = math.ceil(width / tile_size)
	tiles_number_y = math.ceil(height / tile_size)
	download_and_sew_tiles(
		tiles_number_x, tiles_number_y,	tile_size,
		UrlMaker(),
		output_filename
	)


def download_book_from_iiif(manifest_url, output_folder):
	"""
	Downloads entire book via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	manifest = get_json(manifest_url)
	canvases = manifest["sequences"][0]["canvases"]
	for page_number, canvas_metadata in enumerate(canvases):
		output_filename = make_output_filename(output_folder, page_number)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page_number:04d}")
			continue
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
def gallica(
	id=("", "", "Id of the book to be downloaded (e. g. 'btv1b7200356s')")
):
	"""
	Downloads book from http://gallica.bnf.fr/

	NB: There is an option to download high resolution raw images
	(see JSON path manifest["sequences"][0]["canvases"][0]["images"][0]["resource"]["@id"]).
	It does not look standard for IIIF protocol, hence it is not used in this helper script.
	"""
	manifest_url = f"http://gallica.bnf.fr/iiif/ark:/12148/{id}/manifest.json"
	output_folder = make_output_folder("gallica", id)
	download_book_from_iiif(manifest_url, output_folder)


@opster.command()
def vatlib(
	id=("", "", "Id of the book to be downloaded (e. g. 'MSS_Cappon.203')")
):
	"""
	Downloads book from http://digi.vatlib.it/
	"""
	manifest_url = f"http://digi.vatlib.it/iiif/{id}/manifest.json"
	output_folder = make_output_folder("vatlib", id)
	download_book_from_iiif(manifest_url, output_folder)


@opster.command()
def prlib(
	id=("", "", "Book id to be downloaded (e. g. '20596C08-39F0-4E7C-92C3-ABA645C0E20E')"),
	page=("p", "", "Download specified (zero-based) page only"),
):
	"""
	Downloads book from https://www.prlib.ru/
	"""
	metadata_url = f"https://content.prlib.ru/out_metadata/{id}/{id}.json"
	files_root = f"/var/data/out_files/{id}"
	fastcgi_url = "https://content.prlib.ru/fcgi-bin/iipsrv.fcgi"
	output_folder = make_output_folder("prlib", id)
	if page:
		page = int(page)
		output_filename = make_output_filename(output_folder, page)
		metadata = get_json(metadata_url)
		page_metadata = metadata[page]
		remote_filename = os.path.join(files_root, page_metadata["f"])
		download_image_from_iip(fastcgi_url, remote_filename, page_metadata, output_filename)
	else:
		download_book_from_iip(
			metadata_url=metadata_url,
			fastcgi_url=fastcgi_url,
			files_root=files_root,
			output_folder=output_folder
		)


@opster.command()
def nga(
	id=("", "", "Image id to be downloaded (e. g. `49035`)")
):
	"""
	Downloads single image from https://www.nga.gov
	"""
	slashed_image_id = "/".join(id) #will produce "4/9/0/3/5" from "49035-primary-0-nativeres"
	remote_filename = f"/public/objects/{slashed_image_id}/{id}-primary-0-nativeres.ptif"
	fastcgi_url="https://media.nga.gov/fastcgi/iipsrv.fcgi"
	metadata = IIPMetadata.from_text(
		get_text(f"{fastcgi_url}?FIF={remote_filename}&obj=Max-size&obj=Tile-size&obj=Resolution-number")
	)
	download_image_from_iip(
		fastcgi_url=fastcgi_url,
		remote_filename=remote_filename,
		metadata=metadata,
		output_filename=f"nga.{id}.bmp"
	)


@opster.command()
def hab(
	id=("", "", "Image id to be downloaded (e. g. `grafik/uh-4f-47-00192`)")
):
	"""
	Downloads single image from http://diglib.hab.de and http://kk.haum-bs.de
	(both redirect to Virtuelles Kupferstichkabinett website, which is too hard to be typed)
	"""
	#The site does not use any metadata and simply sends unnecessary requests to backend
	#Using head requests to get maximum available zoom and
	class UrlMaker(object):
		def __init__(self, zoom):
			self.zoom = zoom

		def __call__(self, tile_x, tile_y):
			for tile_group in [0, 1, 2]:
				probable_url = f"http://diglib.hab.de/varia/{id}/TileGroup{tile_group}/{self.zoom}-{tile_x}-{tile_y}.jpg"
				head_response = requests.head(probable_url)
				if head_response.status_code == 200:
					return probable_url
			return None

	MAX_ZOOM = 10
	MAX_TILE_NUMBER = 100
	TILE_SIZE = 256
	max_zoom = None
	for test_zoom in range(MAX_ZOOM + 1):
		if UrlMaker(test_zoom)(0, 0) is not None:
			max_zoom = test_zoom
		else:
			#current zoom is not available - consider previous one to be maximal
			break
	assert(max_zoom is not None)
	print(f"Guessed max_zoom={max_zoom}")
	#The site does not use any metadata and simply sends unnecessary requests to backend
	#Guessing tiles_number_x, tiles_number_y using HEAD requests with guessed max_zoom
	#
	#UrlMaker returns None when corresponding tile does not exist
	#
	#FIXME: one can save some requests using bisection here,
	#but python standard library is too poor to have one
	tiles_number_x = None
	tiles_number_y = None
	url_maker = UrlMaker(max_zoom)
	for tile_x in range(MAX_TILE_NUMBER):
		if url_maker(tile_x, 0) is None:
			tiles_number_x = tile_x
			print(f"Guessed tiles_number_x={tiles_number_x}")
			break
	for tile_y in range(MAX_TILE_NUMBER):
		if url_maker(0, tile_y) is None:
			tiles_number_y = tile_y
			print(f"Guessed tiles_number_y={tiles_number_y}")
			break
	assert(tiles_number_x is not None)
	assert(tiles_number_y is not None)
	output_filename = make_output_filename(id.replace("/", "."))
	download_and_sew_tiles(tiles_number_x, tiles_number_y, TILE_SIZE, url_maker, output_filename)

	
@opster.command()
def yale(
	id=("", "", "Image id to be downloaded (e. g. `lwlpr11386`)")
):
	class UrlMaker(object):
		"""
		Similar to UrlMaker from hab() method. Should be deduplicated once
		"""
		def __init__(self, zoom):
			self.zoom = zoom

		def __call__(self, tile_x, tile_y):
			for tile_group in [0, 1, 2]:
				probable_url = f"http://images.library.yale.edu/walpoleimages/dl/011000/{id}/TileGroup{tile_group}/{self.zoom}-{tile_x}-{tile_y}.jpg"
				head_response = requests.head(probable_url)
				if head_response.status_code == 200:
					return probable_url
			return None
	MAX_ZOOM = 5
	#FIXME: replace 011000 with computed expression
	metadata = ElementTree.fromstring(get_text(f"http://images.library.yale.edu/walpoleimages/dl/011000/{id}/ImageProperties.xml"))
	width = int(metadata.attrib["WIDTH"])
	height = int(metadata.attrib["HEIGHT"])
	tile_size = int(metadata.attrib["TILESIZE"])
	
	output_filename = make_output_filename(id)
	tiles_number_x = math.ceil(width / tile_size)
	tiles_number_y = math.ceil(height / tile_size)
	download_and_sew_tiles(
		tiles_number_x, tiles_number_y,	tile_size,
		UrlMaker(MAX_ZOOM),
		output_filename
	)
	

if __name__ == "__main__":
	opster.dispatch()
