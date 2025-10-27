#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Outil CLI : conversion de fichiers .plist (XML ou binaire) en JSON.
Usage : plist2json.py [-h] [-o OUTPUT] [--indent INDENT] input.plist

L'outil lit le fichier .plist, le convertit en JSON et écrit la sortie soit dans un fichier (si -o est fourni), soit sur stdout.
Gère les erreurs de fichier manquant ou format invalide.
"""

import argparse
import sys
import os
import plistlib
import json
from datetime import datetime
import base64
from typing import Iterable, List, Optional, Tuple

from tqdm import tqdm

# import mmap  # Optionnel : pour les très gros fichiers


def parse_args():
    """Configure et parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Convertisseur de fichiers .plist (macOS) en JSON lisible."
    )
    parser.add_argument(
        "plist_file", metavar="PLIST", help="Chemin du fichier .plist à convertir"
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUT",
        help="Fichier de sortie JSON (par défaut stdout)",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        help="Répertoire de sortie quand l'entrée est un dossier (par défaut à côté des fichiers .plist)",
        default=None,
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Niveau d'indentation pour le JSON (par défaut 2)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Parcourt récursivement les sous-dossiers lors de la conversion d'un dossier",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Désactive l'affichage de la barre de progression",
    )
    return parser.parse_args()


def iter_plist_files(directory: str, recursive: bool) -> List[str]:
    """Retourne la liste des fichiers .plist dans un dossier."""
    plist_files: List[str] = []
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".plist"):
                    plist_files.append(os.path.join(root, file))
    else:
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.lower().endswith(".plist"):
                plist_files.append(entry.path)
    return sorted(plist_files)


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def compute_output_path(
    plist_path: str, base_input_dir: str, output_dir: Optional[str]
) -> str:
    """Calcule le chemin du fichier JSON de sortie pour un plist donné."""
    directory = output_dir if output_dir else os.path.dirname(plist_path)
    if base_input_dir:
        rel_path = os.path.relpath(plist_path, base_input_dir)
    else:
        rel_path = os.path.basename(plist_path)

    stem, _ = os.path.splitext(rel_path)
    json_rel_path = f"{stem}.json"
    output_path = os.path.join(directory, json_rel_path)
    ensure_directory(os.path.dirname(output_path))
    return output_path


def convert_single_plist_to_json(
    plist_path: str,
    output_path: Optional[str],
    indent: int,
    stream_output: bool = False,
) -> Tuple[str, bool, Optional[str]]:
    """
    Convertit un fichier plist et le sérialise en JSON.

    Retourne (chemin_plist, succès, erreur éventuelle).
    Si stream_output est True, écrit sur stdout.
    """
    try:
        with open(plist_path, "rb") as fp:
            plist_data = plistlib.load(fp)
    except plistlib.InvalidFileException:
        return plist_path, False, "fichier .plist invalide ou corrompu"
    except FileNotFoundError:
        return plist_path, False, "fichier introuvable"
    except Exception as e:  # pragma: no cover - garde générique pour robustesse
        return plist_path, False, f"erreur de lecture : {e}"

    try:
        if stream_output or not output_path:
            json.dump(
                plist_data,
                sys.stdout,
                ensure_ascii=False,
                indent=indent,
                default=convert_to_json_serializable,
            )
            sys.stdout.write("\n")
        else:
            ensure_directory(os.path.dirname(output_path))
            with open(output_path, "w", encoding="utf-8") as out_fp:
                json.dump(
                    plist_data,
                    out_fp,
                    ensure_ascii=False,
                    indent=indent,
                    default=convert_to_json_serializable,
                )
        return plist_path, True, None
    except Exception as e:  # pragma: no cover - garder message clair
        return plist_path, False, f"erreur de conversion JSON : {e}"


def convert_to_json_serializable(obj):
    """
    Convertit en types JSON-serialisables les types spécifiques de plistlib :
    datetime -> ISO 8601 (chaine), bytes -> chaîne base64.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (bytes, bytearray)):
        # Encode en base64 pour conserver le contenu binaire
        return base64.b64encode(obj).decode("ascii")
    # Autres types non pris en charge → TypeError (json.dump lèvera une erreur)
    raise TypeError(f"Type non sérialisable en JSON : {type(obj)}")


def main():
    args = parse_args()
    plist_path = args.plist_file

    # Vérification de l'existence du fichier .plist
    if not os.path.exists(plist_path):
        print(f"Erreur : chemin introuvable : {plist_path}", file=sys.stderr)
        sys.exit(1)

    if os.path.isdir(plist_path):
        plist_files = iter_plist_files(plist_path, args.recursive)
        if not plist_files:
            print(
                "Aucun fichier .plist trouvé dans le dossier spécifié.",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.output and not args.output_dir:
            print(
                "Option -o/--output réservée aux conversions d'un seul fichier.\n"
                "Utilisez --output-dir pour choisir un dossier de sortie.",
                file=sys.stderr,
            )
            sys.exit(2)

        base_dir = os.path.abspath(plist_path)
        output_dir = args.output_dir
        if output_dir:
            output_dir = os.path.abspath(output_dir)

        total = len(plist_files)
        print(
            f"Conversion de {total} fichier{'s' if total > 1 else ''} .plist depuis "
            f"{plist_path}"
        )

        results: List[Tuple[str, bool, Optional[str]]] = []
        progress_iter: Iterable[str] = plist_files
        if not args.no_progress and total > 1:
            progress_iter = tqdm(
                plist_files,
                desc="Progression",
                unit="fichier",
                total=total,
                ncols=80,
            )

        for plist_file in progress_iter:
            output_path = compute_output_path(plist_file, base_dir, output_dir)
            result = convert_single_plist_to_json(
                plist_file,
                output_path,
                args.indent,
                stream_output=False,
            )
            results.append((plist_file, result[1], result[2]))

        success_count = sum(1 for _, ok, _ in results if ok)
        failure_details = [(path, err) for path, ok, err in results if not ok]

        print(
            f"✅ Conversion terminée : {success_count}/{total} fichier"
            f"{'s' if total > 1 else ''} converti{'s' if success_count > 1 else ''}."
        )
        if failure_details:
            print("❌ Fichiers en erreur :", file=sys.stderr)
            for path, err in failure_details:
                print(f"  - {path} : {err}", file=sys.stderr)
            sys.exit(3)
        sys.exit(0)

    # Chemin fichier unique
    if os.path.isdir(args.output or ""):
        print(
            "Erreur : utilisez -o/--output avec un chemin de fichier, pas un dossier.",
            file=sys.stderr,
        )
        sys.exit(2)

    plist_path = os.path.abspath(plist_path)
    output_path = os.path.abspath(args.output) if args.output else None
    _, success, error = convert_single_plist_to_json(
        plist_path,
        output_path,
        args.indent,
        stream_output=output_path is None,
    )
    if success:
        if output_path:
            print(f"✅ Fichier converti : {plist_path} → {output_path}")
        sys.exit(0)
    else:
        print(f"Erreur : {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
