import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from sklearn.cluster import KMeans
from tkinter import filedialog, Tk
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
import os
import json

def load_point_cloud():
    root = Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Ouvrir le nuage de points (.xyz_rgb)",
        filetypes=[("Fichiers points", "*.xyz_rgb *.txt *.xyz"), ("Tous", "*.*")]
    )
    root.destroy()
    return path

# --- 1. Chargement et Préparation ---
file_path = load_point_cloud()
if not file_path:
    print("Aucun fichier sélectionné.")
    exit()

print(f"Chargement de {os.path.basename(file_path)}...")
try:
    # On charge XYZ (0,1,2) et RGB (3,4,5)
    full_data = np.loadtxt(file_path)
    xyz_all = full_data[:, :3]
    rgb_all = full_data[:, 3:]
except Exception as e:
    print(f"Erreur de lecture : {e}")
    exit()

# Échantillonnage pour la performance interactive (20k points)
MAX_POINTS = 20000
indices = np.random.choice(len(full_data), min(len(full_data), MAX_POINTS), replace=False)
points_xyz = xyz_all[indices]
points_rgb = rgb_all[indices] / 255.0

# Variables globales pour le stockage
last_clusters_data = []
last_labels = None
last_palette = None

# --- 2. Fonctions de calcul et d'UI ---

def update(val):
    global last_clusters_data, last_labels, last_palette
    k = int(slider_k.val)
    
    # Clustering K-Means
    model = KMeans(n_clusters=k, init='k-means++', n_init=5, random_state=42)
    last_labels = model.fit_predict(points_rgb)
    raw_centers = model.cluster_centers_
    
    # Tri de la palette par Teinte (H) pour la stabilité visuelle
    hsv_centers = mcolors.rgb_to_hsv(raw_centers)
    sorted_indices = np.argsort(hsv_centers[:, 0])
    last_palette = raw_centers[sorted_indices]
    
    # Mise à jour de l'affichage palette
    ax_palette.clear()
    ax_palette.imshow([last_palette], aspect='auto')
    ax_palette.set_title(f"Palette Dominante : {k} couleurs (triées par teinte)")
    ax_palette.set_axis_off()
    
    # Préparation des données JSON et Plages HSV
    current_export = []
    for idx, real_idx in enumerate(sorted_indices):
        cluster_mask = (last_labels == real_idx)
        cluster_pts = points_rgb[cluster_mask]
        
        if len(cluster_pts) > 0:
            hsv_data = mcolors.rgb_to_hsv(cluster_pts)
            h_min, s_min, v_min = np.min(hsv_data, axis=0)
            h_max, s_max, v_max = np.max(hsv_data, axis=0)
            
            # Structure du JSON identique à ton besoin
            current_export.append({
                "h_range": [round(float(h_min) * 360), round(float(h_max) * 360)],
                "s_range": [round(float(s_min) * 100), round(float(s_max) * 100)],
                "v_range": [round(float(v_min) * 100), round(float(v_max) * 100)],
                "song_path": ""  # Laissé vide pour l'App d'édition
            })
    
    last_clusters_data = current_export
    fig.canvas.draw_idle()

def save_json_file(event):
    """ Ouvre une boîte de dialogue pour enregistrer le fichier JSON """
    if last_clusters_data:
        root = Tk()
        root.withdraw()
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="analyse_couleurs.json",
            title="Enregistrer la configuration JSON"
        )
        root.destroy()
        
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(last_clusters_data, f, indent=4, ensure_ascii=False)
            print(f"Fichier sauvegardé : {save_path}")

def show_debug_3d(event):
    """ Ouvre une fenêtre 3D pour voir la segmentation spatiale """
    if last_labels is None: return
    
    debug_fig = plt.figure(figsize=(10, 8))
    ax3d = debug_fig.add_subplot(111, projection='3d')
    
    # Affichage d'un point sur deux pour la fluidité en 3D
    ax3d.scatter(points_xyz[::2, 0], points_xyz[::2, 1], points_xyz[::2, 2], 
                 c=points_rgb[::2], s=2)
    
    ax3d.set_title("Nuage Original (Vérification des zones)")
    plt.show()

# --- 3. Configuration de l'interface ---
fig, (ax_raw, ax_palette) = plt.subplots(2, 1, figsize=(12, 8))
plt.subplots_adjust(bottom=0.25, hspace=0.4)

ax_raw.set_title("1. Aperçu des couleurs présentes (Input)")
ax_raw.imshow([points_rgb[:1000]], aspect='auto')
ax_raw.get_yaxis().set_visible(False)

# Widgets (Slider et Boutons)
ax_slider = plt.axes([0.15, 0.1, 0.50, 0.03])
slider_k = Slider(ax_slider, 'K clusters', 1, 30, valinit=8, valfmt='%d')

ax_btn_debug = plt.axes([0.70, 0.09, 0.12, 0.05])
btn_debug = Button(ax_btn_debug, 'Debug 3D', color='aliceblue')

ax_btn_json = plt.axes([0.83, 0.09, 0.14, 0.05])
btn_json = Button(ax_btn_json, 'Générer JSON', color='honeydew')

# Connexions des événements
slider_k.on_changed(update)
btn_debug.on_clicked(show_debug_3d)
btn_json.on_clicked(save_json_file)

# Lancement initial
update(8)
plt.show()
