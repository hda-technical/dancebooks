import os

import iiif
import utils


def get_mzk(*, id):
	# mzk uses json metadata, while other might use xml (probably due to api v7.0)
	# despite being hosted on the same website (www.digitalniknihovna.cz)
	metadata_url = f'https://api.kramerius.mzk.cz/search/api/client/v7.0/search?fl=pid,page.number&q=own_parent.pid:"uuid:{id}"&rows=4000'
	print(f"Downloading metadata from {metadata_url}")
	metadata = utils.get_json(metadata_url)
	output_folder = utils.make_output_folder("mzk", id[:8])
	for page, doc in enumerate(metadata["response"]["docs"]):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page:04d}")
			continue
		page_id = doc["pid"].removeprefix("uuid:")
		print(f"Downloading page {page:04d} with id {page_id}")
		base_url = f"https://api.kramerius.mzk.cz/search/iiif/uuid:{page_id}"
		iiif.download_image_fast_v1(base_url, output_filename)
		
		
def get_nkp(*, id):
	# nkp uses xml metadata, while other might use json (probably due to api v5.0)
	# despite being hoster on the same website (www.digitalniknihovna.cz)
	metadata_url = f'https://kramerius5.nkp.cz/search/api/v5.0/search?fl=PID,page.number&q=parent_pid:"uuid:{id}"&rows=4000'
	print(f"Downloading metadata from {metadata_url}")
	metadata = utils.get_xml(metadata_url)
	output_folder = utils.make_output_folder("nkp", id[:8])
	for page, node in enumerate(metadata.findall("result/doc/str")):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page:04d}")
			continue
		page_id = node.text.removeprefix("uuid:")
		page_url = f"https://kramerius5.nkp.cz/search/api/v5.0/item/uuid:{page_id}/streams/IMG_FULL"
		print(f"Downloading page {page:04d} from {page_url}")
		utils.get_binary(output_filename, page_url)