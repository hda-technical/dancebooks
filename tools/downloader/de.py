import iiif
import utils


def get_karlsruhe(*, id):
	manifest_url = f"https://digital.blb-karlsruhe.de/i3f/v20/{id}/manifest"
	output_folder = utils.make_output_folder("karlsruhe", id)
	# Invoking download_book_fast will cause downloading of a lower-resolution copy of the image.
	# Fallback to a tile-based downloader for the higher resolution.
	iiif.download_book(manifest_url, output_folder)