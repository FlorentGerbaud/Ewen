#!/usr/bin/env python3
"""
Convertisseur PLY → XYZ_RGB
Usage: python ply_to_xyz_rgb.py input.ply [output.xyz]
Format de sortie : X Y Z R G B (une ligne par point)
"""

import sys
import argparse
from pathlib import Path

try:
    from plyfile import PlyData
except ImportError:
    print("Erreur : installez plyfile avec  pip install plyfile")
    sys.exit(1)


def ply_to_xyz_rgb(input_path: str, output_path: str | None = None) -> str:
    """
    Convertit un fichier PLY en fichier XYZ_RGB.

    Args:
        input_path : chemin vers le fichier .ply source
        output_path : chemin de sortie (optionnel, auto-généré si absent)

    Returns:
        Chemin du fichier généré.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {input_path}")

    # Chemin de sortie par défaut
    if output_path is None:
        output_path = input_path.with_suffix(".xyz")
    output_path = Path(output_path)

    print(f"Lecture de {input_path} ...")
    ply_data = PlyData.read(str(input_path))

    # Récupère l'élément 'vertex'
    if "vertex" not in [el.name for el in ply_data.elements]:
        raise ValueError("Le fichier PLY ne contient pas d'élément 'vertex'.")

    vertex = ply_data["vertex"]
    props = vertex.data.dtype.names

    # --- Coordonnées XYZ ---
    for axis in ("x", "y", "z"):
        if axis not in props:
            raise ValueError(f"Propriété manquante dans le PLY : '{axis}'")

    # --- Couleurs RGB (plusieurs nommages possibles) ---
    rgb_candidates = [
        ("red", "green", "blue"),
        ("r", "g", "b"),
        ("diffuse_red", "diffuse_green", "diffuse_blue"),
    ]
    color_fields = None
    for candidate in rgb_candidates:
        if all(c in props for c in candidate):
            color_fields = candidate
            break

    has_color = color_fields is not None
    if not has_color:
        print("⚠  Aucune couleur RGB trouvée — R G B sera mis à 0 0 0.")

    total = len(vertex.data)
    print(f"Points trouvés : {total:,}")
    if has_color:
        print(f"Canaux couleur  : {color_fields}")

    print(f"Écriture vers {output_path} ...")
    with open(output_path, "w") as f:
        for i, v in enumerate(vertex.data):
            x, y, z = float(v["x"]), float(v["y"]), float(v["z"])

            if has_color:
                r = int(v[color_fields[0]])
                g = int(v[color_fields[1]])
                b = int(v[color_fields[2]])
            else:
                r = g = b = 0

            f.write(f"{x} {y} {z} {r} {g} {b}\n")

            # Progression tous les 10 %
            if total >= 10 and (i + 1) % (total // 10) == 0:
                pct = (i + 1) * 100 // total
                print(f"  {pct}% ({i+1:,}/{total:,} points)", end="\r")

    print(f"\n✅ Conversion terminée : {output_path}  ({total:,} points)")
    return str(output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convertit un nuage de points PLY en fichier XYZ_RGB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Format de sortie :
  X Y Z R G B    (séparés par des espaces, un point par ligne)
  X, Y, Z  : coordonnées flottantes
  R, G, B  : entiers 0-255

Exemples :
  python ply_to_xyz_rgb.py nuage.ply
  python ply_to_xyz_rgb.py nuage.ply sortie.xyz
  python ply_to_xyz_rgb.py nuage.ply /tmp/export.xyz
        """,
    )
    parser.add_argument("input", help="Fichier PLY source")
    parser.add_argument("output", nargs="?", help="Fichier XYZ de sortie (optionnel)")
    args = parser.parse_args()

    try:
        ply_to_xyz_rgb(args.input, args.output)
    except (FileNotFoundError, ValueError) as e:
        print(f"Erreur : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
