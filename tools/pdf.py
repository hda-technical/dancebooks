#!/usr/bin/env python3

import io
import pathlib
import os
import subprocess
import sys
import tempfile

import click
import fpdf
import PIL as pil
import pypdf

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


def _assemble(
	paths: list[pathlib.Path],
	output: pathlib.Path,
	*,
	output_size: Geometry | None = None,
) -> None:
	"""
	Assemble jpeg images into a pdf file, an image per page.

	Page size is either the image size, or output_size, if the latter is set,
	the image being losslessly cropped to fit the page.
	"""
	if output_size is None:
		print("Will not change image size during generation")
	else:
		print(f"Will generate images of geometry {output_size}")

	pdf = fpdf.FPDF(unit="in")
	for idx, path in enumerate(paths):
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

		print(
			f"Page {idx + 1}: {path} ({Geometry(*img.size)}) -> {image}, "
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
	print(f"Merging {len(paths)} pages into {output}")
	pdf.output(str(output))


@main.command()
@click.option("--output-size", callback=Geometry.from_click, default=None)
def assemble(output_size: Geometry | None) -> None:
	"""
	Assemble jpeg images from current directory into output.pdf, an image per page.
	"""
	paths = []
	for path in sorted(pathlib.Path(".").iterdir()):
		if is_path_valid(path):
			paths.append(path)
		else:
			print(f"Skip non-jpeg file at {path}")

	if paths:
		_assemble(paths, pathlib.Path("output.pdf"), output_size=output_size)
	else:
		print("No pages to merge")


@main.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path))
def optimize(path: pathlib.Path) -> None:
	"""
	Re-assemble pdf file made of jpeg images (one per page) with images optimized via JPEGmini.

	The result is saved next to the source file, bearing -optimal suffix.
	"""
	output = path.with_name(f"{path.stem}-optimal.pdf")
	page_count = len(pypdf.PdfReader(path).pages)

	with tempfile.TemporaryDirectory(prefix=f"{path.stem}.", dir=path.parent) as tmp:
		tmp_dir = pathlib.Path(tmp)
		print(f"Extracting images from {path} into {tmp_dir}")
		# images are named page-{number}.{ext}, non-jpeg images are extracted in other formats
		subprocess.check_call(["pdfimages", "-j", str(path), str(tmp_dir / "page")])

		# check everything beforehand, as JPEGmini run takes quite a while
		paths = []
		for p in tmp_dir.iterdir():
			if p.suffix != ".jpg":
				raise click.ClickException(f"Only jpeg images are supported, got {p.name}")
			paths.append(p)
		if len(paths) != page_count:
			raise click.ClickException(f"Exactly one image per page is expected, got {len(paths)} images at {page_count} pages")
		# number is zero-padded to 3 digits only, hence it should be sorted numerically
		paths.sort(key=lambda p: int(p.stem.removeprefix("page-")))

		click.pause(f"Optimize {len(paths)} images at {tmp_dir} via JPEGmini, then press any key to continue")

		_assemble(paths, output)
	print(f"Saved optimized file to {output}, {path.stat().st_size} -> {output.stat().st_size} bytes")


if __name__ == "__main__":
	main()
