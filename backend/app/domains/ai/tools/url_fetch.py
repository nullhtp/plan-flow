"""URL content extraction utility and LangChain tool.

Fetches web pages and extracts readable text content using trafilatura.
Used both as a pipeline utility and as a chat tool.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import trafilatura
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; PlanFlow/1.0; +https://planflow.app)"


async def fetch_url_content(
    url: str,
    max_chars: int = 4000,
    timeout: float = 10.0,
) -> str | None:
    """Fetch a web page and extract readable text content.

    Args:
        url: The URL to fetch.
        max_chars: Maximum characters to return (truncated).
        timeout: HTTP request timeout in seconds.

    Returns:
        Extracted text content truncated to max_chars, or None on failure.
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if not content_type.startswith(
                ("text/html", "text/plain", "application/xhtml")
            ):
                logger.debug(
                    "Skipping non-HTML content type: %s for %s", content_type, url
                )
                return None

            html = response.text

        # Extract readable content using trafilatura
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )

        if not extracted:
            logger.debug("No readable content extracted from %s", url)
            return None

        # Truncate to max_chars
        if len(extracted) > max_chars:
            extracted = extracted[:max_chars] + "..."

        return extracted

    except httpx.TimeoutException:
        logger.warning("URL fetch timeout for %s", url)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP error %d fetching %s", e.response.status_code, url)
        return None
    except Exception:
        logger.warning("Failed to fetch URL %s", url, exc_info=True)
        return None


def make_fetch_url_content() -> Any:
    """Create a fetch_url_content LangChain tool for chat agents."""

    @tool
    async def fetch_page_content(url: str) -> dict[str, Any]:
        """Fetch and extract readable text content from a web page URL.

        Use this tool when you need to read the full content of a specific
        web page, for example to dive deeper into a search result.

        Args:
            url: The URL to fetch and extract content from.
        """
        content = await fetch_url_content(url)
        if content is None:
            return {
                "status": "failed",
                "error": (
                    "Unable to fetch content from this URL. "
                    "The page may be unavailable or require JavaScript to load."
                ),
            }
        return {
            "status": "executed",
            "url": url,
            "content": content,
            "chars": len(content),
        }

    return fetch_page_content
