import deep_zoom


def get(id):
	output_filename = f"bodleian_{id}.bmp"
	metadata_url = f"https://digital.bodleian.ox.ac.uk/inquire/viewer.dzi?DeepZoom={id}.dzi"
	
	MAX_ZOOM = 12
	base_url = f"https://digital.bodleian.ox.ac.uk/inquire/viewer.dzi?DeepZoom={id}.jp2_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM)
	deep_zoom.download_image(output_filename, metadata_url, url_maker)