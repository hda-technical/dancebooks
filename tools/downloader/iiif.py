import os

import utils


def download_image(base_url, output_filename):
	"""
	Downloads single image via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	DESIRED_QUALITIES = ["color", "native", "default"]
	DESIRED_FORMATS = ["png", "tif", "jpg"]

	class UrlMaker:
		def __call__(self, tile_x, tile_y):
			left = tile_size * tile_x
			top = tile_size * tile_y
			tile_width = min(width - left, tile_size)
			tile_height = min(height - top, tile_size)
			tile_url = f"{base_url}/{left},{top},{tile_width},{tile_height}/{tile_width},{tile_height}/0/{desired_quality}.{desired_format}"
			return tile_url

	metadata_url = f"{base_url}/info.json"
	metadata = utils.get_json(metadata_url)
	if "tiles" in metadata:
		# Served by e. g. vatlib servant
		tile_size = metadata["tiles"][0]["width"]
	else:
		# Served by e. g. Gallica servant
		tile_size = 1024
	width = metadata["width"]
	height = metadata["height"]

	desired_quality = "default"
	desired_format = "jpg"
	profile = metadata.get("profile")
	if (profile is not None) and (len(profile) >= 2) and (profile is not str):
		# Profile is not served by Gallica servant, but served by e. g. British Library servant
		# Complex condition helps to ignore missing metadata fields, see e. g.:
		# https://gallica.bnf.fr/iiif/ark:/12148/btv1b10508435s/f1/info.json
		# http://www.digitale-bibliothek-mv.de/viewer/rest/image/PPN880809493/00000001.tif/info.json
		if "qualities" in profile[1]:
			available_qualities = profile[1]["qualities"]
			for quality in DESIRED_QUALITIES:
				if quality in available_qualities:
					desired_quality = quality
					break
			else:
				raise RuntimeError(f"Can not choose desired image quality. Available qualities: {available_qualities!r}")
		if "formats" in profile[1]:
			available_formats = profile[1]["formats"]
			for format in DESIRED_FORMATS:
				if format in available_formats:
					desired_format = format
					break
			else:
				raise RuntimeError(f"Can not choose desired image format. Available formats: {available_formats!r}")

	policy = utils.TileSewingPolicy.from_image_size(width, height, tile_size)
	utils.download_and_sew_tiles(output_filename, UrlMaker(), policy)


def download_book(manifest: str | dict, output_folder):
	"""
	Downloads entire book via IIIF protocol.
	API is documented here:
	http://iiif.io/about/
	"""
	if isinstance(manifest, str):
		manifest = utils.get_json(manifest)
	canvases = manifest["sequences"][0]["canvases"]
	for page, metadata in enumerate(canvases):
		output_filename = utils.make_output_filename(output_folder, page)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		base_url = metadata["images"][-1]["resource"]["service"]["@id"]
		download_image(base_url, output_filename)


def download_image_fast_v1(base_url, output_filename):
	"""
	Download image as a single tile
	"""
	info_url = f"{base_url}/info.json"
	info = utils.get_json(info_url)
	w = info["width"]
	h = info["height"]
	img_url = f"{base_url}/0,0,{w},{h}/{w},{h}/0/default.jpg"
	utils.get_binary(output_filename, img_url)


def _download_image_fast(metadata, page, output_filename):
	url = None
	if not url:
		# Certain installations (only opendata.uni-halle.de so far)
		# provide higher resolution images in 'rendering' section
		url = metadata.get("rendering", [{}])[-1].get("@id", "")
	if not url:
		url = metadata["images"][-1]["resource"]["@id"]

	print(f"Downloading page #{page:04d} from {url}")
	utils.get_binary(output_filename, url)


def download_book_fast(manifest: dict | str, output_folder):
	"""
	Downloads entire book via IIIF protocol (v2).
	Issues single request per image, but might be unsupported by certain backends.

	API is documented here:
	http://iiif.io/about/
	"""
	if isinstance(manifest, str):
		manifest = utils.get_json(manifest)
	canvases = manifest["sequences"][0]["canvases"]
	for page, metadata in enumerate(canvases):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		_download_image_fast(
			metadata=metadata,
			page=page,
			output_filename=output_filename,
		)


def download_page_fast(manifest_url, output_folder, *, page):
	"""
	Downloads single page via IIIF protocol.
	Issues single request per image, but might be unsupported by certain backends.

	API is documented here:
	http://iiif.io/about/
	"""
	manifest = utils.get_json(manifest_url)
	canvases = manifest["sequences"][0]["canvases"]
	output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
	_download_image_fast(
		metadata=canvases[page],
		page=page,
		output_filename=output_filename,
	)


def download_book_fast_v3(manifest_url, output_folder):
	"""
	Downloads entire book via IIIF protocol (v3).
	Issues single request per image, but might be unsupported by certain backends.

	API is documented here:
	http://iiif.io/about/
	"""
	print(f"GET {manifest_url}")
	manifest = utils.get_json(manifest_url)
	for page, metadata in enumerate(manifest["items"]):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		image_url = metadata["items"][0]["items"][0]["body"]["id"]
		print(f"Downloading page #{page:04d} from {image_url}")
		utils.get_binary(output_filename, image_url)