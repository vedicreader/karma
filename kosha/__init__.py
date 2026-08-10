"""kosha (कोश) — a treasury of your repo and environment context for coding agents. FTS5 + vector search + call graph, no LLMs required.

Modules:

- `kosha.cli`: Single `kosha` entry point with subcommands for shell-based harnesses. Default output is readable markdown; pass `--as-json` for JSON (piping/harnesses).
- `kosha.core`: Kosha is a tool for building a context for code generation based on your repo and environment. It uses a vector database to store code snippets and their embeddings, allowing you to search for relevant code based on natural language queries. The core functionality includes managing the database, updating package metadata, embedding code snippets, and performing context-aware searches."""

__version__ = "0.0.38"
from .core import *
from .graph import *