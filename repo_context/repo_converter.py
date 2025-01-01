import logging
import tempfile
from pathlib import Path

import git
from tqdm.auto import tqdm

logger = logging.getLogger("repo-context.repo_converter")


class RepoConverter:
    def __init__(self, ignore_patterns: list[str] | None = None):
        self.ignore_patterns = ignore_patterns or []

    def clone_repo(self, url: str) -> Path:
        """Clone a repository from URL to temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        git.Repo.clone_from(url, temp_dir)
        return temp_dir

    def should_ignore(self, path: Path) -> bool:
        """Check if path matches ignore patterns."""
        from fnmatch import fnmatch

        return any(fnmatch(str(path), pattern) for pattern in self.ignore_patterns)

    def convert(self, repo_path: Path) -> str:
        """Convert repository to LLM-friendly context format."""
        context = []

        for file_path in tqdm(list(repo_path.rglob("*"))):
            if not file_path.is_file() or self.should_ignore(file_path):
                continue

            rel_path = file_path.relative_to(repo_path)
            try:
                content = file_path.read_text()
                context.append(f"# File: {rel_path}\n```\n{content}\n```\n")
            except UnicodeDecodeError:
                continue

        return "\n".join(context)
