import enum
import os

from dancebooks import img

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
			tile = policy.tile(tile_x, tile_y)
			return f"{base_url}/{tile.x},{tile.y},{tile.width},{tile.height}/{tile.width},{tile.height}/0/{desired_quality}.{desired_format}"

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

	policy = img.TiledGeometry(width, height, tile_size=tile_size)
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
	print(f"Will download {len(canvases)} pages")
	for page, metadata in enumerate(canvases, start=1):
		output_filename = utils.make_output_filename(output_folder, page)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		base_url = metadata["images"][-1]["resource"]["service"]["@id"]
		download_image(base_url, output_filename)


def download_image_fast_v1(base_url, output_filename, *, width=None, height=None):
	"""
	Download image as a single tile.
	Image size is requested from info.json unless it is known by the caller
	(certain manifests, e. g. haab ones, state it for every canvas).
	"""
	if (width is None) or (height is None):
		info_url = f"{base_url}/info.json"
		info = utils.get_json(info_url)
		width = info["width"]
		height = info["height"]
	img_url = f"{base_url}/0,0,{width},{height}/{width},{height}/0/default.jpg"
	utils.get_binary(output_filename, img_url)


class ImageKind(enum.Enum):
	"""
	Kind of the page image to be downloaded,
	defining the part of IIIF v2 canvas its url is taken from
	"""
	# Image resource url as is.
	# Normally it requests the full-sized image from the image service
	# (e. g. `{service}/full/full/0/default.jpg`).
	RESOURCE = enum.auto()

	# Full-sized image re-encoded by the image service, i. e. `{service}/full/max/0/default.jpg`.
	# Certain installations (e. g. digi-hub.de) link downscaled thumbnails as image resources.
	SERVICE = enum.auto()

	# Original source file linked from `rendering` section of the canvas, served without re-encoding.
	# Provided by certain installations (e. g. opendata.uni-halle.de),
	# while others put PDFs, OCR results or links to the viewer here.
	RENDERING = enum.auto()


def _get_image_url_v2(canvas, kind: ImageKind):
	resource = canvas["images"][-1]["resource"]
	match kind:
		case ImageKind.RESOURCE:
			return resource["@id"]
		case ImageKind.SERVICE:
			return f"{resource['service']['@id']}/full/max/0/default.jpg"
		case ImageKind.RENDERING:
			for rendering in canvas.get("rendering", []):
				if rendering.get("format", "").startswith("image/"):
					return rendering["@id"]
			raise ValueError(f"Canvas {canvas['@id']} has no image in rendering section")


def _download_image_fast_v2(
	metadata,
	page,
	output_filename,
	*,
	kind=ImageKind.RESOURCE,
	**rq_kvargs,
):
	url = _get_image_url_v2(metadata, kind)
	print(f"Downloading page #{page:04d} from {url}")
	utils.get_binary(output_filename, url, **rq_kvargs)


def download_book_fast_v2(
	manifest: dict | str,
	output_folder,
	*,
	from_page=1,
	to_page=None,
	kind=ImageKind.RESOURCE,
	**rq_kvargs,
):
	"""
	Downloads entire book via IIIF protocol (v2).
	Issues single request per image, but might be unsupported by certain backends.

	API is documented here:
	http://iiif.io/about/

	`from_page` and `to_page` limit the download to a 1-based inclusive range of pages
	(`to_page` defaults to the last page of the book).

	`kind` selects the url each page is downloaded from (see ImageKind).
	"""
	if isinstance(manifest, str):
		manifest = utils.get_json(manifest, **rq_kvargs)
	canvases = manifest["sequences"][0]["canvases"]
	if to_page is None:
		to_page = len(canvases)
	if not (1 <= from_page <= to_page <= len(canvases)):
		raise ValueError(f"Invalid page range {from_page}-{to_page} for a book of {len(canvases)} pages")
	print(f"Will download {to_page - from_page + 1} pages")
	for page in range(from_page, to_page + 1):
		metadata = canvases[page - 1]
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		_download_image_fast_v2(
			metadata=metadata,
			page=page,
			output_filename=output_filename,
			kind=kind,
			**rq_kvargs,
		)


def download_page_fast_v2(
	manifest_url,
	output_folder,
	*,
	page,
	kind=ImageKind.RESOURCE,
	**rq_kvargs,
):
	"""
	Downloads single page via IIIF protocol (v2).
	Issues single request per image, but might be unsupported by certain backends.

	API is documented here:
	http://iiif.io/about/
	"""
	manifest = utils.get_json(manifest_url, **rq_kvargs)
	canvases = manifest["sequences"][0]["canvases"]
	output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
	_download_image_fast_v2(
		metadata=canvases[page],
		page=page,
		output_filename=output_filename,
		kind=kind,
		**rq_kvargs,
	)


def download_book_fast_v3(manifest_url, output_folder):
	"""
	Downloads entire book via IIIF protocol (v3).
	Issues single request per image, but might be unsupported by certain backends.

	API is documented here:
	http://iiif.io/about/
	"""
	manifest = utils.get_json(manifest_url)
	canvases = manifest["items"]
	print(f"Will download {len(canvases)} pages")
	for page, metadata in enumerate(canvases, start=1):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page:04d}")
			continue
		image_url = metadata["items"][0]["items"][0]["body"]["id"]
		# Image url has the following structure:
		#
		#     {base}/{region}/{size}/{rotation}/{quality}.{format}
		#             full     max
		#
		# Region `full` (uncropped image) is valid in all versions of IIIF Image API.
		# Size `full` (native resolution) was deprecated in Image API v2.1 and removed in v3.0,
		# where `max` should be used instead.
		# Certain manifests (e. g. polona.pl ones) still provide `full/full` urls,
		# which are rejected by their v3 image servers with HTTP 400.
		image_url = image_url.replace("/full/full/", "/full/max/")
		print(f"Downloading page #{page:04d} from {image_url}")
		utils.get_binary(output_filename, image_url)
