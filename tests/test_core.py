import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from retroid_archive.catalogue import load_catalogue, platform_folder
from retroid_archive.importer import import_local
from retroid_archive.patching import apply_ips, apply_bps, apply_ups
from retroid_archive.storage import prepare_sd, sync_library_to_sd


class CatalogueTests(unittest.TestCase):
    def test_catalogue_preserves_all_ids(self):
        games = load_catalogue()
        self.assertEqual(len(games), 899)
        self.assertEqual(len({game.id for game in games}), 899)
        self.assertEqual(games[0].id, 1)

    def test_hack_uses_base_platform_folder(self):
        self.assertEqual(platform_folder('GBA · ROM hack'), 'gba')
        self.assertEqual(platform_folder('PC · fangame'), 'pc-fangames')
        self.assertEqual(platform_folder('PC Engine / CD'), 'pcengine')
        self.assertEqual(platform_folder('Game Boy / Color'), 'gb')


class ImportTests(unittest.TestCase):
    def test_imports_unique_exact_match_without_touching_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'owned'
            source.mkdir()
            rom = source / 'Final Fantasy X.iso'
            rom.write_bytes(b'personal dump')
            output = root / 'library'
            result = import_local(source, output, load_catalogue())
            self.assertEqual(result['imported'], 1)
            self.assertEqual((output / 'ps2' / rom.name).read_bytes(), b'personal dump')
            self.assertEqual(rom.read_bytes(), b'personal dump')
            self.assertEqual(result['ambiguous'], 0)

    def test_ambiguous_name_is_never_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'owned'
            source.mkdir()
            (source / 'Final Fantasy X.iso').write_bytes(b'a')
            (source / 'Final Fantasy X (USA).iso').write_bytes(b'b')
            result = import_local(source, root / 'library', load_catalogue())
            self.assertEqual(result['ambiguous'], 1)
            self.assertEqual(result['imported'], 0)


class PatchTests(unittest.TestCase):
    def test_ips_patch_writes_new_file_and_preserves_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'base.gba'
            base.write_bytes(b'abcdef')
            patch = root / 'fix.ips'
            patch.write_bytes(b'PATCH' + (2).to_bytes(3, 'big') + (2).to_bytes(2, 'big') + b'XY' + b'EOF')
            output = root / 'patched.gba'
            apply_ips(base, patch, output, hashlib.sha256(b'abcdef').hexdigest())
            self.assertEqual(output.read_bytes(), b'abXYef')
            self.assertEqual(base.read_bytes(), b'abcdef')

    def test_ips_rejects_wrong_base_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'base.gba'
            base.write_bytes(b'abcdef')
            patch = root / 'fix.ips'
            patch.write_bytes(b'PATCHEOF')
            with self.assertRaises(ValueError):
                apply_ips(base, patch, root / 'out.gba', '0' * 64)

    def test_bps_patch_checks_crc_and_produces_target(self):
        import zlib

        def varint(number):
            result = bytearray()
            while True:
                byte = number & 127
                number >>= 7
                if number == 0:
                    return bytes(result + bytes([byte | 128]))
                result.append(byte)
                number -= 1

        source = b'abcdef'
        target = b'abXYef'
        body = b'BPS1' + varint(6) + varint(6) + varint(0) + varint(21) + target
        body += zlib.crc32(source).to_bytes(4, 'little')
        body += zlib.crc32(target).to_bytes(4, 'little')
        patch_data = body + zlib.crc32(body).to_bytes(4, 'little')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'base.gba'
            base.write_bytes(source)
            patch = root / 'fix.bps'
            patch.write_bytes(patch_data)
            output = root / 'out.gba'
            apply_bps(base, patch, output, hashlib.sha256(source).hexdigest())
            self.assertEqual(output.read_bytes(), target)
            self.assertEqual(base.read_bytes(), source)
            patch.write_bytes(patch_data[:-1] + b'\0')
            with self.assertRaises(ValueError):
                apply_bps(base, patch, root / 'bad.gba', hashlib.sha256(source).hexdigest())

    def test_ups_patch_checks_crc_and_produces_target(self):
        import zlib

        source, target = b'abcdef', b'abXYef'
        body = b'UPS1' + bytes([0x86, 0x86, 0x82])
        body += bytes([ord('c') ^ ord('X'), ord('d') ^ ord('Y'), 0])
        body += zlib.crc32(source).to_bytes(4, 'little')
        body += zlib.crc32(target).to_bytes(4, 'little')
        data = body + zlib.crc32(body).to_bytes(4, 'little')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'base.gba'
            base.write_bytes(source)
            patch = root / 'fix.ups'
            patch.write_bytes(data)
            output = root / 'out.gba'
            apply_ups(base, patch, output, hashlib.sha256(source).hexdigest())
            self.assertEqual(output.read_bytes(), target)
            patch.write_bytes(data[:-1] + b'\0')
            with self.assertRaises(ValueError):
                apply_ups(base, patch, root / 'bad.gba', hashlib.sha256(source).hexdigest())


class StorageTests(unittest.TestCase):
    def test_prepare_sd_creates_expected_tree_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'card'
            prepare_sd(root, load_catalogue(), dry_run=False)
            prepare_sd(root, load_catalogue(), dry_run=False)
            self.assertTrue((root / 'ROMs' / 'ps2').is_dir())
            self.assertTrue((root / 'BIOS').is_dir())
            self.assertTrue((root / 'Patches').is_dir())
            self.assertTrue((root / 'Saves').is_dir())

    def test_sd_sync_copies_once_and_refuses_conflicting_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / 'library'
            (library / 'gba').mkdir(parents=True)
            (library / 'gba' / 'Game.gba').write_bytes(b'owned')
            card = root / 'card'
            card.mkdir()
            first = sync_library_to_sd(library, card)
            self.assertEqual(first['copied'], 1)
            self.assertEqual((card / 'ROMs' / 'gba' / 'Game.gba').read_bytes(), b'owned')
            self.assertEqual(sync_library_to_sd(library, card)['existing'], 1)
            (card / 'ROMs' / 'gba' / 'Game.gba').write_bytes(b'other')
            conflict = sync_library_to_sd(library, card)
            self.assertEqual(len(conflict['conflicts']), 1)
            self.assertEqual((card / 'ROMs' / 'gba' / 'Game.gba').read_bytes(), b'other')


if __name__ == '__main__':
    unittest.main()
