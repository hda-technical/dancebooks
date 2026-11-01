import ctypes
import ctypes.util
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
	def parse(cls, value: str) -> Geometry:
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
	def from_click(cls, ctx, param, value: str | None) -> Geometry | None:
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

	@staticmethod
	def _align_axis(
		offset: int | None,
		region_size: int,
		image_size: int,
		grid: int,
	) -> int:
		limit = image_size - region_size
		if limit <= 0:
			return 0
		if offset is None:
			# center the region, rounding to the nearest grid node
			offset = limit // 2 + grid // 2
		# round to the grid node, keeping the whole region inside the image
		return min(offset // grid * grid, limit // grid * grid)

	def align(self, image: Geometry, grid: Geometry) -> Geometry:
		"""
		Place this region within the image of the given size,
		binding region origin to the grid nodes.

		The origin is either the requested one, or the centering one,
		the region size is clipped to the image size.
		"""
		x = self._align_axis(self.x, self.width, image.width, grid.width)
		y = self._align_axis(self.y, self.height, image.height, grid.height)
		return Geometry(
			width=min(self.width, image.width - x),
			height=min(self.height, image.height - y),
			x=x,
			y=y,
		)


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
	) -> TiledGeometry:
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


class _TJTransform(ctypes.Structure):
	"""
	tjtransform from turbojpeg.h, custom filter is never used.

	Its leading tjregion member is flattened into four ints,
	which keeps the memory layout intact.
	"""
	_fields_ = [
		("x", ctypes.c_int),
		("y", ctypes.c_int),
		("w", ctypes.c_int),
		("h", ctypes.c_int),
		("op", ctypes.c_int),
		("options", ctypes.c_int),
		("data", ctypes.c_void_p),
		("customFilter", ctypes.c_void_p),
	]


class TurboJpeg:
	"""
	Minimal ctypes binding to libturbojpeg, performing the very same lossless
	transforms the jpegtran binary does (which is a part of the same library).

	Only the classic tj* API is used: it is available since libjpeg-turbo 2.0
	and is still exported by 3.x for backward compatibility.

	The class is a singleton: the library is loaded and the transform handle
	is initialized upon the first instantiation, the handle lives as long as the process does.
	"""

	_instance: TurboJpeg | None = None

	# MCU (minimum coded unit) size per TJSAMP_* value, as in tjMCUWidth / tjMCUHeight:
	# 4:4:4, 4:2:2, 4:2:0, grayscale, 4:4:0, 4:1:1, 4:4:1
	MCU_SIZES = (
		(8, 8),
		(16, 8),
		(16, 16),
		(8, 8),
		(8, 16),
		(32, 8),
		(8, 32),
	)

	TJXOP_NONE = 0
	TJXOPT_PERFECT = 1
	TJXOPT_CROP = 4

	def __new__(cls) -> TurboJpeg:
		if cls._instance is None:
			instance = super().__new__(cls)
			instance._load()
			cls._instance = instance
		return cls._instance

	def _load(self) -> None:
		lib_path = ctypes.util.find_library("turbojpeg") or "libturbojpeg.so.0"
		lib = ctypes.CDLL(lib_path)
		c_int, c_ulong, c_void_p = ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p
		c_int_p = ctypes.POINTER(c_int)
		c_ubyte_p = ctypes.POINTER(ctypes.c_ubyte)

		lib.tjInitTransform.argtypes = []
		lib.tjInitTransform.restype = c_void_p
		lib.tjGetErrorStr2.argtypes = [c_void_p]
		lib.tjGetErrorStr2.restype = ctypes.c_char_p
		lib.tjFree.argtypes = [c_ubyte_p]
		lib.tjFree.restype = None
		# handle, jpegBuf, jpegSize, width, height, jpegSubsamp, jpegColorspace
		lib.tjDecompressHeader3.argtypes = [c_void_p, ctypes.c_char_p, c_ulong, c_int_p, c_int_p, c_int_p, c_int_p]
		lib.tjDecompressHeader3.restype = c_int
		# handle, jpegBuf, jpegSize, n, dstBufs, dstSizes, transforms, flags
		lib.tjTransform.argtypes = [
			c_void_p,
			ctypes.c_char_p,
			c_ulong,
			c_int,
			ctypes.POINTER(c_ubyte_p),
			ctypes.POINTER(c_ulong),
			ctypes.POINTER(_TJTransform),
			c_int,
		]
		lib.tjTransform.restype = c_int

		self._lib = lib
		self._handle = lib.tjInitTransform()
		if not self._handle:
			raise RuntimeError(f"tjInitTransform failed: {self._error()}")

	def _error(self) -> str:
		return self._lib.tjGetErrorStr2(self._handle).decode(errors="replace")

	def decode_header(self, data: bytes) -> tuple[Geometry, Geometry]:
		"""
		Returns (image size, MCU size) of the given jpeg image.

		MCU size depends on the chroma subsampling of the very file:
		8x8 for 4:4:4 and grayscale, 16x8 for 4:2:2, 16x16 for 4:2:0, 32x8 for 4:1:1.
		"""
		width, height, subsampling, colorspace = (ctypes.c_int() for _ in range(4))
		status = self._lib.tjDecompressHeader3(
			self._handle,
			data,
			len(data),
			ctypes.byref(width),
			ctypes.byref(height),
			ctypes.byref(subsampling),
			ctypes.byref(colorspace),
		)
		if status != 0:
			raise RuntimeError(f"tjDecompressHeader3 failed: {self._error()}")
		if not 0 <= subsampling.value < len(self.MCU_SIZES):
			raise ValueError(f"Unsupported chroma subsampling: {subsampling.value}")
		return (
			Geometry(width.value, height.value),
			Geometry(*self.MCU_SIZES[subsampling.value]),
		)

	def crop(self, data: bytes, region: Geometry) -> bytes:
		"""
		Losslessly crop the given jpeg image, just like `jpegtran -perfect -crop` does.

		Region origin has to be aligned to the MCU grid, missing origin means 0x0.
		"""
		transform = _TJTransform(
			x=region.x or 0,
			y=region.y or 0,
			w=region.width,
			h=region.height,
			op=self.TJXOP_NONE,
			options=self.TJXOPT_PERFECT | self.TJXOPT_CROP,
		)
		dst_buf = ctypes.POINTER(ctypes.c_ubyte)()
		dst_size = ctypes.c_ulong(0)
		status = self._lib.tjTransform(
			self._handle,
			data,
			len(data),
			1,
			ctypes.byref(dst_buf),
			ctypes.byref(dst_size),
			ctypes.byref(transform),
			0,
		)
		try:
			if status != 0:
				raise RuntimeError(f"tjTransform failed: {self._error()}")
			return ctypes.string_at(dst_buf, dst_size.value)
		finally:
			if dst_buf:
				self._lib.tjFree(dst_buf)
