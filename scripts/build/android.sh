#!/bin/bash
set -euo pipefail
SCRIPT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEFAULT_WORKER="$SCRIPT_ROOT/tools/TestPilot.BuildWorker/bin/Release/net10.0/testpilot-build.dll"
if [ -f "$SCRIPT_ROOT/lib/testpilot-build/testpilot-build.dll" ]; then DEFAULT_WORKER="$SCRIPT_ROOT/lib/testpilot-build/testpilot-build.dll"; fi
WORKER="${TESTPILOT_BUILD_WORKER:-$DEFAULT_WORKER}"
exec dotnet "$WORKER" android
