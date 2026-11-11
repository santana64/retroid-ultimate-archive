"""Interface en ligne de commande Windows pour la préparation locale."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .catalogue import load_catalogue
from .adb import build_plan, deploy
from .downloads import download_manifest
from .importer import import_local
from .patching import apply_ips, apply_bps
from .storage import prepare_sd


def _print(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='retroid-archive', description='Préparer une bibliothèque Retroid personnelle')
    sub = parser.add_subparsers(dest='command', required=True)
    status = sub.add_parser('status', help='Bilan du catalogue')
    status.add_argument('--json', action='store_true')
    sources = sub.add_parser('sources', help='Exporter les pages sources connues')
    sources.add_argument('--output', required=True, type=Path)
    local = sub.add_parser('import-local', help='Copier les fichiers personnels correspondants')
    local.add_argument('--source', required=True, type=Path)
    local.add_argument('--library', required=True, type=Path)
    sd = sub.add_parser('prepare-sd', help='Préparer les dossiers microSD')
    sd.add_argument('--root', required=True, type=Path)
    sd.add_argument('--apply', action='store_true', help='Créer effectivement les dossiers')
    downloads = sub.add_parser('download', help='Télécharger un manifeste validé')
    downloads.add_argument('--manifest', required=True, type=Path)
    downloads.add_argument('--output', required=True, type=Path)
    downloads.add_argument('--workers', type=int, default=4)
    deployment = sub.add_parser('deploy', help='Planifier ou transférer les fichiers par ADB')
    deployment.add_argument('--library', required=True, type=Path)
    deployment.add_argument('--remote', required=True)
    deployment.add_argument('--serial')
    deployment.add_argument('--apply', action='store_true', help='Lancer le transfert ADB réel')
    for kind in ('ips', 'bps'):
        patch = sub.add_parser(f'patch-{kind}', help=f'Appliquer un patch {kind.upper()} à une copie personnelle')
        patch.add_argument('--base', required=True, type=Path)
        patch.add_argument('--patch', required=True, type=Path)
        patch.add_argument('--output', required=True, type=Path)
        patch.add_argument('--base-sha256', required=True)
    args = parser.parse_args(argv)
    games = load_catalogue()

    if args.command == 'status':
        platforms = Counter(game.platform for game in games)
        result = {'games': len(games), 'platforms': len(platforms),
                  'rom_hacks': sum('ROM hack' in game.platform for game in games),
                  'fangames': sum('fangame' in game.platform for game in games),
                  'patch_bases_recorded': sum(bool(game.patch_base) for game in games),
                  'source_pages': sum(bool(game.official_link) for game in games),
                  'files_downloaded': 0, 'files_imported': 0, 'patches_applied': 0,
                  'by_platform': dict(sorted(platforms.items()))}
        if args.json:
            _print(result)
        else:
            print(f"{result['games']} jeux, {result['platforms']} catégories, "
                  f"{result['rom_hacks']} ROM hacks, {result['source_pages']} pages sources connues.")
        return 0
    if args.command == 'sources':
        pages = [{'id': game.id, 'title': game.title, 'platform': game.platform,
                  'url': game.official_link, 'patch_base': game.patch_base,
                  'download_approved': False}
                 for game in games if game.official_link]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{len(pages)} pages sources exportées vers {args.output}')
        return 0
    if args.command == 'import-local':
        _print(import_local(args.source, args.library, games))
        return 0
    if args.command == 'prepare-sd':
        folders = prepare_sd(args.root, games, dry_run=not args.apply)
        _print({'mode': 'application' if args.apply else 'simulation', 'folders': [str(path) for path in folders]})
        return 0
    if args.command == 'download':
        result = download_manifest(args.manifest, args.output, max_workers=args.workers)
        _print(result)
        return 1 if result['errors'] else 0
    if args.command == 'deploy':
        plan = build_plan(args.library, args.remote)
        if args.apply:
            result = deploy(plan, args.remote, serial=args.serial)
            _print(result)
            return 1 if result['errors'] else 0
        _print({'mode': 'simulation', 'files': len(plan),
                'bytes': sum(item['bytes'] for item in plan), 'plan': plan})
        return 0
    if args.command in ('patch-ips', 'patch-bps'):
        func = apply_ips if args.command == 'patch-ips' else apply_bps
        digest = func(args.base, args.patch, args.output, args.base_sha256)
        _print({'output': str(args.output), 'sha256': digest})
        return 0
    return 2
