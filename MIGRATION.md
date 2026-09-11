# Oldi Chat source migration

This private repository is the working source for the owner's Oldi Chat.
The original 0.6.5 snapshot and remote history are preserved. No credentials,
Android signing keys, database files or production data are included.

## Source comparison

- Imported snapshot bb8d4a4: 0.6.5-beta / versionCode 14, 198 tracked source/assets.
- The subsequently supplied Sources-and-History archive contains no Android files
  missing from this repository: 167 identical, 31 older differences.
- Newer CI/lint fixes were retained; old archives did not overwrite current code.
- Original remote commit 46b9fd86519b0e5f6bd56c218b85ed2136c479a2 remains in history.
- CODEOWNERS points to @Oldy-Chat.
- Current candidate: 0.6.6-beta / versionCode 15 / chat.oldy.
- Original signing key was recovered outside the repository. Certificate SHA-256:
  c431f53f373f72eef0a013d61cfe0017255a986d22abb81f3dab4e5ce9720ec2.
  Never create a replacement update key or commit the recovered keystore.

## Separate services

- Existing chat server: 5.42.102.11. Do not deploy, migrate, remove or rewrite its
  service/data as part of this update. Media authentication only validates the
  existing user's session with the certificate-pinned read-only /me endpoint.
- New Aéza: 2.56.174.123, only YouTube transport and private sticker creation/storage.
  Owner authorized this independent installation and supplied GitHub Actions secrets.
- The media workflow uses strict pinned SSH host verification. It only installs
  oldi-media under /opt/oldi-media, /etc/oldi-media and /var/lib/oldi-media.
- TLS keys, provider configuration, media storage key and SQLite stay on the new
  VPS. Existing certificate and storage key are reused on updates.
- media-service.json pins the public media certificate in the Android client.

## Verification and packaging

Source-policy checks the Git index for credentials and runtime data. Server tests
use temporary, loopback-only fixtures. Android verification uses JDK 17,
Gradle 8.11.1 and SDK 36. The runtime UI fixture uses a disposable test signature
and an unreachable loopback chat endpoint, never production registration.

The unsigned-update-candidate CI artifact is an intermediate, not a user update.
Sign it only with the restored owner key and check the certificate above.
Never distribute the debug-signed emulator build. Do not run server/install.sh,
tools/package-release.py or tools/update-publisher.py against the old server.

Live media generation and phone playback results must be stated separately from
mocked tests; see RELEASE-0.6.6.md and the relevant Actions run reports.
