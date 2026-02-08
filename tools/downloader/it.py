from base64 import urlsafe_b64encode
import json
import os

import iiif
import utils


def get_internet_culturale(*, id):
	full_id = _make_full_id(id)
	# FIXME: this xpath is just broken
	# metadata_url = f"http://www.internetculturale.it/jmms/magparser?id={full_id}&teca={prefix}&mode=all"
	# metadata = utils.get_xml(metadata_url)
	# page_nodes = metadata.findall("./package/medias/media[1]/pages")
	# page_count = int(page_nodes[0].attrib("count"))
	page_url_base = f"http://www.internetculturale.it/jmms/objdownload?id={full_id}&teca={prefix}&resource=img&mode=raw"
	
	output_folder = utils.make_output_folder("iculturale", id)
	for page in range(1, 1000
):
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


def get_hertziana(*, id):
	manifest_url = f"https://dlib.biblhertz.it/iiif/{id}/manifest2.json"
	output_folder = utils.make_output_folder("hertziana", id)
	iiif.download_book_fast_v2(manifest_url, output_folder)


def get_rovereto(*, id):
	manifest_url = f"https://digitallibrary.bibliotecacivica.rovereto.tn.it/server/iiif/{id}/manifest"
	manifest_text = utils.get_text(manifest_url)
	# rovereto.tn.it IIIF server returns incorrect json which is split info multiple short lines.
	# Join them into single line before parsing.
	manifest = json.loads(manifest_text.replace("\r\n", ""))
	
	output_folder = utils.make_output_folder("rovereto", id[0:8])
	iiif.download_book_fast_v2(manifest, output_folder)


def get_sbn(id):
	def _encode_once(raw):
		return urlsafe_b64encode(raw.encode()).decode()

	def _encode_twice(raw):
		return urlsafe_b64encode(urlsafe_b64encode(raw.encode())).decode()

	def _make_full_id(id):
		return f"oai:www.internetculturale.sbn.it/{id}"

	PREFIX = "MagTeca - ICCU"
	full_id = _make_full_id(id)
	encoded_prefix = _encode_twice(PREFIX)
	encoded_full_id = _encode_once(full_id)
	manifest_url = f"https://jmms.iccu.sbn.it/jmms/metadata/{encoded_prefix}/{encoded_full_id}/manifest.json"
	output_folder = utils.make_output_folder("sbn", id)
	iiif.download_book_fast_v3(manifest_url, output_folder)


def get_vatlib(*, id):
	manifest_url = f"http://digi.vatlib.it/iiif/{id}/manifest.json"
	output_folder = make_output_folder("vatlib", id)
	iiif.download_book(manifest_url, output_folder)