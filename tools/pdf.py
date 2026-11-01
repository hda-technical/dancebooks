#!/usr/bin/env python3

import concurrent.futures
import dataclasses
import functools
import io
import logging
import pathlib
import random
import statistics
import subprocess
import sys
import tempfile
import typing

import click
import fpdf
import PIL as pil
import pypdf

from dancebooks import utils
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

		# checking every image is slow, hence a few random ones are checked
		SAMPLE_SIZE = 5

		def get_not_optimized() -> list[pathlib.Path]:
			sample = random.sample(paths, min(SAMPLE_SIZE, len(paths)))
			return sorted(p for p in sample if not _is_jpegmini_optimized(p.read_bytes()))

		if not get_not_optimized():
			raise click.ClickException(f"Images of {path} are optimized by JPEGmini already")

		# guard against accidental key presses (and unfinished JPEGmini runs)
		prompt = f"Optimize {len(paths)} images at {tmp_dir} via JPEGmini, then press any key to continue"
		while True:
			click.pause(prompt)
			not_optimized = get_not_optimized()
			if not not_optimized:
				break
			print(
				f"Some images are not optimized by JPEGmini yet, e. g. "
				f"{', '.join(p.name for p in not_optimized)}"
			)
			prompt = "Optimize them via JPEGmini, then press any key to continue"

		_assemble(paths, output)
	print(f"Saved optimized file to {output}, {path.stat().st_size} -> {output.stat().st_size} bytes")


@dataclasses.dataclass(frozen=True)
class PdfStats:
	path: pathlib.Path
	size: int
	pages: int

	@property
	def bytes_per_page(self) -> float:
		return self.size / self.pages


def _is_colored(colorspace) -> bool:
	"""
	Inline images might use abbreviated names (/RGB, /CMYK, /I),
	or refer to a named colorspace from the page resources, the latter is considered grayscale.
	"""
	colorspace = colorspace.get_object()
	if isinstance(colorspace, pypdf.generic.ArrayObject):
		family = colorspace[0]
		if family == "/ICCBased":
			return colorspace[1].get_object()["/N"] >= 3
		if family in ("/Indexed", "/I"):
			return _is_colored(colorspace[1])
		return family in ("/CalRGB", "/Lab", "/DeviceN")
	return colorspace in ("/DeviceRGB", "/DeviceCMYK", "/RGB", "/CMYK")


@dataclasses.dataclass(frozen=True)
class _Image:
	"""
	Properties of an image, either an XObject or an inline one.
	"""
	filters: list[str]
	# /ColorSpace is legitimately missing for:
	# * stencil masks (/ImageMask true, e. g. CCITT-encoded scans), painted with the current color,
	#   these are effectively 1-bit monochrome images;
	# * /JPXDecode images, which embed the colorspace into the image data.
	# Neither of these is considered colored.
	colorspace: object | None
	get_data: typing.Callable[[], bytes]

	@classmethod
	def from_settings(cls, settings, get_data: typing.Callable[[], bytes]) -> "_Image":
		"""
		Inline images use abbreviated keys (/F, /CS) and filter names (/DCT).
		"""
		filters = settings.get("/Filter", settings.get("/F", []))
		if not isinstance(filters, list):
			filters = [filters]
		return cls(
			filters=filters,
			colorspace=settings.get("/ColorSpace", settings.get("/CS")),
			get_data=get_data,
		)

	@property
	def jpeg(self) -> bool:
		return "/DCTDecode" in self.filters or "/DCT" in self.filters

	@property
	def colored(self) -> bool:
		return self.colorspace is not None and _is_colored(self.colorspace)


def _is_jpegmini_optimized(data: bytes) -> bool:
	"""
	Check if JPEGmini left its comment ("Optimized by JPEGmini {version}") in the jpeg headers.

	The whole image is searched, as it is cheap, whilst false match within
	the entropy-coded data is practically impossible.
	"""
	return data.find(b"Optimized by JPEGmini") != -1


def _find_xobject_image(resources, depth: int = 0) -> _Image | None:
	"""
	Find image XObject in the given resources,
	descending into form XObjects, as some scans wrap page images into these.
	"""
	MAX_DEPTH = 3
	if resources is None or depth > MAX_DEPTH:
		return None
	xobjects = resources.get_object().get("/XObject")
	if xobjects is None:
		return None
	forms = []
	for xobject in xobjects.get_object().values():
		xobject = xobject.get_object()
		subtype = xobject.get("/Subtype")
		if subtype == "/Image":
			# pypdf leaves DCTDecode-encoded data intact
			return _Image.from_settings(xobject, xobject.get_data)
		if subtype == "/Form":
			forms.append(xobject)
	for form in forms:
		if (image := _find_xobject_image(form.get("/Resources"), depth + 1)) is not None:
			return image
	return None


def _find_image(page: pypdf.PageObject) -> _Image | None:
	# inherited resources are copied into the page by pypdf
	if (image := _find_xobject_image(page.get("/Resources"))) is not None:
		return image

	# some scans embed images right into the page content stream (BI ... ID ... EI)
	contents = page.get_contents()
	for operands, operator in (contents.operations if contents is not None else []):
		if operator == b"INLINE IMAGE":
			data = operands["data"]
			return _Image.from_settings(operands["settings"], lambda: data)
	return None


def _get_pdf_stats(path: pathlib.Path, threshold: int | None) -> PdfStats | str | None:
	"""
	Quickly inspect the pdf file, cheapest checks going first:
	only the cross-reference table, the page tree and a single image (at the middle page) are read.

	Returns stats of colored jpeg-based files not yet optimized by JPEGmini
	(having more bytes per page than the threshold, if set), None for the others,
	or error message if the file can not be inspected.
	"""
	# errors are reported by the caller, pypdf warnings are mere noise
	logging.getLogger("pypdf").setLevel(logging.ERROR)
	try:
		size = path.stat().st_size
		# there is at least one page in the file
		if threshold is not None and size <= threshold:
			return None
		# passing file object instead of path prevents pypdf from reading the whole file into memory
		with open(path, "rb") as fobj:
			reader = pypdf.PdfReader(fobj)
			pages = len(reader.pages)
			if pages == 0:
				return "no pages"
			if threshold is not None and size / pages <= threshold:
				return None
			# covers tend to differ from the rest of the book, hence the middle page is checked,
			# no images there means a text-only (i. e. born-digital) page, nothing to optimize
			image = _find_image(reader.pages[pages // 2])
			if (
				image is None or
				not image.jpeg or
				not image.colored or
				_is_jpegmini_optimized(image.get_data())
			):
				return None
			return PdfStats(path=path, size=size, pages=pages)
	except Exception as ex:
		return repr(ex)


def _read_exceptions(path: pathlib.Path) -> set[str]:
	"""
	Read the list of filenames which are not to be optimized, one per line.

	Just like in yaml, lines starting with # are comments, blank lines (used for grouping) are ignored.
	Unlike yaml, there are no trailing comments, as # might be a part of the filename.
	"""
	result = set()
	for line in path.read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if line and not line.startswith("#"):
			result.add(line)
	return result


def _parse_threshold(ctx, param, value: str | None) -> int | None:
	"""
	click option callback, turning the option value into the size in bytes.
	"""
	if value is None:
		return None
	try:
		return utils.parse_file_size(value)
	except ValueError as ex:
		raise click.BadParameter(str(ex))


@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option(
	"--exceptions",
	type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path),
	default=pathlib.Path(__file__).resolve().parent / "exceptions.txt",
	show_default=True,
	help="File listing names of pdf files which can not be optimized, one per line, lines starting with # are comments",
)
@click.option(
	"--threshold",
	callback=_parse_threshold,
	default=None,
	help="Minimal size per page of the file to be suggested (e. g. 2MB), median one is used by default",
)
def optimize_suggest(directory: pathlib.Path, exceptions: pathlib.Path, threshold: int | None) -> None:
	"""
	Find pdf files in DIRECTORY (recursively) worth being optimized:
	colored jpeg-based files not yet optimized by JPEGmini,
	having more bytes per page than the threshold (the median one, unless set explicitly).

	Files listed in exceptions are never suggested.
	"""
	excluded = _read_exceptions(exceptions)
	paths = []
	skipped = 0
	for path in sorted(directory.rglob("*.pdf", case_sensitive=False)):
		if path.name in excluded:
			skipped += 1
			continue
		paths.append(path)
	print(f"Inspecting {len(paths)} pdf files at {directory}, skipped {skipped} excluded ones")

	candidates: list[PdfStats] = []
	get_pdf_stats = functools.partial(_get_pdf_stats, threshold=threshold)
	with concurrent.futures.ProcessPoolExecutor() as executor:
		for path, stats in zip(paths, executor.map(get_pdf_stats, paths, chunksize=16)):
			if isinstance(stats, str):
				print(f"Skip {path.relative_to(directory)}: {stats}", file=sys.stderr)
			elif stats is not None:
				candidates.append(stats)

	if threshold is None and candidates:
		threshold = statistics.median(stats.bytes_per_page for stats in candidates)
		print(
			f"Median of {len(candidates)} colored jpeg-based files not yet optimized by JPEGmini "
			f"is {utils.pretty_print_file_size(threshold)} per page"
		)
		candidates = [stats for stats in candidates if stats.bytes_per_page > threshold]
	candidates.sort(key=lambda stats: stats.bytes_per_page, reverse=True)
	print(f"Found {len(candidates)} candidates above {utils.pretty_print_file_size(threshold or 0)} per page:")
	for stats in candidates:
		print(
			f"{utils.pretty_print_file_size(stats.bytes_per_page):>10}/page "
			f"{utils.pretty_print_file_size(stats.size):>10} "
			f"{stats.pages:6d} pages  {stats.path.relative_to(directory)}"
		)


if __name__ == "__main__":
	main()
