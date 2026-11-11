import tempfile
import unittest
from pathlib import Path

from retroid_archive.catalogue import load_catalogue
from retroid_archive.scanner import scan_catalogue
from retroid_archive.sources import load_verified_sources
from retroid_archive.state import ArchiveState


class StateTests(unittest.TestCase):
    def test_scan_records_all_games_and_distinguishes_downloadable_from_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / 'ROMs'
            (library / 'ps2').mkdir(parents=True)
            (library / 'ps2' / 'Final Fantasy X.iso').write_bytes(b'owned')
            with ArchiveState(root / 'state.sqlite') as state:
                result = scan_catalogue(load_catalogue(), library, load_verified_sources(), state)
                self.assertEqual(result['games'], 899)
                self.assertEqual(result['available'], 1)
                self.assertEqual(state.game(1)['status'], 'available')
                self.assertEqual(state.game(622)['status'], 'downloadable')
                self.assertEqual(state.game(676)['status'], 'downloadable')
            with ArchiveState(root / 'state.sqlite') as reopened:
                self.assertEqual(reopened.summary()['games'], 899)
                self.assertEqual(reopened.game(1)['status'], 'available')

    def test_patch_without_base_is_not_reported_as_playable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patch_dir = root / 'patches' / '622'
            patch_dir.mkdir(parents=True)
            (patch_dir / 'pokemon_gaia_v3.2.ups').write_bytes(b'patch')
            with ArchiveState(root / 'state.sqlite') as state:
                scan_catalogue(load_catalogue(), root / 'ROMs', load_verified_sources(), state)
                self.assertEqual(state.game(622)['status'], 'patch_only')
                self.assertEqual(state.summary()['available'], 0)

    def test_step_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.sqlite'
            with ArchiveState(path) as state:
                state.set_step('fetch', 'completed', {'downloaded': 2})
            with ArchiveState(path) as state:
                self.assertEqual(state.step('fetch')['status'], 'completed')
                self.assertEqual(state.step('fetch')['detail']['downloaded'], 2)

    def test_scan_removes_stale_catalogue_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with ArchiveState(root / 'state.sqlite') as state:
                state.update_game(9999, 'old', 'GBA', 'missing')
                result = scan_catalogue(load_catalogue(), root / 'ROMs', load_verified_sources(), state)
                self.assertEqual(result['games'], 899)
                self.assertIsNone(state.game(9999))


if __name__ == '__main__':
    unittest.main()
