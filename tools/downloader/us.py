import os

import iiif
import utils


def get_hathitrust(*, id, from_page, to_page):
	raise RuntimeError("This downloader requires Cookies and JavaScript. Use DownThemAll! instead")
	output_folder = utils.make_output_folder("hathitrust", id)
	metadata_url = f"https://babel.hathitrust.org/cgi/imgsrv/meta?id={id}"
	metadata = utils.get_json(metadata_url)
	if from_page is None:
		from_page = 1
	if to_page is None:
		to_page = metadata["total_items"]
	print(f"Going to download {to_page - from_page + 1} pages to {output_folder}")
	for page in range(from_page, to_page + 1):
		url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={id}&format=image/tiff&size=ppi:600&seq={page}"
		output_filename = utils.make_output_filename(output_folder, page, extension="tif")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading page {page} to {output_filename}")
		utils.get_binary(output_filename, url)


def get_huntington(*, id):
	manifest_url = f"https://hdl.huntington.org/iiif/2/{id}/manifest.json"
	output_folder = utils.make_output_folder("huntington", id)
	iiif.download_book_fast(manifest_url, output_folder)


def get_loc(*, id):
	# manifest_url = f"https://www.loc.gov/item/{id}/manifest.json"
	output_folder = utils.make_output_folder("loc", id)
	# manifest = utils.get_json(manifest_url)
	# canvases = manifest["sequences"][0]["canvases"]
	# turn id in from rbc0001.2021rosen1620A into rbc/rbc0001/2021/2021rosen1620A
	# FIXME: most likely this does not scale
	id1, id2 = id.split(".")
	tif_id = f"{id1[0:3]}/{id1}/{id2[0:4]}/{id2}"
	for page in range(1000):
		tif_url = f"https://tile.loc.gov/storage-services/master/{tif_id}/{page + 1:04d}.tif"
		output_filename = utils.make_output_filename(output_folder, page + 1, extension="tif")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading {output_filename} from {tif_url}")
		utils.get_binary(output_filename, tif_url)


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
