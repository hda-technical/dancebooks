import re

import bs4
import iiif

import utils


JSONURL_REGEXP = re.compile(r"var\s*jsonurl\s*=")
STRING_LITERAL_REGEXP = re.compile(r'"((?:[^"\\]|\\.)*)"')


def get_kb(*, id):
	html_url = f"http://digitalesamlinger.kb.dk/manus/musman/2010/dec/viser/{id}/en/"
	html = bs4.BeautifulSoup(
		utils.get_text(html_url),
		features="html.parser",
	)
	for script in html.find_all("script"):
		if match := JSONURL_REGEXP.search(script.text):
			body = script.text[match.end():]
			end = body.find("];")
			if end != -1:
				body = body[:end]
			urls = STRING_LITERAL_REGEXP.findall(body)
			break

	output_folder = utils.make_output_folder("kb_dk", id)
	for page, info_url in enumerate(urls):
		output_filename = utils.make_output_filename(output_folder, page, extension="jpg")
		info = utils.get_json(info_url)
		image_url = f"{info['@id']}/full/full/0/native.jpg"
		print(f"Downloading page #{page:08d} from {image_url}")
		utils.get_binary(output_filename, image_url)
