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


def get_image_size(path):
	img = pil.Image.open(path)
	width, height = img.size
	return (width, height)


def convert_to_pdf(img: pil.Image, output_path: pathlib.Path, *, position):
	DEFAULT_DPI = (600, 600)
	x, y = position
	w_inch = img.width / img.info.get("dpi", DEFAULT_DPI)[0]
	h_inch = img.height / img.info.get("dpi", DEFAULT_DPI)[1]
	pdf = fpdf.FPDF(unit="in", format=(w_inch, h_inch))
	pdf.add_page()
	pdf.image(img.filename, x=x, y=y, w=w_inch, h=h_inch)
	pdf.output(output_path)


def is_path_valid(path):
	return path.is_file() and path.suffix in [".jpg"]


def crop_jpeg_image(*, output_size, input_path, output_path):
	"""
	Losslessly crop given jpeg file via jpegtran invocation
	"""
	def get_offset_for_cropping():
		iw, ih = get_image_size(input_path)
		tw, th = output_size
		assert iw >= tw
		assert ih >= th
		x = (iw - tw) // 2
		y = (ih - th) // 2
		return (x, y)

	width, height = output_size
	x, y = get_offset_for_cropping()
	target_geometry = f"{width}x{height}+{x}+{y}"
	subprocess.check_call([
		"jpegtran",
		"-perfect",
		"-crop", target_geometry,
		"-outfile", str(output_path), str(input_path)
	])


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
		if output_size is None:
			img = pil.Image.open(path)
			convert_to_pdf(img, output_path, position=(0, 0))
			continue

		cropped_path = path.with_suffix(".tmp.jpg")
		crop_jpeg_image(
			output_size=(width, height),
			input_path=path,
			output_path=cropped_path,
		)
		img = pil.Image.open(cropped_path)
		convert_to_pdf(img, output_path, position=(0, 0))
		os.remove(cropped_path)


if __name__ == "__main__":
	main()