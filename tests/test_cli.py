import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from retroid_archive.cli import main


class CliTests(unittest.TestCase):
    def test_bps_command_is_available(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as exit_status:
            main(['patch-bps', '--help'])
        self.assertEqual(exit_status.exception.code, 0)
        self.assertIn('--base-sha256', output.getvalue())

    def test_ups_command_is_available(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as exit_status:
            main(['patch-ups', '--help'])
        self.assertEqual(exit_status.exception.code, 0)
        self.assertIn('--base-sha256', output.getvalue())

    def test_status_reports_all_games_and_source_pages(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['status', '--json'])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['games'], 899)
        self.assertGreater(report['rom_hacks'], 0)
        self.assertGreater(report['source_pages'], 0)
        self.assertEqual(report['files_downloaded'], 0)

    def test_prepare_defaults_to_simulation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'card'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['prepare-sd', '--root', str(root)]), 0)
            self.assertFalse(root.exists())

    def test_deploy_defaults_to_plan_without_adb(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'library'
            (root / 'gba').mkdir(parents=True)
            (root / 'gba' / 'Game.gba').write_bytes(b'owned')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['deploy', '--library', str(root), '--remote', '/sdcard/ROMs']), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['mode'], 'simulation')
            self.assertEqual(len(report['plan']), 1)

    def test_sources_exports_catalogue_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'sources.json'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['sources', '--output', str(target)]), 0)
            pages = json.loads(target.read_text(encoding='utf-8'))
            self.assertTrue(any(item['id'] == 620 and 'github.com' in item['url'] for item in pages))
            self.assertFalse(any(item['download_approved'] for item in pages))


if __name__ == '__main__':
    unittest.main()
