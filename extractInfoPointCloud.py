"""
extractInfoPointCloud.py
========================
Analyse un nuage de points XYZ RGB en streaming + génère des graphiques :
  - Histogrammes RGB
  - Couleur moyenne (carré)
  - Distribution Z (profil de hauteur)
  - Carte de densité XY (heatmap)

Dépendances :
    pip install matplotlib numpy

Usage :
    python extractInfoPointCloud.py fichier.xyz_rgb --skip 1
    python extractInfoPointCloud.py fichier.xyz_rgb --skip 1 --output rapport.json
    python extractInfoPointCloud.py fichier.xyz_rgb --skip 1 --no_graphs
    python extractInfoPointCloud.py fichier.xyz_rgb --skip 1 --export_csv extrait.csv --zmin 10 --zmax 50
"""

import argparse
import json
import sys
import csv
import math
from pathlib import Path

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False
    print("[WARN] matplotlib/numpy non installés — graphiques désactivés.")
    print("       pip install matplotlib numpy\n")


# ──────────────────────────────────────────────────────────────────────────────
# Détection séparateur
# ──────────────────────────────────────────────────────────────────────────────

def detect_separator(path: Path, skip: int) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i < skip:
                continue
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," in line:  return ","
            if "\t" in line: return "\t"
            if ";" in line:  return ";"
            return None
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Welford accumulator (mean + std sans stocker les valeurs)
# ──────────────────────────────────────────────────────────────────────────────

class WelfordStat:
    def __init__(self):
        self.n    = 0
        self.mean = 0.0
        self.M2   = 0.0
        self.mn   = float("inf")
        self.mx   = float("-inf")

    def update(self, x):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.M2   += delta * (x - self.mean)
        if x < self.mn: self.mn = x
        if x > self.mx: self.mx = x

    def result(self):
        if self.n == 0:
            return {}
        std = math.sqrt(self.M2 / self.n) if self.n > 1 else 0.0
        return {
            "min"  : round(self.mn,   4),
            "max"  : round(self.mx,   4),
            "mean" : round(self.mean, 4),
            "std"  : round(std,       4),
            "range": round(self.mx - self.mn, 4),
        }


# ──────────────────────────────────────────────────────────────────────────────
# Streaming : une seule passe, aucune liste de points en RAM
# ──────────────────────────────────────────────────────────────────────────────

HEATMAP_RES = 512

def stream_analyze(path: Path, sep: str, skip: int,
                   export_csv=None,
                   zmin=None, zmax=None,
                   rmin=None, rmax=None,
                   gmin=None, gmax=None,
                   bmin=None, bmax=None):

    sx, sy, sz = WelfordStat(), WelfordStat(), WelfordStat()
    sr, sg, sb = WelfordStat(), WelfordStat(), WelfordStat()

    # Histogrammes RGB exacts (256 bins)
    hist_r = [0] * 256
    hist_g = [0] * 256
    hist_b = [0] * 256

    # Sous-échantillons légers pour les graphiques
    SAMPLE_Z  = 100   # 1 point / 100 pour histogramme Z
    SAMPLE_XY = 50    # 1 point / 50  pour heatmap XY
    z_sample  = []
    xy_x      = []
    xy_y      = []

    total     = 0
    errors    = 0
    has_rgb   = False
    has_int   = False
    col_count = None

    csv_file   = None
    csv_writer = None
    exported   = 0

    if export_csv:
        csv_file = open(export_csv, "w", newline="", encoding="utf-8")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < skip:
                    continue
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(sep) if sep else line.split()
                try:
                    vals = [float(p) for p in parts]
                except ValueError:
                    errors += 1
                    continue

                n = len(vals)
                if col_count is None:
                    col_count = n
                    has_rgb   = n >= 6
                    has_int   = n >= 7
                    if export_csv:
                        headers = ["x", "y", "z"]
                        if has_rgb: headers += ["r", "g", "b"]
                        if has_int: headers += ["intensity"]
                        csv_writer = csv.writer(csv_file)
                        csv_writer.writerow(headers)

                x, y, z = vals[0], vals[1], vals[2]
                r = int(min(max(vals[3], 0), 255)) if has_rgb else None
                g = int(min(max(vals[4], 0), 255)) if has_rgb else None
                b = int(min(max(vals[5], 0), 255)) if has_rgb else None
                intensity = vals[6] if has_int else None

                # Stats
                sx.update(x); sy.update(y); sz.update(z)
                if has_rgb:
                    sr.update(r); sg.update(g); sb.update(b)
                    hist_r[r] += 1
                    hist_g[g] += 1
                    hist_b[b] += 1

                # Sous-échantillons
                if total % SAMPLE_Z  == 0: z_sample.append(z)
                if total % SAMPLE_XY == 0:
                    xy_x.append(x)
                    xy_y.append(y)

                total += 1
                if total % 1_000_000 == 0:
                    print(f"  … {total:,} points traités", flush=True)

                # Export CSV filtré
                if csv_writer:
                    if zmin is not None and z < zmin: continue
                    if zmax is not None and z > zmax: continue
                    if has_rgb:
                        if rmin is not None and r < rmin: continue
                        if rmax is not None and r > rmax: continue
                        if gmin is not None and g < gmin: continue
                        if gmax is not None and g > gmax: continue
                        if bmin is not None and b < bmin: continue
                        if bmax is not None and b > bmax: continue
                    row = [x, y, z]
                    if has_rgb: row += [r, g, b]
                    if has_int: row += [intensity]
                    csv_writer.writerow(row)
                    exported += 1

    finally:
        if csv_file:
            csv_file.close()

    # Rapport JSON
    report = {
        "source_file"     : str(path),
        "file_size_mb"    : round(path.stat().st_size / 1024 / 1024, 2),
        "total_points"    : total,
        "columns_detected": col_count,
        "skipped_lines"   : errors,
        "has_rgb"         : has_rgb,
        "has_intensity"   : has_int,
        "bbox": {
            "x": sx.result(),
            "y": sy.result(),
            "z": sz.result(),
        },
    }
    dx = sx.result().get("range", 0)
    dy = sy.result().get("range", 0)
    if dx > 0 and dy > 0:
        report["approx_density_pts_per_m2"] = round(total / (dx * dy), 4)

    if has_rgb:
        report["rgb_stats"] = {
            "R": sr.result(), "G": sg.result(), "B": sb.result(),
        }
        report["mean_color_rgb"] = [round(sr.mean), round(sg.mean), round(sb.mean)]

    if export_csv:
        report["exported_points"] = exported

    graph_data = {
        "hist_r": hist_r, "hist_g": hist_g, "hist_b": hist_b,
        "z_sample": z_sample,
        "xy_x": xy_x, "xy_y": xy_y,
        "has_rgb" : has_rgb,
        "mean_color": [round(sr.mean), round(sg.mean), round(sb.mean)] if has_rgb else None,
        "z_stat": sz.result(),
    }

    return report, graph_data


# ──────────────────────────────────────────────────────────────────────────────
# Graphiques
# ──────────────────────────────────────────────────────────────────────────────

def generate_graphs(graph_data: dict, out_dir: Path, stem: str):
    if not HAS_PLOT:
        return []

    import numpy as np
    saved = []

    # ── 1. Histogrammes RGB ───────────────────────────────────────────────────
    if graph_data["has_rgb"]:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle("Histogrammes RGB", fontsize=14, fontweight="bold")

        channels = [
            ("R", graph_data["hist_r"], "crimson"),
            ("G", graph_data["hist_g"], "forestgreen"),
            ("B", graph_data["hist_b"], "royalblue"),
        ]
        for ax, (label, hist, color) in zip(axes, channels):
            ax.bar(range(256), hist, color=color, alpha=0.85, width=1.0)
            mean_val = sum(v * h for v, h in enumerate(hist)) / max(sum(hist), 1)
            ax.axvline(mean_val, color="white", linestyle="--", linewidth=1.5,
                       label=f"moy = {mean_val:.1f}")
            ax.set_title(f"Canal {label}", fontweight="bold")
            ax.set_xlabel("Valeur (0–255)")
            ax.set_ylabel("Nombre de points")
            ax.set_xlim(0, 255)
            ax.grid(axis="y", alpha=0.3)
            ax.legend(fontsize=9)

        plt.tight_layout()
        p = out_dir / f"{stem}_01_histogrammes_rgb.png"
        plt.savefig(p, dpi=150, bbox_inches="tight")
        plt.close()
        saved.append(p)
        print(f"[OK] {p.name}")

        # Couleur moyenne
        mc = graph_data["mean_color"]
        fig2, ax2 = plt.subplots(figsize=(3, 2))
        ax2.set_facecolor([c / 255 for c in mc])
        ax2.set_title(f"Couleur moyenne\nRGB({mc[0]}, {mc[1]}, {mc[2]})",
                      fontsize=10, fontweight="bold", color="white")
        ax2.axis("off")
        p2 = out_dir / f"{stem}_02_couleur_moyenne.png"
        plt.savefig(p2, dpi=150, bbox_inches="tight", facecolor=[c/255 for c in mc])
        plt.close()
        saved.append(p2)
        print(f"[OK] {p2.name}")

    # ── 2. Distribution Z ─────────────────────────────────────────────────────
    z_sample = graph_data["z_sample"]
    if z_sample:
        zs = np.array(z_sample)
        fig, ax = plt.subplots(figsize=(10, 5))
        n_bins = 100
        counts, bin_edges, patches = ax.hist(zs, bins=n_bins, edgecolor="none", alpha=0.9)

        # Dégradé de couleur par hauteur
        norm = mcolors.Normalize(vmin=bin_edges[0], vmax=bin_edges[-1])
        cmap = plt.cm.viridis
        for patch, left in zip(patches, bin_edges[:-1]):
            patch.set_facecolor(cmap(norm(left)))

        zstat = graph_data["z_stat"]
        ax.axvline(zstat["mean"], color="red", linestyle="--", linewidth=1.5,
                   label=f"moy = {zstat['mean']:.3f} m")
        ax.axvline(zstat["min"], color="cyan", linestyle=":", linewidth=1,
                   label=f"min = {zstat['min']:.3f} m")
        ax.axvline(zstat["max"], color="orange", linestyle=":", linewidth=1,
                   label=f"max = {zstat['max']:.3f} m")

        ax.set_title("Distribution Z — Profil de hauteur", fontsize=13, fontweight="bold")
        ax.set_xlabel("Z (m)")
        ax.set_ylabel("Nombre de points (échantillon 1/%d)" % 100)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ax=ax, label="Hauteur Z (m)", fraction=0.03, pad=0.02)

        plt.tight_layout()
        p = out_dir / f"{stem}_03_distribution_z.png"
        plt.savefig(p, dpi=150, bbox_inches="tight")
        plt.close()
        saved.append(p)
        print(f"[OK] {p.name}")

    # ── 3. Heatmap densité XY ─────────────────────────────────────────────────
    xy_x = graph_data["xy_x"]
    xy_y = graph_data["xy_y"]
    if xy_x and xy_y:
        xs = np.array(xy_x)
        ys = np.array(xy_y)

        heatmap, xedges, yedges = np.histogram2d(xs, ys, bins=HEATMAP_RES)
        heatmap_log = np.log1p(heatmap.T)

        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(
            heatmap_log,
            origin="lower",
            extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
            cmap="inferno",
            aspect="equal",
        )
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("log(1 + nb points)", rotation=270, labelpad=15)
        ax.set_title("Carte de densité XY (heatmap)", fontsize=13, fontweight="bold")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")

        plt.tight_layout()
        p = out_dir / f"{stem}_04_heatmap_xy.png"
        plt.savefig(p, dpi=150, bbox_inches="tight")
        plt.close()
        saved.append(p)
        print(f"[OK] {p.name}")

    return saved


# ──────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyser un nuage de points XYZ RGB + graphiques"
    )
    parser.add_argument("fichier",       help="Chemin vers le fichier")
    parser.add_argument("--sep",         help="Séparateur (défaut : auto)", default=None)
    parser.add_argument("--skip",        help="Lignes d'en-tête à ignorer", type=int, default=1)
    parser.add_argument("--output",      help="Rapport JSON", metavar="rapport.json")
    parser.add_argument("--export_csv",  help="Exporter points filtrés",    metavar="filtre.csv")
    parser.add_argument("--no_graphs",   help="Désactiver les graphiques",  action="store_true")
    parser.add_argument("--graphs_dir",  help="Dossier pour les graphiques (défaut : dossier du fichier)",
                        default=None)
    parser.add_argument("--zmin",  type=float)
    parser.add_argument("--zmax",  type=float)
    parser.add_argument("--rmin",  type=int)
    parser.add_argument("--rmax",  type=int)
    parser.add_argument("--gmin",  type=int)
    parser.add_argument("--gmax",  type=int)
    parser.add_argument("--bmin",  type=int)
    parser.add_argument("--bmax",  type=int)
    args = parser.parse_args()

    path = Path(args.fichier)
    if not path.exists():
        print(f"[ERREUR] Fichier introuvable : {path}", file=sys.stderr)
        sys.exit(1)

    sep = args.sep
    if sep is None:
        sep = detect_separator(path, args.skip)
        print(f"[INFO] Séparateur : {repr(sep) if sep else 'espace(s)'}")

    print(f"[INFO] Analyse de {path.name} ({path.stat().st_size/1024/1024:.1f} Mo) …\n")

    report, graph_data = stream_analyze(
        path, sep, args.skip,
        export_csv=args.export_csv,
        zmin=args.zmin, zmax=args.zmax,
        rmin=args.rmin, rmax=args.rmax,
        gmin=args.gmin, gmax=args.gmax,
        bmin=args.bmin, bmax=args.bmax,
    )

    output_json = json.dumps(report, indent=2, ensure_ascii=False)
    print("\n" + output_json)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"\n[OK] Rapport JSON → {args.output}")

    if args.export_csv:
        print(f"[OK] {report.get('exported_points', 0):,} points exportés → {args.export_csv}")

    if not args.no_graphs:
        out_dir = Path(args.graphs_dir) if args.graphs_dir else path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[INFO] Génération des graphiques dans : {out_dir}\n")
        saved = generate_graphs(graph_data, out_dir, path.stem)
        if saved:
            print(f"\n{len(saved)} graphique(s) sauvegardé(s) :")
            for s in saved:
                print(f"  {s}")


if __name__ == "__main__":
    main()
