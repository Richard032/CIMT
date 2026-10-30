#!/bin/bash
set -euo pipefail
# Build the selected project unchanged with CIMT's installed default script.
exec bash "$CIMT_INSTALL_ROOT/scripts/build/$1.sh"
