import tkinter as tk
from tkinter import messagebox, filedialog
import colorsys
import json

class ProPaletteBuilder:
    def __init__(self, root):
        self.root = root
        self.root.title("Éditeur de Spectre Musical - Association de Sons")
        self.root.geometry("900x750")
        self.data_palette = []
        self.current_index = None

        # --- Barre Latérale (Liste des zones) ---
        self.side_frame = tk.Frame(root, width=250, bg="#f4f4f4", bd=1, relief="sunken")
        self.side_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        tk.Label(self.side_frame, text="Zones de Couleurs", font=("Arial", 11, "bold"), bg="#f4f4f4").pack(pady=5)
        self.listbox = tk.Listbox(self.side_frame, font=("Arial", 9))
        self.listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.load_selected_range)

        # --- Zone de Travail Principale ---
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20)

        # Aperçu visuel
        self.canvas = tk.Canvas(self.main_frame, height=100, bg="white", highlightthickness=1)
        self.canvas.pack(fill="x", pady=20)

        # Sliders (Lecture seule ou ajustement fin)
        self.h_min, self.h_max = self.create_range_slider("Teinte (H)", 0, 360)
        self.s_min, self.s_max = self.create_range_slider("Saturation (S)", 0, 100)
        self.v_min, self.v_max = self.create_range_slider("Luminosité (V)", 0, 100)

        # Sélection du son
        tk.Label(self.main_frame, text="\nFichier Musique :", font=("Arial", 10, "bold")).pack()
        self.song_path = tk.StringVar(value="Aucun son sélectionné")
        self.entry_path = tk.Entry(self.main_frame, textvariable=self.song_path, state="readonly", font=("Arial", 9))
        self.entry_path.pack(fill="x", pady=5)
        tk.Button(self.main_frame, text="Choisir le fichier audio...", command=self.browse_file).pack()

        # Actions
        btn_frame = tk.Frame(self.main_frame)
        btn_frame.pack(pady=30)
        
        tk.Button(btn_frame, text="📥 IMPORTER JSON", command=self.import_json, bg="#9C27B0", fg="white", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✅ VALIDER MODIFS", command=self.update_current_range, bg="#4CAF50", fg="white", padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="💾 SAUVEGARDER JSON FINAL", command=self.save_json, bg="#2196F3", fg="white", padx=10).pack(side="left", padx=5)

    def create_range_slider(self, label, from_val, to_val):
        frame = tk.LabelFrame(self.main_frame, text=label, padx=10, pady=5)
        frame.pack(fill="x", pady=2)
        s_min = tk.Scale(frame, from_=from_val, to=to_val, orient="horizontal", command=self.update_preview)
        s_max = tk.Scale(frame, from_=from_val, to=to_val, orient="horizontal", command=self.update_preview)
        s_min.pack(side="left", fill="x", expand=True)
        s_max.pack(side="left", fill="x", expand=True)
        return s_min, s_max

    def update_preview(self, event=None):
        self.canvas.delete("all")
        width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 600
        steps = 50
        rect_w = width / steps
        for i in range(steps):
            ratio = i / steps
            h = (self.h_min.get() + (self.h_max.get() - self.h_min.get()) * ratio) / 360.0
            s = (self.s_min.get() + (self.s_max.get() - self.s_min.get()) * ratio) / 100.0
            v = (self.v_min.get() + (self.v_max.get() - self.v_min.get()) * ratio) / 100.0
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            color = "#%02x%02x%02x" % (int(r*255), int(g*255), int(b*255))
            self.canvas.create_rectangle(i*rect_w, 0, (i+1)*rect_w, 100, fill=color, outline=color)

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("Fichiers JSON", "*.json")])
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                self.data_palette = json.load(f)
            self.refresh_listbox()
            messagebox.showinfo("Import", f"{len(self.data_palette)} zones chargées depuis le fichier.")

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for i, item in enumerate(self.data_palette):
            label = f"Zone {i+1} " + ("🎵" if item["song_path"] else "❌")
            self.listbox.insert(tk.END, label)

    def load_selected_range(self, event):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            self.current_index = idx
            data = self.data_palette[idx]
            
            self.h_min.set(data["h_range"][0]); self.h_max.set(data["h_range"][1])
            self.s_min.set(data["s_range"][0]); self.s_max.set(data["s_range"][1])
            self.v_min.set(data["v_range"][0]); self.v_max.set(data["v_range"][1])
            self.song_path.set(data["song_path"] if data["song_path"] else "Aucun son sélectionné")
            self.update_preview()

    def update_current_range(self):
        if self.current_index is not None:
            self.data_palette[self.current_index] = {
                "h_range": [self.h_min.get(), self.h_max.get()],
                "s_range": [self.s_min.get(), self.s_max.get()],
                "v_range": [self.v_min.get(), self.v_max.get()],
                "song_path": self.song_path.get() if self.song_path.get() != "Aucun son sélectionné" else ""
            }
            self.refresh_listbox()
            messagebox.showinfo("Succès", "Données de la zone mises à jour.")

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Choisir un son", filetypes=[("Audio", "*.mp3 *.wav *.ogg")])
        if filename:
            self.song_path.set(filename)

    def save_json(self):
        if not self.data_palette: return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data_palette, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Export", "Fichier de configuration sonore sauvegardé !")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProPaletteBuilder(root)
    root.mainloop()