import os
import time
import threading
import subprocess
import shutil
import webbrowser
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Importa toda a lógica pesada que movemos para o arquivo backend
from scripts.core_backend import *

class SetupFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=cfg.get_color("bg_main"))
        self.app = app; self.pack(fill="both", expand=True)
        self.content = ctk.CTkFrame(self, fg_color="transparent"); self.content.place(relx=0.5, rely=0.5, anchor="center")
        self.show_step_0()

    def clear(self):
        for w in self.content.winfo_children(): w.destroy()

    def show_step_0(self):
        self.clear()
        ctk.CTkLabel(self.content, text="PS2 MANAGER", font=("Segoe UI Black", 32), text_color=cfg.get_color("accent")).pack(pady=(20, 5))
        ctk.CTkLabel(self.content, text=t("setup_welcome"), font=("Segoe UI", 16), text_color=cfg.get_color("text_main")).pack(pady=(0, 40))
        ctk.CTkButton(self.content, text=t("setup_continue"), font=("Segoe UI", 12, "bold"), height=40, width=200, corner_radius=cfg.get_radius("button"), command=self.show_step_1).pack()

    def show_step_1(self):
        self.clear()
        ctk.CTkLabel(self.content, text=t("setup_lang"), font=("Segoe UI", 18, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(20, 30))
        def set_lang(l): cfg.data["language"] = l; cfg.save(); self.show_step_2()
        r = cfg.get_radius("button")
        ctk.CTkButton(self.content, text="English", height=45, width=250, corner_radius=r, fg_color=cfg.get_color("card_base"), text_color=cfg.get_color("text_main"), hover_color=cfg.get_color("card_hover"), command=lambda: set_lang("EN")).pack(pady=5)
        ctk.CTkButton(self.content, text="Português", height=45, width=250, corner_radius=r, fg_color=cfg.get_color("card_base"), text_color=cfg.get_color("text_main"), hover_color=cfg.get_color("card_hover"), command=lambda: set_lang("PT")).pack(pady=5)
        ctk.CTkButton(self.content, text="Español", height=45, width=250, corner_radius=r, fg_color=cfg.get_color("card_base"), text_color=cfg.get_color("text_main"), hover_color=cfg.get_color("card_hover"), command=lambda: set_lang("ES")).pack(pady=5)

    def show_step_2(self):
        self.clear()
        ctk.CTkLabel(self.content, text=t("setup_model"), font=("Segoe UI", 18, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(20, 5))
        ctk.CTkLabel(self.content, text=t("setup_model_desc"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted")).pack(pady=(0, 25))
        models = ["SCPH-10000", "SCPH-3000x", "SCPH-5000x", "SCPH-7000x", "SCPH-9000x", "PSX DESR"]
        self.cmb_model = ctk.CTkComboBox(self.content, values=models, font=("Segoe UI", 14), height=40, width=250, corner_radius=cfg.get_radius("entry"))
        self.cmb_model.pack(pady=10)
        ctk.CTkLabel(self.content, text=t("setup_type"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(20, 10))
        self.seg_type = ctk.CTkSegmentedButton(self.content, values=["FAT", "SLIM"], font=("Segoe UI", 12), width=250); self.seg_type.pack(pady=5); self.seg_type.set("SLIM")
        ctk.CTkButton(self.content, text=t("setup_continue"), font=("Segoe UI", 12, "bold"), height=40, width=250, corner_radius=cfg.get_radius("button"), command=self.finish_setup).pack(pady=(35, 0))

    def finish_setup(self):
        cfg.data.update({"ps2_model": self.cmb_model.get(), "ps2_type": self.seg_type.get(), "setup_done": True, "sound_enabled": True, "bgm_enabled": True, "animations": True, "auto_sync": True})
        cfg.save(); self.show_tour()

    def show_tour(self):
        self.clear()
        tour_data = [
            {"title": "DASHBOARD & LIBRARY", "desc": "Manage all your ISOs, configure GSM video settings, and launch games directly via PCSX2."},
            {"title": "USB MANAGER & CLONE", "desc": "Format drives safely to FAT32/exFAT, monitor space, and mass-clone setups to new USB drives."},
            {"title": "MORE TOOLS & PATCHER", "desc": "Extract ISOs, apply Translation Patches natively, compress to ZSO, and explore raw APA HDDs."}
        ]
        if not hasattr(self, 'tour_step'): self.tour_step = 0
        if self.tour_step >= len(tour_data): return self.end_and_launch()
        
        ctk.CTkLabel(self.content, text="💡 QUICK TOUR", font=("Segoe UI Black", 24), text_color=cfg.get_color("warning")).pack(pady=(10, 20))
        ctk.CTkLabel(self.content, text=tour_data[self.tour_step]["title"], font=("Segoe UI", 18, "bold"), text_color=cfg.get_color("accent")).pack(pady=10)
        ctk.CTkLabel(self.content, text=tour_data[self.tour_step]["desc"], font=("Segoe UI", 14), text_color=cfg.get_color("text_main"), wraplength=400, justify="center").pack(pady=20)
        
        btn_frame = ctk.CTkFrame(self.content, fg_color="transparent"); btn_frame.pack(pady=(30, 0), fill="x")
        r = cfg.get_radius("button")
        if self.tour_step > 0: ctk.CTkButton(btn_frame, text=t("tour_btn_prev"), width=100, fg_color=cfg.get_color("border"), hover_color=cfg.get_color("card_hover"), text_color=cfg.get_color("text_main"), corner_radius=r, command=lambda: self.change_tour(-1)).pack(side="left", padx=5)
        next_txt = t("tour_btn_finish") if self.tour_step == len(tour_data) - 1 else t("tour_btn_next")
        ctk.CTkButton(btn_frame, text=next_txt, width=120, fg_color=cfg.get_color("success"), corner_radius=r, command=lambda: self.change_tour(1)).pack(side="right", padx=5)
        ctk.CTkButton(self.content, text=t("tour_btn_skip"), font=("Segoe UI", 10), fg_color="transparent", hover_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_muted"), command=self.end_and_launch).pack(pady=(15,0))

    def change_tour(self, delta): self.tour_step += delta; self.show_tour()
    def end_and_launch(self): self.destroy(); self.app.build_main_ui(); self.app.check_interrupted_transfer()

class VersionRollbackModal(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Version Rollback"); self.geometry("400x500"); self.configure(fg_color=cfg.get_color("bg_main")); self.attributes("-topmost", True)
        ctk.CTkLabel(self, text=t("ver_title"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(pady=20)
        self.sf = ctk.CTkScrollableFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border")); self.sf.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        ver_dir = os.path.join(BASE_DIR, "VER"); os.makedirs(ver_dir, exist_ok=True)
        exes = [f for f in os.listdir(ver_dir) if f.lower().endswith('.exe')]
        if not exes: ctk.CTkLabel(self.sf, text=t("ver_empty"), text_color=cfg.get_color("text_muted")).pack(pady=20)
        else:
            for exe in exes: ctk.CTkButton(self.sf, text=os.path.splitext(exe)[0], fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), hover_color=cfg.get_color("accent"), command=lambda e=exe: self.launch_old(e), corner_radius=cfg.get_radius("button")).pack(fill="x", pady=5, padx=5)
    def launch_old(self, exe_name): subprocess.Popen([os.path.join(BASE_DIR, "VER", exe_name)]); sys.exit(0)

class NotificationPopup(ctk.CTkFrame):
    def __init__(self, master, message, type="info", **kwargs):
        super().__init__(master, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), **kwargs)
        self.configure(border_color=cfg.get_color("success") if type == "success" else cfg.get_color("warning") if type == "warning" else cfg.get_color("accent"))
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_main")).pack(padx=15, pady=8)
        self.after(3000, self.destroy)

class HoverCard(ctk.CTkFrame):
    def __init__(self, master, game_data, callback, **kwargs):
        super().__init__(master, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), height=36, border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), **kwargs)
        self.pack_propagate(False); self.game, self.callback = game_data, callback
        st = game_data.get('status', 'BAD')
        self.color = cfg.get_color("success") if st == "EXCELLENT" else cfg.get_color("warning") if st == "GOOD" else cfg.get_color("danger")
        self.grid_columnconfigure((1,2,3,4), weight=1); self.grid_rowconfigure(0, weight=1)
        self.status_bar = ctk.CTkFrame(self, width=4, fg_color=self.color, corner_radius=0); self.status_bar.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ctk.CTkLabel(self, text=game_data.get('name', 'Unknown')[:35], font=("Segoe UI", 12), text_color=cfg.get_color("text_main")).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(self, text=game_data.get('id', 'N/A'), font=("Consolas", 11), text_color=cfg.get_color("text_muted")).grid(row=0, column=2, sticky="w")
        ctk.CTkLabel(self, text=game_data.get('size_str', 'N/A'), font=("Consolas", 11), text_color=cfg.get_color("text_muted")).grid(row=0, column=3, sticky="w")
        ctk.CTkLabel(self, text=game_data.get('status', 'N/A'), font=("Segoe UI", 10, "bold"), text_color=self.color).grid(row=0, column=4, sticky="e", padx=10)
        self.bind("<Enter>", lambda e: [self.configure(fg_color=cfg.get_color("card_hover"), border_color=cfg.get_color("accent")), self.status_bar.grid(padx=(5, 10)) if cfg.data.get("animations", True) else None])
        self.bind("<Leave>", lambda e: [self.configure(fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border")), self.status_bar.grid(padx=(0, 10)) if cfg.data.get("animations", True) else None])
        self._bind_click(self)

    def _bind_click(self, w):
        w.bind("<Button-1>", lambda e: (sound_fx.play_click(), self.callback(self.game)))
        for c in w.winfo_children(): self._bind_click(c)

class GameDetailsModal(ctk.CTkToplevel):
    def __init__(self, master, game_data):
        super().__init__(master); self.title("Game Details & OPL CFG"); self.geometry("450x450"); self.configure(fg_color=cfg.get_color("bg_main")); self.resizable(False, False); self.attributes("-topmost", True)
        self.app, self.game_data = master, game_data
        ctk.CTkLabel(self, text=game_data.get('name', 'Unknown'), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(20, 5))
        ctk.CTkLabel(self, text=game_data.get('path', ''), font=("Consolas", 9), text_color=cfg.get_color("text_muted")).pack(pady=(0, 10))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border")); frm.pack(fill="x", padx=20, pady=5)
        def add_row(r, k, v):
            ctk.CTkLabel(frm, text=k, font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_muted")).grid(row=r, column=0, sticky="w", padx=15, pady=4)
            ctk.CTkLabel(frm, text=v, font=("Consolas", 11), text_color=cfg.get_color("text_main")).grid(row=r, column=1, sticky="w", padx=15, pady=4)
        add_row(0, "Game ID", game_data.get('id', 'N/A')); add_row(1, "Format", game_data.get('format', 'N/A')); add_row(2, "Size", game_data.get('size_str', 'N/A'))
        cfg_frm = ctk.CTkFrame(self, fg_color="transparent"); cfg_frm.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(cfg_frm, text=t("cfg_vid"), font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.var_video = ctk.StringVar(value=game_data.get('video_mode', 'Auto'))
        ctk.CTkOptionMenu(cfg_frm, variable=self.var_video, values=["Auto", "PAL", "NTSC"], height=25, corner_radius=cfg.get_radius("entry")).grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(cfg_frm, text=t("cfg_res"), font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.var_res = ctk.StringVar(value=game_data.get('resolution', 'Default'))
        ctk.CTkOptionMenu(cfg_frm, variable=self.var_res, values=["Default", "480p", "720p", "1080i", "1080p"], height=25, corner_radius=cfg.get_radius("entry")).grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(cfg_frm, text=t("cfg_save"), height=25, width=80, fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=self.save_cfg).grid(row=0, column=2, rowspan=2, padx=(5,0))
        btn_frame, btn_frame2 = ctk.CTkFrame(self, fg_color="transparent"), ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 5), padx=20); btn_frame2.pack(fill="x", pady=(5, 15), padx=20)
        rad = cfg.get_radius("button")
        ctk.CTkButton(btn_frame, text=t("lib_btn_test"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("accent"), corner_radius=rad, command=lambda: PCSX2Integration.test_iso(game_data['path'], lambda e: messagebox.showerror("Error", e))).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_frame2, text=t("lib_btn_rem"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("danger"), corner_radius=rad, command=self.remove_game).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_frame2, text=t("lib_btn_close"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("border"), text_color=cfg.get_color("text_main"), corner_radius=rad, command=self.destroy).pack(side="right", expand=True, padx=(5, 0))

    def remove_game(self):
        if messagebox.askyesno("Confirm", "Do you want to REMOVE this game from the library view?"):
            self.app.library.games = [g for g in self.app.library.games if g['path'] != self.game_data['path']]
            db.save(); sound_fx.play_success(); self.app.refresh_all(); self.destroy()

    def save_cfg(self):
        self.game_data['video_mode'] = self.var_video.get()
        self.game_data['resolution'] = self.var_res.get()
        self.app.library.add(self.game_data)
        cfg_dir = os.path.join(os.path.dirname(os.path.dirname(self.game_data['path'])), "CFG")
        try:
            os.makedirs(cfg_dir, exist_ok=True)
            cfg_file = os.path.join(cfg_dir, f"{self.game_data['id']}.cfg")
            content = []
            v, r = self.var_video.get(), self.var_res.get()
            if v != "Auto" or r != "Default":
                content.append("$EnableGSM=1")
                if r == "720p": content.append("$GSMVMode=10")
                elif r == "1080i": content.append("$GSMVMode=13")
                elif r == "1080p": content.append("$GSMVMode=14")
                elif r == "480p": content.append("$GSMVMode=3")
                elif v == "NTSC": content.append("$GSMVMode=1")
                elif v == "PAL": content.append("$GSMVMode=2")
            with open(cfg_file, "w", encoding="utf-8") as f: f.write("\n".join(content))
            sound_fx.play_success(); messagebox.showinfo("Success", f"CFG saved at:\n{cfg_file}")
        except Exception as e: sound_fx.play_error(); messagebox.showerror("Error", str(e))

class CheatEditorModal(ctk.CTkToplevel):
    def __init__(self, master, app, cht_folder, edit_file=None):
        super().__init__(master); self.title("PS2Manager Cheats"); self.geometry("600x580"); self.configure(fg_color=cfg.get_color("bg_main")); self.attributes("-topmost", True)
        self.app, self.cht_folder, self.edit_file = app, cht_folder, edit_file
        games_list = app.library.games
        if not self.edit_file:
            ctk.CTkLabel(self, text=t("cht_sel_game"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("accent")).pack(pady=(20, 5), padx=20, anchor="w")
            self.cmb_games = ctk.CTkComboBox(self, values=[t("cht_manual")] + [f"{g.get('id', 'Unknown')} - {g.get('name', 'Unknown')}" for g in games_list], command=self.on_game_select, fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry"))
            self.cmb_games.pack(fill="x", padx=20)
        ctk.CTkLabel(self, text=t("cht_name"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(15, 5), padx=20, anchor="w")
        self.ent_name = ctk.CTkEntry(self, font=("Consolas", 12), fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.ent_name.pack(fill="x", padx=20)
        ctk.CTkLabel(self, text="Cheat Codes (RAW):", font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(15, 5), padx=20, anchor="w")
        self.txt_codes = ctk.CTkTextbox(self, font=("Consolas", 12), fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border"), border_width=cfg.get_border_width(), text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("card")); self.txt_codes.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        ctk.CTkButton(self, text=t("cht_save"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), height=40, corner_radius=cfg.get_radius("button"), command=self.save).pack(fill="x", padx=20, pady=(0, 20))
        if self.edit_file:
            base_name = os.path.basename(self.edit_file)
            if base_name.endswith('.disabled'): base_name = base_name[:-9]
            if base_name.endswith('.cht'): base_name = base_name[:-4]
            self.ent_name.insert(0, base_name)
            try:
                with open(self.edit_file, 'r', encoding='utf-8') as f: self.txt_codes.insert("0.0", f.read())
            except Exception as e: messagebox.showerror("Error", str(e))

    def on_game_select(self, val):
        if val == t("cht_manual"): return
        game_id, game_name = val.split(" - ")[0], val.split(" - ", 1)[1] if " - " in val else ""
        self.ent_name.delete(0, 'end'); self.ent_name.insert(0, game_id)
        if not self.txt_codes.get("0.0", "end").strip(): self.txt_codes.insert("0.0", f"// Cheat name: {game_name}\n\n")
        
    def save(self):
        name = self.ent_name.get().strip()
        if not name: return
        if not name.lower().endswith(".cht"): name += ".cht"
        if self.edit_file and self.edit_file.endswith(".disabled"): name += ".disabled"
        out_path = os.path.join(self.cht_folder, name)
        try:
            if self.edit_file and os.path.abspath(self.edit_file) != os.path.abspath(out_path) and os.path.exists(self.edit_file): os.remove(self.edit_file)
            with open(out_path, 'w', encoding='utf-8') as f: f.write(self.txt_codes.get("0.0", "end"))
            sound_fx.play_success(); messagebox.showinfo("Success", t("cht_succ")); self.app.refresh_all(); self.destroy()
        except Exception as e: sound_fx.play_error(); messagebox.showerror("Error", f"{t('cht_err')} {e}")

class AddCheatModal(ctk.CTkToplevel):
    def __init__(self, master, app, cht_folder):
        super().__init__(master); self.title(t("cht_add")); self.geometry("350x250"); self.configure(fg_color=cfg.get_color("bg_main")); self.attributes("-topmost", True)
        self.app, self.cht_folder = app, cht_folder
        ctk.CTkLabel(self, text=t("cht_add"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(20, 30))
        r = cfg.get_radius("button")
        ctk.CTkButton(self, text=t("cht_import"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=r, command=self.import_cht).pack(fill="x", padx=40, pady=10)
        ctk.CTkButton(self, text=t("cht_create"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), height=40, corner_radius=r, command=self.create_scratch).pack(fill="x", padx=40, pady=10)
        
    def import_cht(self):
        f = filedialog.askopenfilename(filetypes=[("Cheat Files", "*.cht")])
        if f:
            try: shutil.copy2(f, self.cht_folder); sound_fx.play_success(); self.app.refresh_all(); self.destroy()
            except Exception as e: sound_fx.play_error(); messagebox.showerror("Error", f"{t('cht_err')} {e}")
                
    def create_scratch(self): self.destroy(); CheatEditorModal(self.master, self.app, self.cht_folder)

class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app; self.grid_columnconfigure((0,1,2), weight=1)
        ctk.CTkLabel(self, text=t("tab_dash"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))
        def make_card(r, c, title, var_name, color):
            frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
            frm.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(frm, text=title, font=("Segoe UI", 10, "bold"), text_color=cfg.get_color("text_muted")).pack(anchor="w", padx=15, pady=(15,0))
            lbl = ctk.CTkLabel(frm, text="0", font=("Consolas", 24), text_color=color); lbl.pack(anchor="w", padx=15, pady=(0, 15)); setattr(self, var_name, lbl)
        make_card(1, 0, t("dash_games"), "lbl_games", cfg.get_color("accent"))
        make_card(1, 1, t("dash_usb"), "lbl_usb", cfg.get_color("success"))
        make_card(1, 2, t("dash_size"), "lbl_size", cfg.get_color("text_main"))

    def refresh(self):
        self.app.library.sync(); st = self.app.library.stats()
        self.lbl_games.configure(text=str(st['total'])); self.lbl_size.configure(text=st['size_str'])
        self.lbl_usb.configure(text=str(len(DriveManager.get_drives())))

class GamesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app; self.grid_rowconfigure(2, weight=1); self.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(self, fg_color="transparent"); head.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(head, text=t("tab_lib"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(side="left")
        ctk.CTkButton(head, text=t("lib_scan"), font=("Segoe UI", 11, "bold"), height=28, fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.scan).pack(side="right")
        search_frm = ctk.CTkFrame(self, fg_color="transparent"); search_frm.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.ent_search = ctk.CTkEntry(search_frm, placeholder_text=t("lib_search"), font=("Segoe UI", 11), height=28, width=250, fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.ent_search.pack(side="left")
        self.ent_search.bind("<KeyRelease>", self._filter)
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent"); self.list.grid(row=2, column=0, sticky="nsew")

    def refresh(self): self.app.library.sync(); self._filter()
    def _filter(self, e=None):
        q = self.ent_search.get().lower(); [w.destroy() for w in self.list.winfo_children()]
        filtered = [g for g in self.app.library.games if not q or q in g.get('name', '').lower()]
        if not cfg.data.get("animations", True): [HoverCard(self.list, g, lambda x: GameDetailsModal(self.app, x)).pack(fill="x", pady=2) for g in filtered]; return
        def add_card(idx):
            if idx < len(filtered):
                try: HoverCard(self.list, filtered[idx], lambda x: GameDetailsModal(self.app, x)).pack(fill="x", pady=2); self.app.after(30, lambda: add_card(idx+1))
                except: pass
        add_card(0)

    def scan(self):
        d = filedialog.askdirectory()
        if d: threading.Thread(target=self._do_scan, args=(d,), daemon=True).start()

    def _do_scan(self, d):
        target_dirs = [os.path.join(d, "DVD"), os.path.join(d, "CD")]
        target_dirs = [x for x in target_dirs if os.path.exists(x)]
        if not target_dirs: target_dirs = [d]
        for target in target_dirs:
            for r, ds, fs in os.walk(target):
                for f in fs:
                    if f.lower().endswith(('.iso', '.bin', '.img', '.zso')): self.app.library.add(GameAnalyzer.analyze(os.path.join(r, f)))
        self.app.after(0, self.refresh); self.app.after(0, lambda: [sound_fx.play_success(), messagebox.showinfo("Done", t("lib_scan_done"))])

class EmulatorTestPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_emu"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        card = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border")); card.grid(row=1, column=0, sticky="nsew", pady=10)
        ctk.CTkLabel(card, text=t("emu_sel"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_muted")).pack(pady=(25, 10))
        self.var_game = ctk.StringVar(value="None")
        self.cmb_game = ctk.CTkOptionMenu(card, variable=self.var_game, values=["None"], font=("Segoe UI", 12), height=35, fg_color=cfg.get_color("bg_main"), button_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_game.pack(fill="x", padx=40, pady=10)
        ctk.CTkButton(card, text=t("emu_btn"), font=("Segoe UI", 12, "bold"), height=40, fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.launch).pack(pady=30)
        ctk.CTkLabel(card, text=t("emu_info"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted")).pack(pady=(10, 20))

    def refresh(self):
        games = [g['name'] for g in self.app.library.games] if self.app.library.games else ["None"]
        self.cmb_game.configure(values=games)
        if self.var_game.get() not in games: self.var_game.set(games[0])

    def launch(self):
        g = next((g for g in self.app.library.games if g['name'] == self.var_game.get()), None)
        if g: PCSX2Integration.test_iso(g['path'], lambda e: messagebox.showerror("Error", e))

class AppsManagerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_apps"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(frm, text=t("app_name"), font=("Segoe UI", 11)).pack(anchor="w", padx=20, pady=(20, 5))
        self.ent_name = ctk.CTkEntry(frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_name.pack(fill="x", padx=20)
        ctk.CTkLabel(frm, text=t("app_elf"), font=("Segoe UI", 11)).pack(anchor="w", padx=20, pady=(15, 5))
        btn_frm = ctk.CTkFrame(frm, fg_color="transparent"); btn_frm.pack(fill="x", padx=20)
        self.ent_elf = ctk.CTkEntry(btn_frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_elf.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(btn_frm, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left", padx=10)
        ctk.CTkLabel(frm, text=t("app_drv"), font=("Segoe UI", 11)).pack(anchor="w", padx=20, pady=(15, 5))
        self.var_usb = ctk.StringVar(value="None")
        self.cmb_usb = ctk.CTkOptionMenu(frm, variable=self.var_usb, values=["None"], fg_color=cfg.get_color("bg_main"), button_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_usb.pack(fill="x", padx=20)
        ctk.CTkButton(frm, text=t("app_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=self.install).pack(pady=30)

    def refresh(self):
        drives = DriveManager.get_drives()
        vals = [d['device'] for d in drives] if drives else ["None"]
        self.cmb_usb.configure(values=vals)
        if self.var_usb.get() not in vals: self.var_usb.set(vals[0])

    def browse(self):
        f = filedialog.askopenfilename(filetypes=[("ELF Executable", "*.elf")])
        if f: self.ent_elf.delete(0, 'end'); self.ent_elf.insert(0, f)

    def install(self):
        if not self.ent_name.get() or not self.ent_elf.get() or self.var_usb.get() == "None": return
        res = OplAppsManager.install_app(self.ent_name.get(), self.ent_elf.get(), self.var_usb.get())
        if res is True: sound_fx.play_success(); messagebox.showinfo("Success", t("app_succ"))
        else: sound_fx.play_error(); messagebox.showerror("Error", res)

class IsoExtractorPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_iso"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="nsew")
        self.seg = ctk.CTkSegmentedButton(frm, values=[t("iso_mode_ext"), t("iso_mode_rep"), t("iso_mode_zso"), t("iso_mode_bin")], command=self.mode_changed); self.seg.pack(pady=20, padx=20, fill="x"); self.seg.set(t("iso_mode_ext"))
        ctk.CTkLabel(frm, text=t("iso_file"), font=("Segoe UI", 11)).pack(anchor="w", padx=20)
        src_frm = ctk.CTkFrame(frm, fg_color="transparent"); src_frm.pack(fill="x", padx=20, pady=(0, 15))
        self.ent_src = ctk.CTkEntry(src_frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_src.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(src_frm, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=self.browse_src).pack(side="left", padx=10)
        ctk.CTkLabel(frm, text=t("iso_out"), font=("Segoe UI", 11)).pack(anchor="w", padx=20)
        dst_frm = ctk.CTkFrame(frm, fg_color="transparent"); dst_frm.pack(fill="x", padx=20, pady=(0, 15))
        self.ent_dst = ctk.CTkEntry(dst_frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_dst.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dst_frm, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=self.browse_dst).pack(side="left", padx=10)
        self.cmb_zso_level = ctk.CTkComboBox(frm, values=["Fast (Faster, Larger)", "Ultra (Slower, Smaller)"], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry"))
        self.btn = ctk.CTkButton(frm, text=t("iso_btn_ext"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.process); self.btn.pack(pady=20)
        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent")); self.prog.pack(fill="x", padx=20); self.prog.set(0)
        self.lbl_wait = ctk.CTkLabel(frm, text=t("iso_wait"), font=("Segoe UI", 10, "italic"), text_color=cfg.get_color("warning")); self.lbl_wait.pack(pady=(10, 20), padx=20)

    def mode_changed(self, val):
        if val == t("iso_mode_zso"): self.cmb_zso_level.pack(fill="x", padx=20, pady=(0, 10)); self.btn.configure(text=t("iso_btn_zso"))
        else:
            self.cmb_zso_level.pack_forget()
            if val == t("iso_mode_ext"): self.btn.configure(text=t("iso_btn_ext"))
            elif val == t("iso_mode_rep"): self.btn.configure(text=t("iso_btn_rep"))
            else: self.btn.configure(text=t("iso_btn_bin"))
        self.ent_src.delete(0, 'end'); self.ent_dst.delete(0, 'end'); self.prog.set(0)

    def browse_src(self):
        mode = self.seg.get()
        if mode == t("iso_mode_ext"): f = filedialog.askopenfilename(filetypes=[("Disc Images", "*.iso")]); self.ent_src.delete(0, 'end'); self.ent_src.insert(0, f); self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, os.path.splitext(f)[0] + "_extracted") if f else None
        elif mode == t("iso_mode_rep"): d = filedialog.askdirectory(); self.ent_src.delete(0, 'end'); self.ent_src.insert(0, d); self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, d + ".iso") if d else None
        elif mode == t("iso_mode_zso"): f = filedialog.askopenfilename(filetypes=[("ISO File", "*.iso")]); self.ent_src.delete(0, 'end'); self.ent_src.insert(0, f); self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, os.path.splitext(f)[0] + ".zso") if f else None
        else: f = filedialog.askopenfilename(filetypes=[("BIN File", "*.bin")]); self.ent_src.delete(0, 'end'); self.ent_src.insert(0, f); self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, os.path.splitext(f)[0] + ".iso") if f else None

    def browse_dst(self):
        mode = self.seg.get()
        if mode == t("iso_mode_ext"): d = filedialog.askdirectory(); self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, d) if d else None
        elif mode == t("iso_mode_rep") or mode == t("iso_mode_bin"): f = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[("ISO File", "*.iso")]); self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, f) if f else None
        else: f = filedialog.asksaveasfilename(defaultextension=".zso", filetypes=[("ZSO Compressed", "*.zso")]); self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, f) if f else None

    def process(self):
        src, dst = self.ent_src.get().strip(), self.ent_dst.get().strip()
        if not src or not dst: sound_fx.play_error(); messagebox.showerror("Error", t("iso_empty")); return
        self.btn.configure(state="disabled"); self.prog.set(0)
        p_cb = lambda v: self.app.after(0, lambda: self.prog.set(v))
        d_cb = lambda s: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo("Success", t("iso_succ"))])
        e_cb = lambda e: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_error(), messagebox.showerror("Error", f"{t('iso_err')}{e}")])
        mode = self.seg.get()
        if mode == t("iso_mode_ext"): RealIsoTool.extract(src, dst, p_cb, d_cb, e_cb)
        elif mode == t("iso_mode_rep"): RealIsoTool.repack(src, dst, p_cb, d_cb, e_cb)
        elif mode == t("iso_mode_zso"): RealIsoTool.compress_zso(src, dst, self.cmb_zso_level.get(), p_cb, d_cb, e_cb)
        else: BinConverter.convert(src, dst, p_cb, d_cb, e_cb, ps1_mode=True)

class IsoPatcherPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_patcher"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(frm, text=t("patch_iso"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        f1 = ctk.CTkFrame(frm, fg_color="transparent"); f1.pack(fill="x", padx=20)
        self.ent_iso = ctk.CTkEntry(f1, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_iso.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f1, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=lambda: self.browse(self.ent_iso, [("ISO Files", "*.iso")])).pack(side="left", padx=10)
        ctk.CTkLabel(frm, text=t("patch_file"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        f2 = ctk.CTkFrame(frm, fg_color="transparent"); f2.pack(fill="x", padx=20)
        self.ent_patch = ctk.CTkEntry(f2, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_patch.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f2, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=lambda: self.browse(self.ent_patch, [("Patch Files", "*.ips *.bps *.xdelta")])).pack(side="left", padx=10)
        ctk.CTkLabel(frm, text=t("patch_out"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        f3 = ctk.CTkFrame(frm, fg_color="transparent"); f3.pack(fill="x", padx=20)
        self.ent_out = ctk.CTkEntry(f3, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_out.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f3, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=lambda: self.browse(self.ent_out, [("ISO Files", "*.iso")], save=True)).pack(side="left", padx=10)
        self.chk_region = ctk.CTkCheckBox(frm, text=t("patch_reg"), font=("Segoe UI", 12), text_color=cfg.get_color("warning"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("card")); self.chk_region.pack(anchor="w", padx=20, pady=(25, 10))
        self.btn = ctk.CTkButton(frm, text=t("patch_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=self.process); self.btn.pack(pady=25)
        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent")); self.prog.pack(fill="x", padx=20, pady=(0, 20)); self.prog.set(0)

    def browse(self, entry_widget, ftypes, save=False):
        f = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=ftypes) if save else filedialog.askopenfilename(filetypes=ftypes)
        if f: entry_widget.delete(0, 'end'); entry_widget.insert(0, f)

    def process(self):
        if not self.ent_iso.get() or not self.ent_patch.get() or not self.ent_out.get(): return
        self.btn.configure(state="disabled"); self.prog.set(0)
        TranslationPatcher.patch_iso(self.ent_iso.get().strip(), self.ent_out.get().strip(), self.ent_patch.get().strip(), self.chk_region.get(), 
            lambda v: self.app.after(0, lambda: self.prog.set(v)), 
            lambda s: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo("Success", "Patch applied!")]), 
            lambda e: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_error(), messagebox.showerror("Error", e)])
        )

class UtilSplitterPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_util"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(frm, text=t("util_iso"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        src_frm = ctk.CTkFrame(frm, fg_color="transparent"); src_frm.pack(fill="x", padx=20)
        self.ent_src = ctk.CTkEntry(src_frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_src.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(src_frm, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=self.browse_src).pack(side="left", padx=10)
        ctk.CTkLabel(frm, text=t("util_dst"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        dst_frm = ctk.CTkFrame(frm, fg_color="transparent"); dst_frm.pack(fill="x", padx=20)
        self.ent_dst = ctk.CTkEntry(dst_frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_dst.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dst_frm, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=self.browse_dst).pack(side="left", padx=10)
        ctk.CTkLabel(frm, text=t("util_name"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.ent_name = ctk.CTkEntry(frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_name.pack(fill="x", padx=20)
        self.btn = ctk.CTkButton(frm, text=t("util_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.process); self.btn.pack(pady=30)
        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent")); self.prog.pack(fill="x", padx=20, pady=(0, 20)); self.prog.set(0)

    def browse_src(self):
        f = filedialog.askopenfilename(filetypes=[("ISO File", "*.iso")])
        if f: self.ent_src.delete(0, 'end'); self.ent_src.insert(0, f); self.ent_name.delete(0, 'end'); self.ent_name.insert(0, os.path.splitext(os.path.basename(f))[0][:32])

    def browse_dst(self):
        d = filedialog.askdirectory()
        if d: self.ent_dst.delete(0, 'end'); self.ent_dst.insert(0, d)

    def process(self):
        if not self.ent_src.get() or not self.ent_dst.get() or not self.ent_name.get(): return
        self.btn.configure(state="disabled"); self.prog.set(0)
        USBUtilWorker.split_and_generate(self.ent_src.get().strip(), self.ent_dst.get().strip(), self.ent_name.get().strip(), lambda v: self.app.after(0, lambda: self.prog.set(v)), lambda s: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo("Success", t("util_succ"))]), lambda e: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_error(), messagebox.showerror("Error", e)]))

class DvdRipperPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_rip"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(frm, text=t("disc_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.cmb_drv = ctk.CTkComboBox(frm, values=["Detecting..."], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_drv.pack(fill="x", padx=20)
        ctk.CTkLabel(frm, text=t("rip_out"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        out_frm = ctk.CTkFrame(frm, fg_color="transparent"); out_frm.pack(fill="x", padx=20)
        self.ent_out = ctk.CTkEntry(out_frm, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry")); self.ent_out.pack(side="left", fill="x", expand=True); self.ent_out.insert(0, os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop"))
        ctk.CTkButton(out_frm, text="BROWSE", width=80, corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left", padx=10)
        ctk.CTkLabel(frm, text=t("rip_fmt"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.cmb_fmt = ctk.CTkComboBox(frm, values=[t("rip_orig"), t("rip_fiso")], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_fmt.pack(fill="x", padx=20)
        self.btn_rip = ctk.CTkButton(frm, text=t("rip_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.rip); self.btn_rip.pack(pady=30)
        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent")); self.prog.pack(fill="x", padx=20, pady=(0, 20)); self.prog.set(0)

    def browse(self):
        d = filedialog.askdirectory()
        if d: self.ent_out.delete(0, 'end'); self.ent_out.insert(0, d)
    def refresh(self):
        drives = PhysicalDriveRipper.get_optical_drives()
        vals = drives if drives else ["No CD/DVD Drive Found"]
        self.cmb_drv.configure(values=vals)
        if self.cmb_drv.get() not in vals: self.cmb_drv.set(vals[0])
    def rip(self):
        if not self.cmb_drv.get() or self.cmb_drv.get() == "No CD/DVD Drive Found" or not os.path.exists(self.ent_out.get()): return
        self.btn_rip.configure(state="disabled"); self.prog.set(0)
        PhysicalDriveRipper.rip_drive(self.cmb_drv.get(), self.ent_out.get(), self.cmb_fmt.get() == t("rip_fiso"), lambda v: self.app.after(0, lambda: self.prog.set(v)), lambda p: self.app.after(0, lambda: [self.btn_rip.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo("Done", f"Media ripped:\n{p}")]), lambda e: self.app.after(0, lambda: [self.btn_rip.configure(state="normal"), sound_fx.play_error(), messagebox.showerror("Error", e)]))

class DiscAnalyzerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_disc"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(frm, text=t("disc_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.cmb_drv = ctk.CTkComboBox(frm, values=["Detecting..."], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_drv.pack(fill="x", padx=20)
        ctk.CTkButton(frm, text=t("disc_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.analyze).pack(pady=20)
        self.txt_info = ctk.CTkTextbox(frm, font=("Consolas", 12), height=150, fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("entry")); self.txt_info.pack(fill="x", padx=20, pady=(0, 20))

    def refresh(self):
        drives = PhysicalDriveRipper.get_optical_drives()
        vals = drives if drives else [t("disc_none")]
        self.cmb_drv.configure(values=vals)
        if self.cmb_drv.get() not in vals: self.cmb_drv.set(vals[0])
    def analyze(self):
        if not self.cmb_drv.get() or self.cmb_drv.get() == t("disc_none"): return
        self.txt_info.configure(state="normal"); self.txt_info.delete("1.0", "end"); self.txt_info.insert("end", "Reading disc...\n"); self.txt_info.configure(state="disabled")
        def run():
            info = PhysicalDriveRipper.analyze_disc(self.cmb_drv.get())
            out = f"--- OPTICAL DISC BINARY ANALYSIS ---\n\nDrive Letter:  {self.cmb_drv.get()}\nDisc Status:   {info['status']}\nTotal Size:    {info['size_str']}\nOfficial ID:   {info['game_id']}\nRegion Code:   {info['region']}\n"
            self.app.after(0, lambda: [self.txt_info.configure(state="normal"), self.txt_info.delete("1.0", "end"), self.txt_info.insert("end", out), self.txt_info.configure(state="disabled"), sound_fx.play_success() if info['game_id'] != 'Error' else sound_fx.play_error()])
        threading.Thread(target=run, daemon=True).start()

class USBPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_rowconfigure(2, weight=1); self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_usb"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        top = ctk.CTkFrame(self, fg_color="transparent"); top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.var_usb = ctk.StringVar(value="None")
        self.cmb_usb = ctk.CTkOptionMenu(top, variable=self.var_usb, values=["None"], font=("Consolas", 11), fg_color=cfg.get_color("bg_main"), button_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry"), command=self.analyze); self.cmb_usb.pack(side="left")
        ctk.CTkButton(top, text=t("usb_ref"), font=("Segoe UI", 10, "bold"), width=70, fg_color=cfg.get_color("border"), corner_radius=cfg.get_radius("button"), command=self.refresh).pack(side="left", padx=10)
        self.info = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); self.info.grid(row=2, column=0, sticky="nsew")
        self.lbl_drive = ctk.CTkLabel(self.info, text=t("usb_nodrv"), font=("Segoe UI", 14, "bold"), text_color=cfg.get_color("text_main")); self.lbl_drive.pack(anchor="w", padx=20, pady=(20, 5))
        self.lbl_space = ctk.CTkLabel(self.info, text="", font=("Consolas", 11), text_color=cfg.get_color("text_muted")); self.lbl_space.pack(anchor="w", padx=20)
        self.prog = ctk.CTkProgressBar(self.info, height=12 if cfg.data.get("beta_ui") else 8, progress_color=cfg.get_color("accent"), fg_color=cfg.get_color("bg_main")); self.prog.pack(fill="x", padx=20, pady=(10, 20)); self.prog.set(0)
        self.txt_opl = ctk.CTkTextbox(self.info, font=("Consolas", 11), fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), height=120, corner_radius=cfg.get_radius("entry")); self.txt_opl.pack(fill="x", padx=20, pady=5)

    def refresh(self):
        self.drives = DriveManager.get_drives()
        vals = [f"{d['device']} [{d['fstype']}]" for d in self.drives] if self.drives else ["None"]
        self.cmb_usb.configure(values=vals)
        if self.var_usb.get() not in vals: self.var_usb.set(vals[0])
        self.analyze(self.var_usb.get())

    def analyze(self, sel):
        if sel == "None": self.lbl_drive.configure(text=t("usb_nodrv")); self.prog.set(0); return
        drv = next((d for d in self.drives if d['device'] == sel.split(" ")[0]), None)
        if not drv: return
        self.lbl_drive.configure(text=f"DRIVE: {drv['device']}")
        self.lbl_space.configure(text=f"{t('usb_cap')} {format_size(drv['total'])} | {t('usb_free')} {format_size(drv['free'])}")
        self.prog.set(drv['percent'] / 100)
        res = DriveManager.analyze_opl_structure(drv['mountpoint'])
        out = f"STATUS: {res['status']}\n\n" + "".join([f"[{'OK' if v else 'MISSING'}] {k}/\n" for k, v in res['folders'].items()])
        self.txt_opl.configure(state="normal"); self.txt_opl.delete("1.0", "end"); self.txt_opl.insert("end", out); self.txt_opl.configure(state="disabled")

class ClonePage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("sub_clone")[2:], font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="nsew", pady=10)
        ctk.CTkLabel(frm, text=t("clone_src"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=20, pady=(20, 5))
        self.var_src = ctk.StringVar(value="None")
        self.cmb_src = ctk.CTkComboBox(frm, variable=self.var_src, values=["None"], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_src.pack(fill="x", padx=20)
        ctk.CTkLabel(frm, text=t("clone_dst"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("success")).pack(anchor="w", padx=20, pady=(20, 5))
        self.var_dst = ctk.StringVar(value="None")
        self.cmb_dst = ctk.CTkComboBox(frm, variable=self.var_dst, values=["None"], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_dst.pack(fill="x", padx=20)
        self.chk_fmt_dst = ctk.CTkCheckBox(frm, text=t("clone_fmt_dst"), font=("Segoe UI", 12), text_color=cfg.get_color("text_main"), fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("card")); self.chk_fmt_dst.pack(anchor="w", padx=20, pady=(25, 10))
        self.chk_fmt_src = ctk.CTkCheckBox(frm, text=t("clone_fmt_src"), font=("Segoe UI", 12), text_color=cfg.get_color("text_muted"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("card")); self.chk_fmt_src.pack(anchor="w", padx=20, pady=5)
        self.btn_clone = ctk.CTkButton(frm, text=t("clone_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.start_clone); self.btn_clone.pack(pady=30)
        self.log_clone = ctk.CTkTextbox(frm, font=("Consolas", 10), height=80, fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_muted"), corner_radius=cfg.get_radius("entry")); self.log_clone.pack(fill="x", padx=20, pady=(0, 20))

    def refresh(self):
        self.drives = DriveManager.get_drives()
        vals = [f"{d['device']} [{d['fstype']}]" for d in self.drives] if self.drives else ["None"]
        self.cmb_src.configure(values=vals); self.cmb_dst.configure(values=vals)

    def start_clone(self):
        src_val, dst_val = self.var_src.get().split(" ")[0], self.var_dst.get().split(" ")[0]
        if src_val == "None" or dst_val == "None" or src_val == dst_val: return
        src_d, dst_d = next((d for d in self.drives if d['device'] == src_val), None), next((d for d in self.drives if d['device'] == dst_val), None)
        self.app.active_transfers += 1
        worker = CloneWorker(src_d, dst_d, self.chk_fmt_dst.get(), self.chk_fmt_src.get(), {'log': lambda m: self.app.after(0, lambda: [self.log_clone.insert("end", m+"\n"), self.log_clone.see("end")]), 'prog_total': lambda v: None})
        threading.Thread(target=lambda: [worker.run(), setattr(self.app, 'active_transfers', self.app.active_transfers - 1)], daemon=True).start()

class MigratePage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=2); self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text=t("tab_mig"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        r = cfg.get_radius("card")
        ctrl = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=r); ctrl.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(ctrl, text=t("mig_drv"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_muted")).pack(anchor="w", padx=15, pady=(15,5))
        self.drv_var = ctk.StringVar(value="None")
        self.cmb_drv = ctk.CTkComboBox(ctrl, variable=self.drv_var, values=["None"], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_drv.pack(fill="x", padx=15)
        ctk.CTkLabel(ctrl, text=t("mig_fs"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_muted")).pack(anchor="w", padx=15, pady=(20,5))
        self.fs_var = ctk.StringVar(value="exFAT")
        ctk.CTkComboBox(ctrl, variable=self.fs_var, values=["exFAT", "FAT32"], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")).pack(fill="x", padx=15)
        ctk.CTkButton(ctrl, text=t("mig_btn"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"), command=self.start).pack(fill="x", padx=15, pady=30)
        ctk.CTkLabel(ctrl, text=t("mig_warn"), font=("Segoe UI", 10), text_color=cfg.get_color("warning"), justify="left").pack(anchor="w", padx=15)
        log_frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=r); log_frm.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        self.log_box = ctk.CTkTextbox(log_frm, font=("Consolas", 11), fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("entry")); self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh(self):
        self.drives = DriveManager.get_drives()
        vals = [f"{d['device']} [{d['fstype']}]" for d in self.drives] if self.drives else ["None"]
        self.cmb_drv.configure(values=vals)

    def start(self):
        drv = next((d for d in self.drives if d['device'] == self.drv_var.get().split(" ")[0]), None)
        if not drv or not messagebox.askyesno("Confirm", t("mig_conf")): return
        self.app.active_transfers += 1
        worker = MigrationWorker(drv, self.fs_var.get(), {'log': lambda m: self.app.after(0, lambda: [self.log_box.insert("end", m+"\n"), self.log_box.see("end")]), 'prog_total': lambda v: None, 'prog_step': lambda v: None, 'done': lambda s: self.app.after(0, lambda: [setattr(self.app, 'active_transfers', self.app.active_transfers - 1), self.app.refresh_all()])})
        threading.Thread(target=worker.run, daemon=True).start()

class CheatManagerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app, self.current_folder, self.selected_file = app, cfg.data.get("last_cht_folder", ""), None
        self.grid_rowconfigure(2, weight=1); self.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(self, fg_color="transparent"); head.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(head, text=t("tab_cht"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(side="left")
        folder_frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); folder_frm.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(folder_frm, text=t("cht_folder"), font=("Segoe UI", 11, "bold")).pack(side="left", padx=15, pady=10)
        self.ent_folder = ctk.CTkEntry(folder_frm, fg_color=cfg.get_color("bg_main"), height=28, corner_radius=cfg.get_radius("entry")); self.ent_folder.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)
        if self.current_folder: self.ent_folder.insert(0, self.current_folder)
        ctk.CTkButton(folder_frm, text="BROWSE", font=("Segoe UI", 11, "bold"), width=80, fg_color=cfg.get_color("border"), corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left", padx=(0, 15), pady=10)
        act_frm = ctk.CTkFrame(self, fg_color="transparent"); act_frm.grid(row=2, column=0, sticky="new", pady=(0, 10))
        r = cfg.get_radius("button")
        ctk.CTkButton(act_frm, text=t("cht_add"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("accent"), corner_radius=r, command=lambda: AddCheatModal(self, self.app, self.current_folder) if os.path.exists(self.current_folder) else messagebox.showerror("Error", "Select folder first")).pack(side="left", padx=(0, 5))
        ctk.CTkButton(act_frm, text=t("cht_edit"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("warning"), text_color="#000", corner_radius=r, command=lambda: CheatEditorModal(self, self.app, self.current_folder, self.selected_file) if self.selected_file else messagebox.showwarning("Warning", t("cht_none"))).pack(side="left", padx=5)
        ctk.CTkButton(act_frm, text=t("cht_enable"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("success"), corner_radius=r, command=self.enable_cheat).pack(side="left", padx=5)
        ctk.CTkButton(act_frm, text=t("cht_disable"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("danger"), corner_radius=r, command=self.disable_cheat).pack(side="left", padx=5)
        self.list_frm = ctk.CTkScrollableFrame(self, fg_color="transparent"); self.list_frm.grid(row=3, column=0, sticky="nsew"); self.grid_rowconfigure(3, weight=1); self.refresh()
        
    def browse(self):
        d = filedialog.askdirectory()
        if d: self.ent_folder.delete(0, 'end'); self.ent_folder.insert(0, d); self.current_folder = d; cfg.data["last_cht_folder"] = d; cfg.save(); self.refresh()
            
    def refresh(self):
        self.current_folder = self.ent_folder.get()
        if not os.path.exists(self.current_folder): return
        self.selected_file = None; [w.destroy() for w in self.list_frm.winfo_children()]
        try: [self.add_cheat_card(f) for f in os.listdir(self.current_folder) if f.lower().endswith((".cht", ".disabled"))]
        except: pass
        
    def add_cheat_card(self, filename):
        is_disabled = filename.lower().endswith(".disabled")
        color = cfg.get_color("danger") if is_disabled else cfg.get_color("success")
        card = ctk.CTkFrame(self.list_frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), height=36, border_width=cfg.get_border_width(), border_color=cfg.get_color("border")); card.pack(fill="x", pady=2); card.pack_propagate(False)
        card.grid_columnconfigure(1, weight=1); card.grid_rowconfigure(0, weight=1)
        ctk.CTkFrame(card, width=4, fg_color=color, corner_radius=0).grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ctk.CTkLabel(card, text=filename, font=("Consolas", 12, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(card, text="DISABLED" if is_disabled else "ENABLED", font=("Segoe UI", 10, "bold"), text_color=color).grid(row=0, column=2, sticky="e", padx=15)
        def on_click(e, f=filename, c=card):
            self.selected_file = os.path.join(self.current_folder, f)
            [w.configure(fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border")) for w in self.list_frm.winfo_children()]
            c.configure(fg_color=cfg.get_color("card_hover"), border_color=cfg.get_color("accent")); sound_fx.play_click()
        card.bind("<Button-1>", on_click); [child.bind("<Button-1>", on_click) for child in card.winfo_children()]
        
    def enable_cheat(self):
        if self.selected_file and self.selected_file.endswith(".disabled"):
            try: os.rename(self.selected_file, self.selected_file[:-9]); sound_fx.play_success(); self.refresh()
            except Exception as e: messagebox.showerror("Error", str(e))
            
    def disable_cheat(self):
        if self.selected_file and self.selected_file.endswith(".cht"):
            try: os.rename(self.selected_file, self.selected_file + ".disabled"); sound_fx.play_success(); self.refresh()
            except Exception as e: messagebox.showerror("Error", str(e))

class OplArtDownloaderPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent"); top.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(top, text=t("art_title"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(side="left")
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(frm, text=t("art_desc"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted"), wraplength=500, justify="left").pack(anchor="w", padx=20, pady=(15, 10))
        ctk.CTkLabel(frm, text=t("art_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(5, 5))
        drv_frm = ctk.CTkFrame(frm, fg_color="transparent"); drv_frm.pack(fill="x", padx=20)
        self.cmb_drv = ctk.CTkComboBox(drv_frm, values=["Scanning..."], fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_drv.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(drv_frm, text="BROWSE FOLDER", width=120, fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("button"), command=lambda: self.cmb_drv.set(filedialog.askdirectory() or self.cmb_drv.get())).pack(side="left", padx=10)
        act_frm = ctk.CTkFrame(frm, fg_color="transparent"); act_frm.pack(fill="x", padx=20, pady=(15, 10))
        self.btn_scan = ctk.CTkButton(act_frm, text=t("art_scan"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.scan_games); self.btn_scan.pack(side="left", expand=True, padx=(0,5))
        self.btn_dl = ctk.CTkButton(act_frm, text=t("art_dl"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), state="disabled", command=self.download_art); self.btn_dl.pack(side="left", expand=True, padx=(5,0))
        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent")); self.prog.pack(fill="x", padx=20, pady=(10, 15)); self.prog.set(0)
        log_frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); log_frm.grid(row=2, column=0, sticky="nsew", pady=(10,0))
        self.log_box = ctk.CTkTextbox(log_frm, font=("Consolas", 11), fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("entry")); self.log_box.pack(fill="both", expand=True, padx=10, pady=10); self.log_box.insert("end", "Waiting for scan...\n")
        self.detected_ids = []

    def refresh(self):
        drives = DriveManager.get_drives()
        vals = [d['mountpoint'] for d in drives] if drives else ["None"]
        self.cmb_drv.configure(values=vals)
        if self.cmb_drv.get() not in vals: self.cmb_drv.set(vals[0])

    def append_log(self, text): self.log_box.insert("end", text + "\n"); self.log_box.see("end")

    def scan_games(self):
        mp = self.cmb_drv.get()
        if not mp or mp == "None": return
        self.log_box.delete("1.0", "end"); self.append_log(f"Scanning directory {mp} for OPL structure and ISOs..."); self.btn_scan.configure(state="disabled"); self.prog.set(0.2)
        threading.Thread(target=lambda: self.app.after(0, lambda: self.on_scan_done(ArtScraperWorker.scan_for_ids(mp))), daemon=True).start()
        
    def on_scan_done(self, ids):
        self.prog.set(1.0); self.btn_scan.configure(state="normal"); self.detected_ids = ids
        if ids:
            self.append_log(f"\nScan complete! Found {len(ids)} unique Game IDs:")
            [self.append_log(f" - {gid} -> {ArtScraperWorker.format_opl_id(gid)}") for gid in ids]
            self.btn_dl.configure(state="normal"); sound_fx.play_success()
        else: self.append_log("\nNo valid PS2 games found."); self.btn_dl.configure(state="disabled"); sound_fx.play_error()

    def download_art(self):
        if not self.detected_ids: return
        self.btn_dl.configure(state="disabled"); self.btn_scan.configure(state="disabled"); self.prog.set(0)
        self.append_log("\nConnecting to high-res PS2 databases (GitHub Raw)...")
        ArtScraperWorker.download_art(self.cmb_drv.get(), self.detected_ids, lambda v: self.app.after(0, lambda: self.prog.set(v)), lambda s: self.app.after(0, lambda: [self.btn_dl.configure(state="normal"), self.btn_scan.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo("Success", "Art downloaded!")]), lambda e: self.app.after(0, lambda: [self.btn_dl.configure(state="normal"), self.btn_scan.configure(state="normal"), sound_fx.play_error(), messagebox.showerror("Error", e)]), lambda m: self.app.after(0, lambda: self.append_log(m)))

class ApaExplorerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent"); top.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(top, text=t("apa_title"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(side="left")
        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); frm.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(frm, text=t("apa_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        drv_frm = ctk.CTkFrame(frm, fg_color="transparent"); drv_frm.pack(fill="x", padx=20)
        self.cmb_drv = ctk.CTkComboBox(drv_frm, values=["Scanning..."], command=self.load_partitions, fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")); self.cmb_drv.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(drv_frm, text="BROWSE IMG", width=100, fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("button"), command=self.browse_img).pack(side="left", padx=10)
        act_frm = ctk.CTkFrame(frm, fg_color="transparent"); act_frm.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkButton(act_frm, text=t("apa_btn_raw"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=self.do_raw).pack(side="left", expand=True, padx=(0,5))
        ctk.CTkButton(act_frm, text=t("apa_btn_rest"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("warning"), text_color="#000", corner_radius=cfg.get_radius("button"), command=self.do_restore).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(act_frm, text=t("apa_btn_ext"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"), command=self.do_ext).pack(side="left", expand=True, padx=(5,0))
        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent")); self.prog.pack(fill="x", padx=20, pady=(10, 15)); self.prog.set(0)
        exp_frm = ctk.CTkFrame(self, fg_color="transparent"); exp_frm.grid(row=2, column=0, sticky="nsew", pady=(10,0)); exp_frm.grid_columnconfigure(0, weight=1); exp_frm.grid_columnconfigure(1, weight=2); exp_frm.grid_rowconfigure(0, weight=1)
        self.list_parts = ctk.CTkScrollableFrame(exp_frm, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card")); self.list_parts.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        self.view_files = ctk.CTkTextbox(exp_frm, font=("Consolas", 11), fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("card")); self.view_files.grid(row=0, column=1, sticky="nsew", padx=(5,0))

    def refresh(self):
        def r():
            drives = APAManager.list_physical_drives()
            vals = drives if drives else ["No Physical Drives Found"]
            self.app.after(0, lambda: self.cmb_drv.configure(values=vals))
            if self.cmb_drv.get() not in vals and not self.cmb_drv.get().endswith(".img"): self.app.after(0, lambda: self.cmb_drv.set(vals[0]))
            self.app.after(0, lambda: self.load_partitions(self.cmb_drv.get()))
        threading.Thread(target=r, daemon=True).start()

    def browse_img(self):
        f = filedialog.askopenfilename(filetypes=[("Disk Image", "*.img *.vhd *.raw")])
        if f: self.cmb_drv.set(f); self.load_partitions(f)

    def load_partitions(self, drive_sel):
        if not drive_sel or "No Physical" in drive_sel: return
        src = "\\\\.\\" + drive_sel.split(" (")[0] if not drive_sel.split(" (")[0].endswith(".img") and not drive_sel.split(" (")[0].endswith(".vhd") else drive_sel.split(" (")[0]
        [w.destroy() for w in self.list_parts.winfo_children()]
        self.view_files.configure(state="normal"); self.view_files.delete("1.0", "end"); self.view_files.insert("end", f"Scanning APA Sectors on {src}...\n\n"); self.view_files.configure(state="disabled")
        threading.Thread(target=lambda: self.app.after(0, lambda: self.render_parts(APAManager.read_apa_partitions(src), src)), daemon=True).start()

    def render_parts(self, parts, src):
        [w.destroy() for w in self.list_parts.winfo_children()]
        self.view_files.configure(state="normal"); self.view_files.delete("1.0", "end")
        self.view_files.insert("end", f"Found {len(parts)} APA Partitions." if parts else "[!] No APA signature detected.")
        self.view_files.configure(state="disabled")
        for p in parts: ctk.CTkButton(self.list_parts, text=p['id'], font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"), hover_color=cfg.get_color("accent"), anchor="w", corner_radius=cfg.get_radius("button"), command=lambda part=p, s=src: self.show_part_details(part, s)).pack(fill="x", pady=2, padx=2)

    def show_part_details(self, part, src):
        self.view_files.configure(state="normal"); self.view_files.delete("1.0", "end")
        self.view_files.insert("end", f"=== PARTITION: {part['id']} ===\nOffset: {part['offset']} bytes\nSize: {part['size_str']}\nType: {hex(part['type'])}\n\n")
        if part['id'] == "+OPL":
            try:
                with open(src, 'rb') as f:
                    f.seek(part['offset'] + 1024); data = f.read(2048).decode('utf-8', 'ignore')
                    if "DIR:" in data or "FILE:" in data:
                        self.view_files.insert("end", "--- PFS VIRTUAL TREE ---\n")
                        [self.view_files.insert("end", l.strip() + "\n") for l in data.split('\n') if l.strip()]
                    else: self.view_files.insert("end", "[!] PFS Data encrypted.")
            except Exception as e: self.view_files.insert("end", f"[!] Error: {e}")
        elif part['is_game']: self.view_files.insert("end", "--- PS2 HDL GAME DATA ---\nThis partition contains raw ISO sectors.\nUse 'Extract Content'.")
        self.view_files.configure(state="disabled")

    def do_raw(self):
        src = self.cmb_drv.get().split(" (")[0]
        if "No Physical" in src: return
        f = filedialog.asksaveasfilename(defaultextension=".img", filetypes=[("Image File", "*.img")])
        if not f: return
        self.prog.set(0)
        src = "\\\\.\\" + src if not src.endswith(".img") and not src.endswith(".vhd") else src
        APAManager.backup_raw(src, f, lambda v: self.app.after(0, lambda: self.prog.set(v)), lambda s: self.app.after(0, lambda: messagebox.showinfo("Done", "Backup Complete!")), lambda e: self.app.after(0, lambda: messagebox.showerror("Error", e)))

    def do_restore(self):
        src_img = filedialog.askopenfilename(filetypes=[("Image File", "*.img *.vhd")])
        dest = self.cmb_drv.get().split(" (")[0]
        if not src_img or "No Physical" in dest or dest.endswith(".img"): return
        if messagebox.askyesno("WARNING", f"OVERWRITE ALL DATA ON {dest}?"): self.prog.set(0); APAManager.restore_raw(src_img, "\\\\.\\" + dest, lambda v: self.app.after(0, lambda: self.prog.set(v)), lambda s: self.app.after(0, lambda: messagebox.showinfo("Done", "Restore Complete!")), lambda e: self.app.after(0, lambda: messagebox.showerror("Error", e)))

    def do_ext(self):
        src = self.cmb_drv.get().split(" (")[0]
        if "No Physical" in src: return
        src = "\\\\.\\" + src if not src.endswith(".img") and not src.endswith(".vhd") else src
        d = filedialog.askdirectory()
        if d: self.prog.set(0); APAManager.extract_contents(src, d, lambda v: self.app.after(0, lambda: self.prog.set(v)), lambda s: self.app.after(0, lambda: messagebox.showinfo("Done", "Extraction Complete!")), lambda e: self.app.after(0, lambda: messagebox.showerror("Error", e)))

class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent"); self.app = app; self.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(self, text=t("tab_set"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        frm_left = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border")); frm_left.grid(row=1, column=0, sticky="nsew", padx=(0,5))
        ctk.CTkLabel(frm_left, text=t("set_lang"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=15, pady=(15, 5))
        self.lang_var = ctk.StringVar(value=cfg.data.get("language", "EN"))
        ctk.CTkOptionMenu(frm_left, variable=self.lang_var, values=["EN", "PT", "ES"], command=lambda c: [cfg.data.update({"language": c}), cfg.save(), self.app.after(100, self.app.refresh_all_ui)], fg_color=cfg.get_color("bg_main"), button_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkLabel(frm_left, text="THEME", font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=15, pady=(15, 5))
        self.theme_var = ctk.StringVar(value=cfg.data.get("theme", "Dark"))
        ctk.CTkOptionMenu(frm_left, variable=self.theme_var, values=list(THEMES.keys()), command=lambda c: [cfg.data.update({"theme": c}), cfg.save(), self.app.after(100, self.app.refresh_all_ui)], fg_color=cfg.get_color("bg_main"), button_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkLabel(frm_left, text=t("set_beh"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=15, pady=(15, 5))
        self.snd_var, self.bgm_var, self.anim_var, self.sync_var = ctk.BooleanVar(value=cfg.data.get("sound_enabled", True)), ctk.BooleanVar(value=cfg.data.get("bgm_enabled", True)), ctk.BooleanVar(value=cfg.data.get("animations", True)), ctk.BooleanVar(value=cfg.data.get("auto_sync", True))
        def sv(): cfg.data.update({"sound_enabled": self.snd_var.get(), "bgm_enabled": self.bgm_var.get(), "animations": self.anim_var.get(), "auto_sync": self.sync_var.get()}); cfg.save(); sound_fx.enabled = self.snd_var.get(); sound_fx.update_bgm(self.bgm_var.get())
        ctk.CTkSwitch(frm_left, text=t("set_snd"), font=("Segoe UI", 11), variable=self.snd_var, command=sv).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkSwitch(frm_left, text=t("set_bgm"), font=("Segoe UI", 11), variable=self.bgm_var, command=sv).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkSwitch(frm_left, text=t("set_anim"), font=("Segoe UI", 11), variable=self.anim_var, command=sv).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkSwitch(frm_left, text=t("set_sync"), font=("Segoe UI", 11), variable=self.sync_var, command=sv).pack(anchor="w", padx=15, pady=(0, 10))
        self.beta_var = ctk.BooleanVar(value=cfg.data.get("beta_ui", False))
        ctk.CTkSwitch(frm_left, text=t("set_beta"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("accent"), variable=self.beta_var, command=lambda: [cfg.data.update({"beta_ui": self.beta_var.get()}), cfg.save(), self.app.after(100, self.app.refresh_all_ui)]).pack(anchor="w", padx=15, pady=(0, 10))
        self.cmd_var = ctk.BooleanVar(value=cfg.data.get("show_console", False))
        ctk.CTkSwitch(frm_left, text=t("set_cmd"), font=("Segoe UI", 11), variable=self.cmd_var, command=lambda: [cfg.data.update({"show_console": self.cmd_var.get()}), cfg.save(), messagebox.showinfo("Restart Required", t("msg_restart"))]).pack(anchor="w", padx=15, pady=(0, 20))
        frm_right = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border")); frm_right.grid(row=1, column=1, sticky="nsew", padx=(5,0))
        ctk.CTkLabel(frm_right, text="SYSTEM & TOOLS", font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("warning")).pack(anchor="w", padx=15, pady=(15, 10))
        r = cfg.get_radius("button")
        ctk.CTkButton(frm_right, text=t("set_rate"), font=("Segoe UI", 11, "bold"), fg_color="#D97706", hover_color="#B45309", text_color="#FFFFFF", corner_radius=r, command=lambda: webbrowser.open("https://docs.google.com/forms/d/e/1FAIpQLSdV8WZMSQGHtGOnhsdI1mxxAwzIdifNLrkBN1adfvRR9vDkYQ/viewform?usp=publish-editor")).pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(frm_right, text=t("ver_btn"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("bg_main"), border_width=1, border_color=cfg.get_color("warning"), text_color=cfg.get_color("text_main"), corner_radius=r, command=lambda: VersionRollbackModal(self.app)).pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(frm_right, text=t("set_log"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("bg_main"), border_width=1, border_color=cfg.get_color("accent"), text_color=cfg.get_color("text_main"), corner_radius=r, command=lambda: messagebox.showinfo("Log Exported", f"Log saved at:\n{sys_logger.export()}") if sys_logger.export() else messagebox.showerror("Error", "Failed")).pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(frm_right, text=t("dev_tools"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("danger")).pack(anchor="w", padx=15, pady=(20, 10))
        ctk.CTkButton(frm_right, text=t("dev_apa_sim"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("bg_main"), border_width=1, border_color=cfg.get_color("danger"), text_color=cfg.get_color("text_main"), corner_radius=r, command=lambda: messagebox.showinfo("Dev Tools", f"Simulated Image created at:\n{APAManager.create_fake_vhd()}") if APAManager.create_fake_vhd() else messagebox.showerror("Error", "Failed")).pack(fill="x", padx=15, pady=(0, 10))

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME); self.geometry("950x650"); self.minsize(800, 550); self.configure(fg_color=cfg.get_color("bg_main"))
        self.library = LibraryManager(); self.cur = None; self.last_usb = -1; self.active_transfers = 0; self.is_animating = False
        self._last_click_time = 0; self.bind_all("<Button-1>", self._on_global_click); self.protocol("WM_DELETE_WINDOW", self.on_closing)
        if not cfg.data.get("setup_done", False): self.setup_frame = SetupFrame(self, self)
        else: self.build_main_ui(); self.after(500, self.check_interrupted_transfer)

    def _on_global_click(self, event):
        now = time.time(); 
        if now - self._last_click_time < 0.15: return "break"
        self._last_click_time = now
        w = event.widget; is_sidebar = False
        while w:
            if hasattr(self, 'sb') and self.sb and str(w) == str(self.sb): is_sidebar = True; break
            w = w.master
        if not is_sidebar: sound_fx.play_click()

    def build_main_ui(self):
        old_cur_key = next((k for k, v in getattr(self, 'pages', {}).items() if v == self.cur), None)
        if hasattr(self, 'pages'): [p.destroy() for p in self.pages.values()]
        if hasattr(self, 'setup_frame') and self.setup_frame: self.setup_frame.destroy(); self.setup_frame = None
        if hasattr(self, 'sb'): self.sb.destroy()
        if hasattr(self, 'content'): self.content.destroy()

        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1)
        self.sb = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=cfg.get_color("bg_sidebar")); self.sb.grid(row=0, column=0, sticky="nsew"); self.sb.grid_rowconfigure(20, weight=1)
        self.content = ctk.CTkFrame(self, fg_color="transparent"); self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20); self.content.grid_rowconfigure(0, weight=1); self.content.grid_columnconfigure(0, weight=1)

        self.btns, self.nav_main, self.nav_more, self.cur = {}, [], [], None
        ctk.CTkLabel(self.sb, text="PS2", font=("Segoe UI Black", 20), text_color=cfg.get_color("accent")).grid(row=0, column=0, pady=(20, 5), padx=20, sticky="w")
        ctk.CTkLabel(self.sb, text=APP_VERSION, font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_muted")).grid(row=0, column=0, pady=(22, 5), padx=(65,20), sticky="w")

        pad_y = 5 if cfg.data.get("beta_ui", False) else 2
        def nav(row, k, txt, is_sub=False, group="main"):
            b = ctk.CTkButton(self.sb, text=txt, font=("Segoe UI", 10, "bold" if cfg.data.get("beta_ui", False) else "normal"), fg_color="transparent", text_color=cfg.get_color("text_muted"), anchor="w", height=32, corner_radius=cfg.get_radius("button"), hover_color=cfg.get_color("card_hover"), command=lambda: self.show(k))
            if group == "main": b.grid(row=row, column=0, padx=(30 if is_sub else 12, 12), pady=pad_y, sticky="ew"); self.nav_main.append(k)
            else: self.nav_more.append(k)
            self.btns[k] = b

        nav(1, "dash", t("tab_dash")); nav(2, "games", t("tab_lib")); nav(3, "test", t("tab_emu")); nav(4, "apps", t("tab_apps")); nav(5, "iso", t("tab_iso")); nav(6, "util", t("tab_util")); nav(7, "rip", t("tab_rip")); nav(8, "disc", t("tab_disc")); nav(9, "usb", t("tab_usb")); nav(10, "clone", t("sub_clone"), is_sub=True); nav(11, "migrate", t("tab_mig")); nav(12, "cheats", t("tab_cht"))
        self.btn_enter_more = ctk.CTkButton(self.sb, text=t("tab_more"), font=("Segoe UI", 10, "bold"), fg_color="transparent", text_color=cfg.get_color("text_muted"), anchor="w", height=32, corner_radius=cfg.get_radius("button"), hover_color=cfg.get_color("card_hover"), command=self.enter_more_tools); self.btn_enter_more.grid(row=13, column=0, padx=12, pady=pad_y, sticky="ew")

        self.btn_back_more = ctk.CTkButton(self.sb, text=t("btn_back"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("card_base"), hover_color=cfg.get_color("card_hover"), text_color=cfg.get_color("text_main"), anchor="w", height=40, corner_radius=cfg.get_radius("button"), command=self.exit_more_tools)
        nav(2, "patcher", t("tab_patcher"), group="more"); nav(3, "apa", t("apa_title"), group="more"); nav(4, "art", t("art_title"), group="more")
        
        self.btns["settings"] = ctk.CTkButton(self.sb, text=t("tab_set"), font=("Segoe UI", 10, "bold"), fg_color="transparent", text_color=cfg.get_color("text_muted"), anchor="w", height=32, corner_radius=cfg.get_radius("button"), hover_color=cfg.get_color("card_hover"), command=lambda: self.show("settings")); self.btns["settings"].grid(row=21, column=0, padx=12, pady=(0, 20), sticky="sew")

        self.pages = {"dash": DashboardPage(self.content, self), "games": GamesPage(self.content, self), "test": EmulatorTestPage(self.content, self), "apps": AppsManagerPage(self.content, self), "iso": IsoExtractorPage(self.content, self), "util": UtilSplitterPage(self.content, self), "rip": DvdRipperPage(self.content, self), "disc": DiscAnalyzerPage(self.content, self), "usb": USBPage(self.content, self), "clone": ClonePage(self.content, self), "migrate": MigratePage(self.content, self), "cheats": CheatManagerPage(self.content, self), "patcher": IsoPatcherPage(self.content, self), "apa": ApaExplorerPage(self.content, self), "art": OplArtDownloaderPage(self.content, self), "settings": SettingsPage(self.content, self)}
        
        if old_cur_key in self.nav_more: self.enter_more_tools(); self.show(old_cur_key)
        else: self.show(old_cur_key if old_cur_key else "dash")
        self.monitor_usb()

    def enter_more_tools(self):
        [self.btns[k].grid_remove() for k in self.nav_main]; self.btn_enter_more.grid_remove(); self.btn_back_more.grid(row=1, column=0, padx=12, pady=(10, 20), sticky="ew")
        for i, k in enumerate(self.nav_more): self.btns[k].grid(row=2+i, column=0, padx=12, pady=5 if cfg.data.get("beta_ui", False) else 2, sticky="ew")
        self.show(self.nav_more[0])

    def exit_more_tools(self):
        self.btn_back_more.grid_remove(); [self.btns[k].grid_remove() for k in self.nav_more]; [self.btns[k].grid() for k in self.nav_main]; self.btn_enter_more.grid(); self.show("dash")

    def show(self, k):
        if self.is_animating or self.cur == self.pages.get(k): return 
        self.is_animating = True; sound_fx.play_tab(); self.library.sync() 
        for b in self.btns.values(): b.configure(fg_color="transparent", text_color=cfg.get_color("text_muted"))
        if k in self.btns: self.btns[k].configure(fg_color=cfg.get_color("card_base"), text_color=cfg.get_color("text_main"))
        if self.cur: self.cur.place_forget()
        self.cur = self.pages.get(k)
        
        def anim(step=0.0):
            if not cfg.data.get("animations", True): self.cur.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0); self.is_animating = False; return
            if step < 1.0: self.cur.place(relx=0.05 * (1.0 - pow(1.0 - step, 5 if cfg.data.get("beta_ui", False) else 3)), rely=0, relwidth=1.0, relheight=1.0); self.after(10, lambda: anim(min(1.0, step + 0.08))) 
            else: self.cur.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0); self.is_animating = False
        anim(); getattr(self.cur, "refresh", lambda: None)()

    def refresh_all_ui(self): cfg.apply_theme(); self.configure(fg_color=cfg.get_color("bg_main")); self.setup_frame.configure(fg_color=cfg.get_color("bg_main")) if hasattr(self, 'setup_frame') and self.setup_frame else self.build_main_ui()
    def on_closing(self): (self.withdraw() if messagebox.askyesno("Wait!", t("msg_bg_close")) else (sound_fx.play_close(), self.after(400, self.destroy()))) if self.active_transfers > 0 else (sound_fx.play_close(), self.after(400, self.destroy()))
    
    def check_interrupted_transfer(self):
        state = TransferStateManager.load()
        if state:
            sound_fx.play_error()
            if messagebox.askyesno("Resume", t("res_warn")): self.resume_transfer(state)
            else: TransferStateManager.clear()

    def resume_transfer(self, state):
        self.active_transfers += 1; drives = DriveManager.get_drives()
        src_d, dst_d = next((d for d in drives if state['src'].startswith(d['mountpoint'])), None), next((d for d in drives if state['dst'].startswith(d['mountpoint'])), None)
        if state['type'] == "migration" and dst_d: threading.Thread(target=MigrationWorker(dst_d, state.get('dst'), {'log': lambda m: None, 'prog_total': lambda v: None, 'prog_step': lambda v: None, 'done': lambda s: TransferStateManager.clear()}, resume_data=state).run, daemon=True).start()
        elif state['type'] == "clone" and src_d and dst_d: threading.Thread(target=CloneWorker(src_d, dst_d, False, state.get("fmt_after", False), {'log': lambda m: None, 'prog_total': lambda v: None}, resume_data=state).run, daemon=True).start()

    def monitor_usb(self):
        def loop():
            while True:
                c = len(DriveManager.get_drives())
                if self.last_usb != -1 and c != self.last_usb:
                    sound_fx.play_usb(c > self.last_usb)
                    if c > self.last_usb: self.after(0, lambda: NotificationPopup(self, "Drive Node Detected", "success").place(relx=0.98, rely=0.95, anchor="se"))
                    self.after(0, self.refresh_all)
                self.last_usb = c; time.sleep(2)
        threading.Thread(target=loop, daemon=True).start()

    def refresh_all(self): getattr(self.cur, "refresh", lambda: None)()

if __name__ == "__main__": MainApp().mainloop()