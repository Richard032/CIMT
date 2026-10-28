#!/bin/bash
# Bootstrap pinned Intel Mac runtimes. This is not the future cimt setup command.
set -euo pipefail

CIMT_INSTALL_ROOT="${CIMT_INSTALL_ROOT:-/Users/Shared/CIMT}"
if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != x86_64 ]; then
  echo "This bootstrap currently supports Intel Macs only." >&2
  exit 3
fi
mkdir -p "$CIMT_INSTALL_ROOT/downloads" "$CIMT_INSTALL_ROOT/tools" "$CIMT_INSTALL_ROOT/logs"

download_verified() {
  local url="$1" file="$2" algorithm="$3" expected="$4" actual
  if [ -f "$file" ]; then
    actual="$(shasum -a "$algorithm" "$file" | awk '{print $1}')"
    if [ "$actual" = "$expected" ]; then return; fi
  fi
  curl --fail --location --retry 3 --connect-timeout 20 --max-time 900 \
    --silent --show-error "$url" -o "$file.partial"
  actual="$(shasum -a "$algorithm" "$file.partial" | awk '{print $1}')"
  if [ "$actual" != "$expected" ]; then
    echo "Checksum verification failed: $file" >&2
    exit 3
  fi
  mv "$file.partial" "$file"
}

install_tar() {
  local label="$1" url="$2" filename="$3" algorithm="$4" checksum="$5" destination="$6"
  if [ -f "$destination/.cimt-bootstrap-complete" ]; then
    echo "$label already installed at $destination"
    return
  fi
  echo "Installing $label"
  download_verified "$url" "$CIMT_INSTALL_ROOT/downloads/$filename" "$algorithm" "$checksum"
  mkdir -p "$destination"
  tar -xzf "$CIMT_INSTALL_ROOT/downloads/$filename" -C "$destination" --strip-components=1
  touch "$destination/.cimt-bootstrap-complete"
}

install_tar "Node.js 22.23.4" \
  "https://nodejs.org/dist/v22.23.4/node-v22.23.4-darwin-x64.tar.gz" \
  "node-v22.23.4-darwin-x64.tar.gz" 256 \
  "efcc2b0db6f94bf53eddb038fe2b370277a042bd29e4f19b8f8e23598795b819" \
  "$CIMT_INSTALL_ROOT/tools/node-22.23.4"

install_tar "Microsoft OpenJDK 21.0.13.0.2" \
  "https://aka.ms/download-jdk/microsoft-jdk-21.0.13.0.2-macos-x64.tar.gz" \
  "microsoft-jdk-21.0.13.0.2-macos-x64.tar.gz" 256 \
  "2a28bcd142e7bac5b06838b419e94ba56416df29fbe52b742ea42e060e270472" \
  "$CIMT_INSTALL_ROOT/tools/jdk-21.0.13.0.2"

# .NET SDK archives have no common enclosing directory.
DOTNET_DEST="$CIMT_INSTALL_ROOT/tools/dotnet-10.0.300"
if [ ! -f "$DOTNET_DEST/.cimt-bootstrap-complete" ]; then
  echo "Installing .NET SDK 10.0.300 (Xcode 26.5 compatibility track)"
  download_verified \
    "https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.300/dotnet-sdk-10.0.300-osx-x64.tar.gz" \
    "$CIMT_INSTALL_ROOT/downloads/dotnet-sdk-10.0.300-osx-x64.tar.gz" 512 \
    "d4a5cd68a95d03bb3876d40492a4d53af0595b2d7c7b007be54e498198ebe2692abde7efd1ad8569b2ec5bba1a973c912a68510b32596f57cb6ec4f5dbd6037b"
  mkdir -p "$DOTNET_DEST"
  tar -xzf "$CIMT_INSTALL_ROOT/downloads/dotnet-sdk-10.0.300-osx-x64.tar.gz" -C "$DOTNET_DEST"
  touch "$DOTNET_DEST/.cimt-bootstrap-complete"
fi

# Use shell-quoted paths and keep activation explicit for developer/Jenkins sessions.
JDK_BASE="$CIMT_INSTALL_ROOT/tools/jdk-21.0.13.0.2"
JDK_HOME=""
for candidate in "$JDK_BASE/Contents/Home" "$JDK_BASE"/*/Contents/Home "$JDK_BASE"; do
  if [ -x "$candidate/bin/java" ]; then JDK_HOME="$candidate"; break; fi
done
if [ -z "$JDK_HOME" ]; then echo "JDK archive layout not recognized" >&2; exit 3; fi
{
  echo '# CIMT prerequisite environment. Source in developer/Jenkins sessions.'
  printf 'export CIMT_INSTALL_ROOT=%q\n' "$CIMT_INSTALL_ROOT"
  printf 'export JAVA_HOME=%q\n' "$JDK_HOME"
  printf 'export ANDROID_HOME=%q\n' "$CIMT_INSTALL_ROOT/tools/android-sdk"
  echo 'export ANDROID_SDK_ROOT="$ANDROID_HOME"'
  printf 'export DOTNET_ROOT=%q\n' "$DOTNET_DEST"
  printf 'export APPIUM_HOME=%q\n' "$CIMT_INSTALL_ROOT/tools/appium-home"
  echo 'export MOBILEMCP_DISABLE_TELEMETRY=1'
  echo 'export DOTNET_CLI_TELEMETRY_OPTOUT=1'
  echo 'export DOTNET_GENERATE_ASPNET_CERTIFICATE=false'
  echo 'export PATH="$CIMT_INSTALL_ROOT/tools/node-22.23.4/bin:$CIMT_INSTALL_ROOT/tools/node-packages/bin:$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/current/bin:$DOTNET_ROOT:$PATH"'
} > "$CIMT_INSTALL_ROOT/environment.sh"
source "$CIMT_INSTALL_ROOT/environment.sh"
node --version
npm --version
java -version
dotnet --version
echo "Runtime bootstrap completed. Activate with: source $CIMT_INSTALL_ROOT/environment.sh"
