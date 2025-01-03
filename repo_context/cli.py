import logging
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from pathlib import Path
from urllib.parse import urlparse

from repo_context.repo_converter import RepoConverter

logger = logging.getLogger("repo_context.cli")


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Convert a repository into LLM-friendly context",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "source",
        type=str,
        help="Local path or GitHub URL to repository",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=".",
        help="Output directory",
    )
    parser.add_argument(
        "--ignore",
        type=str,
        nargs="+",
        help="Patterns to ignore",
    )
    parser.add_argument(
        "--ignore-file",
        type=str,
        help="File containing ignore patterns (one per line)",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=None,
        help="Maximum number of lines in context files",
    )
    args = parser.parse_args()
    return args


def main():
    # Parse arguments
    args = parse_args()

    # Concat ignore patterns
    ignore_patterns = args.ignore.copy() if args.ignore else []
    if args.ignore_file:
        with open(args.ignore_file) as f:
            ignore_patterns.extend(line.strip() for line in f if line.strip())

    # Create the repo converter
    converter = RepoConverter(ignore_patterns=ignore_patterns)

    try:
        if urlparse(args.source).scheme:
            logger.info(f"Cloning repository from {args.source}")
            repo_path, _ = converter.clone_repo(args.source)
        else:
            repo_path = Path(args.source)

        context = converter.convert(repo_path, max_file_lines=args.max_file_lines)

        for i, c in enumerate(context):
            output_path = Path(f"{args.output}/context_{i}.md")
            output_path.write_text(c)
            logger.info(f"Context written to {output_path}")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
