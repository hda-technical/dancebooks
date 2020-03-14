import json
from xml.etree import ElementTree

import requests

import utils


def get_book_from_difmoe(id):
	children_url = f"https://kramerius.difmoe.eu/search/api/v5.0/item/uuid:{id}/children"
	children = utils.get_json(children_url)
	print(f"Downloading {len(children)} images from kramerius.difmoe.eu")
	
	output_folder = utils.make_output_folder("difmoe", id)
	for page, child in enumerate(children, start=1):
		child_pid = child["pid"]
		image_url = f"https://kramerius.difmoe.eu/search/img?pid={child_pid}&stream=IMG_FULL"
		output_filename = utils.make_output_filename(output_folder, page=page, extension="jpg")
		utils.get_binary(output_filename, image_url)