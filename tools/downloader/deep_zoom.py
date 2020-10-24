import utils


class UrlMaker:
	def __init__(self, base_url, max_zoom, ext="jpg"):
		self.base_url = base_url
		self.max_zoom = max_zoom
		self.ext = ext

	def __call__(self, tile_x, tile_y):
		return f"{self.base_url}/{self.max_zoom}/{tile_x}_{tile_y}.{self.ext}"


def download_image(output_filename, metadata_url, url_maker):
	image_metadata = utils.get_xml(metadata_url)

	tile_size = int(image_metadata.attrib["TileSize"])
	overlap = int(image_metadata.attrib["Overlap"])

	size_metadata = utils.first(image_metadata)
	width = int(size_metadata.attrib["Width"])
	height = int(size_metadata.attrib["Height"])

	policy = utils.TileSewingPolicy.from_image_size(width, height, tile_size)
	policy.overlap = overlap
	utils.download_and_sew_tiles(output_filename, url_maker, policy)