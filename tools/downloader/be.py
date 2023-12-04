import os

import iiif
import utils


def get_libis(id):
	output_folder = utils.make_output_folder("be_libis", id)
	manifest_url = f"https://lib.is/{id}/manifest"
	iiif.download_book_fast(manifest_url, output_folder)
	

def get_kbr(id, volume):
	class UrlMaker:
		def __init__(self, *, zoom, page):
			self.id_dashed = id[0] + '-' + id[1:]
			self.id_slashed = '/'.join(id)
			self.zoom = zoom
			self.page = page

		def __call__(self, tile_x, tile_y):
			url = f"https://viewerd.kbr.be/display/{self.id_slashed}/0000-00-00_{volume:02d}/zoomtiles/BE-KBR00_{self.id_dashed}_0000-00-00_{volume:02d}_{self.page:04d}/{self.zoom}-{tile_x}-{tile_y}.jpg"
			return url

	
	# We have to provide referer with each request being dispatched.
	# This is easiest, though very dirty way to do it.
	referer = f"https://viewerd.kbr.be/gallery.php?map={'/'.join(id)}/0000-00-00_{volume:02d}/"
	utils.HEADERS["Referer"] = referer

	output_folder = utils.make_output_folder("be_kbr", f"{id}_{volume:02d}")
	
	url_maker_maker = lambda zoom: UrlMaker(zoom=zoom, page=1)
	tiles_zoom = utils.guess_tiles_zoom(url_maker_maker)
	print(f"Guessed tiles_zoom={tiles_zoom}")
	url_maker = UrlMaker(zoom=tiles_zoom, page=1)

	tiles_number_x = utils.guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = utils.guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")

	page = 1
	while True:
		output_filename = utils.make_output_filename(output_folder, page)
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page:04d}")
			page += 1
			continue
		policy = utils.TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size=768)
		policy.trim = True
		url_maker = UrlMaker(zoom=tiles_zoom, page=page)
		utils.download_and_sew_tiles(output_filename, url_maker, policy)
		page += 1
		
		
		#if (tiles_number_x == 0) or (tiles_number_y == 0):
		#	 print(f"Page {page:04d} was not found")
		#	 break