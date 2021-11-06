#!/usr/bin/env python3

import os

import opster

@opster.command()
def main(
	start=("", 1, "First folio number"),
	prefix=("", "", "Prefix to be added to all folio numbers")
):
	filenames = []
	for entry in os.scandir("."):
		if not entry.is_file():
			# take only files into account
			continue
		if entry.name.endswith(".py"):
			# skip some well-known extensions
			# generally, this filter must be improved
			continue
		filenames.append(entry.name)
	
	folio = int(start)
	suffix = "r"
	for filename in sorted(filenames):
		basename, ext = os.path.splitext(filename)
		new_filename = f"{prefix}{folio:04d}{suffix}{ext}"
		print(f"Renaming {filename} to {new_filename}")
		os.rename(filename, new_filename)
		if suffix == "r":
			suffix = "v"
		else:
			suffix = "r"
			folio += 1
	

if __name__ == "__main__":
	main.command()