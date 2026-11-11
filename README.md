# RETROID // THE ARCHIVE

Catalogue personnel et configuration reproductible de la **Retroid Pocket 6 (8 Go)**, avec une carte microSD 1 To. Projet préparé sur PC, à tester sur la console à réception.

## Contenu

- **899 jeux et créations de fans** — sélection éditoriale dans `catalogue/catalogue_ultimate.csv`, conservant les identifiants historiques.
- **Bibliothèque interactive** — fichier HTML autonome dans `docs/index.html` (ouvrable hors ligne et publiable avec GitHub Pages).
- **Émulation Android** — registre des émulateurs et des plateformes dans `emulators/`.
- **ROM hacks et fangames** — méthode d'installation et distinction claire entre patches et jeux PC dans `romhacks/`.
- **RetroAchievements** — guide dans `achievements/`.
- **Outils PC** — validation, import personnel, téléchargement contrôlé, patches IPS/BPS/UPS, préparation microSD et transfert ADB dans `retroid_archive/` et `scripts/`.
- **Guides** — installation Android, préparation de la carte et précautions légales dans `docs/`.

**Choix éditoriaux :** aucun jeu Pokémon officiel, seulement sept exceptions de course/sport, aucun ajout de jeu de combat versus. Certains fangames PC ne peuvent pas être lancés directement sur Android ; la présence au catalogue n'est pas une garantie de compatibilité.

## Démarrage rapide

1. Installer Python 3.12+.
2. Dans le dépôt, lancer `python retroid.py setup --all`.
3. Lire `data/report.csv` : les 899 entrées ont chacune un statut.
4. Ouvrir `python retroid.py dashboard` pour suivre les opérations.
5. Copier `retroid.example.toml` vers `retroid.toml` pour ajouter ses dossiers de jeux personnels, sa microSD ou ses APK d'émulateur vérifiés, puis relancer `python retroid.py resume`.

La première exécution télécharge automatiquement les six sources contrôlées dans `sources/verified.json` (patches Gaia, Vision Quest et Subversion, mod SIGIL, quête Mystery of Solarus DX et APK Android de Sonic Robo Blast 2). Elle n'invente pas de fichiers pour les titres sans source ni copie locale. Les fichiers et rapports personnels restent dans `data/`, ignoré par Git.

Pour importer ses propres fichiers, préparer la microSD, appliquer des patches ou préparer le transfert ADB, consulter [le guide d'automatisation](docs/AUTOMATISATION.md). Les commandes de préparation et de déploiement sont en simulation par défaut.

## Confidentialité, droits et périmètre

**Aucun fichier de ROM, BIOS, clé, firmware, sauvegarde personnelle ou APK propriétaire n'est inclus.** Le dépôt est **public**. Ne publier que des contenus redistribuables et des liens vers les pages légitimes des auteurs. Les ROM hacks nécessitent généralement les patches et une copie de base obtenue légalement. Les émulateurs et leurs liens sont répertoriés, non redistribués.

La liste est une sélection culturelle, pas un benchmark individuel de 899 jeux. Les réglages et performances doivent être confirmés sur Retroid Pocket 6. Aucun suivi des trophées officiels n'est simulé.

## État du projet

La CLI, le scan des 899 entrées, la reprise, le téléchargement de sources validées, l'import local, les patches IPS/BPS/UPS, la copie microSD, le transfert ADB et le tableau de bord Windows disposent de tests automatisés. L'installation des APK locaux vérifiés est prête pour un appareil ADB, mais aucun émulateur ni jeu n'a été testé sur une Retroid Pocket 6. La recherche des autres sources, les configurations d'émulateur par système et les médias restent à compléter. Ce dépôt sert de **source de vérité**, tandis que les données volumineuses restent sur la microSD ou un stockage personnel distinct.

Les marques et titres cités appartiennent à leurs ayants droit.
