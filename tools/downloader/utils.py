import functools
import hashlib
import json
import os
import io
import math
import shutil
import time
import urllib.parse
from xml.etree import ElementTree

import bs4
import PIL.Image
import requests


# FIXME:
#	If the website responds with 4xx errors, changing User-Agent might help.
#	In particularly, CloudFlare works well with curl.
#
# USER_AGENT = "curl/7.68.0"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
HEADERS = {
	"User-Agent": USER_AGENT
}
TIMEOUT = 30


#using single session for all requests
session = requests.Session()


def retry(try_count, delay=0, delay_backoff=1):
	def actual_decorator(func):
		@functools.wraps(func)
		def do_retry(*args, **kwargs):
			retry_number = 0
			current_delay = delay
			for try_number in range(try_count):
				try:
					return func(*args, **kwargs)
				except Exception as ex:
					# 4xx responses (i. e. the HTTP 404 marking the end of the book)
					# won't get any better upon retrying.
					# Reraise HTTPError as is, letting the caller handle it
					if (
						isinstance(ex, requests.exceptions.HTTPError)
						and ex.response is not None
						and 400 <= ex.response.status_code < 500
					):
						raise
					print(f"Got exception: {ex}, will retry in {current_delay} seconds")
					time.sleep(current_delay)
					current_delay *= delay_backoff
			raise RuntimeError(f"Failed to get results after {try_number} retries")
		return do_retry
	return actual_decorator


# Anubis (https://anubis.techaro.lol) protects the website by replying
# with HTTP 200 and a proof-of-work challenge page instead of the requested content.
# Solving the challenge yields an authorization cookie valid for several hours,
# hence a single challenge is solved per session.
ANUBIS_PASS_CHALLENGE_PATH = "/.within.website/x/cmd/anubis/api/pass-challenge"


def _get_anubis_json(soup: bs4.BeautifulSoup, element_id: str):
	"""
	Anubis embeds challenge parameters into <script type="application/json"> tags
	"""
	script = soup.find("script", attrs={"id": element_id})
	if script is None:
		return None
	return json.loads(script.text)


def is_anubis_challenge(response: requests.Response) -> bool:
	# short-circuiting keeps us from fetching the body of a (possibly streamed) binary response
	return (
		response.headers.get("Content-Type", "").startswith("text/html")
		and b"anubis_challenge" in response.content
	)


def solve_anubis_challenge(response: requests.Response):
	"""
	Solves the proof-of-work challenge found in the response
	and stores the resulting authorization cookie in the session.
	"""
	soup = bs4.BeautifulSoup(response.text, features="html.parser")
	challenge = _get_anubis_json(soup, "anubis_challenge")
	if challenge is None:
		raise RuntimeError("Failed to extract Anubis challenge from the response")
	base_prefix = _get_anubis_json(soup, "anubis_base_prefix") or ""

	algorithm = challenge["rules"]["algorithm"]
	if algorithm not in ("fast", "slow"):
		raise NotImplementedError(f"Unsupported Anubis algorithm: {algorithm}")

	# Anubis asks for a nonce making sha256(random_data + nonce)
	# start with `difficulty` zero hex digits
	random_data = challenge["challenge"]["randomData"]
	difficulty = challenge["rules"]["difficulty"]
	expected_prefix = "0" * difficulty
	print(f"Solving Anubis challenge (difficulty {difficulty})")
	start_time = time.monotonic()
	nonce = 0
	while True:
		digest = hashlib.sha256(f"{random_data}{nonce}".encode()).hexdigest()
		if digest.startswith(expected_prefix):
			break
		nonce += 1
	elapsed_ms = int((time.monotonic() - start_time) * 1000)
	print(f"Solved Anubis challenge in {nonce + 1} hashes ({elapsed_ms} ms)")

	url = urllib.parse.urlsplit(response.url)
	query = urllib.parse.urlencode({
		"id": challenge["challenge"]["id"],
		"response": digest,
		"nonce": nonce,
		"redir": response.url,
		"elapsedTime": elapsed_ms,
	})
	pass_challenge_url = urllib.parse.urlunsplit((
		url.scheme,
		url.netloc,
		base_prefix + ANUBIS_PASS_CHALLENGE_PATH,
		query,
		"",
	))
	# not following the redirect to response.url: the caller reissues the request anyway
	pass_response = session.get(
		pass_challenge_url,
		headers=HEADERS,
		timeout=TIMEOUT,
		allow_redirects=False,
	)
	pass_response.raise_for_status()


# FIXME: retry decorator hides HTTPError raised by raise_for_status.
# @retry(try_count=3)
def make_request(rq: str | requests.Request, *args, **kwargs):
	"""
	Performs the request and returns requests.Response object.
	Accepts both raw urls and prepared requests
	"""
	headers = HEADERS | kwargs.pop("headers", {})
	method = kwargs.pop("method", "GET")
	if isinstance(rq, str):
		print(f"{method} {rq}")
		rq = requests.Request(
			url=rq,
			method=method,
			headers=headers,
		)
	elif isinstance(rq, requests.Request):
		rq.headers = headers
	# session.prepare_request (unlike requests.Request.prepare)
	# applies cookies stored in the session
	response = session.send(session.prepare_request(rq), *args, timeout=TIMEOUT, **kwargs)
	if is_anubis_challenge(response):
		solve_anubis_challenge(response)
		response = session.send(session.prepare_request(rq), *args, timeout=TIMEOUT, **kwargs)
		if is_anubis_challenge(response):
			raise RuntimeError("Failed to pass Anubis challenge")
	response.raise_for_status()
	return response


#@retry(try_count=3)
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


@retry(try_count=5, delay=30, delay_backoff=1.5)
def get_binary(output_filename, url_or_request, *args, **kwargs):
	"""
	Writes binary data received via HTTP GET request to output_filename
	Accepts both url as string and request.Requests.

	Returns size of the data that was downloaded.
	"""
	total_size = 0
	BLOCK_SIZE = 4096
	response = make_request(url_or_request, *args, stream=True, **kwargs)
	with open(output_filename, "wb") as file:
		for chunk in response.iter_content(BLOCK_SIZE):
			total_size += len(chunk)
			file.write(chunk)
	return total_size


@retry(try_count=5, delay=30, delay_backoff=1.5)
def get_image(url_or_request, *args, **kwargs):
	response = make_request(url_or_request, *args, stream=True, **kwargs)
	return PIL.Image.open(io.BytesIO(response.content))


def cleanup_filename(bad_name: int | str):
	return str(bad_name)\
		.replace('/', '_')\
		.replace(':', '_')\
		.replace('\\', '_')\


def make_output_folder(downloader, book_id: int | str):
	clean_book_id = cleanup_filename(book_id)
	folder_name = f"{downloader}_{clean_book_id}"
	os.makedirs(folder_name, exist_ok=True)
	return folder_name


def make_output_filename(base, page=None, extension="bmp"):
	result = base
	if isinstance(page, int):
		result = os.path.join(result, f"{page:04d}")
	elif page is not None:
		result = os.path.join(result, page)
	if extension is not None:
		result += "." + extension
	return result


class TileSewingPolicy:
	def __init__(self, tiles_number_x, tiles_number_y, tile_size, image_width=None, image_height=None, overlap=None):
		self.tiles_number_x = tiles_number_x
		self.tiles_number_y = tiles_number_y
		self.tile_size = tile_size
		self.image_width = image_width or self.tiles_number_x * self.tile_size
		self.image_height = image_height or self.tiles_number_y * self.tile_size
		self.overlap = overlap
		self.trim = False
		self.reverse_axis_y = False

	@staticmethod
	def from_image_size(width, height, tile_size):
		tiles_number_x = math.ceil(width / tile_size)
		tiles_number_y = math.ceil(height / tile_size)
		return TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size, image_width=width, image_height=height)


def download_and_sew_tiles(output_filename, url_maker, policy):
	if policy.overlap is not None:
		raise NotImplementedError("TODO: support overlap in this code")
	if policy.reverse_axis_y:
		raise NotImplementedError("TODO: support reverse_axis_y in this code")

	result = PIL.Image.new("RGB", (policy.image_width, policy.image_height))
	print(f"Downloading {policy.tiles_number_x}x{policy.tiles_number_y} tiled image ({policy.image_width}x{policy.image_height}) to {output_filename}")
	for tile_x in range(policy.tiles_number_x):
		for tile_y in range(policy.tiles_number_y):
			url = url_maker(tile_x, tile_y)
			tile_image = get_image(url)
			result.paste(tile_image, (tile_x * policy.tile_size, tile_y * policy.tile_size))

	if policy.trim:
		result = result.crop(result.getbbox())

	result.save(output_filename, "BMP")


def first(iterable):
	return next(iter(iterable))


# These methods try to guess tiles number using HEAD requests with given UrlMaker
#
# url_maker_maker should be a callable accepting zoom in the arguments.
# It should return UrlMaker
#
# url_maker should be a callable accepting (x, y) in the arguments.
# It should return None when corresponding tile does not exist.
#
# FIXME:
#	one can save some requests using bisection here,
#	but python standard library is too poor to have one.

def guess_tiles_zoom(url_maker_maker):
	MAX_ZOOM = 10

	zoom = 0
	for test_zoom in range(MAX_ZOOM):
		probable_url = url_maker_maker(test_zoom)(0, 0)
		head_response = session.head(probable_url, headers=HEADERS)
		if head_response.status_code != 200:
			break
		zoom = test_zoom
	return zoom


def guess_tiles_number_x(url_maker, min_file_size=None):
	MAX_TILE_NUMBER_X = 100

	tiles_number_x = 0
	for test_x in range(MAX_TILE_NUMBER_X):
		probable_url = url_maker(test_x, 0)
		if probable_url is None:
			break
		head_response = session.head(probable_url, headers=HEADERS)
		if head_response.status_code != 200:
			break
		if min_file_size is not None:
			content_length = int(head_response.headers["Content-Length"])
			if content_length < min_file_size:
				break
		tiles_number_x = (test_x + 1)
	return tiles_number_x


def guess_tiles_number_y(url_maker, min_file_size=None):
	MAX_TILE_NUMBER_Y = 100

	tiles_number_y = 0
	for test_y in range(MAX_TILE_NUMBER_Y):
		probable_url = url_maker(0, test_y)
		if probable_url is None:
			break
		head_response = session.head(probable_url, headers=HEADERS)
		if head_response.status_code != 200:
			break
		if min_file_size is not None:
			content_length = int(head_response.headers["Content-Length"])
			if content_length < min_file_size:
				break
		tiles_number_y = (test_y + 1)
	return tiles_number_y


def notify_skip(page):
	print(f"Skip downloading existing page {page:04d}")
