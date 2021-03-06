import requests

import iiif
import utils


def get_gallica(id):
	manifest_url = f"https://gallica.bnf.fr/iiif/ark:/12148/{id}/manifest.json"
	output_folder = utils.make_output_folder("gallica", id)
	iiif.download_book_fast(manifest_url, output_folder)


def get_candide(id):
	#The site does not use any metadata and simply sends unnecessary requests to backend
	#Using head requests to get maximum available zoom and
	class UrlMaker:
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
	tiles_number_x = utils.guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = utils.guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")

	policy = utils.TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
	output_filename = utils.make_output_filename(id.replace("/", "."))
	utils.download_and_sew_tiles(output_filename, url_maker, policy)