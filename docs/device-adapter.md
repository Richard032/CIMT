# Device Adapter

Updated: 1 November 2026. Implements FR-98 / AC-68 and the separate-folder requirement DR-01.

## Responsibility

The layer lives in runtime/device_adapter/. It provides device communication, platform identity, readiness checks, application lifecycle and verified masked screen observations. It performs supported device commands selected by execution. It does not choose test goals, interpret AI replies, select recovery actions for the app or decide whether another worker should stop.

| Module | Responsibility |
| --- | --- |
| mobile.py | Connect the device services and expose them to execution. |
| native.py | Make read-only native helper calls and classify/redact their failures. |
| readiness.py | Verify the device lock and platform readiness. |
| status.py, target.py | Read app/process/crash status and resolve platform identities. |
| startup.py | Probe adapter startup within a bounded recovery window. |
| app_lifecycle.py | Reset, install and launch the configured app. |
| mcp_client.py, rpc_messages.py | Handle MCP transport and mechanical RPC results. |
| screen_capture.py | Obtain verified masked UI information and pixels using shared privacy helpers. |

The adapter depends on common errors, privacy helpers and operating-system/tool I/O. It receives a shared-stop check callback from execution. It does not import AI, scenario/planning, evidence publication or stopping-policy implementations. AI Instruction and Context receives masked observations through the supplied adapter and remains input-only. Execution Stopping Policy owns final failure scope.

## Startup recovery

Before app setup, Mobile.connect checks cancellation and the device lock. DeviceStartup then calls only native apps list, checking the returned inventory is structured. This is a read-only probe; an empty app list can be valid. After success, Mobile rechecks readiness and shared stop before connecting MCP. No install/reset or AI action starts while readiness is unresolved.

Only the native helper's specific device-server startup answer becomes a retryable DeviceServerStartupError. NativeDevice classifies the answer at the command boundary and redacts the message before propagating it. Invalid JSON/inventory, device locks, permission/connection errors and ordinary process timeouts do not retry. The helper's five-second attempt timeout is unchanged; CIMT does not patch or rebuild it.

The cumulative recovery window is 90 seconds, starting with the first probe and capped by the whole-run deadline. Each subprocess receives at most 30 seconds or the remaining window. A known startup failure waits one second before another read-only probe. During waits, execution's shared-stop check runs at most 0.1 seconds apart. Cancellation after a probe is also checked before further setup. In-flight subprocesses retain the existing process/deadline cancellation limits.

Recovery ends on readiness, cancellation, shared stop, the run deadline or window exhaustion. A final process timeout clipped by the window following known startup failures is reported as exhaustion; an unrelated timeout fails immediately. The final error includes the probe count and last redacted failure. Retry activity is written to the existing terminal/HTML timeline. This is one window per device connection; it does not restart around individual app commands or targets.

After recovery fails, the existing infrastructure stopping policy applies. This increment does not change failure scope or final exit precedence. It never automatically repeats taps, swipes, typing, credentials, install/reset, app launch or provider requests. A helper that consistently needs more than five seconds for one attempt can still fail every probe; a longer recovery window is not a longer native attempt.

## Packaging and verification

Install the complete device_adapter/ folder. Remove the old flat mobile.py, app_lifecycle.py, device_commands.py, device_target.py, mcp_client.py, rpc_messages.py and screen_capture.py source modules. No new public command, configuration field or dependency is introduced. Shared privacy helpers retain their existing modules and behavior.

The existing unittest suite supplies fake clocks/commands for bounds, deadline, cancellation, failure classification, no-action retry and connection ordering. Import-boundary checks protect this layer and the existing AI/planning layers. Existing masking, lifecycle, RPC and platform tests use the moved modules. Offline tests do not establish successful recovery on a real emulator or device. Installation and live replay remain separate actions.

```mermaid
sequenceDiagram
    participant Run as Execution
    participant Adapter as Device Adapter
    participant Native as Unmodified Native Helper
    participant Stop as Execution Stopping Policy
    participant Inputs as AI Instruction and Context

    Run->>Adapter: Connect device; supply deadline and stop check
    Adapter->>Adapter: Check device lock
    loop Until ready or recovery/whole-run limit
        Adapter->>Run: Check shared stop and cancellation
        Adapter->>Native: Read-only apps list probe
        Native-->>Adapter: Inventory or startup failure
        Adapter->>Run: Record redacted retry activity if another probe is allowed
    end
    alt Ready
        Adapter->>Adapter: Recheck lock and connect MCP
        Adapter-->>Run: Ready for app setup
        Run->>Adapter: Perform app setup once
        Inputs->>Adapter: Request masked observations for AI inputs
        Adapter-->>Inputs: Verified masked UI and screenshot
    else Final failure
        Adapter-->>Run: Typed failure and diagnostics
        Run->>Stop: Determine stopping scope
        Stop-->>Run: Existing infrastructure or limit policy
    end
```
