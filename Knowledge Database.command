#!/bin/bash
set -euo pipefail

cimt_folder="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$cimt_folder/bin/cimt" ]; then
  launcher="$cimt_folder/bin/cimt"
elif [ -x "$cimt_folder/.local/install/bin/cimt" ]; then
  launcher="$cimt_folder/.local/install/bin/cimt"
elif [ -x "$cimt_folder/scripts/cimt" ]; then
  launcher="$cimt_folder/scripts/cimt"
else
  echo "CIMT is not installed. See the installation guide." >&2
  exit 3
fi

url="$("$launcher" knowledge)"
if [ "${1:-}" = "--url" ]; then
  printf '%s\n' "$url"
else
  open "$url"
fi
