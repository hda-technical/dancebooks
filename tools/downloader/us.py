import os
from string import Template

import bs4
import requests

import iiif
import utils


def get_duke(*, id):
	# Manifest is named after the ARK of the item, which is only found on its page
	soup = bs4.BeautifulSoup(
		utils.get_text(f"https://repository.duke.edu/dc/{id}"),
		features="html.parser",
	)
	manifest_url = soup.find(attrs={"data-manifest-url": True})["data-manifest-url"]
	output_folder = utils.make_output_folder("duke", id)
	iiif.download_book_fast_v3(manifest_url, output_folder)


def get_hathitrust(*, id, from_page, to_page, har):
	# babel.hathitrust.org is guarded by Cloudflare
	headers = utils.load_har_session(
		har,
		hostname="babel.hathitrust.org",
		cookie_domain=".hathitrust.org",
	) | {
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
			utils.raise_on_cloudflare(ex)


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


def get_princeton(*, id, from_page, to_page):
	# catalog.princeton.edu does not reference the scans directly,
	# its viewer looks them up in figgy.princeton.edu via GraphQL
	query = requests.Request(
		method="POST",
		url="https://figgy.princeton.edu/graphql",
		json={
			"query": """
				query GetResources($ids: [String!]!) {
					resourcesByOrangelightIds(ids: $ids) {
						... on ScannedResource { manifestUrl }
					}
				}
			""",
			"variables": {"ids": [id]},
		},
	)
	resources = utils.make_request(query).json()["data"]["resourcesByOrangelightIds"]
	manifest_urls = [resource["manifestUrl"] for resource in resources if resource.get("manifestUrl")]
	if len(manifest_urls) != 1:
		raise ValueError(f"Expected exactly one scanned resource for {id}, got {manifest_urls}")
	manifest = utils.get_json(manifest_urls[0])
	if manifest["@type"] != "sc:Manifest":
		members = [member["@id"] for member in manifest.get("manifests", [])]
		raise NotImplementedError(f"Expected sc:Manifest, got {manifest['@type']} with members {members}")

	canvases = manifest["sequences"][0]["canvases"]
	if to_page is None:
		to_page = len(canvases)
	output_folder = utils.make_output_folder("princeton", id)
	print(f"Going to download {to_page - from_page + 1} pages to {output_folder}")
	for page in range(from_page, to_page + 1):
		canvas = canvases[page - 1]
		# Each canvas offers the original scan via `rendering`,
		# which the viewer shows as `Download the original file` link
		url = next(
			(
				rendering["@id"]
				for rendering in canvas.get("rendering", [])
				if rendering.get("format") == "image/tiff"
			),
			None,
		)
		if url is None:
			raise ValueError(f"No TIFF rendering found for page {page}")
		output_filename = utils.make_output_filename(output_folder, page, extension="tif")
		if os.path.exists(output_filename):
			utils.notify_skip(page)
			continue
		print(f"Downloading page {page:04d} to {output_filename}")
		utils.get_binary(output_filename, url)
