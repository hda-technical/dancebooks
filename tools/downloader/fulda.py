import os

import iiif
import utils


def get(id):
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