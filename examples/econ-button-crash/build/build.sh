#!/bin/bash
set -euo pipefail
EXAMPLE_BUILD_DIR="$(cd "$(dirname "$0")" && pwd)"
export CIMT_ECON_MAC_TARGETS="$EXAMPLE_BUILD_DIR/macos.targets"
export CIMT_ECON_MONO="$(command -v mono)"
python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path(os.environ['CIMT_BUILD_REQUEST'])
data=json.loads(p.read_text())
props=data.setdefault('properties',{})
props['CustomAfterMicrosoftCommonTargets']=os.environ['CIMT_ECON_MAC_TARGETS']
props['CimtMonoExecutable']=os.environ['CIMT_ECON_MONO']
p.write_text(json.dumps(data))
PY
echo "ECON macOS integration: preserve the CuRMiT tagging step using Mono and portable MSBuild Copy."
exec bash "$CIMT_INSTALL_ROOT/scripts/build/$1.sh"
