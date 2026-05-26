import numpy as np
import json
import pygame
import os
import sys

try:
    import vispy
    vispy.use('PyQt6')
except Exception:
    pass

from vispy import app, scene
from tkinter import filedialog, Tk
import matplotlib.colors as mcolors
from scipy.spatial import cKDTree

# --- Initialisation Audio ---
pygame.mixer.init()

def get_paths():
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    c_p = filedialog.askopenfilename(title="Charger XYZ_RGB")
    j_p = filedialog.askopenfilename(title="Charger JSON")
    root.destroy()
    return c_p, j_p

cloud_file, json_file = get_paths()
if not cloud_file or not json_file: sys.exit()

# --- Chargement des données ---
with open(json_file, 'r', encoding='utf-8') as f:
    raw_config = json.load(f)
    config_audio = [e for e in raw_config if e.get("song_path")]

data = np.loadtxt(cloud_file)
pos = data[:, :3]

# Détection automatique de l'orientation (X/Y ou X/Z)
x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
if (np.max(y) - np.min(y)) < (np.max(z) - np.min(z)):
    coords_2d = np.column_stack((x, z))
else:
    coords_2d = np.column_stack((x, y))

# --- Préparation des couleurs avec effet "Peinture" ---
base_colors = data[:, 3:6] / 255.0
hsv_values = mcolors.rgb_to_hsv(base_colors)

# Ajout d'une couche Alpha (transparence) pour que les points se mélangent
rgba_colors = np.ones((base_colors.shape[0], 4), dtype=np.float32)
rgba_colors[:, :3] = base_colors
rgba_colors[:, 3] = 0.5  # 50% d'opacité pour créer du flou et de la densité

tree = cKDTree(coords_2d)

sounds = {}
for entry in config_audio:
    p = entry["song_path"]
    if os.path.exists(p):
        sounds[p] = pygame.mixer.Sound(p)

# --- Interface Graphique ---
canvas = scene.SceneCanvas(keys='interactive', show=True, title="Rendu Peinture Fusionnée", bgcolor='black')
view = canvas.central_widget.add_view()
view.camera = scene.PanZoomCamera(aspect=1)

# Création du visuel avec mélange de couleurs activé (Blending)
scatter = scene.visuals.Markers()
scatter.set_gl_state('translucent', blend=True, depth_test=False)

scatter.set_data(
    coords_2d, 
    edge_width=0, 
    face_color=rgba_colors, 
    size=1.0,        # On réduit la taille pour éviter l'effet "grosses bulles"
    symbol='disc'    # Le disque reste le plus naturel s'il est petit
)
view.add(scatter)

view.camera.set_range(x=(np.min(coords_2d[:,0]), np.max(coords_2d[:,0])), 
                      y=(np.min(coords_2d[:,1]), np.max(coords_2d[:,1])))

# --- Logique Sonore ---
current_path = None

def play_audio(idx):
    global current_path
    if idx == -1:
        if current_path:
            sounds[current_path].fadeout(400)
            current_path = None
        return

    h, s, v = hsv_values[idx]
    h_val, s_val, v_val = h * 360, s * 100, v * 100
    
    found_path = None
    for entry in config_audio:
        if (min(entry["h_range"]) <= h_val <= max(entry["h_range"]) and
            min(entry["s_range"]) <= s_val <= max(entry["s_range"]) and
            min(entry["v_range"]) <= v_val <= max(entry["v_range"])):
            found_path = entry["song_path"]
            break

    if found_path != current_path:
        if current_path in sounds: sounds[current_path].fadeout(400)
        if found_path in sounds: 
            sounds[found_path].play(loops=-1)
            print(f"LECTURE : {os.path.basename(found_path)} | H:{h_val:.0f}")
        current_path = found_path

@canvas.events.mouse_move.connect
def on_mouse_move(event):
    tr = canvas.scene.node_transform(scatter)
    pos_map = tr.map(event.pos)
    dist, idx = tree.query(pos_map[:2], k=1)
    
    # Seuil de détection adapté
    if dist < 0.4:
        play_audio(idx)
    else:
        play_audio(-1)

if __name__ == '__main__':
    app.run()
    pygame.mixer.quit()