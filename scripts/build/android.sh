#!/bin/bash
set -euo pipefail
SCRIPT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEFAULT_WORKER="$SCRIPT_ROOT/tools/Cimt.BuildWorker/bin/Release/net10.0/cimt-build.dll"
if [ -f "$SCRIPT_ROOT/lib/cimt-build/cimt-build.dll" ]; then DEFAULT_WORKER="$SCRIPT_ROOT/lib/cimt-build/cimt-build.dll"; fi
WORKER="${CIMT_BUILD_WORKER:-$DEFAULT_WORKER}"
exec dotnet "$WORKER" android
