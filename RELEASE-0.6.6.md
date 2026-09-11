# 0.6.6-beta — candidate validation

## Changes

- Larger four-tab navigation, regular-width labels, animated icons and a rounded
  hamburger button. The main menu includes the previously separate feature list.
- Taller emoji panel with a visible Stickers tab. Legacy square animation choices
  are removed from the picker; previously sent messages remain readable.
- Sticker creation from photo or description, explicit save, animated transparent
  WebP character output. Collection belongs to the authenticated account and can
  be restored on another signed-in device. Sending shares the sticker with the
  recipient without exposing the creator's private collection.
- Photo/description is submitted on Create. The progress screen gives an approximate
  one-minute estimate, then continues waiting if needed. No successful result is
  fabricated on provider failure. A saved digest cannot be allocated to another
  account/job; semantic uniqueness of every possible future image is not promised.
- Independent media service at Aéza 2.56.174.123 with certificate-pinned TLS.
  YouTube HTTPS is relayed there without decrypting the browser's Google TLS;
  unrelated chat traffic keeps its existing route.
- YouTube opens the selected browser session inside Oldi, with a menu option for
  the embedded player. Google login may be needed once. Android's required VPN
  permission remains a system prompt. On Android 8/9 the browser-session path is
  unavailable; the built-in view is used. Animated WebP playback uses Android 9+;
  Android 8 retains a still-image compatibility fallback.

## Delivery gates

The candidate must pass source policy, isolated server tests, Android compilation,
lint, native page alignment and the 0.6.6 emulator UI check. Sign the resulting
APK outside GitHub with the original certificate documented in MIGRATION.md.

The media deployment report records health, certificate and one bounded live
sticker generation check. A successful health response is not a YouTube playback
test. Real account sign-in, mobile playback and installation over the owner's
existing app still require the owner's device. Do not mark them as tested based
on the emulator fixture or direct HTTP headers.

## Recorded server result (2026-09-11)

Actions run 34549997288 deployed the independent service successfully. The bounded
live description test generated a 384×384 transparent WebP with 6 frames,
262,542 bytes, in 15.7 seconds. SHA-256:
0ce32166528d6cc57cb62a1600e257670f0fb72163f014a6cc33878d696282f3.
This verifies the provider connection and frame assembly on the new VPS. It does
not by itself verify a phone's authenticated creation/save/send workflow.
