import tkinter as tk
from tkinter import ttk

def rgb_to_hex(rgb):
    """Convertit un tuple (R, G, B) en format hexadécimal #RRGGBB"""
    return "#%02x%02x%02x" % rgb

def hsv_to_rgb(h, s, v):
    """Convertit HSV (0-1) en RGB (0-255)"""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))

def update_color(event=None):
    # On récupère les valeurs des curseurs
    s = scale_sat.get() / 100
    v = scale_val.get() / 100
    h = 0  # Fixé sur le rouge pur
    
    # Calcul de la couleur principale
    current_rgb = hsv_to_rgb(h, s, v)
    hex_color = rgb_to_hex(current_rgb)
    
    # Mise à jour de l'affichage
    color_display.config(bg=hex_color)
    label_rgb.config(text=f"RGB: {current_rgb} | HEX: {hex_color.upper()}")
    
    # Génération d'une mini-palette de nuances basée sur ce réglage
    for i in range(5):
        # On crée des variantes de luminosité autour de la sélection
        variant_v = max(0, min(1, (v - 0.2) + (i * 0.1)))
        variant_rgb = hsv_to_rgb(h, s, variant_v)
        pal_boxes[i].config(bg=rgb_to_hex(variant_rgb))

# --- Fenêtre Principale ---
root = tk.Tk()
root.title("Sélecteur de Rouges (Vif à Terne)")
root.geometry("400x500")

# 1. Zone d'affichage de la couleur
color_display = tk.Frame(root, height=150, width=300, relief="ridge", borderwidth=5)
color_display.pack(pady=20)

label_rgb = tk.Label(root, text="RGB: (255, 0, 0)", font=("Courier", 12))
label_rgb.pack()

# 2. Curseur Saturation (Vif -> Moins vif)
tk.Label(root, text="Intensité (Saturation) :", font=("Arial", 10, "bold")).pack(pady=(10, 0))
scale_sat = tk.Scale(root, from_=0, to=100, orient="horizontal", length=300, command=update_color)
scale_sat.set(100) # Par défaut : très vif
scale_sat.pack()

# 3. Curseur Luminosité (Sombre -> Clair)
tk.Label(root, text="Luminosité :", font=("Arial", 10, "bold")).pack(pady=(10, 0))
scale_val = tk.Scale(root, from_=0, to=100, orient="horizontal", length=300, command=update_color)
scale_val.set(100)
scale_val.pack()

# 4. Mini-palette générée automatiquement
tk.Label(root, text="Nuances suggérées :", font=("Arial", 10)).pack(pady=(20, 5))
pal_frame = tk.Frame(root)
pal_frame.pack()
pal_boxes = []
for _ in range(5):
    box = tk.Frame(pal_frame, width=50, height=50, relief="flat")
    box.pack(side="left", padx=2)
    pal_boxes.append(box)

# Initialisation
update_color()

root.mainloop()