import os
import re

import bs4

import iip
import utils


PREVIEW_URL_REGEXP = re.compile(r"https://www.prlib.ru/sites/default/files/book_preview/([\w-]+)/(\d+)_doc1.*$")


def _detect_identifiers(book_id):
	html = utils.get_text(f"https://www.prlib.ru/item/{book_id}")
	soup = bs4.BeautifulSoup(html, "html.parser")
	preview_url = soup.find("meta", attrs={"property": "og:image"})["content"]
	if m := PREVIEW_URL_REGEXP.match(preview_url):
		primary_id, secondary_id = m.group(1, 2)
		# some dirty hacks to go
		primary_id = primary_id.upper()
		secondary_id = int(secondary_id) - 1
		return (primary_id, secondary_id)
	else:
		raise ValueError(f"Failed to parse primary and secondary id from {preview_url}")


def get(book_id, page):
	"""
	Downloads book from https://www.prlib.ru/
	"""
	primary_id, secondary_id = _detect_identifiers(book_id)

	metadata_url = f"https://content.prlib.ru/metadata/public/{primary_id}/{secondary_id}/{primary_id}.json"
	files_root = f"/var/data/scans/public/{primary_id}/{secondary_id}/"
	fastcgi_url = "https://content.prlib.ru/fcgi-bin/iipsrv.fcgi"
	output_folder = utils.make_output_folder("prlib", book_id)
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