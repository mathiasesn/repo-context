import logging
import tempfile
from fnmatch import fnmatch
from multiprocessing import Pool, cpu_count
from pathlib import Path

import git
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from repo_context.ignore import EXTENSIONS, FILES, PATTERNS

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

        self.ignore_patterns += FILES + EXTENSIONS + PATTERNS

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
        fname = path.name
        path_str = str(path)
        relative_path = self._get_relative_path(path)

        for pattern in self.ignore_patterns:
            if pattern in FILES and fname == pattern:
                return True

            if pattern in EXTENSIONS and fnmatch(fname, pattern):
                return True

            if pattern in PATTERNS:
                if pattern in path_str:
                    return True

                normalized_path = relative_path.replace("\\", "/")
                normalized_pattern = pattern.replace("\\", "/")
                if fnmatch(normalized_path, normalized_pattern):
                    return True

            if fnmatch(path_str, pattern):
                return True

        return False

    @staticmethod
    def _get_relative_path(path: Path) -> str:
        """
        Get the relative path of the given Path object with respect to the current working directory.

        Args:
            path (Path): The Path object to be converted to a relative path.

        Returns:
            str: The relative path as a string if the given path is within the current working directory,
                 otherwise the absolute path as a string.
        """
        try:
            return str(path.resolve().relative_to(Path.cwd()))
        except ValueError:
            return str(path)

    def _process_file_wrapper(self, args: tuple[str, str]) -> str | None:
        """
        Wrapper method to process a file with given file path and repository path.

        Args:
            args (tuple[str, str]): A tuple containing the file path and the repository path.

        Returns:
            str | None: The result of processing the file, or None if processing fails.
        """
        file_path, repo_path = args
        return self._process_file(Path(file_path), Path(repo_path))

    def convert(self, repo_path: Path, max_file_lines: int | None = None) -> list[str]:
        """Convert repository to LLM-friendly context format.

        Args:
            repo_path (Path): Path to repository root
            max_file_lines (int | None): Maximum number of lines in context file.
                If set, the context files will be split. Defaults to None.

        Returns:
            list[str]: List of context strings

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

        if max_file_lines:
            context = self._split_context(context, max_file_lines)
        else:
            context = ["\n".join(context)]

        return context

    def _is_valid_file(self, path: Path) -> bool:
        """Check if file should be processed."""
        return (
            path.is_file()
            and not self.should_ignore(path)
            and path.stat().st_size <= self.max_file_size
        )

    def _split_context(self, context: list[str], max_file_lines: int) -> list[str]:
        """
        Splits a list of strings into chunks where each chunk has a maximum number of lines.

        Args:
            context (list[str]): The list of strings to be split.
            max_file_lines (int): The maximum number of lines allowed in each chunk.

        Returns:
            list[str]: A list of strings where each string is a chunk of the original context,
                       and each chunk has at most `max_file_lines` lines.
        """
        if max_file_lines < 1:
            raise ValueError("max_file_lines must be greater than 0")

        chunks = []
        current_chunk = []
        current_line_count = 0

        for c in context:
            # Count lines in the current result
            result_lines = c.count("\n")

            # If adding this result would exceed the limit, start a new chunk
            if current_line_count + result_lines > max_file_lines and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_line_count = 0

            # Add the result to the current chunk
            current_chunk.append(c)
            current_line_count += result_lines

        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def _process_file(self, file_path: Path, repo_path: Path) -> str | None:
        """
        Processes a file and returns its content formatted as a string.

        This method attempts to read the content of the specified file using various encodings.
        If the file is successfully read, it returns a formatted string containing the file's
        relative path and its content. If the file is empty or cannot be decoded with any of
        the supported encodings, it returns None.

        Args:
            file_path (Path): The path to the file to be processed.
            repo_path (Path): The root path of the repository to which the file belongs.

        Returns:
            str | None: A formatted string containing the file's relative path and content,
                        or None if the file is empty or cannot be decoded.
        """
        try:
            rel_path = file_path.relative_to(repo_path)
            for encoding in ["utf-8", "latin1", "cp1252", "iso-8859-1"]:
                try:
                    content = file_path.read_text(encoding=encoding)
                    content = content.strip()
                    if not content:
                        return None

                    if self._is_binary_string(content[:1024]):
                        logger.warning(f"Skipping binary file {file_path}")
                        return None

                    if not self._is_valid_text(content):
                        logger.warning(f"Skipping non-text file {file_path}")
                        return None

                    return f"# File: {rel_path}\n```\n{content}\n```\n"
                except UnicodeDecodeError:
                    continue
            logger.warning(f"Could not decode {file_path} with any supported encoding")
            return None
        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")
            return None

    @staticmethod
    def _is_binary_string(content: str) -> bool:
        """Check if a string appears to be binary data."""
        # Check for common binary file signatures
        binary_signatures = [
            b"\x89PNG",  # PNG
            b"GIF8",  # GIF
            b"\xff\xd8",  # JPEG
            b"PK\x03\x04",  # ZIP/JAR/DOCX
            b"%PDF",  # PDF
        ]

        try:
            # Convert first few bytes to check signatures
            content_bytes = content[:8].encode("utf-8", errors="ignore")
            return any(sig in content_bytes for sig in binary_signatures)
        except Exception:
            return False

    @staticmethod
    def _is_valid_text(
        content: str,
        min_printable_ratio: float = 0.95,
        max_line_length: int = 10000,
        max_line_count: int = 100000,
    ) -> bool:
        """Validate if content appears to be legitimate text."""
        if not content.strip():
            return False

        # Check for high ratio of printable characters but allow some non-printable chars like newlines
        printable_ratio = sum(c.isprintable() or c.isspace() for c in content) / len(
            content
        )
        if printable_ratio < min_printable_ratio:
            return False

        # Check for reasonable line lengths
        line_length = max((len(line) for line in content.splitlines()), default=0)
        if line_length > max_line_length:
            return False

        # Check for reasonable number of lines
        line_count = content.count("\n")
        if line_count > max_line_count:
            return False

        return True
