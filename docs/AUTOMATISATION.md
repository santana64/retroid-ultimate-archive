# Automatisation locale Windows

## Préparer le PC

Installer Python 3.12 ou plus récent. Depuis la racine du dépôt, utiliser `py -3.12 -m retroid_archive` ou installer le paquet avec `py -3.12 -m pip install -e .` puis utiliser `retroid-archive`.

```powershell
py -3.12 -m retroid_archive status --json
py -3.12 -m retroid_archive sources --output .\sources.json
py -3.12 -m unittest discover -s tests -v
```

`sources.json` rassemble les pages de projet connues. Une page n'est **pas** une autorisation de téléchargement. Pour les ROM hacks, privilégier les pages des auteurs, PokéCommunity, ROM Hack Plaza, Metroid Construction et les dépôts de projets. Vérifier la version de la base et les indications de l'auteur. Le catalogue contient actuellement 22 pages sources et 49 bases de patch renseignées ; les autres fiches demandent encore une recherche.

## Importer ses fichiers personnels

```powershell
py -3.12 -m retroid_archive import-local --source "D:\Mes jeux" --library "E:\ROMs"
```

Le rapprochement se fait sur le titre normalisé, avec la plateforme déduite de certaines extensions. Les noms ambigus restent sans copie. La source reste intacte. Le programme copie vers un fichier temporaire, vérifie SHA-256, puis place le fichier dans le dossier système. Si la cible existe avec un contenu différent, le conflit est signalé sans écrasement. Les fichiers `.cue` et leurs `.bin` associés peuvent nécessiter une vérification manuelle : l'import par nom ne reconstruit pas les ensembles multi-fichiers.

## Télécharger des contenus redistribuables

Créer un manifeste JSON local après avoir vérifié l'autorisation du projet et le SHA-256 du **fichier exact** proposé :

```json
[
  {
    "id": 620,
    "url": "https://exemple-auteur.invalid/patch.bps",
    "filename": "patch.bps",
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "redistribution_verified": true,
    "evidence_url": "https://exemple-auteur.invalid/licence"
  }
]
```

Cet exemple est un **gabarit**, pas une source réelle. Le moteur refuse les entrées sans page de preuve HTTPS, empreinte attendue, ou confirmation explicite de distribution. Il refuse les chemins de sortie traversants et les noms dupliqués. Le téléchargement utilise jusqu'à 4 transferts simultanés par défaut, reprend les fichiers `.part`, réessaie les erreurs réseau temporaires et vérifie SHA-256 avant de renommer le fichier final.

```powershell
py -3.12 -m retroid_archive download --manifest .\mes-sources.json --output "D:\Retroid\Patches" --workers 4
```

L'outil ne télécharge pas automatiquement les 899 titres : la majorité n'a pas de distribution autorisée connue. Les copies commerciales doivent provenir de fichiers personnels importés localement.

## Appliquer un patch

La base personnelle doit correspondre exactement à la version et à la région demandées par l'auteur. Calculer son SHA-256 avec `Get-FileHash -Algorithm SHA256`, puis appliquer le patch :

```powershell
py -3.12 -m retroid_archive patch-ips --base "D:\Jeux\base.gba" --patch "D:\Patches\mod.ips" --output "D:\Jeux\mod.gba" --base-sha256 VOTRE_SHA256
py -3.12 -m retroid_archive patch-bps --base "D:\Jeux\base.gba" --patch "D:\Patches\mod.bps" --output "D:\Jeux\mod.gba" --base-sha256 VOTRE_SHA256
py -3.12 -m retroid_archive patch-ups --base "D:\Jeux\base.gba" --patch "D:\Patches\mod.ups" --output "D:\Jeux\mod.gba" --base-sha256 VOTRE_SHA256
```

La base et le patch ne sont jamais modifiés. BPS et UPS vérifient également les CRC intégrés du patch, de la base et de la cible. IPS n'intègre pas de CRC cible : comparer au SHA-256 publié par l'auteur si disponible. xdelta n'est pas encore intégré.

Le patch [Pokémon Gaia v3.2](https://www.pokecommunity.com/threads/pok%C3%A9mon-gaia-version.326118/) provient du miroir indiqué par son auteur. Son archive ZIP a le SHA-256 `13b77277b775d2e526f531ac290667b9f1b557a680fc012dc87204a140a0c3be` et contient `pokemon_gaia_v3.2.ups`, un README et `NUPS.exe`. Le README indique une base FireRed (U) « 1635 », avec « 1636 » également compatible selon l'auteur. Ne pas exécuter le programme joint à l'archive ; notre commande `patch-ups` applique le patch directement.

## Préparer et transférer sur microSD

Laisser d'abord ES-DE créer ses dossiers sur l'appareil. Puis prévisualiser les dossiers proposés :

```powershell
py -3.12 -m retroid_archive prepare-sd --root "E:\"
py -3.12 -m retroid_archive prepare-sd --root "E:\" --apply
```

Les dossiers créés sont `ROMs/<système>`, `BIOS`, `Patches`, `Saves`, `SaveStates`, `Media`, `Metadata`, `Config` et `Collections`. Les BIOS doivent provenir des fichiers personnels et ne sont jamais téléchargés par cet outil. Les noms de dossiers restent à comparer aux conventions de la version ES-DE installée avant de copier toute la bibliothèque.

Avec Android Platform Tools (`adb`) dans le PATH et le débogage USB autorisé :

```powershell
py -3.12 -m retroid_archive deploy --library "D:\Retroid\ROMs" --remote /storage/1234-5678/ROMs
py -3.12 -m retroid_archive deploy --library "D:\Retroid\ROMs" --remote /storage/1234-5678/ROMs --apply
```

Le premier appel affiche le plan sans accéder à l'appareil. Le second exige un appareil ADB autorisé unique, vérifie l'espace libre, ignore les fichiers déjà identiques et contrôle SHA-256 après chaque transfert. `--serial` désigne un appareil précis si plusieurs sont connectés. Le chemin `/storage/1234-5678` est un exemple ; remplacer l'identifiant par celui de la carte réelle. Ce parcours n'a pas été testé sur une Retroid Pocket 6 physique.

## État et limites

Le tableau HTML existant reste un catalogue hors ligne ; son état « terminé » est stocké dans le navigateur, pas relié aux fichiers du PC. L'installation des APK, la configuration des émulateurs, RetroAchievements, les contrôles de lancement et le suivi des trophées ne sont pas encore automatisés. Les performances des jeux restent inconnues tant que la console et les fichiers personnels ne sont pas disponibles pour test.
