import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from retroid_archive.sources import extract_verified, load_verified_sources


class SourceTests(unittest.TestCase):
    def test_curated_sources_are_catalogue_entries_with_hashes(self):
        sources = load_verified_sources()
        self.assertEqual({item['id'] for item in sources}, {622, 676})
        self.assertTrue(all(len(item['sha256']) == 64 for item in sources))
        self.assertTrue(all(item['download_authorized'] for item in sources))

    def test_extracts_only_named_member_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'download.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('patch.ups', b'patch data')
                z.writestr('tool.exe', b'untrusted binary')
            output = root / 'patches'
            selected = [{'name': 'patch.ups', 'sha256': hashlib.sha256(b'patch data').hexdigest()}]
            paths = extract_verified(archive, output, selected)
            self.assertEqual(paths, [output / 'patch.ups'])
            self.assertEqual((output / 'patch.ups').read_bytes(), b'patch data')
            self.assertFalse((output / 'tool.exe').exists())
            self.assertEqual(extract_verified(archive, output, selected), paths)

    def test_rejects_traversal_and_wrong_member_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'download.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('../escape.ups', b'patch')
                z.writestr('patch.ups', b'patch')
            with self.assertRaises(ValueError):
                extract_verified(archive, root / 'out', [{'name': '../escape.ups', 'sha256': '0' * 64}])
            with self.assertRaises(ValueError):
                extract_verified(archive, root / 'out', [{'name': 'patch.ups', 'sha256': '0' * 64}])
            self.assertFalse((root / 'out' / 'patch.ups').exists())


if __name__ == '__main__':
    unittest.main()
