"""
scanner.py

Walks a project directory and finds every file that a registered extractor
can understand (see extractors/registry.py). Today that means every .py
file. Once more extractors are registered, this same function picks up
those file types automatically, with no changes needed here.

We deliberately skip common noise folders (migrations, virtual environments,
node_modules, static, build output, .git) so the scan stays fast and the
final output is not full of generated or vendored code nobody wants summarized.
"""

import os

from agent_token_manager.extractors.registry import get_extractor_for


SKIP_DIR_NAMES = {
    "migrations",
    "venv",
    ".venv",
    "env",
    "node_modules",
    ".git",
    "__pycache__",
    "static",
    "staticfiles",
    "media",
    "dist",
    "build",
    "site-packages",
    ".mypy_cache",
    ".pytest_cache",
    "htmlcov",
}


def _should_skip(dirname):
    return dirname in SKIP_DIR_NAMES or dirname.startswith(".")


def find_source_files(root_path):
    """
    Walk root_path and return every file path for which we have a
    registered extractor, sorted for stable output. This is intentionally
    not Django specific: it finds every understood source file in the
    whole project, regardless of folder layout, single file modules,
    package style modules, anything.
    """
    matches = []

    for current_dir, subdirs, filenames in os.walk(root_path):
        subdirs[:] = [d for d in subdirs if not _should_skip(d)]

        for filename in filenames:
            full_path = os.path.join(current_dir, filename)
            if get_extractor_for(full_path) is not None:
                matches.append(full_path)

    matches.sort()
    return matches


def build_folder_tree(root_path, source_files):
    """
    Build a simple, readable folder tree string covering every source file
    found, plus their line counts once available. This gives an AI agent a
    one glance map of the whole project shape before it reads anything else.

    Returns a list of (relative_path, depth) tuples in display order, which
    render.py turns into an indented tree. We keep this as plain data here,
    formatting stays entirely in render.py.
    """
    entries = []
    for filepath in source_files:
        rel_path = os.path.relpath(filepath, root_path)
        depth = rel_path.count(os.sep)
        entries.append((rel_path, depth))
    return entries
