#!/usr/bin/env python3
"""Audit EN LECTURE SEULE des fichiers de la microSD; aucun réseau ni hash obligatoire."""
from __future__ import annotations
import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

CATALOGUE = Path(__file__).resolve().parents[1] / "catalogue" / "catalogue_ultimate.csv"
EXT = {".iso", ".cso", ".chd", ".rvz", ".gcz", ".gcm", ".wbfs", ".wia",
       ".pbp", ".cue", ".gdi", ".cdi", ".bin", ".ccd", ".img", ".m3u",
       ".zip", ".7z", ".nes", ".sfc", ".smc", ".gba", ".gbc", ".gb",
       ".n64", ".z64", ".v64", ".nds", ".3ds", ".cia", ".md", ".gen",
       ".pce", ".ws", ".wsc", ".scummvm"}
REGIONS = re.compile(r"\s*[\(\[]\s*(usa|europe|japan|world|en|fr|rev [a-z0-9]+|v[0-9.]+)[^\)\]]*[\)\]]", re.I)

def normalise(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = REGIONS.sub("", s)
    return re.sub(r"[^a-z0-9]+", " ", s.casefold()).strip()

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True, help="Dossier ROMs sur la microSD")
    p.add_argument("--output", type=Path, default=Path("audit.csv"), help="Rapport CSV local hors microSD")
    args = p.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        p.error("Dossier de jeux inexistant")
    output = args.output.expanduser().resolve()
    if output.is_relative_to(root):
        p.error("Le rapport doit rester hors de la carte auditée")
    index = defaultdict(list)
    for path in root.rglob("*"):
        try:
            if path.is_file() and path.suffix.lower() in EXT:
                index[normalise(path.stem)].append(str(path.relative_to(root)))
        except OSError:
            continue
    with CATALOGUE.open("r", encoding="utf-8-sig", newline="") as f:
        games = list(csv.DictReader(f))
    result = []
    for game in games:
        candidates = index.get(normalise(game["title"]), [])
        # Aucun rapprochement flou trompeur : une correspondance de nom reste une piste.
        status = "POSSIBLE_NOM" if len(candidates) == 1 else ("AMBIGU" if candidates else "ABSENT")
        result.append({"id": game["id"], "title": game["title"], "platform": game["platform"],
                       "etat": status, "fichiers_possibles": " | ".join(candidates)})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(result[0]))
        w.writeheader()
        w.writerows(result)
    print(f"{len(games)} entrées vérifiées sur les noms : {sum(r['etat']=='POSSIBLE_NOM' for r in result)} pistes uniques.")
    print(f"Rapport : {output} (le support audité n'a pas été modifié)")

if __name__ == "__main__":
    main()
