# Oldi Chat source migration

This private repository receives the owner's existing local Oldi Chat 0.6.5 source snapshot.
The existing chat server and user data remain in place.
No credentials, Android signing keys, database files or production data are included.

Android update releases must retain the original signing certificate. CI verification is separate from publishing a signed update.

## Current migration

- Source: local snapshot bb8d4a4, version 0.6.5-beta / versionCode 14.
- Original snapshot: 198 tracked files. All source/assets retained; no old APK,
  keystore, databases, credentials, runtime folders or user data imported.
- Initial remote commit 46b9fd86519b0e5f6bd56c218b85ed2136c479a2 is preserved.
- CODEOWNERS now points to @Oldy-Chat.
- CI checks the Git index for excluded data, runs server tests on temporary
  loopback-only fixtures, compiles Android app/instrumentation Java, and runs lint.
- CI does not build, sign, upload or publish an installable APK/AAB.
- Owner update signing remains blocked until the original Android keystore is
  restored through a separate authorized step; no replacement key is generated.
- Existing chat server and data are not accessed, moved, changed or deleted.
- Aéza 2.56.174.123 remains separate and unused. Its optional workflow is disabled.
- Live YouTube playback, VPS configuration and live sticker generation remain
  unverified. Mocked/isolated test results are not production validation.

No SSH credentials or OpenAI keys are needed for these CI checks.

## Continuing development

Use this repository as the working source. Read this migration record first.
Do not run server/install.sh, tools/package-release.py, tools/update-publisher.py,
or tools/aeza/*.py as part of source verification. The historical README and
release tools are preserved, but their old deployment instructions are inactive.

The Android checks require JDK 17, Gradle 8.11.1 and SDK 36 on the CI runner.
Server checks require Python 3.12, cryptography, Pillow and ffmpeg/ffprobe.
Physical-device and emulator runtime checks are a separate future task.
