import shutil
import tempfile
from pathlib import Path

import git
import pytest

from repo_context import RepoConverter
from repo_context.ignore import EXTENSIONS, FILES, PATTERNS


@pytest.fixture
def temp_repo():
    temp_dir = Path(tempfile.mkdtemp())
    _ = git.Repo.init(temp_dir)

    # Create test files
    (temp_dir / "file.txt").write_text("test content")
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
    assert converter.ignore_patterns == FILES + EXTENSIONS + PATTERNS
    assert converter.max_file_size == 1_000_000


def test_clone_repo_empty_url(converter):
    with pytest.raises(ValueError):
        converter.clone_repo("")


def test_clone_repo_invalid_url(converter):
    with pytest.raises(git.GitCommandError):
        converter.clone_repo("invalid_url")


def test_should_ignore():
    converter = RepoConverter()

    assert converter.should_ignore(Path(".gitignore"))
    assert converter.should_ignore(Path("some/path/.gitignore"))

    assert converter.should_ignore(Path("image.png"))
    assert converter.should_ignore(Path("deep/path/image.png"))

    assert converter.should_ignore(Path(".git/config"))
    assert converter.should_ignore(Path("some/path/.git/config"))

    assert not converter.should_ignore(Path("regular.txt"))
    assert not converter.should_ignore(Path("src/main.py"))


def test_should_ignore_with_ignore_patterns():
    converter = RepoConverter(ignore_patterns=["*.pyc", "test/*"])
    assert converter.should_ignore(Path("file.pyc"))
    assert converter.should_ignore(Path("test/file.py"))
    assert not converter.should_ignore(Path("src/file.py"))


def test_is_valid_file(converter, temp_repo):
    assert converter._is_valid_file(temp_repo / "file.txt")
    assert not converter._is_valid_file(temp_repo / "large.txt")
    assert not converter._is_valid_file(temp_repo / "test.ignored")
    assert not converter._is_valid_file(temp_repo)


def test_process_file(converter, temp_repo):
    result = converter._process_file(temp_repo / "file.txt", temp_repo)
    assert "# File: file.txt" in result
    assert "test content" in result

    assert converter._process_file(temp_repo / "empty.txt", temp_repo) is None


def test_convert(converter, temp_repo):
    result = converter.convert(temp_repo)[0]
    assert "file.txt" in result
    assert "test content" in result
    assert "empty.txt" not in result
    assert "large.txt" not in result
    assert "test.ignored" not in result


def test_convert_nonexistent_path(converter):
    with pytest.raises(FileNotFoundError):
        converter.convert(Path("nonexistent"))


def test_empty_context(converter):
    result = converter._split_context([], 100)
    assert result == []


def test_single_chunk(converter):
    context = [
        "# File: test1.py\n```\nprint('hello')\n```\n",
        "# File: test2.py\n```\nprint('world')\n```\n",
    ]
    result = converter._split_context(context, 10)
    assert len(result) == 1
    assert result[0] == "\n".join(context)


def test_multiple_chunks(converter):
    context = [
        "# File: test1.py\n```\nline1\nline2\n```\n",  # 4 lines
        "# File: test2.py\n```\nline1\nline2\n```\n",  # 4 lines
        "# File: test3.py\n```\nline1\nline2\nline3\n```\n",  # 6 lines
    ]
    result = converter._split_context(context, 10)
    assert len(result) == 2
    # First chunk should contain first and second files (8 lines total)
    assert result[0] == "\n".join([context[0], context[1]])
    # Second chunk should contain third file (6 lines)
    assert result[1] == context[2]


def test_exact_chunk_size(converter):
    context = [
        "# File: test1.py\n```\nline1\n```\n",  # 4 lines
        "# File: test2.py\n```\nline1\n```\n",  # 4 lines
    ]
    result = converter._split_context(context, 4)
    assert len(result) == 2
    assert result[0] == context[0]
    assert result[1] == context[1]


def test_large_single_file(converter):
    large_file = "# File: large.py\n```\n" + "line\n" * 10 + "```\n"
    result = converter._split_context([large_file], 5)
    assert len(result) == 1
    assert result[0] == large_file


def test_mixed_file_sizes(converter):
    context = [
        "# File: small1.py\n```\nline1\n```\n",  # 4 lines
        "# File: large.py\n```\n" + "line\n" * 8 + "```\n",  # 11 lines
        "# File: small2.py\n```\nline1\n```\n",  # 4 lines
    ]
    result = converter._split_context(context, 6)
    assert len(result) == 3
    assert result[0] == context[0]
    assert result[1] == context[1]
    assert result[2] == context[2]


def test_zero_max_lines(converter):
    context = ["# File: test.py\n```\nline1\n```\n"]
    with pytest.raises(ValueError):
        converter._split_context(context, 0)


def test_negative_max_lines(converter):
    context = ["# File: test.py\n```\nline1\n```\n"]
    with pytest.raises(ValueError):
        converter._split_context(context, -5)


def test_newline_counting(converter):
    context = [
        "# File: test1.py\n```\nline1\r\nline2\rline3\n```\n",  # Mixed newlines
        "# File: test2.py\n```\nline1\nline2\n```\n",  # Unix newlines
    ]
    result = converter._split_context(context, 5)
    assert len(result) == 2
    assert result[0] == context[0]
    assert result[1] == context[1]


def test_preserve_file_boundaries(converter):
    context = [
        "# File: test1.py\n```\nline1\nline2\n```\n",  # 5 lines
        "# File: test2.py\n```\nline1\nline2\n```\n",  # 5 lines
        "# File: test3.py\n```\nline1\nline2\n```\n",  # 5 lines
    ]
    result = converter._split_context(context, 7)
    assert len(result) == 3
    # Each file should be in its own chunk
    assert all(chunk == original for chunk, original in zip(result, context))
