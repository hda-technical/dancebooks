import requests

import iiif
import utils


def _make_manifest_url(id):
	return f"https://gallica.bnf.fr/iiif/ark:/12148/{id}/manifest.json"


def get_gallica_book(id):
	manifest_url = _make_manifest_url(id)
	output_folder = utils.make_output_folder("gallica", id)
	iiif.download_book_fast(manifest_url, output_folder)


def get_gallica_page(id, page):
	manifest_url = _make_manifest_url(id)
	output_folder = utils.make_output_folder("gallica", id)
	iiif.download_page_fast(manifest_url, output_folder, page=page)


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


def get_retronews(*, document_id, page):
	metadata_url = f"https://pv5web.retronews.fr/api/document/{document_id}/page/{page}"
	metadata = utils.get_json(metadata_url)

	output_folder = utils.make_output_folder("retronews", document_id)
	output_filename = utils.make_output_filename(output_folder, page=page)

	policy = utils.TileSewingPolicy.from_image_size(
		width=metadata["width"],
		height=metadata["height"],
		tile_size=512,
	)
	url_maker = lambda tile_x, tile_y: f"https://pv5web.retronews.fr/api/document/{document_id}/page/{page}/tile/{tile_x}/{tile_y}/0"
	utils.download_and_sew_tiles(output_filename, url_maker, policy)
