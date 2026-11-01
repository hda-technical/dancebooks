#!/usr/bin/env python3

import io
import pathlib
import os
import sys

import click
import fpdf
import PIL as pil

from dancebooks.img import Geometry, TurboJpeg


def is_path_valid(path):
	return path.is_file() and path.suffix in [".jpg"]


def crop_jpeg_image(
	img: pil.Image.Image,
	*,
	output: Geometry,
) -> tuple[str | io.BytesIO, Geometry]:
	"""
	Losslessly crop given jpeg image, just like `jpegtran -crop` would do.

	Only the crop origin is bound to the MCU (minimum coded unit) grid,
	the region size is arbitrary: the trailing partial MCUs are stored,
	yet are never shown by the decoder.

	Returns (image data, cropped region) tuple, image data being either
	the untouched source path, or an in-memory jpeg file.
	"""

	with open(img.filename, "rb") as fobj:
		data: bytes = fobj.read()

	image, mcu = TurboJpeg().decode_header(data)
	region = output.align(image, mcu)
	if region.size == image.size:
		# nothing to crop, pass the source file through
		return (img.filename, region)

	cropped: bytes = TurboJpeg().crop(data, region)

	return (io.BytesIO(cropped), region)


@click.group()
def main():
	pass


@main.command()
@click.option("--output-size", callback=Geometry.from_click, default=None)
def convert(output_size: Geometry | None) -> None:
	"""
	Convert set of images from current directory into a set of pdf files.
	"""
	if output_size is None:
		print("Will not change image size during generation")
	else:
		print(f"Will generate images of geometry {output_size}")

	dir = pathlib.Path(".")

	pdf = fpdf.FPDF(unit="in")
	count = 0
	for idx, path in enumerate(sorted(dir.iterdir())):
		if not is_path_valid(path):
			print(f"Skip non-jpeg file at {path}")
			continue

		img = pil.Image.open(path)
		x_dpi, y_dpi = img.info.get("dpi", (600, 600))

		data: str | io.BytesIO
		image: Geometry
		page_size: tuple[int, int]
		if output_size is None:
			data, image = img.filename, Geometry(*img.size, 0, 0)
			page_size = img.size
		else:
			data, image = crop_jpeg_image(img, output=output_size)
			page_size = output_size.size

		# center the image on the page (matters when the image is smaller than the page)
		x: float = (page_size[0] - image.width) / 2
		y: float = (page_size[1] - image.height) / 2

		count += 1
		print(
			f"Page {count}: {path} ({Geometry(*img.size)}) -> {image}, "
			f"{page_size[0] / x_dpi:.2f}x{page_size[1] / y_dpi:.2f} in "
			f"at {x_dpi}x{y_dpi} dpi"
		)
		pdf.add_page(
			format=(page_size[0] / x_dpi, page_size[1] / y_dpi)
		)
		pdf.image(
			data,
			x=x / x_dpi,
			y=y / y_dpi,
			w=image.width / x_dpi,
			h=image.height / y_dpi,
		)
	if count:
		print(f"Merging {count} pages into output.pdf")
		pdf.output("output.pdf")
	else:
		print("No pages to merge")


if __name__ == "__main__":
	main()
