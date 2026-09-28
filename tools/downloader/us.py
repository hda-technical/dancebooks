import json
import os
from string import Template
import urllib.parse

import requests

import iiif
import utils


def _load_hathitrust_session(har_filename):
	"""
	Extracts cookies and User-Agent of the last request to babel.hathitrust.org
	found in HAR file saved by browser developer tools.

	Returns headers to be sent along with every request.
	"""
	with open(har_filename) as har_file:
		entries = json.load(har_file)["log"]["entries"]
	requests_to_babel = [
		entry["request"]
		for entry in entries
		if urllib.parse.urlsplit(entry["request"]["url"]).hostname == "babel.hathitrust.org"
	]
	if not requests_to_babel:
		raise ValueError(f"{har_filename} contains no requests to babel.hathitrust.org")
	request = requests_to_babel[-1]
	# HTTP/2 header names are lowercase
	headers = {header["name"].lower(): header["value"] for header in request["headers"]}
	cookies = [(cookie["name"], cookie["value"]) for cookie in request["cookies"]]
	if not cookies:
		raise ValueError(
			f"{har_filename} contains no cookies. "
			"Chromium-based browsers strip them by default, "
			"use `Export HAR (with sensitive data)` or switch to Firefox"
		)
	for name, value in cookies:
		utils.session.cookies.set(name, value, domain=".hathitrust.org", path="/")
	print(f"Loaded {len(cookies)} cookies from {har_filename}")
	return {
		"User-Agent": headers["user-agent"],
	}


def get_hathitrust(*, id, from_page, to_page, har):
	# babel.hathitrust.org is guarded by Cloudflare which blocks requests
	# lacking the clearance obtained by a real browser.
	# Hence we act as DownThemAll! does: reuse the cookies and the User-Agent of the browser
	# (the clearance is bound to both of them and to the IP address).
	headers = _load_hathitrust_session(har) | {
		"Referer": f"https://babel.hathitrust.org/cgi/pt?id={id}",
	}

	if to_page is None:
		metadata = utils.get_json(f"https://babel.hathitrust.org/cgi/imgsrv/meta?id={id}", headers=headers)
		to_page = metadata["total_items"]

	output_folder = utils.make_output_folder("hathitrust", id)
	print(f"Going to download {to_page - from_page + 1} pages to {output_folder}")
	for page in range(from_page, to_page + 1):
		output_filename = utils.make_output_filename(output_folder, page, extension="tif")
		if os.path.exists(output_filename):
			utils.notify_skip(page)
			continue
		url = f"https://babel.hathitrust.org/cgi/imgsrv/image?id={id}&attachment=1&tracker=D1&format=image%2Ftiff&size=full&seq={page}"
		print(f"Downloading page {page:04d} to {output_filename}")
		try:
			# HathiTrust throttles aggressive clients with HTTP 429,
			# get_binary retries these just like it does for Gallica
			utils.get_binary(output_filename, url, headers=headers)
		except requests.exceptions.HTTPError as ex:
			if ex.response.status_code == 403:
				raise RuntimeError("Got HTTP 403 from Cloudflare, reload the book in the browser and save HAR file again") from ex
			raise
		except BaseException:
			# do not leave truncated pages behind as they will be skipped upon restart
			if os.path.exists(output_filename):
				os.remove(output_filename)
			raise


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


def get_nypl(*, first, last):
	output_folder = utils.make_output_folder("nypl", first)
	for page in range(first, last + 1):
		output_filename = utils.make_output_filename(output_folder, page=page, extension="jpg")
		if os.path.isfile(output_filename):
			print(f"Skip downloading exising page #{idx:04d}")
			continue
		# Download jpg files, as tif files require additional framing
		url = f"https://iiif.nypl.org/iiif/3/{page}/full/max/0/default.jpg"
		print(f"Downloading page #{page}")
		utils.get_binary(output_filename, url)


def get_yale_book(*, id):
	manifest_url = f"https://collections.library.yale.edu/manifests/{id}"
	output_folder = utils.make_output_folder("yale", id)
	iiif.download_book_fast_v3(manifest_url, output_folder)
