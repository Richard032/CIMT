#!/bin/bash
set -euo pipefail
# Build the selected project unchanged with TestPilot's installed default script.
exec bash "$TESTPILOT_INSTALL_ROOT/scripts/build/$1.sh"
