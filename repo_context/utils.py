from fnmatch import fnmatch
from pathlib import Path

from repo_context.ignore import EXTENSIONS, FILES, PATTERNS


def get_relative_path(path: Path) -> str:
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


def should_ignore(path: Path, ignore_patterns: list[str]) -> bool:
    """Check if path matches ignore patterns.

    Args:
        path (Path): Path to check against ignore patterns
        ignore_patterns (list[str]): List of ignore patterns

    Returns:
        True if path should be ignored
    """
    if not isinstance(path, Path):
        path = Path(path)

    fname = path.name
    path_str = str(path)
    relative_path = get_relative_path(path)

    for pattern in ignore_patterns:
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
