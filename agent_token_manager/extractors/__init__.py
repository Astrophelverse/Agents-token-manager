"""
extractors package

Each file in here is a language specific extractor. An extractor's only job
is: read source code in one language, produce the generic shapes defined in
shapes.py (FileUnit, ClassInfo, FunctionInfo, ParamInfo).

Today there is one extractor: python_extractor.py, built on Python's built in
ast module.

To add a new language later (JavaScript, Go, etc), the pattern is:
    1. Create extractors/<language>_extractor.py
    2. Give it one public function: extract_file(filepath) -> FileUnit | None
    3. Register it in extractors/registry.py against its file extension

Nothing outside this package needs to change. render.py and cli.py only ever
work with FileUnit objects, never with raw source or language specific trees.
"""
