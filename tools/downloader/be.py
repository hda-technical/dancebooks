import iiif
import utils


def get_libis(id):
	output_folder = utils.make_output_folder("be_libis", id)
	manifest_url = f"https://lib.is/{id}/manifest"
	iiif.download_book_fast(manifest_url, output_folder)