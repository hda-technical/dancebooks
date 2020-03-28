import os

import utils


def get_book_from_hathitrust(id):
	output_folder = utils.make_output_folder("hathitrust", id)
	metadata_url = f"https://babel.hathitrust.org/cgi/imgsrv/meta?id={id}"
	metadata = utils.get_json(metadata_url)
	total_pages = metadata["total_items"]
	print(f"Going to download {total_pages} pages to {output_folder}")
	for page in range(1, total_pages):
		url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={id};seq={page};width=1000000"
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading page {page} to {output_filename}")
		utils.get_binary(output_filename, url)