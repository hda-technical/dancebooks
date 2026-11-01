import dataclasses
import math
import re

import click


@dataclasses.dataclass(frozen=True)
class Geometry:
	"""
	Region size with an optional offset, spelled the ImageMagick way:
	{width}x{height} or {width}x{height}+{x}+{y}.

	Missing offset means the region is to be centered.
	"""

	width: int
	height: int
	x: int | None = None
	y: int | None = None

	REGEXP = re.compile(r"(?P<width>\d+)x(?P<height>\d+)(?:\+(?P<x>\d+)\+(?P<y>\d+))?")

	@classmethod
	def parse(cls, value: str) -> "Geometry":
		match = cls.REGEXP.fullmatch(value)
		if match is None:
			raise ValueError(f"{value} is not a valid geometry")
		width, height, x, y = match.group("width", "height", "x", "y")
		return cls(
			width=int(width),
			height=int(height),
			x=int(x) if x is not None else None,
			y=int(y) if y is not None else None,
		)

	@classmethod
	def from_click(cls, ctx, param, value: str | None) -> "Geometry | None":
		"""
		click option callback, turning the option value into a Geometry.
		"""
		if value is None:
			return None
		try:
			return cls.parse(value)
		except Exception as ex:
			print(repr(ex))
			raise click.BadParameter("geometry should be {width}x{height} or {width}x{height}+{x}+{y}")

	@property
	def size(self) -> tuple[int, int]:
		return (self.width, self.height)

	@property
	def offset(self) -> tuple[int | None, int | None]:
		return (self.x, self.y)

	def __str__(self) -> str:
		result = f"{self.width}x{self.height}"
		if self.x is not None:
			result += f"+{self.x}+{self.y}"
		return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class TiledGeometry(Geometry):
	"""
	Image of the given size, served as a grid of square tiles of tile_size.

	The trailing row and column of tiles might be partial,
	unless the image size is not known and is derived from the tiles number.
	"""

	tile_size: int
	# DeepZoom-like tilings pad every inner tile edge
	# with `overlap` pixels duplicating the neighbour tile
	overlap: int = 0
	# crop the sewn image to its non-black bounding box
	trim: bool = False
	# tiles are numbered bottom to top
	reverse_axis_y: bool = False

	@classmethod
	def from_tiles_number(
		cls,
		tiles_number_x: int,
		tiles_number_y: int,
		tile_size: int,
		**kwargs,
	) -> "TiledGeometry":
		"""
		Geometry of the image of unknown size, assuming all of its tiles are whole.
		"""
		return cls(
			tiles_number_x * tile_size,
			tiles_number_y * tile_size,
			tile_size=tile_size,
			**kwargs,
		)

	@property
	def tiles_number_x(self) -> int:
		return math.ceil(self.width / self.tile_size)

	@property
	def tiles_number_y(self) -> int:
		return math.ceil(self.height / self.tile_size)

	def tile(self, tile_x: int, tile_y: int) -> Geometry:
		"""
		Region of the image covered by the given tile (overlap excluded).
		"""
		x = tile_x * self.tile_size
		y = tile_y * self.tile_size
		return Geometry(
			width=min(self.tile_size, self.width - x),
			height=min(self.tile_size, self.height - y),
			x=x,
			y=y,
		)
