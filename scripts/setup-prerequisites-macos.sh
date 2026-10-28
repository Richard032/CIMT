#!/bin/bash
# Pilot prerequisite installer. The approved cimt setup CLI is still to be built.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export CIMT_INSTALL_ROOT="${CIMT_INSTALL_ROOT:-/Users/Shared/CIMT}"
SELECTED_XCODE="$(xcodebuild -version | head -n 1)"
if [ "$SELECTED_XCODE" != "Xcode 26.5" ]; then
  echo "This pinned pilot profile requires Xcode 26.5; selected: $SELECTED_XCODE" >&2
  echo "Select a validated compatible toolchain before installing workloads." >&2
  exit 3
fi
bash "$SCRIPT_DIR/bootstrap-macos-prerequisites.sh"
source "$CIMT_INSTALL_ROOT/environment.sh"
# Prevent an unrelated application global.json from selecting a different SDK.
cd "$CIMT_INSTALL_ROOT"
dotnet workload install maui-android maui-ios --version 10.0.300.3 --disable-parallel
bash "$SCRIPT_DIR/install-macos-mobile-tools.sh"
bash "$SCRIPT_DIR/install-cimt-runtime.sh"
echo "Prerequisite installation complete; device/signing/Git account validation is separate."
