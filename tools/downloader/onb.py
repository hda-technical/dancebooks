import os

import requests

import utils


def get(id):
	# First, normalizing id
	id = id.replace('/', '_')
	if id.startswith("ABO"):
		flavour = "OnbViewer"
	elif id.startswith("DTL"):
		flavour = "RepViewer"
	else:
		raise RuntimeError(f"Can not determine flavour for {id}")

	# Second, obtaining JSESSIONID cookie value
	viewer_url = f"http://digital.onb.ac.at/{flavour}/viewer.faces?doc={id}"
	viewer_response = requests.get(viewer_url)
	cookies = viewer_response.cookies
	metadata_url = f"http://digital.onb.ac.at/{flavour}/service/viewer/imageData?doc={id}&from=1&to=1000"
	metadata = utils.get_json(metadata_url, cookies=cookies)
	output_folder = utils.make_output_folder("onb", id)
	image_data = metadata["imageData"]
	print(f"Going to download {len(image_data)} images")
	for image in image_data:
		query_args = image["queryArgs"]
		image_id = image["imageID"]
		image_url = f"http://digital.onb.ac.at/{flavour}/image?{query_args}&s=1.0&q=100"
		output_filename = utils.make_output_filename(output_folder, image_id, extension=None)
		if os.path.isfile(output_filename):
			print(f"Skip downloading existing image {image_id}")
			continue
		print(f"Downloading {image_id}")
		utils.get_binary(output_filename, image_url, cookies=cookies)