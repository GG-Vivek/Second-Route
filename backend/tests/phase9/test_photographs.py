"""
Tests for the photographs (F9.3).

A photograph of a returned device carries the serial number of the device
and often where the device was and when. The file that goes into the
application has none of that in it.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

from secondroute.core.config import settings


def a_photograph_with_metadata() -> bytes:
    """Return a photograph that carries a camera, a moment and a place."""
    image = Image.new("RGB", (240, 180), (40, 60, 80))
    for x in range(240):
        for y in range(180):
            image.putpixel((x, y), (40 + x // 4, 60 + y // 4, 80))

    exif = image.getexif()
    exif[0x010F] = "Secret Camera Model"  # Make
    exif[0x0110] = "Secret Lens Model"  # Model
    exif[0x9003] = "2026:10:20 09:15:00"  # DateTimeOriginal
    exif[0x0132] = "2026:10:20 09:15:00"  # DateTime

    # A place. The GPS block is the one that matters.
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (51, 30, 2136)  # 51°30'21.96"
    gps[3] = "W"
    gps[4] = (0, 0, 49376)  # 0°0'49.376"
    gps[5] = 0
    gps[6] = 3120

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


class TestStoringAPhotograph:
    """The upload endpoint."""

    @pytest.mark.asyncio
    async def test_it_stores_the_photograph(
        self, client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A photograph that is uploaded is stored and reported on."""
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

        response = await client.post(
            "/api/v1/units/photos/upload",
            files={"file": ("photo.jpg", a_photograph_with_metadata(), "image/jpeg")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["exif_stripped"] is True
        assert data["width"] == 240
        assert data["height"] == 180
        assert data["content_type"] == "image/jpeg"
        assert data["storage_path"].startswith("/uploads/")

    @pytest.mark.asyncio
    async def test_the_stored_file_has_no_metadata(
        self, client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nothing about the camera, the moment or the place survives."""
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

        response = await client.post(
            "/api/v1/units/photos/upload",
            files={"file": ("photo.jpg", a_photograph_with_metadata(), "image/jpeg")},
        )
        assert response.status_code == 201

        stored = tmp_path / response.json()["storage_path"].rsplit("/", 1)[-1]
        assert stored.exists()

        with Image.open(stored) as image:
            exif = image.getexif()
            assert not exif
            # The pixels are still there. Only the metadata went.
            assert image.size == (240, 180)
            assert image.getpixel((0, 0)) != (0, 0, 0)

    @pytest.mark.asyncio
    async def test_a_photograph_that_is_too_large_is_refused(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A photograph over the limit is refused rather than stored."""
        monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 100)

        response = await client.post(
            "/api/v1/units/photos/upload",
            files={"file": ("photo.jpg", a_photograph_with_metadata(), "image/jpeg")},
        )

        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_a_file_that_is_not_a_photograph_is_refused(
        self, client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Something that is not an image is refused."""
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

        response = await client.post(
            "/api/v1/units/photos/upload",
            files={"file": ("notes.txt", b"this is not a photograph", "text/plain")},
        )

        assert response.status_code == 415

    @pytest.mark.asyncio
    async def test_a_photograph_with_an_alpha_channel_stays_a_png(
        self, client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A transparent photograph cannot become a JPEG, so it stays a PNG."""
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

        image = Image.new("RGBA", (60, 40), (10, 20, 30, 128))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        response = await client.post(
            "/api/v1/units/photos/upload",
            files={"file": ("photo.png", buffer.getvalue(), "image/png")},
        )

        assert response.status_code == 201
        assert response.json()["content_type"] == "image/png"
