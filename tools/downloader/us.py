import os
from string import Template
import textwrap

import iiif
import utils


def get_hathitrust(*, id, from_page, to_page):
	print(textwrap.dedent(f"""
		This downloader requires Cookies and JavaScript to function.
		Paste
		https://babel.hathitrust.org/cgi/imgsrv/image?id={id}&attachment=1&tracker=D1&format=image%2Ftiff&size=full&seq=[{from_page}:{to_page}]
		to Use DownThemAll! -> Add Download to get images
		"""
	))


def get_huntington(*, id, page):
	id = id.replace('/', ':')
	manifest_url = f"https://hdl.huntington.org/iiif/2/{id}/manifest.json"
	output_folder = utils.make_output_folder("huntington", id)
	if page:
		iiif.download_page_fast_v2(manifest_url, output_folder, page=page)
	else:
		iiif.download_book_fast_v2(manifest_url, output_folder)


def get_loc(*, id):
	# manifest_url = f"https://www.loc.gov/item/{id}/manifest.json"
	output_folder = utils.make_output_folder("loc", id)
	# manifest = utils.get_json(manifest_url)
	# canvases = manifest["sequences"][0]["canvases"]
	# FIXME: most likely this does not scale
	if id.startswith("rbc"):
		# turn rbc0001.2021rosen1620A into rbc/rbc0001/2021/2021rosen1620A
		id1, id2 = id.split(".")
		page_id = f"{id1[0:3]}/{id1}/{id2[0:4]}/{id2}"
		ext = "tif"
		page_template = f"https://tile.loc.gov/storage-services/master/{page_id}/" + "${page}" + f".{ext}"
		page_template = Template(page_template)
	elif id.startswith("music"):
		# turn music.musrism-2020562476 into music/musrism-2020562476/musrism-2020562476
		id1, id2 = id.split(".")
		page_id = f"{id1}/{id2}/{id2}"
		ext = "jp2"
		page_template = f"https://tile.loc.gov/storage-services/public/{page_id}_" + "${page}" + f".{ext}"
		page_template = Template(page_template)
	else:
		raise ValueError(f"id {id} does not belong to a known domain")
	for page in range(1000):
		output_filename = utils.make_output_filename(output_folder, page + 1, extension=ext)
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		url = page_template.substitute(page=f"{page + 1:04d}")
		print(f"Downloading {output_filename} from {url}")
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


def get_yale_book(*, id):
	manifest_url = f"https://collections.library.yale.edu/manifests/{id}"
	output_folder = utils.make_output_folder("yale", id)
	iiif.download_book_fast_v3(manifest_url, output_folder)
