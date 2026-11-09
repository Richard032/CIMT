# Redaction and test records

Implemented correction: 28 October 2026. Resolves D1 and D2 in the [design review](reviews/2026-10-28-design-contract-review.md), under the existing FR-28 and FR-36 requirements. No command, YAML field, or credential-source change is needed.

## Text and control data

Redaction removes configured credential values from observations and other free text. It does not rewrite fixed status words, generated IDs, numbers, JSON property names, or evidence links just because their characters match a configured secret. For example, a password of `failed` must be removed from an observation while the status failed remains a valid failure. Keeping that protocol word is not copying the password from its credential field.

The Python RecordRedactor handles checks, requirement results, actions, steps, crash reproduction actions, device identities, and device results separately. Each record type names its metadata and nested record types. Other fields are redacted as text by default. An arbitrary diagnostic field named status does not gain the exemption given to a known check status. Metadata exemptions accept scalar values, not arbitrary objects. UI references and control types also remain usable while displayed text is scrubbed.

CheckRecorder stores AI findings without evaluating their format or meaning under FR-96. Known status/source words and canonical requirement IDs retain their typed identity; other supplied text is scrubbed. Full original replies are untrusted text and always redacted. Unknown references remain unbound without updating a different catalogue item. Unknown statuses produce an inconclusive result rather than a format error. See [AI Resource Exchange](ai-resource-exchange.md).

The .NET JsonTextRedactor removes secrets from parsed string values before JSON encoding. ExecutionRedactor and RunReportRedactor preserve the metadata of each known record type. Final JSON is serialized after this transformation; replacement never runs over the serialized document. HTML escapes metadata without redacting it and redacts text before escaping. JSON details in HTML are sanitized as parsed data before they are displayed. Run identity, hashes, test statuses, numeric values, and generated relative evidence links remain intact.

The host and build worker share a small SecretText source implementation. Text replacement handles overlapping secrets in one pass and keeps the reserved `<redacted>` marker unchanged across repeated passes. Text filters recognize raw and supported JSON-escaped spellings in diagnostics. Configuration snapshots also scrub a credential embedded in another scalar value, rather than checking only whole-value equality. This does not claim detection of arbitrary encodings such as encrypted or base64 payloads.

## Screen masking

Secret detection searches original nested UI strings before JSON encoding. Unicode, quotes, backslashes, and newlines therefore cannot disappear from detection through JSON escaping. Detection remains separate from text replacement.

Known-secret detection, configured element-ID rules, and secure-field recognition require a pixel mask with reliable bounds. Required masking failure stops execution. Sensitive elements and overlapping child records hide text, label, name, and value fields before UI data is saved or sent to AI. Raw lossless PNG screenshots stay in memory until masking succeeds. Screen size and required mask geometry are checked before and after capture; invalid coordinates and image mapping stop capture. Clean image export removes transparency and metadata. See [screenshot masking](screenshot-masking.md) for the component contracts and tests.

These checks depend on the adapter supplying accurate UI text and bounds. Application-specific element-ID rules can identify sensitive fields whose values are not known, but the adapter must still expose their bounds. Separate UI and image reads cannot prove the absence of transient changes between reads. Offline image tests do not establish real Android/iOS masking acceptance.

## Verification

All 301 offline development checks passed: 165 .NET unit tests, 113 Python tests, and 23 CLI/build/example checks. New cases cover the `failed` status collision, requirement-ID collision, one-digit secrets, run-year collision, valid JSON, evidence links, escaped observations/diagnostics, repeated redaction, a secret beginning with the marker, unknown status handling, Unicode/quote/backslash/newline pixel masks, nested UI text, and required-mask failure. The report cases also inspect decoded HTML for raw and escaped secrets.

A separate synthetic handoff uses the actual Python CheckRecorder, completion policy, RunJournal, worker exit policy, and .NET RunReportWriter. The original instruction-only false-pass case now retains failed and exit 1 through both runtimes. Its temporary files are under `/private/tmp/cimt-redaction-fix-probe`; the full suite log is `/private/tmp/cimt-redaction-fix-checks-20261028.log`.

No API requests, real application builds, physical-device actions, or private configuration reads were used. Existing reports are historical evidence and are not rewritten. New output uses the corrected behavior.
