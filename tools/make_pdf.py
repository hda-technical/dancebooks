#!/usr/bin/env python3

import pathlib

import click
import fpdf
import PIL as pil


def validate_format(ctx, param, value):
	try:
		width, height = map(int, value.split('x'))
		return (width, height)
	except:
		raise click.BadParameter('format should be {width}x{height}')
	

def add_image(pdf, path):
	img = pil.Image.open(path)
	tw, th = pdf.fw_pt, pdf.fh_pt
	iw, ih = img.size
	x = (tw - iw) // 2 
	y = (th - ih) // 2
	pdf.add_page()
	pdf.image(str(path), x=x, y=y)


@click.command()
@click.option("--output-size", callback=validate_format)
def main(output_size):
	"""
	Converts set of images from current directory into a single pdf file.
	"""
	width, height = output_size
	
	print(f"Will generate image of size {width}x{height}")
	pdf = fpdf.FPDF(unit="pt", format=(width, height))
	
	dir = pathlib.Path(".")
	for idx, path in enumerate(dir.iterdir()):
		if not path.is_file():
			print(f"Skipping non-file item at {path}")
			continue
		if path.suffix not in [".jpg"]:
			print(f"Skipping non-image file at {path}")
			continue
		print(f"Adding {path} as page #{idx:04d}")
		add_image(pdf, path)
		
	output_file = "output.pdf"
	print(f"Generating result file at {output_file}")
	pdf.output(output_file)



if __name__ == "__main__":
	main()