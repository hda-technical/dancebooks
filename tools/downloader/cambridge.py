import deep_zoom


def get(id):
	metadata_url = f"https://images.lib.cam.ac.uk/content/images/{id}.dzi"
	output_filename = f"cambridge.{id}.bmp"
	
	MAX_ZOOM = 14
	base_url = f"https://images.lib.cam.ac.uk/content/images/{id}_files"
	url_maker = deep_zoom.UrlMaker(base_url, MAX_ZOOM)
	deep_zoom.download_image(output_filename, metadata_url, url_maker)