"""
Regression tests for PDF text extraction (issue #185).

Background: PyMuPDF (fitz) raises `code=7: cycle in resources` on some
otherwise-readable PDFs — reproduces even on the latest PyMuPDF. When that
happened the profile pipeline silently produced an empty profile, because no
text reached the LLM. These tests pin the fallback behaviour:

  * when PyMuPDF fails, extraction must fall back to pypdf and still return
    the document's real text, and
  * the markdown / change-eval Gemini calls must not reference the retired
    `gemini-2.0-flash-exp` model (404 NOT_FOUND).

We stub `fitz` so its `open()` raises the exact production error, and stub
`docx` (unused here), then exercise the real `file_processing` code with a
real `pypdf` install against the real fixture PDF.
"""

import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "profile-samples" / "sample-junior-comprehensive.pdf"


# --- Stub fitz to reproduce the production failure BEFORE importing the module ---
_fitz = types.ModuleType("fitz")


def _fitz_open_raises(*args, **kwargs):
    raise RuntimeError("code=7: cycle in resources")


_fitz.open = _fitz_open_raises
sys.modules["fitz"] = _fitz

# Stub python-docx (imported at module top, irrelevant to PDF tests).
_docx = types.ModuleType("docx")
_docx.Document = object
sys.modules["docx"] = _docx

import file_processing  # noqa: E402  (SOURCE_DIR placed on sys.path by conftest)


def test_pdf_extraction_falls_back_to_pypdf_when_pymupdf_fails():
    """The exact prod scenario: fitz raises 'cycle in resources' → fallback
    must still extract the real text from the fixture PDF."""
    content = FIXTURE.read_bytes()

    text = file_processing.extract_text_from_file_content(
        content, "sample-junior-comprehensive.pdf"
    )

    assert text, "extraction returned empty/None despite a readable PDF"
    assert "ALEX RIVERA" in text, f"expected student name in extracted text, got: {text[:200]!r}"
    assert len(text) > 500, f"extracted text suspiciously short ({len(text)} chars)"


def test_no_retired_gemini_model_referenced():
    """gemini-2.0-flash-exp is retired (404). No call site may reference it."""
    src = (ROOT / "cloud_functions" / "profile_manager_v2" / "profile_extraction.py").read_text()
    assert "gemini-2.0-flash-exp" not in src, (
        "profile_extraction.py still references the retired gemini-2.0-flash-exp model"
    )
