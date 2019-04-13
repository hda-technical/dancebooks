#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks import const
from dancebooks import db

if __name__ == "__main__":
	with open("Backups.md") as backups_file:
		lines = backups_file.readlines()
	backups = []
	warnings_count = 0
	for idx, line in enumerate(lines, start=1):
		try:
			line = line.strip(" \n").strip("|")
			paths, provenance, aspect_ratio, image_size, note = list(map(str.strip, line.split('|')))
			aspect_ratio_x, aspect_ratio_y = map(int, aspect_ratio.strip('`').split(const.SIZE_DELIMETER))
			image_size_x, image_size_y = map(int, image_size.strip('`').split(const.SIZE_DELIMETER))
			unquote = lambda s: s.strip('`')
			paths = list(map(unquote, paths.split('<br/>')))
			if note and note[-1] != '.':
				print(f"Comment on line {idx} does not end with dot.")
				warnings_count += 1
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
		except Exception as ex:
			print(f"While processing line {idx} got exception: {ex!r}")
			sys.exit(1)
	if warnings_count > 0:
		print(f"You have to fix {warnings_count} warnings first")
		sys.exit(1)
	print(f"Going to upload: {len(backups)} backups")
	with db.make_transaction() as session:
		session.add_all(backups)
		session.commit()
	print(f"Uploaded: {len(backups)} backups")
