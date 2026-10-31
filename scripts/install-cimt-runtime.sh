#!/bin/bash
# Source installation of the Python support runtime; not the final YAML setup CLI.
set -euo pipefail
SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CIMT_INSTALL_ROOT="${CIMT_INSTALL_ROOT:-/Users/Shared/CIMT}"
CIMT_PYTHON_BOOTSTRAP="${CIMT_PYTHON_BOOTSTRAP:-}"
if [ -z "$CIMT_PYTHON_BOOTSTRAP" ]; then
  for candidate in python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/local/bin/python3; do
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
      CIMT_PYTHON_BOOTSTRAP="$candidate"
      break
    fi
  done
fi
if [ -z "$CIMT_PYTHON_BOOTSTRAP" ]; then
  echo "Install Python 3.11 or newer for this Intel Mac, then rerun this helper. See the installation guide." >&2
  exit 3
fi
if [ ! -x "$CIMT_INSTALL_ROOT/tools/python/bin/python" ]; then
  "$CIMT_PYTHON_BOOTSTRAP" -m venv "$CIMT_INSTALL_ROOT/tools/python"
fi
"$CIMT_INSTALL_ROOT/tools/python/bin/python" -m pip install --disable-pip-version-check -r "$SOURCE_ROOT/runtime/requirements.txt"
mkdir -p "$CIMT_INSTALL_ROOT/lib/cimt-runtime"
cp "$SOURCE_ROOT/runtime/"*.py "$CIMT_INSTALL_ROOT/lib/cimt-runtime/"
for runtime_package in test_planning stopping_policy ai_exchange; do
  mkdir -p "$CIMT_INSTALL_ROOT/lib/cimt-runtime/$runtime_package"
  cp "$SOURCE_ROOT/runtime/$runtime_package/"*.py "$CIMT_INSTALL_ROOT/lib/cimt-runtime/$runtime_package/"
done
# This module moved into the planning package. Do not leave two implementations.
rm -f "$CIMT_INSTALL_ROOT/lib/cimt-runtime/exploration_memory.py"
echo "CIMT support runtime installed."
