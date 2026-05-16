import json
import os
from pathlib import Path
from unittest.mock import ANY

import pytest
from openpyxl import load_workbook

from app.services.excel_export import (
    EXPORT_FIELDS,
    HEADER_LABELS,
    ExcelExportError,
    export_approved_documents,
)

SAMPLE_DOCS = [
    {
        "document_id": "doc-1",
        "filename": "alice.pdf",
        "approved": True,
        "verified_json": {
            "candidate_name": {"value": "ALICE SMITH", "confidence": 100},
            "father_name": {"value": "JOHN SMITH", "confidence": 100},
            "aadhaar_number": {"value": "123456789012", "confidence": 100},
            "pan_number": {"value": "ABCDE1234F", "confidence": 100},
            "mobile_number": {"value": "9876543210", "confidence": 90},
            "date_of_birth": {"value": "15/01/1990", "confidence": 100},
            "address": {"value": "123 Main St, NY", "confidence": 95},
        },
    },
    {
        "document_id": "doc-2",
        "filename": "bob.pdf",
        "approved": True,
        "verified_json": {
            "candidate_name": {"value": "BOB JONES", "confidence": 100},
            "aadhaar_number": {"value": "987654321098", "confidence": 100},
            "pan_number": {"value": "XYZAB1234C", "confidence": 100},
            "date_of_birth": {"value": "20/05/1985", "confidence": 100},
        },
    },
]


def test_export_approved_documents_creates_excel_file() -> None:
    file_path = export_approved_documents(SAMPLE_DOCS)
    assert file_path is not None
    assert file_path.endswith(".xlsx")
    assert os.path.exists(file_path)

    wb = load_workbook(file_path)
    ws = wb.active
    assert ws.title == "Approved Documents"

    expected_headers = ["#", "Filename"] + [HEADER_LABELS[f] for f in EXPORT_FIELDS]
    actual_headers = [cell.value for cell in ws[1]]
    assert actual_headers == expected_headers

    assert ws.cell(row=2, column=1).value == 1
    assert ws.cell(row=2, column=2).value == "alice.pdf"
    assert ws.cell(row=2, column=3).value == "ALICE SMITH"
    assert ws.cell(row=2, column=4).value == "JOHN SMITH"
    assert ws.cell(row=2, column=5).value == "123456789012"
    assert ws.cell(row=2, column=6).value == "ABCDE1234F"
    assert ws.cell(row=2, column=7).value == "9876543210"
    assert ws.cell(row=2, column=8).value == "15/01/1990"
    assert ws.cell(row=2, column=9).value == "123 Main St, NY"

    assert ws.cell(row=3, column=1).value == 2
    assert ws.cell(row=3, column=2).value == "bob.pdf"
    assert ws.cell(row=3, column=3).value == "BOB JONES"
    assert ws.cell(row=3, column=4).value in (None, "")  # missing father_name
    assert ws.cell(row=3, column=5).value == "987654321098"
    assert ws.cell(row=3, column=6).value == "XYZAB1234C"
    assert ws.cell(row=3, column=7).value in (None, "")  # missing mobile_number
    assert ws.cell(row=3, column=8).value == "20/05/1985"
    assert ws.cell(row=3, column=9).value in (None, "")  # missing address

    os.remove(file_path)


def test_export_approved_documents_uses_extracted_json_fallback() -> None:
    docs = [
        {
            "document_id": "doc-3",
            "filename": "carol.pdf",
            "approved": True,
            "verified_json": None,
            "extracted_json": {
                "candidate_name": {"value": "CAROL WHITE", "confidence": 90},
                "father_name": {"value": "TOM WHITE", "confidence": 85},
                "aadhaar_number": {"value": "112233445566", "confidence": 80},
                "pan_number": {"value": "LMNOP1234Q", "confidence": 95},
                "date_of_birth": {"value": "10/10/1995", "confidence": 90},
            },
        }
    ]

    file_path = export_approved_documents(docs)
    wb = load_workbook(file_path)
    ws = wb.active

    assert ws.cell(row=2, column=3).value == "CAROL WHITE"
    assert ws.cell(row=2, column=4).value == "TOM WHITE"

    os.remove(file_path)


def test_export_approved_documents_empty_list_creates_header_only() -> None:
    file_path = export_approved_documents([])
    wb = load_workbook(file_path)
    ws = wb.active

    assert ws.max_row == 1
    assert ws.cell(row=1, column=1).value == "#"

    os.remove(file_path)


def test_export_column_order_matches_spec() -> None:
    expected = ["candidate_name", "father_name", "aadhaar_number", "pan_number", "mobile_number", "dob", "address"]
    assert list(EXPORT_FIELDS) == expected


def test_export_filename_includes_timestamp() -> None:
    file_path = export_approved_documents(SAMPLE_DOCS[:1])
    name = Path(file_path).name
    assert name.startswith("approved_documents_")
    assert name.endswith(".xlsx")
    assert len(name) > len("approved_documents_.xlsx")
    os.remove(file_path)
