#!/bin/bash
# Evaluation prerequisites only; the CIMT device adapter is not selected yet.
set -euo pipefail
CIMT_INSTALL_ROOT="${CIMT_INSTALL_ROOT:-/Users/Shared/CIMT}"
source "$CIMT_INSTALL_ROOT/environment.sh"
ARCHIVE="$CIMT_INSTALL_ROOT/downloads/commandlinetools-mac_x86_64-15859902_latest.zip"
EXPECTED="c5a6378ab5cf7e0d5701921405115befff13e9ff7417fb588389338f8bd050f3"
if [ -f "$ARCHIVE.partial" ] && [ ! -f "$ARCHIVE" ]; then
  if [ "$(shasum -a 256 "$ARCHIVE.partial" | awk '{print $1}')" = "$EXPECTED" ]; then
    mv "$ARCHIVE.partial" "$ARCHIVE"
  fi
fi
if [ ! -f "$ARCHIVE" ]; then
  curl --fail --location --retry 3 --connect-timeout 20 --max-time 900 \
    --silent --show-error \
    https://dl.google.com/android/repository/commandlinetools-mac_x86_64-15859902_latest.zip \
    -o "$ARCHIVE.partial"
  [ "$(shasum -a 256 "$ARCHIVE.partial" | awk '{print $1}')" = "$EXPECTED" ]
  mv "$ARCHIVE.partial" "$ARCHIVE"
fi
[ "$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')" = "$EXPECTED" ]
if [ ! -x "$ANDROID_HOME/cmdline-tools/current/bin/sdkmanager" ]; then
  STAGE="$(mktemp -d "$CIMT_INSTALL_ROOT/downloads/android-extract.XXXXXX")"
  unzip -q "$ARCHIVE" -d "$STAGE"
  REVISION="$(awk -F= '/^Pkg.Revision/ {gsub(/[[:space:]]/, "", $2); print $2}' "$STAGE/cmdline-tools/source.properties")"
  [ -n "$REVISION" ]
  mkdir -p "$ANDROID_HOME/cmdline-tools"
  if [ ! -d "$ANDROID_HOME/cmdline-tools/$REVISION" ]; then
    mv "$STAGE/cmdline-tools" "$ANDROID_HOME/cmdline-tools/$REVISION"
  fi
  ln -sfn "$REVISION" "$ANDROID_HOME/cmdline-tools/current"
  rm -rf "$STAGE"
fi

# yes can exit with SIGPIPE after sdkmanager has accepted all licenses.
(set +o pipefail; yes | sdkmanager --sdk_root="$ANDROID_HOME" --licenses)
sdkmanager --sdk_root="$ANDROID_HOME" \
  "platform-tools" "platforms;android-36" "build-tools;36.0.0"

npm install --global --no-fund --no-audit --prefix "$CIMT_INSTALL_ROOT/tools/node-packages" \
  appium@3.9.0 @mobilenext/mobile-mcp@1.0.14

install_driver() {
  local name="$1" version="$2" installed
  installed="$(appium driver list --installed --json | node -e \
    'let s=""; process.stdin.on("data", x=>s+=x); process.stdin.on("end", ()=>process.stdout.write(JSON.parse(s)[process.argv[1]]?.version || ""));' "$name")"
  if [ "$installed" = "$version" ]; then
    echo "$name@$version already installed"
    return
  fi
  if [ -n "$installed" ]; then appium driver uninstall "$name"; fi
  appium driver install "$name@$version"
}
install_driver uiautomator2 8.7.2
install_driver xcuitest 12.22.1

adb version
sdkmanager --version
appium --version
appium driver list --installed
echo "Mobile tooling installation completed."
