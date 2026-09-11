import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cloud_file_patch', ROOT / 'tools/update-cloud-files.py')
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


class CloudFilePatchTest(unittest.TestCase):
    def source(self):
        return (ROOT / 'server/server.py').read_text().replace('419686400 if kind', '26214416 if kind').replace(
            "'blob_iv','blob_format','document'", "'blob_iv'").replace(",'edit_id','edit_version'", "").replace(",'edit_version','edit_id'", "").replace(",'edit'", "").replace(patcher.EDIT_VALIDATION, "")

    def test_patch_preserves_every_unrelated_byte_and_newer_changes(self):
        old = self.source() + '\n# A newer server-side change must survive.\n'
        expected = old.replace('26214416 if kind', '419686400 if kind').replace(
            "'op','mid','emoji'}", "'op','mid','emoji','blob_format','document','edit_id','edit_version'}").replace("('reaction','pin','unpin')", "('reaction','pin','unpin','edit')").replace("('publish','reaction','pin','unpin','signal','comment')", "('publish','reaction','pin','unpin','signal','comment','edit')")
        anchor="  if op=='reaction' and body.get('emoji','') not in ('','👍','❤️','🔥','😂','🤯','🎮'):raise Problem(400,'Неизвестная реакция')\n"
        expected=expected.replace(anchor, anchor+patcher.EDIT_VALIDATION)
        self.assertEqual(patcher.patch_source(old), expected)
        self.assertEqual(patcher.patch_source(expected), expected)

    def test_larger_future_limit_is_not_downgraded(self):
        future = (ROOT / 'server/server.py').read_text().replace('419686400 if kind', '600000000 if kind')
        self.assertEqual(patcher.patch_source(future), future)

    def test_unknown_source_refuses_before_mutation(self):
        for source in ('print("unknown")', self.source().replace('26214416 if kind', '123 if kind')):
            with self.assertRaises(ValueError):
                patcher.patch_source(source)

    def test_failed_health_rolls_back_and_preserves_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, data, backup = root / 'server.py', root / 'chat.db', root / 'backup'
            source = self.source()
            server.write_text(source)
            data.write_bytes(b'existing accounts and messages fixture')
            calls = []
            def restart():
                calls.append(server.read_text())
                if len(calls) == 1:
                    raise RuntimeError('new process failed')
            with self.assertRaises(RuntimeError):
                patcher.install_patch(server, backup, restart)
            self.assertEqual(server.read_text(), source)
            self.assertEqual((backup / 'server.py').read_text(), source)
            self.assertEqual(data.read_bytes(), b'existing accounts and messages fixture')
            self.assertEqual(len(calls), 2)

    def test_success_restarts_once_and_repeat_does_not_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server = root / 'server.py'
            server.write_text(self.source())
            calls = []
            self.assertTrue(patcher.install_patch(server, root / 'backup', lambda: calls.append(True)))
            self.assertFalse(patcher.install_patch(server, root / 'second', lambda: calls.append(True)))
            self.assertEqual(calls, [True])


if __name__ == '__main__':
    unittest.main()
