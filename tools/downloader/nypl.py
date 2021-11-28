import utils


def get(id):
	metadata_url = f"https://digitalcollections.nypl.org/items/{id}/captures?page=1&per_page=1000"
	metadata = utils.get_json(metadata_url)
	output_folder = utils.make_output_folder("nypl", id[0:8])
	captures = metadata["response"]["captures"]
	print(f"Going to download {len(captures)} images")
	for idx, capture in enumerate(captures):
		url = capture["high_res_link"]
		output_filename = utils.make_output_filename(output_folder, page=idx, extension="tif")
		print(f"Downloading page #{idx:04d}")
		utils.get_binary(output_filename, url)