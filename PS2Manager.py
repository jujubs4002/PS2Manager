from __future__ import annotations

import os
import sys

# Interceptador CLI ANTES da interface gráfica: garante que Watchdog e scripts
# internos rodem 100% pelo Python EMBUTIDO dentro do PS2Manager (sem exigir Python no PC do usuário).
if len(sys.argv) >= 2 and sys.argv[1] in ("--watchdog", "--run-script"):
    from scripts.core_backend import run_watchdog_loop, run_internal_script
    if sys.argv[1] == "--watchdog" and len(sys.argv) >= 5:
        run_watchdog_loop(int(sys.argv[2]), sys.argv[3], sys.argv[4])
        sys.exit(0)
    elif sys.argv[1] == "--run-script" and len(sys.argv) >= 3:
        run_internal_script(sys.argv[2])
        sys.exit(0)

import shutil
import threading
import webbrowser
import ctypes
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser

try:
    from PIL import Image as _BgPILImage, ImageFilter as _BgPILFilter, ImageEnhance as _BgPILEnhance, ImageTk as _BgPILTk
    _BG_PIL_OK = True
    _BG_RESAMPLE_BILINEAR = getattr(getattr(_BgPILImage, "Resampling", None), "BILINEAR", getattr(_BgPILImage, "BILINEAR", 2))
except Exception:
    _BG_PIL_OK = False
    _BG_RESAMPLE_BILINEAR = 2

from scripts.core_backend import *
from scripts.tool_workers import *
from scripts.v108_workers import *
from scripts.ui_pages import (
    apply_window_icon, NotificationPopup, HoverCard, PageHeader,
    create_segmented_tabs, UsbOptimizerPage, OplConfigPage,
    ArtScraperV2Page, MemoryCardPage, PopStarterPage,
    IsoPatcherV2Page, IsoStudioPage
)
from scripts.ui_modals import (
    SetupFrame, RemoteNoticeClient, NewsOverlayModal,
    VersionRollbackModal, ChangelogTimelineModal,
    GameDetailsModal, CheatManagerPage, EmulatorTestPage,
    DvdBurnerPage, AppsManagerPage
)

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ps2manager.suite.v108")
except Exception:
    pass


# ==============================================================================
# PAINEL PRINCIPAL (DASHBOARD), BIBLIOTECA & INSTALAÇÃO UNIFICADA NO USB
# ==============================================================================
class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(4, weight=1)

        PageHeader(self, t("tab_dash"), t("dash_sub"), badge_text=APP_VERSION).grid(
            row=0, column=0, columnspan=4, sticky="ew", pady=(0, 16)
        )

        self.card_games = self._stat_card(0, t("dash_games"), "0", cfg.get_color("accent"))
        self.card_usb = self._stat_card(1, t("dash_usb"), "0", cfg.get_color("success"))
        self.card_size = self._stat_card(2, t("dash_size"), "0 B", cfg.get_color("warning"))
        self.card_console = self._stat_card(
            3, t("dash_console"),
            f"{cfg.data.get('ps2_type', 'SLIM')}",
            cfg.get_color("highlight")
        )

        ctk.CTkLabel(
            self, text=t("dash_quick"), font=("Segoe UI", 11, "bold"),
            text_color=cfg.get_color("text_muted")
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(18, 6))

        q_bar = ctk.CTkFrame(self, fg_color="transparent")
        q_bar.grid(row=3, column=0, columnspan=4, sticky="ew")
        q_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        quick_actions = [
            (f"📥  {t('tab_install')}", "install", cfg.get_color("accent")),
            (f"🛡  {t('usb_mode_defrag')}", "usb_defrag", cfg.get_color("success")),
            (f"⚙  {t('tab_opl_cfg')}", "opl_cfg", cfg.get_color("chip_bg")),
            (f"💾  {t('tab_mc')}", "mc", cfg.get_color("chip_bg"))
        ]
        for idx, (label, target_key, col) in enumerate(quick_actions):
            ctk.CTkButton(
                q_bar, text=label, height=40, font=("Segoe UI", 11, "bold"),
                fg_color=col, hover_color=cfg.get_hover("accent_hover", "card_base"),
                corner_radius=cfg.get_radius("button"),
                command=lambda k=target_key: self._jump(k)
            ).grid(row=0, column=idx, sticky="ew", padx=4)

        self.usb_panel = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border"),
            label_text=t("dash_storage"), label_font=("Segoe UI", 11, "bold"),
            label_text_color=cfg.get_color("highlight")
        )
        self.usb_panel.grid(row=4, column=0, columnspan=4, sticky="nsew", pady=(16, 0))

    def _jump(self, key):
        if key == "usb_defrag":
            self.app.show("usb")
            if "usb" in self.app.pages:
                self.app.pages["usb"].switch_to_defrag()
        else:
            self.app.show(key)

    def _stat_card(self, col, title, initial_val, color):
        c = HoverCard(self, fg_color=cfg.get_color("card_base"), height=104)
        c.grid(row=1, column=col, padx=5, sticky="nsew")
        c.pack_propagate(False)
        ctk.CTkFrame(c, height=3, fg_color=color, corner_radius=0).pack(fill="x")
        ctk.CTkLabel(c, text=title, font=("Segoe UI", 10, "bold"), text_color=color).pack(pady=(14, 4), padx=10)
        lbl_val = ctk.CTkLabel(c, text=initial_val, font=("Segoe UI Black", 22), text_color=cfg.get_color("text_main"))
        lbl_val.pack()
        c.bind_children()
        return lbl_val

    def refresh(self):
        games = self.app.library.games
        self.card_games.configure(text=str(len(games)))
        drives = UsbDetector.get_removable_drives()
        self.card_usb.configure(text=str(len(drives)))
        total_b = sum(g.get('size_bytes', 0) for g in games)
        self.card_size.configure(text=format_size(total_b))
        self.card_console.configure(text=f"{cfg.data.get('ps2_model', 'PS2')}")

        for w in self.usb_panel.winfo_children():
            w.destroy()
        if not drives:
            ctk.CTkLabel(
                self.usb_panel, text=t("dash_no_usb"),
                font=("Segoe UI", 12), text_color=cfg.get_color("text_muted")
            ).pack(pady=30)
            return
        for d in drives:
            row = ctk.CTkFrame(self.usb_panel, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("chip"))
            row.pack(fill="x", padx=8, pady=5)
            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(8, 4))
            ctk.CTkLabel(top, text=f"🔌 {d['mountpoint']} [{d['fstype']}]", font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(side="left")
            ctk.CTkLabel(top, text=f"{d['used_str']} / {d['total_str']} ({d['free_str']} free)", font=("Consolas", 11), text_color=cfg.get_color("highlight")).pack(side="right")
            pb = ctk.CTkProgressBar(row, height=7, progress_color=cfg.get_color("accent"))
            pb.pack(fill="x", padx=14, pady=(0, 10))
            pb.set(min(1.0, d["percent"] / 100.0))


class GamesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        def build_actions(box):
            ctk.CTkButton(
                box, text=t("lib_add_iso"), font=("Segoe UI", 11, "bold"),
                height=34, corner_radius=cfg.get_radius("button"),
                fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
                command=self.add_single_file
            ).pack(side="left", padx=(0, 8))
            ctk.CTkButton(
                box, text=t("lib_scan"), font=("Segoe UI", 11, "bold"),
                height=34, corner_radius=cfg.get_radius("button"),
                fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
                command=self.scan_folder
            ).pack(side="left")

        PageHeader(self, t("tab_lib"), t("lib_sub"), right_widget_builder=build_actions).grid(
            row=0, column=0, sticky="ew", pady=(0, 12)
        )

        self._search_job = None
        self._last_render_sig = None

        self.ent_search = ctk.CTkEntry(
            self, placeholder_text=t("lib_search"),
            fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border"),
            height=38, corner_radius=cfg.get_radius("entry")
        )
        self.ent_search.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.ent_search.bind("<KeyRelease>", self._on_search_key)

        self.list_box = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.list_box.grid(row=2, column=0, sticky="nsew")

    def _on_search_key(self, _e=None):
        if self._search_job:
            try:
                self.after_cancel(self._search_job)
            except Exception:
                pass
        self._search_job = self.after(110, self.render_list)

    def add_single_file(self):
        sound_fx.play_click()
        files = filedialog.askopenfilenames(filetypes=[(t("iso_files"), "*.iso *.zso *.bin")])
        if files:
            for f in files:
                try:
                    self.app.library.add(GameAnalyzer.analyze(f))
                except Exception:
                    pass
            sound_fx.play_success()
            self._last_render_sig = None
            self.app.refresh_all()

    def scan_folder(self):
        sound_fx.play_click()
        p = filedialog.askdirectory()
        if p:
            self.app.library.scan_directory(p)
            sound_fx.play_success()
            self._last_render_sig = None
            NotificationPopup(self.app, t("lib_scan_done"), "success")
            self.app.refresh_all()

    def refresh(self):
        self.render_list()

    def render_list(self, force=False):
        self._search_job = None
        q = self.ent_search.get().lower().strip()
        sig = (
            q,
            tuple((g.get('path'), g.get('name'), g.get('id'), g.get('size_bytes')) for g in self.app.library.games)
        )
        if not force and sig == self._last_render_sig:
            return
        self._last_render_sig = sig

        for w in self.list_box.winfo_children():
            w.destroy()
        games = [
            g for g in self.app.library.games
            if q in g.get('name', '').lower() or q in g.get('id', '').lower() or q in g.get('region', '').lower()
        ]
        if not games:
            ctk.CTkLabel(
                self.list_box, text=t("lib_empty"),
                font=("Segoe UI", 12), text_color=cfg.get_color("text_muted")
            ).pack(pady=50)
            return
        for g in games:
            card = HoverCard(
                self.list_box, height=50, corner_radius=cfg.get_radius("chip"),
                fg_color=cfg.get_color("bg_main"), hover_color=cfg.get_color("card_hover"),
                command=lambda gd=g: GameDetailsModal(self.app, gd)
            )
            card.pack(fill="x", pady=3, padx=6)
            card.pack_propagate(False)

            ctk.CTkFrame(card, width=4, fg_color=cfg.get_color("accent"), corner_radius=0).pack(side="left", fill="y", padx=(0, 12))
            ctk.CTkLabel(card, text=g.get('name', 'Unknown'), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(card, text=g.get('id', 'N/A'), font=("Consolas", 11, "bold"), text_color=cfg.get_color("highlight")).pack(side="left", padx=6)
            ctk.CTkLabel(card, text=f"{g.get('region', '')} • {g.get('format', '')} • {g.get('size_str', '')}", font=("Consolas", 10), text_color=cfg.get_color("text_muted")).pack(side="right", padx=16)
            card.bind_children()


class UnifiedInstallPage(ctk.CTkFrame):
    """Unifica Instalação 1-Clique, Fila em Lote e USBUtil (FAT32 >4GB) sem poluir a barra lateral!"""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.queue_items = []
        self.batch_worker = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        PageHeader(self, t("tab_install"), t("inst_sub"), badge_text="FAT32 & exFAT").grid(
            row=0, column=0, sticky="ew", pady=(0, 12)
        )

        self.modes = [t("inst_mode_single"), t("inst_mode_batch"), t("inst_mode_split")]
        self.seg = create_segmented_tabs(self, self.modes, self.switch_submode)
        self.seg.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.f_single = ctk.CTkFrame(self.body, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        self.f_batch = ctk.CTkFrame(self.body, fg_color="transparent")
        self.f_split = ctk.CTkFrame(self.body, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))

        self._build_single()
        self._build_batch()
        self._build_split()
        self.switch_submode(self.modes[0])

    def _build_single(self):
        ctk.CTkLabel(self.f_single, text=t("inst_step1"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(20, 5))
        f_iso = ctk.CTkFrame(self.f_single, fg_color="transparent")
        f_iso.pack(fill="x", padx=22)
        self.ent_iso = ctk.CTkEntry(f_iso, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_iso.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(f_iso, text=t("btn_select"), width=95, height=34, corner_radius=cfg.get_radius("button"), command=self.browse_iso).pack(side="left")

        ctk.CTkLabel(self.f_single, text=t("inst_step2"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(14, 5))
        self.ent_name = ctk.CTkEntry(self.f_single, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_name.pack(fill="x", padx=22)

        ctk.CTkLabel(self.f_single, text=t("inst_step3"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(14, 5))
        self.var_drive = ctk.StringVar(value=t("inst_err_nodrive"))
        self.cmb_drive = ctk.CTkOptionMenu(self.f_single, variable=self.var_drive, values=[t("inst_err_nodrive")], height=34, corner_radius=cfg.get_radius("entry"), command=lambda _: sound_fx.play_click())
        self.cmb_drive.pack(fill="x", padx=22)

        self.var_art = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.f_single, text=t("inst_auto_art"), variable=self.var_art, font=("Segoe UI", 12), command=sound_fx.play_click).pack(anchor="w", padx=22, pady=15)

        self.btn_install = ctk.CTkButton(
            self.f_single, text=t("inst_btn"), font=("Segoe UI", 13, "bold"),
            height=44, fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.start_install
        )
        self.btn_install.pack(pady=(6, 12), padx=22, fill="x")

        self.lbl_status = ctk.CTkLabel(self.f_single, text=t("inst_ready"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted"))
        self.lbl_status.pack(pady=(0, 4))
        self.prog = ctk.CTkProgressBar(self.f_single, progress_color=cfg.get_color("highlight"))
        self.prog.pack(fill="x", padx=22, pady=(0, 20))
        self.prog.set(0)

    def _build_batch(self):
        self.f_batch.grid_columnconfigure(0, weight=1)
        self.f_batch.grid_rowconfigure(1, weight=1)

        b_top = ctk.CTkFrame(self.f_batch, fg_color="transparent")
        b_top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(b_top, text=t("batch_add"), height=32, corner_radius=cfg.get_radius("button"), command=self.add_batch_files).pack(side="left", padx=(0, 6))
        ctk.CTkButton(b_top, text=t("batch_folder"), height=32, corner_radius=cfg.get_radius("button"), command=self.add_batch_folder).pack(side="left", padx=6)
        ctk.CTkButton(b_top, text=t("batch_clear"), height=32, fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"), command=self.clear_queue).pack(side="right")

        self.batch_list = ctk.CTkScrollableFrame(self.f_batch, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        self.batch_list.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        b_bot = ctk.CTkFrame(self.f_batch, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        b_bot.grid(row=2, column=0, sticky="ew")

        drv_r = ctk.CTkFrame(b_bot, fg_color="transparent")
        drv_r.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(drv_r, text=t("inst_step3"), font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 10))
        self.var_b_drv = ctk.StringVar(value=t("inst_err_nodrive"))
        self.cmb_b_drv = ctk.CTkOptionMenu(drv_r, variable=self.var_b_drv, values=[t("inst_err_nodrive")], height=30, corner_radius=cfg.get_radius("entry"), command=lambda _: sound_fx.play_click())
        self.cmb_b_drv.pack(side="left", fill="x", expand=True)
        self.var_b_art = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(drv_r, text=t("inst_auto_art"), variable=self.var_b_art, font=("Segoe UI", 11), command=sound_fx.play_click).pack(side="left", padx=14)

        self.prog_b_total = ctk.CTkProgressBar(b_bot, progress_color=cfg.get_color("accent"))
        self.prog_b_total.pack(fill="x", padx=16, pady=(2, 6))
        self.prog_b_total.set(0)
        self.prog_b_item = ctk.CTkProgressBar(b_bot, progress_color=cfg.get_color("highlight"))
        self.prog_b_item.pack(fill="x", padx=16, pady=(0, 10))
        self.prog_b_item.set(0)

        self.btn_batch = ctk.CTkButton(b_bot, text=t("batch_start"), height=40, font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=self.start_batch)
        self.btn_batch.pack(fill="x", padx=16, pady=(0, 14))
        self.refresh_queue_view()

    def _build_split(self):
        ctk.CTkLabel(self.f_split, text=t("util_iso"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(20, 5))
        r1 = ctk.CTkFrame(self.f_split, fg_color="transparent")
        r1.pack(fill="x", padx=22)
        self.ent_u_iso = ctk.CTkEntry(r1, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_u_iso.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(r1, text=t("btn_browse"), width=95, height=34, corner_radius=cfg.get_radius("button"), command=self.browse_split_iso).pack(side="left")

        ctk.CTkLabel(self.f_split, text=t("util_dst"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(14, 5))
        r2 = ctk.CTkFrame(self.f_split, fg_color="transparent")
        r2.pack(fill="x", padx=22)
        self.ent_u_dst = ctk.CTkEntry(r2, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_u_dst.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(r2, text=t("btn_browse"), width=95, height=34, corner_radius=cfg.get_radius("button"), command=lambda: [sound_fx.play_click(), self._set_entry(self.ent_u_dst, filedialog.askdirectory())]).pack(side="left")

        ctk.CTkLabel(self.f_split, text=t("util_name"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(14, 5))
        self.ent_u_name = ctk.CTkEntry(self.f_split, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_u_name.pack(fill="x", padx=22)

        self.btn_split = ctk.CTkButton(self.f_split, text=t("util_btn"), height=42, font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), corner_radius=cfg.get_radius("button"), command=self.run_split)
        self.btn_split.pack(fill="x", padx=22, pady=20)
        self.prog_u = ctk.CTkProgressBar(self.f_split, progress_color=cfg.get_color("highlight"))
        self.prog_u.pack(fill="x", padx=22, pady=(0, 20))
        self.prog_u.set(0)

    def _set_entry(self, ent, val):
        if val:
            ent.delete(0, "end")
            ent.insert(0, val)

    def switch_submode(self, val):
        self.f_single.grid_forget()
        self.f_batch.grid_forget()
        self.f_split.grid_forget()
        if val == self.modes[0]:
            self.f_single.grid(row=0, column=0, sticky="nsew")
        elif val == self.modes[1]:
            self.f_batch.grid(row=0, column=0, sticky="nsew")
        else:
            self.f_split.grid(row=0, column=0, sticky="nsew")

    def set_iso(self, path):
        self.seg.set(self.modes[0])
        self.switch_submode(self.modes[0])
        self.ent_iso.delete(0, 'end')
        self.ent_iso.insert(0, path)
        self.ent_name.delete(0, 'end')
        self.ent_name.insert(0, GameAnalyzer.clean_display_title(os.path.basename(path))[:32])

    def browse_iso(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso *.bin *.zso")])
        if f:
            self.set_iso(f)

    def browse_split_iso(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso")])
        if f:
            self._set_entry(self.ent_u_iso, f)
            self._set_entry(self.ent_u_name, GameAnalyzer.clean_display_title(os.path.basename(f))[:32])

    def refresh(self):
        drives = UsbDetector.get_removable_drives()
        vals = [f"{d['mountpoint']} [{d['fstype']}] - {d['free_str']} free" for d in drives] or [t("inst_err_nodrive")]
        for cmb, var in [(self.cmb_drive, self.var_drive), (self.cmb_b_drv, self.var_b_drv)]:
            cmb.configure(values=vals)
            if var.get() not in vals:
                var.set(vals[0])
        if drives and not self.ent_u_dst.get().strip():
            self.ent_u_dst.insert(0, drives[0]["mountpoint"])

    def _resolve_drive(self, drv_str):
        if drv_str == t("inst_err_nodrive"):
            return None
        mp = drv_str.split(" ")[0]
        return next((d for d in UsbDetector.get_removable_drives() if d['mountpoint'].upper() == mp.upper()), None)

    def start_install(self):
        sound_fx.play_click()
        iso = self.ent_iso.get().strip()
        target_d = self._resolve_drive(self.var_drive.get())
        if not iso or not os.path.exists(iso) or not target_d:
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("inst_err_select"))
            return
        self.btn_install.configure(state="disabled")
        self.prog.set(0)
        self.lbl_status.configure(text=t("inst_starting"))

        SingleInstallWorker.install(
            iso, target_d, self.ent_name.get().strip(), self.var_art.get(),
            cb_prog=lambda v: self.app.after(0, lambda: self.prog.set(v)),
            cb_done=lambda _: self.app.after(0, lambda: [
                self.btn_install.configure(state="normal"),
                self.prog.set(1.0),
                self.lbl_status.configure(text=t("inst_done")),
                sound_fx.play_success(),
                messagebox.showinfo(t("success"), t("inst_succ_msg"))
            ]),
            cb_err=lambda e: self.app.after(0, lambda: [
                self.btn_install.configure(state="normal"),
                sound_fx.play_error(),
                messagebox.showerror(t("error"), f"{t('inst_err_fail')} {e}")
            ])
        )

    def add_batch_files(self):
        sound_fx.play_click()
        for f in filedialog.askopenfilenames(filetypes=[(t("iso_files"), "*.iso *.bin *.zso")]):
            if not any(x['path'] == f for x in self.queue_items):
                self.queue_items.append({'path': f, 'name': GameAnalyzer.clean_display_title(os.path.basename(f))[:32], 'size': format_size(os.path.getsize(f))})
        self.refresh_queue_view()

    def add_batch_folder(self):
        sound_fx.play_click()
        folder = filedialog.askdirectory()
        if folder:
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(('.iso', '.bin', '.zso')):
                        fp = os.path.join(root, f)
                        if not any(x['path'] == fp for x in self.queue_items):
                            self.queue_items.append({'path': fp, 'name': GameAnalyzer.clean_display_title(f)[:32], 'size': format_size(os.path.getsize(fp))})
            self.refresh_queue_view()

    def clear_queue(self):
        sound_fx.play_click()
        self.queue_items.clear()
        self.refresh_queue_view()

    def refresh_queue_view(self):
        for w in self.batch_list.winfo_children():
            w.destroy()
        if not self.queue_items:
            ctk.CTkLabel(self.batch_list, text=t("batch_empty"), text_color=cfg.get_color("text_muted")).pack(pady=35)
            return
        for idx, item in enumerate(self.queue_items):
            row = ctk.CTkFrame(self.batch_list, fg_color=cfg.get_color("bg_main"), height=38, corner_radius=cfg.get_radius("chip"))
            row.pack(fill="x", pady=2, padx=4)
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"{idx+1}. {item['name']}", font=("Segoe UI", 11, "bold")).pack(side="left", padx=12)
            ctk.CTkLabel(row, text=item['size'], font=("Consolas", 10), text_color=cfg.get_color("text_muted")).pack(side="left", padx=8)
            ctk.CTkButton(row, text="✕", width=28, height=24, fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"), command=lambda i=idx: [sound_fx.play_click(), self.queue_items.pop(i), self.refresh_queue_view()]).pack(side="right", padx=10)

    def start_batch(self):
        sound_fx.play_click()
        if not self.queue_items:
            messagebox.showwarning(t("warning"), t("batch_warn_empty"))
            return
        target_d = self._resolve_drive(self.var_b_drv.get())
        if not target_d:
            messagebox.showerror(t("error"), t("batch_err_nodrive"))
            return
        self.btn_batch.configure(state="disabled")
        self.prog_b_total.set(0)
        self.prog_b_item.set(0)

        self.batch_worker = BatchInstallWorker(
            self.queue_items.copy(), target_d, self.var_b_art.get(),
            cb_item_prog=lambda v: self.app.after(0, lambda: self.prog_b_item.set(v)),
            cb_total_prog=lambda v: self.app.after(0, lambda: self.prog_b_total.set(v)),
            cb_log=lambda m: sys_logger.log(m, "BATCH"),
            cb_done=lambda _: self.app.after(0, lambda: [
                self.btn_batch.configure(state="normal"),
                sound_fx.play_success(),
                messagebox.showinfo(t("batch_done_title"), t("batch_done_msg")),
                self.clear_queue()
            ])
        )
        self.batch_worker.start()

    def run_split(self):
        sound_fx.play_click()
        s, d = self.ent_u_iso.get().strip(), self.ent_u_dst.get().strip()
        if not s or not d:
            sound_fx.play_error()
            return
        self.btn_split.configure(state="disabled")
        self.prog_u.set(0)
        USBUtilWorker.split_and_generate(
            s, d, self.ent_u_name.get().strip() or GameAnalyzer.clean_display_title(os.path.basename(s))[:32],
            cb_prog=lambda v: self.app.after(0, lambda: self.prog_u.set(v)),
            cb_done=lambda _: self.app.after(0, lambda: [self.btn_split.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), t("util_succ"))]),
            cb_err=lambda e: self.app.after(0, lambda: [self.btn_split.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("error"), str(e))])
        )


# ==============================================================================
# CONFIGURAÇÕES (MODO BATATA FORTE, SOM DE ABA SEPARADO & VARIAÇÕES DE ANIMAÇÃO)
# ==============================================================================
class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._bg_commit_job = None
        self._preview_photo = None
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        PageHeader(self, t("tab_set"), t("set_sub")).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14)
        )

        frm_left = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        frm_left.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(frm_left, text=t("set_app"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=14, pady=(10, 8))

        LANG_MAP = {
            "PT_BR": "Português (Brasil) [PT_BR]",
            "PT": "Português (Portugal) [PT]",
            "EN": "English [EN]",
            "ES": "Español [ES]",
            "RU": "Русский [RU]",
            "JA": "日本語 [JA]"
        }
        INV_LANG_MAP = {v: k for k, v in LANG_MAP.items()}
        self.lang_var = ctk.StringVar(value=LANG_MAP.get(cfg.data.get("language", "PT_BR"), LANG_MAP["PT_BR"]))

        def on_lang_change(val):
            sound_fx.play_click()
            cfg.data["language"] = INV_LANG_MAP.get(val, "PT_BR")
            cfg.save()
            self.app.after(40, self.app.refresh_all_ui)

        ctk.CTkLabel(frm_left, text=t("set_lang"), font=("Segoe UI", 10, "bold"), text_color=cfg.get_color("text_muted")).pack(anchor="w", padx=18)
        ctk.CTkOptionMenu(frm_left, variable=self.lang_var, values=list(LANG_MAP.values()), height=32, command=on_lang_change, corner_radius=cfg.get_radius("entry")).pack(fill="x", padx=18, pady=(2, 10))

        ctk.CTkLabel(frm_left, text=t("set_theme"), font=("Segoe UI", 10, "bold"), text_color=cfg.get_color("text_muted")).pack(anchor="w", padx=18)
        self.theme_var = ctk.StringVar(value=cfg.data.get("theme", "Midnight Neon"))
        ctk.CTkOptionMenu(
            frm_left, variable=self.theme_var, values=list(THEMES.keys()), height=32,
            command=lambda c: [sound_fx.play_click(), cfg.data.update({"theme": c}), cfg.save(), self.app.after(40, self.app.refresh_all_ui)],
            corner_radius=cfg.get_radius("entry")
        ).pack(fill="x", padx=18, pady=(2, 10))

        ANIM_MAP = {
            "Slide": t("anim_slide"),
            "Rise": t("anim_rise"),
            "Zoom": t("anim_zoom"),
            "Step": t("anim_step")
        }
        INV_ANIM_MAP = {v: k for k, v in ANIM_MAP.items()}
        self.anim_style_var = ctk.StringVar(value=ANIM_MAP.get(cfg.data.get("anim_style", "Slide"), ANIM_MAP["Slide"]))

        def on_anim_style(val):
            sound_fx.play_click()
            cfg.data["anim_style"] = INV_ANIM_MAP.get(val, "Slide")
            cfg.save()

        ctk.CTkLabel(frm_left, text=t("set_anim_style"), font=("Segoe UI", 10, "bold"), text_color=cfg.get_color("text_muted")).pack(anchor="w", padx=18)
        ctk.CTkOptionMenu(
            frm_left, variable=self.anim_style_var, values=list(ANIM_MAP.values()),
            height=32, command=on_anim_style, corner_radius=cfg.get_radius("entry")
        ).pack(fill="x", padx=18, pady=(2, 14))

        ctk.CTkLabel(frm_left, text=t("set_beh"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("highlight")).pack(anchor="w", padx=18, pady=(4, 8))

        self.snd_var = ctk.BooleanVar(value=bool(cfg.data.get("sound_enabled", True)))
        self.tab_snd_var = ctk.BooleanVar(value=bool(cfg.data.get("tab_sound_enabled", True)))
        self.bgm_var = ctk.BooleanVar(value=bool(cfg.data.get("bgm_enabled", True)))
        self.anim_var = ctk.BooleanVar(value=bool(cfg.data.get("animations", True)))
        self.potato_var = ctk.BooleanVar(value=bool(cfg.data.get("laptop_mode", False)))

        def save_prefs(rebuild=False):
            cfg.data.update({
                "sound_enabled": self.snd_var.get(),
                "tab_sound_enabled": self.tab_snd_var.get(),
                "bgm_enabled": self.bgm_var.get(),
                "animations": self.anim_var.get(),
                "laptop_mode": self.potato_var.get()
            })
            cfg.save()
            sound_fx.sync_from_config()
            if self.snd_var.get():
                sound_fx.play_click()
            if rebuild:
                self.app.after(40, self.app.refresh_all_ui)

        ctk.CTkSwitch(frm_left, text=t("set_snd"), font=("Segoe UI", 11), variable=self.snd_var, command=save_prefs).pack(anchor="w", padx=18, pady=5)
        ctk.CTkSwitch(frm_left, text=t("set_tab_snd"), font=("Segoe UI", 11), variable=self.tab_snd_var, command=save_prefs).pack(anchor="w", padx=18, pady=5)
        ctk.CTkSwitch(frm_left, text=t("set_bgm"), font=("Segoe UI", 11), variable=self.bgm_var, command=save_prefs).pack(anchor="w", padx=18, pady=5)
        ctk.CTkSwitch(frm_left, text=t("set_anim"), font=("Segoe UI", 11), variable=self.anim_var, command=save_prefs).pack(anchor="w", padx=18, pady=5)

        potato_box = ctk.CTkFrame(frm_left, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("chip"))
        potato_box.pack(fill="x", padx=18, pady=(8, 16))
        ctk.CTkSwitch(
            potato_box, text=t("set_potato"), font=("Segoe UI", 11, "bold"),
            text_color=cfg.get_color("warning"), progress_color=cfg.get_color("warning"),
            variable=self.potato_var, command=lambda: save_prefs(rebuild=True)
        ).pack(anchor="w", padx=12, pady=10)

        # Coluna Direita: Personalização do Fundo (Transparência & Borrão) + Sistema
        frm_right = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        frm_right.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        r = cfg.get_radius("button")

        # --- Seção: Personalizar o Fundo de Tudo + Transparência (0-100%) + Borrão (0-100%) ---
        ctk.CTkLabel(
            frm_right, text=t("set_bg_title"), font=("Segoe UI", 12, "bold"),
            text_color=cfg.get_color("highlight")
        ).pack(anchor="w", padx=14, pady=(10, 8))

        bg_box = ctk.CTkFrame(
            frm_right, fg_color=cfg.get_color("bg_main"),
            corner_radius=cfg.get_radius("chip"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        bg_box.pack(fill="x", padx=14, pady=(0, 14))

        self.bg_preview_lbl = tk.Label(bg_box, bg=cfg.get_color("bg_main"), height=3, bd=0, highlightthickness=0)
        self.bg_preview_lbl.pack(fill="x", padx=10, pady=(10, 8))

        bg_btns = ctk.CTkFrame(bg_box, fg_color="transparent")
        bg_btns.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(
            bg_btns, text=t("set_bg_img"), height=32, font=("Segoe UI", 10, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=r, command=self.pick_bg_image
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            bg_btns, text=t("set_bg_col"), height=32, font=("Segoe UI", 10, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=r, command=self.pick_bg_color
        ).pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(
            bg_btns, text=t("set_bg_reset"), width=82, height=32, font=("Segoe UI", 10, "bold"),
            fg_color=cfg.get_color("danger"), corner_radius=r, command=self.reset_bg_custom
        ).pack(side="left", padx=(4, 0))

        cur_tr = max(0, min(100, int(cfg.data.get("bg_transparency", 0) or 0)))
        cur_bl = max(0, min(100, int(cfg.data.get("bg_blur", 0) or 0)))

        tr_hdr = ctk.CTkFrame(bg_box, fg_color="transparent")
        tr_hdr.pack(fill="x", padx=12, pady=(2, 0))
        ctk.CTkLabel(tr_hdr, text=t("set_bg_transp"), font=("Segoe UI", 10, "bold"), text_color=cfg.get_color("text_muted")).pack(side="left")
        self.lbl_transp_val = ctk.CTkLabel(tr_hdr, text=f"{cur_tr}%", font=("Consolas", 11, "bold"), text_color=cfg.get_color("highlight"))
        self.lbl_transp_val.pack(side="right")

        self.sld_transp = ctk.CTkSlider(
            bg_box, from_=0, to=100, number_of_steps=100,
            progress_color=cfg.get_color("accent"), button_color=cfg.get_color("highlight"),
            command=self._on_transp_slide
        )
        self.sld_transp.set(cur_tr)
        self.sld_transp.pack(fill="x", padx=12, pady=(2, 8))

        bl_hdr = ctk.CTkFrame(bg_box, fg_color="transparent")
        bl_hdr.pack(fill="x", padx=12, pady=(2, 0))
        ctk.CTkLabel(bl_hdr, text=t("set_bg_blur"), font=("Segoe UI", 10, "bold"), text_color=cfg.get_color("text_muted")).pack(side="left")
        self.lbl_blur_val = ctk.CTkLabel(bl_hdr, text=f"{cur_bl}%", font=("Consolas", 11, "bold"), text_color=cfg.get_color("highlight"))
        self.lbl_blur_val.pack(side="right")

        self.sld_blur = ctk.CTkSlider(
            bg_box, from_=0, to=100, number_of_steps=100,
            progress_color=cfg.get_color("accent"), button_color=cfg.get_color("highlight"),
            command=self._on_blur_slide
        )
        self.sld_blur.set(cur_bl)
        self.sld_blur.pack(fill="x", padx=12, pady=(2, 12))
        self._update_bg_preview()

        # --- Seção: Sistema & Diagnóstico ---
        ctk.CTkLabel(frm_right, text=t("dev_tools"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("warning")).pack(anchor="w", padx=14, pady=(4, 10))

        ctk.CTkButton(
            frm_right, text=t("roadmap_btn"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            height=38, corner_radius=r, command=lambda: [sound_fx.play_click(), ChangelogTimelineModal(self.app)]
        ).pack(fill="x", padx=14, pady=5)

        ctk.CTkButton(
            frm_right, text=t("set_rate"), font=("Segoe UI", 11, "bold"),
            fg_color="#D97706", hover_color="#B45309", height=38, corner_radius=r,
            command=lambda: [sound_fx.play_click(), webbrowser.open("https://docs.google.com/forms/d/e/1FAIpQLSdV8WZMSQGHtGOnhsdI1mxxAwzIdifNLrkBN1adfvRR9vDkYQ/viewform?usp=publish-editor")]
        ).pack(fill="x", padx=14, pady=5)

        ctk.CTkButton(
            frm_right, text=t("dev_apa_sim"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            height=36, corner_radius=r, command=self.make_apa_test
        ).pack(fill="x", padx=14, pady=5)

        ctk.CTkButton(
            frm_right, text=t("set_log"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            height=36, corner_radius=r, command=self.export_log
        ).pack(fill="x", padx=14, pady=5)

        ctk.CTkButton(
            frm_right, text=t("ver_btn"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            height=36, corner_radius=r, command=lambda: [sound_fx.play_click(), VersionRollbackModal(self.app)]
        ).pack(fill="x", padx=14, pady=(5, 12))

    def _update_bg_preview(self):
        try:
            c_img = str(cfg.data.get("custom_bg_image", "") or "")
            blur_v = int(cfg.data.get("bg_blur", 0) or 0)
            transp_v = int(cfg.data.get("bg_transparency", 0) or 0)
            if _BG_PIL_OK and c_img and os.path.exists(c_img):
                with _BgPILImage.open(c_img) as im:
                    prev = im.convert("RGB").resize((360, 52), _BG_RESAMPLE_BILINEAR)
                if blur_v > 0:
                    prev = prev.filter(_BgPILFilter.GaussianBlur(radius=blur_v * 0.16))
                if transp_v > 0:
                    prev = _BgPILEnhance.Brightness(prev).enhance(max(0.35, 1.0 - transp_v * 0.005))
                self._preview_photo = _BgPILTk.PhotoImage(prev)
                self.bg_preview_lbl.configure(image=self._preview_photo, height=52, bg=cfg.get_color("bg_main"))
            else:
                self._preview_photo = None
                self.bg_preview_lbl.configure(image="", height=2, bg=cfg.get_color("bg_main"))
        except Exception:
            pass

    def _schedule_bg_commit(self, rebuild=False):
        if self._bg_commit_job:
            try:
                self.after_cancel(self._bg_commit_job)
            except Exception:
                pass

        def _commit():
            self._bg_commit_job = None
            cfg.invalidate_palette()
            cfg.save()
            self.app.apply_window_effects(live_alpha_only=False)
            self._update_bg_preview()
            if rebuild:
                self.app.refresh_all_ui()
            else:
                self.app.configure(fg_color=cfg.get_color("bg_main"))
                if hasattr(self.app, "sb") and self.app.sb.winfo_exists():
                    self.app.sb.configure(fg_color=cfg.get_color("bg_sidebar"), border_color=cfg.get_color("border"))

        self._bg_commit_job = self.after(200, _commit)

    def _on_transp_slide(self, val):
        iv = max(0, min(100, int(round(float(val)))))
        self.lbl_transp_val.configure(text=f"{iv}%")
        cfg.data["bg_transparency"] = iv
        cfg.invalidate_palette()
        self.app.apply_window_effects(live_alpha_only=True)
        self._schedule_bg_commit(rebuild=False)

    def _on_blur_slide(self, val):
        iv = max(0, min(100, int(round(float(val)))))
        self.lbl_blur_val.configure(text=f"{iv}%")
        cfg.data["bg_blur"] = iv
        cfg.invalidate_palette()
        self._update_bg_preview()
        self._schedule_bg_commit(rebuild=False)

    def pick_bg_image(self):
        sound_fx.play_click()
        fp = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")]
        )
        if not fp or not os.path.exists(fp):
            return
        ext = os.path.splitext(fp)[1].lower() or ".png"
        dst = os.path.join(APP_DATA_DIR, f"custom_bg{ext}")
        try:
            shutil.copy2(fp, dst)
            cfg.data["custom_bg_image"] = dst
            cfg.data["custom_bg_color"] = ""
            cfg.save()
            sound_fx.play_success()
            self.app.after(30, self.app.refresh_all_ui)
        except Exception:
            sound_fx.play_error()

    def pick_bg_color(self):
        sound_fx.play_click()
        chosen = colorchooser.askcolor(color=cfg.get_color("bg_main"))
        if chosen and chosen[1]:
            cfg.data["custom_bg_color"] = chosen[1]
            cfg.data["custom_bg_image"] = ""
            cfg.save()
            sound_fx.play_success()
            self.app.after(30, self.app.refresh_all_ui)

    def reset_bg_custom(self):
        sound_fx.play_click()
        cfg.data["custom_bg_color"] = ""
        cfg.data["custom_bg_image"] = ""
        cfg.data["bg_transparency"] = 0
        cfg.data["bg_blur"] = 0
        cfg.save()
        self.app.apply_window_effects(live_alpha_only=False)
        self.app.after(30, self.app.refresh_all_ui)

    def make_apa_test(self):
        sound_fx.play_click()
        p = APAManager.create_fake_vhd()
        if p:
            sound_fx.play_success()
            messagebox.showinfo(t("success"), f"Created APA image:\n{p}")

    def export_log(self):
        sound_fx.play_click()
        p = sys_logger.export()
        if p:
            sound_fx.play_success()
            messagebox.showinfo(t("success"), f"{t('set_log')}:\n{p}")


class _LazyPageMap(dict):
    """Constroi cada aba apenas no primeiro acesso, reduzindo o tempo de abertura e troca de tema em ~10x."""
    def __init__(self, factories: dict, aliases: dict = None):
        super().__init__()
        self._factories = dict(factories)
        self._aliases = dict(aliases or {})

    def _resolve_key(self, key):
        return self._aliases.get(key, key)

    def __contains__(self, key):
        rk = self._resolve_key(key)
        return super().__contains__(rk) or (rk in self._factories)

    def __getitem__(self, key):
        rk = self._resolve_key(key)
        if not super().__contains__(rk):
            if rk not in self._factories:
                raise KeyError(key)
            super().__setitem__(rk, self._factories[rk]())
        return super().__getitem__(rk)

    def get(self, key, default=None):
        rk = self._resolve_key(key)
        if rk in self._factories or super().__contains__(rk):
            return self[rk]
        return default

    def instantiated(self):
        return list(super().values())


# ==============================================================================
# APLICAÇÃO PRINCIPAL COM MOTOR DE ANIMAÇÃO MULTI-ESTILO 60 FPS & FUNDO VIVO
# ==============================================================================
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {APP_VERSION}")
        self.geometry("1080x720")
        self.minsize(920, 620)
        self.configure(fg_color=cfg.get_color("bg_main"))

        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.library = LibraryManager()
        self.cur = None
        self.cur_key = None
        self.last_usb = -1
        self.active_transfers = 0
        self._anim_job = None
        self._usb_job = None
        self._usb_probing = False
        self.setup_frame = None
        self._news_checked = False
        self._news_overlay = None
        self._bg_wall_lbl = None
        self._bg_wall_photo = None
        self._bg_wall_sig = None

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Configure>", self._on_root_configure)

        if not cfg.data.get("setup_done", False):
            self.setup_frame = SetupFrame(self, self)
            self.after(60, lambda: self.apply_window_effects(live_alpha_only=False))
        else:
            self.build_main_ui()
            self.after(60, lambda: self.apply_window_effects(live_alpha_only=False))
            self.after(500, self.check_interrupted_transfer)
            self.after(600, self.check_remote_news)

    def apply_window_effects(self, live_alpha_only=False):
        """Aplica transparencia global (0% a 100%) e borrao (0% a 100%) em toda a janela e fundo."""
        try:
            transp = max(0, min(100, int(cfg.data.get("bg_transparency", 0) or 0)))
            alpha = 1.0 if transp <= 0 else round(1.0 - (transp / 100.0) * 0.88, 3)
            self.attributes("-alpha", alpha)
        except Exception:
            pass

        if live_alpha_only:
            return

        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
                is_dark = ctypes.c_int(0 if cfg.data.get("theme") == "Light" else 1)
                for attr_id in (20, 19):
                    try:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr_id, ctypes.byref(is_dark), 4)
                    except Exception:
                        pass
                blur_pct = max(0, min(100, int(cfg.data.get("bg_blur", 0) or 0)))
                backdrop_type = ctypes.c_int(1 if blur_pct <= 0 else (2 if blur_pct < 50 else 3))
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop_type), 4)
                except Exception:
                    pass
            except Exception:
                pass

        self._render_custom_wallpaper()

    def _render_custom_wallpaper(self):
        c_img = str(cfg.data.get("custom_bg_image", "") or "").strip()
        if not (_BG_PIL_OK and c_img and os.path.exists(c_img)):
            if self._bg_wall_lbl is not None and self._bg_wall_lbl.winfo_exists():
                self._bg_wall_lbl.place_forget()
            self._bg_wall_sig = None
            return

        w = max(320, self.winfo_width())
        h = max(240, self.winfo_height())
        blur_pct = max(0, min(100, int(cfg.data.get("bg_blur", 0) or 0)))
        sig = (c_img, w // 16, h // 16, blur_pct)
        if sig == self._bg_wall_sig:
            return
        try:
            with _BgPILImage.open(c_img) as im:
                wall = im.convert("RGB").resize((w, h), _BG_RESAMPLE_BILINEAR)
            if blur_pct > 0:
                wall = wall.filter(_BgPILFilter.GaussianBlur(radius=blur_pct * 0.32))
            wall = _BgPILEnhance.Brightness(wall).enhance(0.55)
            self._bg_wall_photo = _BgPILTk.PhotoImage(wall)
            if self._bg_wall_lbl is None or not self._bg_wall_lbl.winfo_exists():
                self._bg_wall_lbl = tk.Label(self, bd=0, highlightthickness=0, bg=cfg.get_color("bg_main"))
            self._bg_wall_lbl.configure(image=self._bg_wall_photo)
            self._bg_wall_lbl.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            self._bg_wall_lbl.lower()
            self._bg_wall_sig = sig
        except Exception:
            pass

    def _on_root_configure(self, event):
        if event.widget is self and cfg.data.get("custom_bg_image"):
            self._render_custom_wallpaper()

    def build_main_ui(self):
        old_cur_key = self.cur_key
        if self._anim_job:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

        if hasattr(self, 'pages'):
            existing = self.pages.instantiated() if hasattr(self.pages, "instantiated") else list(set(self.pages.values()))
            for p in existing:
                try:
                    p.destroy()
                except Exception:
                    pass
        if hasattr(self, 'setup_frame') and self.setup_frame:
            self.setup_frame.destroy()
            self.setup_frame = None
        if hasattr(self, 'sb'):
            self.sb.destroy()
        if hasattr(self, 'content'):
            self.content.destroy()

        sound_fx.sync_from_config()
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.apply_window_effects(live_alpha_only=False)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sb = ctk.CTkFrame(
            self, width=245, corner_radius=0,
            fg_color=cfg.get_color("bg_sidebar"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.sb.grid(row=0, column=0, sticky="nsew")
        self.sb.grid_propagate(False)
        self.sb.grid_columnconfigure(0, weight=1)
        self.sb.grid_rowconfigure(24, weight=1)

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.btns, self.nav_main, self.nav_more, self.cur, self.cur_key = {}, [], [], None, None

        # Brand Header
        brand = ctk.CTkFrame(self.sb, fg_color="transparent")
        brand.grid(row=0, column=0, pady=(18, 10), padx=18, sticky="ew")
        ctk.CTkLabel(brand, text="PS2", font=("Segoe UI Black", 24), text_color=cfg.get_color("accent")).pack(side="left")
        ctk.CTkLabel(brand, text="MANAGER", font=("Segoe UI Black", 15), text_color=cfg.get_color("text_main")).pack(side="left", padx=(4, 8))
        v_pill = ctk.CTkFrame(brand, fg_color=cfg.get_color("chip_bg"), corner_radius=cfg.get_radius("chip"))
        v_pill.pack(side="left")
        ctk.CTkLabel(v_pill, text=APP_VERSION, font=("Consolas", 10, "bold"), text_color=cfg.get_color("highlight")).pack(padx=7, pady=1)

        self.lbl_sec = ctk.CTkLabel(
            self.sb, text=t("nav_sec_main"), font=("Segoe UI", 9, "bold"),
            text_color=cfg.get_color("text_muted")
        )
        self.lbl_sec.grid(row=1, column=0, padx=20, pady=(2, 4), sticky="w")

        def nav(row, k, txt, group="main"):
            b = ctk.CTkButton(
                self.sb, text=f"  {txt}", font=("Segoe UI", 11, "bold"),
                fg_color="transparent", text_color=cfg.get_color("text_muted"),
                anchor="w", height=35, corner_radius=cfg.get_radius("button"),
                hover_color=cfg.get_hover("card_hover", "bg_sidebar"),
                command=lambda key=k: self.show(key)
            )
            if group == "main":
                b.grid(row=row, column=0, padx=12, pady=2, sticky="ew")
                self.nav_main.append(k)
            else:
                self.nav_more.append(k)
            self.btns[k] = b

        # Navegação Principal (8 abas limpas e intuitivas)
        nav(2, "dash", t("tab_dash"))
        nav(3, "games", t("tab_lib"))
        nav(4, "install", t("tab_install"))
        nav(5, "usb", t("tab_usb"))
        nav(6, "opl_cfg", t("tab_opl_cfg"))
        nav(7, "art", t("tab_art"))
        nav(8, "mc", t("tab_mc"))
        nav(9, "test", t("tab_emu"))

        self.btn_enter_more = ctk.CTkButton(
            self.sb, text=f"  {t('tab_more')}", font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), text_color=cfg.get_color("highlight"),
            anchor="w", height=36, corner_radius=cfg.get_radius("button"),
            hover_color=cfg.get_hover("card_hover", "chip_bg"), command=self.enter_more_tools
        )
        self.btn_enter_more.grid(row=10, column=0, padx=12, pady=(8, 4), sticky="ew")

        self.btn_back_more = ctk.CTkButton(
            self.sb, text=t("btn_back"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("card_base"), hover_color=cfg.get_hover("card_hover", "card_base"),
            text_color=cfg.get_color("highlight"), anchor="w", height=36,
            corner_radius=cfg.get_radius("button"), command=self.exit_more_tools
        )

        # Ferramentas Avançadas (9 abas organizadas)
        nav(3, "iso", t("tab_iso"), group="more")
        nav(4, "patcher", t("tab_patcher"), group="more")
        nav(5, "pops", t("tab_pops"), group="more")
        nav(6, "burn", t("tab_burn"), group="more")
        nav(7, "rip_disc", t("tab_rip"), group="more")
        nav(8, "disk_ops", t("tab_mig"), group="more")
        nav(9, "cheats", t("tab_cht"), group="more")
        nav(10, "apps", t("tab_apps"), group="more")
        nav(11, "apa", t("apa_title"), group="more")

        # Badge de Modo Batata se ativo
        if cfg.is_potato():
            p_badge = ctk.CTkFrame(self.sb, fg_color=cfg.get_color("card_base"), corner_radius=0)
            p_badge.grid(row=25, column=0, padx=12, pady=(0, 6), sticky="ew")
            ctk.CTkLabel(
                p_badge, text=t("set_potato_badge"), font=("Consolas", 10, "bold"),
                text_color=cfg.get_color("warning")
            ).pack(pady=4)

        self.btns["settings"] = ctk.CTkButton(
            self.sb, text=f"  ⚙  {t('tab_set')}", font=("Segoe UI", 11, "bold"),
            fg_color="transparent", text_color=cfg.get_color("text_muted"),
            anchor="w", height=36, corner_radius=cfg.get_radius("button"),
            hover_color=cfg.get_hover("card_hover", "bg_sidebar"),
            command=lambda: self.show("settings")
        )
        self.btns["settings"].grid(row=26, column=0, padx=12, pady=(0, 14), sticky="sew")

        self.pages = _LazyPageMap(
            {
                "dash": lambda: DashboardPage(self.content, self),
                "games": lambda: GamesPage(self.content, self),
                "install": lambda: UnifiedInstallPage(self.content, self),
                "usb": lambda: UsbOptimizerPage(self.content, self),
                "opl_cfg": lambda: OplConfigPage(self.content, self),
                "art": lambda: ArtScraperV2Page(self.content, self),
                "mc": lambda: MemoryCardPage(self.content, self),
                "test": lambda: EmulatorTestPage(self.content, self),
                "iso": lambda: IsoStudioPage(self.content, self),
                "patcher": lambda: IsoPatcherV2Page(self.content, self),
                "pops": lambda: PopStarterPage(self.content, self),
                "burn": lambda: DvdBurnerPage(self.content, self),
                "rip_disc": self._build_optical_disc_page,
                "disk_ops": self._build_disk_ops_page,
                "cheats": lambda: CheatManagerPage(self.content, self),
                "apps": lambda: AppsManagerPage(self.content, self),
                "apa": self._build_apa_page,
                "settings": lambda: SettingsPage(self.content, self),
            },
            aliases={"single_install": "install"}
        )

        if old_cur_key in self.nav_more:
            self.enter_more_tools(play_snd=False)
            self.show(old_cur_key, play_snd=False)
        else:
            self.show(old_cur_key if old_cur_key in self.pages else "dash", play_snd=False)

        if self._usb_job is None:
            self.monitor_usb()

        if self._news_overlay and self._news_overlay.winfo_exists():
            self._news_overlay.lift()

    def check_remote_news(self):
        if self.setup_frame is not None:
            return
        dispatch = lambda notice: self.after(0, lambda n=notice: self._show_remote_news(n))
        if not self._news_checked:
            self._news_checked = True
            RemoteNoticeClient.fetch_async(dispatch)
        RemoteNoticeClient.start_live_watcher(self, dispatch)

    def _show_remote_news(self, notice: dict):
        if not notice or not self.winfo_exists() or (self.setup_frame is not None):
            return
        news_id = int(notice.get("id", 0) or 0)
        prev_backdrop = None
        if self._news_overlay and self._news_overlay.winfo_exists():
            if getattr(self._news_overlay, "news_id", 0) == news_id:
                return
            prev_backdrop = getattr(self._news_overlay, "_base_dim_pil", None)
            self._news_overlay.destroy()
            self._news_overlay = None
            self.update_idletasks()
        try:
            if self.state() == "iconic":
                self.deiconify()
                self.update()
            self.lift()
            self.attributes("-topmost", True)
            self.after(220, lambda: self.attributes("-topmost", False) if self.winfo_exists() else None)
        except Exception:
            pass
        self._news_overlay = NewsOverlayModal(self, notice, base_dim_pil=prev_backdrop)

    def _build_optical_disc_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_rowconfigure(2, weight=1)
        PageHeader(frm, t("tab_rip"), "").grid(row=0, column=0, sticky="ew", pady=(0, 12))

        tabs = [t("tab_rip"), t("tab_disc")]
        f_rip = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        f_ana = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))

        def sw(v):
            f_rip.grid_forget()
            f_ana.grid_forget()
            (f_rip if v == tabs[0] else f_ana).grid(row=2, column=0, sticky="nsew")

        seg = create_segmented_tabs(frm, tabs, sw)
        seg.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        drvs = PhysicalDriveRipper.get_optical_drives() or [t("disc_none")]
        ctk.CTkLabel(f_rip, text=t("disc_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        cmb_d = ctk.CTkComboBox(f_rip, values=drvs, height=34, corner_radius=cfg.get_radius("entry"))
        cmb_d.pack(fill="x", padx=20)
        ctk.CTkLabel(f_rip, text=t("rip_out"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(14, 5))
        r_o = ctk.CTkFrame(f_rip, fg_color="transparent")
        r_o.pack(fill="x", padx=20)
        e_o = ctk.CTkEntry(r_o, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        e_o.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(r_o, text=t("btn_browse"), width=90, height=34, corner_radius=cfg.get_radius("button"), command=lambda: [sound_fx.play_click(), e_o.delete(0, 'end'), e_o.insert(0, filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[(t("iso_files"), "*.iso")]) or "")]).pack(side="left")
        prog = ctk.CTkProgressBar(f_rip, progress_color=cfg.get_color("highlight"))
        prog.pack(fill="x", padx=20, pady=(20, 10))
        prog.set(0)
        btn_r = ctk.CTkButton(f_rip, text=t("rip_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=42, corner_radius=cfg.get_radius("button"))
        btn_r.pack(pady=(6, 20), padx=20, fill="x")

        def go_rip():
            sound_fx.play_click()
            if cmb_d.get() == t("disc_none") or not e_o.get():
                return
            btn_r.configure(state="disabled")
            PhysicalDriveRipper.rip_drive(
                cmb_d.get(), e_o.get(), True,
                lambda v: self.after(0, lambda: prog.set(v)),
                lambda out_f: self.after(0, lambda: [btn_r.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), f"{t('rip_done')}\n{out_f}")]),
                lambda e: self.after(0, lambda: [btn_r.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("error"), str(e))])
            )
        btn_r.configure(command=go_rip)

        cmb_a = ctk.CTkComboBox(f_ana, values=drvs, height=34, corner_radius=cfg.get_radius("entry"))
        cmb_a.pack(fill="x", padx=20, pady=(20, 10))
        txt = ctk.CTkTextbox(f_ana, font=("Consolas", 12), height=190, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry"))
        txt.pack(fill="x", padx=20, pady=10)

        def go_ana():
            sound_fx.play_click()
            if cmb_a.get() == t("disc_none"):
                return
            txt.delete("1.0", "end")
            txt.insert("end", "Analyzing physical optical disc...\n")

            def r():
                info = PhysicalDriveRipper.analyze_disc(cmb_a.get())
                out = f"=== OPTICAL DISC ANALYSIS ===\nDrive  : {cmb_a.get()}\nStatus : {info['status']}\nVolume : {info['size_str']}\nGame ID: {info['game_id']}\nRegion : {info['region']}\n"
                self.after(0, lambda: [txt.delete("1.0", "end"), txt.insert("end", out), sound_fx.play_success()])
            threading.Thread(target=r, daemon=True).start()

        ctk.CTkButton(f_ana, text=t("disc_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=42, corner_radius=cfg.get_radius("button"), command=go_ana).pack(pady=15, padx=20, fill="x")
        sw(tabs[0])
        return frm

    def _build_disk_ops_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_rowconfigure(2, weight=1)
        PageHeader(frm, t("tab_mig"), "").grid(row=0, column=0, sticky="ew", pady=(0, 12))

        tabs = [t("sub_clone")[2:].strip(), t("tab_mig")]
        f_cln = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        f_mig = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))

        def sw(v):
            f_cln.grid_forget()
            f_mig.grid_forget()
            (f_cln if v == tabs[0] else f_mig).grid(row=2, column=0, sticky="nsew")

        create_segmented_tabs(frm, tabs, sw).grid(row=1, column=0, sticky="ew", pady=(0, 12))
        d_vals = [f"{d['device']} [{d['fstype']}]" for d in DriveManager.get_drives()] or ["None"]

        # Clone
        ctk.CTkLabel(f_cln, text=t("clone_src"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        cmb_s = ctk.CTkComboBox(f_cln, values=d_vals, height=34, corner_radius=cfg.get_radius("entry"))
        cmb_s.pack(fill="x", padx=20)
        ctk.CTkLabel(f_cln, text=t("clone_dst"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(12, 4))
        cmb_d = ctk.CTkComboBox(f_cln, values=d_vals, height=34, corner_radius=cfg.get_radius("entry"))
        cmb_d.pack(fill="x", padx=20)
        chk_f = ctk.CTkCheckBox(f_cln, text=t("clone_fmt_dst"), font=("Segoe UI", 11), command=sound_fx.play_click)
        chk_f.pack(anchor="w", padx=20, pady=12)
        log_c = ctk.CTkTextbox(f_cln, font=("Consolas", 10), height=95, fg_color=cfg.get_color("bg_main"))
        log_c.pack(fill="x", padx=20, pady=4)
        prog_c = ctk.CTkProgressBar(f_cln, progress_color=cfg.get_color("highlight"))
        prog_c.pack(fill="x", padx=20, pady=8)
        prog_c.set(0)

        def run_c():
            sound_fx.play_click()
            s_val, d_val = cmb_s.get().split(" ")[0], cmb_d.get().split(" ")[0]
            if s_val == "None" or d_val == "None" or s_val == d_val:
                return
            drives = DriveManager.get_drives()
            s_d = next((d for d in drives if d['device'] == s_val), None)
            d_d = next((d for d in drives if d['device'] == d_val), None)
            if not s_d or not d_d:
                return
            w = CloneWorker(s_d, d_d, chk_f.get(), False, {
                'log': lambda m: self.after(0, lambda: log_c.insert("end", m + "\n")),
                'prog_total': lambda v: self.after(0, lambda: prog_c.set(v)),
                'done': lambda s: self.after(0, lambda: sound_fx.play_success() if s else sound_fx.play_error())
            })
            threading.Thread(target=w.run, daemon=True).start()

        ctk.CTkButton(f_cln, text=t("clone_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"), command=run_c).pack(pady=14, padx=20, fill="x")

        # Migrate
        ctk.CTkLabel(f_mig, text=t("mig_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        cmb_md = ctk.CTkComboBox(f_mig, values=d_vals, height=34, corner_radius=cfg.get_radius("entry"))
        cmb_md.pack(fill="x", padx=20)
        ctk.CTkLabel(f_mig, text=t("mig_fs"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(12, 4))
        cmb_mf = ctk.CTkComboBox(f_mig, values=["exFAT", "FAT32"], height=34, corner_radius=cfg.get_radius("entry"))
        cmb_mf.pack(fill="x", padx=20)
        log_m = ctk.CTkTextbox(f_mig, font=("Consolas", 10), height=105, fg_color=cfg.get_color("bg_main"))
        log_m.pack(fill="x", padx=20, pady=12)
        prog_m = ctk.CTkProgressBar(f_mig, progress_color=cfg.get_color("highlight"))
        prog_m.pack(fill="x", padx=20, pady=4)
        prog_m.set(0)

        def run_m():
            sound_fx.play_click()
            dev = cmb_md.get().split(" ")[0]
            d = next((x for x in DriveManager.get_drives() if x['device'] == dev), None)
            if not d or not messagebox.askyesno(t("confirm"), t("mig_conf")):
                return
            w = MigrationWorker(d, cmb_mf.get(), {
                'log': lambda m: self.after(0, lambda: log_m.insert("end", m + "\n")),
                'prog_total': lambda v: self.after(0, lambda: prog_m.set(v)),
                'prog_step': lambda v: None,
                'done': lambda s: self.after(0, lambda: sound_fx.play_success() if s else sound_fx.play_error())
            })
            threading.Thread(target=w.run, daemon=True).start()

        ctk.CTkButton(f_mig, text=t("mig_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("danger"), height=40, corner_radius=cfg.get_radius("button"), command=run_m).pack(pady=14, padx=20, fill="x")
        sw(tabs[0])
        return frm

    def _build_apa_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_rowconfigure(2, weight=1)
        PageHeader(frm, t("apa_title"), "", badge_text="HDL / +OPL").grid(row=0, column=0, sticky="ew", pady=(0, 14))

        top = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(top, text=t("apa_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        d_vals = APAManager.list_physical_drives() or ["\\\\.\\PhysicalDrive1"]
        cmb_p = ctk.CTkComboBox(top, values=d_vals, height=34, corner_radius=cfg.get_radius("entry"))
        cmb_p.pack(fill="x", padx=16, pady=4)

        prog_apa = ctk.CTkProgressBar(top, progress_color=cfg.get_color("highlight"))
        prog_apa.pack(fill="x", padx=16, pady=(8, 4))
        prog_apa.set(0)

        bar = ctk.CTkFrame(top, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(6, 14))
        list_apa = ctk.CTkScrollableFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        list_apa.grid(row=2, column=0, sticky="nsew")

        def render_parts(parts):
            for w in list_apa.winfo_children():
                w.destroy()
            for p in parts:
                r = ctk.CTkFrame(list_apa, fg_color=cfg.get_color("bg_main"), height=40, corner_radius=cfg.get_radius("chip"))
                r.pack(fill="x", pady=3, padx=6)
                r.pack_propagate(False)
                ctk.CTkLabel(r, text=p['name'], font=("Consolas", 12, "bold"), text_color=cfg.get_color("highlight" if p['is_game'] else "accent")).pack(side="left", padx=12)
                ctk.CTkLabel(r, text=f"{p['size_str']} • Sector {p['start']}", font=("Consolas", 10), text_color=cfg.get_color("text_muted")).pack(side="right", padx=14)

        def open_img():
            sound_fx.play_click()
            f = filedialog.askopenfilename(filetypes=[("APA Disk Image", "*.img *.bin *.raw")])
            if f:
                cmb_p.set(f)
                parts = APAManager.read_apa_partitions(f)
                sound_fx.play_success()
                render_parts(parts)

        def scan_drv():
            sound_fx.play_click()
            parts = APAManager.read_apa_partitions(cmb_p.get())
            sound_fx.play_success() if parts else sound_fx.play_warning()
            render_parts(parts)

        def dump_raw():
            sound_fx.play_click()
            dst = filedialog.asksaveasfilename(defaultextension=".img", filetypes=[("Raw Image", "*.img")])
            if dst:
                APAManager.backup_raw(
                    cmb_p.get(), dst,
                    cb_prog=lambda v: self.after(0, lambda: prog_apa.set(v)),
                    cb_done=lambda _: self.after(0, lambda: [sound_fx.play_success(), NotificationPopup(self, "APA Backup saved!", "success")]),
                    cb_err=lambda e: self.after(0, lambda: [sound_fx.play_error(), messagebox.showerror(t("error"), e)])
                )

        def ext_games():
            sound_fx.play_click()
            dst = filedialog.askdirectory()
            if dst:
                APAManager.extract_contents(
                    cmb_p.get(), dst,
                    cb_prog=lambda v: self.after(0, lambda: prog_apa.set(v)),
                    cb_done=lambda _: self.after(0, lambda: [sound_fx.play_success(), NotificationPopup(self, t("iso_succ"), "success")]),
                    cb_err=lambda e: self.after(0, lambda: [sound_fx.play_error(), messagebox.showerror(t("error"), e)])
                )

        ctk.CTkButton(bar, text=t("apa_btn_open"), height=34, corner_radius=cfg.get_radius("button"), command=open_img).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(bar, text=t("apa_btn_scan_drv"), height=34, fg_color=cfg.get_color("chip_bg"), corner_radius=cfg.get_radius("button"), command=scan_drv).pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(bar, text=t("apa_btn_raw"), height=34, corner_radius=cfg.get_radius("button"), command=dump_raw).pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(bar, text=t("apa_btn_ext"), height=34, fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=ext_games).pack(side="left", expand=True, fill="x", padx=(4, 0))
        return frm

    def enter_more_tools(self, play_snd=True):
        if play_snd:
            sound_fx.play_tab()
        self.lbl_sec.configure(text=t("nav_sec_tools"))
        for k in self.nav_main:
            self.btns[k].grid_remove()
        self.btn_enter_more.grid_remove()
        self.btn_back_more.grid(row=2, column=0, padx=12, pady=(4, 10), sticky="ew")
        for i, k in enumerate(self.nav_more):
            self.btns[k].grid(row=3 + i, column=0, padx=12, pady=2, sticky="ew")
        if play_snd:
            self.show(self.nav_more[0], play_snd=False)

    def exit_more_tools(self):
        sound_fx.play_tab()
        self.lbl_sec.configure(text=t("nav_sec_main"))
        self.btn_back_more.grid_remove()
        for k in self.nav_more:
            self.btns[k].grid_remove()
        for k in self.nav_main:
            self.btns[k].grid()
        self.btn_enter_more.grid()
        self.show("dash", play_snd=False)

    def show(self, k, play_snd=True):
        target_page = self.pages.get(k)
        if not target_page or self.cur == target_page:
            return

        if play_snd:
            sound_fx.play_tab()

        if self._anim_job:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

        self.library.sync_drives()
        nav_key = "install" if k == "single_install" else k
        for b_key, b in self.btns.items():
            if b_key == nav_key:
                b.configure(fg_color=cfg.get_color("accent"), text_color="#FFFFFF")
            else:
                b.configure(fg_color="transparent", text_color=cfg.get_color("text_muted"))

        if self.cur:
            self.cur.place_forget()

        self.cur = target_page
        self.cur_key = nav_key
        getattr(self.cur, "refresh", lambda: None)()

        # Modo Batata ou animações desligadas: exibição plana instantânea (0 ms)
        if cfg.is_potato() or not cfg.data.get("animations", True):
            self.cur.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
            return

        style = cfg.data.get("anim_style", "Slide")
        steps = 8 if style != "Step" else 2

        def animate_frame(step_i):
            prog = step_i / steps
            ease = 1.0 - ((1.0 - prog) ** 3)  # Cubic ease-out suave a 60fps
            if step_i >= steps:
                self.cur.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
                self._anim_job = None
                return
            if style == "Slide":
                rx = 0.055 * (1.0 - ease)
                self.cur.place(relx=rx, rely=0.0, relwidth=1.0, relheight=1.0)
            elif style == "Rise":
                ry = 0.05 * (1.0 - ease)
                self.cur.place(relx=0.0, rely=ry, relwidth=1.0, relheight=1.0)
            elif style == "Zoom":
                sc = 0.94 + (0.06 * ease)
                off = (1.0 - sc) / 2.0
                self.cur.place(relx=off, rely=off, relwidth=sc, relheight=sc)
            else:  # Step
                rx = 0.02 * (1.0 - ease)
                self.cur.place(relx=rx, rely=0.0, relwidth=1.0, relheight=1.0)
            self._anim_job = self.after(15, lambda: animate_frame(step_i + 1))

        animate_frame(1)

    def refresh_all_ui(self):
        cfg.apply_theme()
        self.configure(fg_color=cfg.get_color("bg_main"))
        if hasattr(self, 'setup_frame') and self.setup_frame:
            self.setup_frame.configure(fg_color=cfg.get_color("bg_main"))
        else:
            self.build_main_ui()

    def on_closing(self):
        if TransferLockManager.is_busy() or self.active_transfers > 0:
            sound_fx.play_error()
            messagebox.showwarning(t("warning"), t("msg_corruption_warn"))
            return
        sound_fx.play_close()
        self.destroy()
        sys.exit(0)

    def check_interrupted_transfer(self):
        lock_file = os.path.join(APP_DATA_DIR, "active_transfer.lock")
        if os.path.exists(lock_file):
            sound_fx.play_warning()
            if messagebox.askyesno(t("recovery_title"), t("recovery_msg")):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
                self.show("install")
            else:
                try:
                    os.remove(lock_file)
                except Exception:
                    pass

    def refresh_all(self):
        active_pages = self.pages.instantiated() if hasattr(self.pages, "instantiated") else list(set(self.pages.values()))
        for p in active_pages:
            getattr(p, "refresh", lambda: None)()

    def _apply_usb_count(self, c: int):
        try:
            if not self.winfo_exists():
                return
            if self.last_usb != -1 and c != self.last_usb:
                sound_fx.play_usb(connected=(c > self.last_usb))
                if c > self.last_usb:
                    NotificationPopup(self, t("notif_usb_connected"), "info")
                self.library.sync_drives(force=True)
                self.refresh_all()
            self.last_usb = c
        except Exception:
            pass

    def monitor_usb(self):
        if not self._usb_probing and not TransferLockManager.is_busy():
            self._usb_probing = True

            def _probe():
                try:
                    c = len(UsbDetector.get_removable_drives(force=True))
                    if self.winfo_exists():
                        self.after(0, lambda cnt=c: self._apply_usb_count(cnt))
                except Exception:
                    pass
                finally:
                    self._usb_probing = False

            threading.Thread(target=_probe, daemon=True).start()

        interval = 8000 if cfg.is_potato() else 3500
        self._usb_job = self.after(interval, self.monitor_usb)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
