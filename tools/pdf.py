#!/usr/bin/env python3

import math
import pathlib
import os
import subprocess
import sys

import click
import fpdf
import PIL as pil


def round_up(value, divisor):
	return math.ceil(value / divisor) * divisor


def validate_format(ctx, param, value):
	if value is None:
		return None
	try:
		width, height = map(int, value.split('x'))

		# round up to divisable of 16, as required by jpegtran
		width = round_up(width, 16)
		height = round_up(height, 16)

		return (width, height)
	except Exception as ex:
		print(repr(ex))
		raise click.BadParameter('format should be {width}x{height}')


def is_path_valid(path):
	return path.is_file() and path.suffix in [".jpg"]


def get_crop_offset(img, *, output_size):
	iw, ih = img.size
	tw, th = output_size
	x = (iw - tw) // 2
	y = (ih - th) // 2
	return (x, y)


def get_position(img, *, output_size):
	x, y = get_crop_offset(img, output_size=output_size)
	return (-x, -y)

def crop_jpeg_image(img, *, output_size, output_path):
	"""
	Losslessly crop given jpeg file via jpegtran invocation
	"""

	width, height = output_size
	x, y = get_crop_offset(img, output_size=output_size)
	if x > 0 or y > 0:
		x = max(x, 0)
		y = max(y, 0)
		target_geometry = f"{width}x{height}+{x}+{y}"
		subprocess.check_call([
			"jpegtran",
			"-perfect",
			"-crop", target_geometry,
			"-outfile", str(output_path), img.filename
		])
		return pil.Image.open(img.filename)
	else:
		return img


@click.group()
def main():
	pass


@main.command()
@click.option("--output-size", callback=validate_format, default=None)
def convert(output_size):
	"""
	Convert set of images from current directory into a set of pdf files.
	"""
	if output_size is None:
		print(f"Will not change image size during generation")
	else:
		width, height = output_size
		print(f"Will generate images of size {width}x{height}")

	dir = pathlib.Path(".")

	pdf = fpdf.FPDF(unit="in")
	for idx, path in enumerate(dir.iterdir()):
		if not is_path_valid(path):
			print(f"Skip non-jpeg file at {path}")
			continue

		img = pil.Image.open(path)
		width, height = img.size
		x_dpi, y_dpi = img.info.get("dpi", (600, 600))

		# TODO: restore jpegtran cropping

		pdf.add_page(
			format=(width / x_dpi, heigh / y_dpi)
		)
		pdf.image(
			img.filename,
			x=0,
			y=0,
			w=width / x_dpi,
			h=height / y_dpi,
		)
	pdf.output("output.pdf")


if __name__ == "__main__":
	main()
