#!/usr/bin/env python3

import pathlib

import click
import fpdf
import PIL as pil


def validate_format(ctx, param, value):
	try:
		width, height = map(int, value.split('x'))
		return (width, height)
	except Exception as ex:
		print(repr(ex))
		raise click.BadParameter('format should be {width}x{height}')
	

def add_image(pdf, path):
	img = pil.Image.open(path)
	tw, th = pdf.fw_pt, pdf.fh_pt
	iw, ih = img.size
	x = (tw - iw) // 2 
	y = (th - ih) // 2
	pdf.add_page()
	pdf.image(str(path), x=x, y=y)


def is_path_valid(path):
	return path.is_file() and path.suffix in [".jpg"]


@click.group()
def main():
	pass


@main.command(name="map")
@click.option("--output-size", callback=validate_format)
def do_map(output_size):
	"""
	Convert set of images from current directory into a set of pdf files.
	"""
	width, height = output_size
	print(f"Will generate images of size {width}x{height}")
	
	dir = pathlib.Path(".")
	for idx, path in enumerate(dir.iterdir()):
		if not is_path_valid(path):
			print(f"Skipping non-image object at {path}")
			continue
		output_path = path.with_suffix(".pdf")
		print(f"Converting {path} to {output_path}")
		pdf = fpdf.FPDF(unit="pt", format=(width, height))
		add_image(pdf, path)
		pdf.output(output_path)
		

@main.command()
@click.option("--output-size", callback=validate_format)
def merge(output_size):
	"""
	Converts set of images from current directory into a single pdf file.
	"""
	width, height = output_size
	
	print(f"Will generate images of size {width}x{height}")
	pdf = fpdf.FPDF(unit="pt", format=(width, height))
	
	dir = pathlib.Path(".")
	for idx, path in enumerate(dir.iterdir()):
		if not is_path_valid(path):
			print(f"Skipping non-image object at {path}")
		print(f"Adding {path} as page #{idx:04d}")
		add_image(pdf, path)
		
	output_file = "output.pdf"
	print(f"Generating result file at {output_file}")
	pdf.output(output_file)



if __name__ == "__main__":
	main()