import csv
import json
import hashlib
import tempfile
import unittest
import zipfile
import zlib
from dataclasses import replace
from pathlib import Path

from retroid_archive.catalogue import Game
from retroid_archive.config import load_config
from retroid_archive.runner import _patch, run_setup
from retroid_archive.state import ArchiveState


class RunnerTests(unittest.TestCase):
    def test_config_resolves_personal_paths_relative_to_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'retroid.toml'
            path.write_text('data_dir = "state"\nlibrary = "games"\nimport_roots = ["owned"]\nmax_workers = 3\n', encoding='utf-8')
            config = load_config(path)
            self.assertEqual(config.data_dir, root / 'state')
            self.assertEqual(config.library, root / 'games')
            self.assertEqual(config.import_roots, (root / 'owned',))
            self.assertEqual(config.max_workers, 3)

    def test_config_accepts_hashed_emulator_apk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'retroid.toml'
            path.write_text('[[emulator_apks]]\npath = "apps/emu.apk"\nsha256 = "' + 'a' * 64 + '"\npackage = "org.example.emu"\n', encoding='utf-8')
            config = load_config(path)
            self.assertEqual(config.emulator_apks[0]['path'], str(root / 'apps' / 'emu.apk'))
            self.assertEqual(config.emulator_apks[0]['package'], 'org.example.emu')

    def test_setup_reports_899_games_and_skips_missing_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'retroid.toml'
            source_path = root / 'sources.json'
            source_path.write_text('[]', encoding='utf-8')
            path.write_text('data_dir = "data"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(path)
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                first = run_setup(config, state, {'scan', 'fetch', 'import', 'patch', 'prepare', 'install', 'verify', 'report'})
                self.assertEqual(first['games'], 899)
                self.assertEqual(first['available'], 0)
                self.assertNotIn('steps', state.step('scan')['detail'])
                self.assertEqual(state.step('install')['status'], 'skipped')
                self.assertEqual(state.step('import')['status'], 'skipped')
                second = run_setup(config, state, {'scan', 'fetch', 'import', 'patch', 'prepare', 'install', 'verify', 'report'})
                self.assertEqual(second['games'], 899)
            report = json.loads((root / 'data' / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(len(report['games']), 899)
            with (root / 'data' / 'report.csv').open(encoding='utf-8-sig', newline='') as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 899)

    def test_local_file_is_reported_available_without_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources.json').write_text('[]', encoding='utf-8')
            (root / 'retroid.toml').write_text('data_dir = "data"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(root / 'retroid.toml')
            (config.library / 'ps2').mkdir(parents=True)
            (config.library / 'ps2' / 'Final Fantasy X.iso').write_bytes(b'owned')
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                result = run_setup(config, state, {'scan', 'report'})
                self.assertEqual(result['available'], 1)
                self.assertEqual(state.game(1)['status'], 'available')

    def test_prepare_copies_existing_library_file_to_configured_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card = root / 'card'
            card.mkdir()
            (root / 'sources.json').write_text('[]', encoding='utf-8')
            (root / 'retroid.toml').write_text('data_dir = "data"\nsd_root = "card"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(root / 'retroid.toml')
            (config.library / 'ps2').mkdir(parents=True)
            (config.library / 'ps2' / 'Final Fantasy X.iso').write_bytes(b'owned')
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                run_setup(config, state, {'prepare', 'report'})
                self.assertEqual(state.step('prepare')['detail']['sd_copied'], 1)
                (card / 'ROMs' / 'ps2' / 'Final Fantasy X.iso').write_bytes(b'other')
                run_setup(config, state, {'prepare', 'report'})
                self.assertEqual(state.step('prepare')['status'], 'failed')
            self.assertEqual((card / 'ROMs' / 'ps2' / 'Final Fantasy X.iso').read_bytes(), b'other')

    def test_fetch_counts_only_new_extractions_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'data' / 'downloads' / 'artifact.zip'
            archive.parent.mkdir(parents=True)
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('Test.iso', b'permitted data')
            source = [{'id': 1, 'kind': 'homebrew', 'version': '1',
                       'url': 'https://example.org/artifact.zip', 'filename': 'artifact.zip',
                       'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                       'download_authorized': True, 'evidence_url': 'https://example.org/project',
                       'members': [{'name': 'Test.iso', 'sha256': hashlib.sha256(b'permitted data').hexdigest()}]}]
            (root / 'sources.json').write_text(json.dumps(source), encoding='utf-8')
            (root / 'retroid.toml').write_text('data_dir = "data"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(root / 'retroid.toml')
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                run_setup(config, state, {'fetch', 'report'})
                self.assertEqual(state.step('fetch')['detail']['extracted'], 1)
                run_setup(config, state, {'fetch', 'report'})
                self.assertEqual(state.step('fetch')['detail']['extracted'], 0)

    def test_fetch_direct_solarus_package_is_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'data' / 'downloads' / 'game.solarus'
            archive.parent.mkdir(parents=True)
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('quest.dat', b'game')
            source = [{'id': 682, 'kind': 'fangame', 'version': '1',
                       'url': 'https://example.org/game.solarus', 'filename': 'game.solarus',
                       'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                       'download_authorized': True, 'evidence_url': 'https://example.org/project',
                       'artifact_format': 'direct'}]
            (root / 'sources.json').write_text(json.dumps(source), encoding='utf-8')
            (root / 'retroid.toml').write_text('data_dir = "data"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(root / 'retroid.toml')
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                run_setup(config, state, {'fetch', 'verify', 'report'})
                self.assertEqual(state.game(682)['status'], 'available')
                self.assertEqual(state.step('fetch')['detail']['extracted'], 1)
                run_setup(config, state, {'fetch'})
                self.assertEqual(state.step('fetch')['detail']['extracted'], 0)

    def test_fetch_android_apk_is_ready_to_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apk = root / 'data' / 'downloads' / 'game.apk'
            apk.parent.mkdir(parents=True)
            with zipfile.ZipFile(apk, 'w') as z:
                z.writestr('AndroidManifest.xml', b'manifest')
            source = [{'id': 679, 'kind': 'fangame', 'version': '1',
                       'url': 'https://example.org/game.apk', 'filename': 'game.apk',
                       'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
                       'download_authorized': True, 'evidence_url': 'https://example.org/project',
                       'artifact_format': 'apk', 'package': 'org.example.game'}]
            (root / 'sources.json').write_text(json.dumps(source), encoding='utf-8')
            (root / 'retroid.toml').write_text('data_dir = "data"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(root / 'retroid.toml')
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                run_setup(config, state, {'fetch', 'report'})
                self.assertEqual(state.game(679)['status'], 'apk_ready')
                self.assertEqual(state.summary()['apk_ready'], 1)

    def test_fetch_direct_bps_patch_is_patch_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patch = root / 'data' / 'downloads' / 'hack.bps'
            patch.parent.mkdir(parents=True)
            patch.write_bytes(b'BPS1example')
            source = [{'id': 649, 'kind': 'patch', 'version': '1',
                       'url': 'https://example.org/hack.bps', 'filename': 'hack.bps',
                       'sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
                       'download_authorized': True, 'evidence_url': 'https://example.org/project',
                       'artifact_format': 'patch'}]
            (root / 'sources.json').write_text(json.dumps(source), encoding='utf-8')
            (root / 'retroid.toml').write_text('data_dir = "data"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(root / 'retroid.toml')
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                run_setup(config, state, {'fetch', 'report'})
                self.assertEqual(state.game(649)['status'], 'patch_only')
                self.assertEqual(state.step('fetch')['detail']['extracted'], 1)

    def test_verify_detects_change_against_previous_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources.json').write_text('[]', encoding='utf-8')
            (root / 'retroid.toml').write_text('data_dir = "data"\nsource_manifest = "sources.json"\n', encoding='utf-8')
            config = load_config(root / 'retroid.toml')
            game = config.library / 'ps2' / 'Final Fantasy X.iso'
            game.parent.mkdir(parents=True)
            game.write_bytes(b'owned')
            with ArchiveState(config.data_dir / 'state.sqlite') as state:
                run_setup(config, state, {'verify'})
                game.write_bytes(b'changed')
                run_setup(config, state, {'verify'})
                self.assertEqual(state.step('verify')['status'], 'failed')
                self.assertEqual(state.step('verify')['detail']['changed'], ['ps2/Final Fantasy X.iso'])

    def test_patch_resume_rejects_different_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = replace(load_config(), data_dir=root / 'data', library=root / 'ROMs', patch_bases={1: root / 'base.gba'})
            config.patch_bases[1].write_bytes(b'base')
            patch = config.data_dir / 'patches' / '1' / 'test.ips'
            patch.parent.mkdir(parents=True)
            patch.write_bytes(b'PATCH' + b'\x00\x00\x00' + b'\x00\x01' + b'X' + b'EOF')
            source = {'id': 1, 'kind': 'patch', 'members': [{'name': 'test.ips'}]}
            game = Game(1, 'Test', 'GBA', '', '', '', '')
            status, detail = _patch(config, [source], {1: game})
            self.assertEqual((status, detail['applied']), ('completed', 1))
            output = config.library / 'gba' / 'Test.gba'
            status, detail = _patch(config, [source], {1: game})
            self.assertEqual((status, detail['existing']), ('completed', 1))
            output.write_bytes(b'wrong')
            status, detail = _patch(config, [source], {1: game})
            self.assertEqual(status, 'failed')
            self.assertEqual(output.read_bytes(), b'wrong')

    def test_patch_finds_compatible_personal_base_without_per_game_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned = root / 'owned'
            owned.mkdir()
            base = owned / 'my-copy.gba'
            base.write_bytes(b'abcdef')
            config = replace(load_config(), data_dir=root / 'data', library=root / 'ROMs',
                             import_roots=(owned,), patch_bases={})
            patch = config.data_dir / 'patches' / '1' / 'test.ups'
            patch.parent.mkdir(parents=True)
            source_bytes, target_bytes = b'abcdef', b'abXYef'
            body = b'UPS1' + bytes([0x86, 0x86, 0x82, ord('c') ^ ord('X'), ord('d') ^ ord('Y'), 0])
            body += zlib.crc32(source_bytes).to_bytes(4, 'little')
            body += zlib.crc32(target_bytes).to_bytes(4, 'little')
            patch.write_bytes(body + zlib.crc32(body).to_bytes(4, 'little'))
            source = {'id': 1, 'kind': 'patch', 'members': [{'name': 'test.ups'}]}
            game = Game(1, 'Test', 'GBA', '', '', 'my-copy', '')
            status, detail = _patch(config, [source], {1: game})
            self.assertEqual((status, detail['applied']), ('completed', 1))
            self.assertEqual((config.library / 'gba' / 'Test.gba').read_bytes(), target_bytes)
            self.assertEqual(base.read_bytes(), source_bytes)
            status, detail = _patch(config, [source], {1: game})
            self.assertEqual((status, detail['existing']), ('completed', 1))

    def test_patch_finds_compatible_base_inside_personal_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned = root / 'owned'
            owned.mkdir()
            with zipfile.ZipFile(owned / 'my-dump.zip', 'w') as z:
                z.writestr('backup/base.gba', b'abcdef')
            config = replace(load_config(), data_dir=root / 'data', library=root / 'ROMs',
                             import_roots=(owned,), patch_bases={})
            patch = config.data_dir / 'patches' / '1' / 'test.ups'
            patch.parent.mkdir(parents=True)
            body = b'UPS1' + bytes([0x86, 0x86, 0x82, ord('c') ^ ord('X'), ord('d') ^ ord('Y'), 0])
            body += zlib.crc32(b'abcdef').to_bytes(4, 'little')
            body += zlib.crc32(b'abXYef').to_bytes(4, 'little')
            patch.write_bytes(body + zlib.crc32(body).to_bytes(4, 'little'))
            source = {'id': 1, 'kind': 'patch', 'members': [{'name': 'test.ups'}]}
            game = Game(1, 'Test', 'GBA', '', '', 'my-copy', '')
            status, detail = _patch(config, [source], {1: game})
            self.assertEqual((status, detail['applied']), ('completed', 1))
            self.assertEqual((config.library / 'gba' / 'Test.gba').read_bytes(), b'abXYef')
            self.assertTrue(any((config.data_dir / 'base-cache').glob('*.gba')))


if __name__ == '__main__':
    unittest.main()
