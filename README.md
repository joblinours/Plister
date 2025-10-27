# plister

Convertisseur CLI de fichiers macOS `.plist` (XML ou binaire) vers JSON lisible.

## Fonctionnalités

- Conversion d'un fichier `.plist` unique vers JSON (stdout ou fichier).
- Traitement d'un dossier complet, avec conservation de la structure et export `.json` correspondant.
- Option de parcours récursif des sous-dossiers.
- Barre de progression (désactivable) et messages conviviaux.
- Gestion des types spécifiques (`datetime`, données binaires) pour produire un JSON valide.

## Installation rapide

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Utilisation

Afficher l'aide :

```bash
python plister.py --help
```

Conversion d'un fichier unique vers stdout :

```bash
python plister.py exemple.plist
```

Conversion d'un fichier vers un fichier JSON :

```bash
python plister.py exemple.plist -o sortie.json
```

Conversion d'un dossier (non récursive) vers un dossier de sortie :

```bash
python plister.py /chemin/vers/dossier --output-dir ./json
```

Conversion récursive avec barre de progression :

```bash
python plister.py /chemin/vers/dossier --recursive --output-dir ./json
```

Désactiver la barre de progression (utile pour les scripts CI) :

```bash
python plister.py /chemin/vers/dossier --output-dir ./json --no-progress
```

## Notes

- Sans `--output-dir`, les JSON sont créés à côté des fichiers `.plist` d'origine.
- En mode dossier, l'option `-o/--output` n'est pas autorisée ; utilisez `--output-dir`.
- Les fichiers binaires sont encodés en Base64 et les dates sont converties au format ISO 8601.
