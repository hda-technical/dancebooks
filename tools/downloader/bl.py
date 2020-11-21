import deep_zoom
import iiif
import utils


def get_book(id):
	output_folder = utils.make_output_folder("bl", id)
	manifest_url = f"https://api.bl.uk/metadata/iiif/ark:/81055/{id}.0x000001/manifest.json"
	iiif.download_book_fast(manifest_url, output_folder)


def get_manuscript(id):
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