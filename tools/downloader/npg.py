import deep_zoom
import utils


def get(id):
	base_url = f"https://collectionimages.npg.org.uk/zoom/{id}/zoomXML"
	tile_base_url = f"{base_url}_files"
	url_maker = deep_zoom.UrlMaker(tile_base_url, max_zoom=11)
	
	metadata_url = f"{base_url}.dzi"
	output_filename = utils.make_output_filename(".", f"npg_{id}", extension="bmp")
	deep_zoom.download_image(output_filename, metadata_url, url_maker)
	