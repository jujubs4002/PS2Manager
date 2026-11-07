from __future__ import annotations

import os
import sys
import ctypes
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox

from scripts.core_backend import (
    cfg, t, format_size, sound_fx, sys_logger, get_res_path, PIL_SUPPORT
)
from scripts.tool_workers import (
    DriveManager, UsbDetector, ArtScraperWorker, RealIsoTool, BinConverter,
    PCSX2Integration
)
from scripts.v108_workers import (
    UsbDefragWorker, OplCfgManager, PopStarterConverter,
    WidescreenNtscPatcher, ArtScraperV2Worker, MemoryCardManager
)

if PIL_SUPPORT:
    from PIL import Image


def apply_window_icon(w):
    icon_path = get_res_path("icon.ico")
    if os.path.exists(icon_path):
        try:
            w.iconbitmap(icon_path)
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                u32 = ctypes.windll.user32
                u32.GetParent.restype = ctypes.c_void_p
                u32.LoadImageW.restype = ctypes.c_void_p
                hwnd = u32.GetParent(w.winfo_id()) or w.winfo_id()
                LR_LOADFROMFILE = 0x00000010
                IMAGE_ICON = 1
                WM_SETICON = 0x0080
                h_icon_sm = u32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if h_icon_sm and hwnd:
                    u32.SendMessageW(hwnd, WM_SETICON, 0, h_icon_sm)
                h_icon_lg = u32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                if h_icon_lg and hwnd:
                    u32.SendMessageW(hwnd, WM_SETICON, 1, h_icon_lg)
            except Exception:
                pass


class NotificationPopup(ctk.CTkFrame):
    def __init__(self, master, message, kind="info"):
        color = cfg.get_color("accent")
        prefix = "ℹ"
        if kind == "success":
            color = cfg.get_color("success")
            prefix = "✔"
        elif kind == "error":
            color = cfg.get_color("danger")
            prefix = "✖"
        elif kind == "warning":
            color = cfg.get_color("warning")
            prefix = "⚠"
        super().__init__(
            master, fg_color=color,
            corner_radius=cfg.get_radius("chip"),
            border_width=cfg.get_border_width(),
            border_color="#FFFFFF"
        )
        ctk.CTkLabel(
            self, text=f"{prefix}  {message}",
            font=("Segoe UI", 12, "bold"), text_color="#FFFFFF"
        ).pack(padx=22, pady=10)
        self.place(relx=0.5, rely=0.04, anchor="n")
        self.lift()
        self.after(3200, self.dismiss)

    def dismiss(self):
        try:
            self.destroy()
        except Exception:
            pass


class HoverCard(ctk.CTkFrame):
    """Card moderno com suporte integral ao Modo Batata (zero bindings e cantos retos)."""
    def __init__(self, master, **kwargs):
        self.default_fg = kwargs.get("fg_color", cfg.get_color("card_base"))
        self.hover_fg = kwargs.pop("hover_color", cfg.get_color("card_hover"))
        self.on_click_cb = kwargs.pop("command", None)
        kwargs.setdefault("corner_radius", cfg.get_radius("card"))
        kwargs.setdefault("border_width", cfg.get_border_width())
        kwargs.setdefault("border_color", cfg.get_color("border"))
        super().__init__(master, **kwargs)
        if not cfg.is_potato():
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
        if self.on_click_cb:
            self.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        if cfg.data.get("animations", True) and not cfg.is_potato():
            self.configure(fg_color=self.hover_fg)

    def _on_leave(self, e):
        if not cfg.is_potato():
            self.configure(fg_color=self.default_fg)

    def _on_click(self, e):
        if self.on_click_cb:
            sound_fx.play_click()
            self.on_click_cb()

    def bind_children(self, widget=None):
        target = widget or self
        if target is not self:
            if not cfg.is_potato():
                target.bind("<Enter>", self._on_enter)
                target.bind("<Leave>", self._on_leave)
            if self.on_click_cb:
                target.bind("<Button-1>", self._on_click)
        for child in target.winfo_children():
            self.bind_children(child)


class PageHeader(ctk.CTkFrame):
    """Cabeçalho padronizado, espaçoso e elegante com barra de destaque, título, badge e subtítulo."""
    def __init__(self, master, title_text, subtitle_text="", badge_text=None, right_widget_builder=None):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)

        accent_bar = ctk.CTkFrame(
            self, width=5, height=34 if subtitle_text else 26,
            fg_color=cfg.get_color("accent"),
            corner_radius=0 if cfg.is_potato() else 3
        )
        accent_bar.grid(row=0, column=0, rowspan=2 if subtitle_text else 1, sticky="ns", padx=(0, 12), pady=2)

        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            title_row, text=title_text,
            font=("Segoe UI Black", 20), text_color=cfg.get_color("text_main")
        ).pack(side="left")

        if badge_text:
            badge = ctk.CTkFrame(
                title_row, fg_color=cfg.get_color("chip_bg"),
                corner_radius=cfg.get_radius("chip"),
                border_width=cfg.get_border_width(), border_color=cfg.get_color("accent")
            )
            badge.pack(side="left", padx=10)
            ctk.CTkLabel(
                badge, text=badge_text, font=("Consolas", 10, "bold"),
                text_color=cfg.get_color("highlight")
            ).pack(padx=8, pady=2)

        if subtitle_text:
            ctk.CTkLabel(
                self, text=subtitle_text,
                font=("Segoe UI", 12), text_color=cfg.get_color("text_muted"),
                anchor="w"
            ).grid(row=1, column=1, sticky="w", pady=(2, 0))

        if right_widget_builder:
            right_box = ctk.CTkFrame(self, fg_color="transparent")
            right_box.grid(row=0, column=2, rowspan=2, sticky="e")
            right_widget_builder(right_box)


def create_segmented_tabs(master, values, on_change):
    def _wrapped(val):
        sound_fx.play_tab()
        on_change(val)

    seg = ctk.CTkSegmentedButton(
        master,
        values=values,
        font=("Segoe UI", 12, "bold"),
        height=36,
        corner_radius=cfg.get_radius("button"),
        fg_color=cfg.get_color("card_base"),
        selected_color=cfg.get_color("accent"),
        selected_hover_color=cfg.get_hover("accent_hover", "accent"),
        unselected_color=cfg.get_color("card_base"),
        unselected_hover_color=cfg.get_hover("card_hover", "card_base"),
        text_color=cfg.get_color("text_main"),
        command=_wrapped
    )
    if values:
        seg.set(values[0])
    return seg


# ==============================================================================
# PÁGINA 1: USB MANAGER & OTIMIZADOR ANTI-TELA PRETA (FRAGMENTAÇÃO & HASH)
# ==============================================================================
class HashReportModal(ctk.CTkToplevel):
    def __init__(self, master, info):
        super().__init__(master)
        self.title("MD5 / SHA-1 / CRC32")
        self.geometry("540x320")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        ctk.CTkLabel(
            self, text=info["filename"], font=("Segoe UI Black", 15),
            text_color=cfg.get_color("highlight")
        ).pack(pady=(18, 4), padx=20)
        ctk.CTkLabel(
            self, text=f"{t('game_size')}: {info['size_str']}",
            font=("Consolas", 11), text_color=cfg.get_color("text_muted")
        ).pack(pady=(0, 12))

        box = ctk.CTkTextbox(
            self, font=("Consolas", 12), height=130,
            fg_color=cfg.get_color("card_base"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border"),
            corner_radius=cfg.get_radius("card")
        )
        box.pack(fill="x", padx=20, pady=6)
        report_txt = (
            f"CRC32 : {info['crc32']}\n"
            f"MD5   : {info['md5']}\n"
            f"SHA-1 : {info['sha1']}\n"
        )
        box.insert("1.0", report_txt)

        def copy_clip():
            self.clipboard_clear()
            self.clipboard_append(report_txt)
            sound_fx.play_success()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(
            btn_row, text="COPY HASHES", height=36,
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=copy_clip
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            btn_row, text=t("btn_close"), height=36,
            fg_color=cfg.get_color("card_base"), hover_color=cfg.get_hover("card_hover", "card_base"),
            corner_radius=cfg.get_radius("button"), command=lambda: [sound_fx.play_close(), self.destroy()]
        ).pack(side="right", expand=True, fill="x", padx=(6, 0))


class UsbOptimizerPage(ctk.CTkFrame):
    """Unifica Gerenciador de Unidades OPL + Verificador de Fragmentação & Hash (Anti-Tela Preta)."""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        PageHeader(self, t("tab_usb"), t("usb_sub"), badge_text="ANTI-BLACK SCREEN").grid(
            row=0, column=0, sticky="ew", pady=(0, 12)
        )

        self.tab_names = [t("usb_mode_drives"), t("usb_mode_defrag")]
        self.seg = create_segmented_tabs(self, self.tab_names, self.switch_mode)
        self.seg.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.frm_drives = ctk.CTkFrame(self.body, fg_color="transparent")
        self.frm_defrag = ctk.CTkFrame(self.body, fg_color="transparent")
        self.selected_game_item = None
        self.scanned_items = []

        self._build_drives_subpage()
        self._build_defrag_subpage()
        self.switch_mode(self.tab_names[0])

    def _build_drives_subpage(self):
        self.frm_drives.grid_columnconfigure(0, weight=1)
        self.frm_drives.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self.frm_drives, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(
            top, text=t("usb_ref"), width=120, height=34, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"),
            command=lambda: [sound_fx.play_click(), self.refresh()]
        ).pack(side="right")

        self.drives_list = ctk.CTkScrollableFrame(
            self.frm_drives, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.drives_list.grid(row=1, column=0, sticky="nsew")

    def _build_defrag_subpage(self):
        self.frm_defrag.grid_columnconfigure(0, weight=1)
        self.frm_defrag.grid_rowconfigure(1, weight=1)

        ctrl = ctk.CTkFrame(
            self.frm_defrag, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctrl.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ctrl, text=t("opl_target_root"), font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=12, sticky="w")
        self.cmb_defrag_drv = ctk.CTkComboBox(
            ctrl, values=[t("inst_err_nodrive")], height=34,
            corner_radius=cfg.get_radius("entry")
        )
        self.cmb_defrag_drv.grid(row=0, column=1, padx=(0, 8), pady=12, sticky="ew")

        ctk.CTkButton(
            ctrl, text=t("btn_browse"), width=95, height=34, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=cfg.get_radius("button"), command=self.browse_defrag_folder
        ).grid(row=0, column=2, padx=(0, 8), pady=12)

        self.btn_scan_defrag = ctk.CTkButton(
            ctrl, text=t("defrag_scan_btn"), height=34, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.scan_fragmentation
        )
        self.btn_scan_defrag.grid(row=0, column=3, padx=(0, 15), pady=12)

        self.defrag_scroll = ctk.CTkScrollableFrame(
            self.frm_defrag, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.defrag_scroll.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        bot = ctk.CTkFrame(
            self.frm_defrag, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        bot.grid(row=2, column=0, sticky="ew")

        btn_row = ctk.CTkFrame(bot, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(12, 8))

        self.btn_opt_sel = ctk.CTkButton(
            btn_row, text=t("defrag_fix_one"), height=36, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.optimize_selected
        )
        self.btn_opt_sel.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.btn_opt_all = ctk.CTkButton(
            btn_row, text=t("defrag_fix_all"), height=36, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("warning"), text_color="#000000",
            corner_radius=cfg.get_radius("button"), command=self.optimize_all
        )
        self.btn_opt_all.pack(side="left", expand=True, fill="x", padx=6)

        self.btn_hash = ctk.CTkButton(
            btn_row, text=t("defrag_hash_btn"), height=36, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.verify_selected_hash
        )
        self.btn_hash.pack(side="left", expand=True, fill="x", padx=(6, 0))

        self.lbl_defrag_status = ctk.CTkLabel(
            bot, text=t("inst_ready"), font=("Consolas", 11),
            text_color=cfg.get_color("text_muted")
        )
        self.lbl_defrag_status.pack(anchor="w", padx=16, pady=(0, 4))

        self.prog_defrag = ctk.CTkProgressBar(bot, progress_color=cfg.get_color("highlight"))
        self.prog_defrag.pack(fill="x", padx=16, pady=(0, 12))
        self.prog_defrag.set(0)

    def switch_mode(self, mode_label):
        self.frm_drives.grid_forget()
        self.frm_defrag.grid_forget()
        if mode_label == self.tab_names[0]:
            self.frm_drives.grid(row=0, column=0, sticky="nsew")
        else:
            self.frm_defrag.grid(row=0, column=0, sticky="nsew")
            if not self.scanned_items:
                self._render_defrag_items()

    def switch_to_defrag(self):
        self.seg.set(self.tab_names[1])
        self.switch_mode(self.tab_names[1])

    def browse_defrag_folder(self):
        sound_fx.play_click()
        p = filedialog.askdirectory()
        if p:
            self.cmb_defrag_drv.set(p)
            self.scan_fragmentation()

    def _fix_opl_folders(self, mp):
        sound_fx.play_click()
        DriveManager.create_opl_structure(mp)
        sound_fx.play_success()
        NotificationPopup(self.app, t("usb_fix_done"), "success")
        self.refresh()

    def refresh(self):
        drives = UsbDetector.get_removable_drives()
        # Atualiza combo da aba de desfragmentação
        d_vals = [d["mountpoint"] for d in drives]
        if d_vals:
            self.cmb_defrag_drv.configure(values=d_vals)
            if self.cmb_defrag_drv.get() in ("", t("inst_err_nodrive")):
                self.cmb_defrag_drv.set(d_vals[0])
        else:
            self.cmb_defrag_drv.configure(values=[t("inst_err_nodrive")])

        # Renderiza lista de unidades OPL
        for w in self.drives_list.winfo_children():
            w.destroy()
        if not drives:
            ctk.CTkLabel(
                self.drives_list, text=t("dash_no_usb"),
                font=("Segoe UI", 13), text_color=cfg.get_color("text_muted")
            ).pack(pady=50)
            return

        for d in drives:
            mp = d["mountpoint"]
            opl_info = DriveManager.analyze_opl_structure(mp)
            card = HoverCard(self.drives_list, fg_color=cfg.get_color("bg_main"))
            card.pack(fill="x", padx=10, pady=8)

            top_r = ctk.CTkFrame(card, fg_color="transparent")
            top_r.pack(fill="x", padx=16, pady=(12, 6))
            ctk.CTkLabel(
                top_r, text=f"{mp}  [{d['fstype']}]",
                font=("Segoe UI Black", 15), text_color=cfg.get_color("highlight")
            ).pack(side="left")
            ctk.CTkLabel(
                top_r, text=f"{d['used_str']} / {d['total_str']}  ({d['free_str']} free)",
                font=("Consolas", 11, "bold"), text_color=cfg.get_color("text_muted")
            ).pack(side="right")

            bar = ctk.CTkProgressBar(card, height=8, progress_color=cfg.get_color("accent"))
            bar.pack(fill="x", padx=16, pady=(0, 10))
            bar.set(min(1.0, d["percent"] / 100.0))

            pills_row = ctk.CTkFrame(card, fg_color="transparent")
            pills_row.pack(fill="x", padx=16, pady=(0, 12))
            for folder_name, exists in opl_info["folders"].items():
                col = cfg.get_color("success") if exists else cfg.get_color("text_muted")
                lbl_txt = f"✔ {folder_name}" if exists else f"• {folder_name}"
                ctk.CTkLabel(
                    pills_row, text=lbl_txt, font=("Consolas", 10, "bold"), text_color=col
                ).pack(side="left", padx=(0, 10))

            ctk.CTkButton(
                pills_row, text=t("usb_fix_btn"), height=28, font=("Segoe UI", 11, "bold"),
                fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
                corner_radius=cfg.get_radius("button"),
                command=lambda m=mp: self._fix_opl_folders(m)
            ).pack(side="right")

    def scan_fragmentation(self):
        sound_fx.play_click()
        root = self.cmb_defrag_drv.get().strip()
        if not root or root == t("inst_err_nodrive") or not os.path.exists(root):
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("batch_err_nodrive"))
            return
        self.scanned_items = UsbDefragWorker.scan_usb_games(root)
        self.selected_game_item = self.scanned_items[0] if self.scanned_items else None
        frag_count = sum(1 for x in self.scanned_items if x["is_fragmented"])
        self.lbl_defrag_status.configure(
            text=f"Scanned {len(self.scanned_items)} file(s) — Fragmented: {frag_count}"
        )
        sound_fx.play_success()
        self._render_defrag_items()

    def _render_defrag_items(self):
        for w in self.defrag_scroll.winfo_children():
            w.destroy()
        if not self.scanned_items:
            ctk.CTkLabel(
                self.defrag_scroll, text=t("defrag_empty"),
                font=("Segoe UI", 12), text_color=cfg.get_color("text_muted")
            ).pack(pady=45)
            return

        for item in self.scanned_items:
            is_sel = self.selected_game_item and self.selected_game_item["path"] == item["path"]
            is_frag = item["is_fragmented"]
            status_col = cfg.get_color("danger") if is_frag else cfg.get_color("success")
            status_txt = t("defrag_bad").replace("{n}", str(item["fragments"])) if is_frag else t("defrag_ok")

            row = ctk.CTkFrame(
                self.defrag_scroll,
                fg_color=cfg.get_color("card_hover") if is_sel else cfg.get_color("bg_main"),
                corner_radius=cfg.get_radius("chip"),
                border_width=cfg.get_border_width(),
                border_color=cfg.get_color("accent") if is_sel else cfg.get_color("border"),
                height=48
            )
            row.pack(fill="x", padx=6, pady=3)
            row.pack_propagate(False)

            ctk.CTkFrame(row, width=4, fg_color=status_col, corner_radius=0).pack(side="left", fill="y", padx=(0, 10))
            ctk.CTkLabel(
                row, text=item["name"], font=("Segoe UI", 12, "bold"),
                text_color=cfg.get_color("text_main")
            ).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                row, text=f"[{item['rel_path']} • {item['size_str']}]",
                font=("Consolas", 10), text_color=cfg.get_color("text_muted")
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=status_txt, font=("Segoe UI", 11, "bold"), text_color=status_col
            ).pack(side="right", padx=14)

            def on_sel(e, it=item):
                sound_fx.play_click()
                self.selected_game_item = it
                self._render_defrag_items()

            row.bind("<Button-1>", on_sel)
            for ch in row.winfo_children():
                ch.bind("<Button-1>", on_sel)

    def _run_defrag_targets(self, paths):
        if not paths:
            sound_fx.play_warning()
            return
        self.btn_opt_sel.configure(state="disabled")
        self.btn_opt_all.configure(state="disabled")
        self.prog_defrag.set(0)

        def on_done(summary):
            def ui():
                self.btn_opt_sel.configure(state="normal")
                self.btn_opt_all.configure(state="normal")
                self.prog_defrag.set(1.0)
                sound_fx.play_success()
                self.scan_fragmentation()
                messagebox.showinfo(t("success"), t("defrag_done"))
            self.app.after(0, ui)

        def on_err(err):
            def ui():
                self.btn_opt_sel.configure(state="normal")
                self.btn_opt_all.configure(state="normal")
                sound_fx.play_error()
                messagebox.showerror(t("error"), err)
            self.app.after(0, ui)

        UsbDefragWorker.defragment_files(
            paths,
            cb_prog=lambda v: self.app.after(0, lambda: self.prog_defrag.set(v)),
            cb_log=lambda m: self.app.after(0, lambda: self.lbl_defrag_status.configure(text=m)),
            cb_done=on_done,
            cb_err=on_err
        )

    def optimize_selected(self):
        sound_fx.play_click()
        if not self.selected_game_item:
            return
        self._run_defrag_targets([self.selected_game_item["path"]])

    def optimize_all(self):
        sound_fx.play_click()
        frag_paths = [x["path"] for x in self.scanned_items if x["is_fragmented"]]
        if not frag_paths and self.scanned_items:
            NotificationPopup(self.app, t("defrag_ok"), "success")
            return
        self._run_defrag_targets(frag_paths)

    def verify_selected_hash(self):
        sound_fx.play_click()
        if not self.selected_game_item:
            return
        self.btn_hash.configure(state="disabled")
        self.prog_defrag.set(0)
        self.lbl_defrag_status.configure(text=f"Calculating CRC32 / MD5 / SHA-1: {self.selected_game_item['filename']}...")

        UsbDefragWorker.compute_hashes(
            self.selected_game_item["path"],
            cb_prog=lambda v: self.app.after(0, lambda: self.prog_defrag.set(v)),
            cb_done=lambda info: self.app.after(0, lambda: [
                self.btn_hash.configure(state="normal"),
                self.lbl_defrag_status.configure(text=f"MD5: {info['md5']}"),
                sound_fx.play_success(),
                HashReportModal(self.app, info)
            ]),
            cb_err=lambda e: self.app.after(0, lambda: [
                self.btn_hash.configure(state="normal"),
                sound_fx.play_error(),
                messagebox.showerror(t("error"), e)
            ])
        )


# ==============================================================================
# PÁGINA 2: EDITOR DE COMPATIBILIDADE & MODOS DO OPL (CFG + WIDESCREEN + GSM)
# ==============================================================================
class OplConfigPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=1)

        PageHeader(self, t("tab_opl_cfg"), t("opl_cfg_sub"), badge_text="CFG + GSM + 16:9").grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14)
        )

        # Barra superior: Pasta/USB + Jogo + Presets
        top_card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        top_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        top_card.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(top_card, text=t("opl_target_root"), font=("Segoe UI", 11, "bold")).grid(row=0, column=0, padx=(16, 8), pady=(14, 6), sticky="w")
        self.cmb_root = ctk.CTkComboBox(
            top_card, values=[t("inst_err_nodrive")], height=32,
            corner_radius=cfg.get_radius("entry"), command=lambda _: self.populate_games()
        )
        self.cmb_root.grid(row=0, column=1, padx=(0, 6), pady=(14, 6), sticky="ew")
        ctk.CTkButton(
            top_card, text=t("btn_browse"), width=85, height=32, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=cfg.get_radius("button"), command=self.browse_root
        ).grid(row=0, column=2, padx=(0, 14), pady=(14, 6))

        ctk.CTkLabel(top_card, text=t("opl_preset_lbl"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("highlight")).grid(row=0, column=3, padx=(4, 8), pady=(14, 6), sticky="w")
        self.var_preset = ctk.StringVar(value="— Custom / Manual —")
        ctk.CTkOptionMenu(
            top_card, variable=self.var_preset, values=list(OplCfgManager.COMMUNITY_PRESETS.keys()),
            height=32, corner_radius=cfg.get_radius("entry"), command=self.apply_preset
        ).grid(row=0, column=3, padx=(155, 16), pady=(14, 6), sticky="ew")

        ctk.CTkLabel(top_card, text=t("opl_game_sel"), font=("Segoe UI", 11, "bold")).grid(row=1, column=0, padx=(16, 8), pady=(4, 14), sticky="w")
        self.cmb_games = ctk.CTkComboBox(
            top_card, values=["SLUS_209.46 - God of War II"], height=32,
            corner_radius=cfg.get_radius("entry"), command=self.on_game_picked
        )
        self.cmb_games.grid(row=1, column=1, columnspan=2, padx=(0, 14), pady=(4, 14), sticky="ew")

        id_box = ctk.CTkFrame(top_card, fg_color="transparent")
        id_box.grid(row=1, column=3, padx=(4, 16), pady=(4, 14), sticky="ew")
        ctk.CTkLabel(id_box, text="ID:", font=("Consolas", 12, "bold"), text_color=cfg.get_color("accent")).pack(side="left", padx=(0, 6))
        self.ent_id = ctk.CTkEntry(id_box, width=130, height=32, font=("Consolas", 12, "bold"), corner_radius=cfg.get_radius("entry"))
        self.ent_id.pack(side="left", padx=(0, 8))
        self.ent_id.insert(0, "SLUS_209.46")
        self.ent_title = ctk.CTkEntry(id_box, placeholder_text="Game Title", height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_title.pack(side="left", fill="x", expand=True)

        # Coluna Esquerda: Modos 1..6
        left_card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        left_card.grid(row=2, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            left_card, text=t("opl_modes_hdr"), font=("Segoe UI", 12, "bold"),
            text_color=cfg.get_color("accent")
        ).pack(anchor="w", padx=18, pady=(16, 10))

        self.mode_vars = {}
        for m in range(1, 7):
            v = ctk.BooleanVar(value=False)
            self.mode_vars[m] = v
            ctk.CTkSwitch(
                left_card, text=t(f"opl_m{m}"), variable=v,
                font=("Segoe UI", 11), progress_color=cfg.get_color("accent"),
                command=sound_fx.play_click
            ).pack(anchor="w", padx=18, pady=8)

        # Coluna Direita: GSM, Widescreen & DMA
        right_card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        right_card.grid(row=2, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            right_card, text=t("opl_gsm_hdr"), font=("Segoe UI", 12, "bold"),
            text_color=cfg.get_color("highlight")
        ).pack(anchor="w", padx=18, pady=(16, 10))

        self.var_gsm = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            right_card, text=t("opl_enable_gsm"), variable=self.var_gsm,
            font=("Segoe UI", 11, "bold"), progress_color=cfg.get_color("success"),
            command=sound_fx.play_click
        ).pack(anchor="w", padx=18, pady=(4, 8))

        ctk.CTkLabel(right_card, text=t("opl_gsm_vmode"), font=("Segoe UI", 11)).pack(anchor="w", padx=18, pady=(2, 4))
        self.var_gsm_mode = ctk.StringVar(value="HDTV 480p @60Hz (Progressive)")
        ctk.CTkOptionMenu(
            right_card, variable=self.var_gsm_mode,
            values=list(OplCfgManager.GSM_MODES.keys()),
            height=32, corner_radius=cfg.get_radius("entry"),
            command=lambda _: sound_fx.play_click()
        ).pack(fill="x", padx=18, pady=(0, 8))

        self.var_field_fix = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            right_card, text=t("opl_field_fix"), variable=self.var_field_fix,
            font=("Segoe UI", 11), command=sound_fx.play_click
        ).pack(anchor="w", padx=18, pady=6)

        self.var_wide = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            right_card, text=t("opl_wide_chk"), variable=self.var_wide,
            font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("highlight"),
            progress_color=cfg.get_color("accent"), command=sound_fx.play_click
        ).pack(anchor="w", padx=18, pady=8)

        ctk.CTkLabel(right_card, text=t("opl_dma_lbl"), font=("Segoe UI", 11)).pack(anchor="w", padx=18, pady=(4, 4))
        self.var_dma = ctk.StringVar(value="UDMA 4 (Fastest / Default)")
        ctk.CTkOptionMenu(
            right_card, variable=self.var_dma,
            values=list(OplCfgManager.DMA_MODES.keys()),
            height=32, corner_radius=cfg.get_radius("entry"),
            command=lambda _: sound_fx.play_click()
        ).pack(fill="x", padx=18, pady=(0, 14))

        act = ctk.CTkFrame(right_card, fg_color="transparent")
        act.pack(fill="x", padx=18, pady=(4, 16), side="bottom")
        ctk.CTkButton(
            act, text=t("opl_load_btn"), height=38, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=cfg.get_radius("button"), command=self.load_current_cfg
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            act, text=t("opl_save_btn"), height=38, font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.save_current_cfg
        ).pack(side="right", expand=True, fill="x", padx=(6, 0))

    def select_external_game(self, game_data):
        gid = game_data.get("id", "")
        if gid and gid != "Unknown":
            self.ent_id.delete(0, "end")
            self.ent_id.insert(0, ArtScraperWorker.format_opl_id(gid))
        self.ent_title.delete(0, "end")
        self.ent_title.insert(0, game_data.get("name", ""))
        self.load_current_cfg(silent=True)

    def browse_root(self):
        sound_fx.play_click()
        p = filedialog.askdirectory()
        if p:
            self.cmb_root.set(p)
            self.populate_games()

    def refresh(self):
        drives = UsbDetector.get_removable_drives()
        vals = [d["mountpoint"] for d in drives]
        if vals:
            self.cmb_root.configure(values=vals)
            if self.cmb_root.get() in ("", t("inst_err_nodrive")):
                self.cmb_root.set(vals[0])
        else:
            fallback = os.path.join(os.path.expanduser("~"), "Desktop")
            self.cmb_root.configure(values=[fallback])
            if self.cmb_root.get() in ("", t("inst_err_nodrive")):
                self.cmb_root.set(fallback)
        self.populate_games()

    def populate_games(self):
        root = self.cmb_root.get().strip()
        games = OplCfgManager.discover_games(root, self.app.library.games)
        if games:
            labels = [f"{g['opl_id']} - {g['title']}" for g in games]
            self.cmb_games.configure(values=labels)
            self.cmb_games.set(labels[0])
            self.on_game_picked(labels[0], play_snd=False)

    def on_game_picked(self, val, play_snd=True):
        if play_snd:
            sound_fx.play_click()
        if " - " in val:
            oid, title = val.split(" - ", 1)
            self.ent_id.delete(0, "end")
            self.ent_id.insert(0, oid.strip())
            self.ent_title.delete(0, "end")
            self.ent_title.insert(0, title.strip())
            self.load_current_cfg(silent=True)

    def apply_preset(self, preset_name):
        sound_fx.play_click()
        preset = OplCfgManager.COMMUNITY_PRESETS.get(preset_name)
        if not preset:
            return
        for m in range(1, 7):
            self.mode_vars[m].set(m in preset["modes"])
        self.var_dma.set(OplCfgManager.INV_DMA_MODES.get(preset.get("dma", 7), "UDMA 4 (Fastest / Default)"))
        self.var_wide.set(bool(preset.get("wide", False)))

    def load_current_cfg(self, silent=False):
        if not silent:
            sound_fx.play_click()
        root = self.cmb_root.get().strip()
        gid = self.ent_id.get().strip()
        if not root or not gid:
            return
        st = OplCfgManager.load_cfg(root, gid)
        for m in range(1, 7):
            self.mode_vars[m].set(st["modes"].get(m, False))
        self.var_dma.set(st["dma_label"])
        self.var_gsm.set(st["enable_gsm"])
        self.var_gsm_mode.set(st["gsm_mode_label"])
        self.var_field_fix.set(st["gsm_field_fix"])
        self.var_wide.set(st["widescreen"])
        if st["title"]:
            self.ent_title.delete(0, "end")
            self.ent_title.insert(0, st["title"])
        if not silent:
            NotificationPopup(self.app, f"Loaded {st['opl_id']}.cfg" if st["exists"] else "No existing .cfg (defaults shown)", "info")

    def save_current_cfg(self):
        sound_fx.play_click()
        root = self.cmb_root.get().strip()
        gid = self.ent_id.get().strip()
        if not root or not os.path.exists(root) or not gid:
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("batch_err_nodrive"))
            return
        try:
            payload = {
                "title": self.ent_title.get().strip(),
                "modes": {m: self.mode_vars[m].get() for m in range(1, 7)},
                "dma_label": self.var_dma.get(),
                "enable_gsm": self.var_gsm.get(),
                "gsm_mode_label": self.var_gsm_mode.get(),
                "gsm_field_fix": self.var_field_fix.get(),
                "widescreen": self.var_wide.get()
            }
            saved_path = OplCfgManager.save_cfg(root, gid, payload)
            sound_fx.play_success()
            NotificationPopup(self.app, f"Saved: {os.path.basename(saved_path)}", "success")
            messagebox.showinfo(t("success"), f"{t('cfg_succ')}\n{saved_path}")
        except Exception as e:
            sound_fx.play_error()
            messagebox.showerror(t("error"), str(e))


# ==============================================================================
# PÁGINA 3: ART SCRAPER 2.0 - KIT COMPLETO COM PRÉVIA VISUAL
# ==============================================================================
class ArtScraperV2Page(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.detected_ids = []
        self._img_refs = []
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(1, weight=1)

        PageHeader(self, t("art_title"), t("art_desc"), badge_text="FULL KIT 2.0").grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14)
        )

        # Painel Esquerdo: Unidade, Checkboxes de Artes, Progresso e Log
        left = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(4, weight=1)

        drv_frm = ctk.CTkFrame(left, fg_color="transparent")
        drv_frm.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        self.cmb_drv = ctk.CTkComboBox(drv_frm, values=["None"], height=32, corner_radius=cfg.get_radius("entry"))
        self.cmb_drv.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            drv_frm, text=t("btn_browse"), width=85, height=32, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=cfg.get_radius("button"), command=self.browse_target
        ).pack(side="left")

        chk_grid = ctk.CTkFrame(left, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("chip"))
        chk_grid.grid(row=1, column=0, sticky="ew", padx=16, pady=6)
        chk_grid.grid_columnconfigure((0, 1), weight=1)

        slot_labels = [
            ("COV", t("art_cov")), ("COV2", t("art_cov2")),
            ("DISC", t("art_disc")), ("BG", t("art_bg")),
            ("SCR", t("art_scr")), ("LGO", t("art_lgo"))
        ]
        self.slot_vars = {}
        for idx, (slot_code, lbl_txt) in enumerate(slot_labels):
            v = ctk.BooleanVar(value=True)
            self.slot_vars[slot_code] = v
            ctk.CTkCheckBox(
                chk_grid, text=lbl_txt, variable=v, font=("Segoe UI", 11),
                command=sound_fx.play_click
            ).grid(row=idx // 2, column=idx % 2, sticky="w", padx=12, pady=6)

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        ctk.CTkButton(
            btn_row, text=t("art_scan"), height=36, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.scan_games
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.btn_dl = ctk.CTkButton(
            btn_row, text=t("art_dl"), height=36, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.start_download
        )
        self.btn_dl.pack(side="right", expand=True, fill="x", padx=(5, 0))

        self.prog = ctk.CTkProgressBar(left, progress_color=cfg.get_color("highlight"))
        self.prog.grid(row=3, column=0, sticky="ew", padx=16, pady=(2, 8))
        self.prog.set(0)

        self.log_box = ctk.CTkTextbox(
            left, font=("Consolas", 10), fg_color=cfg.get_color("bg_main"),
            corner_radius=cfg.get_radius("entry")
        )
        self.log_box.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 16))

        # Painel Direito: Pré-visualização ao vivo das 6 Artes
        right = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        right.grid_columnconfigure((0, 1, 2), weight=1)
        right.grid_rowconfigure((2, 3), weight=1)

        hdr_r = ctk.CTkFrame(right, fg_color="transparent")
        hdr_r.grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            hdr_r, text=t("art_preview_hdr"), font=("Segoe UI", 12, "bold"),
            text_color=cfg.get_color("highlight")
        ).pack(side="left")
        ctk.CTkButton(
            hdr_r, text=t("btn_open_folder"), width=110, height=28, font=("Segoe UI", 10, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=cfg.get_radius("button"), command=self.open_art_dir
        ).pack(side="right")

        self.cmb_prev_id = ctk.CTkComboBox(
            right, values=["SLUS-20946"], height=32,
            corner_radius=cfg.get_radius("entry"),
            command=lambda _: [sound_fx.play_click(), self.render_preview()]
        )
        self.cmb_prev_id.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 10))

        self.preview_tiles = {}
        for idx, slot_code in enumerate(ArtScraperV2Worker.ART_SLOTS):
            tile = ctk.CTkFrame(
                right, fg_color=cfg.get_color("bg_main"),
                corner_radius=cfg.get_radius("chip"),
                border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
            )
            tile.grid(row=2 + (idx // 3), column=idx % 3, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(
                tile, text=slot_code, font=("Consolas", 10, "bold"),
                text_color=cfg.get_color("accent")
            ).pack(pady=(6, 2))
            img_lbl = ctk.CTkLabel(
                tile, text=t("art_no_img"), font=("Segoe UI", 10),
                text_color=cfg.get_color("text_muted")
            )
            img_lbl.pack(expand=True, fill="both", padx=6, pady=(0, 6))
            self.preview_tiles[slot_code] = img_lbl

    def browse_target(self):
        sound_fx.play_click()
        p = filedialog.askdirectory()
        if p:
            self.cmb_drv.set(p)
            self.scan_games()

    def open_art_dir(self):
        sound_fx.play_click()
        root = self.cmb_drv.get().strip()
        if root and os.path.exists(root):
            art_d = os.path.join(root, "ART") if not root.upper().endswith("ART") else root
            os.makedirs(art_d, exist_ok=True)
            os.startfile(art_d)

    def refresh(self):
        drives = DriveManager.get_drives()
        vals = [d["mountpoint"] for d in drives]
        if vals:
            self.cmb_drv.configure(values=vals)
            if self.cmb_drv.get() in ("", "None"):
                self.cmb_drv.set(vals[0])

    def scan_games(self):
        sound_fx.play_click()
        mp = self.cmb_drv.get().strip()
        ids = []
        if mp and os.path.exists(mp):
            ids.extend(ArtScraperWorker.scan_for_ids(mp))
        for g in self.app.library.games:
            gid = g.get("id", "Unknown")
            if gid != "Unknown" and gid not in ids:
                ids.append(gid)
        self.detected_ids = sorted(set(ids))
        self.log_box.insert("end", f"Detected {len(self.detected_ids)} game ID(s).\n")
        self.log_box.see("end")
        if self.detected_ids:
            self.cmb_prev_id.configure(values=self.detected_ids)
            self.cmb_prev_id.set(self.detected_ids[0])
            sound_fx.play_success()
            self.render_preview()

    def render_preview(self):
        self._img_refs.clear()
        root = self.cmb_drv.get().strip()
        gid = self.cmb_prev_id.get().strip()
        if not root or not os.path.exists(root) or not gid:
            return
        local_map = ArtScraperV2Worker.find_local_arts(root, gid)
        for slot_code, lbl in self.preview_tiles.items():
            fp = local_map.get(slot_code)
            if fp and PIL_SUPPORT and os.path.exists(fp):
                try:
                    pil_im = Image.open(fp)
                    pil_im.thumbnail((115, 125))
                    ctk_im = ctk.CTkImage(light_image=pil_im, dark_image=pil_im, size=pil_im.size)
                    self._img_refs.append(ctk_im)
                    lbl.configure(image=ctk_im, text="")
                    continue
                except Exception:
                    pass
            lbl.configure(image=None, text="✔ Saved" if fp else t("art_no_img"))

    def start_download(self):
        sound_fx.play_click()
        root = self.cmb_drv.get().strip()
        if not root or root == "None" or not os.path.exists(root):
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("batch_err_nodrive"))
            return
        ids = self.detected_ids or ([self.cmb_prev_id.get().strip()] if self.cmb_prev_id.get().strip() else [])
        if not ids:
            self.scan_games()
            ids = self.detected_ids
        if not ids:
            return

        selected_slots = [k for k, v in self.slot_vars.items() if v.get()]
        self.btn_dl.configure(state="disabled")
        self.prog.set(0)

        ArtScraperV2Worker.download_full_kit(
            root, ids, selected_slots, overwrite=False,
            cb_prog=lambda v: self.app.after(0, lambda: self.prog.set(v)),
            cb_log=lambda m: self.app.after(0, lambda: [self.log_box.insert("end", m + "\n"), self.log_box.see("end")]),
            cb_item_done=lambda gid: self.app.after(0, lambda g=gid: [self.cmb_prev_id.set(g), self.render_preview()]),
            cb_done=lambda s: self.app.after(0, lambda: [
                self.btn_dl.configure(state="normal"),
                self.render_preview(),
                sound_fx.play_success(),
                messagebox.showinfo(t("success"), t("art_done"))
            ]),
            cb_err=lambda e: self.app.after(0, lambda: [
                self.btn_dl.configure(state="normal"),
                sound_fx.play_error(),
                messagebox.showerror(t("error"), e)
            ])
        )


# ==============================================================================
# PÁGINA 4: GERENCIADOR & CONVERSOR DE MEMORY CARD (PCSX2 .ps2 ⇄ OPL VMC .bin)
# ==============================================================================
class MemoryCardPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.current_card_path = ""
        self.selected_save_dir = None
        self.loaded_saves = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        PageHeader(self, t("tab_mc"), t("mc_sub"), badge_text=".PS2 ⇄ .BIN + .PSU").grid(
            row=0, column=0, sticky="ew", pady=(0, 12)
        )

        self.tab_names = [t("mc_mode_exp"), t("mc_mode_conv")]
        self.seg = create_segmented_tabs(self, self.tab_names, self.switch_mode)
        self.seg.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        self.frm_exp = ctk.CTkFrame(self.body, fg_color="transparent")
        self.frm_conv = ctk.CTkFrame(self.body, fg_color="transparent")

        self._build_explorer()
        self._build_converter()
        self.switch_mode(self.tab_names[0])

    def _build_explorer(self):
        self.frm_exp.grid_columnconfigure(0, weight=1)
        self.frm_exp.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(
            self.frm_exp, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(
            top, text=t("mc_open_card"), height=34, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.open_card_dialog
        ).pack(side="left", padx=(14, 6), pady=12)

        ctk.CTkButton(
            top, text=t("mc_find_pcsx2"), height=34, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=cfg.get_radius("button"), command=self.open_pcsx2_memcards
        ).pack(side="left", padx=6, pady=12)

        self.lbl_card_meta = ctk.CTkLabel(
            top, text="—", font=("Consolas", 11, "bold"),
            text_color=cfg.get_color("highlight")
        )
        self.lbl_card_meta.pack(side="right", padx=16)

        self.saves_scroll = ctk.CTkScrollableFrame(
            self.frm_exp, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.saves_scroll.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        act = ctk.CTkFrame(self.frm_exp, fg_color="transparent")
        act.grid(row=2, column=0, sticky="ew")

        ctk.CTkButton(
            act, text=t("mc_import_psu"), height=38, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.import_psu_save
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            act, text=t("mc_export_psu"), height=38, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.export_psu_save
        ).pack(side="left", expand=True, fill="x", padx=6)

        ctk.CTkButton(
            act, text=t("mc_del_save"), height=38, font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"),
            command=self.delete_selected_save
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        self._render_saves_list()

    def _build_converter(self):
        self.frm_conv.grid_columnconfigure((0, 1), weight=1)
        self.frm_conv.grid_rowconfigure(0, weight=1)

        # Card Esquerdo: Conversor .ps2 <-> .bin
        c_left = ctk.CTkFrame(
            self.frm_conv, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        c_left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            c_left, text=t("mc_conv_hdr"), font=("Segoe UI", 12, "bold"),
            text_color=cfg.get_color("accent"), wraplength=380, justify="left"
        ).pack(anchor="w", padx=18, pady=(18, 12))

        ctk.CTkLabel(c_left, text=t("iso_file"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(4, 4))
        r1 = ctk.CTkFrame(c_left, fg_color="transparent")
        r1.pack(fill="x", padx=18)
        self.ent_mc_src = ctk.CTkEntry(r1, height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_mc_src.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            r1, text=t("btn_browse"), width=85, height=32, corner_radius=cfg.get_radius("button"),
            command=self.browse_conv_src
        ).pack(side="left")

        ctk.CTkLabel(c_left, text="Target Format:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(12, 4))
        self.var_conv_mode = ctk.StringVar(value="OPL VMC (.bin Raw 512B)")
        ctk.CTkOptionMenu(
            c_left, variable=self.var_conv_mode,
            values=["OPL VMC (.bin Raw 512B)", "PCSX2 Card (.ps2 + ECC 528B)"],
            height=32, corner_radius=cfg.get_radius("entry"),
            command=lambda _: sound_fx.play_click()
        ).pack(fill="x", padx=18)

        ctk.CTkLabel(c_left, text=t("iso_out"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(12, 4))
        r2 = ctk.CTkFrame(c_left, fg_color="transparent")
        r2.pack(fill="x", padx=18)
        self.ent_mc_dst = ctk.CTkEntry(r2, height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_mc_dst.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            r2, text=t("btn_browse"), width=85, height=32, corner_radius=cfg.get_radius("button"),
            command=self.browse_conv_dst
        ).pack(side="left")

        self.prog_mc = ctk.CTkProgressBar(c_left, progress_color=cfg.get_color("highlight"))
        self.prog_mc.pack(fill="x", padx=18, pady=(18, 8))
        self.prog_mc.set(0)

        ctk.CTkButton(
            c_left, text=t("mc_conv_btn"), height=40, font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.run_conversion
        ).pack(fill="x", padx=18, pady=(6, 18))

        # Card Direito: Criar Novo Cartão Formatado
        c_right = ctk.CTkFrame(
            self.frm_conv, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        c_right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            c_right, text=t("mc_new_hdr"), font=("Segoe UI", 12, "bold"),
            text_color=cfg.get_color("highlight"), wraplength=380, justify="left"
        ).pack(anchor="w", padx=18, pady=(18, 12))

        ctk.CTkLabel(c_right, text="Card Architecture:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(6, 4))
        self.var_new_type = ctk.StringVar(value="OPL VMC (.bin Raw)")
        ctk.CTkOptionMenu(
            c_right, variable=self.var_new_type,
            values=["OPL VMC (.bin Raw)", "PCSX2 Card (.ps2 + ECC)"],
            height=32, corner_radius=cfg.get_radius("entry"),
            command=lambda _: sound_fx.play_click()
        ).pack(fill="x", padx=18)

        ctk.CTkLabel(c_right, text=t("game_size") + ":", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(14, 4))
        self.var_new_sz = ctk.StringVar(value="8 MB (Standard Sony PS2)")
        ctk.CTkOptionMenu(
            c_right, variable=self.var_new_sz,
            values=["8 MB (Standard Sony PS2)", "16 MB (OPL Extended)", "32 MB (OPL Large)", "64 MB (OPL Max)"],
            height=32, corner_radius=cfg.get_radius("entry"),
            command=lambda _: sound_fx.play_click()
        ).pack(fill="x", padx=18)

        ctk.CTkButton(
            c_right, text=t("mc_new_btn"), height=42, font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.create_new_card
        ).pack(fill="x", padx=18, pady=28)

    def switch_mode(self, val):
        self.frm_exp.grid_forget()
        self.frm_conv.grid_forget()
        if val == self.tab_names[0]:
            self.frm_exp.grid(row=0, column=0, sticky="nsew")
        else:
            self.frm_conv.grid(row=0, column=0, sticky="nsew")

    def open_card_dialog(self, initial_dir=None):
        sound_fx.play_click()
        fp = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("PS2 Memory Cards", "*.ps2 *.bin *.vmc"), ("All Files", "*.*")]
        )
        if fp:
            self.load_card_path(fp)

    def open_pcsx2_memcards(self):
        d = os.path.join(PCSX2Integration.get_pcsx2_docs_dir(), "memcards")
        os.makedirs(d, exist_ok=True)
        self.open_card_dialog(initial_dir=d)

    def load_card_path(self, fp):
        try:
            info = MemoryCardManager.inspect_card(fp)
            self.current_card_path = fp
            self.loaded_saves = info["saves"]
            self.selected_save_dir = self.loaded_saves[0]["dir_name"] if self.loaded_saves else None
            self.lbl_card_meta.configure(
                text=f"{os.path.basename(fp)} • {info['format_label']} • Free: {info['free_str']} / {info['total_str']}"
            )
            sound_fx.play_success()
            self._render_saves_list()
        except Exception as e:
            sound_fx.play_error()
            messagebox.showerror(t("error"), str(e))

    def _render_saves_list(self):
        for w in self.saves_scroll.winfo_children():
            w.destroy()
        if not self.loaded_saves:
            ctk.CTkLabel(
                self.saves_scroll, text=t("mc_empty_card"),
                font=("Segoe UI", 12), text_color=cfg.get_color("text_muted")
            ).pack(pady=45)
            return

        for sv in self.loaded_saves:
            is_sel = (self.selected_save_dir == sv["dir_name"])
            row = ctk.CTkFrame(
                self.saves_scroll,
                fg_color=cfg.get_color("card_hover") if is_sel else cfg.get_color("bg_main"),
                corner_radius=cfg.get_radius("chip"),
                border_width=cfg.get_border_width(),
                border_color=cfg.get_color("accent") if is_sel else cfg.get_color("border"),
                height=50
            )
            row.pack(fill="x", padx=6, pady=3)
            row.pack_propagate(False)

            ctk.CTkFrame(row, width=4, fg_color=cfg.get_color("accent"), corner_radius=0).pack(side="left", fill="y", padx=(0, 10))
            ctk.CTkLabel(row, text=sv["title"], font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=sv["dir_name"], font=("Consolas", 10, "bold"), text_color=cfg.get_color("highlight")).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                row, text=f"{sv['files_count']} files • {sv['size_str']} • {sv['modified']}",
                font=("Consolas", 10), text_color=cfg.get_color("text_muted")
            ).pack(side="right", padx=14)

            def pick(e, dname=sv["dir_name"]):
                sound_fx.play_click()
                self.selected_save_dir = dname
                self._render_saves_list()

            row.bind("<Button-1>", pick)
            for ch in row.winfo_children():
                ch.bind("<Button-1>", pick)

    def export_psu_save(self):
        sound_fx.play_click()
        if not self.current_card_path or not self.selected_save_dir:
            return
        out = filedialog.asksaveasfilename(
            initialfile=f"{self.selected_save_dir}.psu",
            defaultextension=".psu",
            filetypes=[("EMS PS2 Save (.psu)", "*.psu")]
        )
        if out:
            try:
                MemoryCardManager.export_psu(self.current_card_path, self.selected_save_dir, out)
                sound_fx.play_success()
                NotificationPopup(self.app, f"Exported {os.path.basename(out)}", "success")
            except Exception as e:
                sound_fx.play_error()
                messagebox.showerror(t("error"), str(e))

    def import_psu_save(self):
        sound_fx.play_click()
        if not self.current_card_path:
            messagebox.showwarning(t("warning"), t("mc_open_card"))
            return
        psu = filedialog.askopenfilename(filetypes=[("EMS PS2 Save (.psu)", "*.psu")])
        if psu:
            try:
                sname = MemoryCardManager.import_psu(self.current_card_path, psu)
                self.load_card_path(self.current_card_path)
                NotificationPopup(self.app, f"Imported {sname}!", "success")
            except Exception as e:
                sound_fx.play_error()
                messagebox.showerror(t("error"), str(e))

    def delete_selected_save(self):
        sound_fx.play_click()
        if not self.current_card_path or not self.selected_save_dir:
            return
        if messagebox.askyesno(t("confirm"), f"Delete save '{self.selected_save_dir}' from Memory Card?"):
            try:
                MemoryCardManager.delete_save(self.current_card_path, self.selected_save_dir)
                self.load_card_path(self.current_card_path)
            except Exception as e:
                sound_fx.play_error()
                messagebox.showerror(t("error"), str(e))

    def browse_conv_src(self):
        sound_fx.play_click()
        fp = filedialog.askopenfilename(filetypes=[("Memory Cards", "*.ps2 *.bin *.vmc")])
        if fp:
            self.ent_mc_src.delete(0, "end")
            self.ent_mc_src.insert(0, fp)
            base, ext = os.path.splitext(fp)
            if ext.lower() == ".ps2":
                self.var_conv_mode.set("OPL VMC (.bin Raw 512B)")
                self.ent_mc_dst.delete(0, "end")
                self.ent_mc_dst.insert(0, base + "_OPL.bin")
            else:
                self.var_conv_mode.set("PCSX2 Card (.ps2 + ECC 528B)")
                self.ent_mc_dst.delete(0, "end")
                self.ent_mc_dst.insert(0, base + "_PCSX2.ps2")

    def browse_conv_dst(self):
        sound_fx.play_click()
        want_ecc = ".ps2" in self.var_conv_mode.get()
        ext = ".ps2" if want_ecc else ".bin"
        fp = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[("Memory Card", f"*{ext}")])
        if fp:
            self.ent_mc_dst.delete(0, "end")
            self.ent_mc_dst.insert(0, fp)

    def run_conversion(self):
        sound_fx.play_click()
        src = self.ent_mc_src.get().strip()
        dst = self.ent_mc_dst.get().strip()
        if not src or not dst or not os.path.exists(src):
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("iso_empty"))
            return
        want_ecc = ".ps2" in self.var_conv_mode.get()
        self.prog_mc.set(0)
        MemoryCardManager.convert_card(
            src, dst, want_ecc,
            cb_prog=lambda v: self.app.after(0, lambda: self.prog_mc.set(v)),
            cb_done=lambda p: self.app.after(0, lambda: [
                sound_fx.play_success(),
                messagebox.showinfo(t("success"), f"{t('iso_succ')}\n{p}")
            ]),
            cb_err=lambda e: self.app.after(0, lambda: [
                sound_fx.play_error(),
                messagebox.showerror(t("error"), e)
            ])
        )

    def create_new_card(self):
        sound_fx.play_click()
        with_ecc = ".ps2" in self.var_new_type.get()
        sz_mb = int(self.var_new_sz.get().split(" ")[0])
        if with_ecc and sz_mb != 8:
            sz_mb = 8  # PCSX2 exige 8 MB padrão para compatibilidade plena com a BIOS Sony
        ext = ".ps2" if with_ecc else ".bin"
        out = filedialog.asksaveasfilename(
            initialfile=f"OPL_VMC_{sz_mb}MB{ext}" if not with_ecc else f"Mcd001{ext}",
            defaultextension=ext,
            filetypes=[("Memory Card", f"*{ext}")]
        )
        if out:
            try:
                MemoryCardManager.create_blank_card(out, size_mb=sz_mb, with_ecc=with_ecc)
                sound_fx.play_success()
                self.seg.set(self.tab_names[0])
                self.switch_mode(self.tab_names[0])
                self.load_card_path(out)
                NotificationPopup(self.app, f"Created {os.path.basename(out)}", "success")
            except Exception as e:
                sound_fx.play_error()
                messagebox.showerror(t("error"), str(e))


# ==============================================================================
# PÁGINA 5: PS1 POPSTARTER (.BIN/.CUE ➔ .VCD DIRETO NA PASTA DOWNLOADS)
# ==============================================================================
class PopStarterPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        PageHeader(self, t("tab_pops"), t("pops_sub"), badge_text="PS1 ➔ .VCD").grid(
            row=0, column=0, sticky="ew", pady=(0, 15)
        )

        card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text=t("pops_src"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(22, 6))
        r_src = ctk.CTkFrame(card, fg_color="transparent")
        r_src.pack(fill="x", padx=22)
        self.ent_src = ctk.CTkEntry(r_src, height=34, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry"))
        self.ent_src.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(
            r_src, text=t("btn_browse"), width=100, height=34, font=("Segoe UI", 11, "bold"),
            corner_radius=cfg.get_radius("button"), command=self.browse_ps1
        ).pack(side="left")

        self.lbl_cue_info = ctk.CTkLabel(
            card, text="—", font=("Consolas", 11, "bold"),
            text_color=cfg.get_color("highlight")
        )
        self.lbl_cue_info.pack(anchor="w", padx=22, pady=(6, 10))

        ctk.CTkLabel(card, text=t("pops_name"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(6, 6))
        self.ent_name = ctk.CTkEntry(card, height=34, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry"))
        self.ent_name.pack(fill="x", padx=22)

        ctk.CTkLabel(
            card, text=t("pops_dest_note"), font=("Segoe UI", 11),
            text_color=cfg.get_color("text_muted")
        ).pack(anchor="w", padx=22, pady=(16, 4))

        dl_bar = ctk.CTkFrame(card, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("chip"))
        dl_bar.pack(fill="x", padx=22, pady=(0, 18))
        self.dl_dir = PopStarterConverter.get_user_downloads_dir()
        ctk.CTkLabel(
            dl_bar, text=f"📁  {self.dl_dir}", font=("Consolas", 11, "bold"),
            text_color=cfg.get_color("success")
        ).pack(side="left", padx=14, pady=8)
        ctk.CTkButton(
            dl_bar, text=t("btn_open_folder"), width=120, height=28, font=("Segoe UI", 10, "bold"),
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            corner_radius=cfg.get_radius("button"),
            command=lambda: [sound_fx.play_click(), os.startfile(PopStarterConverter.get_user_downloads_dir())]
        ).pack(side="right", padx=10, pady=6)

        self.btn_conv = ctk.CTkButton(
            card, text=t("pops_btn"), height=44, font=("Segoe UI", 13, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.start_vcd_convert
        )
        self.btn_conv.pack(fill="x", padx=22, pady=(4, 12))

        self.prog = ctk.CTkProgressBar(card, progress_color=cfg.get_color("highlight"))
        self.prog.pack(fill="x", padx=22, pady=(0, 22))
        self.prog.set(0)

    def browse_ps1(self):
        sound_fx.play_click()
        fp = filedialog.askopenfilename(filetypes=[("PS1 Disc Images (.cue / .bin)", "*.cue *.bin")])
        if fp:
            self.ent_src.delete(0, "end")
            self.ent_src.insert(0, fp)
            base = os.path.splitext(os.path.basename(fp))[0]
            self.ent_name.delete(0, "end")
            self.ent_name.insert(0, f"{base}.VCD")
            try:
                files_ent, tracks, total_secs = PopStarterConverter.parse_cue_or_bin(fp)
                est_sz = format_size(0x100000 + total_secs * 2352)
                self.lbl_cue_info.configure(
                    text=f"✔ {len(tracks)} Track(s) • {len(files_ent)} BIN file(s) • {total_secs:,} sectors (~{est_sz})"
                )
            except Exception as e:
                self.lbl_cue_info.configure(text=f"⚠ {e}")

    def start_vcd_convert(self):
        sound_fx.play_click()
        src = self.ent_src.get().strip()
        if not src or not os.path.exists(src):
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("iso_empty"))
            return
        self.btn_conv.configure(state="disabled")
        self.prog.set(0)

        PopStarterConverter.convert_to_downloads(
            src, self.ent_name.get().strip(),
            cb_prog=lambda v: self.app.after(0, lambda: self.prog.set(v)),
            cb_done=lambda out_vcd: self.app.after(0, lambda: [
                self.btn_conv.configure(state="normal"),
                self.prog.set(1.0),
                sound_fx.play_success(),
                NotificationPopup(self.app, t("pops_done"), "success"),
                messagebox.showinfo(t("success"), f"{t('pops_done')}\n\n{out_vcd}")
            ]),
            cb_err=lambda e: self.app.after(0, lambda: [
                self.btn_conv.configure(state="normal"),
                sound_fx.play_error(),
                messagebox.showerror(t("error"), e)
            ])
        )


# ==============================================================================
# PÁGINA 6: PATCHER PERMANENTE WIDESCREEN 16:9, PAL ➔ NTSC, IPS & ESR
# ==============================================================================
class IsoPatcherV2Page(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        PageHeader(self, t("tab_patcher"), t("patch_sub"), badge_text="16:9 + NTSC 60Hz").grid(
            row=0, column=0, sticky="ew", pady=(0, 14)
        )

        card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text=t("patch_iso"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        f1 = ctk.CTkFrame(card, fg_color="transparent")
        f1.pack(fill="x", padx=20)
        self.ent_iso = ctk.CTkEntry(f1, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_iso.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(f1, text=t("btn_browse"), width=90, height=32, corner_radius=cfg.get_radius("button"), command=self.browse_iso).pack(side="left")

        ctk.CTkLabel(card, text=t("patch_out"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(12, 4))
        f2 = ctk.CTkFrame(card, fg_color="transparent")
        f2.pack(fill="x", padx=20)
        self.ent_out = ctk.CTkEntry(f2, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_out.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(f2, text=t("btn_browse"), width=90, height=32, corner_radius=cfg.get_radius("button"), command=self.browse_out).pack(side="left")

        ctk.CTkLabel(card, text=t("patch_file"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(12, 4))
        f3 = ctk.CTkFrame(card, fg_color="transparent")
        f3.pack(fill="x", padx=20)
        self.ent_patch = ctk.CTkEntry(f3, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_patch.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(f3, text=t("btn_browse"), width=90, height=32, corner_radius=cfg.get_radius("button"), command=self.browse_patch).pack(side="left")

        opts = ctk.CTkFrame(card, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("chip"))
        opts.pack(fill="x", padx=20, pady=14)

        self.var_wide = ctk.BooleanVar(value=True)
        self.var_ntsc = ctk.BooleanVar(value=False)
        self.var_reg = ctk.BooleanVar(value=True)

        ctk.CTkSwitch(opts, text=t("patch_wide"), variable=self.var_wide, font=("Segoe UI", 11, "bold"), command=sound_fx.play_click).pack(anchor="w", padx=14, pady=(10, 6))
        ctk.CTkSwitch(opts, text=t("patch_ntsc"), variable=self.var_ntsc, font=("Segoe UI", 11, "bold"), command=sound_fx.play_click).pack(anchor="w", padx=14, pady=6)
        ctk.CTkSwitch(opts, text=t("patch_reg"), variable=self.var_reg, font=("Segoe UI", 11), command=sound_fx.play_click).pack(anchor="w", padx=14, pady=(6, 10))

        self.btn_run = ctk.CTkButton(
            card, text=t("patch_btn"), height=42, font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.apply_all_patches
        )
        self.btn_run.pack(fill="x", padx=20, pady=(2, 10))

        self.prog = ctk.CTkProgressBar(card, progress_color=cfg.get_color("highlight"))
        self.prog.pack(fill="x", padx=20, pady=(0, 18))
        self.prog.set(0)

    def browse_iso(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso")])
        if f:
            self.ent_iso.delete(0, "end")
            self.ent_iso.insert(0, f)
            if not self.ent_out.get().strip():
                b, ext = os.path.splitext(f)
                self.ent_out.insert(0, f"{b}_16x9_Patched{ext}")

    def browse_out(self):
        sound_fx.play_click()
        f = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[(t("iso_files"), "*.iso")])
        if f:
            self.ent_out.delete(0, "end")
            self.ent_out.insert(0, f)

    def browse_patch(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[("IPS / PCSX2 PNACH", "*.ips *.pnach")])
        if f:
            self.ent_patch.delete(0, "end")
            self.ent_patch.insert(0, f)

    def apply_all_patches(self):
        sound_fx.play_click()
        self.btn_run.configure(state="disabled")
        self.prog.set(0)
        WidescreenNtscPatcher.patch_iso(
            self.ent_iso.get().strip(),
            self.ent_out.get().strip(),
            self.ent_patch.get().strip(),
            self.var_wide.get(),
            self.var_ntsc.get(),
            self.var_reg.get(),
            cb_prog=lambda v: self.app.after(0, lambda: self.prog.set(v)),
            cb_done=lambda rep: self.app.after(0, lambda: [
                self.btn_run.configure(state="normal"),
                sound_fx.play_success(),
                messagebox.showinfo(t("success"), f"{t('patch_success')}\n\n{rep}")
            ]),
            cb_err=lambda e: self.app.after(0, lambda: [
                self.btn_run.configure(state="normal"),
                sound_fx.play_error(),
                messagebox.showerror(t("error"), e)
            ])
        )


# ==============================================================================
# PÁGINA 7: ISO / ZSO STUDIO COMPLETO (EXTRACT, REPACK, ZSO FAST/ULTRA, BIN->ISO)
# ==============================================================================
class IsoStudioPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        PageHeader(self, t("tab_iso"), "", badge_text="ISO • ZSO • BIN").grid(
            row=0, column=0, sticky="ew", pady=(0, 12)
        )

        self.modes = [t("iso_mode_ext"), t("iso_mode_rep"), t("iso_mode_zso"), t("iso_mode_bin")]
        self.cur_mode_idx = 0
        self.seg = create_segmented_tabs(self, self.modes, self.on_mode_change)
        self.seg.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        card.grid(row=2, column=0, sticky="nsew")

        ctk.CTkLabel(card, text=t("iso_file"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        s_row = ctk.CTkFrame(card, fg_color="transparent")
        s_row.pack(fill="x", padx=20)
        self.ent_src = ctk.CTkEntry(s_row, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_src.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(s_row, text=t("btn_browse"), width=95, height=34, corner_radius=cfg.get_radius("button"), command=self.browse_src).pack(side="left")

        ctk.CTkLabel(card, text=t("iso_out"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(14, 5))
        d_row = ctk.CTkFrame(card, fg_color="transparent")
        d_row.pack(fill="x", padx=20)
        self.ent_dst = ctk.CTkEntry(d_row, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_dst.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(d_row, text=t("btn_browse"), width=95, height=34, corner_radius=cfg.get_radius("button"), command=self.browse_dst).pack(side="left")

        self.zso_frm = ctk.CTkFrame(card, fg_color="transparent")
        ctk.CTkLabel(self.zso_frm, text=t("iso_zso_lvl"), font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 10))
        self.var_zso = ctk.StringVar(value="Fast (LZ4 Standard - Recommended)")
        ctk.CTkOptionMenu(
            self.zso_frm, variable=self.var_zso,
            values=["Fast (LZ4 Standard - Recommended)", "Ultra (LZ4-HC Maximum Compression)"],
            height=32, width=280, corner_radius=cfg.get_radius("entry"),
            command=lambda _: sound_fx.play_click()
        ).pack(side="left")

        self.btn_action = ctk.CTkButton(
            card, text=t("iso_btn_ext"), height=42, font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"), command=self.execute
        )
        self.btn_action.pack(fill="x", padx=20, pady=20)

        self.prog = ctk.CTkProgressBar(card, progress_color=cfg.get_color("highlight"))
        self.prog.pack(fill="x", padx=20, pady=(0, 22))
        self.prog.set(0)

    def on_mode_change(self, label):
        self.cur_mode_idx = self.modes.index(label) if label in self.modes else 0
        self.ent_src.delete(0, "end")
        self.ent_dst.delete(0, "end")
        self.zso_frm.pack_forget()
        btn_keys = ["iso_btn_ext", "iso_btn_rep", "iso_btn_zso", "iso_btn_bin"]
        self.btn_action.configure(text=t(btn_keys[self.cur_mode_idx]))
        if self.cur_mode_idx == 2:
            self.zso_frm.pack(fill="x", padx=20, pady=(14, 0), before=self.btn_action)

    def browse_src(self):
        sound_fx.play_click()
        if self.cur_mode_idx == 1:
            p = filedialog.askdirectory()
        elif self.cur_mode_idx == 3:
            p = filedialog.askopenfilename(filetypes=[("BIN Disc Image", "*.bin")])
        else:
            p = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso")])
        if p:
            self.ent_src.delete(0, "end")
            self.ent_src.insert(0, p)
            if not self.ent_dst.get().strip():
                b = os.path.splitext(p)[0]
                if self.cur_mode_idx == 0:
                    self.ent_dst.insert(0, b + "_Extracted")
                elif self.cur_mode_idx == 1:
                    self.ent_dst.insert(0, p.rstrip("\\/") + "_Repacked.iso")
                elif self.cur_mode_idx == 2:
                    self.ent_dst.insert(0, b + ".zso")
                elif self.cur_mode_idx == 3:
                    self.ent_dst.insert(0, b + ".iso")

    def browse_dst(self):
        sound_fx.play_click()
        if self.cur_mode_idx == 0:
            p = filedialog.askdirectory()
        elif self.cur_mode_idx == 2:
            p = filedialog.asksaveasfilename(defaultextension=".zso", filetypes=[("ZSO Compressed", "*.zso")])
        else:
            p = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[(t("iso_files"), "*.iso")])
        if p:
            self.ent_dst.delete(0, "end")
            self.ent_dst.insert(0, p)

    def execute(self):
        sound_fx.play_click()
        s = self.ent_src.get().strip()
        d = self.ent_dst.get().strip()
        if not s or not d:
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("iso_empty"))
            return

        self.btn_action.configure(state="disabled")
        self.prog.set(0)

        on_p = lambda v: self.app.after(0, lambda: self.prog.set(v))
        on_ok = lambda _: self.app.after(0, lambda: [
            self.btn_action.configure(state="normal"),
            self.prog.set(1.0),
            sound_fx.play_success(),
            messagebox.showinfo(t("success"), t("iso_succ"))
        ])
        on_err = lambda e: self.app.after(0, lambda: [
            self.btn_action.configure(state="normal"),
            sound_fx.play_error(),
            messagebox.showerror(t("error"), str(e))
        ])

        if self.cur_mode_idx == 0:
            RealIsoTool.extract(s, d, on_p, on_ok, on_err)
        elif self.cur_mode_idx == 1:
            RealIsoTool.repack(s, d, on_p, on_ok, on_err)
        elif self.cur_mode_idx == 2:
            RealIsoTool.compress_zso(s, d, self.var_zso.get(), on_p, on_ok, on_err)
        else:
            BinConverter.convert(s, d, on_p, on_ok, on_err, ps1_mode=True)
