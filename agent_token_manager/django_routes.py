"""
django_routes.py

This file is intentionally separate from extractors/python_extractor.py.
The extractor's job is language understanding (Python in general). This
file's job is framework understanding (Django specifically): reading a
urls.py file and producing (pattern, target) pairs.

Keeping this separate matters for the same reason the extractor/registry
split matters: later, if we support other frameworks (Flask, FastAPI,
Express for JS, etc), each one gets its own small file like this, and none
of them touch the generic Python extractor or the renderer's section 1 to 3
logic. Only render_entry_points() in render.py needs to learn about a new
framework's output shape.
"""

import ast


def _name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        return _name_of(node.func)
    return "unknown"


def _literal_or_source(node):
    try:
        return repr(ast.literal_eval(node))
    except (ValueError, TypeError, SyntaxError):
        try:
            return ast.unparse(node)
        except Exception:
            return "?"


def parse_django_urls(filepath):
    """
    Read a urls.py file and return a list of (pattern, target) tuples.
    Looks for the urlpatterns list and reads path()/re_path()/url() calls
    inside it. Returns an empty list if the file cannot be parsed or has
    no urlpatterns list, never raises.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []

    results = []

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.List)):
            continue

        is_urlpatterns = any(
            isinstance(t, ast.Name) and t.id == "urlpatterns" for t in node.targets
        )
        if not is_urlpatterns:
            continue

        for element in node.value.elts:
            if not isinstance(element, ast.Call):
                continue

            call_name = _name_of(element.func)
            if call_name not in ("path", "re_path", "url"):
                continue
            if len(element.args) == 0:
                continue

            pattern = _literal_or_source(element.args[0])

            target = "unknown"
            if len(element.args) > 1:
                target_node = element.args[1]
                if isinstance(target_node, ast.Call):
                    target = _name_of(target_node.func) + "()"
                else:
                    target = _name_of(target_node)

            results.append((pattern, target))

    return results
