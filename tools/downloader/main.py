#!/usr/bin/env python3

import http.client
import os
import subprocess
import sys
from xml.etree import ElementTree

import bs4
import click
import requests

from utils import *  # TODO: fix imports
import deep_zoom
import iiif
import iip


@click.group()
def main():
	pass


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `btv1b7200356s`)", required=True)
@click.option("--page", help="Zero based page number to be downloaded", required=False, default=0)
def gallica(id, page):
	"""
	Downloads book from https://gallica.bnf.fr/
	"""
	import bnf
	if page:
		bnf.get_gallica_page(id, page)
	else:
		bnf.get_gallica_book(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `can_097`)", required=True)
def candide(id):
	"""
	Downloads book from http://classes.bnf.fr/candide/
	"""
	import bnf
	bnf.get_candide(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `A0524435`)", required=True)
@click.option("--volume", help="Volume of the book to be downloaded (e. g. '1')", required=True)
def belgiumRoyalLibrary(id, volume):
	"""
	Downloads a book from https://www.kbr.be
	"""
	class UrlMaker:
		def __init__(self, zoom, page_root_url):
			self.zoom = zoom
			self.page_root_url = page_root_url

		def __call__(self, tile_x, tile_y):
			probable_url = f"{page_root_url}/{self.zoom}-{tile_x}-{tile_y}.jpg"
			return probable_url


	volume = int(volume)
	assert(id[0].isalpha())
	assert(id[1:].isdigit())
	slash_separated_id = '/'.join(id)
	dash_deparated_id = id[0] + '-' + id[1:]
	base_url = f"https://viewerd.kbr.be/display/{slash_separated_id}/0000-00-00_{volume:02d}/zoomtiles/BE-KBR00_{dash_deparated_id}_0000-00-00_{volume:02d}"

	# We have to provide referer with each request being dispatched.
	# This is easiest, though very dirty way to do it.
	referer = f"https://viewerd.kbr.be/gallery.php?map={slash_separated_id}/0000-00-00_{volume:02d}/"
	HEADERS["Referer"] = referer

	output_folder = make_output_folder("belgiumRoyalLibrary", f"{id}_{volume:02d}")
	page = 1

	TILE_SIZE = 768
	while True:
		output_filename = make_output_filename(output_folder, page)
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page:04d}")
			page += 1
			continue

		page_root_url = f"{base_url}_{page:04d}"
		url_maker_maker = lambda zoom: UrlMaker(zoom, page_root_url)
		tiles_zoom = guess_tiles_zoom(url_maker_maker)
		print(f"Guessed tiles_zoom={tiles_zoom}")
		url_maker = UrlMaker(tiles_zoom, page_root_url)

		tiles_number_x = guess_tiles_number_x(url_maker)
		print(f"Guessed tiles_number_x={tiles_number_x}")
		tiles_number_y = guess_tiles_number_y(url_maker)
		print(f"Guessed tiles_number_y={tiles_number_y}")
		if (tiles_number_x == 0) or (tiles_number_y == 0):
			print(f"Page {page:04d} was not found")
			break
		policy = TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
		policy.trim = True
		download_and_sew_tiles(output_filename, url_maker, policy)
		page += 1


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `bsb10029940`)", required=True)
def bsb(id):
	"""
	Downloads book from https://www.digitale-sammlungen.de
	"""
	import bsb
	bsb.get_book(id)


@main.command()
@click.option("--first", type=int, help="First page to be downloaded (e. g. '1910311')", required=True)
@click.option("--last", type=int, help="First page to be downloaded (e. g. '1911077')", required=True)
def uniDuesseldorf(first, last):
	"""
	Downloads set of images from http://digital.ub.uni-duesseldorf.de
	"""
	# Automatic definition of max zoom level is hard,
	# since backend does not return error status even if the request if wrong
	ZOOM = 6

	# Instead of returning an error, backend will send blank image.
	# In order to detect proper time for stopping the iteration,
	# we will check if tile size is greater than this number of bytes
	MIN_FILE_SIZE = 5120
	TILE_SIZE = 512

	class UrlMaker:
		def __init__(self, page):
			self.page = page

		def __call__(self, tile_x, tile_y):
			# Some unknown number with unspecified purpose.
			# It can change from item to item if looked in web browser console,
			# yet looks like it does not have any effect of the resulting image.
			UNKNOWN_NUMBER = 1862
			return f"http://digital.ub.uni-duesseldorf.de/image/tile/wc/nop/{UNKNOWN_NUMBER}/1.0.0/{page}/{ZOOM}/{tile_x}/{tile_y}.jpg"


	for page in range(first, last + 1):
		output_filename = make_output_filename(base="", page=page)
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page {page}")
			continue
		url_maker = UrlMaker(page)

		tiles_number_x = guess_tiles_number_x(url_maker, min_file_size=5120)
		print(f"Guessed tiles_number_x={tiles_number_x}")
		tiles_number_y = guess_tiles_number_y(url_maker, min_file_size=5120)
		print(f"Guessed tiles_number_y={tiles_number_y}")
		policy = TileSewingPolicy(tiles_number_x, tiles_number_y, TILE_SIZE)
		policy.trim = True
		policy.reverse_axis_y = True
		download_and_sew_tiles(output_filename, url_maker, policy)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. 'PPN722203519')", required=True)
def uniGoettingen(id):
	"""
	Downloads book from https://gdz.sub.uni-goettingen.de
	"""
	manifest_url = f"https://manifests.sub.uni-goettingen.de/iiif/presentation/{id}/manifest"
	output_folder = make_output_folder("goettingen", id)
	iiif.download_book(manifest_url, output_folder)


@main.command()
@click.option("--volume", type=int, help="Volume to be downloaded (e. g. '24')", required=True)
@click.option("--page", type=int, help="Page number to be downloaded (e. g. '247')", required=True)
def encyclopedie(volume, page):
	"""
	Downloads single image from http://enccre.academie-sciences.fr/encyclopedie
	"""
	#there is no manifest.json file, slightly modified IIIF protocol is being used by the website
	image_list_url = f"http://enccre.academie-sciences.fr/icefront/api/volume/{volume}/imglist"
	image_list_metadata = get_json(image_list_url)
	image_metadata = image_list_metadata[page]
	image_url = f"http://enccre.academie-sciences.fr/digilib/Scaler/IIIF/{image_metadata['image']}"
	output_file = f"{page:04d}.bmp"
	iiif.download_image(image_url, output_file)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. 'MSS_Cappon.203')", required=True)
def vatlib(id):
	"""
	Downloads book from http://digi.vatlib.it/
	"""
	manifest_url = f"http://digi.vatlib.it/iiif/{id}/manifest.json"
	output_folder = make_output_folder("vatlib", id)
	iiif.download_book(manifest_url, output_folder)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. 'PPN880809493')", required=True)
def mecklenburgVorpommern(id):
	"""
	Downloads book from http://www.digitale-bibliothek-mv.de
	"""
	# it looks like Mecklenburg-Vorpommern does not use manifest.json
	output_folder = make_output_folder("mecklenburg_vorpommern", id)
	for page in range(1, 1000):
		output_filename = make_output_filename(output_folder, page)
		if os.path.isfile(output_filename):
			print(f"Skipping existing page {page}")
			continue
		try:
			base_url = f"http://www.digitale-bibliothek-mv.de/viewer/rest/image/{id}/{page:08d}.tif"
			iiif.download_image(base_url, output_filename)
		except ValueError:
			break



@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `335368`)", required=True)
@click.option("--page", help="Download specified (zero-based) page only", required=False, type=int, default=None)
def prlib(id, page):
	"""
	Download a book from https://www.prlib.ru/
	"""
	import prlib
	prlib.get(id, page)


@main.command()
@click.option("--id", help="Image id to be downloaded (e. g. `49035`)", required=True)
def nga(id):
	"""
	Downloads single image from https://www.nga.gov
	"""
	slashed_image_id = "/".join(id) #will produce "4/9/0/3/5" from "49035-primary-0-nativeres"
	remote_filename = f"/public/objects/{slashed_image_id}/{id}-primary-0-nativeres.ptif"
	fastcgi_url="https://media.nga.gov/fastcgi/iipsrv.fcgi"
	metadata = IIPMetadata.from_text(
		get_text(f"{fastcgi_url}?FIF={remote_filename}&obj=Max-size&obj=Tile-size&obj=Resolution-number")
	)
	iip.download_image(
		fastcgi_url=fastcgi_url,
		remote_filename=remote_filename,
		metadata=metadata,
		output_filename=f"nga.{id}.bmp"
	)


@main.command()
@click.option("--id", help="Image id to be downloaded (e. g. `grafik/uh-4f-47-00192`)", required=True)
def habImage(id):
	"""
	Downloads single image from http://diglib.hab.de and http://kk.haum-bs.de
	(both redirect to Virtuelles Kupferstichkabinett website, which is too hard to be typed)
	"""
	import hab
	hab.get_image(id)


@main.command()
@click.option("--id", help="Book id to be downloaded (e. g. `mss/120-1-extrav`)", required=True)
def habBook(id):
	"""
	Downloads book from http://diglib.hab.de
	"""
	import hab
	hab.get_book(id)


@main.command()
@click.option("--id", help="Book id to be downloaded (e. g. `Mus-Ms-1827`)", required=True)
def darmstadt(id):
	"""
	Downloads book from http://tudigit.ulb.tu-darmstadt.de
	"""
	import darmstadt
	darmstadt.get(id)


@main.command()
@click.option("--id", help="Image id to be downloaded (e. g. `lwlpr11386`)", required=True)
def yaleImage(id):
	"""
	Downloads image from http://images.library.yale.edu/
	"""
	class UrlMaker:
		"""
		Similar to UrlMaker from hab() method. Should be deduplicated once
		"""
		def __init__(self, zoom):
			self.zoom = zoom

		def __call__(self, tile_x, tile_y):
			for tile_group in [0, 1, 2]:
				probable_url = f"http://images.library.yale.edu/walpoleimages/dl/011000/{id}/TileGroup{tile_group}/{self.zoom}-{tile_x}-{tile_y}.jpg"
				head_response = requests.head(probable_url)
				if head_response.status_code == 200:
					return probable_url
			return None
	MAX_ZOOM = 5
	#FIXME: replace 011000 with computed expression
	metadata = ElementTree.fromstring(get_text(f"http://images.library.yale.edu/walpoleimages/dl/011000/{id}/ImageProperties.xml"))
	width = int(metadata.attrib["WIDTH"])
	height = int(metadata.attrib["HEIGHT"])
	tile_size = int(metadata.attrib["TILESIZE"])
	policy = TileSewingPolicy.from_image_size(width, height, tile_size)

	output_filename = make_output_filename(id)
	download_and_sew_tiles(output_filename, UrlMaker(MAX_ZOOM), policy)


@main.command()
@click.option("--id", help="Image id to be downloaded (e. g. `1327507`)", required=True)
@click.option("--chapter", help="Chapter to download from (e. g. `PATREQIMGX12`)", required=True)
def yaleBook(id, chapter):
	"""
	Downloads image from https://brbl-zoom.library.yale.edu
	"""

	output_filename = make_output_filename("", id)
	remote_filename = f"{chapter}/{id[-1]}/{id}/{id}.jp2"
	fastcgi_url = "https://brbl-zoom.library.yale.edu/fcgi-bin/iipsrv.fcgi"
	metadata_url = f"{fastcgi_url}?FIF={remote_filename}&obj=Max-size&obj=Tile-size&obj=Resolution-number"
	metadata = IIPMetadata.from_text(get_text(metadata_url))
	iip.download_image(fastcgi_url, remote_filename, metadata, output_filename)


@main.command()
@click.option("--id", help="Book id to be downloaded (e. g. `vdc_100026052453`, as it is displayed in the viewer url)", required=True)
def bl_book(id):
	"""
	Downloads a book from http://explore.bl.uk
	"""
	import bl
	bl.get_book(id)


@main.command()
@click.option("--id", help="Page id of the manuscript to be downloaded (e. g. `add_ms_12531!1_f005r`)", required=True)
def bl_manuscript(id):
	"""
	Downloads single manuscript page from http://www.bl.uk/manuscripts/Default.aspx
	"""
	import bl
	bl.get_manuscript(id)


@main.command()
@click.option("--id", help="Image id of the painting to be downloaded(e. g. `js-108-jan_steen-the_fair_at_warmond_files`)", required=True)
def leidenCollection(id):
	"""
	Downloads single image from https://www.theleidencollection.com
	"""
	MAX_ZOOM = 13

	class UrlMaker:
		def __call__(self, tile_x, tile_y):
			return f"https://www.theleidencollection.com/LeidenCollectionSamples/images/{id}_files/{MAX_ZOOM}/{tile_x}_{tile_y}.jpg"

	url_maker = UrlMaker()
	tiles_number_x = guess_tiles_number_x(url_maker)
	print(f"Guessed tiles_number_x={tiles_number_x}")
	tiles_number_y = guess_tiles_number_y(url_maker)
	print(f"Guessed tiles_number_y={tiles_number_y}")
	policy = TileSewingPolicy(tiles_number_x, tiles_number_y, tile_size=None, overlap=None)

	output_filename = make_output_filename("", id)
	download_and_sew_tiles(output_filename, url_maker, policy)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `4_cgntCY2Bj2ZpaKCjjXrWcNSEjlsU_Mk6ZUJByJ4smfJUNCpbPL_8dPavSb0DwGNavju8-nAYNsFUXP1jmb1KuGO2_RIzJoMfr8QvK5JTc/thf97207`", required=True)
def henryFord(id):
	"""
	Downloads single image from https://www.thehenryford.org/
	"""
	metadata_url = f"https://www.thehenryford.org/linkedpub-image/{id}.dzi"
	basename = os.path.basename(id)

	MAX_ZOOM = 12
	base_url = f"https://www.thehenryford.org/linkedpub-image/{id}_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM, ext="jpeg")
	output_filename = f"henryFord_{basename}.bmp"
	deep_zoom.download_image(output_filename, metadata_url, url_maker)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `ki-6952-1_1`)", required=True)
def makAt(id):
	"""
	Downloads single image from https://sammlung.mak.at/
	"""
	metadata_url = f"https://sammlung.mak.at/img/zoomimages/publikationsbilder/{id}.xml"

	output_filename = make_output_filename('.', id)

	MAX_ZOOM = 11
	base_url = f"https://sammlung.mak.at/img/zoomimages/publikationsbilder/{id}_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM)

	deep_zoom.download_image(output_filename, metadata_url, url_maker)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `mw61074`)", required=True)
def npg(id):
	"""
	Downloads single image from https://www.npg.org.uk
	"""
	import npg
	npg.get(id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded, including document id (e. g. `00108217/JLM_1787_H002_0003_a`)", required=True)
def uniJena(id):
	"""
	Downloads single image from https://zs.thulb.uni-jena.de

	Requires a lot of work though
	"""
	class UrlMaker:
		def __init__(self, zoom):
			self.zoom = zoom

		def __call__(self, tile_x, tile_y):
			return f"https://zs.thulb.uni-jena.de/servlets/MCRTileServlet/jportal_derivate_{id}.tif/{self.zoom}/{tile_y}/{tile_x}.jpg"

	metadata_url = f"https://zs.thulb.uni-jena.de/servlets/MCRTileServlet/jportal_derivate_{id}.tif/imageinfo.xml"
	metadata = get_xml(metadata_url)

	output_filename = make_output_filename("", os.path.basename(id))

	width = int(metadata.attrib["width"])
	height = int(metadata.attrib["height"])
	zoom = int(metadata.attrib["zoomLevel"])

	TILE_SIZE = 256
	policy = TileSewingPolicy.from_image_size(width, height, TILE_SIZE)

	url_maker = UrlMaker(zoom)
	download_and_sew_tiles(output_filename, url_maker, policy)

	subprocess.check_call([
		"convert",
		output_filename,
		"-crop", f"{width}x{height}+0+0",
		output_filename
	])


###################
#PAGE BASED DOWNLOADERS
###################


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `056`)", required=True)
@click.option("--start", type=int, default=1, help="The number of the first page in the sequence")
def locMusdi(id, start):
	"""
	Downloads book from Library of Congress Music/Dance instruction
	"""
	# Some ids are known to be missing
	MISSING_IDS = [
		"050", "054", "057", "061", "071",
		"078", "083", "095", "100", "103",
		"106", "111", "116", "120", "135",
		"152", "172", "173", "175", "176",
		"180", "185", "192", "193", "196",
		"206", "223", "231", "232", "234",
		"238", "244", "249",
	]
	MAX_ID = 252
	if len(id) != 3:
		print("Expected id to have 3 digits. Please, recheck the ID.")
		sys.exit(1)
	if id in MISSING_IDS:
		print(f"The book with id musdi.{id} is known to be missing. Please, recheck the ID.")
		sys.exit(1)
	if int(id) > MAX_ID:
		print(f"The maximum id is musdi.{MAX_ID}. Please, recheck the ID.")
		sys.exit(1)
	output_folder = make_output_folder("locMusdi", id)
	for page in range(start, 1000):
		base_url = f"https://memory.loc.gov/music/musdi/{id}/{page:04d}"
		url = None
		for extension in ["tif", "jpg"]:
			output_filename = make_output_filename(output_folder, page, extension=extension)
			if os.path.exists(output_filename):
				break
			maybe_url = base_url + "." + extension
			head_response = requests.head(maybe_url)
			if head_response.status_code == http.client.OK:
				url = maybe_url
				break
		if url is None:
			break
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Downloading page #{page:08d}")
		get_binary(output_filename, url)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `wu.89005529961`)", required=True)
@click.option("--from", "from_page", help="First page to be downloaded", type=int, default=None)
@click.option("--to", "to_page", help="Last page to be downloaded", type=int, default=None)
def hathitrust(id, from_page, to_page):
	"""
	Downloads book from the HathiTrust Digital Library (https://www.hathitrust.org/)
	"""
	import hathitrust
	hathitrust.get(id=id, from_page=from_page, to_page=to_page)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `Teca:20:NT0000:RMLE032585`)", required=True)
def internet_culturale(id):
	"""
	Downloads book from Internet Culturale, Biblioteca Digitale Italiana (http://www.internetculturale.it/)
	"""
	import internet_culturale
	internet_culturale.get(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `Wilson1808`)", required=True)
def	vwml(id):
	"""
	Downloads book from https://www.vwml.org/topics/historic-dance-and-tune-books
	"""
	main_url = f"https://www.vwml.org/topics/historic-dance-and-tune-books/{id}"
	main_markup = get_text(main_url)
	soup = bs4.BeautifulSoup(main_markup, "html.parser")
	output_folder = make_output_folder("vwml", id)
	for page, thumbnail in enumerate(soup.find_all("img", attrs={"class": "image_thumb"})):
		thumbnail_url = thumbnail.attrs["src"]
		#IT'S MAGIC!
		full_url = thumbnail_url.replace("thumbnails", "web")
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		print(f"Saving {full_url} to {output_filename}")
		try:
			get_binary(output_filename, full_url, verify=False)
		except ValueError:
			#VWML is known to have missing pages listed in this table.
			#Ignoring such pages
			pass


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `ABO_+Z178189508`)", required=True)
def onb(id):
	"""
	Downloads book from http://onb.ac.at/
	"""
	import onb
	onb.get(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `PPN670016500`)", required=True)
def staats_berlin(id):
	"""
	Downloads book from http://digital.staatsbibliothek-berlin.de/
	"""
	output_folder = make_output_folder("staats_berlin", id)
	page = 1
	while True:
		output_filename = make_output_filename(output_folder, page, extension="tif")
		if os.path.isfile(output_filename):
			print(f"Skipping existing page {page}")
		else:
			try:
				image_url = f"https://content.staatsbibliothek-berlin.de/dms/{id}/800/0/{page:08d}.tif?original=true"
				#WARN:
				#	it looks like there is no normal way
				#	to get the number of pages in the book via http request
				get_binary(output_filename, image_url)
			except ValueError:
				print(f"No more images left. Last page was {page - 1:04d}")
				break
		page += 1


@main.command()
@click.option("--id", help="UUID of the book to be downloaded (e. g. `c96b8876-b4f8-48a5-8221-3949392b1a5c`)", required=True)
def difmoe(id):
	"""
	Downloads book from https://www.difmoe.eu/
	"""
	import difmoe
	difmoe.get(id)


@main.command()
@click.option("--id", help="Base64-encoded id of the book to be downloaded (e. g. `Nzg4NDk0MzY`, can be found in permalink)", required=True)
def polona(id):
	"""
	Downloads book from https://polona.pl
	"""
	entity_url = f"https://polona.pl/api/entities/{id}"
	entity_metadata = get_json(entity_url)
	output_folder = make_output_folder("polona", id)
	for page, page_metadata in enumerate(entity_metadata["scans"]):
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			continue
		found = False
		for image_metadata in page_metadata["resources"]:
			if image_metadata["mime"] == "image/jpeg":
				get_binary(output_filename, image_metadata["url"])
				found = True
		if not found:
			raise Exception(f"JPEG file was not found in image_metadata for page {page}")


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `1286758696_1822000000/EPN_798582804`)", required=True)
def haab(id):
	"""
	Downloads book from https://haab-digital.klassik-stiftung.de/
	"""
	def make_url(page):
		return f"https://haab-digital.klassik-stiftung.de/viewer/rest/image/{id}_{page:04d}.tif/full/full/0/default.jpg"
	output_folder = make_output_folder("haab", id)
	page = 0
	# HAAB server returns 403 for non-existing pages. First,
	while True:
		page_url = make_url(page)
		head_response = requests.head(page_url)
		if head_response.status_code == 200:
			print(f"Found starting page {page:04d}")
			break
		page += 1

	exception_count = 0
	while True:
		page_url = make_url(page)
		output_filename = make_output_filename(output_folder, page, extension="jpg")
		if os.path.exists(output_filename):
			print(f"Skip downloading existing page #{page:08d}")
			page += 1
			continue
		try:
			print(f"Downloading page #{page:08d}")
			get_binary(output_filename, page_url)
			page += 1
		except ValueError as ex:
			page += 1
			#WARN:
			#	Certain pages can return 403 even in the middle of the book.
			# 	Skipping certain number of such pages.
			exception_count += 1
			if exception_count < 10:
				print(f"Got ValueError while getting page {page:08d}: {ex}")
				continue
			else:
				print(f"Got exception while getting page {page:08d}: {ex}. Exception limit was reached, downloader will exit now.")
				break


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `PPN446487767`)", required=True)
def fulda(id):
	"""
	Downloads book from https://fuldig.hs-fulda.de
	"""
	import fulda
	fulda.get(id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `PR-INC-00000-A-00007-00002-00888-000-00420`)", required=True)
def cambridge(id):
	"""
	Downloads image from https://images.lib.cam.ac.uk
	"""
	import cambridge
	cambridge.get(id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `1273e6f5-ee79-4f6b-9014-a9065a93b9ff`)", required=True)
def bodleian(id):
	"""
	Downloads image from https://digital.bodleian.ox.ac.uk
	"""
	import bodleian
	bodleian.get(id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `PPN1748520709`)", required=True)
def goettingen(id):
	"""
	Downloads book from https://gdz.sub.uni-goettingen.de
	"""
	import goettingen
	goettingen.get_book(id)
	
	
@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `172099`)", required=True)
def nb_no(id):
	"""
	Downloads book from https://www.nb.no
	"""
	import nb_no
	nb_no.get(id)
	

@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `object125610`)", required=True)
def kb_dk(id):
	"""
	Downloads book from http://www5.kb.dk
	"""
	import kb_dk
	kb_dk.get(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `63678`)", required=True)
def shpl(id):
	"""
	Downloads book from http://elib.shpl.ru
	"""
	import shpl
	shpl.get(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `122cdc10-0032-0130-6561-58d385a7bc34`)", required=True)
def nypl(id):
	"""
	Downloads image sequence from https://digitalcollections.nypl.org/
	"""
	import nypl
	nypl.get(id)


if __name__ == "__main__":
	main()
