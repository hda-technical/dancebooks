import iiif
import utils


def get(id):
	output_folder = utils.make_output_folder("darmstadt", id)
	manifest_url = f"http://tudigit.ulb.tu-darmstadt.de/show/iiif/{id}/manifest.json"
	iiif.download_book_fast(manifest_url, output_folder)