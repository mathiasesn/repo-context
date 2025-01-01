from pathlib import Path

import pytest

from repo_context import RepoConverter


def test_should_ignore():
    converter = RepoConverter(ignore_patterns=["*.pyc", "test/*"])
    assert converter.should_ignore(Path("file.pyc"))
    assert converter.should_ignore(Path("test/file.py"))
    assert not converter.should_ignore(Path("src/file.py"))


def test_convert(tmp_path):
    # Create test files
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    converter = RepoConverter()
    result = converter.convert(tmp_path)

    assert "# File: test.txt" in result
    assert "test content" in result
