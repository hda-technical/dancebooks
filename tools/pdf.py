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


def round_down(value: int, divisor: int) -> int:
	return value // divisor * divisor


def validate_format(ctx, param, value):
	if value is None:
		return None
	try:
		width, height = map(int, value.split('x'))
		return (width, height)
	except Exception as ex:
		print(repr(ex))
		raise click.BadParameter('format should be {width}x{height}')


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
	output_size: tuple[int, int],
) -> tuple[int, int]:
	"""
	Offset of the centered crop region.

	Only the crop origin is bound to the MCU (minimum coded unit) grid,
	the region size is arbitrary: the trailing partial MCUs are stored,
	yet are never shown by the decoder.

	MCU size depends on the chroma subsampling of the very file being cropped:
	8x8 for 4:4:4 and grayscale, 16x8 for 4:2:2, 16x16 for 4:2:0, 32x8 for 4:1:1.
	"""

	def align(
		image_size: int,
		output_size: int,
		grid: int,
	) -> int:
		offset = (image_size - output_size) // 2
		if offset <= 0:
			return 0
		# round to the nearest grid node, keeping the whole region inside the image
		return min(round_down(offset + grid // 2, grid), round_down(image_size - output_size, grid))

	iw, ih, subsampling, _ = get_jpegtran().decode_header(data)
	tw, th = output_size
	return (
		align(iw, tw, turbojpeg.tjMCUWidth[subsampling]),
		align(ih, th, turbojpeg.tjMCUHeight[subsampling]),
	)


def crop_jpeg_image(
	img: pil.Image.Image,
	*,
	output_size: tuple[int, int],
) -> tuple[str | io.BytesIO, tuple[int, int]]:
	"""
	Losslessly crop given jpeg image, just like `jpegtran -crop` would do.

	Returns (image data, image size) tuple, image data being either
	the untouched source path, or an in-memory jpeg file.
	"""

	iw, ih = img.size
	tw, th = output_size
	if iw <= tw and ih <= th:
		return (img.filename, img.size)

	with open(img.filename, "rb") as fobj:
		data: bytes = fobj.read()

	x, y = get_crop_offset(data, output_size=output_size)
	width: int = min(tw, iw - x)
	height: int = min(th, ih - y)

	cropped: bytes = get_jpegtran().crop_multiple(
		jpeg_buf=data,
		crop_parameters=[(
			x,        # region origin x
			y,        # region origin y
			width,    # region width
			height,   # region height
		)],
	)[0]

	return (io.BytesIO(cropped), (width, height))


@click.group()
def main():
	pass


@main.command()
@click.option("--output-size", callback=validate_format, default=None)
def convert(output_size: tuple[int, int] | None) -> None:
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
	count = 0
	for idx, path in enumerate(sorted(dir.iterdir())):
		if not is_path_valid(path):
			print(f"Skip non-jpeg file at {path}")
			continue

		img = pil.Image.open(path)
		x_dpi, y_dpi = img.info.get("dpi", (600, 600))

		data: str | io.BytesIO
		width: int
		height: int
		page_size: tuple[int, int]
		if output_size is None:
			data, (width, height) = img.filename, img.size
			page_size = img.size
		else:
			data, (width, height) = crop_jpeg_image(img, output_size=output_size)
			page_size = output_size

		# center the image on the page (matters when the image is smaller than the page)
		x: float = (page_size[0] - width) / 2
		y: float = (page_size[1] - height) / 2

		count += 1
		pdf.add_page(
			format=(page_size[0] / x_dpi, page_size[1] / y_dpi)
		)
		pdf.image(
			data,
			x=x / x_dpi,
			y=y / y_dpi,
			w=width / x_dpi,
			h=height / y_dpi,
		)
	if count:
		pdf.output("output.pdf")
	else:
		print("No pages to merge")


if __name__ == "__main__":
	main()
