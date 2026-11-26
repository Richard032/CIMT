#!/bin/bash
# Run development checks with fake tools and devices. No API key is needed.
set -euo pipefail

TESTPILOT_SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TESTPILOT_INSTALL_ROOT="${TESTPILOT_INSTALL_ROOT:-/Users/Shared/TestPilot}"
if [ -f "$TESTPILOT_INSTALL_ROOT/environment.sh" ]; then
    source "$TESTPILOT_INSTALL_ROOT/environment.sh"
fi
TESTPILOT_TEST_PYTHON="$TESTPILOT_INSTALL_ROOT/tools/python/bin/python"
if [ ! -x "$TESTPILOT_TEST_PYTHON" ]; then
    echo "Install the TestPilot support runtime before running these checks." >&2
    exit 3
fi

cd "$TESTPILOT_SOURCE_ROOT"
dotnet test tests/TestPilot.UnitTests/TestPilot.UnitTests.csproj -c Release --nologo
"$TESTPILOT_TEST_PYTHON" tests/check-runtime.py
"$TESTPILOT_TEST_PYTHON" -m unittest discover -s tests -p 'test_*.py' -v
dotnet run --project tests/TestPilot.Checks/TestPilot.Checks.csproj -c Release
"$TESTPILOT_TEST_PYTHON" tests/check-build-contract.py
"$TESTPILOT_TEST_PYTHON" tests/check-example-build.py
"$TESTPILOT_TEST_PYTHON" tests/check-output-layout.py
