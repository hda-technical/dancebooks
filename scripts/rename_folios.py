#!/usr/bin/env python3

import os

import opster

@opster.command()
def main(
	start=("", 1, "First folio number"),
	prefix=("", "", "Prefix to be added to all folio numbers")
):
	files = os.listdir(".")
	folio = int(start)
	suffix = "r"
	prefix = str(prefix)
	for file in files:
		if file.endswith(".py"):
			continue
		basename, ext = os.path.splitext(file)
		new_filename = f"{prefix}{folio:04d}{suffix}{ext}"
		print(f"Renaming {file} to {new_filename}")
		os.rename(file, new_filename)
		if suffix == "r":
			suffix = "v"
		else:
			suffix = "r"
			folio += 1
	

if __name__ == "__main__":
	main.command()