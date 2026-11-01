#!/usr/bin/env python3

import pytest

from dancebooks.img import Geometry, TiledGeometry


def test_geometry_parse():
	assert Geometry.parse("100x200") == Geometry(100, 200)
	assert Geometry.parse("100x200+10+20") == Geometry(100, 200, 10, 20)
	assert str(Geometry(100, 200)) == "100x200"
	assert str(Geometry(100, 200, 10, 20)) == "100x200+10+20"
	with pytest.raises(ValueError):
		Geometry.parse("100x200+10")


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
