#!/bin/bash
set -euo pipefail

testpilot_folder="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$testpilot_folder/bin/testpilot" ]; then
  launcher="$testpilot_folder/bin/testpilot"
elif [ -x "$testpilot_folder/.local/install/bin/testpilot" ]; then
  launcher="$testpilot_folder/.local/install/bin/testpilot"
elif [ -x "$testpilot_folder/scripts/testpilot" ]; then
  launcher="$testpilot_folder/scripts/testpilot"
else
  echo "TestPilot is not installed. See the installation guide." >&2
  exit 3
fi

url="$("$launcher" knowledge)"
if [ "${1:-}" = "--url" ]; then
  printf '%s\n' "$url"
else
  open "$url"
fi
