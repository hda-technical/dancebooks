#!/usr/bin/env python3

import functools
import io
import pathlib
import os
import sys

import click
import fpdf
import PIL as pil
import turbojpeg

from dancebooks.img import Geometry


def round_down(value: int, divisor: int) -> int:
	return value // divisor * divisor


def is_path_valid(path):
	return path.is_file() and path.suffix in [".jpg"]


@functools.cache
def get_jpegtran() -> turbojpeg.TurboJPEG:
	"""
	libjpeg-turbo handle, performing the very same lossless transforms
	the jpegtran binary does (which is a part of the same library).
	"""
	return turbojpeg.TurboJPEG()


def get_crop_offset(
	data: bytes,
	*,
	output: Geometry,
) -> tuple[int, int]:
	"""
	Offset of the crop region: either the requested one, or the centering one.

	Only the crop origin is bound to the MCU (minimum coded unit) grid,
	the region size is arbitrary: the trailing partial MCUs are stored,
	yet are never shown by the decoder.

	MCU size depends on the chroma subsampling of the very file being cropped:
	8x8 for 4:4:4 and grayscale, 16x8 for 4:2:2, 16x16 for 4:2:0, 32x8 for 4:1:1.
	"""

	def align(
		offset: int | None,
		image_size: int,
		region_size: int,
		grid: int,
	) -> int:
		limit = image_size - region_size
		if limit <= 0:
			return 0
		if offset is None:
			# center the region, rounding to the nearest grid node
			offset = limit // 2 + grid // 2
		# round to the grid node, keeping the whole region inside the image
		return min(round_down(offset, grid), round_down(limit, grid))

	iw, ih, subsampling, _ = get_jpegtran().decode_header(data)
	return (
		align(output.x, iw, output.width, turbojpeg.tjMCUWidth[subsampling]),
		align(output.y, ih, output.height, turbojpeg.tjMCUHeight[subsampling]),
	)


def crop_jpeg_image(
	img: pil.Image.Image,
	*,
	output: Geometry,
) -> tuple[str | io.BytesIO, Geometry]:
	"""
	Losslessly crop given jpeg image, just like `jpegtran -crop` would do.

	Returns (image data, cropped region) tuple, image data being either
	the untouched source path, or an in-memory jpeg file.
	"""

	iw, ih = img.size
	with open(img.filename, "rb") as fobj:
		data: bytes = fobj.read()

	x, y = get_crop_offset(data, output=output)
	region = Geometry(
		width=min(output.width, iw - x),
		height=min(output.height, ih - y),
		x=x,
		y=y,
	)
	if region.size == img.size:
		# nothing to crop, pass the source file through
		return (img.filename, region)

	cropped: bytes = get_jpegtran().crop_multiple(
		jpeg_buf=data,
		crop_parameters=[(
			region.x,		 # region origin x
			region.y,		 # region origin y
			region.width,	 # region width
			region.height,	 # region height
		)],
	)[0]

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
