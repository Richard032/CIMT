#!/bin/bash
# Source installation of the Python support runtime; not the final YAML setup CLI.
set -euo pipefail
SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TESTPILOT_INSTALL_ROOT="${TESTPILOT_INSTALL_ROOT:-/Users/Shared/TestPilot}"
TESTPILOT_PYTHON_BOOTSTRAP="${TESTPILOT_PYTHON_BOOTSTRAP:-}"
if [ -z "$TESTPILOT_PYTHON_BOOTSTRAP" ]; then
  for candidate in python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/local/bin/python3; do
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
      TESTPILOT_PYTHON_BOOTSTRAP="$candidate"
      break
    fi
  done
fi
if [ -z "$TESTPILOT_PYTHON_BOOTSTRAP" ]; then
  echo "Install Python 3.11 or newer for this Intel Mac, then rerun this helper. See the installation guide." >&2
  exit 3
fi
if [ ! -x "$TESTPILOT_INSTALL_ROOT/tools/python/bin/python" ]; then
  "$TESTPILOT_PYTHON_BOOTSTRAP" -m venv "$TESTPILOT_INSTALL_ROOT/tools/python"
fi
"$TESTPILOT_INSTALL_ROOT/tools/python/bin/python" -m pip install --disable-pip-version-check -r "$SOURCE_ROOT/runtime/requirements.txt"
mkdir -p "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime"
cp "$SOURCE_ROOT/runtime/"*.py "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/"
for runtime_package in test_planning stopping_policy ai_instructions device_adapter result_review knowledge; do
  mkdir -p "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/$runtime_package"
  cp "$SOURCE_ROOT/runtime/$runtime_package/"*.py "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/$runtime_package/"
done
mkdir -p "$TESTPILOT_INSTALL_ROOT/data/knowledge"
install -m 644 "$SOURCE_ROOT/runtime/knowledge/editor.html" "$TESTPILOT_INSTALL_ROOT/data/knowledge/editor.html"
if [ ! "$SOURCE_ROOT/Knowledge Database.command" -ef "$TESTPILOT_INSTALL_ROOT/Knowledge Database.command" ]; then
  install -m 755 "$SOURCE_ROOT/Knowledge Database.command" "$TESTPILOT_INSTALL_ROOT/Knowledge Database.command"
fi
# Remove source modules replaced by the named packages and execution components.
rm -f "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/exploration_memory.py"
rm -f "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/decision_recovery.py"
rm -f "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/request_context.py"
# Reply decoding belongs to execution, outside the instruction layer.
rm -f "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/ai_exchange/replies.py"
rm -f "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/ai_exchange/__init__.py"
# The adapter implementation now lives only in its own package.
for old_module in mobile app_lifecycle device_commands device_target mcp_client rpc_messages screen_capture; do
  rm -f "$TESTPILOT_INSTALL_ROOT/lib/testpilot-runtime/$old_module.py"
done
# Keep test-folder wrappers separate from the backend scripts they invoke.
mkdir -p "$TESTPILOT_INSTALL_ROOT/templates/test-run/build"
cp "$SOURCE_ROOT/scripts/test-run/build/"*.sh "$TESTPILOT_INSTALL_ROOT/templates/test-run/build/"
echo "TestPilot support runtime installed."
