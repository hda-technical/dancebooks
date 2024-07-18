import json

import iiif
import utils


def get_rovereto(*, id):
	manifest_url = f"https://digitallibrary.bibliotecacivica.rovereto.tn.it/server/iiif/{id}/manifest"
	manifest_text = utils.get_text(manifest_url)
	# rovereto.tn.it IIIF server returns incorrect json which is split info multiple short lines.
	# Join them into single line before parsing.
	manifest = json.loads(manifest_text.replace("\r\n", ""))
	
	output_folder = utils.make_output_folder("rovereto", id[0:8])
	iiif.download_book_fast(manifest, output_folder)
