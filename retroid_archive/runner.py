"""Orchestration idempotente des étapes de préparation."""
from __future__ import annotations

import csv
import json
import re
import tempfile
from pathlib import Path

from .adb import build_plan, deploy, install_apks
from .basefinder import find_base
from .catalogue import load_catalogue, platform_folder
from .config import Config
from .downloads import download_manifest
from .importer import EXTENSIONS, import_local, sha256
from .patching import apply_bps, apply_ips, apply_ups
from .scanner import scan_catalogue
from .sources import copy_verified_direct, extract_verified, load_verified_sources
from .state import ArchiveState
from .storage import prepare_sd, sync_library_to_sd

STEP_ORDER = ('scan', 'fetch', 'import', 'patch', 'prepare', 'install', 'verify', 'report')
PATCHERS = {'.ips': apply_ips, '.bps': apply_bps, '.ups': apply_ups}


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def _export_report(config: Config, state: ArchiveState) -> dict:
    games = state.games()
    report = {'summary': state.summary(), 'games': games}
    _write_json(config.data_dir / 'report.json', report)
    csv_path = config.data_dir / 'report.csv'
    with csv_path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(games[0]))
        writer.writeheader()
        writer.writerows(games)
    return {'json': str(config.data_dir / 'report.json'), 'csv': str(csv_path), 'games': len(games)}


def _fetch(config: Config, sources: list[dict], games_by_id: dict) -> dict:
    if not sources:
        return {'downloaded': 0, 'existing': 0, 'extracted': 0, 'errors': []}
    result = download_manifest(config.source_manifest, config.download_dir, max_workers=config.max_workers)
    extracted = 0
    for source in sources:
        archive = config.download_dir / source['filename']
        if not archive.is_file() or sha256(archive) != source['sha256'].lower():
            continue
        folder = (config.data_dir / 'patches' / str(source['id']) if source['kind'] == 'patch'
                  else config.data_dir / 'apks' if source.get('artifact_format') == 'apk'
                  else config.library / platform_folder(games_by_id[source['id']].platform))
        try:
            if source.get('artifact_format') in ('direct', 'apk', 'patch'):
                target = folder / source['filename']
                new_count = int(not target.exists())
                copy_verified_direct(archive, target, source['sha256'])
            else:
                new_count = sum(not (folder / member['name']).exists() for member in source['members'])
                extract_verified(archive, folder, source['members'])
            extracted += new_count
        except Exception as exc:
            result['errors'].append({'id': source['id'], 'error': f'extraction: {exc}'})
    result['extracted'] = extracted
    return result


def _import(config: Config, games: list) -> tuple[str, dict]:
    roots = [root for root in config.import_roots if root.is_dir()]
    if not roots:
        return 'skipped', {'reason': 'Aucun dossier personnel disponible'}
    totals = {'imported': 0, 'existing': 0, 'ambiguous': 0, 'conflicts': [], 'unmatched': []}
    for root in roots:
        result = import_local(root, config.library, games)
        for key in ('imported', 'existing', 'ambiguous'):
            totals[key] += result[key]
        for key in ('conflicts', 'unmatched'):
            totals[key].extend(result[key])
    return 'completed', totals


def _patch(config: Config, sources: list[dict], games_by_id: dict) -> tuple[str, dict]:
    patches = [source for source in sources if source['kind'] == 'patch']
    result: dict = {'applied': 0, 'existing': 0, 'missing_base': [], 'base_search': {}, 'errors': []}
    roots = (config.library, *config.import_roots)
    for source in patches:
        game_id = source['id']
        patch_names = ([source['filename']] if source.get('artifact_format') == 'patch'
                       else [member['name'] for member in source['members']])
        for name in patch_names:
            patch = config.data_dir / 'patches' / str(game_id) / name
            if not patch.is_file():
                continue
            base = config.patch_bases.get(game_id)
            if base is None:
                try:
                    base, reason = find_base(patch, roots)
                except Exception as exc:
                    result['errors'].append({'id': game_id, 'error': f'Recherche de base : {exc}'})
                    continue
                result['base_search'][str(game_id)] = reason
            if base is None or not base.is_file():
                result['missing_base'].append(game_id)
                continue
            title = re.sub(r'[<>:"/\\|?*]', ' ', games_by_id[game_id].title).strip()
            output = config.library / platform_folder(games_by_id[game_id].platform) / (title + base.suffix)
            patcher = PATCHERS.get(patch.suffix.lower())
            if patcher is None:
                result['errors'].append({'id': game_id, 'error': 'Format de patch non pris en charge'})
                continue
            try:
                if output.exists():
                    with tempfile.TemporaryDirectory() as temporary:
                        expected = Path(temporary) / output.name
                        patcher(base, patch, expected, sha256(base))
                        if sha256(expected) != sha256(output):
                            raise ValueError('Sortie existante différente du résultat du patch')
                    result['existing'] += 1
                else:
                    patcher(base, patch, output, sha256(base))
                    result['applied'] += 1
            except Exception as exc:
                result['errors'].append({'id': game_id, 'error': str(exc)})
    status = ('failed' if result['errors'] else 'completed' if result['applied'] or result['existing']
              else 'skipped')
    return status, result


def _prepare(config: Config, games: list) -> dict:
    folders = [config.library / name for name in sorted({platform_folder(game.platform) for game in games})]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    if config.sd_root and not config.sd_root.is_dir():
        raise ValueError('Carte microSD configurée mais absente')
    sd_folders = prepare_sd(config.sd_root, games, dry_run=False) if config.sd_root else []
    synced = sync_library_to_sd(config.library, config.sd_root) if config.sd_root else None
    return {'local_folders': len(folders), 'sd_folders': len(sd_folders),
            'sd_root': str(config.sd_root) if config.sd_root else None,
            'sd_copied': synced['copied'] if synced else 0,
            'sd_existing': synced['existing'] if synced else 0,
            'sd_conflicts': synced['conflicts'] if synced else []}


def _verify(config: Config) -> dict:
    manifest = []
    if config.library.is_dir():
        for path in sorted(config.library.rglob('*')):
            if path.is_file() and (path.suffix.lower() in EXTENSIONS or path.suffix.lower() == '.wad'):
                if not path.resolve().is_relative_to(config.library):
                    continue
                manifest.append({'path': path.relative_to(config.library).as_posix(),
                                 'bytes': path.stat().st_size, 'sha256': sha256(path)})
    manifest_path = config.data_dir / 'files.json'
    previous = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.is_file() else []
    old = {entry['path'].replace('\\', '/'): entry['sha256'] for entry in previous}
    current = {entry['path']: entry['sha256'] for entry in manifest}
    changed = sorted(path for path in old.keys() & current.keys() if old[path] != current[path])
    missing = sorted(old.keys() - current.keys())
    if not changed and not missing:
        _write_json(manifest_path, manifest)
    return {'hashed_files': len(manifest), 'changed': changed, 'missing': missing,
            'manifest': str(manifest_path)}


def run_setup(config: Config, state: ArchiveState, steps: set[str]) -> dict:
    unknown = steps - set(STEP_ORDER)
    if unknown:
        raise ValueError(f'Étapes inconnues : {sorted(unknown)}')
    games = load_catalogue()
    games_by_id = {game.id: game for game in games}
    sources = load_verified_sources(config.source_manifest)
    if any(source['id'] not in games_by_id for source in sources):
        raise ValueError('Source absente du catalogue')
    scan_catalogue(games, config.library, sources, state)
    for step in STEP_ORDER:
        if step not in steps:
            continue
        state.set_step(step, 'running', {})
        try:
            status = 'completed'
            if step == 'scan':
                detail = scan_catalogue(games, config.library, sources, state)
            elif step == 'fetch':
                detail = _fetch(config, sources, games_by_id)
                status = 'failed' if detail['errors'] else 'completed'
            elif step == 'import':
                status, detail = _import(config, games)
            elif step == 'patch':
                status, detail = _patch(config, sources, games_by_id)
            elif step == 'prepare':
                detail = _prepare(config, games)
                status = 'failed' if detail['sd_conflicts'] else 'completed'
            elif step == 'install':
                if not config.adb_remote and not config.emulator_apks:
                    status, detail = 'skipped', {'reason': 'Aucun chemin ADB ni APK configuré'}
                else:
                    detail = {'apks': None, 'files': None}
                    apks = list(config.emulator_apks)
                    for source in sources:
                        if source.get('artifact_format') == 'apk':
                            path = config.data_dir / 'apks' / source['filename']
                            if path.is_file():
                                apks.append({'path': str(path), 'sha256': source['sha256'],
                                             'package': source['package']})
                    if apks:
                        detail['apks'] = install_apks(apks, serial=config.adb_serial)
                    if config.adb_remote:
                        plan = build_plan(config.library, config.adb_remote)
                        detail['files'] = deploy(plan, config.adb_remote, serial=config.adb_serial)
                    status = 'failed' if any(part and part['errors'] for part in detail.values()) else 'completed'
            elif step == 'verify':
                detail = _verify(config)
                status = 'failed' if detail['changed'] or detail['missing'] else 'completed'
            else:
                detail = _export_report(config, state)
            state.set_step(step, status, detail)
        except Exception as exc:
            state.set_step(step, 'failed', {'error': str(exc)})
        if step in ('fetch', 'import', 'patch'):
            scan_catalogue(games, config.library, sources, state)
    if 'report' in steps:
        _export_report(config, state)
    return state.summary()
