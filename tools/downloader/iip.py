import os
import requests

import utils


class Metadata:
	def __init__(self, tile_size, width, height, max_level):
		self.tile_size = tile_size
		self.width = width
		self.height = height
		self.max_level = max_level

	@staticmethod
	def from_json(data):
		tile_size = 256
		width = int(data["d"][-1]["w"])
		height = int(data["d"][-1]["h"])
		max_level = data["m"]
		return Metadata(tile_size, width, height, max_level)

	@staticmethod
	def from_text(text):
		"""
		Parses the following text:
		```
		Max-size:3590 3507
		Tile-size:256 256
		Resolution-number:5
		```
		"""
		tile_size = None
		width = None
		height = None
		max_level = None
		for line in text.split('\n'):
			parts = line.split(':')
			if parts[0] == "Max-size":
				(width, height) = map(int, parts[1].split())
			elif parts[0] == "Tile-size":
				tile_size = int(parts[1].split()[0])
			elif parts[0] == "Resolution-number":
				max_level = int(parts[1]) - 1
			else:
				pass
		return Metadata(tile_size, width, height, max_level)


def download_image(fastcgi_url, remote_filename, metadata, output_filename):
	policy = utils.TileSewingPolicy.from_image_size(metadata.width, metadata.height, metadata.tile_size)
	utils.download_and_sew_tiles(
		output_filename,
		lambda tile_x, tile_y: requests.Request(
			"GET",
			fastcgi_url,
			# WARN: passing parameters as string in order to send them in urldecoded form
			# (iip does not support urlencoded parameters)
			params=f"FIF={remote_filename}&JTL={metadata.max_level},{tile_y * policy.tiles_number_x + tile_x}",
		),
		policy
	)


def download_book(metadata_url, fastcgi_url, output_folder, files_root):
	"""
	Downloads book served by IIPImage fastcgi servant.
	API is documented here:
	http://iipimage.sourceforge.net/documentation/protocol/
	"""
	metadata = utils.get_json(metadata_url)["pgs"]
	print(f"Going to download {len(metadata)} pages")
	for page_number, page_metadata in enumerate(metadata):
		iip_page_metadata = Metadata.from_json(page_metadata)
		remote_filename = os.path.join(files_root, page_metadata["f"])
		output_filename = utils.make_output_filename(output_folder, page_number)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing page #{page_number:04d}")
			continue
		else:
			print(f"Downloading page #{page_number:04d}")
			download_image(fastcgi_url, remote_filename, iip_page_metadata, output_filename)
