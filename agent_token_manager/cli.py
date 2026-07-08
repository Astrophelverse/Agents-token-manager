"""
cli.py

Entry point installed as the "atm" command.

"atm scan <path>" walks a project, extracts every understood source file
into the generic FileUnit shapes (see shapes.py), separately picks up
Django urls.py routing info, then hands everything to render.py to produce
one compressed markdown file.

This file only wires things together. All real logic lives in scanner.py,
extractors/, django_routes.py and render.py. The only thing added here
beyond wiring is the terminal presentation, via style.py, so the command
line experience is not just a wall of plain print statements.
"""

import argparse
import os
import sys
import time

from agent_token_manager import __version__, style
from agent_token_manager.scanner import find_source_files
from agent_token_manager.extractors.registry import get_extractor_for
from agent_token_manager.django_routes import parse_django_urls
from agent_token_manager.render import render_full_document


def _estimate_tokens(char_count):
    """
    Rough token estimate using the common ~4 characters per token
    approximation. This is not exact, actual tokenizers vary, but it is
    good enough to show a meaningful before/after comparison without
    pulling in a tokenizer library as a dependency.
    """
    return max(1, round(char_count / 4))


def _original_char_count(file_units_by_path, project_root):
    """
    Sum the actual on disk byte size of every scanned source file, used as
    the "before" side of the compression ratio. We read file size directly
    rather than reconstructing from line counts, since that is a more
    honest measure of what the agent would have had to read otherwise.
    """
    total = 0
    for filepath in file_units_by_path:
        try:
            total += os.path.getsize(filepath)
        except OSError:
            pass
    return total


def _scan_command(args):
    start_time = time.time()
    project_root = os.path.abspath(args.path)

    print(style.header("agent-token-manager"))
    print()

    if not os.path.isdir(project_root):
        print(style.fail(project_root + " is not a directory"))
        return 1

    print(style.step("Scanning " + style.bold(project_root)))

    source_files = find_source_files(project_root)

    if not source_files:
        print(style.warn("No source files found for any registered language."))
        return 1

    print(style.success("Found " + str(len(source_files)) + " source file(s)"))

    print(style.step("Extracting signatures, calls and models touched ..."))
    file_units_by_path = {}
    for filepath in source_files:
        extractor = get_extractor_for(filepath)
        unit = extractor(filepath)
        if unit is not None:
            file_units_by_path[filepath] = unit
    print(style.success("Extracted " + str(len(file_units_by_path)) + " file(s)"))

    print(style.step("Looking for Django urls.py entry points ..."))
    url_infos_by_file = {}
    for current_dir, _, filenames in os.walk(project_root):
        if "urls.py" in filenames:
            urls_path = os.path.join(current_dir, "urls.py")
            url_infos_by_file[urls_path] = parse_django_urls(urls_path)
    total_routes = sum(len(v) for v in url_infos_by_file.values())
    if url_infos_by_file:
        print(style.success(str(total_routes) + " route(s) found across " + str(len(url_infos_by_file)) + " urls.py file(s)"))
    else:
        print(style.dim("  no urls.py files found"))

    print(style.step("Rendering compressed context file ..."))
    document = render_full_document(project_root, source_files, file_units_by_path, url_infos_by_file)

    output_path = os.path.join(project_root, args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(document)

    elapsed = time.time() - start_time

    original_bytes = _original_char_count(file_units_by_path, project_root)
    compressed_bytes = len(document.encode("utf-8"))

    original_tokens = _estimate_tokens(original_bytes)
    compressed_tokens = _estimate_tokens(compressed_bytes)

    if original_bytes > 0:
        reduction_percent = 100 - (compressed_bytes / original_bytes * 100)
    else:
        reduction_percent = 0

    print()
    print(style.success("Wrote " + style.bold(output_path)))
    print()
    print(style.dim("  Summary"))
    print("  " + style.kv("Files scanned", len(file_units_by_path)))
    print("  " + style.kv("Time taken", str(round(elapsed, 2)) + "s"))
    print("  " + style.kv("Original size (approx)", str(original_bytes) + " bytes / ~" + str(original_tokens) + " tokens"))
    print("  " + style.kv("Compressed size", str(compressed_bytes) + " bytes / ~" + str(compressed_tokens) + " tokens"))
    print()
    print("  " + style.bar(reduction_percent) + style.dim("  size reduction"))
    print()

    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="atm",
        description="agent-token-manager: compress a codebase into one small context file for AI coding agents",
    )
    parser.add_argument("--version", action="version", version="atm " + __version__)

    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="scan a project and write a compressed context file")
    scan_parser.add_argument("path", nargs="?", default=".", help="path to the project root (default: current directory)")
    scan_parser.add_argument("-o", "--output", default="PROJECT_CONTEXT.md", help="output filename (default: PROJECT_CONTEXT.md)")
    scan_parser.set_defaults(func=_scan_command)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not getattr(args, "command", None):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
