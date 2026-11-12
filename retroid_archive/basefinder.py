"""Find a compatible personal base ROM using BPS/UPS source fingerprints."""
from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import zipfile
import zlib
from pathlib import Path

from .importer import sha256

BASE_EXTENSIONS = {'.gba', '.gbc', '.gb', '.sfc', '.smc', '.nes', '.z64', '.n64',
                   '.v64', '.nds', '.md', '.gen', '.bin'}


def _varint(data: bytes, offset: int) -> int:
    value, shift = 0, 1
    for byte in data[offset:]:
        value += (byte & 127) * shift
        if byte & 128:
            return value
        shift <<= 7
        value += shift
    raise ValueError('En-tête de patch tronqué')


def source_fingerprint(patch: Path) -> tuple[int, int] | None:
    """Return (base size, CRC32) embedded in a BPS or UPS patch."""
    if patch.suffix.lower() not in ('.bps', '.ups'):
        return None
    with patch.open('rb') as stream:
        head = stream.read(32)
        stream.seek(-12, 2)
        source_crc = int.from_bytes(stream.read(4), 'little')
    if head[:4] != (b'BPS1' if patch.suffix.lower() == '.bps' else b'UPS1'):
        raise ValueError('En-tête de patch invalide')
    return _varint(head, 4), source_crc


def _crc32(path: Path) -> int:
    value = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value = zlib.crc32(chunk, value)
    return value


def _extract_zip_base(archive: Path, member: zipfile.ZipInfo, cache_dir: Path,
                      expected_size: int, expected_crc: int) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=cache_dir, prefix='.base-')
    os.close(fd)
    staging = Path(name)
    try:
        digest = hashlib.sha256()
        size, crc = 0, 0
        with staging.open('wb') as stream, zipfile.ZipFile(archive) as z:
            with z.open(member) as incoming:
                while chunk := incoming.read(1024 * 1024):
                    size += len(chunk)
                    if size > expected_size:
                        raise ValueError('Base ZIP plus volumineuse qu’annoncé')
                    crc = zlib.crc32(chunk, crc)
                    digest.update(chunk)
                    stream.write(chunk)
        if size != expected_size or crc != expected_crc:
            raise ValueError('Base ZIP différente du patch')
        target = cache_dir / (digest.hexdigest() + Path(member.filename).suffix.lower())
        if target.exists():
            if sha256(target) != digest.hexdigest():
                raise FileExistsError('Cache de base différent')
        else:
            os.replace(staging, target)
        return target
    finally:
        staging.unlink(missing_ok=True)


def find_base(patch: Path, roots: tuple[Path, ...], cache_dir: Path | None = None) -> tuple[Path | None, str]:
    """Choose one matching base; identical duplicates are treated as one copy."""
    fingerprint = source_fingerprint(patch)
    if fingerprint is None:
        return None, 'Patch sans empreinte de base'
    expected_size, expected_crc = fingerprint
    matches: list[Path] = []
    archives: list[tuple[Path, zipfile.ZipInfo]] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob('*'):
            if not path.is_file() or path.suffix.lower() not in BASE_EXTENSIONS | {'.zip'}:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.suffix.lower() == '.zip':
                try:
                    with zipfile.ZipFile(path) as z:
                        archives.extend((path, info) for info in z.infolist()
                                        if not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16)
                                        and not info.flag_bits & 1
                                        and Path(info.filename).suffix.lower() in BASE_EXTENSIONS
                                        and info.file_size == expected_size and info.CRC == expected_crc)
                except zipfile.BadZipFile:
                    continue
            elif path.stat().st_size == expected_size and _crc32(path) == expected_crc:
                matches.append(path)
    if archives:
        if cache_dir is None:
            return None, 'Cache requis pour extraire une base ZIP'
        matches.extend(_extract_zip_base(path, info, cache_dir, expected_size, expected_crc)
                       for path, info in archives)
    if not matches:
        return None, 'Aucune copie locale compatible trouvée'
    if len(matches) > 1 and len({sha256(path) for path in matches}) != 1:
        return None, 'Plusieurs copies différentes avec la même empreinte CRC32'
    return matches[0], 'Empreinte de base BPS/UPS vérifiée'
