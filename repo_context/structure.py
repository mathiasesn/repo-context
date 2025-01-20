import logging
from pathlib import Path

from repo_context.ignore import EXTENSIONS, FILES, PATTERNS
from repo_context.utils import should_ignore

logger = logging.getLogger("repo_context.structure")


class RepoStructure:
    def __init__(self, ignore_patterns: list[str] | None = None) -> None:
        self.ignore_patterns = ignore_patterns or []
        self.ignore_patterns += FILES + EXTENSIONS + PATTERNS

    def generate_tree(
        self,
        directory: Path,
        prefix: str = "",
        is_last: bool = True,
        ignore_patterns: list[str] | None = None,
    ) -> list[str]:
        """
        Recursively generate a tree structure of the directory.

        Args:
            directory: Path object pointing to the directory
            prefix: Prefix for the current line (used for recursion)
            is_last: Boolean indicating if this is the last item in current directory
            ignore_patterns: List of patterns to ignore

        Returns:
            List[str]: Lines of the tree structure
        """
        if ignore_patterns is None:
            ignore_patterns = []

        if not directory.is_dir():
            logger.error(f"'{directory}' is not a valid directory")
            return []

        tree_lines = []
        items = [
            item
            for item in sorted(directory.iterdir())
            if not should_ignore(item.name, ignore_patterns)
        ]

        for i, item in enumerate(items):
            is_last_item = i == len(items) - 1
            connector = "??? " if is_last_item else "??? "

            tree_lines.append(f"{prefix}{connector}{item.name}")

            if item.is_dir():
                extension = "    " if is_last_item else "?   "
                tree_lines.extend(
                    self.generate_tree(
                        item,
                        prefix + extension,
                        is_last_item,
                        ignore_patterns,
                    )
                )

        return tree_lines

    def create_tree_structure(
        self,
        path: str,
        output_file: str | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        """
        Create and display/save a tree structure of the specified directory.

        Args:
            path: Path to the directory
            output_file: Optional file path to save the tree structure
            ignore_patterns: List of patterns to ignore
        """
        directory = Path(path)
        if not directory.exists():
            logger.error(f"Directory '{path}' does not exist")
            return

        logger.info(f"Generating tree structure for: {directory.absolute()}")

        tree_lines = ["Directory Structure:", directory.name]
        tree_lines.extend(
            self.generate_tree(directory, ignore_patterns=ignore_patterns or [])
        )

        # Join lines with newlines
        tree_structure = "\n".join(tree_lines)

        # Print to console
        logger.info(tree_structure)

        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            try:
                output_path.write_text(tree_structure)
                logger.info(f"Tree structure saved to: {output_path.absolute()}")
            except Exception as e:
                logger.error(f"Failed to save tree structure: {e}")
