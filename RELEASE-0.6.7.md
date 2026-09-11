# Oldi Chat 0.6.7-beta (candidate)

- Receive the complete photo body across TLS records. Previously a fragmented upload could fail with `BODY_INVALID` before a sticker job existed.
- Retry interrupted sticker submission with the original job UUID, so a lost acknowledgement cannot create a second generation.
- Open the YouTube site in Oldi's WebView by default. Require an authenticated Aeza CONNECT, verified YouTube TLS certificate and successful HTTP response before marking the route ready. Do not fall back to direct YouTube if explicit WebView proxy setup fails.
- Keep account credentials out of the tunnel process's account-vault loader. Only the session token is passed through an explicit, app-owned service intent.
- Expose photo and description creation directly in My. Keep the full feature list in Menu and remove the redundant All features item from My.

The old chat server, accounts, messages and production databases are not changed by this candidate. The new service remains on the separate Aeza VPS. No signing, SSH or provider keys are in the repository.

Verification: the fragmented-photo regression failed on 0.6.6 and passes with this change; 89 isolated server tests passed locally. Android CI adds real media checks using a short-lived loopback fixture on Aeza, an isolated test account, and an emulator with direct TCP/UDP 443 blocked. The fixture never changes the public media service or production account data. A test-fixture pass is not a claim that a user's network, Google sign-in or every video has been verified.

Do not publish this candidate as a working update until the route and sticker tests pass and the public media fix is deployed. The APK must be signed using the owner's recovered original key.
