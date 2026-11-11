# Full Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exécuter la préparation maximale du catalogue avec `python retroid.py setup --all`, reprendre une exécution et afficher son état.

**Architecture:** Une configuration TOML déclare les emplacements personnels. Un moteur d'exécution durable enregistre les étapes et les résultats par jeu dans SQLite. Des sources vérifiées et figées sont téléchargées automatiquement ; les autres pages restent des candidats. La CLI et le tableau de bord lisent le même état.

**Tech Stack:** Python 3.12 stdlib, SQLite, urllib, concurrent.futures, Tkinter, ADB externe.

**Spec:** demande utilisateur du 11 novembre 2026 dans cette conversation.

## Global Constraints

- Préserver les 899 identifiants et les données du catalogue.
- Ne pas committer les ROM, BIOS, APK ou patches téléchargés dans le dépôt public.
- Ne jamais écraser un fichier personnel différent.
- `setup --all` poursuit les autres étapes lorsqu'une source ou un périphérique manque.
- Python 3.12+ et documentation française.

## Review Focus

- Téléchargement interrompu : le fichier partiel doit reprendre et le résultat doit être haché.
- Exécution répétée : ne pas télécharger ou recopier les fichiers identiques.
- Chemin personnel absent : l'étape doit être signalée comme ignorée sans faire échouer tout le catalogue.
- Archive hostile : extraction limitée aux membres attendus, sans traversée de chemin.
- Appareil ADB absent : le plan reste disponible, l'installation n'est pas prétendue effectuée.

---

### Task 1: Sources vérifiées

**Files:** `sources/verified.json`, `retroid_archive/sources.py`, `tests/test_sources.py`

**Interfaces:** `load_verified_sources(path: Path) -> list[dict]` ; `extract_verified(archive: Path, output: Path, members: list[str]) -> list[Path]`.

- [ ] Écrire les tests pour Gaia, SIGIL, membres d'archive autorisés et traversée.
- [ ] Exécuter les tests et constater l'échec attendu.
- [ ] Implémenter le chargeur et l'extraction sûre.
- [ ] Exécuter les tests, puis la suite complète.
- [ ] Commit.

### Task 2: État durable et scan

**Files:** `retroid_archive/state.py`, `retroid_archive/scanner.py`, `tests/test_state.py`

**Interfaces:** `ArchiveState(path: Path)` ; `scan_catalogue(games: list[Game], library: Path, sources: list[dict], state: ArchiveState) -> dict`.

- [ ] Écrire les tests pour 899 entrées, états et reprise.
- [ ] Exécuter les tests et constater l'échec attendu.
- [ ] Implémenter SQLite et l'analyse des fichiers locaux.
- [ ] Exécuter les tests, puis la suite complète.
- [ ] Commit.

### Task 3: Orchestration et commandes

**Files:** `retroid.py`, `retroid_archive/config.py`, `retroid_archive/runner.py`, `retroid_archive/cli.py`, `tests/test_runner.py`

**Interfaces:** `load_config(path: Path) -> Config` ; `run_setup(config: Config, state: ArchiveState, steps: set[str]) -> dict`.

- [ ] Écrire les tests CLI et orchestration, y compris dossier manquant et seconde exécution.
- [ ] Exécuter les tests et constater l'échec attendu.
- [ ] Implémenter `setup --all`, `scan`, `fetch`, `import`, `patch`, `prepare`, `install`, `verify`, `resume`, `report`.
- [ ] Exécuter les tests, puis la suite complète.
- [ ] Commit.

### Task 4: Tableau de bord et documentation

**Files:** `retroid_archive/dashboard.py`, `docs/AUTOMATISATION.md`, `README.md`, `.github/workflows/catalogue.yml`

**Interfaces:** `launch_dashboard(state_path: Path) -> None`.

- [ ] Écrire les tests du modèle d'affichage et de la sortie rapport.
- [ ] Exécuter les tests et constater l'échec attendu.
- [ ] Implémenter la fenêtre Tkinter avec rafraîchissement d'état.
- [ ] Exécuter les tests, la compilation et les commandes de démonstration.
- [ ] Commit, push et mise à jour de la PR.
