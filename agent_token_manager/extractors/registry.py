"""
extractors/registry.py

This file is the single plug point for adding new languages later.
It maps a file extension to the extractor function that knows how to
read that language.

Today only Python is registered. To add JavaScript later, the only change
needed anywhere in the project is:

    1. Write extractors/javascript_extractor.py with an extract_file(filepath)
       function that returns a shapes.FileUnit, same as python_extractor.py does.
    2. Add its entries to EXTRACTORS_BY_EXTENSION below, e.g.
       ".js": javascript_extractor.extract_file,
       ".jsx": javascript_extractor.extract_file,

Nothing in scanner.py, render.py or cli.py needs to change, since they all
work through get_extractor_for() and the generic FileUnit shape.
"""

from agent_token_manager.extractors import python_extractor


EXTRACTORS_BY_EXTENSION = {
    ".py": python_extractor.extract_file,
    # Future languages get added here, one line each, once their
    # extractor file exists. Example for when that day comes:
    # ".js":  javascript_extractor.extract_file,
    # ".jsx": javascript_extractor.extract_file,
    # ".ts":  typescript_extractor.extract_file,
    # ".go":  go_extractor.extract_file,
}


def get_extractor_for(filepath):
    """
    Return the extractor function responsible for this file's extension,
    or None if no extractor is registered for it yet. Callers should skip
    files with no matching extractor rather than error out, since a
    codebase will always contain file types we do not understand yet
    (images, configs, lockfiles, and so on).
    """
    for extension, extractor_func in EXTRACTORS_BY_EXTENSION.items():
        if filepath.endswith(extension):
            return extractor_func
    return None


def supported_extensions():
    """Return the list of file extensions this tool currently understands."""
    return list(EXTRACTORS_BY_EXTENSION.keys())
