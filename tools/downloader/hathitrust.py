import os

import utils


def get(*, id, from_page, to_page):
	output_folder = utils.make_output_folder("hathitrust", id)
	metadata_url = f"https://babel.hathitrust.org/cgi/imgsrv/meta?id={id}"
	metadata = utils.get_json(metadata_url)
	if from_page is None:
		from_page = 1
	if to_page is None:
		to_page = metadata["total_items"]
	print(f"Going to download {to_page - from_page + 1} pages to {output_folder}")
	for page in range(from_page, to_page + 1):
		url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={id};seq={page};width=1000000"
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading page {page} to {output_filename}")
		utils.get_binary(output_filename, url)