import iiif
import utils


def get_mzk(*, id):
	manifest_url = f"https://iiif.digitalniknihovna.cz/mzk/uuid:{id}"
	output_folder = utils.make_output_folder("mzk", id[:8])
	iiif.download_book_fast_v3(manifest_url, output_folder)


def get_nkp(*, id):
	manifest_url = f"https://iiif.digitalniknihovna.cz/nkp/uuid:{id}"
	output_folder = utils.make_output_folder("nkp", id[:8])
	iiif.download_book_fast_v3(manifest_url, output_folder)
