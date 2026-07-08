"""
render.py

Takes the FileUnit objects produced by the extractors (see shapes.py and
extractors/) and writes the final compressed markdown document.

This file is completely language agnostic. It never looks at raw source
code or language specific ast nodes, only at the generic FileUnit,
ClassInfo and FunctionInfo shapes. That is what lets new languages plug
in later without any changes here.

The output has four sections, in this order:

    1. Project map     one line per file, so an agent sees the whole shape
                        of the project before reading anything else
    2. Signatures       every class and function, project wide, with params,
                        return types and a one line docstring if present
    3. Call graph        for every function: what it calls, which models it
                        touches, what it can raise. This is the part that
                        lets an agent write new code against a function
                        without opening the file that function lives in
    4. Entry points     Django urls.py routes mapped to their view targets,
                        since that is usually where an agent should start
                        reading a request/response flow from
"""

from datetime import datetime


def _format_params(params):
    parts = []
    for p in params:
        piece = p.name
        if p.annotation:
            piece += ": " + p.annotation
        if p.default:
            piece += " = " + p.default
        parts.append(piece)
    return ", ".join(parts)


def _format_signature(func):
    signature = func.name + "(" + _format_params(func.params) + ")"
    if func.returns:
        signature += " -> " + func.returns
    return signature


def render_project_map(root_path, source_files, file_units_by_path):
    """
    Section 1: a compact, indented tree of every source file found, with
    line counts, so an agent can see the whole project's shape at a glance.
    """
    import os

    lines = ["## 1. Project Map", ""]
    lines.append("Root: `" + root_path + "`")
    lines.append("Total source files understood: " + str(len(source_files)))
    lines.append("")
    lines.append("```")
    for filepath in source_files:
        rel_path = os.path.relpath(filepath, root_path)
        unit = file_units_by_path.get(filepath)
        line_count = unit.line_count if unit else 0
        lines.append(rel_path + "  (" + str(line_count) + " lines)")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_signatures(root_path, source_files, file_units_by_path):
    """
    Section 2: every class and function, grouped by file, showing only
    signatures and one line docstrings. No bodies. This is the core
    compression: an agent reading this section knows exactly what exists
    and how to call it, without seeing a single line of implementation.
    """
    import os

    lines = ["## 2. Signatures", ""]

    for filepath in source_files:
        unit = file_units_by_path.get(filepath)
        if unit is None:
            continue
        if not unit.classes and not unit.functions:
            continue

        rel_path = os.path.relpath(filepath, root_path)
        lines.append("### `" + rel_path + "`")
        lines.append("")

        for cls in unit.classes:
            bases = ", ".join(cls.bases) if cls.bases else "object"
            lines.append("**class " + cls.name + "(" + bases + ")**")
            if cls.docstring:
                lines.append("_" + cls.docstring + "_")
            if cls.attributes:
                for attr in cls.attributes:
                    lines.append("- " + attr)
            for method in cls.methods:
                doc = "  # " + method.docstring if method.docstring else ""
                lines.append("- def " + _format_signature(method) + doc)
            lines.append("")

        for func in unit.functions:
            doc = "  # " + func.docstring if func.docstring else ""
            lines.append("def " + _format_signature(func) + doc)
        if unit.functions:
            lines.append("")

    return "\n".join(lines)


def render_call_graph(root_path, source_files, file_units_by_path):
    """
    Section 3: for every function or method that calls something, touches
    a model, or can raise an exception, list those effects. Functions with
    none of that (pure signature, no notable body content) are skipped here
    to keep this section focused only on things worth knowing.
    """
    import os

    lines = ["## 3. Call Graph", ""]
    lines.append("What each function calls, which models it touches, and what it can raise.")
    lines.append("")

    any_content = False

    for filepath in source_files:
        unit = file_units_by_path.get(filepath)
        if unit is None:
            continue

        all_functions = list(unit.functions)
        for cls in unit.classes:
            all_functions.extend(cls.methods)

        interesting = [f for f in all_functions if f.calls or f.touches or f.raises]
        if not interesting:
            continue

        any_content = True
        rel_path = os.path.relpath(filepath, root_path)
        lines.append("### `" + rel_path + "`")
        lines.append("")

        for func in interesting:
            lines.append("**" + func.name + "**")
            if func.touches:
                lines.append("- touches models: " + ", ".join(func.touches))
            if func.calls:
                shown = func.calls[:8]
                extra = len(func.calls) - len(shown)
                call_line = "- calls: " + ", ".join(shown)
                if extra > 0:
                    call_line += " (+" + str(extra) + " more)"
                lines.append(call_line)
            if func.raises:
                lines.append("- raises: " + ", ".join(func.raises))
            lines.append("")

    if not any_content:
        lines.append("_No notable calls, model access, or raises detected._")
        lines.append("")

    return "\n".join(lines)


def render_entry_points(url_infos_by_file, root_path):
    """
    Section 4: Django urls.py route to view target mappings, across every
    urls.py file found in the project. This is framework specific (Django
    today), unlike sections 1 to 3 which work for any language. As other
    frameworks are supported later, this function is where their entry
    point detection would be added alongside this one.
    """
    import os

    lines = ["## 4. Entry Points (Django routes)", ""]

    if not url_infos_by_file:
        lines.append("_No urls.py files found._")
        lines.append("")
        return "\n".join(lines)

    for filepath, url_list in url_infos_by_file.items():
        rel_path = os.path.relpath(filepath, root_path)
        lines.append("### `" + rel_path + "`")
        lines.append("")
        if url_list:
            lines.append("| pattern | target |")
            lines.append("|---|---|")
            for pattern, target in url_list:
                lines.append("| " + pattern + " | " + target + " |")
        else:
            lines.append("_No routes detected._")
        lines.append("")

    return "\n".join(lines)


def render_full_document(root_path, source_files, file_units_by_path, url_infos_by_file):
    """
    Assemble the complete four section document.
    """
    lines = []
    lines.append("# Project Context (compressed)")
    lines.append("")
    lines.append("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("")
    lines.append("This file was generated by agent-token-manager. It is a compressed, ")
    lines.append("structured map of this codebase: every file, every class and function ")
    lines.append("signature, and what each function calls, touches, and raises. No ")
    lines.append("implementation bodies are included. Give this file to an AI coding ")
    lines.append("agent instead of the raw source tree to save tokens.")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append(render_project_map(root_path, source_files, file_units_by_path))
    lines.append("---")
    lines.append("")
    lines.append(render_signatures(root_path, source_files, file_units_by_path))
    lines.append("---")
    lines.append("")
    lines.append(render_call_graph(root_path, source_files, file_units_by_path))
    lines.append("---")
    lines.append("")
    lines.append(render_entry_points(url_infos_by_file, root_path))

    return "\n".join(lines)
