#!/usr/bin/env python3

import os
import sys

import opster

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks import db
from dancebooks import const

NOT_DEFINED = "NOT_DEFINED"

@opster.command()
def add(
	path=("", "", "Backup path")
):
	raise NotImplementedError()


@opster.command()
def get(
	id=("", 0, "Id of the backup to be updated"),
):
	if id == 0:
		print("Backup id is required")
		sys.exit(1)
	with db.make_transaction() as session:
		backup = session.query(db.Backup).get(id)
		print(f"Path:\n{backup.path}")
		print(f"Provenance:\n{backup.provenance}")
		print(f"Note:\n{backup.note}")
		print(f"Image size: {backup.image_size_x}{const.SIZE_DELIMETER}{backup.image_size_y}")
		print(f"Aspect ration: {backup.aspect_ratio_x}{const.SIZE_DELIMETER}{backup.aspect_ratio_y}")


@opster.command()
def update(
	id=("", 0, "Id of the backup to be updated"),
	# opster does not allow checking if the option was defined.
	# Workaround this by passing ugly default.
	path=("", NOT_DEFINED, "Set backup path to the given value"),
	provenance=("", NOT_DEFINED, "Set backup provenance to the given value (markdown supported)"),
	note=("", NOT_DEFINED, "Set backup note to the given value (markdown supported)"),
	image_size=("", NOT_DEFINED, "Set backup image size to the given value (WxH)"),
	aspect_ratio=("", NOT_DEFINED, "Set backup image aspect ratio to the given value (WxH)")
):
	if id == 0:
		print("Backup id is required")
		sys.exit(1)
	with db.make_transaction() as session:
		backup = session.query(db.Backup).get(id)
		modified = False
		if path != NOT_DEFINED:
			backup.path = path
			modified = True
		if provenance != NOT_DEFINED:
			backup.provenance = provenance
			modified = True
		if note != NOT_DEFINED:
			backup.note = note
			modified = True
		if image_size != NOT_DEFINED:
			backup.image_size_x, backup.image_size_y = map(int, image_size.split(const.SIZE_DELIMETER))
			modified = True
		if aspect_ratio != NOT_DEFINED:
			backup.aspect_ratio_x, backup.aspect_ratio_y = map(int, image_size.split(const.SIZE_DELIMETER))
			modified = True
		if modified:
			session.add(backup)
			session.commit()
			print("Updated successfully")
		else:
			print("Nothing to modify")

if __name__ == "__main__":
	opster.dispatch()
