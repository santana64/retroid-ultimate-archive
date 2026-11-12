#!/usr/bin/env python3
"""Integrity tests for IKARIAN's personal-achievement catalogue.

The tests intentionally do not claim that an emulator can detect these trophies.
"""
import csv
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "ikarian" / "data.json"
SOURCE = ROOT / "catalogue" / "catalogue_ultimate.csv"
RARITIES = {"bronze", "silver", "gold", "platinum", "mythic"}
KINDS = {"start", "milestone", "explore", "challenge", "finish", "archive", "signature", "platinum"}


class IkarianCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
            cls.source = list(csv.DictReader(handle))
        cls.games = cls.data["games"]

    def test_snapshot_is_exactly_899_games(self):
        self.assertEqual(len(self.source), 899)
        self.assertEqual(len(self.games), 899)
        self.assertEqual(len({str(game["id"]) for game in self.games}), 899)

    def test_metadata_matches_the_original_csv(self):
        catalogue = {str(row["id"]): row for row in self.source}
        for game in self.games:
            source = catalogue[str(game["id"])]
            with self.subTest(id=game["id"]):
                for field in ("title", "platform", "genre", "priority", "grade"):
                    self.assertEqual(game[field], source[field])
        self.assertEqual(set(catalogue), {str(game["id"]) for game in self.games})

    def test_every_game_has_a_valid_unique_trophy_set(self):
        ids = []
        for game in self.games:
            with self.subTest(game=game["title"]):
                trophies = game["trophies"]
                self.assertGreaterEqual(len(trophies), 7)
                self.assertEqual(sum(t["kind"] == "platinum" for t in trophies), 1)
                for trophy in trophies:
                    ids.append(trophy["id"])
                    self.assertTrue(trophy["name"].strip())
                    self.assertTrue(trophy["description"].strip())
                    self.assertEqual(trophy["source"], "ikarian")
                    self.assertIn(trophy["rarity"], RARITIES)
                    self.assertIn(trophy["kind"], KINDS)
                    self.assertGreater(trophy["xp"], 0)
                    self.assertEqual(trophy["mode"], "derived" if trophy["kind"] == "platinum" else "self_report")
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_trophies_are_personal_proposals(self):
        self.assertEqual(self.data["schema"], "ikarian.v1")
        self.assertEqual(self.data["claim"], "proposed_personal_objectives_not_emulator_verified")
        self.assertGreaterEqual(sum(len(g["trophies"]) for g in self.games), 6300)

    def test_game_specific_awards_have_explicit_provenance(self):
        signatures = [(g["title"], t) for g in self.games for t in g["trophies"] if t["kind"] == "signature"]
        self.assertGreaterEqual(len(signatures), 20)
        self.assertEqual(len(signatures), len({title for title, _ in signatures}))
        self.assertTrue(all(t.get("curated") is True for _, t in signatures))

    def test_genres_and_platforms_are_covered(self):
        source_platforms = Counter(row["platform"] for row in self.source)
        output_platforms = Counter(g["platform"] for g in self.games)
        self.assertEqual(source_platforms, output_platforms)


if __name__ == "__main__":
    unittest.main()
