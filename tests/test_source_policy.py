import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('source_policy', Path(__file__).resolve().parents[1] / 'tools/check-source-policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class SourcePolicyTest(unittest.TestCase):
    def test_nested_credentials_and_runtime_files_are_rejected(self):
        for name in ('server/mail.env', 'server/.env.local', '.keys/beta.jks',
                     'backup/accounts.sqlite3-wal', 'copy/users.db', 'app/release.apk',
                     'uploads/photo.webp', 'credentials.json', '.ssh/oldi_work'):
            with self.subTest(name=name):
                self.assertTrue(policy.violations(name, b'fixture'))

    def test_secret_content_is_rejected_even_with_an_innocent_filename(self):
        for content in (b'-----BEGIN ' + b'OPENSSH PRIVATE KEY-----',
                        b'sk-proj-' + b'x' * 40, b'ghp_' + b'y' * 36,
                        b'SQLite format 3' + b'\x00', bytes.fromhex('feedfeed')):
            self.assertTrue(policy.violations('notes.txt', content))

    def test_source_assets_and_placeholder_variables_are_allowed(self):
        for name, content in (('server/server.py', b"key = os.environ.get('OLDY_STICKER_OPENAI_KEY')"),
                              ('app/src/main/assets/mascot.png', b'PNG fixture'),
                              ('tests/assets/player-test.mp4', b'synthetic video fixture')):
            self.assertEqual(policy.violations(name, content), [])
