# Device Adapter

> Contract and dated evidence: later refinements supersede earlier wording. Recorded test counts and live observations belong to their stated dates, not the current full-suite result. See [implementation status](implementation-status.md), [release readiness](release-1.0.md), and the [current usage guide](product-guide.md).

Updated: 1 November 2026. Implements FR-98 / AC-68 and FR-100 / AC-70 and the separate-folder requirement DR-01.

## Responsibility

The layer lives in runtime/device_adapter/. It provides device communication, platform identity, readiness checks, application lifecycle and verified masked screen observations. It performs supported device commands selected by execution. It does not choose test goals, interpret AI replies, select recovery actions for the app or decide whether another worker should stop.

| Module | Responsibility |
| --- | --- |
| mobile.py | Connect the device services and expose them to execution. |
| native.py | Make read-only native helper calls and classify/redact their failures. |
| readiness.py | Verify the device lock and platform readiness. |
| status.py, target.py | Read app/process/crash status and resolve platform identities. |
| startup.py | Probe adapter startup within a bounded recovery window. |
| app_lifecycle.py | Reset, install and launch the configured app; wait for startup to settle. |
| mcp_client.py, rpc_messages.py | Handle MCP transport and mechanical RPC results. |
| screen_capture.py | Obtain verified masked UI information and pixels using shared privacy helpers. |

The adapter depends on common errors, privacy helpers and operating-system/tool I/O. It receives a shared-stop check callback from execution. It does not import AI, scenario/planning, evidence publication or stopping-policy implementations. AI Instruction and Context receives masked observations through the supplied adapter and remains input-only. Execution Stopping Policy owns final failure scope.

## Replacement boundaries

The device adapter is separate from AI decision making. The Python composition root can inject a device factory for tests or another integration. Production startup and execution still expect Mobile MCP.

| Boundary | Current dependency | What a replacement needs |
| --- | --- | --- |
| Host discovery and readiness | DeviceDiscovery and ReadinessValidator load the Mobile MCP Node module. WorkPreparation and RunCleanup own the helper home and daemon. | Supply inventory, owned startup and shutdown, and diagnostics through a host device service. Keep device selection and run ownership in the host. |
| Worker preflight and construction | Execution checks for Node and mcp-server-mobile and gives Mobile the native binary and run context. | Let the selected backend check its own prerequisites and supply its own worker adapter. |
| Actions and recovery | ActionExecutor and crash recovery call MCP tool names and assemble backend-specific arguments. Swipe evidence also names the provider tool. | Expose operations such as tap, type, swipe, back, launch and terminate through a device contract. Have the implementation translate calls and report the actual tool and parameters. |
| Observations and lifecycle | Execution consumes verified masked screenshots, elements, app identity and crash records. It assumes the TestPilot screen-size record, device-coordinate bounds and current target refs. | Standardize those data and behavior guarantees, including credential masking, typed errors, cancellation, reset and foreground checks. |

A neutral action contract would make a second worker adapter easier to test. Replacing Mobile MCP throughout run, replay and validate additionally requires the host discovery, readiness and cleanup boundary. The build and AI decision interfaces can stay separate from both. Verify a replacement using the existing offline suites and qualify the actual device platforms separately.

## Android app memory

The AI can request the read-only `sample_memory` command at any point when the tested app is running on Android. TestPilot uses ADB on the selected device and measures the main process of the installed app. Action feedback contains total PSS and RSS in KiB and the PID. Compare the samples at comparable checkpoints in the same process. Missing readings produce command feedback without fabricated metrics.

## Startup recovery

Before app setup, Mobile.connect checks cancellation and the device lock. DeviceStartup then calls only native apps list, checking the returned inventory is structured. This is a read-only probe; an empty app list can be valid. After success, Mobile rechecks readiness and shared stop before connecting MCP. No install/reset or AI action starts while readiness is unresolved.

Only the native helper's specific device-server startup answer becomes a retryable DeviceServerStartupError. NativeDevice classifies the answer at the command boundary and redacts the message before propagating it. Invalid JSON/inventory, device locks, permission/connection errors and ordinary process timeouts do not retry. The helper's five-second attempt timeout is unchanged; TestPilot does not patch or rebuild it.

The cumulative recovery window is 90 seconds, starting with the first probe and capped by the whole-run deadline. Each subprocess receives at most 30 seconds or the remaining window. A known startup failure waits one second before another read-only probe. During waits, execution's shared-stop check runs at most 0.1 seconds apart. Cancellation after a probe is also checked before further setup. In-flight subprocesses retain the existing process/deadline cancellation limits.

Recovery ends on readiness, cancellation, shared stop, the run deadline or window exhaustion. A final process timeout clipped by the window following known startup failures is reported as exhaustion; an unrelated timeout fails immediately. The final error includes the probe count and last redacted failure. Retry activity is written to the existing terminal/HTML timeline. This is one window per device connection; it does not restart around individual app commands or targets.

After recovery fails, the existing infrastructure stopping policy applies. This increment does not change failure scope or final exit precedence. It never automatically repeats taps, swipes, typing, credentials, install/reset, app launch or provider requests. A helper that consistently needs more than five seconds for one attempt can still fail every probe; a longer recovery window is not a longer native attempt.

## Wait before effective app testing

After successful reset/install/launch, Mobile.reset calls AppLifecycle.wait_after_launch before returning to the scenario. The wait lasts 20 seconds and is logged as an explicit activity operation. It precedes the first masked capture, startup/foreground check and AI request. Mobile supplies execution's shared-stop check; AppLifecycle uses a monotonic duration and 0.1-second sleep chunks, with checks before sleeping and on completion. Cancellation, shared stop or the run deadline end the wait and prevent subsequent checks.

This belongs entirely to TestPilot. The helper is already connected during installation; the wait does not delay its process startup, patch source or change an internal timeout. Failed setup never waits. The new interval applies to each successful scenario installation on either platform/device kind, not every tap, normal AI command, app restart or crash relaunch. It is a settling delay, not a foreground-specific retry or proof that the historical error is fixed.

## Packaging and verification

Install the complete device_adapter/ folder. Remove the old flat mobile.py, app_lifecycle.py, device_commands.py, device_target.py, mcp_client.py, rpc_messages.py and screen_capture.py source modules. No new public command, configuration field or dependency is introduced. Shared privacy helpers retain their existing modules and behavior.

The existing unittest suite supplies fake clocks/commands for bounds, deadline, cancellation, failure classification, no-action retry and connection ordering. Import-boundary checks protect this layer and the existing AI/planning layers. Existing masking, lifecycle, RPC and platform tests use the moved modules. Offline tests do not establish successful recovery on a real emulator or device. Installation and live replay remain separate actions.

```mermaid
sequenceDiagram
    participant Run as Execution
    participant Adapter as Device Adapter
    participant Native as Unmodified native helper
    participant Stop as Execution Stopping Policy
    participant Inputs as AI Instruction and Context

    Run->>Adapter: Connect with deadline and shared-stop callback
    Adapter->>Adapter: Check device lock
    loop Probe until ready or final failure, within 90 seconds and whole-run deadline
        Adapter->>Run: Check shared stop and cancellation
        Adapter->>Native: Read-only apps list probe
        Native-->>Adapter: Inventory or typed failure
        alt Valid inventory, including empty inventory
            Adapter->>Adapter: Mark ready and leave probe loop
        else Known device-server startup error and time remains
            Adapter->>Run: Record redacted retry activity
            Adapter->>Adapter: Wait one second with cancellation checks
        else Other error or exhausted window
            Adapter->>Adapter: Leave probe loop with failure; no automatic retry
        end
    end
    alt Ready
        Adapter->>Adapter: Recheck lock and connect MCP
        Adapter-->>Run: Ready for app setup
        Run->>Adapter: Reset, optional fixture transfer and launch once
        Adapter->>Adapter: After success, wait 20 seconds with shared-stop checks
        Adapter-->>Run: Ready for first screen and foreground/startup checks
        Inputs->>Adapter: Request current masked observation
        Adapter-->>Inputs: Verified masked UI and screenshot
    else Final preparation failure
        Adapter-->>Run: Typed failure and redacted diagnostics
        Run->>Stop: Determine stopping scope
        Stop-->>Run: Existing local or shared failure policy
    end
```
