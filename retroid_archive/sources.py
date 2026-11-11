"""Sources validées et extraction limitée aux membres attendus."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_SOURCES = Path(__file__).resolve().parents[1] / 'sources' / 'verified.json'
MAX_MEMBER_BYTES = 128 * 1024 * 1024


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _safe_name(name: str) -> bool:
    return bool(name) and name not in ('.', '..') and Path(name).name == name and '/' not in name and '\\' not in name


def load_verified_sources(path: Path = DEFAULT_SOURCES) -> list[dict]:
    sources = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(sources, list):
        raise ValueError('Liste de sources invalide')
    ids, filenames = set(), set()
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get('id'), int) or item['id'] in ids:
            raise ValueError('ID source absent ou dupliqué')
        ids.add(item['id'])
        name = item.get('filename')
        if not isinstance(name, str) or not _safe_name(name) or name.casefold() in filenames:
            raise ValueError('Nom source absent ou dupliqué')
        filenames.add(name.casefold())
        if item.get('kind') not in ('patch', 'mod', 'homebrew', 'fangame'):
            raise ValueError('Type de source invalide')
        if item.get('download_authorized') is not True:
            raise ValueError('Téléchargement non autorisé')
        if any(urlparse(str(item.get(key, ''))).scheme != 'https' for key in ('url', 'evidence_url')):
            raise ValueError('URL HTTPS requise')
        if not re.fullmatch(r'[0-9a-fA-F]{64}', str(item.get('sha256', ''))):
            raise ValueError('SHA-256 de source absent')
        if not isinstance(item.get('members'), list) or not item['members']:
            raise ValueError('Membres d’archive absents')
        for member in item['members']:
            if not isinstance(member, dict) or not _safe_name(str(member.get('name', ''))):
                raise ValueError('Membre d’archive invalide')
            if not re.fullmatch(r'[0-9a-fA-F]{64}', str(member.get('sha256', ''))):
                raise ValueError('SHA-256 de membre absent')
    return sources


def extract_verified(archive: Path, output: Path, members: list[dict]) -> list[Path]:
    if not members or any(not _safe_name(str(item.get('name', ''))) for item in members):
        raise ValueError('Membres demandés invalides')
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = [output / item['name'] for item in members]
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory(dir=output, prefix='.extract-') as temp:
        staging = Path(temp)
        for item, path in zip(members, paths):
            info = z.getinfo(item['name'])
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_ISLNK(mode) or info.file_size > MAX_MEMBER_BYTES:
                raise ValueError('Membre d’archive non sûr')
            tmp = staging / item['name']
            h = hashlib.sha256()
            size = 0
            with z.open(info) as src, tmp.open('wb') as dest:
                while chunk := src.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_MEMBER_BYTES:
                        raise ValueError('Membre d’archive trop volumineux')
                    h.update(chunk)
                    dest.write(chunk)
            if h.hexdigest() != item['sha256'].lower():
                raise ValueError('SHA-256 du membre incorrect')
            if path.exists() and _digest(path) != item['sha256'].lower():
                raise FileExistsError(f'Fichier existant différent : {path}')
        for item, path in zip(members, paths):
            if not path.exists():
                os.replace(staging / item['name'], path)
    return paths
