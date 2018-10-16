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

import bs4
import opster
import requests

#NOTE: if the website is protected by cloudflare, removing User-Agent header will help to pass it by
USER_AGENT = "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64; rv:62.0) Gecko/20100101 Firefox/62.0"
HEADERS = {
	"User-Agent": USER_AGENT
}
TIMEOUT = 30

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


#using single session for all requests
session = requests.Session()

#@retry(retry_count=3)
def make_request(*args, **kwargs):
	"""
	Performs the request and returns requests.Response object.
	Accepts both raw urls and prepared requests
	"""
	if isinstance(args[0], str):
		url = args[0]
		response = requests.get(*args, headers=HEADERS, timeout=TIMEOUT, **kwargs)
	elif isinstance(args[0], requests.Request):
		request = args[0].prepare()
		url = request.url
		args = args[1:]
		request.headers = HEADERS
		response = session.send(request, *args, timeout=TIMEOUT, **kwargs)
	if response.status_code == 200:
		return response
	else:
		raise ValueError(f"While getting {url}: HTTP status 200 was expected. Got {response.status_code}")


#@retry(retry_count=3)
def get_json(*args, **kwargs):
	"""
	Returns parsed JSON object received via HTTP GET request
	"""
	return json.loads(make_request(*args, **kwargs).content)


def get_xml(*args, **kwargs):
	"""
	Returns parsed xml (as ElementTree) received via HTTP GET request
	"""
	return ElementTree.fromstring(make_request(*args, **kwargs).content)


def get_text(*args, **kwargs):
	return make_request(*args, **kwargs).content.decode("utf-8")


def get_binary(output_filename, url_or_request, *args, **kwargs):
	"""
	Writes binary data received via HTTP GET request to output_filename
	Accepts both url as string and request.Requests
	"""
	BLOCK_SIZE = 4096
	response = make_request(url_or_request, *args, stream=True, **kwargs)
	with open(output_filename, "wb") as file:
		for chunk in response.iter_content(BLOCK_SIZE):
			file.write(chunk)


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
	elif isinstance(page_number, int):
		return os.path.join(base, f"{page_number:08}.{extension}")
	else:
		return os.path.join(base, f"{page_number}.{extension}")


def make_temporary_folder():
	return str(uuid.uuid4())


class TileSewingPolicy(object):
	def __init__(self, tiles_number_x, tiles_number_y, tile_size, overlap=None):
		self.tiles_number_x = tiles_number_x
		self.tiles_number_y = tiles_number_y
		self.tile_size = tile_size
		self.overlap = overlap
		self.trim = True

	@staticmethod
	def from_image_size(width, height, tile_size):
		tiles_number_x = math.ceil(width / tile_size)
		tiles_number_y = math.ceil(height / tile_size)
		return TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size)


def sew_tiles_with_montage(folder, output_file, policy):
	"""
	Invokes montage tool from ImageMagick package to sew tiles together
	"""
	def format_magick_geometry(policy):
		geometry = ""
		if policy.tile_size is not None:
			geometry += f"{policy.tile_size}x{policy.tile_size}"
		if policy.overlap is not None:
			geometry += f"-{policy.overlap}-{policy.overlap}"
		if geometry:
			#WARN:
			#  Do not allow enlarging tiles.
			#  Certain libraries (i. e. Gallica) use variable tile size
			geometry += '>'
		return geometry

	def format_magick_tile(policy):
		return f"{policy.tiles_number_x}x{policy.tiles_number_y}"

	cmd_line = [
		"montage",
		f"{folder}/*",
		"-mode", "Concatenate"
	]
	geometry = format_magick_geometry(policy)
	if geometry:
		cmd_line += ["-geometry", geometry]
	cmd_line += [
		"-tile", format_magick_tile(policy),
		output_file
	]
	cmd_line_repr = ' '.join(cmd_line)
	print(f"Executing:\n    {cmd_line_repr}")
	subprocess.check_call(cmd_line)
	if policy.trim:
		subprocess.check_call([
			"convert",
			output_file,
			"-trim",
			output_file
		])


def download_and_sew_tiles(output_filename, url_maker, policy):
	tmp_folder = make_temporary_folder()
	os.mkdir(tmp_folder)
	try:
		print(f"Going to download {policy.tiles_number_x}x{policy.tiles_number_y} tiled image in {tmp_folder}")
		for tile_x in range(policy.tiles_number_x):
			for tile_y in range(policy.tiles_number_y):
				tile_file = os.path.join(tmp_folder, f"{tile_y:08d}_{tile_x:08d}.jpg")
				get_binary(
					tile_file,
					url_maker(tile_x, tile_y)
				)
		sew_tiles_with_montage(tmp_folder, output_filename, policy)
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


def download_image_from_iiif(base_url, output_filename, basename="native.jpg"):
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
			return f"{base_url}/{left},{top},{tile_width},{tile_height}/{tile_width},{tile_height}/0/{basename}"

	metadata = get_json(f"{base_url}/info.json")
	if "tiles" in metadata:
		# Served by e. g. vatlib servant
		tile_size = metadata["tiles"][0]["width"]
	else:
		# Served by e. g. gallica servant
		tile_size = 1024
	width = metadata["width"]
	height = metadata["height"]
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
	for page_number, canvas_metadata in enumerate(canvases):
		output_filename = make_output_filename(output_folder, page_number)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page_number:04d}")
			continue
		base_url = canvas_metadata["images"][-1]["resource"]["service"]["@id"]
		download_image_from_iiif(base_url, output_filename)


MAX_TILE_NUMBER = 100
def guess_tiles_number_x(url_maker):
	tiles_number_x = 0
	for tiles_number_x in range(MAX_TILE_NUMBER):
		probable_url = url_maker(tiles_number_x, 0)
		if probable_url is None:
			break
		head_response = requests.get(probable_url)
		if head_response.status_code != 200:
			break
	return tiles_number_x


def guess_tiles_number_y(url_maker):
	tiles_number_y = 0
	for tiles_number_y in range(MAX_TILE_NUMBER):
		probable_url = url_maker(0, tiles_number_y)
		if probable_url is None:
			break
		head_response = requests.head(probable_url)
		if head_response.status_code != 200:
			break
	return tiles_number_y


###################
#TILE BASED DOWNLOADERS
###################

@opster.command()
def gallica(
	id=("", "", "Id of the book to be downloaded (e. g. 'btv1b7200356s')")
):
	"""
	Downloads book from https://gallica.bnf.fr/

	NB: There is an option to download high resolution raw images
	(see JSON path manifest["sequences"][0]["canvases"][0]["images"][0]["resource"]["@id"]).
	It does not look standard for IIIF protocol, hence it is not used in this helper script.
	"""
	manifest_url = f"https://gallica.bnf.fr/iiif/ark:/12148/{id}/manifest.json"
	output_folder = make_output_folder("gallica", id)
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
			base_url = f"http://www.digitale-bibliothek-mv.de/viewer/rest/image/PPN880809493/{page:08d}.tif"
			download_image_from_iiif(base_url, output_filename, basename="default.jpg")
		except ValueError as ex:
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
	#The site does not use any metadata and simply sends unnecessary requests to backend
	#Guessing tiles_number_x, tiles_number_y using HEAD requests with guessed max_zoom
	#
	#UrlMaker returns None when corresponding tile does not exist
	#
	#FIXME: one can save some requests using bisection here,
	#but python standard library is too poor to have one
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
	id=("", "", "Image id to be downloaded (e. g. `BRBL_Exhibitions/7/1327507/1327507`)")
):
	"""
	Downloads image from https://brbl-zoom.library.yale.edu
	"""
	modulo = id[-1]
	output_filename = make_output_filename("", id)
	remote_filename = f"BRBL_Exhibitions/{modulo}/{id}/{id}.jp2"
	fastcgi_url = "https://brbl-zoom.library.yale.edu/fcgi-bin/iipsrv.fcgi"
	metadata_url = f"{fastcgi_url}?FIF={remote_filename}&obj=Max-size&obj=Tile-size&obj=Resolution-number"
	metadata = IIPMetadata.from_text(get_text(metadata_url))
	download_image_from_iip(fastcgi_url, remote_filename, metadata, output_filename)


@opster.command()
def britishLibraryBook(
	id=("", "", "Book id to be downloaded (e. g. `vdc_100025756343`). Warning: this id is different from the one found in online viewer. Pick one from the requested urls instead.")
):
	"""
	Downloads a book from http://explore.bl.uk
	"""
	#It looks like manifest.json is not being used by The British Library

	output_folder = make_output_folder("bl", id)
	current_page = 1
	while True:
		base_url=f"http://access.bl.uk/IIIFImageService/ark:/81055/{id}.0x{current_page:06x}"
		info_json_url = f"{base_url}/info.json"
		head_response = requests.head(info_json_url)
		if head_response.status_code != 200:
			break
		output_filename = make_output_filename(output_folder, current_page)
		download_image_from_iiif(base_url, output_filename)
		current_page += 1


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
	tiles_number_x = math.ceil(width / tile_size)

	height = int(size_metadata.attrib["Height"])
	tiles_number_y = math.ceil(height / tile_size)

	policy = TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size, overlap)
	download_and_sew_tiles(output_filename, url_maker, policy)


@opster.command()
def leidenCollection(
	id=("", "", "Image id of the painting to be donwloaded(e. g. `js-108-jan_steen-the_fair_at_warmond_files`)")
):
	"""
	Downloads single image from https://www.theleidencollection.com
	"""
	MAX_ZOOM = 13
	TILE_SIZE = None

	class UrlMaker(object):
		def __call__(self, tile_x, tile_y):
			return f"https://www.theleidencollection.com/LeidenCollectionSamples/images/{id}_files/{MAX_ZOOM}/{tile_x}_{tile_y}.jpg"

	url_maker = UrlMaker()
	tiles_number_x = guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")
	policy = TileSewingPolicy(tiles_number_x, tiles_number_y, None, None)

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
	Downloads single image from http://zs.thulb.uni-jena.de

	Requires a lot of work though
	"""
	class UrlMaker(object):
		def __init__(self, zoom):
			self.zoom = zoom

		def __call__(self, tile_x, tile_y):
			return f"http://zs.thulb.uni-jena.de/servlets/MCRTileServlet/jportal_derivate_{id}.tif/{self.zoom}/{tile_y}/{tile_x}.jpg"

	metadata_url = f"http://zs.thulb.uni-jena.de/servlets/MCRTileServlet/jportal_derivate_{id}.tif/imageinfo.xml"
	metadata = get_xml(metadata_url)

	output_filename = make_output_filename("", os.path.basename(id))

	width = int(metadata.attrib["width"])
	height = int(metadata.attrib["height"])
	zoom = int(metadata.attrib["zoomLevel"])

	TILE_SIZE = 256
	policy = TileSewingPolicy.from_image_size(width, height, TILE_SIZE)
	policy.trim = False

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
	for page in range(total_pages):
		url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={id};seq={page + 1};width=1000000"
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
	cookies = requests.cookies.RequestsCookieJar()
	#WARN: this value might require updating
	#	   FIXME: it can be obtained by sending request to 
	#	   http://digital.onb.ac.at/OnbViewer/viewer.faces?doc={id}
	cookies.set("JSESSIONID", "A1579FE74A1C057F5111D969C3B2F7E3", domain="digital.onb.ac.at", path="/")
	metadata_url = f"http://digital.onb.ac.at/OnbViewer/service/viewer/imageData?doc={id}&from=1&to=500"
	metadata = get_json(metadata_url, cookies=cookies)
	output_folder = make_output_folder("onb", id)
	image_data = metadata["imageData"]
	print(f"Going to download {len(image_data)} images")
	for image in image_data:
		query_args = image["queryArgs"]
		image_id = image["imageID"]
		image_url = f"http://digital.onb.ac.at/OnbViewer/image?{query_args}&w=10000&h=10000&x=0&y=0&s=1.0&q=100"
		output_filename = make_output_filename(output_folder, image_id, extension="jpg")
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
			except ValueError as ex:
				print(f"No more images left. Last page was {page - 1:04d}")
				break
		page += 1


if __name__ == "__main__":
	opster.dispatch()
