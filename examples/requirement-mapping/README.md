# Requirement mapping example

This example shows the complete mapping report with synthetic data. It does not test an app and needs no API key or phone. Run from the CIMT source folder on a prepared Mac:

```bash
source /Users/Shared/CIMT/environment.sh
dotnet run --project tools/Cimt.RequirementDemo/Cimt.RequirementDemo.csproj -c Release
```

Expected: the command prints a report path under this example's ignored reports folder. Open index.html there. There are five requirements and five statuses: passed, failed, not tested, inconclusive, and overridden. The export conflict quotes “Do not test export.” Every item retains its original label, text, line range, and generated internal ID. Missing screenshots are explicitly explained.

**Exit 1 is expected:** the synthetic observations include a failure. Completion is incomplete because two requirements remain unresolved. No real test result is implied. Copy the whole report folder to retain its machine-readable catalogue, results, and input snapshots.

For a real run, use your normal default/private and application YAML. Point the existing inputs fields at your testable requirements and instructions:

```yaml
inputs:
  instructions: ./instructions.txt
  requirements: ./requirements.txt
```

Those paths resolve from the declaring YAML file. Requirements need no special IDs or grammar. Use separate paragraphs, list items, labelled items, or completed lines for separate results. Wrapped lines remain together. A compound item is assessed as a whole; split it into list items if you need separate decisions. Nothing nonblank is silently discarded, including headings or context; unclear or unevaluable items stay unresolved with an explanation. Replace these example expectations with ones that apply to your app.

Then use the existing public command:

```text
cimt run --config /absolute/path/default.private.yaml --run-config /absolute/path/app.yaml
```

A real run initializes all requirements before device actions. The model sees the catalogue and current statuses, and must reference known IDs. The report includes every applicable configured target/startup-device pair, including failed builds, locked devices, and objectives that did not start. Missing evidence cannot produce a pass. See [mapping rules](../../docs/requirement-mapping.md).
