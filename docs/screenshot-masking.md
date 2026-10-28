# Screenshot masking

Implemented correction: 28 October 2026, under FR-28 and FR-36. Commands and YAML stay unchanged. Masking rules still use element IDs only; users do not supply screen rectangles.

## Capture and release

The production adapter reads full-frame lossless PNG from the installed native helper using binary stdout. It does not use the Mobile MCP screenshot tool's JPEG conversion. Raw screenshot bytes remain in memory and are never written as an intermediate file.

ScreenCapture checks device readiness, reads screen size and UI elements, captures the PNG, then reads UI elements and screen size again. It checks readiness again before masking. A size change or a change in required sensitive regions stops capture. Reordering the same regions is allowed; added or removed duplicate regions are still a change. Invalid structured UI data is rejected.

ScreenshotImage accepts a valid, single-frame PNG with matching pixel orientation. JPEG, animated images, corrupt images, and rotated EXIF orientation are rejected. Pixels are copied onto a fresh opaque black canvas before masking. This removes hidden transparent RGB data and source metadata. The output is an RGB PNG with no copied metadata.

ScreenMasker returns UI data and image bytes only after all required geometry and image checks succeed. A failure produces no image for storage or AI. The existing run error/report path records the failure. No extra AI request is needed.

## Mask geometry and UI text

MaskGeometry validates finite, positive screen dimensions and finite rectangle coordinates with positive width/height. It also rejects overflowed rectangle edges and non-finite scale factors. Screen and image scale may differ by at most one image pixel of rounding; rotation or a larger aspect mismatch stops capture.

Partly visible rectangles are clipped before scaling. A sensitive field with valid bounds completely outside the screen has no pixels to paint, but its UI text stays hidden. Missing or invalid required bounds stop capture. Pixel edges round outward, with a two-image-pixel border on every side. This covers fractional coordinates and smaller screenshots without relying on drawing-library truncation.

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

The first Mac's inventory found an authorized Android phone. Its read-only probe stopped at the lock check before any capture or app action. The product owner then requested skipping physical-device checks for now. No aggregate live masking pass is claimed. The iOS inventory showed paired devices unavailable, and one wired device still pairing/disconnected; no ready iPhone control session was available. No raw screenshots or UI text were saved by this probe. Aggregate outcome data remains local under `/private/tmp/cimt-screenshot-masking-live-20261028`.

These checks depend on the adapter supplying accurate, complete UI bounds and a matching full-frame image. Element-ID rules can identify sensitive elements even when their text is not a configured secret, but the adapter must still expose those elements and their bounds. Screenshots and UI reads are separate operations: matching before/after data cannot prove that no transient change occurred between them. This implementation does not use OCR and does not claim that unlisted sensitive pixels can always be detected. Real Android/iOS credential-entry, layout/orientation, and interruption acceptance remains required; no product requirement was relaxed.
