#!/usr/bin/env python3
"""Run the server suite with temporary data and loopback-only connections."""
import ipaddress
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def loopback_only(event, args):
    if event != 'socket.connect':
        return
    address = args[1]
    if isinstance(address, str):  # Unix sockets do not leave the runner.
        return
    host = address[0]
    if host == 'localhost':
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise RuntimeError('CI server tests cannot connect to external services')


def main():
    if not all(shutil.which(binary) for binary in ('ffmpeg', 'ffprobe')):
        raise SystemExit('ffmpeg and ffprobe are required; media checks must not be silently skipped.')
    # Never inherit a real key, mail account, release directory or production data path.
    for name in list(os.environ):
        if name.startswith(('OLDY_', 'AEZA_')):
            del os.environ[name]
    sys.addaudithook(loopback_only)
    with tempfile.TemporaryDirectory(prefix='oldi-ci-') as temporary:
        os.environ['OLDY_DATA'] = temporary
        sys.path.insert(0, str(ROOT / 'tests'))
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_*.py')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
