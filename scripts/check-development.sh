#!/bin/bash
# Run development checks with fake tools and devices. No API key is needed.
set -euo pipefail

CIMT_SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CIMT_INSTALL_ROOT="${CIMT_INSTALL_ROOT:-/Users/Shared/CIMT}"
if [ -f "$CIMT_INSTALL_ROOT/environment.sh" ]; then
    source "$CIMT_INSTALL_ROOT/environment.sh"
fi
CIMT_TEST_PYTHON="$CIMT_INSTALL_ROOT/tools/python/bin/python"
if [ ! -x "$CIMT_TEST_PYTHON" ]; then
    echo "Install the CIMT support runtime before running these checks." >&2
    exit 3
fi

cd "$CIMT_SOURCE_ROOT"
dotnet test tests/Cimt.UnitTests/Cimt.UnitTests.csproj -c Release --nologo
"$CIMT_TEST_PYTHON" tests/check-runtime.py
"$CIMT_TEST_PYTHON" -m unittest discover -s tests -p 'test_*.py' -v
dotnet run --project tests/Cimt.Checks/Cimt.Checks.csproj -c Release
"$CIMT_TEST_PYTHON" tests/check-build-contract.py
"$CIMT_TEST_PYTHON" tests/check-example-build.py
