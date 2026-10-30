#!/usr/bin/env python3
"""Check the example adapter with small MSBuild projects, without building a MAUI app."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
WINDOWS_COPY = r'<Exec Command="copy /Y &quot;$(ProjectDir)Platforms\Android\Resources\values\template\strings.xml&quot; &quot;$(ProjectDir)Platforms\Android\Resources\values\strings.xml&quot;" />'


class ExampleBuildChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='cimt-example-build-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.app = self.root / 'EconMobile.Common'
        self.app.mkdir()
        self.project = self.app / 'EconMobile.Common.csproj'
        self.resources = self.app / 'Platforms/Android/Resources/values'
        (self.resources / 'template').mkdir(parents=True)
        (self.resources / 'template/strings.xml').write_text('<resources />')
        self.request = self.root / 'request.json'
        self.request.write_text(json.dumps({
            'project': 'EconMobile.Common/EconMobile.Common.csproj',
            'configuration': 'Release_Generic',
            'properties': {'FixtureSetting': 'from configuration'},
        }))
        self.original_request = self.request.read_bytes()
        scripts = self.root / 'installation/scripts/build'
        scripts.mkdir(parents=True)
        # The supplied defaults are replaced only in this fixture. Run the real MSBuild PreBuild target.
        worker = '''#!/bin/bash
python3 - <<'WORKER'
import json, os, pathlib, subprocess
request = json.loads(pathlib.Path(os.environ['CIMT_BUILD_REQUEST']).read_text())
project = pathlib.Path(os.environ['CIMT_REPOSITORY_ROOT']) / request['project']
args = ['dotnet', 'msbuild', str(project), '-nologo', '-t:PreBuild', '-p:Configuration=' + request['configuration']]
args += ['-p:' + key + '=' + value for key, value in request['properties'].items()]
raise SystemExit(subprocess.run(args).returncode)
WORKER
'''
        for platform in ('android', 'ios'):
            (scripts / (platform + '.sh')).write_text(worker)
        self.environment = dict(os.environ,
            CIMT_BUILD_REQUEST=str(self.request),
            CIMT_REPOSITORY_ROOT=str(self.root),
            CIMT_INSTALL_ROOT=str(self.root / 'installation'))

    def write_project(self, targets):
        self.project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
            '<TargetFramework>net10.0</TargetFramework></PropertyGroup>' + targets + '</Project>')

    def run_adapter(self, platform='android', expect_success=True):
        result = subprocess.run(['bash', str(SOURCE / 'examples/econ-button-crash/build' / (platform + '.sh'))],
            env=self.environment, capture_output=True, text=True)
        if expect_success:
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        else:
            self.assertNotEqual(0, result.returncode, 'The original failing build was hidden')
        self.assertEqual(self.original_request, self.request.read_bytes(), 'Build properties were changed')
        return result.stdout

    def test_windows_command_is_preserved_and_its_failure_is_not_hidden(self):
        self.write_project('<Target Name="PreBuild" BeforeTargets="PreBuildEvent">' + WINDOWS_COPY + '</Target>')
        original = self.project.read_bytes()
        self.run_adapter(expect_success=False)
        self.assertEqual(original, self.project.read_bytes())
        self.assertFalse((self.resources / 'strings.xml').exists())

    def test_project_configured_tool_and_properties_are_preserved(self):
        self.write_project('<Target Name="ConfiguredTool" BeforeTargets="PreBuild">'
            '<WriteLinesToFile File="$(MSBuildProjectDirectory)/configured-tool.txt" Lines="$(FixtureSetting)" />'
            '</Target><Target Name="PreBuild" BeforeTargets="PreBuildEvent">'
            '<Copy SourceFiles="$(MSBuildProjectDirectory)/Platforms/Android/Resources/values/template/strings.xml" '
            'DestinationFiles="$(MSBuildProjectDirectory)/Platforms/Android/Resources/values/strings.xml" /></Target>')
        original = self.project.read_bytes()
        self.run_adapter('ios')
        self.assertEqual(original, self.project.read_bytes())
        self.assertEqual('from configuration', (self.app / 'configured-tool.txt').read_text().strip())
        self.assertTrue((self.resources / 'strings.xml').exists())

    def test_other_prebuild_steps_remain_unchanged(self):
        self.write_project('<Target Name="PreBuild" BeforeTargets="PreBuildEvent">'
            '<WriteLinesToFile File="$(MSBuildProjectDirectory)/original.txt" Lines="original" /></Target>')
        original = self.project.read_bytes()
        self.run_adapter()
        self.assertEqual(original, self.project.read_bytes())
        self.assertEqual('original', (self.app / 'original.txt').read_text().strip())

    def test_project_target_condition_is_preserved(self):
        self.write_project('<Target Name="PreBuild" BeforeTargets="PreBuildEvent" Condition="false">'
            + WINDOWS_COPY + '</Target>')
        original = self.project.read_bytes()
        self.run_adapter()
        self.assertEqual(original, self.project.read_bytes())
        self.assertFalse((self.resources / 'strings.xml').exists())
        self.assertIn('Condition="false"', self.project.read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
