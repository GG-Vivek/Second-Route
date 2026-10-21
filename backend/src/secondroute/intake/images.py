"""The photographs (F9.3).

A photograph of a returned device carries the serial number of the device,
and often where the device was and when. That is information about a
customer's property, and it does not belong in a record of a return.

Every photograph that goes into the application is therefore decoded and
written out again without its metadata. The file that is stored has no EXIF
at all: not the camera, not the moment, not the place.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from secondroute.core.config import settings

__all__ = [
    "ImageTooLarge",
    "ImageTypeNotAllowed",
    "StoredImage",
    "store_photo",
]


class ImageTooLarge(Exception):
    """The photograph is larger than the application accepts."""


class ImageTypeNotAllowed(Exception):
    """The photograph is not one of the types the application accepts."""


@dataclass(frozen=True, slots=True)
class StoredImage:
    """A photograph that has been stored.

    Attributes:
        storage_path: The path the photograph is served from.
        exif_stripped: Always true. The file has no metadata in it.
        width: The width of the stored image, in pixels.
        height: The height of the stored image, in pixels.
        size_bytes: The size of the stored file.
        content_type: The type of the stored file.
    """

    storage_path: str
    exif_stripped: bool
    width: int
    height: int
    size_bytes: int
    content_type: str


def _upload_root() -> Path:
    """The directory the photographs are kept in."""
    return Path(settings.UPLOAD_DIR).resolve()


def _decode(content: bytes) -> Image.Image:
    """Decode the photograph, without keeping anything but the pixels."""
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageTypeNotAllowed("The file is not an image the application can read.") from exc
    return image


def store_photo(content: bytes, *, content_type: str | None = None) -> StoredImage:
    """Store a photograph without its metadata.

    The image is decoded and written out again, so that nothing about the
    camera, the moment or the place survives. The stored file is a JPEG
    unless the photograph had an alpha channel, in which case it is a PNG.

    Args:
        content: The bytes of the photograph.
        content_type: What the caller says the file is.

    Returns:
        The stored photograph.

    Raises:
        ImageTooLarge: When the photograph is larger than the limit.
        ImageTypeNotAllowed: When the photograph is not an accepted type.
    """
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise ImageTooLarge(
            f"The photograph is larger than the {settings.MAX_UPLOAD_SIZE} byte limit."
        )

    if content_type and content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise ImageTypeNotAllowed(f"{content_type} is not an accepted image type.")

    image = _decode(content)

    # A photograph with an alpha channel cannot become a JPEG, so it stays
    # a PNG. Everything else is written as a JPEG, which is smaller and
    # which every browser reads.
    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if has_alpha:
        stored_type = "image/png"
        extension = ".png"
        target_mode = "RGBA"
    else:
        stored_type = "image/jpeg"
        extension = ".jpg"
        target_mode = "RGB"

    # A palette image has to be resolved before it can be pasted.
    if image.mode == "P":
        image = image.convert("RGBA" if has_alpha else "RGB")
    elif image.mode not in ("RGB", "RGBA", "L", "LA"):
        image = image.convert("RGBA" if has_alpha else "RGB")

    # This is the point of the whole module: the image is rebuilt from its
    # pixels, so there is nowhere for the metadata to hide.
    cleaned = Image.new(target_mode, image.size)
    cleaned.paste(image)

    buffer = io.BytesIO()
    save_kwargs: dict[str, object] = {}
    if stored_type == "image/jpeg":
        save_kwargs = {"quality": 88, "optimize": True}
    cleaned.save(buffer, format="PNG" if stored_type == "image/png" else "JPEG", **save_kwargs)
    payload = buffer.getvalue()

    root = _upload_root()
    root.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{extension}"
    path = root / name
    path.write_bytes(payload)

    return StoredImage(
        storage_path=f"/uploads/{name}",
        exif_stripped=True,
        width=cleaned.width,
        height=cleaned.height,
        size_bytes=len(payload),
        content_type=stored_type,
    )
