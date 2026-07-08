"""
agent-token-manager

A CLI tool that scans a Django project using pure static analysis (the ast module)
and produces a single, structured Markdown file describing the entire codebase:
models, fields, relationships, views, urls, serializers and admin registrations.

The goal is simple: AI coding agents (Claude Code, Copilot, Codex, Cursor, etc.)
burn a lot of tokens reading raw Django files to understand a project's shape.
This tool builds that "shape" once, as clean Markdown, so the agent can read
one small file instead of dozens of large ones.

No Django import is required. No settings.py is required. It only reads text
and parses syntax trees, so it is safe to run against any Django repo, even a
broken one.
"""

__version__ = "0.1.0"
