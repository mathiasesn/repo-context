import logging
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from pathlib import Path
from urllib.parse import urlparse

from repo_context.converter import RepoConverter

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
    parser.add_argument(
        "--web",
        action="store_true",
        help="Convert a webpage instead of a repository",
    )
    args = parser.parse_args()
    return args


def main():
    # Parse arguments
    args = parse_args()

    if args.web:
        from repo_context.webpage import Webpage

        # Create the webpage converter and get markdown
        webpage = Webpage()
        context = webpage.get_markdown(args.source)

        # Get the filename from the URL
        fname = urlparse(args.source).path.strip("/").replace("/", "-")

        # Write context to file
        output_path = Path(f"{args.output}/{fname}.md")
        output_path.write_text(context)

        logger.info(f"Context written to {output_path}")
        return

    # Concat ignore patterns
    ignore_patterns = args.ignore.copy() if args.ignore else []
    if args.ignore_file:
        with open(args.ignore_file) as f:
            ignore_patterns.extend(line.strip() for line in f if line.strip())

    # Create the repo converter
    converter = RepoConverter(ignore_patterns=ignore_patterns)

    try:
        # Clone or use local repository
        if urlparse(args.source).scheme:
            logger.info(f"Cloning repository from {args.source}")
            repo_path, _ = converter.clone_repo(args.source)
            fname = Path(urlparse(args.source).path).stem
        else:
            repo_path = Path(args.source)
            fname = repo_path.stem

        # Convert repository to context
        context = converter.convert(repo_path, max_file_lines=args.max_file_lines)

        # Write context to files
        if len(context) == 1:
            output_path = Path(f"{args.output}/{fname}.md")
            output_path.write_text(context[0])
            logger.info(f"Context written to {output_path}")
        else:
            for i, c in enumerate(context):
                output_path = Path(f"{args.output}/{fname}_{i}.md")
                output_path.write_text(c)
                logger.info(f"Context written to {output_path}")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
