"""Configuration TOML de l'installation personnelle."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .sources import DEFAULT_SOURCES


@dataclass(frozen=True)
class Config:
    data_dir: Path
    library: Path
    download_dir: Path
    source_manifest: Path
    import_roots: tuple[Path, ...]
    sd_root: Path | None
    adb_remote: str | None
    adb_serial: str | None
    max_workers: int
    patch_bases: dict[int, Path]
    emulator_apks: tuple[dict, ...]


def load_config(path: Path | None = None) -> Config:
    if path is None:
        candidate = Path.cwd() / 'retroid.toml'
        path = candidate if candidate.is_file() else None
    if path is None:
        base, raw = Path.cwd(), {}
    else:
        path = path.expanduser().resolve(strict=True)
        base = path.parent
        with path.open('rb') as stream:
            raw = tomllib.load(stream)

    def resolve(value: str | Path) -> Path:
        result = Path(value).expanduser()
        return (result if result.is_absolute() else base / result).resolve()

    data_dir = resolve(raw.get('data_dir', 'data'))
    library = resolve(raw['library']) if raw.get('library') else data_dir / 'ROMs'
    download_dir = resolve(raw['download_dir']) if raw.get('download_dir') else data_dir / 'downloads'
    source_manifest = resolve(raw['source_manifest']) if raw.get('source_manifest') else DEFAULT_SOURCES
    sd_root = resolve(raw['sd_root']) if raw.get('sd_root') else None
    max_workers = raw.get('max_workers', 4)
    if not isinstance(max_workers, int) or not 1 <= max_workers <= 16:
        raise ValueError('max_workers doit être compris entre 1 et 16')
    bases = {int(key): resolve(value) for key, value in raw.get('patch_bases', {}).items()}
    apks = tuple({'path': str(resolve(item['path'])), 'sha256': item['sha256'],
                  'package': item['package']} for item in raw.get('emulator_apks', []))
    return Config(data_dir, library, download_dir, source_manifest,
                  tuple(resolve(value) for value in raw.get('import_roots', [])),
                  sd_root, raw.get('adb_remote') or None, raw.get('adb_serial') or None,
                  max_workers, bases, apks)
