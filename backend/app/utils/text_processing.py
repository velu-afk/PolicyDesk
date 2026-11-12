"""
Document text extraction (PyMuPDF / pypdf + UTF-8 TXT) and overlapping semantic chunking.
Preserves page boundaries, paragraph structure, and character offsets.
"""
import io
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Primary PDF extractor: PyMuPDF (fitz) per specification; fallback: pypdf
try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    fitz = None
    HAS_PYMUPDF = False

try:
    from pypdf import PdfReader

    HAS_PYPDF = True
except ImportError:
    PdfReader = None  # type: ignore[assignment]
    HAS_PYPDF = False


class DocumentProcessingError(Exception):
    """Raised when an uploaded document is empty, corrupted, or unreadable."""


@dataclass
class ExtractedPage:
    """Represents cleaned text extracted from a single document page."""

    page_number: Optional[int]
    text: str


@dataclass
class TextChunk:
    """Represents a chunk of text ready for embedding generation and DB persistence."""

    chunk_index: int
    chunk_text: str
    page_number: Optional[int]
    metadata: Dict[str, Any]


def clean_extracted_text(raw_text: str) -> str:
    """
    Clean unnecessary whitespace while preserving meaningful paragraph and heading structure.
    - Normalizes line endings
    - Removes null bytes and non-printable control characters
    - Collapses horizontal whitespace runs into a single space
    - Preserves double newlines for paragraph boundaries
    """
    if not raw_text:
        return ""
    text = raw_text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove control characters except newline and tab
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse horizontal spaces/tabs within each line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(lines)
    # Collapse 3+ consecutive newlines to 2 newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[List[ExtractedPage], int]:
    """
    Extract text page-by-page from a PDF byte stream using PyMuPDF (fitz)
    with automatic fallback to pypdf.
    Raises DocumentProcessingError if the PDF is corrupted, encrypted, or has no extractable text.
    """
    if not file_bytes or len(file_bytes) < 8 or not file_bytes.lstrip().startswith(b"%PDF"):
        raise DocumentProcessingError(
            "Invalid or corrupted PDF file: missing valid PDF header signature."
        )

    pages: List[ExtractedPage] = []
    total_pages = 0

    if HAS_PYMUPDF and fitz is not None:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if doc.is_encrypted:
                doc.close()
                raise DocumentProcessingError("Encrypted PDF documents are not supported.")
            total_pages = len(doc)
            for idx in range(total_pages):
                page = doc.load_page(idx)
                raw_page_text = page.get_text("text") or ""
                cleaned = clean_extracted_text(raw_page_text)
                if cleaned:
                    pages.append(ExtractedPage(page_number=idx + 1, text=cleaned))
            doc.close()
        except DocumentProcessingError:
            raise
        except Exception as exc:
            raise DocumentProcessingError(f"Failed to parse PDF document: {exc}") from exc
    elif HAS_PYPDF and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            if getattr(reader, "is_encrypted", False):
                raise DocumentProcessingError("Encrypted PDF documents are not supported.")
            total_pages = len(reader.pages)
            for idx, page in enumerate(reader.pages):
                raw_page_text = page.extract_text() or ""
                cleaned = clean_extracted_text(raw_page_text)
                if cleaned:
                    pages.append(ExtractedPage(page_number=idx + 1, text=cleaned))
        except DocumentProcessingError:
            raise
        except Exception as exc:
            raise DocumentProcessingError(f"Failed to parse PDF document: {exc}") from exc
    else:
        raise DocumentProcessingError("No PDF extraction engine (PyMuPDF or pypdf) is installed.")

    if total_pages == 0 or not pages:
        raise DocumentProcessingError(
            "The uploaded PDF contains no extractable text (empty or scanned image-only PDF)."
        )

    return pages, total_pages


def extract_text_from_txt(file_bytes: bytes) -> Tuple[List[ExtractedPage], int]:
    """
    Extract and clean text from a plain text (.txt) file.
    Raises DocumentProcessingError if binary/unreadable or empty.
    """
    if not file_bytes:
        raise DocumentProcessingError("The uploaded TXT file is empty.")

    # Reject binary files masquerading as .txt
    if b"\x00" in file_bytes[:4096]:
        raise DocumentProcessingError(
            "Invalid text file: binary content detected in .txt upload."
        )

    decoded: Optional[str] = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            decoded = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded is None:
        raise DocumentProcessingError("Unable to decode text file encoding.")

    cleaned = clean_extracted_text(decoded)
    if not cleaned:
        raise DocumentProcessingError(
            "The uploaded TXT document contains only whitespace and no readable content."
        )

    return [ExtractedPage(page_number=1, text=cleaned)], 1


def create_overlapping_chunks(
    pages: List[ExtractedPage],
    filename: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[TextChunk]:
    """
    Split extracted document pages into overlapping chunks while respecting paragraph
    and sentence boundaries where possible.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        chunk_overlap = max(0, min(chunk_overlap, chunk_size // 2))

    chunks: List[TextChunk] = []
    chunk_idx = 0
    step = max(1, chunk_size - chunk_overlap)

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        text_len = len(text)
        if text_len <= chunk_size:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_idx,
                    chunk_text=text,
                    page_number=page.page_number,
                    metadata={
                        "source_filename": filename,
                        "page_number": page.page_number,
                        "char_start": 0,
                        "char_end": text_len,
                        "word_count": len(text.split()),
                    },
                )
            )
            chunk_idx += 1
            continue

        start = 0
        while start < text_len:
            end = min(start + chunk_size, text_len)
            if end < text_len:
                # Look for natural break point (paragraph, newline, sentence end, or space)
                window = text[start:end]
                best_break = -1
                for sep in ("\n\n", "\n", ". ", "; ", " "):
                    pos = window.rfind(sep)
                    if pos >= int(chunk_size * 0.55):
                        best_break = start + pos + len(sep)
                        break
                if best_break > start:
                    end = best_break

            segment = text[start:end].strip()
            if segment:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_idx,
                        chunk_text=segment,
                        page_number=page.page_number,
                        metadata={
                            "source_filename": filename,
                            "page_number": page.page_number,
                            "char_start": start,
                            "char_end": end,
                            "word_count": len(segment.split()),
                        },
                    )
                )
                chunk_idx += 1

            if end >= text_len:
                break

            next_start = end - chunk_overlap
            if next_start <= start:
                next_start = start + step
            start = next_start

    return chunks
