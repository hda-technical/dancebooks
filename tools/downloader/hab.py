import os

import requests

import utils


def get_book(id):
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


def get_image(id):
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
