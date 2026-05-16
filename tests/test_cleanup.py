import os
import time
from pathlib import Path

from app.services.cleanup import clean_temp_files


def _touch_file(path: Path, age_hours: float = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test")
    mtime = time.time() - age_hours * 3600
    os.utime(str(path), (mtime, mtime))
    os.utime(str(path.parent), (mtime, mtime))


def test_cleans_old_pdf_images_dir(tmp_path: Path) -> None:
    img_dir = tmp_path / "pdf-images-abc123"
    img_dir.mkdir(parents=True)
    _touch_file(img_dir / "page-1.jpg", age_hours=2)

    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 2
    assert not img_dir.exists()


def test_keeps_recent_pdf_images_dir(tmp_path: Path) -> None:
    img_dir = tmp_path / "pdf-images-abc123"
    img_dir.mkdir(parents=True)
    _touch_file(img_dir / "page-1.jpg", age_hours=0.1)

    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 0
    assert img_dir.exists()


def test_cleans_old_batch_pdfs(tmp_path: Path) -> None:
    batch_dir = tmp_path / "batch-abc"
    batch_dir.mkdir(parents=True)
    _touch_file(batch_dir / "doc.pdf", age_hours=2)
    _touch_file(batch_dir / "doc2.pdf", age_hours=3)

    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 3
    assert not batch_dir.exists()


def test_keeps_recent_batch_pdfs(tmp_path: Path) -> None:
    batch_dir = tmp_path / "batch-abc"
    batch_dir.mkdir(parents=True)
    _touch_file(batch_dir / "doc.pdf", age_hours=0.1)

    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 0
    assert batch_dir.exists()


def test_cleans_old_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True)
    _touch_file(export_dir / "approved_documents_20260115.xlsx", age_hours=2)

    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 2
    assert not export_dir.exists()


def test_keeps_recent_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True)
    _touch_file(export_dir / "approved_documents_20260115.xlsx", age_hours=0.1)

    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 0
    assert export_dir.exists()


def test_mixed_old_and_recent(tmp_path: Path) -> None:
    _touch_file(tmp_path / "pdf-images-old" / "img.jpg", age_hours=2)
    _touch_file(tmp_path / "pdf-images-new" / "img.jpg", age_hours=0.1)
    _touch_file(tmp_path / "batch-old" / "doc.pdf", age_hours=3)
    _touch_file(tmp_path / "batch-new" / "doc.pdf", age_hours=0.2)

    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 4


def test_handles_empty_temp_dir(tmp_path: Path) -> None:
    removed = clean_temp_files(temp_dir=str(tmp_path), max_age_hours=1)
    assert removed == 0


def test_handles_missing_temp_dir() -> None:
    removed = clean_temp_files(temp_dir="/tmp/nonexistent-cleanup-test-dir")
    assert removed == 0
