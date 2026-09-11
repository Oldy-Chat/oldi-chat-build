# Oldi Chat 0.6.7-beta — release candidate

Package `chat.oldy`, versionCode **16**. Based on the latest migrated sources;
no older archive replaces newer repository changes. Sign only with the owner's
recovered original certificate, outside Git and CI test signing.

## Changes

- YouTube opens in Oldi's WebView. The explicit proxy is required: page and video
  connections go through the authenticated, pinned Aéza endpoint. Readiness requires
  a successful upstream YouTube TLS/HTTP exchange; proxy failure cannot fall back
  to direct YouTube. History, favorites, search, sharing and player access remain.
- Fixed fragmented photo uploads: a raw socket read is accumulated until the full
  bounded request arrives. Interrupted submissions retain their job UUID.
- Transparent animated stickers can be generated from photos or descriptions,
  previewed, saved to the account and sent to others. My and chat + expose both
  creation modes. A photo message also has a direct Create sticker action.
- Main Menu retains prominent YouTube and the primary destinations. Services are
  cards under Возможности. My owns profile, favorites, stickers, files/media,
  saved links, reminders and sessions. Settings contains configuration only;
  Archive belongs to Chats. Removed the redundant All features navigation level.
- Larger animated bottom icons and a larger hamburger button. Old square animated
  sticker choices are absent from the picker; existing messages remain readable.
- Message reminders: hour, tomorrow, week or chosen date. Quiet sending is available
  by holding Send. Smart favorites categorize links, photos, files and important
  messages, with a reminders shortcut.
- Multiple selected messages support summary, translation, explanation and task
  extraction through Aéza. Only the explicitly selected fragment is submitted;
  the provider key remains server-side and Responses storage is disabled.
- Voice messages can include automatic on-device Vosk text inside the encrypted
  attachment. Verified Russian and English models are bundled; disabling the
  option leaves ordinary voice sending available. Recognition failure never
  removes or replaces the recording. Bundled models increase APK size.
- Private watch-together invitations synchronize the official player's pause and
  position after both participants join. Signals must match account, peer, session
  and video. No unsolicited activity launch or cross-session player control.
- Shared polls, checklists, timer, random draw and choice wheel use encrypted
  messages with readable fallbacks for older clients. Includes a local pairs game.
- Optional event deletion is configured by the message author for private chats.
  Peer and configuration-specific receipts are required. The original remains
  locally until server deletion is confirmed. Both clients need protocol 5. Photo/video receipts follow the first viewer
  close, so deleting the remote source does not interrupt that viewing session.
- Additive account metadata supports expiring statuses and owned device/session
  management. It does not replace existing accounts, sessions or message tables.

## Evidence and remaining deployment gates

[Run 34564723585](https://github.com/Oldy-Chat/oldi-chat-build/actions/runs/34564723585)
passed server, Android compilation/lint and emulator checks for the menu/media
baseline at `3a9824b43a595bea52d349c85578fd0ee7f115db`.
The emulator blocked direct TCP/UDP 443 over IPv4/IPv6. YouTube's WebView received
bytes through Aéza and its player advanced to 6.45 seconds with readyState 4 and
no media error. Real photo-edit and text generation returned animated stickers;
Android preview, save and collection reload succeeded. Screenshots are in that
run's android-ui-report artifact.

The real photo edit used the existing **synthetic diagnostic cat**, not the
owner's three portraits. Those portrait crops were checked locally with a mocked
provider for upload/decoding; their real provider output is **not verified**.
Human reference photos, private keys, databases and user media are not in Git.

The media test uses a short-lived **loopback-only** copy of the current service on
Aéza, an isolated random test account, and an authenticated SSH forward. It neither
updates the public media service nor accesses an existing account's collection.
A test pass must not be described as a public deployment or a physical-phone test.

Current extended checks include local conversation fixtures, authorization of
expiry/watch signals, automatic voice text and actual selected-text generation
through Aéza. Consult the latest successful Actions run on PR #1 for their result.
A real simultaneous two-phone watch session remains an owner acceptance check.

The **public Aéza service still requires the approved main-branch deployment**.
Its installer preserves prior code releases and checks the loaded media source
hash from the public port. An unsuccessful local health check restores the prior
service unit. The old chat server is not deployed by the Aéza workflow.

**Statuses and device management additionally need the additive chat-server
update on the existing host.** That deployment has not been performed. Older
servers retain ordinary messaging; the client reports an unavailable session list.

Google account authorization is not silently imported from Chrome or the YouTube
app. Explicit browser login and embedded viewing have separate cookies. Android
may require its connection permission once. Neither Google sign-in, every video,
exact alarm timing under Doze nor every mobile carrier has been certified.

Do not publish an APK as a working update until the corresponding source checks,
original signing identity and required public service deployments are verified.
