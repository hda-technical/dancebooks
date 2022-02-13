import iip
import utils


def get(id, secondary_id, page):
	"""
	Downloads book from https://www.prlib.ru/
	"""
	metadata_url = f"https://content.prlib.ru/metadata/public/{id}/{secondary_id}/{id}.json"
	files_root = f"/var/data/scans/public/{id}/{secondary_id}/"
	fastcgi_url = "https://content.prlib.ru/fcgi-bin/iipsrv.fcgi"
	output_folder = utils.make_output_folder("prlib", id.split('-')[0])
	if page:
		page = int(page)
		output_filename = utils.make_output_filename(output_folder, page)
		metadata = utils.get_json(metadata_url)
		page_metadata = metadata[page]
		remote_filename = os.path.join(files_root, page_metadata["f"])
		iip.download_image(fastcgi_url, remote_filename, page_metadata, output_filename)
	else:
		iip.download_book(
			metadata_url=metadata_url,
			fastcgi_url=fastcgi_url,
			files_root=files_root,
			output_folder=output_folder
		)