#!/usr/bin/env python3

import io

import PIL.Image
import pytest

from dancebooks.img import Geometry, TiledGeometry, TurboJpeg


def test_geometry_parse():
	assert Geometry.parse("100x200") == Geometry(100, 200)
	assert Geometry.parse("100x200+10+20") == Geometry(100, 200, 10, 20)
	assert str(Geometry(100, 200)) == "100x200"
	assert str(Geometry(100, 200, 10, 20)) == "100x200+10+20"
	with pytest.raises(ValueError):
		Geometry.parse("100x200+10")



def test_geometry_align():
	image = Geometry(1003, 777)
	mcu = Geometry(16, 16)
	# centered: (503 // 2 + 8) // 16 * 16, (376 // 2 + 8) // 16 * 16
	assert Geometry(500, 401).align(image, mcu) == Geometry(500, 401, 256, 192)
	# requested offset is rounded down to the grid
	assert Geometry(500, 401, 100, 50).align(image, mcu) == Geometry(500, 401, 96, 48)
	# yet the region is kept inside the image
	assert Geometry(500, 401, 900, 900).align(image, mcu) == Geometry(500, 401, 496, 368)
	# region larger than the image is clipped
	assert Geometry(2000, 401).align(image, mcu) == Geometry(1003, 401, 0, 192)

def test_tiled_geometry_from_image_size():
	tiled = TiledGeometry(1000, 600, tile_size=256)
	assert (tiled.tiles_number_x, tiled.tiles_number_y) == (4, 3)
	assert str(tiled) == "1000x600"
	assert tiled.tile(0, 0) == Geometry(256, 256, 0, 0)
	# trailing tiles are partial
	assert tiled.tile(3, 2) == Geometry(232, 88, 768, 512)


def test_tiled_geometry_from_tiles_number():
	tiled = TiledGeometry.from_tiles_number(4, 3, 256, trim=True)
	assert tiled.size == (1024, 768)
	assert (tiled.tiles_number_x, tiled.tiles_number_y) == (4, 3)
	assert tiled.trim
	assert not tiled.reverse_axis_y
	assert tiled.tile(3, 2) == Geometry(256, 256, 768, 512)


@pytest.fixture(scope="module")
def turbojpeg():
	try:
		return TurboJpeg()
	except OSError:
		pytest.skip("libturbojpeg is not available")


@pytest.mark.parametrize("subsampling, mcu", [
	("4:4:4", Geometry(8, 8)),
	("4:2:2", Geometry(16, 8)),
	("4:2:0", Geometry(16, 16)),
	("gray", Geometry(8, 8)),
])
def test_turbojpeg(turbojpeg, subsampling, mcu):
	img = PIL.Image.radial_gradient("L").resize((203, 177))
	if subsampling == "gray":
		kwargs = {}
	else:
		img = PIL.Image.merge("RGB", (img, img.rotate(90), img.rotate(45)))
		kwargs = {"subsampling": subsampling}
	buf = io.BytesIO()
	img.save(buf, "JPEG", **kwargs)
	data = buf.getvalue()

	assert turbojpeg.decode_header(data) == (Geometry(203, 177), mcu)

	cropped = turbojpeg.crop(data, Geometry(100, 51, 32, 48))
	assert PIL.Image.open(io.BytesIO(cropped)).size == (100, 51)
	assert turbojpeg.decode_header(cropped) == (Geometry(100, 51), mcu)

	with pytest.raises(RuntimeError, match="multiple of"):
		turbojpeg.crop(data, Geometry(100, 51, 3, 3))


def test_turbojpeg_is_singleton(turbojpeg):
	assert TurboJpeg() is turbojpeg
