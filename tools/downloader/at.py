import os

import utils


def get_ubs(*, first, last):
	output_folder = utils.make_output_folder("ubs", first)
	
	for page in range(first, last + 1):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue

		page_url = f"https://eplus.uni-salzburg.at/obvusboa/download/webcache/0/{page}"
		print(f"Downloading page #{page:04d} from {page_url}")
		utils.get_binary(output_filename, page_url)