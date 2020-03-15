#!/usr/bin/env python3

import functools
import http.client
import json
import math
import os
import subprocess
import shutil
import time
import uuid
from xml.etree import ElementTree

import bs4
import opster
import requests

from utils import *  # TODO: fix imports
from difmoe import get_book_from_difmoe


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
	policy = TileSewingPolicy.from_image_size(metadata.width, metadata.height, metadata.tile_size)
	download_and_sew_tiles(
		output_filename,
		lambda tile_x, tile_y: requests.Request(
			"GET",
			fastcgi_url,
			#WARN: passing parameters as string in order to send them in urldecoded form
			#(iip does not support urlencoded parameters)
			params=f"FIF={remote_filename}&JTL={metadata.max_level},{tile_y * policy.tiles_number_x + tile_x}",
		),
		policy
	)


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


def download_image_from_iiif(base_url, output_filename):
	"""
	Downloads single image via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	DESIRED_QUALITIES = ["color", "native", "default"]
	DESIRED_FORMATS = ["png", "tif", "jpg"]

	class UrlMaker(object):
		def __call__(self, tile_x, tile_y):
			left = tile_size * tile_x
			top = tile_size * tile_y
			tile_width = min(width - left, tile_size)
			tile_height = min(height - top, tile_size)
			tile_url = f"{base_url}/{left},{top},{tile_width},{tile_height}/{tile_width},{tile_height}/0/{desired_quality}.{desired_format}"
			return tile_url

	metadata_url = f"{base_url}/info.json"
	metadata = get_json(metadata_url)
	if "tiles" in metadata:
		# Served by e. g. vatlib servant
		tile_size = metadata["tiles"][0]["width"]
	else:
		# Served by e. g. Gallica servant
		tile_size = 1024
	width = metadata["width"]
	height = metadata["height"]

	desired_quality = "default"
	desired_format = "jpg"
	profile = metadata.get("profile")
	if (profile is not None) and (len(profile) >= 2) and (profile is not str):
		# Profile is not served by Gallica servant, but served by e. g. British Library servant
		# Complex condition helps to ignore missing metadata fields, see e. g.:
		# https://gallica.bnf.fr/iiif/ark:/12148/btv1b10508435s/f1/info.json
		# http://www.digitale-bibliothek-mv.de/viewer/rest/image/PPN880809493/00000001.tif/info.json
		if "qualities" in profile[1]:
			available_qualities = profile[1]["qualities"]
			for quality in DESIRED_QUALITIES:
				if quality in available_qualities:
					desired_quality = quality
					break
			else:
				raise RuntimeError(f"Can not choose desired image quality. Available qualities: {available_qualities!r}")
		if "formats" in profile[1]:
			available_formats = profile[1]["formats"]
			for format in DESIRED_FORMATS:
				if format in available_formats:
					desired_format = format
					break
			else:
				raise RuntimeError(f"Can not choose desired image format. Available formats: {available_formats!r}")

	policy = TileSewingPolicy.from_image_size(width, height, tile_size)
	download_and_sew_tiles(output_filename,	UrlMaker(),	policy)


def download_book_from_iiif(manifest_url, output_folder):
	"""
	Downloads entire book via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	manifest = get_json(manifest_url)
	canvases = manifest["sequences"][0]["canvases"]
	for page, metadata in enumerate(canvases):
		output_filename = make_output_filename(output_folder, page)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		base_url = metadata["images"][-1]["resource"]["service"]["@id"]
		download_image_from_iiif(base_url, output_filename)


def download_book_from_iiif_fast(manifest_url, output_folder):
	"""
	Downloads entire book via IIIF protocol.
	Issues single request per image, but might be unsupported by certain backends.

	API is documented here:
	http://iiif.io/about/
	"""
	manifest = get_json(manifest_url)
	canvases = manifest["sequences"][0]["canvases"]
	for page, metadata in enumerate(canvases):
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		full_url = metadata["images"][-1]["resource"]["@id"]
		get_binary(output_filename, full_url)


# These methods try to guess tiles number using HEAD requests with given UrlMaker
#
# url_maker_maker should be a callable accepting zoom in the arguments.
# It should return UrlMaker
#
# url_maker should be a callable accepting (x, y) in the arguments.
# It should return None when corresponding tile does not exist.
#
# FIXME:
#	one can save some requests using bisection here,
# 	but python standard library is too poor to have one.

def guess_tiles_zoom(url_maker_maker):
	MAX_ZOOM = 10

	zoom = 0
	for test_zoom in range(MAX_ZOOM):
		probable_url = url_maker_maker(test_zoom)(0, 0)
		head_response = requests.head(probable_url, headers=HEADERS)
		if head_response.status_code != 200:
			break
		zoom = test_zoom
	return zoom


def guess_tiles_number_x(url_maker, min_file_size=None):
	MAX_TILE_NUMBER_X = 100

	tiles_number_x = 0
	for test_x in range(MAX_TILE_NUMBER_X):
		probable_url = url_maker(test_x, 0)
		if probable_url is None:
			break
		head_response = requests.head(probable_url, headers=HEADERS)
		if head_response.status_code != 200:
			break
		if min_file_size is not None:
			content_length = int(head_response.headers["Content-Length"])
			if content_length < min_file_size:
				break
		tiles_number_x = (test_x + 1)
	return tiles_number_x


def guess_tiles_number_y(url_maker, min_file_size=None):
	MAX_TILE_NUMBER_Y = 100

	tiles_number_y = 0
	for test_y in range(MAX_TILE_NUMBER_Y):
		probable_url = url_maker(0, test_y)
		if probable_url is None:
			break
		head_response = requests.head(probable_url, headers=HEADERS)
		if head_response.status_code != 200:
			break
		if min_file_size is not None:
			content_length = int(head_response.headers["Content-Length"])
			if content_length < min_file_size:
				break
		tiles_number_y = (test_y + 1)
	return tiles_number_y


###################
#TILE BASED DOWNLOADERS
###################

@opster.command()
def bnfGallica(
	id=("", "", "Id of the book to be downloaded (e. g. 'btv1b7200356s')")
):
	"""
	Downloads book from https://gallica.bnf.fr/
	"""
	manifest_url = f"https://gallica.bnf.fr/iiif/ark:/12148/{id}/manifest.json"
	output_folder = make_output_folder("gallica", id)
	download_book_from_iiif_fast(manifest_url, output_folder)


@opster.command()
def bnfCandide(
	id=("", "", "Id of the image to be downloaded (e. g. 'can_097')")
):
	"""
	Downloads book from http://classes.bnf.fr/candide/
	"""
	#The site does not use any metadata and simply sends unnecessary requests to backend
	#Using head requests to get maximum available zoom and
	class UrlMaker(object):
		def __init__(self, zoom):
			self.zoom = zoom

		def __call__(self, tile_x, tile_y):
			probable_url = f"http://classes.bnf.fr/candide/images/5ci_nq/{id}/TileGroup0/{self.zoom}-{tile_x}-{tile_y}.jpg"
			if requests.head(probable_url).status_code == 200:
				return probable_url
			else:
				return None

	MAX_ZOOM = 10
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
	url_maker = UrlMaker(max_zoom)
	tiles_number_x = guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")

	policy = TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
	output_filename = make_output_filename(id.replace("/", "."))
	download_and_sew_tiles(output_filename, url_maker, policy)


@opster.command()
def belgiumRoyalLibrary(
	id=("", "", "Id of the book to be downloaded (e. g. 'A0524435')"),
	volume=("", "", "Volume of the book to be downloaded (e. g. '1')")
):
	class UrlMaker(object):
		def __init__(self, zoom, page_root_url):
			self.zoom = zoom
			self.page_root_url = page_root_url

		def __call__(self, tile_x, tile_y):
			probable_url = f"{page_root_url}/{self.zoom}-{tile_x}-{tile_y}.jpg"
			return probable_url


	volume = int(volume)
	assert(id[0].isalpha())
	assert(id[1:].isdigit())
	slash_separated_id = '/'.join(id)
	dash_deparated_id = id[0] + '-' + id[1:]
	base_url = f"https://viewerd.kbr.be/display/{slash_separated_id}/0000-00-00_{volume:02d}/zoomtiles/BE-KBR00_{dash_deparated_id}_0000-00-00_{volume:02d}"

	# We have to provide referer with each request being dispatched.
	# This is easiest, though very dirty way to do it.
	referer = f"https://viewerd.kbr.be/gallery.php?map={slash_separated_id}/0000-00-00_{volume:02d}/"
	HEADERS["Referer"] = referer

	output_folder = make_output_folder("belgiumRoyalLibrary", f"{id}_{volume:02d}")
	page = 1

	TILE_SIZE = 768
	while True:
		output_filename = make_output_filename(output_folder, page)
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page:04d}")
			page += 1
			continue

		page_root_url = f"{base_url}_{page:04d}"
		url_maker_maker = lambda zoom: UrlMaker(zoom, page_root_url)
		tiles_zoom = guess_tiles_zoom(url_maker_maker)
		print(f"Guessed tiles_zoom={tiles_zoom}")
		url_maker = UrlMaker(tiles_zoom, page_root_url)

		tiles_number_x = guess_tiles_number_x(url_maker)
		print(f"Guessed tiles_number_x={tiles_number_x}")
		tiles_number_y = guess_tiles_number_y(url_maker)
		print(f"Guessed tiles_number_y={tiles_number_y}")
		if (tiles_number_x == 0) or (tiles_number_y == 0):
			print(f"Page {page:04d} was not found")
			break
		policy = TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
		policy.trim = True
		download_and_sew_tiles(output_filename, url_maker, policy)
		page += 1


@opster.command()
def uniDuesseldorf(
	first=("", "", "First page to be downloaded (e. g. '1910311')"),
	last=("", "", "Last page to be downloaded (e. g. '1911077')")
):
	"""
	Downloads set of images from http://digital.ub.uni-duesseldorf.de
	"""
	# Automatic definition of max zoom level is hard,
	# since backend does not return error status even if the request if wrong
	ZOOM = 6

	# Instead of returning an error, backend will send blank image.
	# In order to detect proper time for stopping the iteration,
	# we will check if tile size is greater than this number of bytes
	MIN_FILE_SIZE = 5120

	class UrlMaker(object):
		def __init__(self, page):
			self.page = page

		def __call__(self, tile_x, tile_y):
			# Some unknown number with unspecified purpose.
			# It can change from item to item if looked in web browser console,
			# yet looks like it does not have any effect of the resulting image.
			UNKNOWN_NUMBER = 1862
			return f"http://digital.ub.uni-duesseldorf.de/image/tile/wc/nop/{UNKNOWN_NUMBER}/1.0.0/{page}/{ZOOM}/{tile_x}/{tile_y}.jpg"

	first = int(first)
	last = int(last)
	TILE_SIZE = 512

	for page in range(first, last + 1):
		output_filename = make_output_filename(base="", page=page)
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page}")
			continue
		url_maker = UrlMaker(page)

		tiles_number_x = guess_tiles_number_x(url_maker, min_file_size=5120)
		print(f"Guessed tiles_number_x={tiles_number_x}")
		tiles_number_y = guess_tiles_number_y(url_maker, min_file_size=5120)
		print(f"Guessed tiles_number_y={tiles_number_y}")
		policy = TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
		policy.trim = True
		policy.reverse_axis_y = True
		download_and_sew_tiles(output_filename, url_maker, policy)


@opster.command()
def uniGoettingen(
	id=("", "", "Id of the book to be downloaded (e. g. 'PPN722203519')")
):
	"""
	Downloads book from https://gdz.sub.uni-goettingen.de
	"""
	manifest_url = f"https://manifests.sub.uni-goettingen.de/iiif/presentation/{id}/manifest"
	output_folder = make_output_folder("goettingen", id)
	download_book_from_iiif(manifest_url, output_folder)


@opster.command()
def encyclopedie(
	volume=("", "", "Volume to be downloaded (e. g. '24')"),
	page=("", "", "Page number to be downloaded (e. g. '247')")
):
	"""
	Downloads single image from http://enccre.academie-sciences.fr/encyclopedie
	"""
	volume = int(volume)
	page = int(page)

	#there is no manifest.json file, slightly modified IIIF protocol is being used by the website
	image_list_url = f"http://enccre.academie-sciences.fr/icefront/api/volume/{volume}/imglist"
	image_list_metadata = get_json(image_list_url)
	image_metadata = image_list_metadata[page]
	image_url = f"http://enccre.academie-sciences.fr/digilib/Scaler/IIIF/{image_metadata['image']}"
	output_file = f"{page:04d}.bmp"
	download_image_from_iiif(image_url, output_file)


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
def mecklenburgVorpommern(
	id=("", "", "Id of the book to be downloaded (e. g. 'PPN880809493')")
):
	"""
	Downloads book from http://www.digitale-bibliothek-mv.de
	"""
	# it looks like Mecklenburg-Vorpommern does not use manifest.json
	output_folder = make_output_folder("mecklenburg_vorpommern", id)
	for page in range(1, 1000):
		output_filename = make_output_filename(output_folder, page)
		if os.path.isfile(output_filename):
			print(f"Skipping existing page {page}")
			continue
		try:
			base_url = f"http://www.digitale-bibliothek-mv.de/viewer/rest/image/{id}/{page:08d}.tif"
			download_image_from_iiif(base_url, output_filename)
		except ValueError:
			break


@opster.command()
def prlib(
	id=("", "", "Book id to be downloaded (e. g. '20596C08-39F0-4E7C-92C3-ABA645C0E20E')"),
	secondary_id=("", "", "Secondary id of the book (e. g. '5699092')"),
	page=("p", "", "Download specified (zero-based) page only"),
):
	"""
	Downloads book from https://www.prlib.ru/
	"""
	metadata_url = f"https://content.prlib.ru/metadata/public/{id}/{secondary_id}/{id}.json"
	files_root = f"/var/data/scans/public/{id}/{secondary_id}/"
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
	url_maker = UrlMaker(max_zoom)
	tiles_number_x = guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")

	policy = TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
	output_filename = make_output_filename(id.replace("/", "."))
	download_and_sew_tiles(output_filename, url_maker, policy)


@opster.command()
def yaleImage(
	id=("", "", "Image id to be downloaded (e. g. `lwlpr11386`)")
):
	"""
	Downloads image from http://images.library.yale.edu/
	"""
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
	policy = TileSewingPolicy.from_image_size(width, height, tile_size)

	output_filename = make_output_filename(id)
	download_and_sew_tiles(output_filename, UrlMaker(MAX_ZOOM), policy)


@opster.command()
def yaleBook(
	id=("", "", "Image id to be downloaded (e. g. `1327507`)"),
	chapter=("", "", "Chapter to download from (e. g. `PATREQIMGX12`)")
):
	"""
	Downloads image from https://brbl-zoom.library.yale.edu
	"""

	output_filename = make_output_filename("", id)
	remote_filename = f"{chapter}/{id[-1]}/{id}/{id}.jp2"
	fastcgi_url = "https://brbl-zoom.library.yale.edu/fcgi-bin/iipsrv.fcgi"
	metadata_url = f"{fastcgi_url}?FIF={remote_filename}&obj=Max-size&obj=Tile-size&obj=Resolution-number"
	metadata = IIPMetadata.from_text(get_text(metadata_url))
	download_image_from_iip(fastcgi_url, remote_filename, metadata, output_filename)


@opster.command()
def britishLibraryBook(
	id=("", "", "Book id to be downloaded (e. g. `vdc_100026052453`, as it is displayed in the viewer url)")
):
	"""
	Downloads a book from http://explore.bl.uk
	"""
	output_folder = make_output_folder("bl", id)
	manifest_url = f"https://api.bl.uk/metadata/iiif/ark:/81055/{id}.0x000001/manifest.json"
	download_book_from_iiif_fast(manifest_url, output_folder)


class DeepZoomUrlMaker(object):
	def __init__(self, base_url, max_zoom, ext="jpg"):
		self.base_url = base_url
		self.max_zoom = max_zoom
		self.ext = ext

	def __call__(self, tile_x, tile_y):
		return f"{self.base_url}/{self.max_zoom}/{tile_x}_{tile_y}.{self.ext}"


def download_image_from_deepzoom(output_filename, metadata_url, url_maker):
	image_metadata = get_xml(metadata_url)

	tile_size = int(image_metadata.attrib["TileSize"])
	overlap = int(image_metadata.attrib["Overlap"])

	size_metadata = image_metadata.getchildren()[0]
	width = int(size_metadata.attrib["Width"])
	height = int(size_metadata.attrib["Height"])

	policy = TileSewingPolicy.from_image_size(width, height, tile_size)
	policy.overlap = overlap
	download_and_sew_tiles(output_filename, url_maker, policy)


@opster.command()
def leidenCollection(
	id=("", "", "Image id of the painting to be downloaded(e. g. `js-108-jan_steen-the_fair_at_warmond_files`)")
):
	"""
	Downloads single image from https://www.theleidencollection.com
	"""
	MAX_ZOOM = 13

	class UrlMaker(object):
		def __call__(self, tile_x, tile_y):
			return f"https://www.theleidencollection.com/LeidenCollectionSamples/images/{id}_files/{MAX_ZOOM}/{tile_x}_{tile_y}.jpg"

	url_maker = UrlMaker()
	tiles_number_x = guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")
	policy = TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size=None, overlap=None)

	output_filename = make_output_filename("", id)
	download_and_sew_tiles(output_filename, url_maker, policy)

@opster.command()
def britishLibraryManuscript(
	id=("", "", "Page id of the manuscript to be downloaded (e. g. `add_ms_12531!1_f005r`)")
):
	"""
	Downloads single manuscript page from http://www.bl.uk/manuscripts/Default.aspx
	"""
	def parse_id(full_id):
		manuscript_id, _, page_id = tuple(id.rpartition('_'))
		return (manuscript_id, page_id)

	manuscript_id, page_id = parse_id(id)
	#WARN: here and below base_url and metadata_url have common prefix. One might save something
	metadata_url = f"http://www.bl.uk/manuscripts/Proxy.ashx?view={id}.xml"

	output_folder = make_output_folder("bl", manuscript_id)
	output_filename = make_output_filename(output_folder, page_id)

	MAX_ZOOM = 13
	base_url = f"http://www.bl.uk/manuscripts/Proxy.ashx?view={id}_files"
	url_maker = DeepZoomUrlMaker(base_url, MAX_ZOOM)
	download_image_from_deepzoom(output_filename, metadata_url, url_maker)


@opster.command()
def henryFord(
	id=("", "", "Id of the image to be downloaded (e. g. `4_cgntCY2Bj2ZpaKCjjXrWcNSEjlsU_Mk6ZUJByJ4smfJUNCpbPL_8dPavSb0DwGNavju8-nAYNsFUXP1jmb1KuGO2_RIzJoMfr8QvK5JTc/thf97207`")
):
	"""
	Downloads single image from https://www.thehenryford.org/
	"""
	metadata_url = f"https://www.thehenryford.org/linkedpub-image/{id}.dzi"
	basename = os.path.basename(id)

	MAX_ZOOM = 12
	base_url = f"https://www.thehenryford.org/linkedpub-image/{id}_files"
	url_maker = DeepZoomUrlMaker(base_url, MAX_ZOOM, ext="jpeg")
	output_filename = f"henryFord_{basename}.bmp"
	download_image_from_deepzoom(output_filename, metadata_url, url_maker)


@opster.command()
def makAt(
	id=("", "", "Id of the image to be downloaded (e. g. `ki-6952-1_1`)")
):
	"""
	Downloads single image from https://sammlung.mak.at/
	"""
	metadata_url = f"https://sammlung.mak.at/img/zoomimages/publikationsbilder/{id}.xml"

	output_filename = make_output_filename('.', id)

	MAX_ZOOM = 11
	base_url = f"https://sammlung.mak.at/img/zoomimages/publikationsbilder/{id}_files"
	url_maker = DeepZoomUrlMaker(base_url, MAX_ZOOM)

	download_image_from_deepzoom(output_filename, metadata_url, url_maker)


@opster.command()
def uniJena(
	id=("", "", "Id of the image to be downloaded, including document id (e. g. `00108217/JLM_1787_H002_0003_a`)")
):
	"""
	Downloads single image from https://zs.thulb.uni-jena.de

	Requires a lot of work though
	"""
	class UrlMaker(object):
		def __init__(self, zoom):
			self.zoom = zoom

		def __call__(self, tile_x, tile_y):
			return f"https://zs.thulb.uni-jena.de/servlets/MCRTileServlet/jportal_derivate_{id}.tif/{self.zoom}/{tile_y}/{tile_x}.jpg"

	metadata_url = f"https://zs.thulb.uni-jena.de/servlets/MCRTileServlet/jportal_derivate_{id}.tif/imageinfo.xml"
	metadata = get_xml(metadata_url)

	output_filename = make_output_filename("", os.path.basename(id))

	width = int(metadata.attrib["width"])
	height = int(metadata.attrib["height"])
	zoom = int(metadata.attrib["zoomLevel"])

	TILE_SIZE = 256
	policy = TileSewingPolicy.from_image_size(width, height, TILE_SIZE)

	url_maker = UrlMaker(zoom)
	download_and_sew_tiles(output_filename, url_maker, policy)

	subprocess.check_call([
		"convert",
		output_filename,
		"-crop", f"{width}x{height}+0+0",
		output_filename
	])


###################
#PAGE BASED DOWNLOADERS
###################


@opster.command()
def locMusdi(
	id=("", "", "Id of the book to be downloaded (e. g. `056`)"),
	start_from=("", 1, "The number of the first page in the sequence (defaults to 1)")
):
	"""
	Downloads book from Library of Congress Music/Dance instruction
	"""
	start_from = int(start_from)
	# Some ids are known to be missing
	MISSING_IDS = [
		"050", "054", "057", "061", "071",
		"078", "083", "095", "100", "103",
		"106", "111", "116", "120", "135",
		"152", "172", "173", "175", "176",
		"180", "185", "192", "193", "196",
		"206", "223", "231", "232", "234",
		"238", "244", "249",
	]
	MAX_ID = 252
	if len(id) != 3:
		print("Expected id to have 3 digits. Please, recheck the ID.")
		sys.exit(1)
	if id in MISSING_IDS:
		print(f"The book with id musdi.{id} is known to be missing. Please, recheck the ID.")
		sys.exit(1)
	if int(id) > MAX_ID:
		print(f"The maximum id is musdi.{MAX_ID}. Please, recheck the ID.")
		sys.exit(1)
	output_folder = make_output_folder("locMusdi", id)
	for page in range(start_from, 1000):
		base_url = f"https://memory.loc.gov/music/musdi/{id}/{page:04d}"
		url = None
		for extension in ["tif", "jpg"]:
			output_filename = make_output_filename(output_folder, page, extension=extension)
			if os.path.exists(output_filename):
				break
			maybe_url = base_url + "." + extension
			head_response = requests.head(maybe_url)
			if head_response.status_code == http.client.OK:
				url = maybe_url
				break
		if url is None:
			break
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading page #{page:08d}")
		get_binary(output_filename, url)


@opster.command()
def hathi(
	id=("", "", "Id of the book to be downloaded (e. g. `wu.89005529961`)")
):
	"""
	Downloads book from http://www.hathitrust.org/
	"""
	output_folder = make_output_folder("hathi", id)
	meta_url = f"https://babel.hathitrust.org/cgi/imgsrv/meta?id={id}"
	metadata = get_json(meta_url)
	total_pages = metadata["total_items"]
	print(f"Going to download {total_pages} pages to {output_folder}")
	for page in range(1, total_pages):
		url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={id};seq={page};width=1000000"
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading page {page} to {output_filename}")
		get_binary(output_filename, url)


@opster.command()
def	vwml(
	id=("", "", "Id of the book to be downloaded (e. g. `Wilson1808`)")
):
	"""
	Downloads book from https://www.vwml.org/topics/historic-dance-and-tune-books
	"""
	main_url = f"https://www.vwml.org/topics/historic-dance-and-tune-books/{id}"
	main_markup = get_text(main_url)
	soup = bs4.BeautifulSoup(main_markup, "html.parser")
	output_folder = make_output_folder("vwml", id)
	for page, thumbnail in enumerate(soup.find_all("img", attrs={"class": "image_thumb"})):
		thumbnail_url = thumbnail.attrs["src"]
		#IT'S MAGIC!
		full_url = thumbnail_url.replace("thumbnails", "web")
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Saving {full_url} to {output_filename}")
		try:
			get_binary(output_filename, full_url, verify=False)
		except ValueError:
			#VWML is known to have missing pages listed in this table.
			#Ignoring such pages
			pass


@opster.command()
def onb(
	id=("", "", "Id of the book to be downloaded (e. g. `ABO_+Z178189508`)")
):
	"""
	Downloads book from http://onb.ac.at/
	"""
	# First, normalizing id
	id = id.replace('/', '_')
	if id.startswith("ABO"):
		flavour = "OnbViewer"
	elif id.startswith("DTL"):
		flavour = "RepViewer"
	else:
		raise RuntimeError(f"Can not determine flavour for {id}")

	# Second, obtaining JSESSIONID cookie value
	viewer_url = f"http://digital.onb.ac.at/{flavour}/viewer.faces?doc={id}"
	viewer_response = requests.get(viewer_url)
	cookies = viewer_response.cookies
	metadata_url = f"http://digital.onb.ac.at/{flavour}/service/viewer/imageData?doc={id}&from=1&to=1000"
	metadata = get_json(metadata_url, cookies=cookies)
	output_folder = make_output_folder("onb", id)
	image_data = metadata["imageData"]
	print(f"Going to download {len(image_data)} images")
	for image in image_data:
		query_args = image["queryArgs"]
		image_id = image["imageID"]
		image_url = f"http://digital.onb.ac.at/{flavour}/image?{query_args}&s=1.0&q=100"
		output_filename = make_output_filename(output_folder, image_id, extension=None)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing image {image_id}")
			continue
		print(f"Downloading {image_id}")
		get_binary(output_filename, image_url, cookies=cookies)


@opster.command()
def staatsBerlin(
	id=("", "", "Id of the book to be downloaded (e. g. `PPN86902910X`)")
):
	"""
	Downloads book from http://digital.staatsbibliothek-berlin.de/
	"""

	output_folder = make_output_folder("staatsBerlin", id)
	page = 1
	while True:
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.isfile(output_filename):
			print(f"Skipping existing page {page}")
		else:
			try:
				image_url = f"http://ngcs.staatsbibliothek-berlin.de/?action=metsImage&metsFile={id}&divID=PHYS_{page:04d}"
				#WARN:
				#	it looks like there is no normal way
				#	to get the number of pages in the book via http request
				get_binary(output_filename, image_url)
			except ValueError:
				print(f"No more images left. Last page was {page - 1:04d}")
				break
		page += 1

		
@opster.command()
def difmoe(
	id=("", "", "UUID of the book to be downloaded (e. g. `c96b8876-b4f8-48a5-8221-3949392b1a5c`)")
):
	"""
	Downloads book from https://www.difmoe.eu/
	"""
	get_book_from_difmoe(id)


@opster.command()
def polona(
	id=("", "", "Base64-encoded id of the book to be downloaded (e. g. `Nzg4NDk0MzY`, can be found in permalink)")
):
	"""
	Downloads book from https://polona.pl
	"""
	entity_url = f"https://polona.pl/api/entities/{id}"
	entity_metadata = get_json(entity_url)
	output_folder = make_output_folder("polona", id)
	for page, page_metadata in enumerate(entity_metadata["scans"]):
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		found = False
		for image_metadata in page_metadata["resources"]:
			if image_metadata["mime"] == "image/jpeg":
				get_binary(output_filename, image_metadata["url"])
				found = True
		if not found:
			raise Exception(f"JPEG file was not found in image_metadata for page {page}")


@opster.command()
def haab(
	id=("", "", "Id of the book to be downloaded (e. g. `1286758696_1822000000/EPN_798582804`)")
):
	"""
	Downloads book from https://haab-digital.klassik-stiftung.de/
	"""
	def make_url(page):
		return f"https://haab-digital.klassik-stiftung.de/viewer/rest/image/{id}_{page:04d}.tif/full/full/0/default.jpg"
	output_folder = make_output_folder("haab", id)
	page = 0
	# HAAB server returns 403 for non-existing pages. First,
	while True:
		page_url = make_url(page)
		head_response = requests.head(page_url)
		if head_response.status_code == 200:
			print(f"Found starting page {page:04d}")
			break
		page += 1

	exception_count = 0
	while True:
		page_url = make_url(page)
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			page += 1
			continue
		try:
			print(f"Downloading page #{page:08d}")
			get_binary(output_filename, page_url)
			page += 1
		except ValueError as ex:
			page += 1
			#WARN:
			#	Certain pages can return 403 even in the middle of the book.
			# 	Skipping certain number of such pages.
			exception_count += 1
			if exception_count < 10:
				print(f"Got ValueError while getting page {page:08d}: {ex}")
				continue
			else:
				print(f"Got exception while getting page {page:08d}: {ex}. Exception limit was reached, downloader will exit now.")
				break


if __name__ == "__main__":
	opster.dispatch()
