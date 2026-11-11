"""Inventaire exhaustif et prudent du catalogue."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .catalogue import Game, normalise, platform_folder
from .importer import EXTENSIONS
from .state import ArchiveState


def scan_catalogue(games: list[Game], library: Path, sources: list[dict], state: ArchiveState) -> dict:
    state.retain_games({game.id for game in games})
    library = library.expanduser().resolve()
    index: dict[tuple[str, str], list[Path]] = defaultdict(list)
    if library.is_dir():
        for file in library.rglob('*'):
            if file.is_file() and (file.suffix.lower() in EXTENSIONS or file.suffix.lower() == '.wad'):
                if file.resolve().is_relative_to(library):
                    index[(file.parent.name.casefold(), normalise(file.stem))].append(file)
    verified = {item['id']: item for item in sources}
    for game in games:
        source = verified.get(game.id)
        folder = platform_folder(game.platform)
        matches = index.get((folder, normalise(game.title)), [])
        if source and source['kind'] != 'patch':
            for member in source['members']:
                target = library / folder / member['name']
                if target.is_file() and target not in matches:
                    matches.append(target)
        file_path = None
        size = 0
        if len(matches) == 1:
            status = 'available'
            file_path = str(matches[0])
            size = matches[0].stat().st_size
        elif len(matches) > 1:
            status = 'ambiguous'
        elif source and source['kind'] == 'patch' and all(
                (state.path.parent / 'patches' / str(game.id) / member['name']).is_file()
                for member in source['members']):
            status = 'patch_only'
        elif source:
            status = 'downloadable'
        elif game.official_link:
            status = 'source_candidate'
        else:
            status = 'missing'
        state.update_game(game.id, game.title, game.platform, status, file_path, size,
                          source['evidence_url'] if source else game.official_link or None)
    return state.summary()
