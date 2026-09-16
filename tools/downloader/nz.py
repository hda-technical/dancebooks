import re

import iiif
import utils


# tiaki.natlib.govt.nz itself sits behind an Imperva bot check and is not scriptable,
# but the Rosetta instance actually storing the scans is reachable as is.
DELIVERY_URL = "https://ndhadeliver.natlib.govt.nz"

IE_PID_REGEXP = re.compile(r"IE\d+")


def _get_ie_pid(record_id):
	"""
	Translates Tiaki (EMu) record id into the pid of the corresponding Rosetta digital object.
	"""
	url = f"{DELIVERY_URL}/content-aggregator/getIEs?system=emu&id={record_id}"
	# the aggregator answers with a redirect to the viewer of the digitised copy
	response = utils.make_request(url, allow_redirects=False)
	match = IE_PID_REGEXP.search(response.headers.get("Location", ""))
	if match is None:
		raise RuntimeError(f"Record {record_id} has no digitised copy in the delivery system")
	return match.group()


def get_tiaki(*, id):
	if id.startswith("IE"):
		ie_pid = id
	else:
		# `ecatalogue.20015` (as it is written in the tiaki url) or bare `20015`
		ie_pid = _get_ie_pid(id.rpartition(".")[2])
		print(f"Record {id} is digitised as {ie_pid}")
	manifest_url = f"{DELIVERY_URL}/delivery/iiif/presentation/3/{ie_pid}/manifest"
	output_folder = utils.make_output_folder("tiaki", id)
	iiif.download_book_fast_v3(manifest_url, output_folder)
