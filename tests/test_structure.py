from pathlib import Path

import pytest

from repo_context.ignore import EXTENSIONS, FILES, PATTERNS
from repo_context.structure import RepoStructure


@pytest.fixture
def temp_directory(tmp_path: Path) -> Path:
    """
    Create a temporary directory structure for testing.

    Creates:
    /temp_dir
        /folder1
            file1.txt
            file2.py
        /folder2
            /subfolder
                test.py
        test.txt
    """
    base_dir = tmp_path / "temp_dir"
    base_dir.mkdir()

    # Create folder1 with files
    folder1 = base_dir / "folder1"
    folder1.mkdir()
    (folder1 / "file1.txt").write_text("content")
    (folder1 / "file2.py").write_text("print('test')")

    # Create folder2 with subfolder
    folder2 = base_dir / "folder2"
    folder2.mkdir()
    subfolder = folder2 / "subfolder"
    subfolder.mkdir()
    (subfolder / "test.py").write_text("test content")

    # Create root level file
    (base_dir / "test.txt").write_text("root file")

    return base_dir


@pytest.fixture
def ignore_patterns():
    """Return the default ignore patterns."""
    return FILES + EXTENSIONS + PATTERNS


class TestRepoStructure:
    def test_init_default_patterns(self, ignore_patterns):
        """Test initialization with default ignore patterns."""
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        assert isinstance(rs.ignore_patterns, list)
        assert all(isinstance(pattern, str) for pattern in rs.ignore_patterns)

    def test_init_custom_patterns(self):
        """Test initialization with custom ignore patterns."""
        custom_patterns = ["*.log", "temp*"]
        rs = RepoStructure(ignore_patterns=custom_patterns)
        assert all(pattern in rs.ignore_patterns for pattern in custom_patterns)

    def test_generate_tree_invalid_directory(self, tmp_path, ignore_patterns):
        """Test generate_tree with an invalid directory."""
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        invalid_dir = tmp_path / "nonexistent"
        result = rs.generate_tree(invalid_dir)
        assert result == []

    def test_generate_tree_empty_directory(self, tmp_path, ignore_patterns):
        """Test generate_tree with an empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        result = rs.generate_tree(empty_dir)
        assert result == []

    def test_generate_tree_basic_structure(self, temp_directory, ignore_patterns):
        """Test generate_tree with a basic directory structure."""
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        tree = rs.generate_tree(temp_directory)

        # Verify expected structure
        assert any("folder1" in line for line in tree)
        assert any("folder2" in line for line in tree)
        # assert any("test.txt" in line for line in tree)

    def test_generate_tree_with_ignore_patterns(self, temp_directory):
        """Test generate_tree with custom ignore patterns."""
        ignore_patterns = ["*.txt"]
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        tree = rs.generate_tree(temp_directory)

        # Verify txt files are ignored
        assert not any(".txt" in line for line in tree)
        # Verify py files are included
        assert any(".py" in line for line in tree)

    def test_create_tree_structure_nonexistent_directory(self, ignore_patterns):
        """Test create_tree_structure with a nonexistent directory."""
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        with pytest.raises(FileNotFoundError):
            _ = rs.create_tree_structure("/nonexistent/path")

    def test_create_tree_structure_valid_directory(
        self, temp_directory, ignore_patterns
    ):
        """Test create_tree_structure with a valid directory."""
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        result = rs.create_tree_structure(str(temp_directory))

        # Verify the result is a string and contains expected content
        assert isinstance(result, str)
        assert "Directory Structure" in result
        assert temp_directory.name in result
        assert "folder1" in result
        assert "folder2" in result

    def test_create_tree_structure_with_ignore_patterns(
        self, temp_directory, ignore_patterns
    ):
        """Test create_tree_structure with custom ignore patterns."""
        ignore_patterns = ["folder1"]
        rs = RepoStructure(ignore_patterns=ignore_patterns)
        result = rs.create_tree_structure(str(temp_directory))

        # Verify folder1 is ignored but folder2 is included
        assert "folder1" not in result
        assert "folder2" in result

    @pytest.mark.parametrize(
        "prefix,is_last",
        [("", True), ("    ", False), ("???   ", True), ("?   ", False)],
    )
    def test_generate_tree_different_prefixes(self, temp_directory, prefix, is_last):
        """Test generate_tree with different prefix configurations."""
        rs = RepoStructure()
        tree = rs.generate_tree(temp_directory, prefix=prefix, is_last=is_last)
        assert len(tree) > 0
        assert all(line.startswith(prefix) for line in tree if prefix)

    def test_nested_directory_structure(self, temp_directory):
        """Test handling of deeply nested directory structures."""
        # Create a deep nested structure
        deep_dir = temp_directory / "deep1" / "deep2" / "deep3"
        deep_dir.mkdir(parents=True)
        (deep_dir / "test.txt").write_text("deep file")

        rs = RepoStructure()
        tree = rs.generate_tree(temp_directory)

        # Verify the deep structure is properly represented
        assert any("deep1" in line for line in tree)
        deep_lines = [line for line in tree if "deep" in line]
        assert len(deep_lines) >= 3  # Should have at least 3 levels

    def test_empty_ignore_patterns(self, temp_directory):
        """Test behavior with empty ignore patterns."""
        rs = RepoStructure(ignore_patterns=[])
        tree = rs.generate_tree(temp_directory)

        # Should include all files and directories
        assert any(".txt" in line for line in tree)
        assert any(".py" in line for line in tree)
        assert any("folder1" in line for line in tree)
        assert any("folder2" in line for line in tree)
