"""
File processing utilities for student profile documents.
Handles PDF, DOCX, and text file extraction and cleaning.
"""

import io
import logging
import fitz  # PyMuPDF
from pypdf import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


def extract_text_from_file_content(file_content, filename):
    """
    Extract text from file content based on extension.
    Uses PyMuPDF (fitz) for PDFs which produces clean, properly formatted text.
    
    Args:
        file_content: Binary file content
        filename: Original filename with extension
        
    Returns:
        Extracted text string or None if extraction fails
    """
    try:
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_ext == 'pdf':
            return _extract_pdf_text(file_content, filename)
        elif file_ext == 'docx':
            return _extract_docx_text(file_content)
        elif file_ext in ['txt', 'text', 'md', 'csv']:
            return file_content.decode('utf-8', errors='ignore')
        else:
            # Try plain text as fallback
            return file_content.decode('utf-8', errors='ignore')
            
    except Exception as e:
        logger.error(f"[FILE_PROCESSING] Text extraction failed: {e}")
        return None


def _extract_pdf_text(file_content, filename):
    """Extract text from a PDF.

    PyMuPDF (fitz) is tried first for its high-quality layout extraction, but
    it raises on some otherwise-readable PDFs (e.g. 'code=7: cycle in
    resources', reproducible even on the latest PyMuPDF). When PyMuPDF fails or
    yields no text we fall back to pypdf, which parses those files cleanly.
    See issue #185.
    """
    text = _extract_pdf_text_pymupdf(file_content, filename)
    if text and text.strip():
        return text

    logger.warning(
        f"[PDF_EXTRACTION] PyMuPDF produced no text for {filename}; "
        f"falling back to pypdf"
    )
    return _extract_pdf_text_pypdf(file_content, filename)


def _extract_pdf_text_pymupdf(file_content, filename):
    """Extract text from PDF using PyMuPDF. Returns None on failure."""
    try:
        pdf_doc = fitz.open(stream=file_content, filetype="pdf")
        text_parts = []

        for page_num, page in enumerate(pdf_doc):
            # Extract text with proper layout preservation
            page_text = page.get_text("text")  # "text" mode preserves paragraphs
            if page_text.strip():
                text_parts.append(page_text)

        pdf_doc.close()

        # Join pages with double newlines for clear separation
        text = "\n\n".join(text_parts)

        # Clean up any remaining word-per-line formatting issues
        text = clean_extracted_text(text)

        logger.info(f"[PDF_EXTRACTION] PyMuPDF extracted {len(text)} chars from {filename}")
        return text

    except Exception as e:
        logger.error(f"[PDF_EXTRACTION] PyMuPDF failed for {filename}: {e}")
        return None


def _extract_pdf_text_pypdf(file_content, filename):
    """Fallback PDF extractor using pypdf. Returns None on failure."""
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)

        text = clean_extracted_text("\n\n".join(text_parts))

        logger.info(f"[PDF_EXTRACTION] pypdf extracted {len(text)} chars from {filename}")
        return text

    except Exception as e:
        logger.error(f"[PDF_EXTRACTION] pypdf failed for {filename}: {e}")
        return None


def _extract_docx_text(file_content):
    """Extract text from DOCX file."""
    try:
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return clean_extracted_text(text)
    except Exception as e:
        logger.error(f"[DOCX_EXTRACTION] Failed: {e}")
        return None


def clean_extracted_text(text):
    """
    Clean up PDF extraction artifacts like word-per-line formatting.
    Joins fragmented words while preserving intentional paragraph breaks.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text string
    """
    if not text:
        return text
    
    lines = text.split('\n')
    cleaned = []
    buffer = []
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            # Empty line = paragraph break
            if buffer:
                cleaned.append(' '.join(buffer))
                buffer = []
            cleaned.append('')
        elif stripped.startswith('●') or stripped.startswith('•') or stripped.startswith('-') or stripped.startswith('*'):
            # Bullet point - save buffer and start new line with bullet
            if buffer:
                cleaned.append(' '.join(buffer))
                buffer = []
            cleaned.append(stripped)
        elif len(stripped) == 1 or (len(stripped) <= 3 and stripped.isalpha()):
            # Very short word fragment - likely poorly extracted, add to buffer
            buffer.append(stripped)
        elif stripped.endswith(':') or any(stripped.lower().startswith(h) for h in ['grade', 'gpa', 'sat', 'act', 'school', 'major', 'awards', 'activities']):
            # Section header - save buffer and start new line
            if buffer:
                cleaned.append(' '.join(buffer))
                buffer = []
            cleaned.append(stripped)
        else:
            buffer.append(stripped)
    
    # Don't forget remaining buffer
    if buffer:
        cleaned.append(' '.join(buffer))
    
    # Join and clean up excessive spacing
    result = '\n'.join(cleaned)
    result = result.replace('\n\n\n', '\n\n')  # Max 2 newlines
    
    return result.strip()
