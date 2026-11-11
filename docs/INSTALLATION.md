# Préparer la Retroid Pocket 6 / 8 Go et microSD 1 To

## Avant Noël — sur PC

1. Conserver ce dépôt sur l'ordinateur : `git clone https://github.com/santana64/retroid-ultimate-archive.git`.
2. Ouvrir `docs/index.html` dans un navigateur ; examiner les 899 titres, puis choisir une **première vague de 30 à 60 jeux**.
3. Préparer les jeux et fichiers système que tu as légalement le droit d'utiliser. Garder ces fichiers **hors Git** et effectuer une sauvegarde indépendante.
4. Vérifier le catalogue : `python scripts/validate_catalogue.py`.
5. Garder au moins 10 à 20 % d'espace libre sur la microSD pour les changements et médias (repère de gestion, pas exigence du fabricant).

## À réception de la console

1. Vérifier mises à jour système, réseau, compte Android et manette.
2. Formater la microSD **depuis le système de la console** si nécessaire (cette opération efface son contenu ; sauvegarder d'abord).
3. Installer ES-DE depuis https://es-de.org/ et l'exécuter **avant** de créer manuellement des dossiers de systèmes.
4. Choisir la microSD comme emplacement ROMs et laisser ES-DE générer sa structure.
5. Installer les émulateurs nécessaires, un par un, via les sources de `emulators/registry.json`.
6. Configurer autorisations Android, manette, résolutions de départ, sauvegardes, touches de retour et sortie.
7. Copier un ou deux jeux par plateforme, tester lancement + sauvegarde + rechargement, puis élargir.
8. Configurer les BIOS légalement obtenus quand nécessaires ; ne jamais les stocker sur GitHub.
9. Configurer le scraper de jaquettes/vidéos avec les fournisseurs autorisés, puis les collections ES-DE.
10. Activer RetroAchievements uniquement pour les systèmes pris en charge ; vérifier chaque jeu dans le service.

## Tester sa microSD depuis un PC

Exemple : `python scripts/audit_library.py --root "/chemin/vers/la/microSD/ROMs" --output audit.csv`.

L'outil n'écrit **rien sur la carte**, il classe les noms de fichiers comme correspondances possibles et produit un rapport sur le PC. Un résultat trouvé par nom ne certifie ni le contenu de la ROM ni sa compatibilité.

## Autres appareils

La Switch 2 et la Xiaomi Pad 8 (GeForce NOW) restent des bibliothèques séparées. Le tableau de bord peut les représenter à terme, mais il ne les contrôle pas et ne lance pas leurs applications à distance.
