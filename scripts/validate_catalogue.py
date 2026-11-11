#!/usr/bin/env python3
"""Contrôles éditoriaux simples du catalogue CSV (stdlib seulement)."""
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path

CATALOGUE = Path(__file__).resolve().parents[1] / "catalogue" / "catalogue_ultimate.csv"
REQUIRED = {"id", "title", "platform", "genre", "source", "run_target"}

def main() -> None:
    with CATALOGUE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None, "En-tête absent"
        assert REQUIRED.issubset(reader.fieldnames), "Colonnes requises manquantes"
        rows = list(reader)
    errors = []
    ids = []
    titles = []
    for n, r in enumerate(rows, 2):
        try:
            ids.append(int(r["id"]))
        except (ValueError, TypeError):
            errors.append(f"ligne {n} : id invalide")
        if not r["title"].strip() or not r["platform"].strip():
            errors.append(f"ligne {n} : titre ou plateforme vide")
        titles.append((r["platform"].casefold().strip(), r["title"].casefold().strip()))
    duplicate_ids = [i for i, c in Counter(ids).items() if c > 1]
    duplicate_titles = [t for t, c in Counter(titles).items() if c > 1]
    if duplicate_ids:
        errors.append(f"IDs dupliqués : {duplicate_ids[:20]}")
    if duplicate_titles:
        errors.append(f"Jeux dupliqués plateforme/titre : {duplicate_titles[:20]}")
    if len(rows) != 899:
        errors.append(f"899 entrées attendues, {len(rows)} trouvées")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"OK : {len(rows)} jeux, {len(set(r['platform'] for r in rows))} catégories de plateforme, IDs uniques.")

if __name__ == "__main__":
    main()
