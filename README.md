# RETROID // THE ARCHIVE

Catalogue personnel et configuration reproductible de la **Retroid Pocket 6 (8 Go)**, avec une carte microSD 1 To. Projet préparé sur PC, à tester sur la console à réception.

## Contenu

- **899 jeux et créations de fans** — sélection éditoriale dans `catalogue/catalogue_ultimate.csv`, conservant les identifiants historiques.
- **Bibliothèque interactive** — fichier HTML autonome dans `docs/index.html` (ouvrable hors ligne et publiable avec GitHub Pages).
- **Émulation Android** — registre des émulateurs et des plateformes dans `emulators/`.
- **ROM hacks et fangames** — méthode d'installation et distinction claire entre patches et jeux PC dans `romhacks/`.
- **RetroAchievements** — guide dans `achievements/`.
- **Outils PC** — validation, import personnel, téléchargement contrôlé, patches IPS/BPS, préparation microSD et transfert ADB dans `retroid_archive/` et `scripts/`.
- **Guides** — installation Android, préparation de la carte et précautions légales dans `docs/`.

**Choix éditoriaux :** aucun jeu Pokémon officiel, seulement sept exceptions de course/sport, aucun ajout de jeu de combat versus. Certains fangames PC ne peuvent pas être lancés directement sur Android ; la présence au catalogue n'est pas une garantie de compatibilité.

## Démarrage rapide

1. Parcourir `docs/index.html` sur ordinateur.
2. Consulter `docs/INSTALLATION.md`.
3. Installer Python 3.12+ et exécuter `python -m retroid_archive status` (aucune dépendance externe).
4. À réception de la console, installer ES-DE puis **le laisser créer les dossiers** avant de copier des fichiers.
5. Utiliser `python scripts/audit_library.py --root "CHEMIN_VERS_LA_CARTE"` pour obtenir un rapport sans modifier la carte.

Pour importer ses propres fichiers, préparer la microSD, appliquer des patches ou préparer le transfert ADB, consulter [le guide d'automatisation](docs/AUTOMATISATION.md). Les commandes de préparation et de déploiement sont en simulation par défaut.

## Confidentialité, droits et périmètre

**Aucun fichier de ROM, BIOS, clé, firmware, sauvegarde personnelle ou APK propriétaire n'est inclus.** Le dépôt est **public**. Ne publier que des contenus redistribuables et des liens vers les pages légitimes des auteurs. Les ROM hacks nécessitent généralement les patches et une copie de base obtenue légalement. Les émulateurs et leurs liens sont répertoriés, non redistribués.

La liste est une sélection culturelle, pas un benchmark individuel de 899 jeux. Les réglages et performances doivent être confirmés sur Retroid Pocket 6. Aucun suivi des trophées officiels n'est simulé.

## État du projet

Le noyau local est opérationnel et testé par des tests automatisés. L'installation des émulateurs, l'interface de gestion connectée à l'état réel, les autres formats de patches et les tests individuels sur Retroid restent à réaliser. Ce dépôt sert de **source de vérité**, tandis que les données volumineuses restent sur la microSD ou un stockage personnel distinct.

Les marques et titres cités appartiennent à leurs ayants droit.
