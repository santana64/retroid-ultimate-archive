import hashlib
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from retroid_archive.downloads import download_manifest, validate_entry

PAYLOAD = b'permitted patch bytes' * 100


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/patch.bps':
            self.send_error(404)
            return
        offset = 0
        if self.headers.get('Range'):
            offset = int(self.headers['Range'].split('=')[1].split('-')[0])
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {offset}-{len(PAYLOAD)-1}/{len(PAYLOAD)}')
        else:
            self.send_response(200)
        self.send_header('Content-Length', str(len(PAYLOAD) - offset))
        self.end_headers()
        self.wfile.write(PAYLOAD[offset:])

    def log_message(self, *args):
        pass


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def entry(self):
        return {'id': 620, 'url': f'http://127.0.0.1:{self.server.server_port}/patch.bps',
                'filename': 'patch.bps', 'sha256': hashlib.sha256(PAYLOAD).hexdigest(),
                'redistribution_verified': True, 'evidence_url': 'https://example.org/author-release'}

    def test_requires_rights_evidence_and_checksum(self):
        entry = self.entry()
        entry['redistribution_verified'] = False
        with self.assertRaises(ValueError):
            validate_entry(entry, allow_localhost=True)
        entry['redistribution_verified'] = True
        entry['sha256'] = ''
        with self.assertRaises(ValueError):
            validate_entry(entry, allow_localhost=True)

    def test_resumes_partial_file_and_verifies_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps([self.entry()]), encoding='utf-8')
            dest = root / 'downloads'
            dest.mkdir()
            (dest / 'patch.bps.part').write_bytes(PAYLOAD[:100])
            result = download_manifest(manifest, dest, max_workers=2, allow_localhost=True)
            self.assertEqual(result['downloaded'], 1)
            self.assertEqual((dest / 'patch.bps').read_bytes(), PAYLOAD)
            self.assertFalse((dest / 'patch.bps.part').exists())
            self.assertEqual(download_manifest(manifest, dest, allow_localhost=True)['existing'], 1)

    def test_rejects_path_traversal(self):
        entry = self.entry()
        entry['filename'] = '../outside.bps'
        with self.assertRaises(ValueError):
            validate_entry(entry, allow_localhost=True)


if __name__ == '__main__':
    unittest.main()
