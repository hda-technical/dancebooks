import iiif
import utils


def get_nb(*, id):
	manifest_url = f"https://api.nb.no/catalog/v1/iiif/URN:NBN:no-nb_digimanus_{id}/manifest?profile=nbdigital"
	output_folder = utils.make_output_folder("nb_no", id)
	iiif.download_book_fast(manifest_url, output_folder)