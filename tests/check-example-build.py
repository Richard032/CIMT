#!/usr/bin/env python3
"""Verify the example overrides only the intended Windows pre-build target."""
import os, pathlib, subprocess, tempfile
source = pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='cimt-example-build-') as folder:
    root = pathlib.Path(folder); app = root / 'EconMobile.Common'; app.mkdir()
    resources = app / 'Platforms/Android/Resources/values'; (resources / 'template').mkdir(parents=True)
    (resources / 'template/strings.xml').write_text('<resources />')
    (root / 'CuRMiT-project.xml').write_text('<fixture />')
    (root / 'Tools/CuRMiT').mkdir(parents=True); (root / 'Tools/CuRMiT/CuRMiTagger.exe').write_text('fixture')
    project = app / 'EconMobile.Common.csproj'
    project.write_text('''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup><Target Name="PreBuild" BeforeTargets="PreBuildEvent"><Error Text="Windows-only prebuild was not replaced" /></Target></Project>''')
    mono = root / 'fixture-mono'
    mono.write_text('''#!/bin/bash
set -euo pipefail
test "$MONO_IOMAP" = all
test -f "$1"
test -f "$2"
touch "$CIMT_FIXTURE_TAGGER_MARKER"
'''); mono.chmod(0o700)
    marker = root / 'tagger-invoked'; env = dict(os.environ, CIMT_FIXTURE_TAGGER_MARKER=str(marker))
    args = ['dotnet', 'msbuild', str(project), '-nologo', '-t:PreBuild',
            '-p:CustomAfterMicrosoftCommonTargets=' + str(source / 'examples/econ-button-crash/build/macos.targets'),
            '-p:CimtMonoExecutable=' + str(mono)]
    r = subprocess.run(args, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert marker.exists(), 'Tagging was bypassed'
    assert (resources / 'strings.xml').read_text() == '<resources />'
    other = app / 'Other.csproj'; other.write_text(project.read_text())
    r = subprocess.run([x if x != str(project) else str(other) for x in args], env=env, capture_output=True, text=True)
    assert r.returncode != 0 and 'Windows-only prebuild was not replaced' in r.stdout, 'Unrelated project target was overridden'
print('PASS example runs the tagger, copies resources, and preserves unrelated project targets.')
