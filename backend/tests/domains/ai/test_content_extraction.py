"""Unit tests for content extraction module."""

from __future__ import annotations

import pytest

from app.domains.ai.content_extraction import (
    ExtractionError,
    extract_from_file,
    extract_text,
)


class TestExtractText:
    def test_plain_text(self) -> None:
        data = b"Step 1: Plan the project\nStep 2: Execute"
        result = extract_text(data)
        assert "Step 1" in result
        assert "Step 2" in result

    def test_utf8_with_errors(self) -> None:
        data = b"Hello \xff world"
        result = extract_text(data)
        assert "Hello" in result


class TestExtractFromFile:
    def test_txt_file(self) -> None:
        content = "This is a plain text file with enough content to pass the minimum character requirement."
        result = extract_from_file(content.encode(), "test.txt")
        assert result.source_type == "file"
        assert result.source_name == "test.txt"
        assert result.char_count > 0

    def test_md_file(self) -> None:
        content = "# Heading\n\nThis is markdown content with enough text to pass validation minimum."
        result = extract_from_file(content.encode(), "readme.md")
        assert result.source_type == "file"
        assert "Heading" in result.content

    def test_unsupported_extension(self) -> None:
        with pytest.raises(ExtractionError, match="Unsupported file type"):
            extract_from_file(b"data", "file.exe")

    def test_empty_extension(self) -> None:
        with pytest.raises(ExtractionError, match="Unsupported file type"):
            extract_from_file(b"data", "noext")

    def test_file_too_large(self) -> None:
        large_data = b"x" * (10 * 1024 * 1024 + 1)
        with pytest.raises(ExtractionError, match="exceeds"):
            extract_from_file(large_data, "big.txt")

    def test_empty_content(self) -> None:
        with pytest.raises(ExtractionError, match="too short"):
            extract_from_file(b"", "empty.txt")

    def test_content_too_short(self) -> None:
        with pytest.raises(ExtractionError, match="too short"):
            extract_from_file(b"hi", "short.txt")

    def test_truncation(self) -> None:
        content = "a" * 60000
        result = extract_from_file(content.encode(), "large.txt")
        assert result.truncated is True
        assert result.char_count == 50000
