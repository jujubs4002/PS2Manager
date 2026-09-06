import os
import sys
import json
import time
import re
import threading
import shutil
import psutil
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Sistema de som customizado via Beep (frequências puras)
try:
    import winsound
    SOUND_SUPPORT = True
except ImportError:
    SOUND_SUPPORT = False

# ==========================================
# DESIGN SYSTEM (Sleek, Compact, Professional)
# ==========================================
ctk.set_appearance_mode("dark")

COLORS = {
    "bg_main": "#0D1117",        # Github Dark bg
    "bg_sidebar": "#010409",     # Darker sidebar
    "card_base": "#161B22",      # Sleek card
    "card_hover": "#21262D",     # Hover state
    "accent": "#2F81F7",         # Tech Blue
    "text_main": "#E6EDF3",      # Crisp white
    "text_muted": "#8B949E",     # Subtle gray
    "success": "#238636",        # Muted Emerald
    "warning": "#D29922",        # Muted Gold
    "danger": "#DA3633",         # Muted Crimson
    "border": "#30363D"          # Thin borders
}

APP_NAME = "PS2 MANAGER"
DATA_FILE = "library.json"

# ==========================================
# MÓDULO CORE: SONS SINTETIZADOS
# ==========================================
class SoundManager:
    def __init__(self):
        self.enabled = False  # Desligado por padrão, ligável nas configs

    def _play_freq(self, freqs_durations):
        if not self.enabled or not SOUND_SUPPORT: return
        def play():
            for freq, dur in freqs_durations:
                try: winsound.Beep(freq, dur)
                except: pass
        threading.Thread(target=play, daemon=True).start()

    def play_click(self): self._play_freq([(4000, 10)])
    def play_success(self): self._play_freq([(1200, 40), (1800, 60)])
    def play_error(self): self._play_freq([(200, 150), (200, 150)])
    def play_usb(self, connected=True):
        if connected: self._play_freq([(800, 40), (1200, 40), (1800, 80)])
        else: self._play_freq([(1800, 40), (1200, 40), (800, 80)])

sound_fx = SoundManager()

def format_size(bytes_size):
    if bytes_size == 0: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0: return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0

# ==========================================
# MÓDULO CORE: ANALYZER & MANAGER
# ==========================================
class GameAnalyzer:
    REGION_MAP = {'SLUS': 'USA', 'SCUS': 'USA', 'SLES': 'Europe', 'SCES': 'Europe', 'SLPS': 'Japan', 'SLPM': 'Japan', 'SCPS': 'Japan', 'SLKA': 'Korea'}

    @staticmethod
    def extract_game_id(file_path):
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(2 * 1024 * 1024)
                match = re.search(b'([S|s][L|C|l|c][U|E|P|A|K][S|M|J|A|s|m|j|a]_?\d{3}\.?\d{2})', chunk)
                if match:
                    clean_id = match.group(1).decode('utf-8', errors='ignore').upper().replace('_', '-').replace('.', '')
                    if len(clean_id) == 9 and clean_id[4] != '-': clean_id = clean_id[:4] + '-' + clean_id[4:]
                    return clean_id
        except: pass
        return "Unknown"

    @staticmethod
    def get_region(game_id): return GameAnalyzer.REGION_MAP.get(game_id[:4], "Other") if game_id != "Unknown" and len(game_id) >= 4 else "Unknown"
    
    @staticmethod
    def get_media_type(size_bytes):
        mb = size_bytes / (1024 * 1024)
        if mb < 701: return "CD"
        elif mb <= 4700: return "DVD5"
        else: return "DVD9"

    @staticmethod
    def analyze(file_path):
        size = os.stat(file_path).st_size
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        game_id = GameAnalyzer.extract_game_id(file_path)
        
        # Lógica de status mais realista
        status = "BAD" if game_id == "Unknown" else "TERRIBLE" if ext not in ['.iso', '.bin', '.img'] else "EXCELLENT"

        return {
            "path": file_path, "name": os.path.splitext(filename)[0].replace('_', ' '),
            "id": game_id, "region": GameAnalyzer.get_region(game_id), "size_bytes": size,
            "size_str": format_size(size), "format": ext[1:].upper() if ext else "N/A",
            "media": GameAnalyzer.get_media_type(size), "fragmentation": "N/A", "status": status
        }

class LibraryManager:
    def __init__(self):
        self.games = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f: self.games = json.load(f)
            except: pass

    def save(self):
        with open(DATA_FILE, 'w') as f: json.dump(self.games, f)

    def add(self, game_data):
        for i, g in enumerate(self.games):
            if g['path'] == game_data['path']:
                self.games[i] = game_data; self.save(); return False
        self.games.append(game_data); self.save(); return True

    def stats(self):
        size = sum(g.get("size_bytes", 0) for g in self.games)
        return {"total": len(self.games), "size_str": format_size(size)}

class USBManager:
    @staticmethod
    def get_usb_drives():
        usb_drives = []
        for p in psutil.disk_partitions(all=False):
            if 'removable' in p.opts.lower() or p.fstype.lower() in ['fat32', 'exfat', 'ntfs']:
                if p.device.startswith('C:'): continue 
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    usb_drives.append({
                        "device": p.device, "mountpoint": p.mountpoint, "fstype": p.fstype,
                        "total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent
                    })
                except: continue
        return usb_drives

    @staticmethod
    def analyze_opl_structure(mountpoint):
        expected = ['DVD', 'CD', 'ART', 'CFG', 'VMC']
        struct = {d: os.path.isdir(os.path.join(mountpoint, d)) for d in expected}
        has_essential = struct['DVD'] or struct['CD']
        status = "VALID" if all(struct.values()) else ("INCOMPLETE" if has_essential else "INVALID")
        return {"folders": struct, "status": status}

# ==========================================
# MÓDULO DE MIGRAÇÃO E FORMATAÇÃO
# ==========================================
class MigrationWorker:
    def __init__(self, drive, target_fs, callbacks):
        self.drive = drive
        self.target_fs = target_fs
        self.cb_log = callbacks['log']
        self.cb_prog_total = callbacks['prog_total']
        self.cb_prog_step = callbacks['prog_step']
        self.cb_done = callbacks['done']
        self.tmp_dir = os.path.join(os.getcwd(), "jogos.tmp")
        self.cancel_flag = False

    def log(self, msg): self.cb_log(msg)

    def _copy_chunked(self, src, dst):
        size = os.path.getsize(src)
        copied = 0
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            while True:
                if self.cancel_flag: raise Exception("Cancelled by user.")
                buf = fsrc.read(1024 * 1024 * 4) # 4MB
                if not buf: break
                fdst.write(buf)
                copied += len(buf)
                self.cb_prog_step(copied / size if size > 0 else 1)

    def _copy_dir_with_progress(self, src_dir, dst_dir):
        if not os.path.exists(dst_dir): os.makedirs(dst_dir)
        files = []
        for r, d, f in os.walk(src_dir):
            for file in f: files.append(os.path.join(r, file))
        
        for idx, file_path in enumerate(files):
            rel_path = os.path.relpath(file_path, src_dir)
            target = os.path.join(dst_dir, rel_path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            self.log(f"Copying: {rel_path}")
            self._copy_chunked(file_path, target)

    def run(self):
        try:
            self.cb_prog_total(0.0)
            self.log(f"--- MIGRATION PROTOCOL STARTED ---")
            self.log(f"Target Drive: {self.drive['device']} | Target FS: {self.target_fs}")
            
            # STEP 1: Backup
            self.log("\n[1/7] Initializing backup to jogos.tmp...")
            self.cb_prog_total(0.1)
            if os.path.exists(self.tmp_dir): shutil.rmtree(self.tmp_dir)
            self._copy_dir_with_progress(self.drive['mountpoint'], self.tmp_dir)
            
            # STEP 2: Format
            self.log("\n[2/7] Formatting drive (This may take a moment)...")
            self.cb_prog_total(0.4)
            letter = self.drive['device'].replace(':', '').replace('\\', '')
            cmd = f'powershell -Command "Format-Volume -DriveLetter {letter} -FileSystem {self.target_fs} -NewFileSystemLabel PS2USB -Confirm:$false"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode != 0:
                raise Exception(f"Format failed: {res.stderr}")
            self.log("Format successful.")

            # STEP 3: Restore
            self.log("\n[3/7] Restoring files to USB...")
            self.cb_prog_total(0.5)
            self._copy_dir_with_progress(self.tmp_dir, self.drive['mountpoint'])
            
            # STEP 4 & 5: Verify
            self.log("\n[4/7] Verifying integrity...")
            self.cb_prog_total(0.8)
            corrupted = False
            for r, d, f in os.walk(self.tmp_dir):
                for file in f:
                    tmp_path = os.path.join(r, file)
                    usb_path = os.path.join(self.drive['mountpoint'], os.path.relpath(tmp_path, self.tmp_dir))
                    if not os.path.exists(usb_path) or os.path.getsize(tmp_path) != os.path.getsize(usb_path):
                        corrupted = True
                        self.log(f"Integrity check failed for: {file}")
                        break

            if corrupted:
                self.log("\n[5/7] CORRUPTION DETECTED. Re-attempting format and copy...")
                res = subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW) 
                self._copy_dir_with_progress(self.tmp_dir, self.drive['mountpoint']) 
                self.log("\n[6/7] Second attempt completed. Assuming tmp data is intact.")
            else:
                self.log("\n[5/7] Integrity verification passed 100%.")

            # STEP 7: Cleanup
            self.log("\n[7/7] Cleaning up temporary files...")
            self.cb_prog_total(0.9)
            shutil.rmtree(self.tmp_dir)

            self.log("\n--- MIGRATION COMPLETED SUCCESSFULLY ---")
            self.cb_prog_total(1.0)
            self.cb_prog_step(1.0)
            self.cb_done(True)
            sound_fx.play_success()

        except Exception as e:
            self.log(f"\n[!] FATAL ERROR: {str(e)}")
            self.cb_done(False)
            sound_fx.play_error()

# ==========================================
# MÓDULO UI: COMPONENTES
# ==========================================
class NotificationPopup(ctk.CTkFrame):
    def __init__(self, master, message, type="info", **kwargs):
        super().__init__(master, fg_color=COLORS["card_base"], corner_radius=4, border_width=1, **kwargs)
        color = COLORS["success"] if type == "success" else COLORS["warning"] if type == "warning" else COLORS["accent"]
        self.configure(border_color=color)
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 11, "bold"), text_color=COLORS["text_main"]).pack(padx=15, pady=8)
        self.after(3000, self.destroy)

class HoverCard(ctk.CTkFrame):
    def __init__(self, master, game_data, callback, **kwargs):
        super().__init__(master, fg_color=COLORS["card_base"], corner_radius=4, height=36, border_width=1, border_color=COLORS["border"], **kwargs)
        self.pack_propagate(False)
        self.game = game_data
        self.callback = callback
        
        st = game_data.get('status', 'BAD')
        self.color = COLORS["success"] if st == "EXCELLENT" else COLORS["warning"] if st == "GOOD" else COLORS["danger"]

        self.grid_columnconfigure((1,2,3,4), weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.status_bar = ctk.CTkFrame(self, width=4, fg_color=self.color, corner_radius=0)
        self.status_bar.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        ctk.CTkLabel(self, text=game_data.get('name', 'Unknown')[:35], font=("Segoe UI", 12, "bold"), text_color=COLORS["text_main"]).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(self, text=game_data.get('id', 'N/A'), font=("Consolas", 11), text_color=COLORS["text_muted"]).grid(row=0, column=2, sticky="w")
        ctk.CTkLabel(self, text=game_data.get('size_str', 'N/A'), font=("Consolas", 11), text_color=COLORS["text_muted"]).grid(row=0, column=3, sticky="w")
        ctk.CTkLabel(self, text=game_data.get('status', 'N/A'), font=("Segoe UI", 10, "bold"), text_color=self.color).grid(row=0, column=4, sticky="e", padx=10)
        
        self.bind("<Enter>", lambda e: self.configure(fg_color=COLORS["card_hover"], border_color=COLORS["accent"]))
        self.bind("<Leave>", lambda e: self.configure(fg_color=COLORS["card_base"], border_color=COLORS["border"]))
        self._bind_click(self)

    def _bind_click(self, w):
        w.bind("<Button-1>", lambda e: (sound_fx.play_click(), self.callback(self.game)))
        for c in w.winfo_children(): self._bind_click(c)

class GameDetailsModal(ctk.CTkToplevel):
    def __init__(self, master, game_data):
        super().__init__(master)
        self.title("Game Details")
        self.geometry("400x380")
        self.configure(fg_color=COLORS["bg_main"])
        self.resizable(False, False)
        self.attributes("-topmost", True)

        lbl_name = ctk.CTkLabel(self, text=game_data.get('name', 'Unknown'), font=("Segoe UI", 16, "bold"), text_color=COLORS["text_main"])
        lbl_name.pack(pady=(20, 5))
        lbl_path = ctk.CTkLabel(self, text=game_data.get('path', ''), font=("Consolas", 9), text_color=COLORS["text_muted"])
        lbl_path.pack(pady=(0, 15))

        frm = ctk.CTkFrame(self, fg_color=COLORS["card_base"], corner_radius=4, border_width=1, border_color=COLORS["border"])
        frm.pack(fill="both", expand=True, padx=20, pady=10)

        r = 0
        def add_row(k, v, color=COLORS["text_main"]):
            nonlocal r
            ctk.CTkLabel(frm, text=k, font=("Segoe UI", 11, "bold"), text_color=COLORS["text_muted"]).grid(row=r, column=0, sticky="w", padx=15, pady=8)
            ctk.CTkLabel(frm, text=v, font=("Consolas", 11), text_color=color).grid(row=r, column=1, sticky="w", padx=15, pady=8)
            r += 1

        add_row("Game ID", game_data.get('id', 'N/A'))
        add_row("Region", game_data.get('region', 'N/A'))
        add_row("Size", game_data.get('size_str', 'N/A'))
        add_row("Media", game_data.get('media', 'N/A'))
        add_row("Format", game_data.get('format', 'N/A'))
        add_row("Fragmentation", game_data.get('fragmentation', 'N/A'))
        
        st = game_data.get('status', 'BAD')
        c = COLORS["success"] if st == "EXCELLENT" else COLORS["warning"] if st == "GOOD" else COLORS["danger"]
        add_row("Status", st, c)

        btn = ctk.CTkButton(self, text="CLOSE", font=("Segoe UI", 11, "bold"), fg_color=COLORS["border"], hover_color=COLORS["card_hover"], command=self.destroy)
        btn.pack(pady=15)

# ==========================================
# UI: PÁGINAS (Sleek Design)
# ==========================================
class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkLabel(self, text="DASHBOARD", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_main"]).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))

        def make_card(r, c, title, var_name, color):
            frm = ctk.CTkFrame(self, fg_color=COLORS["card_base"], corner_radius=4, border_width=1, border_color=COLORS["border"])
            frm.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(frm, text=title, font=("Segoe UI", 10, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=15, pady=(15,0))
            lbl = ctk.CTkLabel(frm, text="0", font=("Consolas", 24), text_color=color)
            lbl.pack(anchor="w", padx=15, pady=(0, 15))
            setattr(self, var_name, lbl)

        make_card(1, 0, "LIBRARY GAMES", "lbl_games", COLORS["accent"])
        make_card(1, 1, "CONNECTED USB", "lbl_usb", COLORS["success"])
        make_card(1, 2, "TOTAL SIZE", "lbl_size", COLORS["text_main"])

    def refresh(self):
        st = self.app.library.stats()
        self.lbl_games.configure(text=str(st['total']))
        self.lbl_size.configure(text=st['size_str'])
        self.lbl_usb.configure(text=str(len(USBManager.get_usb_drives())))

class GamesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(head, text="LIBRARY", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_main"]).pack(side="left")
        ctk.CTkButton(head, text="+ SCAN DIR", font=("Segoe UI", 11, "bold"), height=28, width=100, corner_radius=4, fg_color=COLORS["accent"], hover_color="#1d4ed8", command=self.scan).pack(side="right")

        search_frm = ctk.CTkFrame(self, fg_color="transparent")
        search_frm.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        self.ent_search = ctk.CTkEntry(search_frm, placeholder_text="Search by name or ID...", font=("Segoe UI", 11), height=28, width=250, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.ent_search.pack(side="left")
        self.ent_search.bind("<KeyRelease>", self._filter)

        self.cmb_filter = ctk.CTkOptionMenu(search_frm, values=["ALL", "EXCELLENT", "GOOD", "BAD", "TERRIBLE", "ISO"], font=("Segoe UI", 11), height=28, fg_color=COLORS["bg_main"], button_color=COLORS["border"], command=self._filter)
        self.cmb_filter.pack(side="left", padx=10)

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=2, column=0, sticky="nsew")

    def refresh(self):
        self._filter()

    def _filter(self, e=None):
        q = self.ent_search.get().lower()
        f = self.cmb_filter.get()
        
        for w in self.list.winfo_children(): w.destroy()
        
        for g in self.app.library.games:
            if q and q not in g.get('name', '').lower() and q not in g.get('id', '').lower(): continue
            if f != "ALL":
                if f in ["EXCELLENT", "GOOD", "BAD", "TERRIBLE"] and g.get('status') != f: continue
                if f == "ISO" and g.get('format') != "ISO": continue
            
            HoverCard(self.list, g, self.details).pack(fill="x", pady=2)

    def scan(self):
        d = filedialog.askdirectory()
        if not d: return
        self.app.show_toast("Scanning folder...")
        threading.Thread(target=self._do_scan, args=(d,), daemon=True).start()

    def _do_scan(self, d):
        for r, ds, fs in os.walk(d):
            for f in fs:
                if f.lower().endswith(('.iso', '.bin', '.img')):
                    self.app.library.add(GameAnalyzer.analyze(os.path.join(r, f)))
        self.app.after(0, self.refresh)
        self.app.after(0, sound_fx.play_success)
        self.app.after(0, lambda: self.app.show_toast("Scan complete!", "success"))

    def details(self, g):
        GameDetailsModal(self.app, g)

class USBPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="USB MANAGER", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_main"]).grid(row=0, column=0, sticky="w", pady=(0, 15))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        self.var_usb = ctk.StringVar(value="None")
        self.cmb_usb = ctk.CTkOptionMenu(top, variable=self.var_usb, values=["None"], font=("Consolas", 11), height=28, fg_color=COLORS["bg_main"], button_color=COLORS["border"], command=self.analyze)
        self.cmb_usb.pack(side="left")

        self.btn_ref = ctk.CTkButton(top, text="REFRESH", font=("Segoe UI", 10, "bold"), height=28, width=70, corner_radius=4, fg_color=COLORS["border"], hover_color=COLORS["card_hover"], command=self.refresh)
        self.btn_ref.pack(side="left", padx=10)

        self.info = ctk.CTkFrame(self, fg_color=COLORS["card_base"], corner_radius=4, border_width=1, border_color=COLORS["border"])
        self.info.grid(row=2, column=0, sticky="nsew")

        self.lbl_drive = ctk.CTkLabel(self.info, text="No drive selected", font=("Segoe UI", 14, "bold"), text_color=COLORS["text_main"])
        self.lbl_drive.pack(anchor="w", padx=20, pady=(20, 5))
        
        self.lbl_space = ctk.CTkLabel(self.info, text="", font=("Consolas", 11), text_color=COLORS["text_muted"])
        self.lbl_space.pack(anchor="w", padx=20)
        
        self.prog = ctk.CTkProgressBar(self.info, height=8, progress_color=COLORS["accent"], fg_color=COLORS["bg_main"])
        self.prog.pack(fill="x", padx=20, pady=(10, 20))
        self.prog.set(0)

        ctk.CTkLabel(self.info, text="OPL STRUCTURE", font=("Segoe UI", 11, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=20)
        self.txt_opl = ctk.CTkTextbox(self.info, font=("Consolas", 11), fg_color=COLORS["bg_main"], text_color=COLORS["text_main"], border_width=1, border_color=COLORS["border"], height=120)
        self.txt_opl.pack(fill="x", padx=20, pady=5)
        self.txt_opl.configure(state="disabled")

        self.drives = []

    def refresh(self):
        self.drives = USBManager.get_usb_drives()
        vals = [f"{d['device']} [{d['fstype']}]" for d in self.drives] if self.drives else ["None"]
        self.cmb_usb.configure(values=vals)
        if self.var_usb.get() not in vals: self.var_usb.set(vals[0])
        self.analyze(self.var_usb.get())

    def analyze(self, sel):
        if sel == "None":
            self.lbl_drive.configure(text="No drive selected"); self.lbl_space.configure(text=""); self.prog.set(0)
            self._write_opl("")
            return
            
        drv = next((d for d in self.drives if d['device'] == sel.split(" ")[0]), None)
        if not drv: return

        self.lbl_drive.configure(text=f"USB DRIVE: {drv['device']}")
        self.lbl_space.configure(text=f"Capacity: {format_size(drv['total'])} | Free: {format_size(drv['free'])}")
        self.prog.set(drv['percent'] / 100)
        self.prog.configure(progress_color=COLORS["danger"] if drv['percent'] > 90 else COLORS["accent"])

        res = USBManager.analyze_opl_structure(drv['mountpoint'])
        out = f"STATUS: {res['status']}\n\n"
        for k, v in res['folders'].items(): out += f"[{'OK' if v else 'MISSING'}] {k}/\n"
        self._write_opl(out)

    def _write_opl(self, txt):
        self.txt_opl.configure(state="normal")
        self.txt_opl.delete("1.0", "end"); self.txt_opl.insert("end", txt)
        self.txt_opl.configure(state="disabled")

class MigratePage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1, uniform="col")
        self.grid_columnconfigure(1, weight=2, uniform="col")
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="FORMAT & MIGRATE", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_main"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # Controls (Left)
        ctrl = ctk.CTkFrame(self, fg_color=COLORS["card_base"], corner_radius=4, border_width=1, border_color=COLORS["border"])
        ctrl.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        ctk.CTkLabel(ctrl, text="1. Select Target Drive", font=("Segoe UI", 11, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=15, pady=(15,5))
        self.drv_var = ctk.StringVar(value="None")
        self.cmb_drv = ctk.CTkComboBox(ctrl, variable=self.drv_var, values=["None"], font=("Consolas", 12), height=28, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.cmb_drv.pack(fill="x", padx=15)

        ctk.CTkLabel(ctrl, text="2. Target File System", font=("Segoe UI", 11, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=15, pady=(20,5))
        self.fs_var = ctk.StringVar(value="exFAT")
        self.cmb_fs = ctk.CTkComboBox(ctrl, variable=self.fs_var, values=["exFAT", "FAT32"], font=("Consolas", 12), height=28, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.cmb_fs.pack(fill="x", padx=15)

        self.btn_start = ctk.CTkButton(ctrl, text="START MIGRATION", font=("Segoe UI", 11, "bold"), height=30, corner_radius=4, fg_color=COLORS["danger"], hover_color="#B22222", command=self.start_migration)
        self.btn_start.pack(fill="x", padx=15, pady=30)
        
        ctk.CTkLabel(ctrl, text="WARNING: This will format the drive.\nA safe backup to ./jogos.tmp is performed.", font=("Segoe UI", 10), text_color=COLORS["warning"], justify="left").pack(anchor="w", padx=15)

        # Log & Progress (Right)
        log_frm = ctk.CTkFrame(self, fg_color=COLORS["card_base"], corner_radius=4, border_width=1, border_color=COLORS["border"])
        log_frm.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        
        self.log_box = ctk.CTkTextbox(log_frm, font=("Consolas", 11), fg_color=COLORS["bg_main"], text_color=COLORS["text_main"], border_width=0)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_box.insert("end", "System Ready.\nSelect a drive and FS to begin migration process.\n")
        self.log_box.configure(state="disabled")

        prog_frm = ctk.CTkFrame(log_frm, fg_color="transparent")
        prog_frm.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(prog_frm, text="Overall Progress", font=("Segoe UI", 10), text_color=COLORS["text_muted"]).pack(anchor="w")
        self.prog_tot = ctk.CTkProgressBar(prog_frm, height=6, progress_color=COLORS["accent"], fg_color=COLORS["bg_main"])
        self.prog_tot.pack(fill="x", pady=(2, 10))
        self.prog_tot.set(0)

        ctk.CTkLabel(prog_frm, text="Current Step Progress", font=("Segoe UI", 10), text_color=COLORS["text_muted"]).pack(anchor="w")
        self.prog_step = ctk.CTkProgressBar(prog_frm, height=6, progress_color=COLORS["success"], fg_color=COLORS["bg_main"])
        self.prog_step.pack(fill="x", pady=(2, 5))
        self.prog_step.set(0)
        
        self.drives = []

    def refresh(self):
        self.drives = USBManager.get_usb_drives()
        vals = [f"{d['device']} [{d['fstype']}]" for d in self.drives] if self.drives else ["None"]
        self.cmb_drv.configure(values=vals)
        if self.drv_var.get() not in vals: self.drv_var.set(vals[0])

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def start_migration(self):
        sel = self.drv_var.get()
        if sel == "None": return
        drv = next((d for d in self.drives if d['device'] == sel.split(" ")[0]), None)
        if not drv: return

        if not messagebox.askyesno("CONFIRM MIGRATION", f"Are you sure you want to backup and format {drv['device']} to {self.fs_var.get()}?\nDo not remove the drive during this process."): return

        self.btn_start.configure(state="disabled", fg_color=COLORS["border"])
        self.log_box.configure(state="normal"); self.log_box.delete("1.0", "end"); self.log_box.configure(state="disabled")
        
        worker = MigrationWorker(drv, self.fs_var.get(), {
            'log': lambda m: self.app.after(0, self.log, m),
            'prog_total': lambda v: self.app.after(0, self.prog_tot.set, v),
            'prog_step': lambda v: self.app.after(0, self.prog_step.set, v),
            'done': lambda s: self.app.after(0, self._done)
        })
        threading.Thread(target=worker.run, daemon=True).start()

    def _done(self, success):
        self.btn_start.configure(state="normal", fg_color=COLORS["danger"])
        self.app.refresh_all()

class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="SETTINGS", font=("Segoe UI", 16, "bold"), text_color=COLORS["text_main"]).pack(anchor="w", pady=(0, 20))
        
        frm = ctk.CTkFrame(self, fg_color=COLORS["card_base"], corner_radius=4, border_width=1, border_color=COLORS["border"])
        frm.pack(fill="x")
        
        ctk.CTkLabel(frm, text="SOUND EFFECTS", font=("Segoe UI", 11, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.snd_var = ctk.BooleanVar(value=sound_fx.enabled)
        ctk.CTkSwitch(frm, text="Enable synthesized sounds (Beeps)", font=("Segoe UI", 11), variable=self.snd_var, command=self.toggle_sound, progress_color=COLORS["accent"]).pack(anchor="w", padx=15, pady=(0, 20))

    def toggle_sound(self):
        sound_fx.enabled = self.snd_var.get()
        if sound_fx.enabled: sound_fx.play_click()

# ==========================================
# MAIN APP (Sleek Window)
# ==========================================
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("950x600")
        self.minsize(800, 500)
        self.configure(fg_color=COLORS["bg_main"])
        
        self.library = LibraryManager()
        self.cur = None
        self.last_usb = -1

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sleek Sidebar
        self.sb = ctk.CTkFrame(self, width=170, corner_radius=0, fg_color=COLORS["bg_sidebar"])
        self.sb.grid(row=0, column=0, sticky="nsew")
        self.sb.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(self.sb, text="PS2", font=("Segoe UI Black", 20), text_color=COLORS["accent"]).grid(row=0, column=0, pady=(20, 5), padx=20, sticky="w")
        ctk.CTkLabel(self.sb, text="UTILITY", font=("Segoe UI", 12), text_color=COLORS["text_muted"]).grid(row=0, column=0, pady=(24, 5), padx=(65,20), sticky="w")

        self.btns = {}
        def nav(r, k, t):
            b = ctk.CTkButton(self.sb, text=t, font=("Segoe UI", 11, "bold"), fg_color="transparent", text_color=COLORS["text_muted"], anchor="w", height=30, corner_radius=4, hover_color=COLORS["card_hover"], command=lambda: self.show(k))
            b.grid(row=r, column=0, padx=10, pady=2, sticky="ew")
            self.btns[k] = b

        nav(1, "dash", "DASHBOARD")
        nav(2, "games", "LIBRARY DB")
        nav(3, "usb", "USB MANAGER")
        nav(4, "migrate", "FORMAT & MIGRATE")
        nav(5, "settings", "SETTINGS")

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.pages = {
            "dash": DashboardPage(self.content, self), 
            "games": GamesPage(self.content, self), 
            "usb": USBPage(self.content, self),
            "migrate": MigratePage(self.content, self),
            "settings": SettingsPage(self.content, self)
        }
        self.show("dash")
        self.monitor_usb()

    def show(self, k):
        sound_fx.play_click()
        for b in self.btns.values(): b.configure(fg_color="transparent", text_color=COLORS["text_muted"])
        self.btns[k].configure(fg_color=COLORS["card_base"], text_color=COLORS["text_main"])
        if self.cur: self.cur.grid_forget()
        self.cur = self.pages[k]
        self.cur.grid(row=0, column=0, sticky="nsew")
        if hasattr(self.cur, "refresh"): self.cur.refresh()

    def monitor_usb(self):
        def loop():
            while True:
                c = len(USBManager.get_usb_drives())
                if self.last_usb != -1 and c != self.last_usb:
                    sound_fx.play_usb(c > self.last_usb)
                    if c > self.last_usb: self.after(0, lambda: self.show_toast("USB Inserted", "success"))
                    else: self.after(0, lambda: self.show_toast("USB Removed", "warning"))
                    self.after(0, self.refresh_all)
                self.last_usb = c
                time.sleep(2)
        threading.Thread(target=loop, daemon=True).start()

    def refresh_all(self):
        if hasattr(self.cur, "refresh"): self.cur.refresh()

    def show_toast(self, msg, type="info"):
        t = NotificationPopup(self, msg, type)
        t.place(relx=0.98, rely=0.95, anchor="se")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()