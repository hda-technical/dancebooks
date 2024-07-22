import json
import re

import bs4
import iiif

import utils


URL_REGEXP = re.compile(r'var jsonurl = (\[.*\]);')


def get_kb(*, id):
	html_url = f"http://www5.kb.dk/manus/musman/2010/dec/viser/{id}/en/"
	html = bs4.BeautifulSoup(utils.get_text(html_url))
	for script in html.find_all("script"):
		if match := URL_REGEXP.search(script.text):
			urls = json.loads(match.group(1))
			break
	
	output_folder = utils.make_output_folder("kb_dk", id)
	for page, info_url in enumerate(urls):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		info = utils.get_json(info_url)
		image_url = f"{info['@id']}/full/full/0/native.jpg"
		print(f"Downloading page #{page:08d} from {image_url}")
		utils.get_binary(output_filename, image_url)