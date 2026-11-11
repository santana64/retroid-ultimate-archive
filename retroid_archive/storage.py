"""Préparation idempotente d'une arborescence de carte personnelle."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import tempfile
from .catalogue import Game, platform_folder
from .importer import EXTENSIONS, sha256

EXTRA = ('BIOS', 'Patches', 'Saves', 'SaveStates', 'Media', 'Metadata', 'Config', 'Collections')


def prepare_sd(root: Path, games: list[Game], dry_run: bool = True) -> list[Path]:
    root = root.expanduser().resolve()
    folders = [root / name for name in EXTRA]
    folders += [root / 'ROMs' / name for name in sorted({platform_folder(game.platform) for game in games})]
    if not dry_run:
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
    return folders


def sync_library_to_sd(library: Path, sd_root: Path) -> dict:
    """Copier les jeux sans écraser des fichiers différents sur la carte."""
    library = library.expanduser().resolve(strict=True)
    sd_root = sd_root.expanduser().resolve(strict=True)
    if not library.is_dir() or not sd_root.is_dir():
        raise ValueError('Bibliothèque ou carte inexistante')
    if library.is_relative_to(sd_root) or sd_root.is_relative_to(library):
        raise ValueError('Bibliothèque et carte ne doivent pas être imbriquées')
    destination = sd_root / 'ROMs'
    result: dict = {'copied': 0, 'existing': 0, 'conflicts': [], 'bytes_copied': 0}
    pending = []
    for source in sorted(library.rglob('*')):
        if not source.is_file() or source.suffix.lower() not in EXTENSIONS | {'.wad'}:
            continue
        if not source.resolve().is_relative_to(library):
            continue
        target = destination / source.relative_to(library)
        digest = sha256(source)
        if target.exists():
            if sha256(target) == digest:
                result['existing'] += 1
            else:
                result['conflicts'].append(str(target))
        else:
            pending.append((source, target, digest))
    if shutil.disk_usage(sd_root).free < sum(source.stat().st_size for source, _, _ in pending):
        raise OSError('Espace libre insuffisant sur la carte')
    for source, target, digest in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to(sd_root):
            raise ValueError('Destination hors carte')
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.copy-', delete=False) as stream:
            staging = Path(stream.name)
        try:
            shutil.copyfile(source, staging)
            if sha256(staging) != digest:
                raise OSError('SHA-256 incorrect après copie')
            os.replace(staging, target)
        finally:
            staging.unlink(missing_ok=True)
        result['copied'] += 1
        result['bytes_copied'] += source.stat().st_size
    return result
