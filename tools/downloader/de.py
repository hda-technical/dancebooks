import http
import os

import iiif
import utils

import requests
from requests.exceptions import HTTPError


def _bsb_manifest_url(id):
	return f"https://api.digitale-sammlungen.de/iiif/presentation/v2/{id}/manifest"


def get_bsb_book(*, id):
	manifest_url = _bsb_manifest_url(id)
	output_folder = utils.make_output_folder("bsb", id)
	iiif.download_book_fast(manifest_url, output_folder)


def get_bsb_page(*, id, page):
	manifest_url = _bsb_manifest_url(id)
	output_folder = utils.make_output_folder("bsb", id)
	iiif.download_page_fast(manifest_url, output_folder, page=page)


def get_darmstadt(*, id):
	output_folder = utils.make_output_folder("darmstadt", id)
	manifest_url = f"http://tudigit.ulb.tu-darmstadt.de/show/iiif/{id}/manifest.json"
	iiif.download_book_fast(manifest_url, output_folder)


def get_fulda(*, id):
	output_folder = utils.make_output_folder("fulda", id)
	for page in range(1, 1000):
		# it looks like Fulda library does not use manifest.json, hence it is not possible to guess number of pages in the book in advance
		image_url = f"https://fuldig.hs-fulda.de/viewer/rest/image/{id}/{page:08d}.tif/full/10000,/0/default.jpg"
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading page {page} to {output_filename}")
		try:
			utils.get_binary(output_filename, image_url)
		except ValueError:
			break


def get_goettingen(*, id):
	# No manifest could be found, just iterate over pages while we can
	output_folder = utils.make_output_folder("goettingen", id)
	for page in range(1, 1000):
		page_url = f"https://gdz.sub.uni-goettingen.de/iiif/image/gdz:{id}:{page:08d}/full/max/0/default.jpg"
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if not os.path.isfile(output_filename):
			try:
				print(f"Downloading page #{page:04d} from {page_url}")
				utils.get_binary(output_filename, page_url)
			except ValueError:
				print(f"Got HTTP error on page #{page:04d}. Considering download as complete")
				return
		else:
			print(f"Skip existing page #{page:08d}")


def get_haab(*, first_id, second_id):
	output_folder = utils.make_output_folder("haab", first_id)
	first_found = False

	for page in range(1, 1000):
		base_url = f"https://haab-digital.klassik-stiftung.de/viewer/api/v1/records/{first_id}/files/images/{second_id}_{page:04d}.tif"

		output_filename = utils.make_output_filename(output_folder, page, extension="bmp")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue

		try:
			manifest_url = f"{base_url}/info.json"
			utils.get_text(manifest_url)
			first_found = True
			# Proceed to download
		except HTTPError as ex:
			if ex.response.status_code == http.client.NOT_FOUND:
				if first_found:
					# There is no way to get the number of the last page in the document.
					# Exit on first HTTP 404 response received.
					break
				else:
					# There is no way to get the number of the first page in the document.
					# Continue catching HTTP 404 until we find one.
					print(f"Got HTTP 404 while trying to get page {page:04d}")
					continue
			raise

		iiif.download_image(
			base_url=base_url,
			output_filename=output_filename,
		)


def get_hab_book(*, id):
	output_folder = utils.make_output_folder("hab", id)
	page = 0
	for page in range(1, 1000):
		url = f"http://diglib.hab.de/{id}/max/{page:05d}.jpg"
		output_filename = utils.make_output_filename(output_folder, page=page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:05d}")
			continue
		try:
			print(f"Downloading page #{page:05d} from {url}")
			utils.get_binary(output_filename, url)
		except ValueError:
			break


def get_hab_image(*, id):
	# hab.de site does not use any metadata and just sends unnecessary requests to backend
	# Using head requests to get maximum available zoom and
	class UrlMaker:
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
			# current zoom is not available - consider previous one to be maximal
			break
	assert(max_zoom is not None)
	print(f"Guessed max_zoom={max_zoom}")
	url_maker = UrlMaker(max_zoom)
	tiles_number_x = utils.guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = utils.guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")

	policy = utils.TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
	output_filename = utils.make_output_filename(id.replace("/", "."))
	utils.download_and_sew_tiles(output_filename, url_maker, policy)


def get_karlsruhe(*, id):
	manifest_url = f"https://digital.blb-karlsruhe.de/i3f/v20/{id}/manifest"
	output_folder = utils.make_output_folder("karlsruhe", id)
	# Invoking download_book_fast will cause downloading of a lower-resolution copy of the image.
	# Fallback to a tile-based downloader for the higher resolution.
	iiif.download_book(manifest_url, output_folder)


def get_mv(*, id):
	# it looks like Mecklenburg-Vorpommern does not use manifest.json
	output_folder = utils.make_output_folder("mv", id)
	for page in range(1, 1000):
		output_filename = utils.make_output_filename(output_folder, page)
		if os.path.isfile(output_filename):
			print(f"Skipping existing page {page}")
			continue
		try:
			base_url = f"http://www.digitale-bibliothek-mv.de/viewer/api/v1/records/{id}/files/images/{page:08d}.tif"
			iiif.download_image(base_url, output_filename)
		except ValueError:
			# stop upon first HTTP 404 response
			break


def get_gwlb(*, id):
	output_folder = utils.make_output_folder("gwlb", id)
	page = 0
	while True:
		page += 1
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue

		page_url = f"https://digitale-sammlungen.gwlb.de/content/{id}/jpgs/default/{page:08d}.jpg"
		try:
			print(f"Downloading page #{page:04d} from {page_url}")
			utils.get_binary(output_filename, page_url, allow_redirects=False)
		except ValueError:
			# gwlb.de starts an infinite redirection cycle in case of requesting a non-existing file
			break


def get_rosdok(*, id):
	output_folder = utils.make_output_folder("rosdok", id)
	page = 0
	while True:
		page += 1
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue

		# slashes has to be twice-encoded, otherwise the server returns 404
		slash = "%252F"
		page_url = f"https://rosdok.uni-rostock.de/iiif/image-api/rosdok{slash}{id}{slash}phys_{page:04d}/full/full/0/native.jpg"
		print(f"Downloading page #{page:04d} from {page_url}")
		try:
			utils.get_binary(output_filename, page_url)
		except HTTPError as ex:
			if ex.response.status_code == http.client.NOT_FOUND:
				print("Got HTTP 404, stopping download")
				break


def get_slub(*, id):
	output_folder = utils.make_output_folder("slub", id)
	page = 0
	while True:
		page += 1
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue

		page_url = f"https://digital.slub-dresden.de/data/kitodo/{id}/{id}_tif/jpegs/{page:08d}.tif.original.jpg"
		print(f"Downloading page #{page:04d} from {page_url}")
		try:
			utils.get_binary(output_filename, page_url)
		except HTTPError as ex:
			if ex.response.status_code == http.client.NOT_FOUND:
				print("Got HTTP 404, stopping download")
				break


def get_unihalle(*, id):
	output_folder = utils.make_output_folder("halle", id.split('/')[0])
	manifest_url = f"https://opendata.uni-halle.de/json/iiif/{id}/manifest"
	iiif.download_book_fast(manifest_url, output_folder)
