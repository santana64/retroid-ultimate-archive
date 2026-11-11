"""Tableau de bord Windows lisant l'état réel en continu."""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path

from .config import load_config
from .state import ArchiveState

REPO_ROOT = Path(__file__).resolve().parents[1]
BG = '#0b0815'
PANEL = '#1c142b'
PANEL_LIGHT = '#2b1e3f'
TEXT = '#f3eaff'
MUTED = '#ad9bbf'
ACCENT = '#c39aff'
MINT = '#7de1c3'


def dashboard_snapshot(state_path: Path) -> dict:
    with ArchiveState(state_path) as state:
        summary = state.summary()
        rows = state.games()
    steps = {item['name']: item for item in summary['steps']}
    fetch = steps.get('fetch', {}).get('detail', {})
    imported = steps.get('import', {}).get('detail', {})
    patched = steps.get('patch', {}).get('detail', {})
    installed = steps.get('install', {}).get('detail', {})
    apks = installed.get('apks') or {}
    return {**summary, 'rows': rows, 'downloads': fetch.get('downloaded', 0) + fetch.get('existing', 0),
            'imports': imported.get('imported', 0) + imported.get('existing', 0),
            'patches': patched.get('applied', 0) + patched.get('existing', 0),
            'apks_installed': apks.get('installed', 0),
            'active': sum(item['status'] == 'running' for item in summary['steps']),
            'errors': sum(item['status'] == 'failed' for item in summary['steps'])}


def launch_dashboard(config_path: Path | None = None) -> None:
    import tkinter as tk
    from tkinter import ttk

    config = load_config(config_path)
    state_path = config.data_dir / 'state.sqlite'
    root = tk.Tk()
    root.title('RETROID // ULTIMATE ARCHIVE')
    root.geometry('1360x850')
    root.minsize(950, 650)
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('Archive.Treeview', background=PANEL, fieldbackground=PANEL,
                    foreground=TEXT, borderwidth=0, rowheight=29, font=('Segoe UI', 10))
    style.configure('Archive.Treeview.Heading', background=PANEL_LIGHT, foreground=ACCENT,
                    borderwidth=0, font=('Segoe UI Semibold', 10))
    style.map('Archive.Treeview', background=[('selected', '#624488')], foreground=[('selected', '#ffffff')])
    style.configure('Archive.Horizontal.TProgressbar', troughcolor=PANEL_LIGHT, background=ACCENT)

    main = tk.Frame(root, bg=BG, padx=26, pady=20)
    main.pack(fill='both', expand=True)
    tk.Label(main, text='RETROID  //  ULTIMATE ARCHIVE', bg=BG, fg=ACCENT,
             font=('Segoe UI Semibold', 12)).pack(anchor='w')
    tk.Label(main, text='Ta bibliothèque, en clair.', bg=BG, fg=TEXT,
             font=('Segoe UI Semibold', 30)).pack(anchor='w', pady=(3, 1))
    tk.Label(main, text='État réel des fichiers et opérations • aucune compatibilité présumée',
             bg=BG, fg=MUTED, font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 18))

    cards = tk.Frame(main, bg=BG)
    cards.pack(fill='x', pady=(0, 15))
    keys = [('games', 'JEUX SUIVIS'), ('available', 'FICHIERS PRÊTS'),
            ('downloads', 'RÉCUPÉRÉS'), ('imports', 'IMPORTS'),
            ('patches', 'PATCHES'), ('missing', 'SANS SOURCE'),
            ('active', 'EN COURS'), ('errors', 'ERREURS')]
    values = {}
    for i, (key, label) in enumerate(keys):
        card = tk.Frame(cards, bg=PANEL, padx=14, pady=12)
        card.grid(row=0, column=i, sticky='nsew', padx=(0, 8 if i < len(keys) - 1 else 0))
        cards.columnconfigure(i, weight=1)
        tk.Label(card, text=label, bg=PANEL, fg=MUTED, font=('Segoe UI Semibold', 9)).pack(anchor='w')
        value = tk.Label(card, text='—', bg=PANEL, fg=TEXT, font=('Segoe UI Semibold', 25))
        value.pack(anchor='w')
        values[key] = value

    progress = ttk.Progressbar(main, style='Archive.Horizontal.TProgressbar', mode='determinate', maximum=899)
    progress.pack(fill='x', pady=(0, 15))
    actions = tk.Frame(main, bg=BG)
    actions.pack(fill='x', pady=(0, 12))
    query = tk.StringVar()
    search = tk.Entry(actions, textvariable=query, bg=PANEL_LIGHT, fg=TEXT, insertbackground=ACCENT,
                      relief='flat', font=('Segoe UI', 11), width=42)
    search.pack(side='left', ipady=7)
    tk.Label(actions, text='  Rechercher un titre, système ou statut', bg=BG, fg=MUTED,
             font=('Segoe UI', 10)).pack(side='left')

    buttons = []
    process_state = {'running': False, 'message': ''}

    def run_command(command: str) -> None:
        if process_state['running']:
            return
        process_state['running'] = True
        process_state['message'] = f'{command} en cours…'
        for button in buttons:
            button.configure(state='disabled')

        def worker() -> None:
            args = [sys.executable, str(REPO_ROOT / 'retroid.py'), command]
            if command == 'setup':
                args.append('--all')
            if config_path:
                args += ['--config', str(config_path)]
            try:
                result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True,
                                        text=True, errors='replace', timeout=7200)
                process_state['message'] = f'{command} terminé (code {result.returncode})'
                if result.returncode:
                    process_state['message'] += ': ' + (result.stderr or result.stdout)[-300:]
            except Exception as exc:
                process_state['message'] = f'{command} : {exc}'
            finally:
                process_state['running'] = False

        threading.Thread(target=worker, daemon=True).start()

    for label, command in [('Lancer setup --all', 'setup'), ('Reprendre', 'resume'), ('Actualiser le scan', 'scan')]:
        button = tk.Button(actions, text=label, command=lambda c=command: run_command(c),
                           bg=ACCENT if command == 'setup' else PANEL_LIGHT,
                           fg='#170c23' if command == 'setup' else TEXT,
                           activebackground='#e2cfff', relief='flat', padx=13, pady=7,
                           font=('Segoe UI Semibold', 10))
        button.pack(side='right', padx=(8, 0))
        buttons.append(button)

    columns = ('id', 'title', 'platform', 'status', 'bytes')
    table_frame = tk.Frame(main, bg=PANEL)
    table_frame.pack(fill='both', expand=True)
    table = ttk.Treeview(table_frame, columns=columns, show='headings', style='Archive.Treeview')
    headings = {'id': '#', 'title': 'JEU', 'platform': 'PLATEFORME',
                'status': 'ÉTAT VÉRIFIÉ', 'bytes': 'TAILLE'}
    widths = {'id': 55, 'title': 420, 'platform': 210, 'status': 180, 'bytes': 100}
    for column in columns:
        table.heading(column, text=headings[column])
        table.column(column, width=widths[column], stretch=column == 'title')
    table.pack(side='left', fill='both', expand=True)
    scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=table.yview)
    scrollbar.pack(side='right', fill='y')
    table.configure(yscrollcommand=scrollbar.set)
    table.tag_configure('available', foreground=MINT)
    table.tag_configure('patch_only', foreground='#e7c77f')
    table.tag_configure('mod_only', foreground='#e7c77f')
    table.tag_configure('missing', foreground=MUTED)

    footer = tk.Label(main, text='', bg=BG, fg=MUTED, anchor='w', font=('Segoe UI', 10))
    footer.pack(fill='x', pady=(12, 0))
    rows_cache: list[dict] = []
    last_key = {'value': None}

    def draw_rows() -> None:
        term = query.get().casefold().strip()
        key = (term, len(rows_cache), rows_cache[-1]['updated_at'] if rows_cache else '')
        if key == last_key['value']:
            return
        last_key['value'] = key
        table.delete(*table.get_children())
        for row in rows_cache:
            if term and term not in (row['title'] + ' ' + row['platform'] + ' ' + row['status']).casefold():
                continue
            size = f"{row['bytes'] / 1048576:.1f} Mo" if row['bytes'] else '—'
            table.insert('', 'end', values=(row['id'], row['title'], row['platform'], row['status'], size),
                         tags=(row['status'],))

    query.trace_add('write', lambda *_: draw_rows())

    def refresh() -> None:
        nonlocal rows_cache
        try:
            snapshot = dashboard_snapshot(state_path)
            rows_cache = snapshot['rows']
            for key, _ in keys:
                values[key].configure(text=str(snapshot.get(key, 0)))
            progress['value'] = snapshot['games']
            draw_rows()
            volume = config.sd_root or config.library
            while not volume.exists() and volume != volume.parent:
                volume = volume.parent
            free = shutil.disk_usage(volume).free / (1024 ** 3)
            footer.configure(text=f"Espace libre : {free:.1f} Gio • APK installés : {snapshot['apks_installed']} • "
                                  f"{process_state['message'] or 'En attente'}")
            for button in buttons:
                button.configure(state='disabled' if process_state['running'] else 'normal')
        except Exception as exc:
            footer.configure(text=f'État indisponible : {exc}')
        root.after(1500, refresh)

    refresh()
    root.mainloop()
