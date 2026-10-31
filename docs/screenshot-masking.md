# Screenshot masking

Implemented correction: 28 October 2026, under FR-28 and FR-36. Commands and YAML stay unchanged. Masking rules still use element IDs only; users do not supply screen rectangles.

## Capture and release

The production adapter reads full-frame lossless PNG from the installed native helper using binary stdout. It does not use the Mobile MCP screenshot tool's JPEG conversion. Raw screenshot bytes remain in memory and are never written as an intermediate file.

ScreenCapture checks device readiness, reads screen size and UI elements, captures the PNG, then reads UI elements and screen size again. It checks readiness again before masking. A size change or a change in required sensitive regions rejects that capture. ScreenCapture retries only these valid transition changes, with up to three fresh attempts and a 250 ms wait between attempts within the run deadline. Every candidate repeats the full checks; exhaustion stops execution without releasing an image. Invalid geometry, image data, tool errors, and lock errors are not retried. Reordering the same regions is allowed; added or removed duplicate regions are still a change. Invalid structured UI data is rejected.

ScreenshotImage accepts a valid, single-frame PNG with matching pixel orientation. JPEG, animated images, corrupt images, and rotated EXIF orientation are rejected. Pixels are copied onto a fresh opaque black canvas before masking. This removes hidden transparent RGB data and source metadata. The output is an RGB PNG with no copied metadata.

ScreenMasker returns UI data and image bytes only after all required geometry and image checks succeed. A failure produces no image for storage or AI. The existing run error/report path records the failure. No extra AI request is needed.

## Mask geometry and UI text

MaskGeometry validates finite, positive screen dimensions and finite rectangle coordinates with positive width/height. It also rejects overflowed rectangle edges and non-finite scale factors. The horizontal and vertical image scales are `sx = imageWidth / screenWidth` and `sy = imageHeight / screenHeight`. Their ratio `sx / sy` must be within **0.95 through 1.05**, inclusive (±5%, with a small floating-point epsilon at the boundary). This is a relative check shared by physical and virtual devices on both platforms. It is independent of native pixel-density metadata and supports uniform resizing. A rotated frame or a mismatch outside the permitted ratio stops capture.

Partly visible rectangles are clipped before scaling. A sensitive field with valid bounds completely outside the screen has no pixels to paint, but its UI text stays hidden. Missing or invalid required bounds stop capture. Pixel edges round outward. Each axis retains a two-image-pixel border and adds the rounded-up full-screen drift between the two accepted scales: `ceil(abs(sx - sy) * screenAxisSize)`. The extra border covers mapping uncertainty instead of exposing secret edges when tolerance is used. With identical scales, the border stays two pixels.

Configured element IDs, secure-field type/identifier hints, and configured secrets in original nested UI strings identify required masks. Sensitive text values are hidden in both the image and the returned UI data. A container mask also hides text in overlapping child records. When masks exist and another UI text record has no reliable bounds, its text is hidden conservatively. That record does not expand the pixel mask. References and control types remain usable for navigation.

## Components and testing

Each module has a small responsibility:

| Module | Responsibility |
| --- | --- |
| device_commands.py | Read native PNG bytes for the fixed device within the run deadline. |
| screenshot_image.py | Decode a verified image onto a clean canvas and encode the result. |
| mask_geometry.py | Validate coordinates, map them to pixels, and test overlap. |
| capture_guard.py | Compare observable size and required mask regions around capture. |
| redaction.py | Choose sensitive elements, draw their masks, and hide corresponding UI text. |
| screen_capture.py | Order capture, verification, masking, and the safe return value. |

The development suite passes 343 checks: 165 .NET unit tests, 155 Python tests, and 23 CLI/build/example checks. Image and geometry cases use small invented pictures and data. They cover transparency, metadata, PNG-only capture, image corruption/orientation/animation, scaled/fractional/clipped/offscreen rectangles, NaN/infinity/overflow, size changes, region reordering/duplicates, container text, missing bounds, and the native binary command contract. Existing Unicode/escaped-secret and appearing/disappearing/moving-field regressions also pass. Run `bash scripts/check-development.sh` from the source folder.

## Physical-device acceptance and limits

On 28 October, the first Mac's Android probe stopped at the lock check, and no ready iPhone session was available. The product owner requested skipping physical checks at that time. That attempt did not establish a live masking pass. Its aggregate result remains local under `/private/tmp/cimt-screenshot-masking-live-20261028`.

On 29 October, the product owner connected both devices and verification resumed. Both were online and passed the production readiness check. Android passed immediately. The connected iPhone initially had no DeviceKit helper installed, so its UI read failed before screenshot capture. Installation with an existing profile that also matched a valid local signing identity succeeded; the repeated iPhone check then passed.

| Physical platform | Returned PNG | Visible selected masks | Hidden text fields | Result |
| --- | --- | --- | --- | --- |
| Android | 1080 × 2340 | 1 | 2 | Passed |
| iOS | 828 × 1792 | 1 | 4 | Passed after helper installation |

Each check selected a visible element with an identifier and text from the current screen, treated that identifier as a configured masking rule, and called the production Mobile.snapshot path. It verified that every pixel in the selected mask was black, corresponding returned UI text was `<masked>`, and the result was an RGB PNG with no image metadata. All 28 installed runtime modules matched source. The checks ran sequentially, without AI requests, real MAUI builds, navigation, typing, resets, or application-data changes. Installing the separate iPhone automation helper was the only device setup change. Raw screenshots and UI responses stayed in memory; the probe discarded MCP diagnostic output and retained aggregate outcomes locally under `/private/tmp/cimt-screenshot-masking-live-20261029`.

This establishes a live capture/masking smoke check on both connected platforms. The selected fields were not entered credentials, and no real application scenario or orientation change was exercised. The earlier failed attempts remain part of the history.

These checks depend on the adapter supplying accurate, complete UI bounds and a matching full-frame image. Element-ID rules can identify sensitive elements even when their text is not a configured secret, but the adapter must still expose those elements and their bounds. Screenshots and UI reads are separate operations: matching before/after data cannot prove that no transient change occurred between them. This implementation does not use OCR and does not claim that unlisted sensitive pixels can always be detected. Real Android/iOS credential-entry, layout/orientation, and interruption acceptance remains required; no product requirement was relaxed.

## 30 October 2026: permission dialog transition

The observed run report_2026-10-30_12-36-25-944 changed from login/password controls to an OS Bluetooth permission alert during initial capture. Immediate rejection stopped the worker before step 0 or any AI request, so there was no screenshot to display. The new bounded policy discards that unstable frame and can capture the settled alert without treating it as an app failure. It does not release the rejected image or rewrite the historical report. Mobile records retries as chronological activity; HTML explicitly explains a scenario with no verified screenshot.

The non-atomic capture limitations above still apply. Retries do not prove that the screen never changed between observations. They use the same validated observations and masking boundary as the original capture path.

Permission decisions are controlled by testing instructions. The AI guidance requires explicit authorization to accept or deny an OS request; otherwise a blocking prompt is reported as blocked/incomplete, not a permission-only app failure. Capture retries only collect images and never click dialog buttons. For the local TestRun_SingleDevice_SingleTarget inputs only, instructions now authorize Allow (or its equivalent) for the tested ECON-M application. FirstRun and public example instructions were not given that authorization.

## Generic mapping tolerance correction — 31 October 2026

The first virtual-device run built and installed both apps, but stopped before AI inference because the helper returned one pixel less width than the simulator's reported screen size implied. The product owner requested a generic ±5% correction. CIMT applies the same relative scale-ratio rule to every device and expands masks for accepted scale differences. Native PNG capture through binary stdout, image/region validation and fail-closed behavior remain. No third-party tool source changes or raw-file capture fallback were added.

The existing Python suite passes 234 unit tests, including both 5% boundaries, just-outside rejection, the real simulator dimensions without platform metadata, uniform downscaling, large mismatch rejection, expanded mask bounds and synthetic secret-pixel masking. The 22 runtime-policy checks also pass. Real replay qualification is recorded separately.
