import os

import utils


def get_book(id):
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