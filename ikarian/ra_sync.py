#!/usr/bin/env python3
"""Local RetroAchievements export for IKARIAN.

Requires RA_WEB_API_KEY in your environment. Never uploads credentials to GitHub.
This exports RECENT genuine RA events separately from IKARIAN's manual trophies.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def normalize_event(record: dict) -> dict | None:
    try:
        aid = int(record["AchievementID"])
        game_id = int(record["GameID"])
        if aid <= 0 or game_id <= 0:
            return None
        return {
            "achievementId": aid,
            "gameId": game_id,
            "gameTitle": str(record["GameTitle"])[:200],
            "consoleName": str(record.get("ConsoleName", ""))[:100],
            "title": str(record["Title"])[:200],
            "description": str(record.get("Description", ""))[:600],
            "points": max(0, int(record.get("Points") or 0)),
            "hardcore": bool(int(record.get("HardcoreMode") or 0)),
            "date": str(record.get("Date", ""))[:40],
            "badgeName": str(record.get("BadgeName", ""))[:70],
        }
    except (KeyError, TypeError, ValueError):
        return None


def merge_events(previous: list[dict], current: list[dict]) -> list[dict]:
    merged: dict[tuple[int, bool], dict] = {}
    for event in previous + current:
        merged[(event["achievementId"], bool(event["hardcore"]))] = event
    return sorted(merged.values(), key=lambda item: item["date"], reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporter les succès récents RetroAchievements vers IKARIAN")
    parser.add_argument("--username", required=True, help="Compte public RetroAchievements")
    parser.add_argument("--minutes", type=int, default=1440, help="Fenêtre de récupération (défaut : 1440 = 24 h)")
    parser.add_argument("--output", type=Path, default=Path.home() / "IKARIAN" / "ra-unlocks.private.json")
    args = parser.parse_args()
    if not 1 <= args.minutes <= 43200:
        parser.error("--minutes doit être entre 1 et 43200")
    key = os.environ.get("RA_WEB_API_KEY", "").strip()
    if not key:
        parser.error("Définis RA_WEB_API_KEY localement avant de lancer la synchronisation.")
    username = args.username.strip()
    if not username:
        parser.error("Le nom de compte est vide.")

    query = urlencode({"y": key, "u": username, "m": args.minutes})
    request = Request("https://retroachievements.org/API/API_GetUserRecentAchievements.php?" + query,
                      headers={"User-Agent": "IKARIAN-personal-archive/1.0", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as exc:
        print("RetroAchievements a renvoyé HTTP " + str(exc.code), file=sys.stderr)
        return 1
    except (URLError, TimeoutError, json.JSONDecodeError):
        print("Impossible de récupérer ou lire la réponse de RetroAchievements.", file=sys.stderr)
        return 1
    if not isinstance(payload, list):
        print("Réponse API inattendue (liste de trophées attendue).", file=sys.stderr)
        return 1

    current = [event for item in payload if isinstance(item, dict) if (event := normalize_event(item))]
    previous = []
    if args.output.exists():
        try:
            old = json.loads(args.output.read_text(encoding="utf-8"))
            if old.get("schema") == "ikarian-ra-import.v1" and old.get("username") == username:
                previous = [x for x in old.get("unlocks", []) if isinstance(x, dict)]
        except (OSError, ValueError, TypeError):
            pass

    events = merge_events(previous, current)
    export = {
        "schema": "ikarian-ra-import.v1",
        "source": "retroachievements-api",
        "username": username,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "minutes": args.minutes,
        "unlocks": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(args.output, 0o600)
    except OSError:
        pass
    print(f"Export réussi : {len(current)} événements récupérés, {len(events)} uniques conservés.")
    print(f"Fichier privé : {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
