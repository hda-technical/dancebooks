import iiif
import utils


def get_book(id):
	manifest_url = f"https://api.digitale-sammlungen.de/iiif/presentation/v2/{id}/manifest"
	output_folder = utils.make_output_folder("bsb", id)
	iiif.download_book_fast(manifest_url, output_folder)