"""Find a compatible personal base ROM using BPS/UPS source fingerprints."""
from __future__ import annotations

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


def find_base(patch: Path, roots: tuple[Path, ...]) -> tuple[Path | None, str]:
    """Choose one matching base; identical duplicates are treated as one copy."""
    fingerprint = source_fingerprint(patch)
    if fingerprint is None:
        return None, 'Patch sans empreinte de base'
    expected_size, expected_crc = fingerprint
    matches: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob('*'):
            if not path.is_file() or path.suffix.lower() not in BASE_EXTENSIONS:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.stat().st_size == expected_size and _crc32(path) == expected_crc:
                matches.append(path)
    if not matches:
        return None, 'Aucune copie locale compatible trouvée'
    if len(matches) > 1 and len({sha256(path) for path in matches}) != 1:
        return None, 'Plusieurs copies différentes avec la même empreinte CRC32'
    return matches[0], 'Empreinte de base BPS/UPS vérifiée'
