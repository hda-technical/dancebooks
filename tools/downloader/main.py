#!/usr/bin/env python3

import http.client
import os
import subprocess
import sys
import traceback
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
	"""
	Downloads...
	"""
	pass



@main.command()
@click.option("--first", help="First page to be downloaded (e. g. `8076189`)", type=int, required=True)
@click.option("--last", help="Last page (inclusive) to be downloaded (e. g. `8076299`)", type=int, required=True)
def at_ubs(*, first, last):
	"""
	book from eplus.uni-salzburg.at
	"""
	import at
	at.get_ubs(first=first, last=last)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `btv1b7200356s`)", required=True)
@click.option("--page", help="Zero based page number to be downloaded", required=False, default=0)
def fr_gallica(id, page):
	"""
	book from gallica.bnf.fr
	"""
	import fr
	if page:
		fr.get_gallica_page(id, page)
	else:
		fr.get_gallica_book(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `can_097`)", required=True)
def fr_candide(id):
	"""
	book from classes.bnf.fr/candide
	"""
	import fr
	fr.get_candide(id)


@main.command()
@click.option("--id", help="Id of the books to be downloaded (e. g. `098461435`)", required=True)
def fr_tolosana(id):
	"""
	book from tolosana.univ-toulouse.fr
	"""
	import fr
	fr.get_tolosana(id=id)


@main.command()
@click.option("--document-id", help="Id of the paper to be downloaded (e. g. `4466/5537594`)", required=True)
@click.option("--page", type=int, help="Id of the page to be downloaded (e. g. `11`)", required=True)
def fr_retronews(document_id, page):
	"""
	single page from www.retronews.fr
	"""
	import fr
	fr.get_retronews(document_id=document_id, page=page)



@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `IE17209883`)", required=True)
def be_libis(id):
	"""
	book from repository.teneo.libis.be
	"""
	import be
	be.get_libis(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `A0524435`)", required=True)
@click.option("--volume", help="Volume of the book to be downloaded (e. g. `0`)", required=True, type=int, default=0)
def be_kbr(id, volume):
	"""
	book from www.kbr.be
	"""
	import be
	be.get_kbr(id, volume)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `fad2738c-c223-4a68-8044-c9fd73c8efd6`)", required=True)
def cz_kramerius(id):
	"""
	book from www.digitalniknihovna.cz
	"""
	import cz
	cz.get_kramerius(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `bsb10029940`)", required=True)
def de_bsb(id):
	"""
	book from www.digitale-sammlungen.de
	"""
	import de
	de.get_bsb(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `ppn1727545419`)", required=True)
def de_rosdok(id):
	"""
	book from rosdok.uni-rostock.de
	"""
	import de
	de.get_rosdok(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `1981185920/49609/13562386-aa42-4089-921f-069524552928` (find manifest request to get it))", required=True)
def de_unihalle(id):
	"""
	book from opendata.uni-halle.de
	"""
	import de
	de.get_unihalle(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `Teca:20:NT0000:RMLE032585`)", required=True)
def it_internet_culturale(id):
	"""
	book from www.internetculturale.it
	"""
	import it
	it.get_internet_culturale(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `418f9526-f9cf-422e-9a73-2064fb1ae820`)", required=True)
def it_rovereto(id):
	"""
	book from digitallibrary.bibliotecacivica.rovereto.tn.it
	"""
	import it
	it.get_rovereto(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `Teca:20:NT0000:N:MUS006101`)", required=True)
def it_sbn(id):
	"""
	book from sbn.it
	"""
	import it
	it.get_sbn(id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. 'MSS_Cappon.203')", required=True)
def it_vatlib(id):
	"""
	book from digi.vatlib.it
	"""
	import it
	it.get_valtib(id=id)


@main.command()
@click.option("--first", type=int, help="First page to be downloaded (e. g. '1910311')", required=True)
@click.option("--last", type=int, help="First page to be downloaded (e. g. '1911077')", required=True)
def uniDuesseldorf(first, last):
	"""
	set of images from digital.ub.uni-duesseldorf.de
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
	book from gdz.sub.uni-goettingen.de
	"""
	manifest_url = f"https://manifests.sub.uni-goettingen.de/iiif/presentation/{id}/manifest"
	output_folder = make_output_folder("goettingen", id)
	iiif.download_book(manifest_url, output_folder)


@main.command()
@click.option("--volume", type=int, help="Volume to be downloaded (e. g. '24')", required=True)
@click.option("--page", type=int, help="Page number to be downloaded (e. g. '247')", required=True)
def encyclopedie(volume, page):
	"""
	single image enccre.academie-sciences.fr/encyclopedie
	"""
	#there is no manifest.json file, slightly modified IIIF protocol is being used by the website
	image_list_url = f"http://enccre.academie-sciences.fr/icefront/api/volume/{volume}/imglist"
	image_list_metadata = get_json(image_list_url)
	image_metadata = image_list_metadata[page]
	image_url = f"http://enccre.academie-sciences.fr/digilib/Scaler/IIIF/{image_metadata['image']}"
	output_file = f"{page:04d}.bmp"
	iiif.download_image(image_url, output_file)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. 'PPN880809493')", required=True)
def de_mv(id):
	"""
	book from www.digitale-bibliothek-mv.de
	"""
	import de
	de.get_mv(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `335368`)", required=True)
@click.option("--page", help="Download specified (zero-based) page only", required=False, type=int, default=None)
def ru_prlib(id, page):
	"""
	book from www.prlib.ru
	"""
	import ru
	ru.get_prlib(id=id, page=page)


@main.command()
@click.option("--id", help="Image id to be downloaded (e. g. `49035`)", required=True)
def nga(id):
	"""
	single image from www.nga.gov
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
	single image from diglib.hab.de or kk.haum-bs.de
	"""
	import hab
	hab.get_image(id)


@main.command()
@click.option("--id", help="Book id to be downloaded (e. g. `mss/120-1-extrav`)", required=True)
def habBook(id):
	"""
	book from diglib.hab.de
	"""
	import hab
	hab.get_book(id)


@main.command()
@click.option("--id", help="Book id to be downloaded (e. g. `Mus-Ms-1827`)", required=True)
def darmstadt(id):
	"""
	book from tudigit.ulb.tu-darmstadt.de
	"""
	import darmstadt
	darmstadt.get(id)


@main.command()
@click.option("--id", help="Image id to be downloaded (e. g. `lwlpr11386`)", required=True)
def yaleImage(id):
	"""
	image from images.library.yale.edu
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
	image from brbl-zoom.library.yale.edu
	"""

	output_filename = make_output_filename("", id)
	remote_filename = f"{chapter}/{id[-1]}/{id}/{id}.jp2"
	fastcgi_url = "https://brbl-zoom.library.yale.edu/fcgi-bin/iipsrv.fcgi"
	metadata_url = f"{fastcgi_url}?FIF={remote_filename}&obj=Max-size&obj=Tile-size&obj=Resolution-number"
	metadata = IIPMetadata.from_text(get_text(metadata_url))
	iip.download_image(fastcgi_url, remote_filename, metadata, output_filename)


@main.command()
@click.option("--id", help="Book id to be downloaded (e. g. `vdc_100026052453`, as it is displayed in the viewer url)", required=True)
def uk_bl_book(id):
	"""
	book from explore.bl.uk
	"""
	import uk
	uk.get_bl_book(id=id)


@main.command()
@click.option("--id", help="Page id of the manuscript to be downloaded (e. g. `add_ms_12531!1_f005r`)", required=True)
def uk_bl_manuscript(id):
	"""
	single page from www.bl.uk/manuscripts
	"""
	import uk
	uk.get_bl_manuscript(id=id)


@main.command()
@click.option("--id", help="Image id of the painting to be downloaded(e. g. `js-108-jan_steen-the_fair_at_warmond_files`)", required=True)
def leidenCollection(id):
	"""
	single image from www.theleidencollection.com
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
	single image from www.thehenryford.org
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
	single image from sammlung.mak.at
	"""
	metadata_url = f"https://sammlung.mak.at/img/zoomimages/publikationsbilder/{id}.xml"

	output_filename = make_output_filename('.', id)

	MAX_ZOOM = 11
	base_url = f"https://sammlung.mak.at/img/zoomimages/publikationsbilder/{id}_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM)

	deep_zoom.download_image(output_filename, metadata_url, url_maker)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `mw61074`)", required=True)
def uk_npg(id):
	"""
	single image from www.npg.org.uk
	"""
	import uk
	uk.get_npg(id=id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded, including document id (e. g. `00108217/JLM_1787_H002_0003_a`)", required=True)
def uniJena(id):
	"""
	single image from zs.thulb.uni-jena.de
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
	book from www.loc.gov
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
def us_hathitrust(id, from_page, to_page):
	"""
	book from www.hathitrust.org
	"""
	import us
	us.get_hathitrust(id=id, from_page=from_page, to_page=to_page)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `Wilson1808`)", required=True)
def	vwml(id):
	"""
	book from www.vwml.org/topics/historic-dance-and-tune-books
	"""
	main_url = f"https://www.vwml.org/topics/historic-dance-and-tune-books/{id}"
	
	soup = bs4.BeautifulSoup(
		get_text(main_url),
		features="html.parser",
	)
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
def at_onb(id):
	"""
	book from onb.ac.at
	"""
	import at
	at.get_onb(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `PPN670016500`)", required=True)
def staats_berlin(id):
	"""
	book from digital.staatsbibliothek-berlin.de
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
	book from www.difmoe.eu
	"""
	import difmoe
	difmoe.get(id)


@main.command()
@click.option("--id", help="GUID of the book to be downloaded (e. g. `ad69332a-5a9e-4a5a-ad33-26362745fa25`)", required=True)
def pl_polona(id):
	"""
	book from polona.pl
	"""
	import pl
	pl.get_polona(id=id)


@main.command()
@click.option("--book-id", help="Id of the book to be downloaded (e. g. `93346204`)", required=True)
@click.option("--first-page-id", type=int, help="If of the first page to be downloaded (e. g. `93968359`)", required=True)
@click.option("--last-page-id", type=int, help="If of the first page to be downloaded (e. g. `93968555`)", required=True)
def pl_academica(*, book_id, first_page_id, last_page_id):
	import pl
	pl.get_academica(
		book_id=book_id,
		first_page_id=first_page_id,
		last_page_id=last_page_id,
	)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `1759078042`)", required=True)
def de_gwlb(*, id):
	"""
	book from digitale-sammlungen.gwlb.de

	(click on DFG-Viewer to get the id)
	"""
	import de
	de.get_gwlb(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `RollSyst_43333035X`)", required=True)
def de_slub(*, id):
	"""
	book from digital.slub-dresden.de
	(download single image to get the id)
	"""
	import de
	de.get_slub(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `6444409`)", required=True)
def de_karlsruhe(*, id):
	"""
	book from digital.blb-karlsruhe.de
	"""
	import de
	de.get_karlsruhe(id=id)

@main.command()
@click.option("--first-id", help="Id of the book to be downloaded (e. g. `86571696X`)", required=True)
@click.option("--second-id", help="Id of the book to be downloaded (e. g. `EPN_390287636`)", required=True)
def de_haab(*, first_id, second_id):
	"""
	book from haab-digital.klassik-stiftung.de
	"""
	import de
	de.get_haab(first_id=first_id, second_id=second_id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `PPN446487767`)", required=True)
def fulda(id):
	"""
	book from fuldig.hs-fulda.de
	"""
	import fulda
	fulda.get(id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `PR-INC-00000-A-00007-00002-00888-000-00420`)", required=True)
def uk_cambridge(id):
	"""
	image from images.lib.cam.ac.uk
	"""
	import uk
	uk.get_cambridge(id=id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `1273e6f5-ee79-4f6b-9014-a9065a93b9ff`)", required=True)
def uk_bodleian(id):
	"""
	image from digital.bodleian.ox.ac.uk
	"""
	import uk
	uk.get_bodleian(id=id)


@main.command()
@click.option("--id", help="Id of the image to be downloaded (e. g. `PPN1748520709`)", required=True)
def goettingen(id):
	"""
	book from gdz.sub.uni-goettingen.de
	"""
	import goettingen
	goettingen.get_book(id)
	
	
@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `172099`)", required=True)
def no_nb(id):
	"""
	book from www.nb.no
	"""
	import no
	no.get_nb(id=id)
	

@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `object125610`)", required=True)
def dk_kb(id):
	"""
	book from www5.kb.dk
	"""
	import dk
	dk.get_kb(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `63678`)", required=True)
def ru_shpl(id):
	"""
	book from elib.shpl.ru
	"""
	import ru
	ru.get_shpl(id=id)


@main.command()
@click.option("--id", help="Id of the book to be downloaded (e. g. `122cdc10-0032-0130-6561-58d385a7bc34`)", required=True)
def us_nypl(id):
	"""
	image set from digitalcollections.nypl.org
	"""
	import us
	us.get_nypl(id=id)


if __name__ == "__main__":
	try:
		main()
	except Exception as ex:
		traceback.print_exc()
