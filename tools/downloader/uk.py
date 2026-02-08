import deep_zoom
import iiif
import utils


def get_bl_book(*, id):
	output_folder = utils.make_output_folder("bl", id)
	manifest_url = f"https://api.bl.uk/metadata/iiif/ark:/81055/{id}.0x000001/manifest.json"
	iiif.download_book_fast_v2(manifest_url, output_folder)


def get_bl_manuscript(*, id):
	def parse_id(full_id):
		manuscript_id, _, page_id = tuple(id.rpartition('_'))
		return (manuscript_id, page_id)

	manuscript_id, page_id = parse_id(id)
	#WARN: here and below base_url and metadata_url have common prefix. One might save something
	metadata_url = f"http://www.bl.uk/manuscripts/Proxy.ashx?view={id}.xml"
	output_filename = f"bl_{id}.bmp"

	MAX_ZOOM = 13
	base_url = f"http://www.bl.uk/manuscripts/Proxy.ashx?view={id}_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM)
	deep_zoom.download_image(output_filename, metadata_url, url_maker)


def get_bodleian(*, id):
	output_filename = f"bodleian_{id}.bmp"
	metadata_url = f"https://digital.bodleian.ox.ac.uk/inquire/viewer.dzi?DeepZoom={id}.dzi"
	
	MAX_ZOOM = 12
	base_url = f"https://digital.bodleian.ox.ac.uk/inquire/viewer.dzi?DeepZoom={id}.jp2_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM)
	deep_zoom.download_image(output_filename, metadata_url, url_maker)
	

def get_cambridge(*, id):
	metadata_url = f"https://images.lib.cam.ac.uk/content/images/{id}.dzi"
	output_filename = f"cambridge.{id}.bmp"
	
	MAX_ZOOM = 14
	base_url = f"https://images.lib.cam.ac.uk/content/images/{id}_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM)
	deep_zoom.download_image(output_filename, metadata_url, url_maker)
	

def get_npg(*, id):
	base_url = f"https://collectionimages.npg.org.uk/zoom/{id}/zoomXML"
	tile_base_url = f"{base_url}_files"
	url_maker = deep_zoom.UrlMaker(tile_base_url, max_zoom=11)
	
	metadata_url = f"{base_url}.dzi"
	output_filename = utils.make_output_filename(".", f"npg_{id}", extension="bmp")
	deep_zoom.download_image(output_filename, metadata_url, url_maker)
	