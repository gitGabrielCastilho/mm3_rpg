from __future__ import annotations

from io import BytesIO
from typing import Tuple
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
import os


def _pil_open(file_obj) -> Image.Image:
    image = Image.open(file_obj)
    try:
        image.load()
    except Exception:
        pass
    return image


def process_image_upload(
    uploaded,
    *,
    max_bytes: int = 10 * 1024 * 1024,
    max_side: int = 4096,
) -> InMemoryUploadedFile:
    """Downscale and recompress an uploaded image to be <= max_bytes.

    Strategy:
    - Downscale if width/height exceed max_side.
    - Convert to RGB and save as JPEG with progressive+optimize.
    - Decrease quality stepwise until under size threshold; if quality gets too low,
      downscale a bit more and retry.
    """
    img = _pil_open(uploaded)

    # Downscale if huge
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / float(max(w, h))
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # Convert to RGB (drop alpha) for JPEG
    if img.mode not in ("RGB", "L"):
        # flatten alpha over white background
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

    # Iterate quality and optional downscale to fit size
    quality = 85
    min_quality = 35
    attempt = 0

    def _save_to_bytes(_img: Image.Image, q: int) -> BytesIO:
        bio = BytesIO()
        _img.save(bio, format="JPEG", quality=q, progressive=True, optimize=True)
        bio.seek(0)
        return bio

    bio = _save_to_bytes(img, quality)
    while bio.getbuffer().nbytes > max_bytes and (quality > min_quality or max(img.size) > 1200):
        attempt += 1
        if quality > min_quality:
            quality = max(min_quality, quality - 10)
        else:
            # reduce dimensions by 10% and retry from a higher quality to preserve detail
            w, h = img.size
            new_size = (max(1, int(w * 0.9)), max(1, int(h * 0.9)))
            if new_size == img.size:
                break
            img = img.resize(new_size, Image.LANCZOS)
            quality = 75
        bio = _save_to_bytes(img, quality)

    # Build an InMemoryUploadedFile
    final_name = uploaded.name
    root, _ext = os.path.splitext(final_name)
    final_name = f"{root}.jpg"
    content = bio.getvalue()
    file_obj = BytesIO(content)
    file_obj.seek(0)
    return InMemoryUploadedFile(
        file_obj,
        field_name="imagem",
        name=final_name,
        content_type="image/jpeg",
        size=len(content),
        charset=None,
    )
