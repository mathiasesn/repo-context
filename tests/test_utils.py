import os
from pathlib import Path

import pytest

from repo_context.ignore import EXTENSIONS, FILES, PATTERNS
from repo_context.utils import get_relative_path, should_ignore


@pytest.fixture
def temp_directory(tmp_path):
    """Create a temporary directory structure for testing."""
    # Create test directory structure
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Create a subdirectory
    sub_dir = test_dir / "sub_dir"
    sub_dir.mkdir()

    # Create some test files
    (test_dir / "test_file.txt").touch()
    (sub_dir / "sub_file.txt").touch()

    return test_dir


@pytest.fixture
def change_test_dir(temp_directory):
    """Temporarily change working directory to the test directory."""
    original_dir = Path.cwd()
    os.chdir(temp_directory)
    yield temp_directory
    os.chdir(original_dir)


def test_relative_path_same_directory(change_test_dir):
    """Test getting relative path for a file in the current directory."""
    test_file = Path("test_file.txt")
    result = get_relative_path(test_file)
    assert result == "test_file.txt"


def test_relative_path_subdirectory(change_test_dir):
    """Test getting relative path for a file in a subdirectory."""
    sub_file = Path("sub_dir/sub_file.txt")
    result = get_relative_path(sub_file)
    assert result == os.path.join("sub_dir", "sub_file.txt")


def test_absolute_path_within_cwd(change_test_dir):
    """Test getting relative path from an absolute path within the working directory."""
    abs_path = (Path.cwd() / "test_file.txt").resolve()
    result = get_relative_path(abs_path)
    assert result == "test_file.txt"


def test_path_outside_cwd(temp_directory):
    """Test getting path for a location outside the working directory."""
    # Create a path that's guaranteed to be outside CWD
    outside_path = temp_directory.parent / "outside_dir" / "file.txt"
    result = get_relative_path(outside_path)
    assert result == str(outside_path)


def test_nonexistent_path_within_cwd(change_test_dir):
    """Test getting relative path for a nonexistent file within working directory."""
    nonexistent = Path("nonexistent.txt")
    result = get_relative_path(nonexistent)
    assert result == "nonexistent.txt"


def test_path_with_symlink(change_test_dir):
    """Test getting relative path with a symlink in the path."""
    # Create a symlink
    (Path.cwd() / "test_link.txt").symlink_to("test_file.txt")
    symlink_path = Path("test_link.txt")
    result = get_relative_path(symlink_path)
    assert result == "test_file.txt"


@pytest.mark.parametrize(
    "path_str",
    [
        ".",
        "..",
        "../test",
        "./test_file.txt",
    ],
)
def test_various_path_formats(change_test_dir, path_str: str):
    """Test getting relative path with various path format strings."""
    path = Path(path_str)
    result = get_relative_path(path)
    if path_str.startswith("./"):
        path_str = path_str[2:]
    assert result == path_str


def test_empty_path():
    """Test getting relative path with an empty path."""
    empty_path = Path("")
    result = get_relative_path(empty_path)
    assert result == "."


def test_relative_path_case_sensitivity(change_test_dir):
    """Test that path case is preserved in the output."""
    mixed_case = Path("Test_File.txt")
    result = get_relative_path(mixed_case)
    assert result == "Test_File.txt"


def test_should_ignore():
    ignore_patterns = EXTENSIONS + FILES + PATTERNS

    assert should_ignore(Path(".gitignore"), ignore_patterns)
    assert should_ignore(Path("some/path/.gitignore"), ignore_patterns)

    assert should_ignore(Path("image.png"), ignore_patterns)
    assert should_ignore(Path("deep/path/image.png"), ignore_patterns)

    assert should_ignore(Path(".git/config"), ignore_patterns)
    assert should_ignore(Path("some/path/.git/config"), ignore_patterns)

    assert not should_ignore(Path("regular.txt"), ignore_patterns)
    assert not should_ignore(Path("src/main.py"), ignore_patterns)


def test_should_ignore_with_ignore_patterns():
    ignore_patterns = ["*.pyc", "test/*"]
    assert should_ignore(Path("file.pyc"), ignore_patterns)
    assert should_ignore(Path("test/file.py"), ignore_patterns)
    assert not should_ignore(Path("src/file.py"), ignore_patterns)
