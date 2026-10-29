#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import json
import os
from pathlib import Path

request = json.loads(Path(os.environ['CIMT_BUILD_REQUEST']).read_text())
project = Path(os.environ['CIMT_REPOSITORY_ROOT']) / request['project'].replace('\\', '/')
content = project.read_bytes()
windows_copy = rb'<Exec Command="copy /Y &quot;$(ProjectDir)Platforms\Android\Resources\values\template\strings.xml&quot; &quot;$(ProjectDir)Platforms\Android\Resources\values\strings.xml&quot;" />'
portable_copy = b'<Copy SourceFiles="$(MSBuildProjectDirectory)/Platforms/Android/Resources/values/template/strings.xml" DestinationFiles="$(MSBuildProjectDirectory)/Platforms/Android/Resources/values/strings.xml" />'
# Change only this known command in the disposable clone. Keep every other build step.
if content.count(windows_copy) == 1:
    project.write_bytes(content.replace(windows_copy, portable_copy, 1))
    print('ECON macOS integration: replaced the known Windows resource-copy command in the run clone.')
else:
    print('ECON macOS integration: no single known Windows resource-copy command; project build steps are unchanged.')
PY
exec bash "$CIMT_INSTALL_ROOT/scripts/build/$1.sh"
