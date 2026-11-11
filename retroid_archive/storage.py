"""Préparation idempotente d'une arborescence de carte personnelle."""
from __future__ import annotations

from pathlib import Path
from .catalogue import Game, platform_folder

EXTRA = ('BIOS', 'Patches', 'Saves', 'SaveStates', 'Media', 'Metadata', 'Config', 'Collections')


def prepare_sd(root: Path, games: list[Game], dry_run: bool = True) -> list[Path]:
    root = root.expanduser().resolve()
    folders = [root / name for name in EXTRA]
    folders += [root / 'ROMs' / name for name in sorted({platform_folder(game.platform) for game in games})]
    if not dry_run:
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
    return folders
