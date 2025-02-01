import os

import iiif
import utils


def get_libis(id):
	output_folder = utils.make_output_folder("be_libis", id)
	manifest_url = f"https://lib.is/{id}/manifest"
	iiif.download_book_fast(manifest_url, output_folder)
	

class KbrUrlMaker:
	def __init__(self, *, id, volume, zoom, page):
		match id[0]:
			case 'A':
				self.id_dashed = id[0] + '-' + id[1:]
			case 'B':
				self.id_dashed = id[0] + '-' + '1' + id[1:]
		self.id_slashed = '/'.join(id)
		self.volume = volume
		self.zoom = zoom
		self.page = page

	def set_page(self, page):
		self.page = page

	def __call__(self, tile_x, tile_y):
		url = f"https://viewerd.kbr.be/display/{self.id_slashed}/0000-00-00_{self.volume:02d}/zoomtiles/BE-KBR00_{self.id_dashed}_0000-00-00_{self.volume:02d}_{self.page:04d}/{self.zoom}-{tile_x}-{tile_y}.jpg"
		return url
	

def get_kbr_page(*, id, volume, page):
	# We have to provide referer with each request being dispatched.
	# This is easiest, though very dirty way to do it.
	referer = f"https://viewerd.kbr.be/gallery.php?map={'/'.join(id)}/0000-00-00_{volume:02d}/"
	utils.HEADERS["Referer"] = referer

	output_folder = utils.make_output_folder("be_kbr", f"{id}_{volume:02d}")
	output_filename = utils.make_output_filename(output_folder, page)

	url_maker_maker = lambda zoom: KbrUrlMaker(id=id, volume=volume, zoom=zoom, page=page)
	tiles_zoom = utils.guess_tiles_zoom(url_maker_maker)
	print(f"Guessed tiles_zoom={tiles_zoom}")
	url_maker = KbrUrlMaker(id=id, volume=volume, zoom=tiles_zoom, page=page)

	tiles_number_x = utils.guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = utils.guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")

	policy = utils.TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size=768)
	policy.trim = True
	utils.download_and_sew_tiles(output_filename, url_maker, policy)


def get_kbr_book(*, id, volume):
	# We have to provide referer with each request being dispatched.
	# This is easiest, though very dirty way to do it.
	referer = f"https://viewerd.kbr.be/gallery.php?map={'/'.join(id)}/0000-00-00_{volume:02d}/"
	utils.HEADERS["Referer"] = referer

	output_folder = utils.make_output_folder("be_kbr", f"{id}_{volume:02d}")
	
	url_maker_maker = lambda zoom: KbrUrlMaker(id=id, volume=volume, zoom=zoom, page=1)
	tiles_zoom = utils.guess_tiles_zoom(url_maker_maker)
	print(f"Guessed tiles_zoom={tiles_zoom}")
	url_maker = KbrUrlMaker(id=id, volume=volume, zoom=tiles_zoom, page=1)

	tiles_number_x = utils.guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = utils.guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")

	policy = utils.TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size=768)
	policy.trim = True

	page = 1
	while True:
		output_filename = utils.make_output_filename(output_folder, page)
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page:04d}")
			page += 1
			continue
		
		url_maker.set_page(page)
		utils.download_and_sew_tiles(output_filename, url_maker, policy)
		page += 1
		
		#if (tiles_number_x == 0) or (tiles_number_y == 0):
		#	 print(f"Page {page:04d} was not found")
		#	 break