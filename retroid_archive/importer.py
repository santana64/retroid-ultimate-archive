"""Import sûr de fichiers appartenant à l'utilisateur."""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

from .catalogue import Game, normalise, platform_folder

EXTENSIONS = {'.iso', '.cso', '.chd', '.rvz', '.gcz', '.gcm', '.wbfs', '.wia',
              '.pbp', '.cue', '.gdi', '.cdi', '.bin', '.ccd', '.img', '.m3u',
              '.zip', '.7z', '.nes', '.sfc', '.smc', '.gba', '.gbc', '.gb',
              '.n64', '.z64', '.v64', '.nds', '.3ds', '.md', '.gen', '.pce',
              '.ws', '.wsc', '.scummvm'}
SUFFIX_PLATFORM = {'.gba': {'gba'}, '.gbc': {'gbc', 'gb'}, '.gb': {'gb'},
                   '.nds': {'nds'}, '.3ds': {'n3ds'}, '.nes': {'nes'},
                   '.sfc': {'snes'}, '.smc': {'snes'}, '.n64': {'n64'},
                   '.z64': {'n64'}, '.v64': {'n64'}, '.pce': {'pcengine'}}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def import_local(source: Path, destination: Path, games: list[Game]) -> dict:
    source = source.expanduser().resolve(strict=True)
    destination = destination.expanduser().resolve()
    if not source.is_dir() or destination.is_relative_to(source):
        raise ValueError('La source doit être un dossier distinct de la destination')
    names = defaultdict(list)
    for game in games:
        names[normalise(game.title)].append(game)
    matches = defaultdict(list)
    unmatched = []
    for path in source.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        candidates = names.get(normalise(path.stem), [])
        allowed = SUFFIX_PLATFORM.get(path.suffix.lower())
        if allowed:
            candidates = [g for g in candidates if platform_folder(g.platform) in allowed]
        if len(candidates) == 1:
            matches[candidates[0].id].append((candidates[0], path))
        else:
            unmatched.append(str(path))
    result = {'imported': 0, 'existing': 0, 'ambiguous': 0, 'conflicts': [], 'unmatched': unmatched, 'items': []}
    for entries in matches.values():
        if len(entries) != 1:
            result['ambiguous'] += 1
            continue
        game, path = entries[0]
        target = destination / platform_folder(game.platform) / path.name
        digest = sha256(path)
        if target.exists():
            if sha256(target) == digest:
                result['existing'] += 1
            else:
                result['conflicts'].append(str(target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.import-', delete=False) as stream:
            staging = Path(stream.name)
        try:
            shutil.copyfile(path, staging)
            if sha256(staging) != digest:
                raise OSError('La copie ne correspond pas à la source')
            os.replace(staging, target)
        finally:
            staging.unlink(missing_ok=True)
        result['imported'] += 1
        result['items'].append({'id': game.id, 'path': str(target), 'sha256': digest})
    return result
