import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess

from retroid_archive.adb import build_plan, deploy, parse_devices, validate_remote


class AdbTests(unittest.TestCase):
    def test_device_parser_only_accepts_authorized_devices(self):
        output = 'List of devices attached\nABC123\tdevice product:x\nOFF\toffline\nBAD\tunauthorized\n'
        self.assertEqual(parse_devices(output), ['ABC123'])

    def test_plan_contains_relative_files_and_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'gba').mkdir()
            (root / 'gba' / 'Game.gba').write_bytes(b'owned')
            (root / 'gba' / 'notes.txt').write_text('ignore')
            plan = build_plan(root, '/storage/1234-5678/ROMs')
            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0]['remote'], '/storage/1234-5678/ROMs/gba/Game.gba')
            self.assertEqual(len(plan[0]['sha256']), 64)

    def test_remote_path_rejects_shell_metacharacters(self):
        for path in ('/sdcard/ROMs;reboot', '/storage/123/../ROMs', '/tmp/ROMs'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_remote(path)

    def test_deploy_skips_file_already_verified_on_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'gba').mkdir()
            (root / 'gba' / 'Game.gba').write_bytes(b'owned')
            plan = build_plan(root, '/sdcard/ROMs')
            calls = []

            def runner(args):
                calls.append(args)
                if args == ['adb', 'devices', '-l']:
                    return CompletedProcess(args, 0, 'List of devices attached\nABC\tdevice\n', '')
                if 'df -k' in args[-1]:
                    return CompletedProcess(args, 0, 'Filesystem 1K-blocks Used Available Use% Mounted\n/data 10000 1 9999 1% /sdcard\n', '')
                return CompletedProcess(args, 0, plan[0]['sha256'] + '  file\n', '')

            report = deploy(plan, '/sdcard/ROMs', runner=runner)
            self.assertEqual(report['existing'], 1)
            self.assertEqual(report['transferred'], 0)
            self.assertFalse(any('push' in call for call in calls))


if __name__ == '__main__':
    unittest.main()
