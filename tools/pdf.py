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
	try:
		if value == "unchanged":
			return None
		width, height = map(int, value.split('x'))

		# round up to divisable of 16, as required by jpegtran
		width = round_up(width, 16)
		height = round_up(height, 16)

		return (width, height)
	except Exception as ex:
		print(repr(ex))
		raise click.BadParameter('format should be {width}x{height}')


def convert_to_pdf(
	img: pil.Image, 
	output_path: pathlib.Path, 
	*,
	size=None,
	position=(0, 0),
):
	if size is None:
		size = img.size
	x_dpi, y_dpi = img.info.get("dpi", (600, 600))
	pdf = fpdf.FPDF(
		unit="in",
		format=(size[0] / x_dpi, size[1] / y_dpi)
	)
	pdf.add_page()
	pdf.image(
		img.filename, 
		x=position[0] / x_dpi,
		y=position[1] / y_dpi,
		w=img.size[0] / x_dpi,
		h=img.size[1] / y_dpi,
	)
	pdf.output(output_path)


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
@click.option("--output-size", callback=validate_format)
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
	for idx, path in enumerate(dir.iterdir()):
		if not is_path_valid(path):
			print(f"Skipping non-image object at {path}")
			continue
		output_path = path.with_suffix(".pdf")
		print(f"Converting {path} to {output_path}")
		img = pil.Image.open(path)
		if output_size is None:
			convert_to_pdf(img, output_path)
			continue

		cropped_path = path.with_suffix(".tmp.jpg")
		
		img = crop_jpeg_image(
			img,
			output_size=output_size,
			output_path=cropped_path,
		)
		
		x, y = get_position(img, output_size=output_size)
		convert_to_pdf(img, output_path, size=output_size, position=(x, y))
		if os.path.exists(cropped_path):
			os.remove(cropped_path)


if __name__ == "__main__":
	main()