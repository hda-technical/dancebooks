import os
import http

import iiif
import utils

import requests
from requests.exceptions import HTTPError


def get_haab(*, first_id, second_id):
	output_folder = utils.make_output_folder("haab", first_id)
	first_found = False

	for page in range(1, 1000):
		base_url = f"https://haab-digital.klassik-stiftung.de/viewer/api/v1/records/{first_id}/files/images/{second_id}_{page:04d}.tif"
		
		output_filename = utils.make_output_filename(output_folder, page, extension="bmp")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		
		try:
			manifest_url = f"{base_url}/info.json"
			utils.get_text(manifest_url)
			first_found = True
			# Proceed to download
		except HTTPError as ex:
			if ex.response.status_code == http.client.NOT_FOUND:
				if first_found:
					# There is no way to get the number of the last page in the document.
					# Exit on first HTTP 404 response received.
					break
				else:
					# There is no way to get the number of the first page in the document.
					# Continue catching HTTP 404 until we find one.
					print(f"Got HTTP 404 while trying to get page {page:04d}")
					continue
			raise

		print(f"Will download from {manifest_url}")
		iiif.download_image(
			base_url=base_url,
			output_filename=output_filename,
		)

def get_karlsruhe(*, id):
	manifest_url = f"https://digital.blb-karlsruhe.de/i3f/v20/{id}/manifest"
	output_folder = utils.make_output_folder("karlsruhe", id)
	# Invoking download_book_fast will cause downloading of a lower-resolution copy of the image.
	# Fallback to a tile-based downloader for the higher resolution.
	iiif.download_book(manifest_url, output_folder)
