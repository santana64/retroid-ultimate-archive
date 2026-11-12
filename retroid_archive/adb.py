"""Plan et transfert ADB vérifiable de fichiers personnels."""
from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

from .importer import EXTENSIONS, sha256


def validate_remote(remote_root: str) -> None:
    if not (remote_root.startswith('/sdcard/') or remote_root.startswith('/storage/')):
        raise ValueError('Chemin distant hors stockage utilisateur')
    if any(segment in ('', '.', '..') for segment in remote_root.split('/')[1:]):
        raise ValueError('Chemin distant non canonique')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', remote_root):
        raise ValueError('Caractère interdit dans le chemin distant')


def parse_devices(output: str) -> list[str]:
    return [parts[0] for line in output.splitlines()[1:]
            if len(parts := line.split()) >= 2 and parts[1] == 'device']


def build_plan(library: Path, remote_root: str) -> list[dict]:
    validate_remote(remote_root)
    library = library.expanduser().resolve(strict=True)
    if not library.is_dir():
        raise ValueError('Bibliothèque locale inexistante')
    plan = []
    for file in sorted(library.rglob('*')):
        if not file.is_file() or file.suffix.lower() not in EXTENSIONS:
            continue
        if not file.resolve().is_relative_to(library):
            raise ValueError('Lien symbolique hors bibliothèque')
        relative = file.relative_to(library)
        if any('\n' in part or '\r' in part for part in relative.parts):
            raise ValueError('Nom de fichier incompatible avec ADB')
        plan.append({'local': str(file), 'remote': remote_root + '/' + relative.as_posix(),
                     'bytes': file.stat().st_size, 'sha256': sha256(file)})
    return plan


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False, timeout=1200)


def deploy(plan: list[dict], remote_root: str, serial: str | None = None, runner=_run) -> dict:
    validate_remote(remote_root)
    devices_result = runner(['adb', 'devices', '-l'])
    if devices_result.returncode:
        raise OSError(devices_result.stderr or 'ADB indisponible')
    devices = parse_devices(devices_result.stdout)
    if serial:
        if serial not in devices:
            raise ValueError('Appareil ADB demandé non autorisé ou absent')
    elif len(devices) == 1:
        serial = devices[0]
    else:
        raise ValueError('Un seul appareil ADB autorisé est requis, ou préciser --serial')
    prefix = ['adb', '-s', serial]
    volume = '/sdcard' if remote_root.startswith('/sdcard/') else '/' + '/'.join(remote_root.split('/')[1:3])
    space = runner(prefix + ['shell', f'df -k {shlex.quote(volume)}'])
    if space.returncode:
        raise OSError(space.stderr or 'Espace disponible inconnu')
    lines = [line.split() for line in space.stdout.splitlines() if line.strip()]
    try:
        free_bytes = int(lines[-1][3]) * 1024
    except (IndexError, ValueError) as exc:
        raise OSError('Réponse df illisible') from exc
    if free_bytes < sum(item['bytes'] for item in plan):
        raise OSError('Espace libre insuffisant pour le transfert')
    report: dict = {'serial': serial, 'transferred': 0, 'existing': 0, 'errors': []}
    for item in plan:
        remote = item['remote']
        if not remote.startswith(remote_root + '/'):
            raise ValueError('Fichier hors dossier distant')
        digest_cmd = f'sha256sum {shlex.quote(remote)}'
        current = runner(prefix + ['shell', digest_cmd])
        if current.returncode == 0 and current.stdout.split()[0:1] == [item['sha256']]:
            report['existing'] += 1
            continue
        mkdir = runner(prefix + ['shell', f'mkdir -p {shlex.quote(remote.rsplit("/", 1)[0])}'])
        if mkdir.returncode:
            report['errors'].append({'remote': remote, 'error': mkdir.stderr or 'mkdir impossible'})
            continue
        sent = runner(prefix + ['push', item['local'], remote])
        if sent.returncode:
            report['errors'].append({'remote': remote, 'error': sent.stderr or 'push impossible'})
            continue
        verified = runner(prefix + ['shell', digest_cmd])
        if verified.returncode or verified.stdout.split()[0:1] != [item['sha256']]:
            report['errors'].append({'remote': remote, 'error': 'SHA-256 distant incorrect'})
            continue
        report['transferred'] += 1
    return report


def install_apks(items: list[dict], serial: str | None = None, runner=_run) -> dict:
    """Installer des APK locaux hachés et confirmer leur paquet Android."""
    prepared = []
    for item in items:
        path = Path(item['path']).expanduser().resolve(strict=True)
        digest = item.get('sha256', '')
        package = item.get('package', '')
        if path.suffix.lower() != '.apk' or not path.is_file():
            raise ValueError('APK local invalide')
        if not re.fullmatch(r'[0-9a-fA-F]{64}', digest) or sha256(path) != digest.lower():
            raise ValueError('SHA-256 APK incorrect')
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+', package):
            raise ValueError('Identifiant de paquet Android invalide')
        prepared.append((path, package))
    devices_result = runner(['adb', 'devices', '-l'])
    if devices_result.returncode:
        raise OSError(devices_result.stderr or 'ADB indisponible')
    devices = parse_devices(devices_result.stdout)
    if serial:
        if serial not in devices:
            raise ValueError('Appareil ADB demandé non autorisé ou absent')
    elif len(devices) == 1:
        serial = devices[0]
    else:
        raise ValueError('Un seul appareil ADB autorisé est requis, ou préciser --serial')
    prefix = ['adb', '-s', serial]
    report: dict = {'serial': serial, 'installed': 0, 'errors': []}
    for path, package in prepared:
        result = runner(prefix + ['install', '-r', str(path)])
        if result.returncode or 'Success' not in result.stdout:
            report['errors'].append({'package': package, 'error': result.stderr or result.stdout or 'Installation échouée'})
            continue
        verified = runner(prefix + ['shell', f'pm path {package}'])
        if verified.returncode or 'package:' not in verified.stdout:
            report['errors'].append({'package': package, 'error': 'Paquet absent après installation'})
            continue
        report['installed'] += 1
    return report
