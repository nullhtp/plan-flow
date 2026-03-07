"""Content extraction from files and URLs.

Supports PDF, DOCX, TXT, and Markdown files, plus URL fetching.
Each extractor is a simple function — no classes needed (KISS).
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import httpx
import trafilatura  # pyright: ignore[reportMissingTypeStubs]

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_CONTENT_CHARS = 50_000
MIN_CONTENT_CHARS = 20
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
URL_FETCH_TIMEOUT = 15.0


@dataclass
class ExtractedContent:
    """Result of content extraction."""

    content: str
    source_type: str  # "file" or "url"
    source_name: str
    char_count: int
    truncated: bool = False


class ExtractionError(Exception):
    """Raised when content extraction fails."""


def extract_pdf(data: bytes) -> str:
    """Extract text from PDF bytes."""
    from pypdf import PdfReader  # pyright: ignore[reportMissingTypeStubs]

    reader = PdfReader(io.BytesIO(data))  # pyright: ignore[reportUnknownMemberType]
    pages: list[str] = []
    for page in reader.pages:  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        text = page.extract_text()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if text:
            pages.append(text)  # pyright: ignore[reportUnknownArgumentType]
    return "\n\n".join(pages)


def extract_docx(data: bytes) -> str:
    """Extract text from DOCX bytes."""
    from docx import Document  # pyright: ignore[reportMissingTypeStubs]

    doc = Document(io.BytesIO(data))  # pyright: ignore[reportUnknownMemberType]
    paragraphs: list[str] = []
    for para in doc.paragraphs:  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if para.text.strip():  # pyright: ignore[reportUnknownMemberType]
            paragraphs.append(para.text)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    return "\n\n".join(paragraphs)


def extract_text(data: bytes) -> str:
    """Extract text from plain text / markdown bytes."""
    return data.decode("utf-8", errors="replace")


# Map extension → extractor. Add new formats by adding entries here (Open/Closed).
EXTRACT_BY_EXT = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".txt": extract_text,
    ".md": extract_text,
}


def extract_from_file(data: bytes, filename: str) -> ExtractedContent:
    """Extract content from an uploaded file.

    Raises ExtractionError for unsupported types or size violations.
    """
    if len(data) > MAX_FILE_SIZE:
        msg = f"File exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit"
        raise ExtractionError(msg)

    ext = _get_extension(filename)
    if ext not in EXTRACT_BY_EXT:
        msg = f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        raise ExtractionError(msg)

    extractor = EXTRACT_BY_EXT[ext]
    raw_text = extractor(data)
    return _finalize(raw_text, source_type="file", source_name=filename)


async def extract_from_url(url: str) -> ExtractedContent:
    """Fetch and extract text content from a URL.

    Uses trafilatura for HTML→text (already a project dependency).
    Raises ExtractionError on fetch failures.
    """
    try:
        async with httpx.AsyncClient(timeout=URL_FETCH_TIMEOUT) as client:
            response = await client.get(
                url, follow_redirects=True, headers={"User-Agent": "PlanFlow/1.0"}
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        msg = f"URL fetch timed out after {URL_FETCH_TIMEOUT}s"
        raise ExtractionError(msg)
    except httpx.HTTPStatusError as e:
        msg = f"URL returned HTTP {e.response.status_code}"
        raise ExtractionError(msg)
    except httpx.RequestError as e:
        msg = f"Failed to fetch URL: {e}"
        raise ExtractionError(msg)

    html = response.text
    text = trafilatura.extract(html) or ""  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if not text:
        msg = "Could not extract meaningful text from the URL"
        raise ExtractionError(msg)

    return _finalize(str(text), source_type="url", source_name=url)


def _get_extension(filename: str) -> str:
    """Get lowercase file extension."""
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        return ""
    return filename[dot_idx:].lower()


def _finalize(raw_text: str, source_type: str, source_name: str) -> ExtractedContent:
    """Truncate if needed and build result."""
    text = raw_text.strip()
    if not text or len(text) < MIN_CONTENT_CHARS:
        msg = "Extracted content is too short or empty"
        raise ExtractionError(msg)

    truncated = len(text) > MAX_CONTENT_CHARS
    if truncated:
        text = text[:MAX_CONTENT_CHARS]

    return ExtractedContent(
        content=text,
        source_type=source_type,
        source_name=source_name,
        char_count=len(text),
        truncated=truncated,
    )
