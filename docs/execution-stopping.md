# Execution Stopping Policy

Date: 31 October 2026.

## Responsibility

The separate `runtime/stopping_policy/` layer makes stopping decisions without calling devices, clocks, storage or AI. Its rules are in policy.py, with a package entry point in __init__.py. Execution services keep their own operational responsibilities: RunControl checks the deadline and user interruption; Budget reserves shared spending; startup/crash services gather evidence and count matching crashes; DeviceRunner saves failures and closes its connection; the scheduler waits for the other workers. The policy supplies failure scope, the matching-crash threshold and final exit precedence. DR-01 requires this layer and every future layer to have a separate source folder.

This layer does not filter AI context, select an exploration path or decide whether an application action is useful. Those responsibilities stay with the AI planning and recovery layer.

## Scope rules

| Condition | Scope | Result |
| --- | --- | --- |
| Adapter answers a launch or relaunch request with an app launch failure | Affected device | Save the launch error and partial observations, close that device connection and continue the other active or queued devices. |
| Device is locked | Affected device | Save the readiness limit and continue other devices. |
| Three matching crashes at the same point | Affected scenario | Save the failed/incomplete scenario and continue the remaining scenarios. |
| Whole-run deadline, shared AI budget or user interruption | Whole run | Stop device work through the existing shared control and retain observations. |
| Blocking infrastructure failure, including adapter connection/protocol/timeouts, disconnection, AI failure, reset verification, required masking or evidence storage | Whole run | Preserve the failure and stop the remaining work safely. |

An app launch failure is recognized by the operation and the adapter's answered error result, not by platform names or error-text keywords. The RPC boundary raises AppLaunchError only for an answered `mobile_launch_app` failure. A timeout, closed connection or protocol error remains an InfrastructureError and keeps the whole-run policy. Device readiness raises DeviceLocked for a verified lock. Other limits remain shared.

## Reporting and exit precedence

A local failure does not become a successful test merely because another device completes. The combined report retains every device's observations. Existing exit precedence stays unchanged: 3 for configuration/infrastructure errors, then 1 for application failure/crash, then 2 for incomplete work, otherwise 0. An adapter-reported launch error remains an error contributing exit 3. Crash observations collected before a failed relaunch remain visible too.

## Regression checks

The existing Python unit suites cover both directions: iOS launch failure followed by Android completion, and Android launch failure followed by iOS completion. They verify preserved failure reporting, no shared stop signal, no false cancellation for the continuing device and final error precedence. Separate cases check redacted launch errors, unchanged successful tool results, global handling for other tool errors, typed device locks, shared limits and the third-crash boundary.

These checks use synthetic device operations. They do not establish that an application with a startup defect now launches, or that a live two-device replay has passed.
