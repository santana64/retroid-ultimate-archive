"""Lecture du catalogue historique sans modifier ses identifiants."""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CATALOGUE = Path(__file__).resolve().parents[1] / 'catalogue' / 'catalogue_ultimate.csv'
REGION = re.compile(r'\s*[\[(](?:USA|Europe|Japan|World|En|Fr|Rev [^\])]+|v\d[^\])]*)[\])]', re.I)
FOLDERS = {
    'PS1': 'psx', 'PS2': 'ps2', 'PSP': 'psp', 'GameCube': 'gc',
    'Wii': 'wii', 'DS': 'nds', '3DS': 'n3ds', 'GBA': 'gba',
    'GBC': 'gbc', 'Game Boy / Color': 'gb', 'NES': 'nes', 'SNES': 'snes',
    'N64': 'n64', 'Dreamcast': 'dreamcast', 'Saturn': 'saturn',
    'Mega Drive': 'megadrive', 'PC Engine / CD': 'pcengine',
    'Arcade / Neo Geo': 'arcade', 'ScummVM': 'scummvm',
    'Neo Geo Pocket Color': 'ngpc', 'WonderSwan Color': 'wonderswancolor',
    'Android': 'android', 'Doom': 'doom', 'PC': 'pc-fangames',
    'Navigateur': 'browser',
}


@dataclass(frozen=True)
class Game:
    id: int
    title: str
    platform: str
    genre: str
    run_target: str
    patch_base: str
    official_link: str


def normalise(value: str) -> str:
    value = unicodedata.normalize('NFKD', REGION.sub('', value))
    value = ''.join(char for char in value if not unicodedata.combining(char))
    return re.sub(r'[^a-z0-9]+', ' ', value.casefold()).strip()


def platform_folder(platform: str) -> str:
    base = platform.split(' · ', 1)[0]
    if base not in FOLDERS:
        base = base.split(' / ', 1)[0]
    return FOLDERS.get(base, re.sub(r'[^a-z0-9]+', '-', normalise(base)))


def load_catalogue(path: Path = DEFAULT_CATALOGUE) -> list[Game]:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    return [Game(int(row['id']), row['title'], row['platform'], row['genre'],
                 row['run_target'], row['patch_base'], row['official_link']) for row in rows]
