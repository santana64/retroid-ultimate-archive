import tempfile
import unittest
from pathlib import Path

from retroid_archive.dashboard import dashboard_snapshot
from retroid_archive.state import ArchiveState


class DashboardTests(unittest.TestCase):
    def test_snapshot_shows_counts_and_latest_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.sqlite'
            with ArchiveState(path) as state:
                state.update_game(1, 'Final Fantasy X', 'PS2', 'missing')
                state.set_step('fetch', 'completed', {'downloaded': 2})
            snapshot = dashboard_snapshot(path)
            self.assertEqual(snapshot['games'], 1)
            self.assertEqual(snapshot['missing'], 1)
            self.assertEqual(snapshot['downloads'], 2)
            self.assertEqual(snapshot['rows'][0]['title'], 'Final Fantasy X')

    def test_snapshot_counts_running_and_failed_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.sqlite'
            with ArchiveState(path) as state:
                state.set_step('fetch', 'running', {})
                state.set_step('install', 'failed', {'error': 'ADB absent'})
            snapshot = dashboard_snapshot(path)
            self.assertEqual(snapshot['active'], 1)
            self.assertEqual(snapshot['errors'], 1)

    def test_snapshot_keeps_existing_imports_and_patches_visible_after_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.sqlite'
            with ArchiveState(path) as state:
                state.set_step('import', 'completed', {'imported': 0, 'existing': 3})
                state.set_step('patch', 'completed', {'applied': 0, 'existing': 2})
            snapshot = dashboard_snapshot(path)
            self.assertEqual(snapshot['imports'], 3)
            self.assertEqual(snapshot['patches'], 2)


if __name__ == '__main__':
    unittest.main()
