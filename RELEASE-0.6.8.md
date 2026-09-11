# Oldi Chat 0.6.8-beta — candidate

Package `chat.oldy`, versionCode **17**. Builds on the repository's latest
0.6.7 changes. The original signing certificate is used outside Git and CI.

## User-facing changes

- The bottom-left destination is **Видеосвязь**. Choose up to four people from
  chats, contacts or search. Native WebRTC provides two-to-five-person calls,
  camera switching, camera/microphone controls and background call delivery.
  Media is pairwise DTLS-SRTP; direct connections use the existing Cloud TURN
  fallback when needed. Aéza and the YouTube route are separate.
- **Главная** returns to the chats screen with YouTube and the main menu.
  The intermediate services entry and poll/list/wheel/timer/draw creation
  entries have been removed. Existing messages remain readable.
- Chat **+ → Файл** accepts documents up to **400 MiB**. Encrypted records and
  bounded buffers handle large attachments without loading the entire file
  into RAM. The recipient saves the file through the Android document picker.
- Hold the microphone to record a voice message. Automatic transcription and
  the duplicate voice-recording action in the plus menu are removed.
  **Перевести в текст** runs bundled multilingual Whisper Small Q4 locally;
  no recording or transcript goes to a speech API. Russian and English are
  available. Transcription has a ten-minute input limit.
- **Моё → Заметки** provides searchable, pinnable notes saved automatically in
  the account's encrypted device vault and its backup. This does not claim
  automatic cross-device note synchronization.
- Hold your sent message, open **Действия → Редактировать**, and save text or
  a media caption. Author-signed edits keep the original message ID, replies
  and attachment. An **изменено** marker is shown; delayed delivery and
  encrypted history restoration replay the latest edit. Both participants
  need an app version that supports editing.
- The message composer enables keyboard correction/suggestion support. Actual
  suggestions depend on the installed keyboard and its language settings.
- Boot completion after first unlock and an in-place APK update restart the
  signed-in message delivery service. Android notification and manufacturer
  background/autostart permissions still apply. A user force-stop cannot be
  overridden by an app.
- Privacy copy describes implemented protections without claiming a security
  audit. YouTube, saved stickers and existing account data retain their prior
  storage and routing behavior.

## Deployment

The APK targets ARM64 and ARMv7 phones. The verification build additionally
contains x86-64 for the Android emulator. No signing key, API key, database or
user photo belongs in the repository or release archive.

Large files and channel/group edit routing require `tools/update-cloud-files.py` on the **existing Cloud
5.42.102.11**, not Aéza. It patches only the known upload limit and attachment
metadata allowlist and author-checked edit control handling. It preserves
newer unrelated code, backs up the previous
server source, restarts the same service and rolls back if health fails.
It does not run the full installer or retention tool, or open the database.

The old server has not been patched from this development workspace. Publishing
the APK and applying that narrow server patch are separate from building it.
The optional Yandex video-dubbing integration is not included.

## Verification

Required checks include the real 400 MiB cipher round trip under a 64 MiB Java
heap, isolated server integration tests, Android navigation/notes, bundled
speech recognition, authenticated message edits and reordered history, independent video peers, post-reboot authenticated polling,
and the existing Aéza media route. A compiled APK alone is not a passing release.
Physical-phone camera performance and manufacturer autostart behavior require
validation on those devices; emulator results are reported separately.
