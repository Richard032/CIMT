# Automatic output folders

The installed CIMT runs from any folder. The user supplies only YAML configuration,
referenced text inputs, and optional custom scripts. Output folders are created by CIMT.

For example, prepare these inputs using the supplied application example:

```text
testing/FirstRun/
  default.private.yaml
  application.yaml
  inputs/instructions.txt
  inputs/requirements.txt
  inputs/setup.txt
  build/                     # optional application-specific scripts
```

Do not create CIMT output, work, or reports. Do not add workspace.root or reports.root.
Older private settings with those keys still load, but CIMT ignores the values and records a notice.

From FirstRun:

```bash
source /Users/Shared/CIMT/environment.sh
cimt validate --config ./default.private.yaml --run-config ./application.yaml
cimt run --config ./default.private.yaml --run-config ./application.yaml
```

From another folder, pass absolute configuration paths or relative paths that reach
the same files. The folder containing application.yaml remains the output parent.
When --run-config is absent, the folder containing --config is used instead.

CIMT creates CIMT output/reports/report_<date-time>/index.html. Execution also creates
CIMT output/work/work_<date-time> when clone work is needed, then removes that owned
work during cleanup. The paired names share a timestamp. Existing reports stay intact.

Missing or invalid YAML still produces a report beside the selected inputs when that
folder is writable. An unsafe or unwritable output location stops with a terminal
error, without creating a fallback output tree elsewhere.

## Runnable offline demonstration

From a CIMT source checkout with the current host built:

```bash
source /Users/Shared/CIMT/environment.sh
/Users/Shared/CIMT/tools/python/bin/python tests/check-output-layout.py
```

To check the installed launcher instead:

```bash
/Users/Shared/CIMT/tools/python/bin/python tests/check-output-layout.py \
  --command /Users/Shared/CIMT/bin/cimt
```

The demonstration creates disposable input folders, uses synthetic credentials and
fake readiness tools, and invokes the real public validate command from two launch
folders. It verifies automatic creation, paths with spaces, retained earlier reports,
ignored legacy roots, and local reports for missing/invalid YAML. Expected result:
five checks pass. It performs no API request, real repository access, build, or phone action.
