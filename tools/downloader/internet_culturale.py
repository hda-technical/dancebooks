import os

import utils


def get(id):
	full_id = f"oai:www.internetculturale.sbn.it/{id}"
	# FIXME: this xpath is just broken
	# metadata_url = f"http://www.internetculturale.it/jmms/magparser?id={full_id}&teca=MagTeca+-+ICCU&mode=all"
	# metadata = utils.get_xml(metadata_url)
	# page_nodes = metadata.findall("./package/medias/media[1]/pages")
	# page_count = int(page_nodes[0].attrib("count"))
	page_url_base = f"http://www.internetculturale.it/jmms/objdownload?id={full_id}&teca=MagTeca%20-%20ICCU&resource=img&mode=raw"
	
	output_folder = utils.make_output_folder("iculturale", id)
	for page in range(1, 1000):
		page_url = f"{page_url_base}&start={page}"
		print(f"Downloading page #{page} from {page_url}")
		output_filename = utils.make_output_filename(output_folder, page=page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		data_size = utils.get_binary(output_filename, page_url)
		if data_size == 0:
			os.remove(output_filename)
			break