import os

import utils


def get_hathitrust(*, id, from_page, to_page):
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
		

def get_nypl(*, id):
	metadata_url = f"https://digitalcollections.nypl.org/items/{id}/captures?page=1&per_page=1000"
	metadata = utils.get_json(metadata_url)
	output_folder = utils.make_output_folder("nypl", id[0:8])
	captures = metadata["response"]["captures"]
	print(f"Going to download {len(captures)} images")
	for idx, capture in enumerate(captures):
		output_filename = utils.make_output_filename(output_folder, page=idx, extension="tif")
		if os.path.isfile(output_filename):
			print(f"Skip downloading exising page #{idx:04d}")
			continue
		url = capture["high_res_link"]
		print(f"Downloading page #{idx:04d}")
		utils.get_binary(output_filename, url)