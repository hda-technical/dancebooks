import math

from dancebooks import img

import utils


class UrlMaker:
	def __init__(self, base_url, max_zoom, ext="jpg"):
		self.base_url = base_url
		self.max_zoom = max_zoom
		self.ext = ext

	def __call__(self, tile_x, tile_y):
		return f"{self.base_url}/{self.max_zoom}/{tile_x}_{tile_y}.{self.ext}"


def make_tile_policy(metadata_url):
	image_metadata = utils.get_xml(metadata_url)

	tile_size = int(image_metadata.attrib["TileSize"])
	overlap = int(image_metadata.attrib["Overlap"])

	size_metadata = utils.first(image_metadata)
	width = int(size_metadata.attrib["Width"])
	height = int(size_metadata.attrib["Height"])

	return img.TiledGeometry(width, height, tile_size=tile_size, overlap=overlap)


def download_image(output_filename, metadata_url, url_maker=None):
	policy = make_tile_policy(metadata_url)
	if url_maker is None:
		# `<name>.xml` manifest is accompanied by the `<name>_files` tile folder,
		# holding a zoom level per halving of the image, the topmost one being a single pixel
		max_zoom = math.ceil(math.log2(max(policy.size)))
		url_maker = UrlMaker(metadata_url.rpartition(".")[0] + "_files", max_zoom)
	utils.download_and_sew_tiles(output_filename, url_maker, policy)
