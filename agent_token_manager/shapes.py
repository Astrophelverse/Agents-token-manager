"""
shapes.py

This file defines the generic, language agnostic data shapes that describe
any codebase, in any language. Nothing in this file knows about Python,
Django, JavaScript, or anything else. It is pure structure.

The idea: today we only have one extractor (extractors/python_extractor.py),
which reads Python source and produces these shapes. Later, when we add
support for JavaScript, Go, or anything else, we write a new extractor that
reads that language's source and produces the exact same shapes below.

Because the renderer (render.py) only ever looks at these shapes, and never
at raw source or language specific ast nodes, adding a new language never
requires touching the renderer. That is the whole point of this file: it is
the boundary between "reading code" (language specific) and "understanding
code" (language agnostic).

A quick mental model for the four shapes below:

    ParamInfo    one parameter of a function, e.g. "user: User = None"
    FunctionInfo one function or method, its parameters, and what it does
                 when it runs (calls made, models touched, exceptions raised)
    ClassInfo    one class, its bases, attributes, and its methods
    FileUnit     one source file, holding every class and top level function
                 found in it, plus the raw list of imports for that file

FunctionInfo is the most important shape in this whole project. Its calls,
touches and raises fields are what let an AI agent understand not just the
*signature* of a function, but what it *does* when called, without ever
opening the file it lives in.
"""

from dataclasses import dataclass, field


@dataclass
class ParamInfo:
    name: str
    annotation: str = ""
    default: str = ""


@dataclass
class FunctionInfo:
    name: str
    params: list = field(default_factory=list)
    returns: str = ""
    docstring: str = ""
    decorators: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    touches: list = field(default_factory=list)
    raises: list = field(default_factory=list)
    is_method: bool = False


@dataclass
class ClassInfo:
    name: str
    bases: list = field(default_factory=list)
    docstring: str = ""
    attributes: list = field(default_factory=list)
    methods: list = field(default_factory=list)
    decorators: list = field(default_factory=list)


@dataclass
class FileUnit:
    path: str
    language: str
    imports: list = field(default_factory=list)
    classes: list = field(default_factory=list)
    functions: list = field(default_factory=list)
    line_count: int = 0
