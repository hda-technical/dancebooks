import os

import deep_zoom
import utils


def get_academica(*, book_id, first_page_id, last_page_id):
	output_folder = utils.make_output_folder("academica", book_id)
	for page_id in range(first_page_id, last_page_id + 1, 8):
		metadata_url = f"https://academica.edu.pl/resource/image/{book_id}/{page_id}.tif.dzi"
		print(f"Metadata will be read from {metadata_url}")
		print(utils.get_text(metadata_url))
		output_filename = utils.make_output_filename(output_folder, page_id)
		url_maker = deep_zoom.UrlMaker(
			base_url=f"https://academica.edu.pl/resource/image/{book_id}/{page_id}.tif_files",
			max_zoom=12,
		)
		deep_zoom.download_image(
			output_filename=output_filename,
			metadata_url=metadata_url,
			url_maker=url_maker,
		)


def get_polona(*, id):
	metadata_url = f"https://polona.pl/api/entities/{id}"
	metadata = utils.get_json(metadata_url)
	output_folder = utils.make_output_folder("polona", id)
	for page, page_metadata in enumerate(metadata["scans"]):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		found = False
		for image_metadata in page_metadata["resources"]:
			if image_metadata["mime"] == "image/jpeg":
				print(f"Downloading page #{page:08d}")
				utils.get_binary(output_filename, image_metadata["url"])
				found = True
		if not found:
			raise Exception(f"JPEG file was not found in image_metadata for page {page}")