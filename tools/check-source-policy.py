#!/usr/bin/env python3
"""Reject credentials and runtime data in the Git index; never print secret values."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_DIRS = {'.keys', '.ssh', '.gradle', '.venv', 'venv', 'node_modules',
                'build', '__pycache__', 'data', 'uploads', 'backups', 'releases'}
BLOCKED_NAMES = {'authorized_keys', 'known_hosts', 'credentials.json', 'secrets.json',
                 'signing.properties', 'key.properties', 'local.properties'}
PATH_PATTERN = re.compile(
    r'(?i)(?:\.(?:env|jks|keystore|pem|key|p12|pfx|der|sqlite\w*|db|apk|aab|apks|b64|log|pyc)(?:$|[.-])'
    r'|(?:^|/)(?:\.env|id_rsa|id_ed25519)(?:$|[.-]))'
)
CONTENT_PATTERNS = {
    'private key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'API token': re.compile(rb'\b(?:sk-proj-|sk-svcacct-|ghp_|github_pat_|gho_)[A-Za-z0-9_-]{20,}'),
    'OpenAI token': re.compile(rb'\bsk-[A-Za-z0-9]{40,}\b'),
    'SQLite database': re.compile(rb'^SQLite format 3\x00'),
    'Java keystore': re.compile(rb'^\xfe\xed\xfe\xed'),
}


def violations(name, content):
    path = PurePosixPath(name)
    issues = []
    if set(path.parts[:-1]) & BLOCKED_DIRS or path.name in BLOCKED_NAMES or PATH_PATTERN.search(name):
        issues.append('credential or runtime-data path')
    for label, pattern in CONTENT_PATTERNS.items():
        if pattern.search(content):
            issues.append(label)
    return issues


def main():
    entries = subprocess.check_output(['git', 'ls-files', '-s', '-z'], cwd=ROOT).split(b'\0')
    failures = []
    checked = 0
    for entry in entries:
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, sha, stage = metadata.decode().split()
        name = raw_name.decode()
        checked += 1
        if mode not in ('100644', '100755') or stage != '0':
            failures.append((name, 'unexpected Git entry or unresolved conflict'))
            continue
        content = subprocess.check_output(['git', 'cat-file', 'blob', sha], cwd=ROOT)
        failures.extend((name, reason) for reason in violations(name, content))
    for name, reason in failures:
        print(f'BLOCKED: {name}: {reason}', file=sys.stderr)
    if failures:
        return 1
    print(f'SOURCE_POLICY_PASS: {checked} indexed files; no forbidden paths or detected credentials.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
