import json
import os
import re
import textwrap

import bs4
import requests

import iip
import utils


def get_prlib(*, id, page):
	def _detect_identifiers(id):
		PREVIEW_URL_REGEXP = re.compile(r"https://www.prlib.ru/sites/default/files/book_preview/([\w-]+)/(\d+)_doc1.*$")
		
		book_url = f"https://www.prlib.ru/item/{id}"
		soup = bs4.BeautifulSoup(
			utils.get_text(book_url),
			features="html.parser",
		)
		preview_url = soup.find("meta", attrs={"property": "og:image"})["content"]
		
		if m := PREVIEW_URL_REGEXP.match(preview_url):
			primary_id, secondary_id = m.group(1, 2)
			# some dirty hacks to go
			primary_id = primary_id.upper()
			secondary_id = int(secondary_id) - 1
			return (primary_id, secondary_id)
		else:
			raise ValueError(f"Failed to parse primary and secondary id from {preview_url}")
	
	primary_id, secondary_id = _detect_identifiers(id)

	metadata_url = f"https://content.prlib.ru/metadata/public/{primary_id}/{secondary_id}/{primary_id}.json"
	files_root = f"/var/data/scans/public/{primary_id}/{secondary_id}/"
	fastcgi_url = "https://content.prlib.ru/fcgi-bin/iipsrv.fcgi"
	output_folder = utils.make_output_folder("prlib", id)
	if page is not None:
		output_filename = utils.make_output_filename(output_folder, page)
		page_metadata = utils.get_json(metadata_url)["pgs"][page - 1]
		remote_filename = os.path.join(files_root, page_metadata["f"])
		iip.download_image(
			fastcgi_url,
			remote_filename,
			iip.Metadata.from_json(page_metadata),
			output_filename,
		)
	else:
		iip.download_book(
			metadata_url=metadata_url,
			fastcgi_url=fastcgi_url,
			files_root=files_root,
			output_folder=output_folder
		)


def get_shpl(*, id):
	INIT_REGEXP = re.compile(r'initDocview\((.*)\)')
	
	main_page_url = f"http://elib.shpl.ru/ru/nodes/{id}"
	main_page = bs4.BeautifulSoup(
		utils.get_text(main_page_url),
		features="html.parser"
	)
	for script in main_page.find_all("script"):
		if match := INIT_REGEXP.search(script.text.strip()):
			metadata = json.loads(match.group(1))
			break
	
	pages = metadata["pages"]
	first_page = pages[0]["id"]
	last_page = pages[-1]["id"]
	# Assume max_zoom to be equal to 8. Proper value can be found in metadata
	dta_url = f"http://elib.shpl.ru/pages/[{first_page}:{last_page}]/zooms/8"
	print(textwrap.dedent(
		f"""
		Downloading from shpl.ru is not supported via this tool.
		Paste the following url into DownThemAll browser extension:
		{dta_url}
		"""
	).strip())