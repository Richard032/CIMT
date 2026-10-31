# Instruction-driven planning example

Use these text inputs with an application's existing working CIMT configuration. They demonstrate a focused objective, configuration alternatives, navigation back to a known screen and requirement checks. They do not assume a particular app or authorize unrelated actions.

Copy instructions.txt and requirements.txt into your test input folder. In its existing application.yaml, point inputs.instructions and inputs.requirements to those files:

```yaml
inputs:
  instructions: ./instructions.txt
  requirements: ./requirements.txt
```

Keep your own Git branch, build targets, platform/device selection, model, time/budget limits, credentials and private key configuration. The app must actually provide the described settings; missing features stay blocked/not tested rather than being invented.

Run using the normal command from any directory:

```sh
source /Users/Shared/CIMT/environment.sh
cimt run --config /absolute/path/default.private.yaml --run-config /absolute/path/application.yaml
```

The normal per-invocation report is created under that input folder's CIMT output/reports/report_<timestamp>. No user-created report/work folders are needed. Use the printed index.html path.

Expected demonstration: the AI first defines/selects a concrete task, identifies current controls, visits language settings, observes supported choices and tests the requested alternatives. It records state transitions and last-observed selected values, returns using known routes and checks the requirements. Other features need an explicit scope explanation instead of random taps. A path being visited does not prove its requirement passed. Permission blocks, missing settings and run limits remain explicit incomplete work. These files are an example, not recorded live acceptance.

For an offline demonstration of the same policy without a device or paid request, run the existing test module from the CIMT source folder:

```sh
/Users/Shared/CIMT/tools/python/bin/python -m unittest discover -s tests -p test_test_planner.py -v
```

The separate implementation layer is runtime/test_planning. It receives masked observations, instructions and requirements; it has no device/API/storage access. The current runtime adapter remains Mobile MCP. An Appium implementation can supply the same semantics after separate qualification.
