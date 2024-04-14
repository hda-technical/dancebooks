import os

import iiif
import utils


def get_kramerius(*, id):
	metadata_url = f'https://api.kramerius.mzk.cz/search/api/client/v7.0/search?fl=pid,page.number&q=own_parent.pid:"uuid:{id}"&rows=4000'
	metadata = utils.get_json(metadata_url)
	output_folder = utils.make_output_folder("kram", id)
	for page, doc in enumerate(metadata["response"]["docs"]):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page:04d}")
			continue
		page_id = doc["pid"].removeprefix("uuid:")
		print(f"Downloading page {page:04d} with id {page_id}")
		base_url = f"https://api.kramerius.mzk.cz/search/iiif/uuid:{page_id}"
		iiif.download_image_fast_v1(base_url, output_filename)