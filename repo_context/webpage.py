import logging
import re
from functools import lru_cache
from urllib.parse import urlparse

import requests
from markdownify import markdownify
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger("repo_context.webpage")


class Webpage:
    """A class for fetching and converting webpages to markdown format."""

    def __init__(
        self,
        timeout: int = 20,
        allowed_schemes: tuple[str] = ("http", "https"),
        max_retries: int = 3,
    ) -> None:
        self.timeout = timeout
        self.allowed_schemes = allowed_schemes
        self.max_retries = max_retries

        self.user_agent: str = "Mozilla/5.0 (compatible; WebpageFetcher/1.0)"

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def _validate_url(self, url: str) -> None:
        """Validates URL scheme and format."""
        parsed = urlparse(url)
        if parsed.scheme not in self.allowed_schemes:
            raise ValueError(f"Invalid URL scheme. Allowed: {self.allowed_schemes}")

    def _fetch_content(self, url: str) -> str:
        """Fetches webpage content with retries."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except Timeout:
                if attempt == self.max_retries - 1:
                    raise RuntimeError("Request timed out after retries")
            except RequestException as e:
                raise RuntimeError(f"Failed to fetch webpage: {e}")

    def _convert_to_markdown(self, html: str) -> str:
        """Converts HTML to clean markdown format."""
        try:
            markdown = markdownify(html).strip()
            return re.sub(r"\n{3,}", "\n\n", markdown)
        except Exception as e:
            raise RuntimeError(f"Failed to convert HTML to markdown: {e}")

    @lru_cache(maxsize=100)
    def get_markdown(self, url: str) -> str:
        """
        Fetches webpage and converts to markdown format with caching.

        Args:
            url: Webpage URL to fetch

        Returns:
            Converted markdown content

        Raises:
            WebpageError: If fetching or conversion fails
            ValueError: If URL is invalid
        """
        try:
            self._validate_url(url)
            content = self._fetch_content(url)
            return self._convert_to_markdown(content)
        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")
            raise
