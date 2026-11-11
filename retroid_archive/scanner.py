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
            names = ([source['filename']] if source.get('artifact_format') in ('direct', 'apk')
                     else [member['name'] for member in source['members']])
            for name in names:
                target = ((state.path.parent / 'apks' / name) if source.get('artifact_format') == 'apk'
                          else library / folder / name)
                if target.is_file() and target not in matches:
                    matches.append(target)
        file_path = None
        size = 0
        if len(matches) == 1:
            base_names = {name.casefold() for name in source.get('base_files', [])} if source else set()
            present = {path.name.casefold() for path in (library / folder).iterdir()} if base_names else set()
            status = ('apk_ready' if source and source.get('artifact_format') == 'apk'
                      else 'mod_only' if source and source['kind'] == 'mod'
                      and (not base_names or not base_names.issubset(present)) else 'available')
            file_path = str(matches[0])
            size = matches[0].stat().st_size
        elif len(matches) > 1:
            status = 'ambiguous'
        elif source and source['kind'] == 'patch' and all(
                (state.path.parent / 'patches' / str(game.id) / name).is_file()
                for name in ([source['filename']] if source.get('artifact_format') == 'patch'
                             else [member['name'] for member in source['members']])):
            status = 'patch_only'
        elif source:
            status = 'downloadable'
        elif game.official_link:
            status = 'source_candidate'
        else:
            status = 'missing'
        state.update_game(game.id, game.title, game.platform, status, file_path, size,
                          source['evidence_url'] if source else game.official_link or None)
    result = state.summary()
    del result['steps']
    return result
