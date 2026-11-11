# Automatisation locale Windows

## Commande unique et état réel

Depuis la racine du dépôt, avec Python 3.12+ :

```powershell
python retroid.py setup --all
python retroid.py dashboard
```

`setup --all` lit les 899 entrées, télécharge les sources contrôlées de `sources/verified.json`, importe les dossiers personnels configurés, applique les patches disposant de leur base, prépare la bibliothèque et la carte configurée, tente les opérations ADB configurées, vérifie les fichiers et écrit `data/report.json`, `data/report.csv` et `data/files.json`. L'état et le journal structuré se trouvent dans `data/state.sqlite` et `data/state.jsonl`. Une nouvelle exécution avec `python retroid.py resume` réutilise les archives et copies identiques. Les commandes `scan`, `fetch`, `import`, `patch`, `prepare`, `install`, `verify` et `report` exécutent séparément une étape et mettent à jour le bilan.

La première exécution ne demande aucune configuration. Pour chercher ses propres copies, sa carte et des APK locaux, copier `retroid.example.toml` vers `retroid.toml` et y indiquer les chemins concernés. Exemple :

```toml
data_dir = "data"
import_roots = ["D:/Mes jeux", "F:/Archives personnelles"]
sd_root = "E:/"
max_workers = 4
```

Pour les patches BPS/UPS, le programme lit la taille et le CRC32 de la ROM de base dans le patch, recherche récursivement une copie compatible dans `import_roots` et `library`, y compris dans les archives ZIP personnelles, puis applique automatiquement le patch. Une ROM trouvée dans un ZIP est extraite dans le cache privé `data/base-cache/`. Les copies identiques dans plusieurs dossiers ne demandent aucun choix. Le fichier de base n'est jamais modifié. `patch_bases` reste un recours facultatif pour un patch IPS sans empreinte de base ou un cas ambigu ; aucun chemin par jeu n'est normalement nécessaire.

`sd_root` doit être un dossier ou lecteur existant. Le transfert microSD copie sans écraser les fichiers différents et contrôle chaque SHA-256. L'installation Android exige un appareil ADB autorisé. Pour un APK, ajouter `[[emulator_apks]]` avec le chemin local, son SHA-256 et l'identifiant de paquet Android ; l'installation est ensuite vérifiée avec `pm path`. Le programme ne télécharge pas encore les APK d'émulateurs faute de manifeste d'archives et d'empreintes validé. Il ne prétend pas configurer les contrôles ou garantir la compatibilité.

Les statuts `patch_only` et `mod_only` signifient qu'un fichier additionnel est présent, mais que le jeu de base manque. `available` signifie qu'un fichier local correspondant est présent ; cela ne garantit ni lancement ni compatibilité. `apk_ready` signifie qu'un APK Android contrôlé attend un appareil ADB pour être installé. `source_candidate` indique seulement une page à examiner. `missing` signifie qu'aucune source vérifiée ni copie locale n'a été trouvée par cette exécution. Le rapport CSV garde un statut explicite pour chaque ID.

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
    "download_authorized": true,
    "evidence_url": "https://exemple-auteur.invalid/licence"
  }
]
```

Cet exemple est un **gabarit**, pas une source réelle. Le moteur refuse les entrées sans page de preuve HTTPS, empreinte attendue ou confirmation explicite d'un téléchargement autorisé. Cela n'autorise pas la republication du fichier dans Git. Il refuse les chemins de sortie traversants et les noms dupliqués. Le téléchargement utilise jusqu'à 4 transferts simultanés par défaut, reprend les fichiers `.part`, réessaie les erreurs réseau temporaires et vérifie SHA-256 avant de renommer le fichier final.

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

Le tableau HTML existant reste un catalogue hors ligne ; son état « terminé » est stocké dans le navigateur. Le nouveau tableau Windows lit l'état réel de `state.sqlite`. Les APK locaux hachés peuvent être installés via ADB, mais le téléchargement et la configuration des émulateurs, RetroAchievements, les contrôles de lancement et le suivi des trophées ne sont pas encore automatisés. Les performances des jeux restent inconnues tant que la console et les fichiers personnels ne sont pas disponibles pour test.
