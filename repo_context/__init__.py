import logging

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

load_dotenv()

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%d/%m/%Y-%H:%M:%S",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)

from repo_context.converter import RepoConverter  # noqa: E402
from repo_context.structure import RepoStructure  # noqa: E402

__all__ = ["RepoConverter", "RepoStructure"]
