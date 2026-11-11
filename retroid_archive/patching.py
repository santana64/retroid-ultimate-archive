"""Application de patches IPS sur copie locale avec vérification de base."""
from __future__ import annotations

import os
import tempfile
import zlib
from pathlib import Path

from .importer import sha256


def apply_ips(base: Path, patch: Path, output: Path, expected_base_sha256: str) -> str:
    if not expected_base_sha256 or sha256(base).lower() != expected_base_sha256.lower():
        raise ValueError('SHA-256 du jeu de base incorrect')
    if output.exists() or output.resolve() in {base.resolve(), patch.resolve()}:
        raise FileExistsError('La sortie existe ou écraserait une entrée')
    data = patch.read_bytes()
    if not data.startswith(b'PATCH'):
        raise ValueError('En-tête IPS invalide')
    result = bytearray(base.read_bytes())
    pos = 5
    while True:
        if data[pos:pos + 3] == b'EOF':
            pos += 3
            break
        if pos + 5 > len(data):
            raise ValueError('Patch IPS tronqué')
        offset = int.from_bytes(data[pos:pos + 3], 'big')
        size = int.from_bytes(data[pos + 3:pos + 5], 'big')
        pos += 5
        if size == 0:
            if pos + 3 > len(data):
                raise ValueError('Patch IPS RLE tronqué')
            length = int.from_bytes(data[pos:pos + 2], 'big')
            payload = data[pos + 2:pos + 3] * length
            pos += 3
        else:
            if pos + size > len(data):
                raise ValueError('Patch IPS tronqué')
            payload = data[pos:pos + size]
            pos += size
        if offset + len(payload) > 64 * 1024 * 1024:
            raise ValueError('Patch IPS trop volumineux')
        if offset > len(result):
            result.extend(b'\0' * (offset - len(result)))
        end = offset + len(payload)
        if end > len(result):
            result.extend(b'\0' * (end - len(result)))
        result[offset:end] = payload
    if pos != len(data):
        if pos + 3 != len(data):
            raise ValueError('Fin IPS invalide')
        result = result[:int.from_bytes(data[pos:pos + 3], 'big')]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.patch-', delete=False) as stream:
        staging = Path(stream.name)
        stream.write(result)
    try:
        os.replace(staging, output)
    finally:
        staging.unlink(missing_ok=True)
    return sha256(output)


def apply_bps(base: Path, patch: Path, output: Path, expected_base_sha256: str) -> str:
    """Appliquer BPS1 et vérifier les CRC source, cible et patch."""
    if not expected_base_sha256 or sha256(base).lower() != expected_base_sha256.lower():
        raise ValueError('SHA-256 du jeu de base incorrect')
    if output.exists() or output.resolve() in {base.resolve(), patch.resolve()}:
        raise FileExistsError('La sortie existe ou écraserait une entrée')
    source = base.read_bytes()
    data = patch.read_bytes()
    if not data.startswith(b'BPS1') or len(data) < 19:
        raise ValueError('En-tête BPS invalide')
    if zlib.crc32(data[:-4]) != int.from_bytes(data[-4:], 'little'):
        raise ValueError('CRC du patch BPS incorrect')
    end = len(data) - 12
    pos = 4

    def varint() -> int:
        nonlocal pos
        value, shift = 0, 1
        while pos < end:
            byte = data[pos]
            pos += 1
            value += (byte & 127) * shift
            if byte & 128:
                return value
            shift <<= 7
            value += shift
        raise ValueError('Variable BPS tronquée')

    source_size = varint()
    target_size = varint()
    metadata_size = varint()
    if source_size != len(source) or target_size > 64 * 1024 * 1024 or pos + metadata_size > end:
        raise ValueError('Tailles BPS invalides')
    pos += metadata_size
    result = bytearray()
    source_relative = target_relative = 0
    while len(result) < target_size:
        action = varint()
        size = (action >> 2) + 1
        mode = action & 3
        if len(result) + size > target_size:
            raise ValueError('Action BPS hors cible')
        if mode == 0:
            start = len(result)
            if start + size > len(source):
                raise ValueError('Lecture source BPS invalide')
            result.extend(source[start:start + size])
        elif mode == 1:
            if pos + size > end:
                raise ValueError('Lecture patch BPS tronquée')
            result.extend(data[pos:pos + size])
            pos += size
        else:
            delta = varint()
            signed = -(delta >> 1) if delta & 1 else delta >> 1
            if mode == 2:
                source_relative += signed
                if source_relative < 0 or source_relative + size > len(source):
                    raise ValueError('Copie source BPS invalide')
                result.extend(source[source_relative:source_relative + size])
                source_relative += size
            else:
                target_relative += signed
                if target_relative < 0 or target_relative >= len(result):
                    raise ValueError('Copie cible BPS invalide')
                for _ in range(size):
                    if target_relative >= len(result):
                        raise ValueError('Copie cible BPS invalide')
                    result.append(result[target_relative])
                    target_relative += 1
    if pos != end:
        raise ValueError('Données BPS surnuméraires')
    if zlib.crc32(source) != int.from_bytes(data[-12:-8], 'little'):
        raise ValueError('CRC de la base BPS incorrect')
    if zlib.crc32(result) != int.from_bytes(data[-8:-4], 'little'):
        raise ValueError('CRC de la cible BPS incorrect')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.patch-', delete=False) as stream:
        staging = Path(stream.name)
        stream.write(result)
    try:
        os.replace(staging, output)
    finally:
        staging.unlink(missing_ok=True)
    return sha256(output)
