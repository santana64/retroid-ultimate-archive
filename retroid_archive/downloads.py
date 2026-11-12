"""Téléchargements concurrents, repris et vérifiés depuis un manifeste explicite."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from .importer import sha256

MAX_BYTES = 2 * 1024 * 1024 * 1024
RETRYABLE = {408, 429, 500, 502, 503, 504}


def validate_entry(entry: dict, allow_localhost: bool = False) -> None:
    required = ('id', 'url', 'filename', 'sha256', 'evidence_url')
    if any(key not in entry for key in required):
        raise ValueError('Entrée incomplète')
    if not isinstance(entry['id'], int) or entry['id'] < 1:
        raise ValueError('ID invalide')
    filename = entry['filename']
    if not isinstance(filename, str) or filename in ('', '.', '..') or Path(filename).name != filename or '\\' in filename or '/' in filename:
        raise ValueError('Nom de fichier invalide')
    if not re.fullmatch(r'[a-fA-F0-9]{64}', str(entry['sha256'])):
        raise ValueError('SHA-256 attendu requis')
    if entry.get('download_authorized') is not True and entry.get('redistribution_verified') is not True:
        raise ValueError('Autorisation de téléchargement non vérifiée')
    evidence = urlparse(str(entry['evidence_url']))
    if evidence.scheme != 'https' or not evidence.netloc:
        raise ValueError('Page de preuve HTTPS requise')
    url = urlparse(str(entry['url']))
    local = allow_localhost and url.hostname in ('127.0.0.1', 'localhost') and url.scheme == 'http'
    if (url.scheme != 'https' and not local) or not url.netloc or url.username or url.password:
        raise ValueError('URL de téléchargement HTTPS requise')


def _download_one(entry: dict, destination: Path, allow_localhost: bool, retries: int) -> tuple[str, dict]:
    validate_entry(entry, allow_localhost)
    target = destination / entry['filename']
    expected = entry['sha256'].lower()
    if target.exists():
        if sha256(target) == expected:
            return 'existing', {'id': entry['id'], 'path': str(target), 'sha256': expected}
        raise FileExistsError(f'Fichier existant différent : {target}')
    part = target.with_name(target.name + '.part')
    for attempt in range(retries + 1):
        offset = part.stat().st_size if part.exists() else 0
        if offset > MAX_BYTES:
            raise ValueError('Téléchargement partiel trop volumineux')
        headers = {'User-Agent': 'retroid-ultimate-archive/1.0'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        request = urllib.request.Request(entry['url'], headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                final = urlparse(response.url)
                local = allow_localhost and final.hostname in ('127.0.0.1', 'localhost') and final.scheme == 'http'
                if final.scheme != 'https' and not local:
                    raise ValueError('Redirection vers une URL non HTTPS')
                status = response.status
                if status not in (200, 206):
                    raise OSError(f'HTTP {status}')
                if status == 206 and offset:
                    content_range = response.headers.get('Content-Range', '')
                    if not content_range.startswith(f'bytes {offset}-'):
                        raise ValueError('Réponse Range incohérente')
                else:
                    offset = 0
                mode = 'ab' if offset else 'wb'
                with part.open(mode) as stream:
                    total = offset
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise ValueError('Téléchargement trop volumineux')
                        stream.write(chunk)
            if sha256(part) != expected:
                part.unlink(missing_ok=True)
                raise ValueError('SHA-256 téléchargé incorrect')
            os.replace(part, target)
            return 'downloaded', {'id': entry['id'], 'path': str(target), 'sha256': expected}
        except urllib.error.HTTPError as exc:
            if exc.code == 416:
                part.unlink(missing_ok=True)
            if exc.code not in RETRYABLE and exc.code != 416:
                raise
            if attempt == retries:
                raise
            time.sleep(min(2 ** attempt, 16))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries:
                raise
            time.sleep(min(2 ** attempt, 16))
    raise RuntimeError('Téléchargement impossible')


def download_manifest(manifest: Path, destination: Path, max_workers: int = 4,
                      allow_localhost: bool = False, retries: int = 3) -> dict:
    if not 1 <= max_workers <= 16 or not 0 <= retries <= 8:
        raise ValueError('Paramètres de téléchargement invalides')
    entries = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(entries, list):
        raise ValueError('Le manifeste doit être une liste JSON')
    for entry in entries:
        validate_entry(entry, allow_localhost)
    names = [entry['filename'].casefold() for entry in entries]
    if len(names) != len(set(names)):
        raise ValueError('Noms de fichiers dupliqués dans le manifeste')
    destination.mkdir(parents=True, exist_ok=True)
    result: dict = {'downloaded': 0, 'existing': 0, 'errors': [], 'items': []}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_download_one, entry, destination, allow_localhost, retries): entry for entry in entries}
        for future in as_completed(futures):
            try:
                status, item = future.result()
                result[status] += 1
                result['items'].append(item)
            except Exception as exc:
                result['errors'].append({'id': futures[future]['id'], 'error': str(exc)})
    result['items'].sort(key=lambda item: item['id'])
    result['errors'].sort(key=lambda item: item['id'])
    return result
