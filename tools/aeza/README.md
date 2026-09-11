# Separate Aéza media service

Target: `2.56.174.123:22` (administration), `2.56.174.123:9443` (pinned media TLS).
The existing chat server `5.42.102.11` stays in place. Its database, accounts,
messages and files are never copied into the media service.

## Configuration

Repository Actions secrets:

- `AEZA_SSH_KNOWN_HOSTS`: the public host-key line obtained from the trusted VPS
  console, containing the IP, `ssh-ed25519` and its public key.
- `AEZA_SSH_PRIVATE_KEY`: the complete dedicated private SSH key. The matching
  public key must already be authorized for this VPS; preserve existing keys.
- `AEZA_SSH_USER`: the existing SSH login, currently `root`.
- `AEZA_SSH_KEY_PASSPHRASE`: only if that key has a passphrase.
- `OLDY_STICKER_OPENAI_KEY`: the provider key; stored on the server outside code.

Never commit those values or print them in diagnostics. Host verification is
strict. The only files uploaded by the media installer are the media handler,
collection, generation and selected-text modules. Provider configuration and TLS
keys remain under `/etc/oldi-media`; media data remains `/var/lib/oldi-media`.

## Verification and deployment

`aeza-access.yml` checks access and public YouTube reachability. That is not a
playback check. `android.yml` separately runs a disposable Android emulator with
direct HTTPS blocked. It tests pinned Aéza CONNECT, YouTube page/video playback,
real sticker generation, preview and account collection persistence. The route
fixture binds only VPS loopback and exits when its SSH session closes.

`aeza-media.yml` deploys the independent public media service on changes to main.
Feature-branch test fixtures do not publish it. The installer validates package
syntax before activation, retains prior code releases, and verifies the actual
loaded source hash at `/health`. The external runner verifies the pinned public
port and source hash too. A health failure after replacing an existing service
unit restores that unit; no old chat-server restart is involved.

The cached `service-check.webp` is a synthetic diagnostic cat. Its cached
provider result is historical evidence only. Fresh Android media test results,
including their source commit, are documented in `RELEASE-0.6.7.md` and Actions.
