#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks import db

if __name__ == "__main__":
	with open("Backups.md") as backups_file:
		lines = backups_file.readlines()
	backups = []
	for idx, line in enumerate(lines):
		line = line.strip(" \n").strip("|")
		paths, provenance, aspect_ratio, image_size, note = list(map(str.strip, line.split('|')))
		aspect_ratio_x, aspect_ratio_y = map(int, aspect_ratio.strip('`').split('x'))
		image_size_x, image_size_y = map(int, aspect_ratio.strip('`').split('x'))
		unquote = lambda s: s.strip('`')
		paths = list(map(unquote, paths.split('<br/>')))
		if note and note[-1] != '.':
			print(f"Comment on line {idx + 1} does not end with dot.")
		for path in paths:
			backup = db.Backup(
				path=path,
				provenance=provenance,
				aspect_ratio_x=aspect_ratio_x,
				aspect_ratio_y=aspect_ratio_y,
				image_size_x=image_size_x,
				image_size_y=image_size_y,
				note=note
			)
			backups.append(backup)

	print(f"Going to upload: {len(backups)} backups")
	with db.make_transaction() as txn:
		txn.add_all(backups)
		txn.commit()
	print(f"Uploaded: {len(backups)} backups")
