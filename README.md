# repo-context

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Quality Check](https://github.com/mathiasesn/repo-context/actions/workflows/check.yaml/badge.svg?branch=master)](https://github.com/mathiasesn/repo-context/actions/workflows/check.yaml)
[![Unit Tests](https://github.com/mathiasesn/repo-context/actions/workflows/test.yaml/badge.svg)](https://github.com/mathiasesn/repo-context/actions/workflows/test.yaml)
![code coverage](https://raw.githubusercontent.com/mathiasesn/repo-context/coverage-badge/coverage.svg?raw=true)
[![Publish](https://github.com/mathiasesn/repo-context/actions/workflows/publish.yaml/badge.svg)](https://github.com/mathiasesn/repo-context/actions/workflows/publish.yaml)

Convert Git repositories into LLM-friendly context format. This tool processes local repositories or GitHub URLs and generates a formatted file suitable for use with Large Language Models.

## Features

- Process local Git repositories or GitHub URLs
- Configurable file ignore patterns
- Progress tracking with rich console output
- Markdown-formatted output optimized for LLM context
- Built with UV package manager support

## Installation

Using UV:
```bash
uv venv
uv pip install repo-context
```

From source:
```bash
git clone https://github.com/mathiasesn/repo-context
cd repo-context
uv venv
uv pip install -e .
```

## Usage

### Command Line Interface

Basic usage:
```bash
repo-context /path/to/local/repo
repo-context https://github.com/username/repo
```

Options:
```bash
repo-context --help
usage: repo-context [-h] [--output OUTPUT] [--ignore IGNORE [IGNORE ...]] source

Convert a repository into LLM-friendly context

positional arguments:
  source                Local path or GitHub URL to repository

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output file path (default: context.md)
  --ignore IGNORE [IGNORE ...]
                        Patterns to ignore (default: ['.git', '__pycache__', '*.pyc', '*.pyo', '*.pyd', '.DS_Store'])
```

### Python API

```python
from repo-context import RepoConverter

converter = RepoConverter(ignore_patterns=[".git", "*.pyc"])
context = converter.convert("/path/to/repo")
```

## Output Format

The tool generates a Markdown file with the following structure:
````markdown
# File: path/to/file1

``` 
[file1 content]
``` 

# File: path/to/file2
``` 
[file2 content]
``` 
````

## Development

Requirements:
- Python >=3.12
- UV package manager

Setup development environment:
```bash
uv venv
uv pip install -e ".[dev]"
```

Run tests:
```bash
pytest tests/
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
