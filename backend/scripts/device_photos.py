"""
The photographs of the demonstration data (F9.3).

A returned device is photographed from four angles: the lid, the screen, the
keyboard and the label with the serial number on it. The photographs are
generated rather than taken, because there are no returned devices to
photograph, but they are generated the way a photograph is: from the pixels
up, with the light falling on them, and with the metadata that a real
camera would have put in them.

The metadata is then stripped on the way in, the same way a real photograph
is, so that the demonstration data exercises the path rather than going
around it.
"""

from __future__ import annotations

import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

__all__ = ["ANGLES", "make_device_photo"]

#: The angles a returned device is photographed from.
ANGLES = ("lid", "screen", "keyboard", "label")

_WIDTH = 1200
_HEIGHT = 900

#: The colours the desk can be.
_DESK_COLOURS = [
    (58, 52, 46),
    (44, 48, 54),
    (62, 56, 48),
    (40, 44, 42),
]

#: Where to find a font to write the serial number with.
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

_MONO_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]


def _font(paths: list[str], size: int) -> ImageFont.ImageFont:
    """Return a font, or the built-in one when there is no font to be had."""
    for path in paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
) -> None:
    """Draw a rectangle with rounded corners."""
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def _desk(rng: random.Random) -> Image.Image:
    """The surface the device is lying on."""
    base = rng.choice(_DESK_COLOURS)
    image = Image.new("RGB", (_WIDTH, _HEIGHT), base)
    draw = ImageDraw.Draw(image)

    # The light falls from one side, so the surface is not one flat colour.
    for y in range(_HEIGHT):
        shade = int(18 * (1 - y / _HEIGHT))
        draw.line(
            [(0, y), (_WIDTH, y)],
            fill=(base[0] + shade, base[1] + shade, base[2] + shade),
        )

    # A little grain, so that the surface does not look like a fill.
    pixels = image.load()
    for _ in range(24000):
        x = rng.randrange(_WIDTH)
        y = rng.randrange(_HEIGHT)
        r, g, b = pixels[x, y]
        noise = rng.randint(-9, 9)
        pixels[x, y] = (
            max(0, min(255, r + noise)),
            max(0, min(255, g + noise)),
            max(0, min(255, b + noise)),
        )

    return image


def _shadow(image: Image.Image, box: tuple[int, int, int, int], radius: int) -> None:
    """Put a soft shadow under the device."""
    shadow = Image.new("L", image.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle(box, radius=radius, fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    image.paste(Image.new("RGB", image.size, (0, 0, 0)), (0, 0), shadow)


def _lid(image: Image.Image, body: tuple[int, int, int], rng: random.Random) -> None:
    """The device, closed."""
    draw = ImageDraw.Draw(image)
    box = (250, 210, 950, 690)
    _shadow(image, box, 26)
    _rounded(draw, box, 26, body, outline=(0, 0, 0))

    # The light across the lid.
    for y in range(box[1], box[3]):
        fraction = (y - box[1]) / (box[3] - box[1])
        shade = int(26 * (1 - fraction))
        draw.line(
            [(box[0] + 2, y), (box[2] - 2, y)],
            fill=(body[0] + shade, body[1] + shade, body[2] + shade),
        )

    # The mark in the middle of the lid.
    draw.ellipse((568, 405, 632, 469), outline=(210, 210, 214), width=3)


def _screen(image: Image.Image, body: tuple[int, int, int], rng: random.Random) -> None:
    """The device, open, with the screen on."""
    draw = ImageDraw.Draw(image)
    box = (250, 170, 950, 700)
    _shadow(image, box, 18)
    _rounded(draw, box, 18, (28, 28, 30), outline=(0, 0, 0))

    inner = (272, 192, 928, 640)
    _rounded(draw, inner, 8, (0, 0, 0))

    # A desktop: a gradient with a strip of icons down one side.
    for y in range(inner[1], inner[3]):
        fraction = (y - inner[1]) / (inner[3] - inner[1])
        draw.line(
            [(inner[0], y), (inner[2], y)],
            fill=(
                int(18 + 40 * fraction),
                int(28 + 70 * fraction),
                int(64 + 90 * fraction),
            ),
        )
    for index in range(6):
        top = inner[1] + 24 + index * 56
        colour = rng.choice([(90, 140, 210), (200, 120, 90), (110, 180, 130), (170, 160, 200)])
        _rounded(draw, (inner[0] + 20, top, inner[0] + 52, top + 32), 7, colour)

    # The menu bar.
    draw.rectangle((inner[0], inner[1], inner[2], inner[1] + 22), fill=(240, 240, 244))


def _keyboard(image: Image.Image, body: tuple[int, int, int], rng: random.Random) -> None:
    """The keyboard."""
    draw = ImageDraw.Draw(image)
    box = (250, 200, 950, 700)
    _shadow(image, box, 18)
    _rounded(draw, box, 18, body, outline=(0, 0, 0))

    key_colour = (44, 44, 48)
    rows, columns = 5, 14
    left, top = 275, 230
    key_width, key_height = 45, 62
    for row in range(rows):
        for column in range(columns):
            x0 = left + column * (key_width + 7)
            y0 = top + row * (key_height + 7)
            if x0 + key_width > 925:
                continue
            _rounded(draw, (x0, y0, x0 + key_width, y0 + key_height), 6, key_colour)

    # The space bar.
    _rounded(draw, (500, 640, 700, 676), 6, key_colour)


def _label(image: Image.Image, serial: str, rng: random.Random) -> None:
    """The label with the serial number on it."""
    draw = ImageDraw.Draw(image)
    box = (300, 250, 900, 560)
    _shadow(image, box, 12)
    _rounded(draw, box, 12, (238, 236, 230), outline=(196, 194, 188))

    font = _font(_FONT_CANDIDATES, 30)
    mono = _font(_MONO_CANDIDATES, 34)

    draw.text((330, 285), "SERIAL NUMBER", font=font, fill=(96, 94, 90))
    draw.text((330, 340), serial, font=mono, fill=(28, 28, 30))

    # The barcode.
    x = 330
    while x < 870:
        width = rng.choice([3, 3, 5, 8])
        draw.rectangle((x, 410, x + width, 500), fill=(28, 28, 30))
        x += width + rng.choice([4, 5, 7])

    draw.text((330, 512), "Model and configuration are on the box", font=font, fill=(120, 118, 112))


def make_device_photo(
    *,
    serial: str,
    body_colour: tuple[int, int, int],
    angle: str,
    seed: int,
) -> bytes:
    """Return one photograph of a returned device.

    The photograph carries the metadata a real camera would have put in
    it, including a place, so that the path that strips it is exercised
    rather than skipped.

    Args:
        serial: The serial number of the device.
        body_colour: The colour of the device.
        angle: Which of the four angles this is.
        seed: The seed, so the same device always looks the same.

    Returns:
        The bytes of a JPEG.
    """
    rng = random.Random(f"{seed}:{serial}:{angle}")
    image = _desk(rng)

    if angle == "lid":
        _lid(image, body_colour, rng)
    elif angle == "screen":
        _screen(image, body_colour, rng)
    elif angle == "keyboard":
        _keyboard(image, body_colour, rng)
    else:
        _label(image, serial, rng)

    exif = image.getexif()
    exif[0x010F] = "SecondRoute Inspection Camera"
    exif[0x0110] = "SR-4 Inspection Lens"
    exif[0x0131] = "SecondRoute Inspect"
    exif[0x9003] = "2026:10:20 09:15:00"

    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (51, 30, 2136)
    gps[3] = "W"
    gps[4] = (0, 0, 49376)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, exif=exif.tobytes())
    return buffer.getvalue()


def body_colour_for(colour: str) -> tuple[int, int, int]:
    """Return the colour of a device from the name the catalogue gives it."""
    name = (colour or "").lower()
    table = {
        "space gray": (86, 88, 94),
        "graphite": (74, 74, 78),
        "silver": (196, 198, 202),
        "midnight": (26, 32, 52),
        "starlight": (226, 222, 208),
        "platinum": (206, 206, 210),
        "gold": (198, 168, 106),
        "white": (238, 238, 238),
        "black": (38, 38, 40),
    }
    for key, value in table.items():
        if key in name:
            return value
    # A colour the catalogue does not name still gets a colour.
    digest = sum(ord(character) for character in name)
    return (
        60 + (digest * 37) % 150,
        60 + (digest * 61) % 150,
        60 + (digest * 89) % 150,
    )


__all__.append("body_colour_for")
