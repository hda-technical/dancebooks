#!/usr/bin/env python3

import datetime
import os
import subprocess
import sys

import click

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dancebooks.config import config
from dancebooks import const
from dancebooks import db

NOT_DEFINED = "NOT_DEFINED"
SIZE_FORMAT = f"W{const.SIZE_DELIMETER}H"

def fixup_path(path):
	# Fixing Windows-style paths
	return path.replace('\\', '/')


def make_library_path(path):
	path, maybe_ext = os.path.splitext(path)
	if len(maybe_ext) > 4:
		path += maybe_ext
	return os.path.join(config.www.elibrary_dir, path) + ".pdf"


@click.group()
def main():
	pass


@main.command()
@click.option("--force", is_flag=True, help="Do not check PDF file presence")
def add(force):
	backup = db.Backup()
	backup.path = input("Enter path: ")
	backup.path = fixup_path(backup.path)

	library_path = make_library_path(backup.path)
	if not os.path.isfile(library_path) and not force:
		raise ValueError(f"Original file for this backup ({library_path}) was not found in elibrary")

	backup.provenance = input("Enter provenance (markdown supported): ")
	backup.aspect_ratio_x, backup.aspect_ratio_y = map(
		int,
		input(f"Enter aspect ratio ({SIZE_FORMAT}): ").split(const.SIZE_DELIMETER)
	)
	backup.image_size_x, backup.image_size_y = map(
		int,
		input(f"Enter image size ({SIZE_FORMAT}): ").split(const.SIZE_DELIMETER)
	)
	backup.note = input("Enter note (markdown supported): ")
	if backup.note and backup.note[-1] != '.':
		print("The note must end with a dot.")
		sys.exit(1)

	with db.make_transaction() as session:
		session.add(backup)
		session.commit()
		print(f"Added backup #{backup.id}")


@main.command()
@click.option("--id", type=int, required=True, help="Id of the backup to be shown")
def get(id):
	if id == 0:
		print("Backup id is required")
		sys.exit(1)
	with db.make_transaction() as session:
		backup = session.get(db.Backup, id)
		print(f"Path:\n{backup.path}")
		print(f"Provenance:\n{backup.provenance}")
		print(f"Note:\n{backup.note}")
		print(f"Image size: {backup.image_size_x}{const.SIZE_DELIMETER}{backup.image_size_y}")
		print(f"Aspect ratio: {backup.aspect_ratio_x}{const.SIZE_DELIMETER}{backup.aspect_ratio_y}")


@main.command()
@click.option("--id", type=int, required=True, help="Id of the backup to be updated")
@click.option("--path", type=str, default=None, help="Set backup path to the given value")
@click.option("--provenance", type=str, default=None, help="Set backup provenance to the given value (markdown supported)")
@click.option("--note", type=str, default=None, help="Set backup note to the given value (markdown supported)")
@click.option("--image-size", type=str, default=None, help=f"Set backup image size to the given value ({SIZE_FORMAT})")
@click.option("--aspect-ratio", type=str, default=None, help=f"Set backup image aspect ratio to the given value ({SIZE_FORMAT})")
@click.option("--type", type=str, default=None, help="Set backup to the given value")
def update(
	id,
	path,
	provenance,
	note,
	image_size,
	aspect_ratio,
	type,
):
	with db.make_transaction() as session:
		backup = session.get(db.Backup, id)
		modified = False
		if path is not None:
			path = fixup_path(path)
			library_path = make_library_path(path)
			if not os.path.isfile(library_path):
				raise ValueError("Original file for this backup was not found in elibrary")
			backup.path = path
			modified = True
		if provenance is not None:
			backup.provenance = provenance
			modified = True
		if note is not None:
			backup.note = note
			modified = True
		if image_size is not None:
			backup.image_size_x, backup.image_size_y = map(int, image_size.split(const.SIZE_DELIMETER))
			modified = True
		if aspect_ratio is not None:
			backup.aspect_ratio_x, backup.aspect_ratio_y = map(int, aspect_ratio.split(const.SIZE_DELIMETER))
			modified = True
		if type is not None:
			backup.type = type
			modified = True
		if modified:
			session.add(backup)
			session.commit()
			print("Updated successfully")
		else:
			print("Nothing to modify")


@main.command()
@click.option("--id", type=int, required=True, help="Id of the backup to be deleted")
def delete(id):
	if id == 0:
		print("Backup id is required")
		sys.exit(1)
	with db.make_transaction() as session:
		backup = session.get(db.Backup, id)
		print(f"You are going to delete backup #{id} at '{backup.path}'")
		confirmation = input("Type YES to continue: ")
		if confirmation == "YES":
			session.delete(backup)
			session.commit()
			print(f"Backup #{id} was deleted")


@main.command()
def make_dump():
	output_folder = datetime.date.today().isoformat()
	env = {
		"PGHOST": config.db.host,
		"PGPORT": str(config.db.port),
		"PGUSER": config.db.user,
		"PGPASSWORD": config.db.password,
		"PGDATABASE": config.db.database_name
	}
	cmd = [
		"pg_dump",
		f"--schema={db.Backup.__table_args__['schema']}",
		"--format=d",
		f"--file={output_folder}"
	]
	subprocess.check_call(cmd, env=env)
	print(f"Backed up database to {output_folder}")


if __name__ == "__main__":
	main()
