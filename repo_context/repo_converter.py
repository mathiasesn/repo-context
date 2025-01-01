import logging
import tempfile
from fnmatch import fnmatch
from multiprocessing import Pool, cpu_count
from pathlib import Path

import git
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

logger = logging.getLogger("repo_context.repo_converter")


class RepoConverter:
    def __init__(
        self,
        ignore_patterns: list[str] | None = None,
        max_file_size: int = 1_000_000,
        max_workers: int | None = None,
    ) -> None:
        self.ignore_patterns = ignore_patterns or []
        self.max_file_size = max_file_size
        self.max_workers = max_workers or cpu_count()

    def clone_repo(self, url: str) -> Path:
        """Clone a repository from URL to temporary directory.

        Args:
            url: Repository URL to clone

        Returns:
            Tuple of (temp directory path, git repo object)

        Raises:
            git.GitCommandError: If cloning fails
            ValueError: If URL is invalid
        """
        if not url.strip():
            raise ValueError("Repository URL cannot be empty")

        # Create a temporary directory
        temp_dir = Path(tempfile.mkdtemp())

        # Create a progress bar
        progress = tqdm(
            desc="Cloning repository",
            unit="B",
            unit_scale=True,
            ncols=120,
        )

        def progress_callback(op_code, cur_count, max_count=None, message=""):
            progress.total = max_count
            progress.n = cur_count
            progress.refresh()

        # Clone the repository
        try:
            repo = git.Repo.clone_from(url, temp_dir, progress=progress_callback)
            progress.close()
            logger.info(f"Cloned repository {url} to {temp_dir}")
            return temp_dir, repo
        except git.GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise

    def should_ignore(self, path: Path) -> bool:
        """Check if path matches ignore patterns.

        Args:
            path: Path to check against ignore patterns

        Returns:
            True if path should be ignored
        """
        return any(fnmatch(str(path), pattern) for pattern in self.ignore_patterns)

    def _process_file_wrapper(self, args: tuple[str, str]) -> str | None:
        file_path, repo_path = args
        return self._process_file(Path(file_path), Path(repo_path))

    def convert(self, repo_path: Path) -> str:
        """Convert repository to LLM-friendly context format.

        Args:
            repo_path: Path to repository root

        Returns:
            Formatted string containing repository content

        Raises:
            FileNotFoundError: If repo_path doesn't exist
        """
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path {repo_path} does not exist")

        with logging_redirect_tqdm():
            file_paths = [
                (str(p), str(repo_path))
                for p in tqdm(repo_path.rglob("*"), ncols=120)
                if self._is_valid_file(p)
            ]

        context = []
        with Pool(self.max_workers) as pool:
            with logging_redirect_tqdm():
                with tqdm(
                    total=len(file_paths),
                    desc="Processing files",
                    ncols=120,
                ) as pbar:
                    for result in pool.imap_unordered(
                        self._process_file_wrapper, file_paths
                    ):
                        if result:
                            context.append(result)
                        pbar.update()

        return "\n".join(context)

    def _is_valid_file(self, path: Path) -> bool:
        """Check if file should be processed."""
        return (
            path.is_file()
            and not self.should_ignore(path)
            and path.stat().st_size <= self.max_file_size
        )

    def _process_file(self, file_path: Path, repo_path: Path) -> str | None:
        try:
            rel_path = file_path.relative_to(repo_path)
            for encoding in ["utf-8", "latin1", "cp1252", "iso-8859-1"]:
                try:
                    content = file_path.read_text(encoding=encoding)
                    return (
                        f"# File: {rel_path}\n```\n{content}\n```\n"
                        if content.strip()
                        else None
                    )
                except UnicodeDecodeError:
                    continue
            logger.warning(f"Could not decode {file_path} with any supported encoding")
            return None
        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")
            return None
