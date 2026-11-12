"""État durable des 899 entrées et des étapes d'exécution."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ArchiveState:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                platform TEXT NOT NULL,
                status TEXT NOT NULL,
                file_path TEXT,
                bytes INTEGER NOT NULL DEFAULT 0,
                source_url TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS steps (
                name TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                detail TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        ''')

    def __enter__(self) -> ArchiveState:
        return self

    def __exit__(self, *_: object) -> None:
        self.db.close()

    def update_game(self, game_id: int, title: str, platform: str, status: str,
                    file_path: str | None = None, size: int = 0, source_url: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute('''
            INSERT INTO games (id,title,platform,status,file_path,bytes,source_url,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, platform=excluded.platform,
              status=excluded.status, file_path=excluded.file_path, bytes=excluded.bytes,
              source_url=excluded.source_url, updated_at=excluded.updated_at
        ''', (game_id, title, platform, status, file_path, size, source_url, now))
        self.db.commit()

    def game(self, game_id: int) -> dict | None:
        row = self.db.execute('SELECT * FROM games WHERE id=?', (game_id,)).fetchone()
        return dict(row) if row else None

    def games(self) -> list[dict]:
        return [dict(row) for row in self.db.execute('SELECT * FROM games ORDER BY id')]

    def retain_games(self, ids: set[int]) -> None:
        if not ids:
            raise ValueError('Catalogue vide')
        placeholders = ','.join('?' for _ in ids)
        self.db.execute(f'DELETE FROM games WHERE id NOT IN ({placeholders})', tuple(sorted(ids)))
        self.db.commit()

    def set_step(self, name: str, status: str, detail: dict) -> None:
        if status not in ('running', 'completed', 'skipped', 'failed'):
            raise ValueError('Statut d’étape invalide')
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute('''
            INSERT INTO steps (name,status,detail,updated_at) VALUES (?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET status=excluded.status,
              detail=excluded.detail, updated_at=excluded.updated_at
        ''', (name, status, json.dumps(detail, ensure_ascii=False), now))
        self.db.commit()
        with self.path.with_suffix('.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'at': now, 'name': name, 'status': status,
                                     'detail': detail}, ensure_ascii=False) + '\n')

    def step(self, name: str) -> dict | None:
        row = self.db.execute('SELECT * FROM steps WHERE name=?', (name,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result['detail'] = json.loads(result['detail'])
        return result

    def steps(self) -> list[dict]:
        rows = [dict(row) for row in self.db.execute('SELECT * FROM steps ORDER BY name')]
        for row in rows:
            row['detail'] = json.loads(row['detail'])
        return rows

    def summary(self) -> dict:
        counts = {row['status']: row['n'] for row in self.db.execute(
            'SELECT status, COUNT(*) AS n FROM games GROUP BY status')}
        return {'games': sum(counts.values()), 'available': counts.get('available', 0),
                'apk_ready': counts.get('apk_ready', 0),
                'downloadable': counts.get('downloadable', 0),
                'patch_only': counts.get('patch_only', 0),
                'mod_only': counts.get('mod_only', 0),
                'source_candidate': counts.get('source_candidate', 0),
                'ambiguous': counts.get('ambiguous', 0),
                'missing': counts.get('missing', 0), 'status_counts': counts,
                'steps': self.steps()}
