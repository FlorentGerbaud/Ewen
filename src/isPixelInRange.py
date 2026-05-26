import json
import colorsys
import pygame # Importation pour le son
import os

def play_song_for_pixel(r, g, b, json_file):
    # 1. Initialiser le moteur audio de Pygame
    pygame.mixer.init()

    # 2. Charger le JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        palettes = json.load(f)

    # 3. Conversion du pixel (RGB -> HSV)
    h_px, s_px, v_px = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    h_px, s_px, v_px = h_px * 360, s_px * 100, v_px * 100
    
    print(f"--- Analyse du pixel RGB({r},{g},{b}) ---")
    print(f"H: {h_px:.1f} | S: {s_px:.1f} | V: {v_px:.1f}")

    # 4. Recherche dans le JSON
    song_to_play = None
    for entry in palettes:
        h_min, h_max = min(entry["h_range"]), max(entry["h_range"])
        s_min, s_max = min(entry["s_range"]), max(entry["s_range"])
        v_min, v_max = min(entry["v_range"]), max(entry["v_range"])

        if (h_min <= h_px <= h_max and 
            s_min <= s_px <= s_max and 
            v_min <= v_px <= v_max):
            song_to_play = entry["song_path"]
            break 

    # 5. Action : Jouer le son
    if song_to_play:
        if os.path.exists(song_to_play):
            print(f"✅ Correspondance trouvée ! Lecture de : {os.path.basename(song_to_play)}")
            pygame.mixer.music.load(song_to_play)
            pygame.mixer.music.play()
            
            # On attend que la musique finisse ou que l'utilisateur appuie sur Entrée
            input("Appuyez sur Entrée pour arrêter la musique...")
            pygame.mixer.music.stop()
        else:
            print(f"⚠️ Fichier introuvable sur le disque : {song_to_play}")
    else:
        print("❌ Ce pixel ne correspond à aucune plage du JSON.")

# --- TEST ---
# Le pixel (150, 180, 140) est un vert doux qui correspond à ton JSON [121, 103]
play_song_for_pixel(150, 180, 140, 'test.json')