"""Reusable PDF-to-image conversion service."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import TypeAlias

from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

PageImage: TypeAlias = dict[str, str | int]


class PDFConversionError(RuntimeError):
    """Raised when PDF-to-image conversion fails."""


async def convert_pdf_to_images(
    pdf_path: str | Path,
    temp_dir: str | Path = "temp",
) -> list[PageImage]:
    """Convert a PDF into optimized page images and return their paths."""
    input_path = Path(pdf_path)
    if not input_path.exists():
        raise PDFConversionError(f"PDF file not found: {input_path}")

    output_root = Path(temp_dir) / f"pdf-images-{uuid.uuid4().hex}"
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        return await asyncio.to_thread(
            _convert_pdf_to_images_sync,
            input_path,
            output_root,
        )
    except PDFConversionError:
        raise
    except Exception as exc:
        logger.exception("Failed to convert PDF to images")
        raise PDFConversionError("Failed to convert PDF to images") from exc


def _convert_pdf_to_images_sync(
    input_path: Path,
    output_root: Path,
) -> list[PageImage]:
    images = convert_from_path(str(input_path), dpi=200)
    page_images: list[PageImage] = []

    for page_index, image in enumerate(images, start=1):
        output_path = output_root / f"page-{page_index}.jpg"
        image.save(
            output_path,
            format="JPEG",
            optimize=True,
            quality=80,
            progressive=True,
        )
        page_images.append(
            {
                "page_number": page_index,
                "image_path": str(output_path),
            }
        )

    return page_images

