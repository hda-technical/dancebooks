import json
import re

import bs4
import requests

import utils


INIT_REGEXP = re.compile(r'initDocview\((.*)\)')


def get(id):
	main_page_url = f"http://elib.shpl.ru/ru/nodes/{id}"
	main_page = bs4.BeautifulSoup(utils.get_text(main_page_url))
	for script in main_page.find_all("script"):
		if match := INIT_REGEXP.search(script.text.strip()):
			metadata = json.loads(match.group(1))
			break
	
	pages = metadata["pages"]
	first_page = pages[0]["id"]
	last_page = pages[-1]["id"]
	# Assume max_zoom to be equal to 8. Proper value can be found in metadata
	dta_url = f"http://elib.shpl.ru/pages/[{first_page}:{last_page}]/zooms/8"
	print(f"""
Downloading from shpl.ru is not supported via this tool.
Paste the following url into DownThemAll browser extension:
{dta_url}
""")