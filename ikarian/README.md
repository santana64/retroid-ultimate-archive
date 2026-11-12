# IKARIAN — Aether Achievement System

**Version 1 : archive personnelle jouable sur navigateur, tablette, PC ou Android.**

IKARIAN est une couche de progression indépendante pour la collection `retroid-ultimate-archive`. L'application se trouve dans [`docs/ikarian/`](../docs/ikarian/).

## Ce qui fonctionne dès cette version

- **899 fiches de jeux** construites directement à partir de `catalogue/catalogue_ultimate.csv`.
- **6 315 trophées personnels proposés**, répartis en Bronze, Argent, Or, Platine et Mythique ; **22 défis signature** correspondent à des jeux identifiés.
- **Fiches par jeu**, filtres, recherche sans accents, favoris et navigation manette via le navigateur si celui-ci la prend en charge.
- **Validation manuelle** des objectifs, dates de déblocage, XP et niveaux.
- **Platine automatique** lorsqu'on a déclaré tous les autres objectifs d'un jeu.
- **Constellations** calculées à partir des jeux maîtrisés sur plusieurs plateformes.
- **Toasts animés**, célébrations rares et sons originaux désactivés par défaut.
- **Carnet de notes** par jeu. Le trophée du carnet nécessite une note effectivement enregistrée.
- **Sauvegarde et restauration JSON** pour migrer la progression entre navigateurs ou appareils.
- **PWA avec cache hors ligne** après une première installation en HTTPS ou sur localhost.
- **Import séparé RetroAchievements** à partir du script local `ra_sync.py` ; les événements importés ne produisent ni XP ni déblocage IKARIAN.

## Démarrer depuis Windows

Depuis le dossier racine du dépôt :

```powershell
cd docs
python -m http.server 8000
```

Puis ouvrir **http://localhost:8000/ikarian/** dans un navigateur.

Ne pas ouvrir `index.html` en double-cliquant : le navigateur bloque généralement `fetch("./data.json")` depuis le protocole `file://`.

## Sur la Retroid Pocket 6

Une fois le site déployé sur un hébergement HTTPS (par exemple GitHub Pages configuré sur `main/docs`), ouvrir l'URL `/ikarian/` dans Chrome Android. Le raccourci « Ajouter à l'écran d'accueil » peut permettre d'y accéder comme à une application. L'installation autonome dépend du navigateur et du support du manifeste.

**Pas de notification système en superposition d'un jeu dans cette version** : les notifications sont des effets au sein de l'interface web. Pour les afficher *pendant* l'émulation, il faudra développer un compagnon Android et des intégrations avec des émulateurs capables de fournir des événements de succès.

## Importer des succès RetroAchievements

Les succès RetroAchievements sont distincts des objectifs personnels et ne sont jamais pris pour des trophées confirmés par IKARIAN.

1. Créer ou utiliser son compte sur https://retroachievements.org/ et récupérer sa **Web API Key** depuis le panneau de contrôle.
2. Dans PowerShell sur ton PC, définir la variable d'environnement sans écrire la clé dans un fichier du dépôt :

```powershell
$env:RA_WEB_API_KEY = "CLE_DU_COMPTE"
python ikarian/ra_sync.py --username TON_PSEUDO --minutes 43200
```

3. Le script écrit `~/IKARIAN/ra-unlocks.private.json`. Importer ce fichier via l'onglet **RetroAchievements** de l'application.

Le script s'appuie sur l'endpoint officiel `API_GetUserRecentAchievements.php`. Il récupère une **fenêtre de succès récents**, pas nécessairement l'historique complet du compte ; en lançant le script régulièrement, le fichier local cumule les événements identifiés. Il préserve les déblocages Hardcore et Softcore comme événements distincts.

L'association à un jeu IKARIAN se fait seulement si le **titre normalisé correspond exactement et sans ambiguïté** à une unique entrée du catalogue. Sinon l'événement est conservé dans l'onglet RetroAchievements sans attribution arbitraire.

**Ne jamais publier la clé API, les sauvegardes ou les fichiers RA privés sur le dépôt public.**

## Structure

```
docs/ikarian/
  index.html             Tableau de bord
  styles.css             Identité visuelle lilas / obscur
  app.js                 Logique des trophées, XP, collections, sauvegardes
  data.json              Manifeste des 899 jeux et 6 315 objectifs
  sw.js                  Cache hors ligne
  manifest.webmanifest   Métadonnées PWA
  icon.svg               Icône
ikarian/
  ra_sync.py             Client API RA local (clé via variable d'environnement)
  tests/test_archive.py  Tests de cohérence du catalogue
.github/workflows/ikarian.yml
```

## Origine des trophées et limitations

- **Trophées personnels IKARIAN** : propositions éditoriales à valider manuellement. Le CSV ne contient pas les états internes des jeux, les adresses mémoire, ni des preuves de déblocage. Des objectifs génériques, propres au *genre*, complètent les défis signature élaborés pour certains titres.
- **Trophées RetroAchievements** : historiques de succès obtenus via l'API RA et affichés séparément après import. Les succès d'une autre plateforme (Steam, PlayStation, etc.) n'ont pas été importés.
- **Platine IKARIAN** : calculé sur les déclarations personnelles, non sur une preuve cryptographique ou de l'émulateur.
- **Mode hors ligne** : cache des ressources après un premier chargement valide, et progression enregistrée localement dans le navigateur. Exporter une sauvegarde avant toute suppression de données de navigation.
- **Aucune émulation ni installation de jeu** n'est réalisée par le tableau de bord.
- **Aucune connexion automatique RA** n'est déclenchée par un navigateur : la clé API reste sur le PC utilisateur.

## Validation

```bash
python -m unittest discover -s ikarian/tests -v
node --check docs/ikarian/app.js
```

Le workflow GitHub Actions `ikarian.yml` effectue ces contrôles lors des mises à jour. Il vérifie notamment les 899 identifiants uniques, les métadonnées originales, les trophées, les rangs et la provenance déclarative.

## Prochaine couche technique

1. Faire correspondre les jeux du catalogue aux identifiants RA à partir de **hashs de ROM et de métadonnées vérifiées**, et non uniquement de chaînes de titres.
2. Établir des définitions détectables par émulateur / core pour les jeux non couverts par RetroAchievements ; aucun succès ne sera qualifié de « vérifié » avant tests.
3. Créer un **compagnon Android natif** pour les notifications en jeu quand les événements sont disponibles, avec permission de superposition explicitement accordée.
4. Étoffer et vérifier éditorialement les trophées propres à chaque titre, puis intégrer des cartes d'artwork et des animations spécifiques.
5. Mettre en place une synchronisation multi-appareils chiffrée et privée, facultative.
