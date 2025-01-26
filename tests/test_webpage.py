from unittest.mock import Mock, patch

import pytest
from requests.exceptions import RequestException, Timeout
from repo_context.webpage import Webpage


@pytest.fixture
def webpage():
    """Base webpage instance with default settings."""
    return Webpage()


@pytest.fixture
def mock_response():
    """Mock successful response fixture."""
    response = Mock()
    response.text = "<h1>Test</h1><p>Content</p>"
    response.raise_for_status.return_value = None
    return response


class TestWebpage:
    def test_init_default_values(self):
        """Test initialization with default values."""
        webpage = Webpage()
        assert webpage.timeout == 20
        assert webpage.allowed_schemes == ("http", "https")
        assert webpage.max_retries == 3
        assert "Mozilla" in webpage.user_agent

    @pytest.mark.parametrize(
        "url,valid",
        [
            ("https://example.com", True),
            ("http://test.com", True),
            ("ftp://invalid.com", False),
            ("invalid-url", False),
        ],
    )
    def test_validate_url(self, webpage, url, valid):
        """Test URL validation with various inputs."""
        if valid:
            webpage._validate_url(url)
        else:
            with pytest.raises(ValueError):
                webpage._validate_url(url)

    @patch("requests.Session.get")
    def test_fetch_content_success(self, mock_get, webpage, mock_response):
        """Test successful content fetching."""
        mock_get.return_value = mock_response
        content = webpage._fetch_content("https://example.com")
        assert content == "<h1>Test</h1><p>Content</p>"
        mock_get.assert_called_once()

    @patch("requests.Session.get")
    def test_fetch_content_timeout_retry(self, mock_get, webpage):
        """Test timeout handling with retries."""
        mock_get.side_effect = Timeout()
        with pytest.raises(RuntimeError, match="timed out"):
            webpage._fetch_content("https://example.com")
        assert mock_get.call_count == webpage.max_retries

    @patch("requests.Session.get")
    def test_fetch_content_request_error(self, mock_get, webpage):
        """Test request exception handling."""
        mock_get.side_effect = RequestException("Network error")
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            webpage._fetch_content("https://example.com")

    def test_convert_to_markdown(self, webpage):
        """Test HTML to markdown conversion."""
        html = "<h1>Test</h1><p>Content</p>\n\n\n<p>More</p>"
        markdown = webpage._convert_to_markdown(html)
        assert "Test\n====" in markdown
        assert "\n\n\n" not in markdown

    @patch("requests.Session.get")
    def test_get_markdown_integration(self, mock_get, webpage, mock_response):
        """Test complete markdown conversion flow."""
        mock_get.return_value = mock_response
        result = webpage.get_markdown("https://example.com")
        assert "Test\n====" in result
        assert "Content" in result

    @patch("requests.Session.get")
    def test_get_markdown_caching(self, mock_get, webpage, mock_response):
        """Test LRU caching functionality."""
        mock_get.return_value = mock_response
        url = "https://example.com"

        # First call
        webpage.get_markdown(url)
        # Second call (should use cache)
        webpage.get_markdown(url)

        mock_get.assert_called_once()

    def test_custom_timeout(self):
        """Test custom timeout configuration."""
        webpage = Webpage(timeout=30)
        assert webpage.timeout == 30

    def test_custom_schemes(self):
        """Test custom allowed schemes."""
        webpage = Webpage(allowed_schemes=("https",))
        assert webpage.allowed_schemes == ("https",)
        with pytest.raises(ValueError):
            webpage._validate_url("http://example.com")
