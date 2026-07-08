#!/usr/bin/env bash
#
# install.sh
#
# Installs agent-token-manager (the "atm" command) on the current machine.
#
# What this script does, step by step:
#   1. Checks that python3 and pip are available.
#   2. Finds where this script itself lives, so it can install from source
#      no matter which directory the user runs it from.
#   3. Runs "pip install ." on this project, which reads pyproject.toml
#      and registers the "atm" command on the user's PATH.
#   4. Prints a short confirmation and usage example.
#
# Usage:
#   ./install.sh
#
# or, once this project is hosted on GitHub:
#   curl -sSL https://raw.githubusercontent.com/yourname/agent-token-manager/main/install.sh | bash

set -e

echo "agent-token-manager installer"
echo "=============================="

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found on PATH."
    echo "Install python3 first, then run this script again."
    exit 1
fi

echo "python3 found: $(python3 --version)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
    echo "Error: pyproject.toml not found next to install.sh."
    echo "Make sure you are running this from inside the agent-token-manager folder."
    exit 1
fi

echo "Installing from $SCRIPT_DIR ..."
python3 -m pip install --user "$SCRIPT_DIR"

echo ""
echo "Installed successfully."
echo ""
echo "If the 'atm' command is not found, make sure your user pip bin"
echo "directory is on your PATH. On most systems that is:"
echo "    ~/.local/bin"
echo ""
echo "Try it now:"
echo "    atm scan /path/to/your/django/project"
echo ""
