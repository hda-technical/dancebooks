import json
import os
from xml.etree import ElementTree

import requests


#NOTE: if the website is protected by cloudflare, removing User-Agent header will help to pass it by
USER_AGENT = "User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64; rv:62.0) Gecko/20100101 Firefox/62.0"
HEADERS = {
	"User-Agent": USER_AGENT
}
TIMEOUT = 30


#using single session for all requests
session = requests.Session()


def retry(retry_count, delay=0, delay_backoff=1):
	def actual_decorator(func):
		@functools.wraps(func)
		def do_retry(*args, **kwargs):
			retry_number = 0
			current_delay = delay
			try:
				return func(*args, **kwargs)
			except Exception:
				if retry_number >= retry_count:
					raise RuntimeError(f"Failed to get results after {retry_number} retries")
				else:
					time.sleep(current_delay)
					current_delay *= delay_backoff
					retry_number += 1
		return do_retry
	return actual_decorator


#@retry(retry_count=3)
def make_request(*args, **kwargs):
	"""
	Performs the request and returns requests.Response object.
	Accepts both raw urls and prepared requests
	"""
	if isinstance(args[0], str):
		url = args[0]
		response = requests.get(*args, headers=HEADERS, timeout=TIMEOUT, **kwargs)
	elif isinstance(args[0], requests.Request):
		request = args[0].prepare()
		url = request.url
		args = args[1:]
		request.headers = HEADERS
		response = session.send(request, *args, timeout=TIMEOUT, **kwargs)
	if response.status_code == 200:
		return response
	else:
		raise ValueError(f"While getting {url}: HTTP status 200 was expected. Got {response.status_code}")


#@retry(retry_count=3)
def get_json(*args, **kwargs):
	"""
	Returns parsed JSON object received via HTTP GET request
	"""
	return json.loads(make_request(*args, **kwargs).content)


def get_xml(*args, **kwargs):
	"""
	Returns parsed xml (as ElementTree) received via HTTP GET request
	"""
	return ElementTree.fromstring(make_request(*args, **kwargs).content)


def get_text(*args, **kwargs):
	return make_request(*args, **kwargs).content.decode("utf-8")


def get_binary(output_filename, url_or_request, *args, **kwargs):
	"""
	Writes binary data received via HTTP GET request to output_filename
	Accepts both url as string and request.Requests
	"""
	BLOCK_SIZE = 4096
	response = make_request(url_or_request, *args, stream=True, **kwargs)
	with open(output_filename, "wb") as file:
		for chunk in response.iter_content(BLOCK_SIZE):
			file.write(chunk)


def make_output_folder(downloader, book_id):
	clean_book_id = book_id\
		.replace('/', '_')\
		.replace(':', '_')
	folder_name = f"{downloader}_{clean_book_id}"
	os.makedirs(folder_name, exist_ok=True)
	return folder_name


def make_output_filename(base, page=None, extension="bmp"):
	result = base
	if isinstance(page, int):
		result = os.path.join(result, f"{page:08}")
	elif page is not None:
		result = os.path.join(result, page)
	if extension is not None:
		result += "." + extension
	return result


def make_temporary_folder():
	return str(uuid.uuid4())
	

class TileSewingPolicy:
	def __init__(self, tiles_number_x, tiles_number_y, tile_size, image_width=None, image_height=None, overlap=None):
		self.tiles_number_x = tiles_number_x
		self.tiles_number_y = tiles_number_y
		self.tile_size = tile_size
		self.image_width = image_width
		self.image_height = image_height
		self.overlap = overlap
		self.trim = False
		self.reverse_axis_y = False

	@staticmethod
	def from_image_size(width, height, tile_size):
		tiles_number_x = math.ceil(width / tile_size)
		tiles_number_y = math.ceil(height / tile_size)
		return TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size, image_width=width, image_height=height)


def sew_tiles_with_montage(folder, output_file, policy):
	"""
	Invokes montage tool from ImageMagick package to sew tiles together
	"""
	def format_magick_geometry(policy):
		geometry = ""
		if policy.tile_size is not None:
			geometry += f"{policy.tile_size}x{policy.tile_size}"
		if policy.overlap is not None:
			geometry += f"-{policy.overlap}-{policy.overlap}"
		if geometry:
			#WARN:
			#  Do not allow enlarging tiles.
			#  Certain libraries (i. e. Gallica) use variable tile size
			geometry += '>'
		return geometry

	def format_magick_tile(policy):
		return f"{policy.tiles_number_x}x{policy.tiles_number_y}"

	# Sewing tiles
	cmd_line = [
		"montage",
		f"{folder}/*",
		"-mode", "Concatenate"
	]
	geometry = format_magick_geometry(policy)
	if geometry:
		cmd_line += ["-geometry", geometry]
	cmd_line += [
		"-tile", format_magick_tile(policy),
		output_file
	]
	print(f"Sewing tiles with:\n    {' '.join(cmd_line)}")
	subprocess.check_call(cmd_line)

	if policy.image_width and policy.image_height:
		# Cropping extra boundaries (right and bottom) added during sewing
		cmd_line = [
			"convert",
			output_file,
			"-extent", f"{policy.image_width}x{policy.image_height}",
			output_file
		]
		print(f"Cropping output image with:\n    {' '.join(cmd_line)}")
		subprocess.check_call(cmd_line)
	elif policy.trim:
		# Trimming extra boundaries automatically
		cmd_line = [
			"convert",
			output_file,
			"-trim",
			output_file
		]
		print(f"Trimming output image with:\n    {' '.join(cmd_line)}")
		subprocess.check_call(cmd_line)


def download_and_sew_tiles(output_filename, url_maker, policy):
	if os.path.exists(output_filename):
		print(f"Skip downloading existing file {output_filename}")
	tmp_folder = make_temporary_folder()
	os.mkdir(tmp_folder)
	try:
		print(f"Downloading {policy.tiles_number_x}x{policy.tiles_number_y} tiled image to {output_filename}")
		for tile_x in range(policy.tiles_number_x):
			for tile_y in range(policy.tiles_number_y):
				if policy.reverse_axis_y:
					MAX_TILE_NUMBER_Y = 50
					tile_file = os.path.join(tmp_folder, f"{MAX_TILE_NUMBER_Y - tile_y:08d}_{tile_x:08d}.jpg")
				else:
					tile_file = os.path.join(tmp_folder, f"{tile_y:08d}_{tile_x:08d}.jpg")
				url = url_maker(tile_x, tile_y)
				get_binary(tile_file, url)
		sew_tiles_with_montage(tmp_folder, output_filename, policy)
	finally:
		if "KEEP_TEMP" not in os.environ:
			shutil.rmtree(tmp_folder)