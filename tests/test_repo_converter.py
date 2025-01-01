import shutil
import tempfile
from pathlib import Path

import git
import pytest

from repo_context import RepoConverter


@pytest.fixture
def temp_repo():
    temp_dir = Path(tempfile.mkdtemp())
    _ = git.Repo.init(temp_dir)

    # Create test files
    (temp_dir / "test.txt").write_text("test content")
    (temp_dir / "empty.txt").write_text("")
    (temp_dir / "large.txt").write_text("x" * 2_000_000)
    (temp_dir / ".gitignore").write_text("*.ignored")
    (temp_dir / "test.ignored").write_text("ignored content")

    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def converter():
    return RepoConverter(ignore_patterns=["*.ignored"])


def test_init_default():
    converter = RepoConverter()
    assert converter.ignore_patterns == []
    assert converter.max_file_size == 1_000_000


def test_clone_repo_empty_url(converter):
    with pytest.raises(ValueError):
        converter.clone_repo("")


def test_clone_repo_invalid_url(converter):
    with pytest.raises(git.GitCommandError):
        converter.clone_repo("invalid_url")


def test_should_ignore():
    converter = RepoConverter(ignore_patterns=["*.pyc", "test/*"])
    assert converter.should_ignore(Path("file.pyc"))
    assert converter.should_ignore(Path("test/file.py"))
    assert not converter.should_ignore(Path("src/file.py"))


def test_is_valid_file(converter, temp_repo):
    assert converter._is_valid_file(temp_repo / "test.txt")
    assert not converter._is_valid_file(temp_repo / "large.txt")
    assert not converter._is_valid_file(temp_repo / "test.ignored")
    assert not converter._is_valid_file(temp_repo)


def test_process_file(converter, temp_repo):
    result = converter._process_file(temp_repo / "test.txt", temp_repo)
    assert "# File: test.txt" in result
    assert "test content" in result

    assert converter._process_file(temp_repo / "empty.txt", temp_repo) is None


def test_convert(converter, temp_repo):
    result = converter.convert(temp_repo)
    assert "test.txt" in result
    assert "test content" in result
    assert "empty.txt" not in result
    assert "large.txt" not in result
    assert "test.ignored" not in result


def test_convert_nonexistent_path(converter):
    with pytest.raises(FileNotFoundError):
        converter.convert(Path("nonexistent"))
