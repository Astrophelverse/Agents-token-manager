# agent-token-manager

A CLI tool that compresses an entire codebase into one small, structured
Markdown file: every file, every class and function signature, and what
each function calls, touches and raises. No implementation bodies. Built
so an AI coding agent can read one small file instead of the full source
tree, and still understand the whole project well enough to write new
code against it.

## Why

AI coding agents (Claude Code, Copilot, Codex, Cursor and similar tools)
often need to read many raw source files just to understand a project's
shape and how its pieces connect. That costs a lot of tokens, sometimes
hundreds of thousands for a mid sized codebase. This tool builds that
understanding once, as a single compact file.

It works with pure static analysis (Python's `ast` module today). No
imports, no settings.py, no virtualenv, no running the project at all.
Safe to run against any Python codebase, even one that is currently broken.

## Install

```bash
git clone https://github.com/yourname/agent-token-manager.git
cd agent-token-manager
./install.sh
```

or, once hosted:

```bash
curl -sSL https://raw.githubusercontent.com/yourname/agent-token-manager/main/install.sh | bash
```

## Usage

```bash
atm scan /path/to/your/project
```

Writes `PROJECT_CONTEXT.md` inside that project's root folder.

```bash
atm scan . -o CONTEXT.md
```

## What the output contains

The generated file has four sections:

1. **Project Map** - every source file found, with line counts, so an agent sees the whole project's shape before reading anything else
2. **Signatures** - every class and function, project wide, with parameters, return types and a one line docstring, no bodies
3. **Call Graph** - for every function: what it calls, which Django models it touches, and what it can raise. This is what lets an agent write new code that correctly calls into existing functions without opening the file those functions live in
4. **Entry Points** - Django `urls.py` routes mapped to the view they point to

## Architecture

This project is built so new languages can be added later without
touching the renderer or CLI:

```
agent-token-manager/
    install.sh
    pyproject.toml
    README.md
    agent_token_manager/
        __init__.py
        cli.py                  entry point, wires everything together
        scanner.py                walks the project, finds understood source files
        shapes.py                 generic, language agnostic data shapes
        django_routes.py          Django specific urls.py parsing, kept separate
        render.py                 turns shapes into the final markdown, language agnostic
        extractors/
            __init__.py
            registry.py            maps file extension to extractor function
            python_extractor.py    reads .py files via ast, produces shapes.py objects
```

The key idea: `shapes.py` defines a generic `FileUnit` / `ClassInfo` /
`FunctionInfo` structure that any language's extractor can produce.
`render.py` only ever reads those shapes, never raw source or language
specific syntax trees. Adding a new language later means writing one new
file in `extractors/` and registering its file extensions in
`extractors/registry.py`. Nothing else in the project needs to change.

Framework specific logic (like Django's routing) is kept separate from
language logic on purpose, in its own file (`django_routes.py`), so
support for other frameworks can be added the same way later without
touching the Python extractor.

**Note:** The main purpose of this repo is for Django education, use it to learn!

## License

MIT
___
*_Peace ☮️ Astrophel_*
