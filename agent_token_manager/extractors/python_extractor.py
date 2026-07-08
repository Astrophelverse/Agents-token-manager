"""
extractors/python_extractor.py

This is the Python specific extractor. It reads a .py file using the built
in ast module and produces one FileUnit, filled with ClassInfo and
FunctionInfo objects, as defined in shapes.py.

This file replaces the old parser.py's job, but with two real upgrades:

1. It is language agnostic on the output side. Everything it returns is a
   plain shapes.py object. A future JS or Go extractor returns the exact
   same shapes, so render.py never needs to know which language it is
   looking at.

2. It tracks what each function actually DOES when it runs, not just its
   signature. For every function and method we walk its body and record:
       calls     every function/method call made inside it, e.g. "Order.objects.create"
       touches   every Django model class name referenced inside it
       raises    every exception type explicitly raised
   This is the piece that lets an AI agent write new code that correctly
   calls into a function, without opening the file that function lives in,
   because it already knows the side effects, not just the type signature.

The public entry point is extract_file(filepath) -> FileUnit | None.
"""

import ast
import os

from agent_token_manager.shapes import FileUnit, ClassInfo, FunctionInfo, ParamInfo


def _name_of(node):
    """
    Turn an ast node representing a name, attribute chain, or call target
    into a readable string. Handles simple names (Model), dotted access
    (models.Model, self.request.user), and call targets (Order.objects.create).
    """
    if node is None:
        return ""
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
        elif isinstance(current, ast.Call):
            parts.append(_name_of(current.func) + "()")
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        return _name_of(node.func)
    return ""


def _annotation_to_str(node):
    """
    Convert a type annotation node into a readable string, e.g. "int",
    "Optional[str]", "list[Product]". Falls back to unparse for anything
    complex, and to empty string if there is no annotation at all.
    """
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return _name_of(node)


def _default_to_str(node):
    """
    Convert a default value node into a short readable string.
    Used for parameters like "status: str = 'pending'".
    """
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "?"


def _extract_params(args_node):
    """
    Read a function's ast.arguments node and produce a list of ParamInfo.
    Handles positional args, defaults (aligned from the right, since Python
    only allows trailing defaults), and skips "self" and "cls" since those
    are implicit and not useful in a signature summary.
    """
    params = []

    positional = args_node.args
    defaults = args_node.defaults
    num_no_default = len(positional) - len(defaults)

    for i, arg in enumerate(positional):
        if arg.arg in ("self", "cls"):
            continue
        default_str = ""
        default_index = i - num_no_default
        if default_index >= 0:
            default_str = _default_to_str(defaults[default_index])
        params.append(
            ParamInfo(
                name=arg.arg,
                annotation=_annotation_to_str(arg.annotation),
                default=default_str,
            )
        )

    for arg in args_node.kwonlyargs:
        params.append(
            ParamInfo(name=arg.arg, annotation=_annotation_to_str(arg.annotation))
        )

    if args_node.vararg:
        params.append(ParamInfo(name="*" + args_node.vararg.arg))
    if args_node.kwarg:
        params.append(ParamInfo(name="**" + args_node.kwarg.arg))

    return params


# A small, fixed list of common Django model style base names, used only as
# a heuristic to guess which called names in a function body are likely to
# be model classes, e.g. "Order.objects.create(...)" implies the function
# touches the Order model. This is intentionally simple: it looks at the
# left hand side of ".objects." style chains.
def _extract_body_info(body_nodes):
    """
    Walk every statement inside a function body and collect three things:
        calls    every distinct call target, as a readable dotted string
        touches  every distinct name that appears immediately before
                 ".objects" in a call chain, a strong signal it is a
                 Django model being queried or written to
        raises   every distinct exception type name from raise statements

    This function does not try to be a full data flow analyzer. It is a
    lightweight, best effort pass, good enough to tell an agent "this
    function reads and writes these models and calls these things",
    without needing to actually execute any code.
    """
    calls = []
    touches = []
    raises = []

    for node in ast.walk(ast.Module(body=body_nodes, type_ignores=[])):
        if isinstance(node, ast.Call):
            call_name = _name_of(node.func)
            if call_name and call_name not in calls:
                calls.append(call_name)

            if ".objects." in call_name:
                model_name = call_name.split(".objects.")[0]
                model_name = model_name.split(".")[-1]
                if model_name and model_name not in touches:
                    touches.append(model_name)

        if isinstance(node, ast.Raise) and node.exc is not None:
            exc_name = _name_of(node.exc)
            if exc_name and exc_name not in raises:
                raises.append(exc_name)

    return calls, touches, raises


def _get_docstring_first_line(node):
    doc = ast.get_docstring(node)
    if not doc:
        return ""
    return doc.strip().splitlines()[0]


def _extract_function(node, is_method=False):
    """
    Build a FunctionInfo from an ast.FunctionDef or ast.AsyncFunctionDef node,
    including its parameters, return annotation, decorators, docstring, and
    the calls/touches/raises extracted from its body.
    """
    params = _extract_params(node.args)
    returns = _annotation_to_str(node.returns)
    docstring = _get_docstring_first_line(node)
    decorators = [_name_of(d) for d in node.decorator_list]

    calls, touches, raises = _extract_body_info(node.body)

    return FunctionInfo(
        name=node.name,
        params=params,
        returns=returns,
        docstring=docstring,
        decorators=decorators,
        calls=calls,
        touches=touches,
        raises=raises,
        is_method=is_method,
    )


def _extract_class(node):
    """
    Build a ClassInfo from an ast.ClassDef node: its base classes, docstring,
    simple attribute assignments at class body level (e.g. name = models.CharField(...)),
    and every method defined inside it.
    """
    bases = [_name_of(b) for b in node.bases]
    docstring = _get_docstring_first_line(node)
    decorators = [_name_of(d) for d in node.decorator_list]

    attributes = []
    methods = []

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_extract_function(item, is_method=True))

        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    value_desc = _name_of(item.value) if isinstance(item.value, ast.Call) else _default_to_str(item.value)
                    attributes.append(target.id + ": " + value_desc)

    return ClassInfo(
        name=node.name,
        bases=bases,
        docstring=docstring,
        attributes=attributes,
        methods=methods,
        decorators=decorators,
    )


def _extract_imports(tree):
    """
    Collect a readable list of import statements from the top of the file.
    Kept as plain strings since imports are shown as is, not restructured.
    """
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append("import " + alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join(alias.name for alias in node.names)
            imports.append("from " + module + " import " + names)
    return imports


def extract_file(filepath):
    """
    Public entry point for this extractor. Reads one .py file and returns
    a FileUnit describing it, or None if the file cannot be read or parsed.
    Never raises: a broken file should not stop a full project scan.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None

    unit = FileUnit(
        path=filepath,
        language="python",
        imports=_extract_imports(tree),
        line_count=len(source.splitlines()),
    )

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            unit.classes.append(_extract_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            unit.functions.append(_extract_function(node, is_method=False))

    return unit
