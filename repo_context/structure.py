import logging
from pathlib import Path

from repo_context.utils import should_ignore

logger = logging.getLogger("repo_context.structure")


class RepoStructure:
    def __init__(self, ignore_patterns: list[str] | None = None) -> None:
        self.ignore_patterns = ignore_patterns or []

    def generate_tree(
        self,
        directory: Path,
        prefix: str = "",
        is_last: bool = True,
    ) -> list[str]:
        """
        Recursively generate a tree structure of the directory.

        Args:
            directory (Path): Path object pointing to the directory
            prefix (str): Prefix for the current line (used for recursion). default: ""
            is_last (bool): Boolean indicating if this is the last item in current directory. default: True
            ignore_patterns (list[str] | None): List of patterns to ignore. default: None

        Returns:
            list[str]: Lines of the tree structure
        """
        if not directory.is_dir():
            logger.error(f"'{directory}' is not a valid directory")
            return []

        tree_lines = []
        items = [
            item
            for item in sorted(directory.iterdir())
            if not should_ignore(item.name, self.ignore_patterns)
        ]

        for i, item in enumerate(items):
            is_last_item = i == len(items) - 1
            connector = "└── " if is_last_item else "├── "

            tree_lines.append(f"{prefix}{connector}{item.name}")

            if item.is_dir():
                extension = "    " if is_last_item else "│   "
                tree_lines.extend(
                    self.generate_tree(
                        item,
                        prefix + extension,
                        is_last_item,
                    )
                )

        return tree_lines

    def create_tree_structure(self, path: str) -> str:
        """
        Create and display/save a tree structure of the specified directory.

        Args:
            path: Path to the directory

        Returns:
            str: The tree structure
        """
        directory = Path(path)
        if not directory.exists():
            raise FileNotFoundError(f"Directory '{path}' does not exist")

        logger.info(f"Generating tree structure for: {directory.absolute()}")

        tree_lines = ["# Directory Structure", directory.name]
        tree_lines.extend(self.generate_tree(directory))

        # Join lines with newlines
        tree_structure = "\n".join(tree_lines) + "\n"

        return tree_structure
