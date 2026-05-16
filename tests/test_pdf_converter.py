from pathlib import Path

import pytest

from app.services import pdf_converter
from app.services.pdf_converter import PDFConversionError, convert_pdf_to_images


class FakeImage:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str, bool, int, bool]] = []

    def save(
        self,
        output_path: Path,
        format: str,
        optimize: bool,
        quality: int,
        progressive: bool,
    ) -> None:
        self.calls.append((output_path, format, optimize, quality, progressive))
        output_path.write_bytes(b"jpeg")


@pytest.mark.anyio
async def test_convert_pdf_to_images_returns_page_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_pdf = tmp_path / "sample.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\nsample")
    image_one = FakeImage()
    image_two = FakeImage()

    def fake_convert_from_path(path: str, dpi: int) -> list[FakeImage]:
        assert path == str(source_pdf)
        assert dpi == 200
        return [image_one, image_two]

    monkeypatch.setattr(pdf_converter, "convert_from_path", fake_convert_from_path)

    page_images = await convert_pdf_to_images(source_pdf, tmp_path)

    assert len(page_images) == 2
    assert page_images[0]["page_number"] == 1
    assert str(page_images[0]["image_path"]).endswith("page-1.jpg")
    assert Path(str(page_images[0]["image_path"])).exists()
    assert page_images[1]["page_number"] == 2
    assert str(page_images[1]["image_path"]).endswith("page-2.jpg")
    assert Path(str(page_images[1]["image_path"])).exists()

    first_call = image_one.calls[0]
    assert first_call[1] == "JPEG"
    assert first_call[2] is True
    assert first_call[3] == 80
    assert first_call[4] is True


@pytest.mark.anyio
async def test_convert_pdf_to_images_raises_for_missing_source(tmp_path: Path) -> None:
    missing_pdf = tmp_path / "missing.pdf"

    with pytest.raises(PDFConversionError, match="PDF file not found"):
        await convert_pdf_to_images(missing_pdf, tmp_path)

