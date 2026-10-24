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
from collections.abc import Callable
from pathlib import Path
from typing import cast

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


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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
    for _ in range(24000):
        point = (rng.randrange(_WIDTH), rng.randrange(_HEIGHT))
        red, green, blue = cast("tuple[int, int, int]", image.getpixel(point))
        noise = rng.randint(-9, 9)
        image.putpixel(
            point,
            (
                max(0, min(255, red + noise)),
                max(0, min(255, green + noise)),
                max(0, min(255, blue + noise)),
            ),
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

    # The footer is set in a smaller face, so that it stays inside the label
    # whatever the font the machine has.
    footer = _font(_FONT_CANDIDATES, 22)
    draw.text(
        (330, 512), "Model and configuration are on the box", font=footer, fill=(120, 118, 112)
    )


#: The outline of each kind of device, on the desk, in the photograph's
#: coordinates: (box, corner radius). A device is drawn as the thing it is,
#: so a refrigerator is tall and a TV is wide, rather than every device
#: being a laptop.
_SILHOUETTES: dict[str, tuple[tuple[int, int, int, int], int]] = {
    "phone": ((455, 130, 745, 770), 46),
    "tablet": ((290, 200, 910, 700), 34),
    "tv": ((150, 170, 1050, 600), 14),
    "refrigerator": ((380, 110, 820, 790), 18),
    "washer": ((300, 170, 900, 760), 26),
    "console": ((250, 370, 950, 560), 26),
    "camera": ((330, 300, 870, 640), 30),
    "mixer": ((450, 250, 750, 780), 26),
    "ac": ((150, 210, 1050, 430), 24),
    "purifier": ((430, 150, 770, 780), 46),
    "hairdryer": ((320, 300, 880, 620), 40),
}


def _glass(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int) -> None:
    """Draw a dark display with a gradient and a soft reflection."""
    _rounded(draw, box, radius, (6, 8, 14))
    left, top, right, bottom = box
    for y in range(top + 4, bottom - 4):
        fraction = (y - top) / max(1, bottom - top)
        shade = int(34 * (1 - fraction))
        draw.line([(left + 4, y), (right - 4, y)], fill=(12 + shade, 16 + shade, 26 + shade))
    # A reflection across the top third, as a real glass front would show.
    draw.polygon(
        [
            (left + 20, top + 12),
            (left + (right - left) * 0.55, top + 12),
            (left + (right - left) * 0.25, top + (bottom - top) * 0.36),
            (left + 20, top + (bottom - top) * 0.36),
        ],
        fill=(30, 34, 44),
    )


def _buttons(draw: ImageDraw.ImageDraw, centres: list[tuple[int, int]], radius: int) -> None:
    """Draw a row of buttons or knobs."""
    for cx, cy in centres:
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(56, 58, 62),
            outline=(18, 18, 20),
            width=2,
        )


def _product(
    image: Image.Image,
    category: str,
    body: tuple[int, int, int],
    angle: str,
    rng: random.Random,
) -> None:
    """Draw a device of one of the non-laptop categories, from one angle."""
    draw = ImageDraw.Draw(image)
    if category == "audio":
        _headphones(image, body, angle)
        return

    box, radius = _SILHOUETTES[category]
    _shadow(image, box, radius)
    _rounded(draw, box, radius, body, outline=(0, 0, 0))
    left, top, right, bottom = box
    width, height = right - left, bottom - top

    if category == "tv":
        stand_top = bottom
        draw.polygon(
            [(560, stand_top), (640, stand_top), (690, stand_top + 120), (510, stand_top + 120)],
            fill=(30, 30, 32),
        )
        draw.rectangle((420, stand_top + 120, 780, stand_top + 134), fill=(30, 30, 32))

    if angle == "lid":
        # The back of the device, with its mark: there is no screen to show.
        draw.ellipse(
            (
                left + width // 2 - 30,
                top + height // 2 - 30,
                left + width // 2 + 30,
                top + height // 2 + 30,
            ),
            outline=(210, 210, 214),
            width=3,
        )
        return

    if angle == "screen":
        _screen_detail(draw, category, box, rng)
        return

    if angle == "keyboard":
        _controls(draw, category, box)
        return


def _screen_detail(
    draw: ImageDraw.ImageDraw,
    category: str,
    box: tuple[int, int, int, int],
    rng: random.Random,
) -> None:
    """What a device shows when it is facing the viewer."""
    appliance = _APPLIANCE_FRONT.get(category)
    if appliance is not None:
        appliance(draw, box)
        return

    left, top, right, bottom = box
    if category == "phone":
        _glass(draw, (left + 22, top + 26, right - 22, bottom - 26), 30)
        for row in range(4):
            for column in range(3):
                x = left + 60 + column * 70
                y = top + 90 + row * 110
                _rounded(
                    draw,
                    (x, y, x + 46, y + 46),
                    10,
                    rng.choice([(90, 140, 210), (200, 120, 90), (110, 180, 130), (170, 160, 200)]),
                )
    elif category == "tablet":
        _glass(draw, (left + 30, top + 26, right - 30, bottom - 26), 20)
    elif category == "tv":
        _glass(draw, (left + 20, top + 20, right - 20, bottom - 20), 8)
    elif category == "refrigerator":
        # Two doors and their handles, the way the front of one looks.
        draw.line([(left + 6, top + 320), (right - 6, top + 320)], fill=(20, 20, 22), width=4)
        draw.rounded_rectangle(
            (right - 60, top + 90, right - 36, top + 260), radius=10, fill=(190, 192, 196)
        )
        draw.rounded_rectangle(
            (right - 60, top + 360, right - 36, top + 580), radius=10, fill=(190, 192, 196)
        )
    elif category == "washer":
        draw.ellipse(
            (left + 110, top + 130, right - 110, bottom - 130),
            fill=(20, 22, 28),
            outline=(16, 16, 18),
            width=10,
        )
        draw.ellipse((left + 150, top + 170, right - 150, bottom - 170), fill=(40, 60, 84))
    elif category == "console":
        for x in range(left + 60, right - 60, 28):
            draw.line([(x, top + 30), (x, bottom - 30)], fill=(54, 56, 60), width=6)
        draw.rectangle((left + 60, top + 8, left + 150, top + 14), fill=(60, 180, 240))
    elif category == "camera":
        draw.ellipse(
            (left + 110, top + 36, right - 110, bottom - 36),
            fill=(24, 26, 32),
            outline=(10, 10, 12),
            width=12,
        )
        draw.ellipse((left + 160, top + 86, right - 160, bottom - 86), fill=(40, 58, 92))


def _mixer_front(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The jar sitting on its base, the way the front of one looks."""
    left, top, right, bottom = box
    _rounded(
        draw,
        (left + 70, top + 30, right - 70, top + 300),
        18,
        (206, 210, 216),
        outline=(60, 62, 66),
    )
    draw.line([(left + 70, top + 170), (right - 70, top + 170)], fill=(150, 154, 160), width=3)
    _rounded(draw, (left + 40, top + 330, right - 40, bottom - 30), 24, (44, 48, 58))


def _ac_front(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The louvre the air leaves through, and the read-out beside it."""
    left, top, right, bottom = box
    draw.rectangle((left + 24, bottom - 80, right - 24, bottom - 44), fill=(34, 38, 46))
    draw.text((right - 170, top + 36), "24 C", fill=(120, 200, 255))


def _purifier_front(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The grill, in rings."""
    left, top, right, bottom = box
    cx, cy = (left + right) // 2, (top + bottom) // 2
    for radius in range(46, 150, 26):
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=(74, 78, 88),
            width=5,
        )


def _hairdryer_front(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The nozzle, seen head on."""
    left, top, right, bottom = box
    cx, cy = (left + right) // 2, (top + bottom) // 2
    draw.ellipse(
        (cx - 96, cy - 96, cx + 96, cy + 96), fill=(30, 32, 38), outline=(14, 14, 16), width=10
    )
    draw.ellipse((cx - 58, cy - 58, cx + 58, cy + 58), fill=(66, 68, 74))


#: How the front of an appliance is drawn, by category. An appliance has no
#: screen, so what it has instead is a face: a jar, a louvre, a grill.
_APPLIANCE_FRONT: dict[str, Callable[[ImageDraw.ImageDraw, tuple[int, int, int, int]], None]] = {
    "mixer": _mixer_front,
    "ac": _ac_front,
    "purifier": _purifier_front,
    "hairdryer": _hairdryer_front,
}


def _controls(draw: ImageDraw.ImageDraw, category: str, box: tuple[int, int, int, int]) -> None:
    """The buttons and ports the owner would reach for."""
    appliance = _APPLIANCE_CONTROLS.get(category)
    if appliance is not None:
        appliance(draw, box)
        return

    left, top, right, bottom = box
    if category == "phone":
        _buttons(draw, [(600, top + 60)], 22)
        draw.rectangle((left, top + 200, left + 8, top + 280), fill=(40, 40, 44))
    elif category == "tablet":
        _buttons(draw, [(left + 80, top + 60), (left + 150, top + 60)], 16)
    elif category == "tv":
        for x in range(left + 60, left + 300, 60):
            draw.rectangle((x, bottom - 60, x + 40, bottom - 34), fill=(36, 36, 40))
    elif category == "refrigerator":
        draw.rounded_rectangle(
            (left + 70, top + 40, left + 200, top + 110), radius=8, fill=(14, 20, 16)
        )
        draw.text((left + 90, top + 58), "3 C", fill=(120, 230, 150))
    elif category == "washer":
        draw.ellipse(
            (left + 60, top + 40, left + 200, top + 180),
            fill=(90, 92, 96),
            outline=(30, 30, 32),
            width=4,
        )
        _buttons(draw, [(left + 260, top + 90), (left + 330, top + 90)], 14)
    elif category == "console":
        _buttons(
            draw,
            [(left + 90, top + 95), (left + 170, top + 95), (right - 170, top + 95)],
            16,
        )
    elif category == "camera":
        _buttons(draw, [(left + 300, top + 70)], 40)
        _buttons(draw, [(right - 110, top + 70)], 22)


def _mixer_controls(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The speed dial on the base."""
    left, top, right, _bottom = box
    _buttons(draw, [(left + (right - left) // 2, top + 70)], 34)


def _ac_controls(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The display and the buttons beside it."""
    left, top, _right, _bottom = box
    draw.rectangle((left + 40, top + 30, left + 220, top + 90), fill=(18, 22, 28))
    draw.text((left + 62, top + 46), "ON", fill=(140, 220, 160))
    _buttons(draw, [(left + 300, top + 60), (left + 370, top + 60)], 16)


def _purifier_controls(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The one button on the top."""
    left, top, right, _bottom = box
    _buttons(draw, [(left + (right - left) // 2, top + 60)], 28)


def _hairdryer_controls(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The two switches on the handle."""
    left, top, _right, _bottom = box
    _buttons(draw, [(left + 120, top + 60), (left + 190, top + 60)], 16)


#: How an appliance's controls are drawn, by category.
_APPLIANCE_CONTROLS: dict[str, Callable[[ImageDraw.ImageDraw, tuple[int, int, int, int]], None]] = {
    "mixer": _mixer_controls,
    "ac": _ac_controls,
    "purifier": _purifier_controls,
    "hairdryer": _hairdryer_controls,
}


def _headphones(image: Image.Image, body: tuple[int, int, int], angle: str) -> None:
    """Draw a pair of headphones, from one angle."""
    draw = ImageDraw.Draw(image)
    _shadow(image, (260, 90, 940, 620), 60)
    draw.arc((300, 80, 900, 600), start=190, end=350, fill=body, width=34)
    for left in (250, 790):
        _rounded(draw, (left, 300, left + 160, 600), 60, body, outline=(0, 0, 0))
        if angle == "screen":
            draw.rounded_rectangle((left + 26, 340, left + 134, 560), radius=44, fill=(36, 36, 40))
        elif angle == "keyboard":
            draw.ellipse((left + 60, 380, left + 100, 420), fill=(56, 58, 62))
        elif angle == "lid":
            draw.ellipse((left + 52, 430, left + 108, 486), outline=(210, 210, 214), width=3)


def make_device_photo(
    *,
    serial: str,
    body_colour: tuple[int, int, int],
    angle: str,
    seed: int,
    category: str = "laptop",
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
        category: The kind of device, so that it is drawn as the thing it is.

    Returns:
        The bytes of a JPEG.
    """
    rng = random.Random(f"{seed}:{serial}:{angle}")
    image = _desk(rng)

    if angle == "label":
        _label(image, serial, rng)
    elif category == "laptop" or category not in _SILHOUETTES and category != "audio":
        if angle == "lid":
            _lid(image, body_colour, rng)
        elif angle == "screen":
            _screen(image, body_colour, rng)
        else:
            _keyboard(image, body_colour, rng)
    else:
        _product(image, category, body_colour, angle, rng)

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
