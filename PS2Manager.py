import os
import sys
import time
import threading
import subprocess
import shutil
import webbrowser
import ctypes
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Importa os módulos divididos: backend essencial e motores de ferramentas
from scripts.core_backend import *
from scripts.tool_workers import *

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ps2manager.suite.v107")
except Exception:
    pass

def apply_window_icon(w):
    icon_path = get_res_path("icon.ico")
    if os.path.exists(icon_path):
        try:
            w.iconbitmap(icon_path)
        except Exception:
            pass
        try:
            hwnd = ctypes.windll.user32.GetParent(w.winfo_id())
            if not hwnd:
                hwnd = w.winfo_id()
            LR_LOADFROMFILE = 0x00000010
            IMAGE_ICON = 1
            WM_SETICON = 0x0080
            h_icon_sm = ctypes.windll.user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
            if h_icon_sm and hwnd:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, h_icon_sm)
            h_icon_lg = ctypes.windll.user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
            if h_icon_lg and hwnd:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, h_icon_lg)
        except Exception:
            pass

class SetupFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=cfg.get_color("bg_main"))
        self.app = app
        self.pack(fill="both", expand=True)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.place(relx=0.5, rely=0.5, anchor="center")
        apply_window_icon(self.master)
        self.after(80, lambda: apply_window_icon(self.master))
        self.show_step_0()

    def clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def show_step_0(self):
        self.clear()
        ctk.CTkLabel(
            self.content, text="PS2 MANAGER",
            font=("Segoe UI Black", 34), text_color=cfg.get_color("accent")
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            self.content, text=t("setup_welcome"),
            font=("Segoe UI", 16), text_color=cfg.get_color("text_main")
        ).pack(pady=(0, 35))
        ctk.CTkButton(
            self.content, text=t("setup_continue"),
            font=("Segoe UI", 13, "bold"), height=42, width=220,
            corner_radius=cfg.get_radius("button"), command=self.show_step_1
        ).pack()

    def show_step_1(self):
        self.clear()
        ctk.CTkLabel(
            self.content, text=t("setup_lang"),
            font=("Segoe UI", 18, "bold"), text_color=cfg.get_color("text_main")
        ).pack(pady=(15, 25))

        def set_lang(l):
            cfg.data["language"] = l
            cfg.save()
            self.show_step_2()

        r = cfg.get_radius("button")
        langs = [
            ("Português (Brasil)", "PT_BR"),
            ("Português (Portugal)", "PT"),
            ("English", "EN"),
            ("Español", "ES"),
            ("Русский", "RU"),
            ("日本語", "JA")
        ]
        for label, code in langs:
            ctk.CTkButton(
                self.content, text=label, height=38, width=280,
                corner_radius=r, fg_color=cfg.get_color("card_base"),
                text_color=cfg.get_color("text_main"), hover_color=cfg.get_color("card_hover"),
                command=lambda c=code: set_lang(c)
            ).pack(pady=4)

    def show_step_2(self):
        self.clear()
        ctk.CTkLabel(
            self.content, text=t("setup_model"),
            font=("Segoe UI", 18, "bold"), text_color=cfg.get_color("text_main")
        ).pack(pady=(20, 15))
        models = ["SCPH-10000", "SCPH-3000x", "SCPH-5000x", "SCPH-7000x", "SCPH-9000x", "PSX DESR"]
        self.cmb_model = ctk.CTkComboBox(
            self.content, values=models, font=("Segoe UI", 13),
            height=38, width=260, corner_radius=cfg.get_radius("entry")
        )
        self.cmb_model.pack(pady=10)
        ctk.CTkLabel(
            self.content, text=t("setup_type"),
            font=("Segoe UI", 18, "bold"), text_color=cfg.get_color("text_main")
        ).pack(pady=(20, 15))
        self.cmb_type = ctk.CTkComboBox(
            self.content, values=["SLIM", "FAT"], font=("Segoe UI", 13),
            height=38, width=260, corner_radius=cfg.get_radius("entry")
        )
        self.cmb_type.pack(pady=10)
        ctk.CTkButton(
            self.content, text=t("setup_continue"),
            font=("Segoe UI", 13, "bold"), height=42, width=220,
            corner_radius=cfg.get_radius("button"), command=self.show_step_3
        ).pack(pady=25)

    def show_step_3(self):
        self.clear()
        ctk.CTkLabel(
            self.content, text=t("setup_finish"),
            font=("Segoe UI", 18, "bold"), text_color=cfg.get_color("accent")
        ).pack(pady=(20, 10))
        cfg.data["ps2_model"] = self.cmb_model.get()
        cfg.data["ps2_type"] = self.cmb_type.get()
        cfg.data["setup_done"] = True
        cfg.save()
        ctk.CTkButton(
            self.content, text="START PS2 MANAGER",
            font=("Segoe UI", 14, "bold"), height=45, width=240,
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.finish
        ).pack(pady=30)

    def finish(self):
        self.destroy()
        self.app.build_main_ui()

class VersionRollbackModal(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(t("modal_rollback"))
        self.geometry("450x520")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        ctk.CTkLabel(
            self, text=t("ver_btn"), font=("Segoe UI", 16, "bold"),
            text_color=cfg.get_color("accent")
        ).pack(pady=(20, 5))
        self.sf = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"), border_width=1,
            border_color=cfg.get_color("border")
        )
        self.sf.pack(fill="both", expand=True, padx=20, pady=20)
        ver_dir = os.path.join(BASE_DIR, "VER")
        os.makedirs(ver_dir, exist_ok=True)
        exes = [f for f in os.listdir(ver_dir) if f.lower().endswith('.exe')]
        if not exes:
            ctk.CTkLabel(self.sf, text=t("ver_empty"), text_color=cfg.get_color("text_muted")).pack(pady=30)
        else:
            for exe in exes:
                ctk.CTkButton(
                    self.sf, text=f"{t('ver_launch')} {os.path.splitext(exe)[0]}",
                    fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"),
                    hover_color=cfg.get_color("accent"), height=36,
                    corner_radius=cfg.get_radius("button"),
                    command=lambda e=exe: self.launch_old(e)
                ).pack(fill="x", pady=4, padx=5)

    def launch_old(self, exe_name):
        subprocess.Popen([os.path.join(BASE_DIR, "VER", exe_name)])
        sys.exit(0)

class ChangelogTimelineModal(ctk.CTkToplevel):
    """Linha do tempo interativa e arrastável com histórico e roadmap de atualizações 100% localizado."""
    RELEASES = [
        {
            "ver": "v1.00", "date": "06/09/2026",
            "title": ["Initial Release", "Lançamento Inicial", "Lançamento Inicial", "Lanzamiento Inicial", "Первый релиз", "初期リリース"],
            "desc": [
                "First public release of PS2Manager with library explorer and game detection.",
                "Primeira versão pública do PS2Manager com explorador básico e leitura de jogos.",
                "Primeira versão pública do PS2Manager com explorador básico e leitura de jogos.",
                "Primera versión pública de PS2Manager con explorador básico y detección de juegos.",
                "Первый публичный релиз PS2Manager с проводником игр и автоопределением.",
                "ライブラリ閲覧とゲーム検出を備えたPS2Managerの初期公開バージョン。"
            ]
        },
        {
            "ver": "v1.01", "date": "07/09/2026",
            "title": ["Audio & Themes Support", "Áudio & Suporte a Temas", "Áudio & Suporte a Temas", "Audio y Soporte de Temas", "Звуки и поддержка тем", "オーディオ＆テーマ対応"],
            "desc": [
                "Integrated sound feedback with Pygame and UI color palette themes.",
                "Integração do sistema de som com Pygame e temas de cores da interface.",
                "Integração do sistema de som com Pygame e temas de cores da interface.",
                "Integración de sonido con Pygame y personalización de temas visuales.",
                "Интеграция звуков через Pygame и поддержка тем оформления.",
                "Pygameによるサウンド再生とUIカラーテーマのサポート。"
            ]
        },
        {
            "ver": "v1.02", "date": "08/09/2026",
            "title": ["OPL Apps & Memory Card", "OPL Apps & Cartões de Memória", "OPL Apps & Cartões de Memória", "OPL Apps y Memory Card", "OPL приложения и карты памяти", "OPLアプリ＆メモリーカード"],
            "desc": [
                "Support for installing homebrew ELF applications and VMC management.",
                "Suporte à instalação de aplicativos homebrew ELF e gerenciamento de VMC.",
                "Suporte à instalação de aplicações homebrew ELF e gestão de VMC.",
                "Instalación de aplicaciones ELF y gestión de tarjetas de memoria virtuales.",
                "Поддержка установки приложений ELF и управление картами памяти VMC.",
                "ELFアプリのインストールと仮想メモリーカード（VMC）管理の追加。"
            ]
        },
        {
            "ver": "v1.03", "date": "29/09/2026",
            "title": ["Cheat Engine", "Criador de Cheats", "Criador de Cheats", "Gestor de Cheats", "Редактор читов", "チートエディタ"],
            "desc": [
                "Raw .cht cheat file editor and manager for PS2RD and OPL.",
                "Adicionado gerenciador e editor de arquivos .cht (RAW) para uso no PS2RD/OPL.",
                "Adicionado gestor e editor de ficheiros .cht (RAW) para uso no PS2RD/OPL.",
                "Gestión y edición de trucos .cht (RAW) para PS2RD y OPL.",
                "Редактор и менеджер файлов читов .cht (RAW) для PS2RD и OPL.",
                "PS2RDおよびOPL用の.cht（RAW）チートファイルの作成・編集機能。"
            ]
        },
        {
            "ver": "v1.04", "date": "01/10/2026",
            "title": ["USBUtil Support", "Suporte a USBUtil", "Suporte a USBUtil", "Soporte USBUtil", "Поддержка USBUtil", "USBUtilサポート"],
            "desc": [
                "Automatic splitting of games over 4GB for FAT32 drives with ul.cfg creation.",
                "Divisão automática de jogos maiores que 4 GB para pendrives FAT32 com geração de ul.cfg.",
                "Divisão automática de jogos maiores que 4 GB para unidades FAT32 com geração de ul.cfg.",
                "División automática de juegos mayores de 4 GB para FAT32 con ul.cfg.",
                "Автоматическое разделение игр более 4 ГБ для FAT32 с созданием ul.cfg.",
                "FAT32ドライブ用に4GB超のゲームを自動分割しul.cfgを生成。"
            ]
        },
        {
            "ver": "v1.05", "date": "02/10/2026",
            "title": ["Stability & Fixes", "Estabilidade & Correções", "Estabilidade & Correções", "Estabilidad y Correcciones", "Стабильность и исправления", "安定性の向上と修正"],
            "desc": [
                "Fixed USB detection on Windows 11, improved game scraper speed and UI responsiveness.",
                "Correção na detecção de pendrives no Windows 11, otimização do scraper e interface.",
                "Correção na deteção de unidades no Windows 11, otimização do scraper e interface.",
                "Corrección en detección USB para Win11 y mejoras de rendimiento general.",
                "Исправлено обнаружение USB в Windows 11, ускорен поиск обложек.",
                "Windows 11でのUSB検出修正、ジャケット取得高速化、応答性改善。"
            ]
        },
        {
            "ver": "v1.06", "date": "10/10/2026",
            "title": ["Disc Analyzer & Installer", "Analisador de Discos", "Analisador de Discos", "Analizador de Discos", "Анализатор оптических дисков", "ディスクアナライザー"],
            "desc": [
                "Direct optical disc analysis, binary header inspection, and custom installer.",
                "Análise direta de CDs/DVDs físicos, leitura de cabeçalhos binários e instalador customizado.",
                "Análise direta de CDs/DVDs físicos, leitura de cabeçalhos binários e instalador personalizado.",
                "Análisis directo de discos físicos, lectura de encabezados e instalador.",
                "Прямой анализ оптических дисков, чтение бинарных заголовков и инсталлятор.",
                "光学ディスクの直接解析、バイナリヘッダー検査、カスタムインストーラーの追加。"
            ]
        },
        {
            "ver": "v1.07", "date": "06/11/2026",
            "title": ["Ultimate PS2 Suite (Current)", "Versão Atual (V1.07)", "Versão Atual (V1.07)", "Versión Actual (V1.07)", "Текущая версия (V1.07)", "現在のバージョン (V1.07)"],
            "desc": [
                "1-Click USB install, batch queue, real DVD burner, modern dark UI, anti-corruption watchdog, laptop mode, 6 languages (PT-BR, PT, EN, ES, RU, JA).",
                "Instalação 1-clique no pendrive, fila de processamento em lote, gravação real de DVD, nova interface moderna, watchdog anti-corrupção, modo notebook, 6 idiomas completos.",
                "Instalação 1-clique no pendrive, fila de processamento por lotes, gravação real de DVD, nova interface moderna, watchdog anti-corrupção, modo portátil, 6 idiomas completos.",
                "Instalación 1-clic en USB, cola por lotes, grabador de DVD real, interfaz moderna, protector anti-corrupción, modo portátil, 6 idiomas.",
                "Установка в 1 клик на USB, пакетная очередь, реальная запись DVD, новый интерфейс, защита от повреждения файлов, режим ноутбука, 6 языков.",
                "1クリックUSBインストール、一括キュー、実DVD書き込み、最新UI、ファイル破損防止監視、ノートPCモード、6言語対応。"
            ]
        },
        {
            "ver": "v1.08+", "date": "Future",
            "title": ["Future Update", "Próxima Atualização", "Próxima Atualização", "Futura Actualización", "Будущее обновление", "将来のアップデート"],
            "desc": [
                "No future updates currently planned. Enjoy all features of v1.07!",
                "Nenhuma atualização planejada no momento. Aproveite todos os recursos da v1.07!",
                "Nenhuma atualização planeada no momento. Aproveite todos os recursos da v1.07!",
                "No hay actualizaciones planificadas actualmente. ¡Disfruta la v1.07!",
                "На данный момент обновлений не планируется. Наслаждайтесь всеми функциями v1.07!",
                "現在計画されている更新はありません。v1.07の全機能をお楽しみください！"
            ]
        }
    ]

    def __init__(self, master):
        super().__init__(master)
        self.title(t("roadmap_title"))
        self.geometry("700x560")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.resizable(False, False)
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.cur_idx = 7  # Índice da v1.07 (atual)
        lang_code = cfg.data.get("language", "PT_BR")
        self.lang_idx = LANGS.get(lang_code, 1)

        ctk.CTkLabel(
            self, text=t("roadmap_title"),
            font=("Segoe UI Black", 18), text_color=cfg.get_color("accent")
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            self, text=t("roadmap_sub"),
            font=("Segoe UI", 12), text_color=cfg.get_color("text_muted")
        ).pack(pady=(0, 15))

        timeline_frm = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=12, border_width=1, border_color=cfg.get_color("border")
        )
        timeline_frm.pack(fill="x", padx=30, pady=10)

        nodes_frm = ctk.CTkFrame(timeline_frm, fg_color="transparent")
        nodes_frm.pack(fill="x", padx=20, pady=(15, 10))
        nodes_frm.grid_columnconfigure(tuple(range(len(self.RELEASES))), weight=1)

        self.node_lbls = []
        for idx, r_data in enumerate(self.RELEASES):
            lbl = ctk.CTkLabel(
                nodes_frm, text=r_data["ver"],
                font=("Segoe UI", 10, "bold"),
                text_color=cfg.get_color("highlight") if idx == self.cur_idx else cfg.get_color("text_muted")
            )
            lbl.grid(row=0, column=idx, padx=4)
            self.node_lbls.append(lbl)

        self.slider = ctk.CTkSlider(
            timeline_frm, from_=0, to=len(self.RELEASES) - 1, number_of_steps=len(self.RELEASES) - 1,
            command=self.on_slide, height=18, progress_color=cfg.get_color("accent")
        )
        self.slider.pack(fill="x", padx=30, pady=(0, 10))
        self.slider.set(self.cur_idx)

        self.card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=14, border_width=1, border_color=cfg.get_color("border")
        )
        self.card.pack(fill="both", expand=True, padx=30, pady=15)

        self.lbl_ver = ctk.CTkLabel(self.card, text="", font=("Segoe UI Black", 24), text_color=cfg.get_color("accent"))
        self.lbl_ver.pack(pady=(20, 2))

        self.lbl_date = ctk.CTkLabel(self.card, text="", font=("Consolas", 12, "bold"), text_color=cfg.get_color("text_muted"))
        self.lbl_date.pack(pady=(0, 15))

        self.lbl_title = ctk.CTkLabel(self.card, text="", font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main"))
        self.lbl_title.pack(pady=(0, 10))

        self.lbl_desc = ctk.CTkLabel(
            self.card, text="", font=("Segoe UI", 13),
            text_color=cfg.get_color("text_main"), wraplength=550, justify="center"
        )
        self.lbl_desc.pack(pady=(0, 20), padx=30)

        nav_frm = ctk.CTkFrame(self, fg_color="transparent")
        nav_frm.pack(fill="x", padx=30, pady=(0, 20))
        ctk.CTkButton(
            nav_frm, text=t("roadmap_prev"), width=140,
            fg_color=cfg.get_color("card_base"), hover_color=cfg.get_color("card_hover"),
            command=lambda: self.step(-1)
        ).pack(side="left")
        ctk.CTkButton(
            nav_frm, text=t("roadmap_next"), width=140,
            fg_color=cfg.get_color("card_base"), hover_color=cfg.get_color("card_hover"),
            command=lambda: self.step(1)
        ).pack(side="right")

        self.update_view()

    def on_slide(self, val):
        self.cur_idx = int(round(val))
        self.update_view()

    def step(self, delta):
        self.cur_idx = max(0, min(len(self.RELEASES) - 1, self.cur_idx + delta))
        self.slider.set(self.cur_idx)
        self.update_view()

    def update_view(self):
        item = self.RELEASES[self.cur_idx]
        is_cur = (self.cur_idx == 7)
        self.lbl_ver.configure(
            text=f"{item['ver']} - {t('roadmap_cur')}" if is_cur else item['ver'],
            text_color=cfg.get_color("highlight") if is_cur else cfg.get_color("accent")
        )
        self.lbl_date.configure(text=f"Release Date: {item['date']}")
        t_list = item["title"]
        title_text = t_list[self.lang_idx] if self.lang_idx < len(t_list) else (t_list[0] if isinstance(t_list, list) else str(t_list))
        d_list = item["desc"]
        desc_text = d_list[self.lang_idx] if self.lang_idx < len(d_list) else (d_list[0] if isinstance(d_list, list) else str(d_list))
        self.lbl_title.configure(text=title_text)
        self.lbl_desc.configure(text=desc_text)
        for idx, lbl in enumerate(self.node_lbls):
            if idx == self.cur_idx:
                lbl.configure(text_color=cfg.get_color("highlight"), font=("Segoe UI", 11, "bold"))
            else:
                lbl.configure(text_color=cfg.get_color("text_muted"), font=("Segoe UI", 10))

class NotificationPopup(ctk.CTkFrame):
    def __init__(self, master, message, kind="info"):
        color = cfg.get_color("accent")
        if kind == "success": color = cfg.get_color("success")
        elif kind == "error": color = cfg.get_color("danger")
        elif kind == "warning": color = cfg.get_color("warning")
        super().__init__(master, fg_color=color, corner_radius=cfg.get_radius("chip"))
        ctk.CTkLabel(self, text=message, font=("Segoe UI", 12, "bold"), text_color="#FFFFFF").pack(padx=20, pady=10)
        self.place(relx=0.5, rely=0.05, anchor="n")
        self.after(3000, self.dismiss)

    def dismiss(self):
        try:
            self.destroy()
        except Exception:
            pass

class HoverCard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        self.default_fg = kwargs.get("fg_color", cfg.get_color("card_base"))
        self.hover_fg = kwargs.pop("hover_color", cfg.get_color("card_hover"))
        self.on_click_cb = kwargs.pop("command", None)
        super().__init__(master, **kwargs)
        if not cfg.data.get("laptop_mode", False):
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
        if self.on_click_cb:
            self.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        if cfg.data.get("animations", True) and not cfg.data.get("laptop_mode", False):
            self.configure(fg_color=self.hover_fg)

    def _on_leave(self, e):
        self.configure(fg_color=self.default_fg)

    def _on_click(self, e):
        if self.on_click_cb:
            self.on_click_cb()

    def bind_children(self, widget):
        if not cfg.data.get("laptop_mode", False):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
        if self.on_click_cb:
            widget.bind("<Button-1>", self._on_click)
        for child in widget.winfo_children():
            self.bind_children(child)

class GameDetailsModal(ctk.CTkToplevel):
    def __init__(self, master, game_data):
        super().__init__(master)
        self.title(t("modal_game_profile"))
        self.geometry("480x480")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.resizable(False, False)
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.app, self.game_data = master, game_data
        ctk.CTkLabel(
            self, text=game_data.get('name', 'Unknown'),
            font=("Segoe UI Black", 16), text_color=cfg.get_color("text_main")
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            self, text=game_data.get('path', ''),
            font=("Consolas", 9), text_color=cfg.get_color("text_muted")
        ).pack(pady=(0, 15))

        frm = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=1, border_color=cfg.get_color("border")
        )
        frm.pack(fill="x", padx=20, pady=5)

        def add_row(r, k, v):
            ctk.CTkLabel(frm, text=k, font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_muted")).grid(row=r, column=0, sticky="w", padx=15, pady=4)
            ctk.CTkLabel(frm, text=v, font=("Consolas", 11), text_color=cfg.get_color("text_main")).grid(row=r, column=1, sticky="w", padx=15, pady=4)

        add_row(0, t("game_id"), game_data.get('id', 'N/A'))
        add_row(1, t("game_format"), f"{game_data.get('format', 'N/A')} ({game_data.get('media_type', 'DVD')})")
        add_row(2, t("game_size"), game_data.get('size_str', 'N/A'))
        add_row(3, t("game_region"), game_data.get('region', 'Unknown'))

        cfg_frm = ctk.CTkFrame(self, fg_color="transparent")
        cfg_frm.pack(fill="x", padx=20, pady=12)

        ctk.CTkLabel(cfg_frm, text=t("cfg_vid"), font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.var_video = ctk.StringVar(value=game_data.get('video_mode', 'Auto'))
        ctk.CTkOptionMenu(
            cfg_frm, variable=self.var_video, values=["Auto", "PAL", "NTSC"],
            height=28, corner_radius=cfg.get_radius("entry")
        ).grid(row=0, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(cfg_frm, text=t("cfg_res"), font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.var_res = ctk.StringVar(value=game_data.get('resolution', 'Default'))
        ctk.CTkOptionMenu(
            cfg_frm, variable=self.var_res, values=["Default", "480p", "720p", "1080i", "1080p"],
            height=28, corner_radius=cfg.get_radius("entry")
        ).grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkButton(
            cfg_frm, text=t("cfg_save"), height=28, width=90,
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.save_cfg
        ).grid(row=0, column=2, rowspan=2, padx=(5, 0))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10, padx=20)
        rad = cfg.get_radius("button")
        ctk.CTkButton(
            btn_frame, text=t("lib_btn_test"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), corner_radius=rad,
            command=lambda: PCSX2Integration.test_iso(game_data['path'], lambda e: messagebox.showerror(t("error"), e))
        ).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(
            btn_frame, text=t("lib_btn_inst"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("success"), corner_radius=rad,
            command=self.send_to_install
        ).pack(side="left", expand=True, padx=5)

        btn_frame2 = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame2.pack(fill="x", pady=(0, 15), padx=20)
        ctk.CTkButton(
            btn_frame2, text=t("lib_btn_rem"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("danger"), corner_radius=rad, command=self.remove_game
        ).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(
            btn_frame2, text=t("lib_btn_close"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("border"), text_color=cfg.get_color("text_main"),
            corner_radius=rad, command=self.destroy
        ).pack(side="right", expand=True, padx=(5, 0))

    def send_to_install(self):
        self.destroy()
        self.app.show("single_install")
        if "single_install" in self.app.pages:
            self.app.pages["single_install"].set_iso(self.game_data['path'])

    def remove_game(self):
        if messagebox.askyesno(t("confirm"), t("msg_remove_confirm")):
            self.app.library.games = [g for g in self.app.library.games if g['path'] != self.game_data['path']]
            db.save()
            sound_fx.play_success()
            self.app.refresh_all()
            self.destroy()

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
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write("\n".join(content))
            sound_fx.play_success()
            messagebox.showinfo(t("success"), f"{t('cfg_save')} - {self.game_data['id']}")
        except Exception as e:
            sound_fx.play_error()
            messagebox.showerror(t("error"), str(e))

class CheatEditorModal(ctk.CTkToplevel):
    def __init__(self, master, app, cht_folder, edit_file=None):
        super().__init__(master)
        self.title("PS2Manager Cheats")
        self.geometry("600x580")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.app, self.cht_folder, self.edit_file = app, cht_folder, edit_file
        games_list = app.library.games
        if not self.edit_file:
            ctk.CTkLabel(self, text=t("cht_sel_game"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("accent")).pack(pady=(20, 5), padx=20, anchor="w")
            self.cmb_games = ctk.CTkComboBox(
                self, values=[t("cht_manual")] + [f"{g.get('id', 'Unknown')} - {g.get('name', 'Unknown')}" for g in games_list],
                command=self.on_game_select, fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry")
            )
            self.cmb_games.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text=t("cht_name"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(15, 5), padx=20, anchor="w")
        self.ent_name = ctk.CTkEntry(self, font=("Consolas", 12), fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("entry"))
        self.ent_name.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Cheat Codes (RAW):", font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(15, 5), padx=20, anchor="w")
        self.txt_codes = ctk.CTkTextbox(
            self, font=("Consolas", 12), fg_color=cfg.get_color("card_base"),
            border_color=cfg.get_color("border"), border_width=cfg.get_border_width(),
            text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("card")
        )
        self.txt_codes.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkButton(self, text=t("cht_save"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), height=40, corner_radius=cfg.get_radius("button"), command=self.save).pack(fill="x", padx=20, pady=(0, 20))

        if self.edit_file:
            base_name = os.path.basename(self.edit_file)
            if base_name.endswith('.disabled'): base_name = base_name[:-9]
            if base_name.endswith('.cht'): base_name = base_name[:-4]
            self.ent_name.insert(0, base_name)
            try:
                with open(self.edit_file, 'r', encoding='utf-8') as f:
                    self.txt_codes.insert("0.0", f.read())
            except Exception as e:
                messagebox.showerror(t("error"), str(e))

    def on_game_select(self, val):
        if val == t("cht_manual"): return
        game_id = val.split(" - ")[0]
        game_name = val.split(" - ", 1)[1] if " - " in val else ""
        self.ent_name.delete(0, 'end')
        self.ent_name.insert(0, game_id)
        if not self.txt_codes.get("0.0", "end").strip():
            self.txt_codes.insert("0.0", f"// Cheat name: {game_name}\n\n")

    def save(self):
        name = self.ent_name.get().strip()
        if not name: return
        if not name.lower().endswith(".cht"): name += ".cht"
        if self.edit_file and self.edit_file.endswith(".disabled"): name += ".disabled"
        out_path = os.path.join(self.cht_folder, name)
        try:
            if self.edit_file and os.path.abspath(self.edit_file) != os.path.abspath(out_path) and os.path.exists(self.edit_file):
                os.remove(self.edit_file)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(self.txt_codes.get("0.0", "end"))
            sound_fx.play_success()
            messagebox.showinfo(t("success"), t("cht_succ"))
            self.app.refresh_all()
            self.destroy()
        except Exception as e:
            sound_fx.play_error()
            messagebox.showerror(t("error"), f"{t('cht_err')} {e}")

class AddCheatModal(ctk.CTkToplevel):
    def __init__(self, master, app, cht_folder):
        super().__init__(master)
        self.title(t("cht_add"))
        self.geometry("350x250")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.app, self.cht_folder = app, cht_folder
        ctk.CTkLabel(self, text=t("cht_add"), font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(20, 30))
        r = cfg.get_radius("button")
        ctk.CTkButton(self, text=t("cht_import"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=r, command=self.import_cht).pack(fill="x", padx=40, pady=10)
        ctk.CTkButton(self, text=t("cht_create"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), height=40, corner_radius=r, command=self.create_scratch).pack(fill="x", padx=40, pady=10)

    def import_cht(self):
        f = filedialog.askopenfilename(filetypes=[("Cheat Files", "*.cht")])
        if f:
            try:
                shutil.copy2(f, self.cht_folder)
                sound_fx.play_success()
                self.app.refresh_all()
                self.destroy()
            except Exception as e:
                sound_fx.play_error()
                messagebox.showerror(t("error"), f"{t('cht_err')} {e}")

    def create_scratch(self):
        self.destroy()
        CheatEditorModal(self.master, self.app, self.cht_folder)

class CheatManagerPage(ctk.CTkFrame):
    """Gerenciador completo de Cheats .cht (RAW) para Open PS2 Loader e PS2RD."""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app, self.current_folder, self.selected_file = app, cfg.data.get("last_cht_folder", ""), None
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ctk.CTkLabel(head, text=t("tab_cht"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).pack(side="left")

        folder_frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card"))
        folder_frm.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(folder_frm, text=t("cht_folder"), font=("Segoe UI", 11, "bold")).pack(side="left", padx=15, pady=10)
        self.ent_folder = ctk.CTkEntry(folder_frm, fg_color=cfg.get_color("bg_main"), height=28, corner_radius=cfg.get_radius("entry"))
        self.ent_folder.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)
        if self.current_folder:
            self.ent_folder.insert(0, self.current_folder)
        ctk.CTkButton(folder_frm, text=t("btn_browse"), font=("Segoe UI", 11, "bold"), width=80, fg_color=cfg.get_color("border"), corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left", padx=(0, 15), pady=10)

        act_frm = ctk.CTkFrame(self, fg_color="transparent")
        act_frm.grid(row=2, column=0, sticky="new", pady=(0, 10))
        r = cfg.get_radius("button")
        ctk.CTkButton(act_frm, text=t("cht_add"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("accent"), corner_radius=r, command=lambda: AddCheatModal(self, self.app, self.current_folder) if (self.current_folder and os.path.exists(self.current_folder)) else messagebox.showerror(t("error"), "Select folder first")).pack(side="left", padx=(0, 5))
        ctk.CTkButton(act_frm, text=t("cht_edit"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("warning"), text_color="#000", corner_radius=r, command=lambda: CheatEditorModal(self, self.app, self.current_folder, self.selected_file) if self.selected_file else messagebox.showwarning(t("warning"), t("cht_none"))).pack(side="left", padx=5)
        ctk.CTkButton(act_frm, text=t("cht_enable"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("success"), corner_radius=r, command=self.enable_cheat).pack(side="left", padx=5)
        ctk.CTkButton(act_frm, text=t("cht_disable"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("danger"), corner_radius=r, command=self.disable_cheat).pack(side="left", padx=5)

        self.list_frm = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frm.grid(row=3, column=0, sticky="nsew")
        self.refresh()

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.ent_folder.delete(0, 'end')
            self.ent_folder.insert(0, d)
            self.current_folder = d
            cfg.data["last_cht_folder"] = d
            cfg.save()
            self.refresh()

    def refresh(self):
        self.current_folder = self.ent_folder.get()
        if not self.current_folder or not os.path.exists(self.current_folder):
            return
        self.selected_file = None
        for w in self.list_frm.winfo_children():
            w.destroy()
        try:
            for f in os.listdir(self.current_folder):
                if f.lower().endswith((".cht", ".disabled")):
                    self.add_cheat_card(f)
        except Exception:
            pass

    def add_cheat_card(self, filename):
        is_disabled = filename.lower().endswith(".disabled")
        color = cfg.get_color("danger") if is_disabled else cfg.get_color("success")
        card = ctk.CTkFrame(
            self.list_frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"),
            height=36, border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        card.pack(fill="x", pady=2)
        card.pack_propagate(False)
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(0, weight=1)
        ctk.CTkFrame(card, width=4, fg_color=color, corner_radius=0).grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ctk.CTkLabel(card, text=filename, font=("Consolas", 12, "bold"), text_color=cfg.get_color("text_main")).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(card, text=t("cht_disabled") if is_disabled else t("cht_enabled"), font=("Segoe UI", 10, "bold"), text_color=color).grid(row=0, column=2, sticky="e", padx=15)

        def on_click(e, f=filename, c=card):
            self.selected_file = os.path.join(self.current_folder, f)
            for w in self.list_frm.winfo_children():
                w.configure(fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border"))
            c.configure(fg_color=cfg.get_color("card_hover"), border_color=cfg.get_color("accent"))
            sound_fx.play_click()

        card.bind("<Button-1>", on_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_click)

    def enable_cheat(self):
        if self.selected_file and self.selected_file.endswith(".disabled"):
            try:
                os.rename(self.selected_file, self.selected_file[:-9])
                sound_fx.play_success()
                self.refresh()
            except Exception as e:
                messagebox.showerror(t("error"), str(e))

    def disable_cheat(self):
        if self.selected_file and self.selected_file.endswith(".cht"):
            try:
                os.rename(self.selected_file, self.selected_file + ".disabled")
                sound_fx.play_success()
                self.refresh()
            except Exception as e:
                messagebox.showerror(t("error"), str(e))

class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            self, text=t("tab_dash"), font=("Segoe UI Black", 18),
            text_color=cfg.get_color("text_main")
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 15))

        self.card_games = self.create_card(0, t("dash_games"), "0", cfg.get_color("accent"))
        self.card_usb = self.create_card(1, t("dash_usb"), "0", cfg.get_color("success"))
        self.card_size = self.create_card(2, t("dash_size"), "0 GB", cfg.get_color("warning"))

    def create_card(self, col, title, initial_val, color):
        c = HoverCard(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"), height=100,
            border_width=1, border_color=cfg.get_color("border")
        )
        c.grid(row=1, column=col, padx=6, sticky="nsew")
        c.pack_propagate(False)

        ctk.CTkLabel(c, text=title, font=("Segoe UI", 11, "bold"), text_color=color).pack(pady=(15, 2))
        lbl_val = ctk.CTkLabel(c, text=initial_val, font=("Segoe UI Black", 22), text_color=cfg.get_color("text_main"))
        lbl_val.pack()
        c.bind_children(c)
        return lbl_val

    def refresh(self):
        games = self.app.library.games
        self.card_games.configure(text=str(len(games)))
        drives = UsbDetector.get_removable_drives()
        self.card_usb.configure(text=str(len(drives)))
        total_b = sum(g.get('size_bytes', 0) for g in games)
        self.card_size.configure(text=format_size(total_b))

class GamesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(header, text=t("tab_lib"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).pack(side="left")
        ctk.CTkButton(
            header, text=t("lib_scan"), font=("Segoe UI", 11, "bold"),
            height=32, corner_radius=cfg.get_radius("button"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_color("accent_hover"),
            command=self.scan_folder
        ).pack(side="right")

        f_search = ctk.CTkFrame(self, fg_color="transparent")
        f_search.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.ent_search = ctk.CTkEntry(
            f_search, placeholder_text=t("lib_search"),
            fg_color=cfg.get_color("card_base"), border_color=cfg.get_color("border"),
            height=36, corner_radius=cfg.get_radius("entry")
        )
        self.ent_search.pack(fill="x")
        self.ent_search.bind("<KeyRelease>", lambda e: self.render_list())

        self.list_box = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"), border_width=1,
            border_color=cfg.get_color("border")
        )
        self.list_box.grid(row=2, column=0, sticky="nsew")

    def scan_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.app.library.scan_directory(p)
            sound_fx.play_success()
            NotificationPopup(self.app, t("lib_scan_done"), "success")
            self.render_list()

    def refresh(self):
        self.render_list()

    def render_list(self):
        for w in self.list_box.winfo_children():
            w.destroy()
        q = self.ent_search.get().lower().strip()
        games = [g for g in self.app.library.games if q in g.get('name', '').lower() or q in g.get('id', '').lower()]
        for g in games:
            card = HoverCard(
                self.list_box, height=44, corner_radius=cfg.get_radius("chip"),
                fg_color=cfg.get_color("bg_main"), hover_color=cfg.get_color("card_hover"),
                command=lambda gd=g: GameDetailsModal(self.app, gd)
            )
            card.pack(fill="x", pady=3, padx=4)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=g.get('name', 'Unknown'), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(side="left", padx=12)
            ctk.CTkLabel(card, text=g.get('id', 'N/A'), font=("Consolas", 11, "bold"), text_color=cfg.get_color("accent")).pack(side="left", padx=10)
            ctk.CTkLabel(card, text=g.get('size_str', ''), font=("Consolas", 10), text_color=cfg.get_color("text_muted")).pack(side="right", padx=15)
            card.bind_children(card)

class SingleInstallPage(ctk.CTkFrame):
    """Instalador 1-Clique inteligente para pendrive/HD USB 100% localizado."""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_install"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))

        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=1, border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card"))
        frm.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(frm, text=t("inst_step1"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(anchor="w", padx=20, pady=(20, 5))
        f_iso = ctk.CTkFrame(frm, fg_color="transparent")
        f_iso.pack(fill="x", padx=20)
        self.ent_iso = ctk.CTkEntry(f_iso, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_iso.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_iso, text=t("btn_select"), width=90, corner_radius=cfg.get_radius("button"), command=self.browse_iso).pack(side="left", padx=10)

        ctk.CTkLabel(frm, text=t("inst_step2"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(anchor="w", padx=20, pady=(15, 5))
        self.ent_name = ctk.CTkEntry(frm, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_name.pack(fill="x", padx=20)

        ctk.CTkLabel(frm, text=t("inst_step3"), font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(anchor="w", padx=20, pady=(15, 5))
        self.var_drive = ctk.StringVar(value="Select USB...")
        self.cmb_drive = ctk.CTkOptionMenu(frm, variable=self.var_drive, values=["Select USB..."], height=32, corner_radius=cfg.get_radius("entry"))
        self.cmb_drive.pack(fill="x", padx=20)

        self.var_art = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frm, text=t("inst_auto_art"), variable=self.var_art, font=("Segoe UI", 12)).pack(anchor="w", padx=20, pady=15)

        self.btn_install = ctk.CTkButton(frm, text=t("inst_btn"), font=("Segoe UI", 13, "bold"), height=42, fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=self.start_install)
        self.btn_install.pack(pady=20, padx=20, fill="x")

        self.lbl_status = ctk.CTkLabel(frm, text=t("inst_ready"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted"))
        self.lbl_status.pack(pady=(0, 5))

        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("highlight"))
        self.prog.pack(fill="x", padx=20, pady=(0, 20))
        self.prog.set(0)

    def set_iso(self, path):
        self.ent_iso.delete(0, 'end')
        self.ent_iso.insert(0, path)
        base_name = os.path.splitext(os.path.basename(path))[0]
        self.ent_name.delete(0, 'end')
        self.ent_name.insert(0, base_name[:32])

    def browse_iso(self):
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso *.bin *.zso")])
        if f:
            self.set_iso(f)

    def refresh(self):
        drives = UsbDetector.get_removable_drives()
        vals = [f"{d['mountpoint']} [{d['fstype']}] - {d['device']}" for d in drives]
        if not vals: vals = [t("inst_err_nodrive")]
        self.cmb_drive.configure(values=vals)
        if self.var_drive.get() not in vals and vals:
            self.var_drive.set(vals[0])

    def start_install(self):
        iso = self.ent_iso.get().strip()
        drv_str = self.var_drive.get()
        name = self.ent_name.get().strip()
        if not iso or not os.path.exists(iso) or drv_str == t("inst_err_nodrive"):
            messagebox.showerror(t("error"), t("inst_err_select"))
            return

        mp = drv_str.split(" ")[0]
        drives = UsbDetector.get_removable_drives()
        target_d = next((d for d in drives if d['mountpoint'].upper() == mp.upper() or d['device'].upper() == mp.upper()), None)
        if not target_d:
            messagebox.showerror(t("error"), t("inst_err_nodrive"))
            return

        self.btn_install.configure(state="disabled")
        self.prog.set(0)
        self.lbl_status.configure(text=t("inst_starting"))

        def on_done(s):
            self.app.after(0, lambda: [
                self.btn_install.configure(state="normal"),
                self.prog.set(1.0),
                self.lbl_status.configure(text=t("inst_done")),
                sound_fx.play_success(),
                messagebox.showinfo(t("success"), t("inst_succ_msg"))
            ])

        def on_err(e):
            self.app.after(0, lambda: [
                self.btn_install.configure(state="normal"),
                self.lbl_status.configure(text=f"{t('error')}: {e}"),
                sound_fx.play_error(),
                messagebox.showerror(t("error"), f"{t('inst_err_fail')} {e}")
            ])

        def on_prog(v):
            self.app.after(0, lambda: self.prog.set(v))

        SingleInstallWorker.install(iso, target_d, name, self.var_art.get(), on_prog, on_done, on_err)

class BatchInstallPage(ctk.CTkFrame):
    """Fila de processamento em lote para instalar múltiplos jogos de uma vez 100% localizada."""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.queue_items = []
        self.worker = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text=t("tab_batch"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).pack(side="left")

        btn_f = ctk.CTkFrame(header, fg_color="transparent")
        btn_f.pack(side="right")
        ctk.CTkButton(btn_f, text=f"+ {t('btn_browse')}", width=110, height=32, corner_radius=cfg.get_radius("button"), command=self.add_files).pack(side="left", padx=4)
        ctk.CTkButton(btn_f, text=t("lib_scan"), width=120, height=32, corner_radius=cfg.get_radius("button"), command=self.add_folder).pack(side="left", padx=4)
        ctk.CTkButton(btn_f, text=t("btn_cancel"), width=80, height=32, fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"), command=self.clear_queue).pack(side="left", padx=4)

        self.list_box = ctk.CTkScrollableFrame(self, fg_color=cfg.get_color("card_base"), border_width=1, border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card"))
        self.list_box.grid(row=1, column=0, sticky="nsew", pady=5)

        bottom = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=1, border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card"))
        bottom.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        drv_row = ctk.CTkFrame(bottom, fg_color="transparent")
        drv_row.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(drv_row, text=t("inst_step3"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_main")).pack(side="left", padx=(0, 10))
        self.var_drive = ctk.StringVar(value="Select USB...")
        self.cmb_drive = ctk.CTkOptionMenu(drv_row, variable=self.var_drive, values=["Select USB..."], height=28, corner_radius=cfg.get_radius("entry"))
        self.cmb_drive.pack(side="left", fill="x", expand=True)

        self.var_art = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(drv_row, text=t("inst_auto_art"), variable=self.var_art, font=("Segoe UI", 11)).pack(side="left", padx=15)

        prog_f = ctk.CTkFrame(bottom, fg_color="transparent")
        prog_f.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(prog_f, text=t("batch_prog_total"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_main")).pack(anchor="w")
        self.prog_total = ctk.CTkProgressBar(prog_f, progress_color=cfg.get_color("accent"))
        self.prog_total.pack(fill="x", pady=(2, 6))
        self.prog_total.set(0)

        ctk.CTkLabel(prog_f, text=t("batch_prog_cur"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted")).pack(anchor="w")
        self.prog_item = ctk.CTkProgressBar(prog_f, progress_color=cfg.get_color("highlight"))
        self.prog_item.pack(fill="x", pady=(2, 10))
        self.prog_item.set(0)

        self.btn_start = ctk.CTkButton(bottom, text=t("tab_batch"), font=("Segoe UI", 12, "bold"), height=38, fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=self.start_batch)
        self.btn_start.pack(fill="x", padx=15, pady=(0, 12))
        self.refresh_queue_view()

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[(t("iso_files"), "*.iso *.bin *.zso")])
        for f in files:
            if not any(x['path'] == f for x in self.queue_items):
                sz = os.path.getsize(f)
                self.queue_items.append({'path': f, 'name': os.path.splitext(os.path.basename(f))[0][:32], 'size': format_size(sz)})
        self.refresh_queue_view()

    def add_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(('.iso', '.bin', '.zso')):
                        full_p = os.path.join(root, f)
                        if not any(x['path'] == full_p for x in self.queue_items):
                            sz = os.path.getsize(full_p)
                            self.queue_items.append({'path': full_p, 'name': os.path.splitext(f)[0][:32], 'size': format_size(sz)})
            self.refresh_queue_view()

    def clear_queue(self):
        self.queue_items.clear()
        self.refresh_queue_view()

    def refresh(self):
        drives = UsbDetector.get_removable_drives()
        vals = [f"{d['mountpoint']} [{d['fstype']}] - {d['device']}" for d in drives]
        if not vals: vals = [t("inst_err_nodrive")]
        self.cmb_drive.configure(values=vals)
        if self.var_drive.get() not in vals and vals:
            self.var_drive.set(vals[0])

    def refresh_queue_view(self):
        for w in self.list_box.winfo_children(): w.destroy()
        if not self.queue_items:
            ctk.CTkLabel(self.list_box, text=t("batch_empty"), text_color=cfg.get_color("text_muted")).pack(pady=40)
            return
        for idx, item in enumerate(self.queue_items):
            row = ctk.CTkFrame(self.list_box, fg_color=cfg.get_color("bg_main"), height=36)
            row.pack(fill="x", pady=2, padx=4); row.pack_propagate(False)
            ctk.CTkLabel(row, text=f"{idx+1}. {item['name']}", font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_main")).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=item['size'], font=("Consolas", 10), text_color=cfg.get_color("text_muted")).pack(side="left", padx=10)
            ctk.CTkButton(row, text="X", width=28, height=24, fg_color=cfg.get_color("danger"), corner_radius=4, command=lambda i=idx: self.remove_item(i)).pack(side="right", padx=10)

    def remove_item(self, idx):
        if 0 <= idx < len(self.queue_items):
            self.queue_items.pop(idx)
            self.refresh_queue_view()

    def start_batch(self):
        if not self.queue_items:
            messagebox.showwarning(t("warning"), t("batch_warn_empty"))
            return
        drv_str = self.var_drive.get()
        if drv_str == t("inst_err_nodrive"):
            messagebox.showerror(t("error"), t("batch_err_nodrive"))
            return
        mp = drv_str.split(" ")[0]
        drives = UsbDetector.get_removable_drives()
        target_d = next((d for d in drives if d['mountpoint'].upper() == mp.upper() or d['device'].upper() == mp.upper()), None)
        if not target_d:
            messagebox.showerror(t("error"), t("batch_err_nodrive"))
            return

        self.btn_start.configure(state="disabled")
        self.prog_total.set(0); self.prog_item.set(0)

        def on_done(success):
            self.app.after(0, lambda: [
                self.btn_start.configure(state="normal"),
                self.prog_total.set(1.0), self.prog_item.set(1.0),
                sound_fx.play_success(),
                messagebox.showinfo(t("batch_done_title"), t("batch_done_msg")),
                self.clear_queue()
            ])

        self.worker = BatchInstallWorker(
            self.queue_items.copy(), target_d, self.var_art.get(),
            cb_item_prog=lambda v: self.app.after(0, lambda: self.prog_item.set(v)),
            cb_total_prog=lambda v: self.app.after(0, lambda: self.prog_total.set(v)),
            cb_log=lambda m: sys_logger.log(m, "BATCH"),
            cb_done=on_done
        )
        self.worker.start()

class DvdBurnerPage(ctk.CTkFrame):
    """Aba para gravação física de DVDs com velocidade e barra de progresso (sem simulações falsas)."""
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("burn_title"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))

        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=1, border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card"))
        frm.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(frm, text=t("burn_iso"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        f_iso = ctk.CTkFrame(frm, fg_color="transparent")
        f_iso.pack(fill="x", padx=20)
        self.ent_iso = ctk.CTkEntry(f_iso, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_iso.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_iso, text=t("btn_select"), width=90, corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left", padx=10)

        ctk.CTkLabel(frm, text=t("burn_drv"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.var_drv = ctk.StringVar(value=t("burn_no_drives"))
        self.cmb_drv = ctk.CTkOptionMenu(frm, variable=self.var_drv, values=[t("burn_no_drives")], height=32, corner_radius=cfg.get_radius("entry"))
        self.cmb_drv.pack(fill="x", padx=20)

        ctk.CTkLabel(frm, text=t("burn_spd"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.var_spd = ctk.StringVar(value="4x (OPL/PS2)")
        self.cmb_spd = ctk.CTkOptionMenu(frm, variable=self.var_spd, values=["1x", "2x", "4x (OPL/PS2)", "8x", "16x", "MAX"], height=32, corner_radius=cfg.get_radius("entry"))
        self.cmb_spd.pack(fill="x", padx=20)

        self.btn_burn = ctk.CTkButton(frm, text=t("burn_btn"), font=("Segoe UI", 13, "bold"), height=42, fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"), command=self.start_burn)
        self.btn_burn.pack(pady=20, padx=20, fill="x")

        self.lbl_status = ctk.CTkLabel(frm, text=t("burn_ready"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted"))
        self.lbl_status.pack(pady=(0, 5))

        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent"))
        self.prog.pack(fill="x", padx=20, pady=(0, 20))
        self.prog.set(0)

    def browse(self):
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso")])
        if f:
            self.ent_iso.delete(0, 'end')
            self.ent_iso.insert(0, f)

    def refresh(self):
        burners = DvdBurnerWorker.list_burners()
        vals = [b['name'] for b in burners] if burners else [t("burn_no_drives")]
        self.cmb_drv.configure(values=vals)
        if self.var_drv.get() not in vals and vals:
            self.var_drv.set(vals[0])

    def start_burn(self):
        iso = self.ent_iso.get().strip()
        if not iso or not os.path.exists(iso):
            messagebox.showerror(t("error"), t("burn_err_select_iso"))
            return

        drv_name = self.var_drv.get()
        if drv_name == t("burn_no_drives"):
            messagebox.showerror(t("error"), t("burn_err_nomedia"))
            return

        burners = DvdBurnerWorker.list_burners()
        target_b = next((b for b in burners if b['name'] == drv_name), None)
        target_id = target_b['id'] if target_b else drv_name

        self.btn_burn.configure(state="disabled")
        self.prog.set(0)
        self.lbl_status.configure(text=t("burn_progress_msg"))

        def on_done(s):
            self.app.after(0, lambda: [
                self.btn_burn.configure(state="normal"),
                self.prog.set(1.0),
                self.lbl_status.configure(text=t("burn_done")),
                sound_fx.play_success(),
                messagebox.showinfo(t("success"), t("burn_done"))
            ])

        def on_err(e):
            self.app.after(0, lambda: [
                self.btn_burn.configure(state="normal"),
                self.lbl_status.configure(text=f"{t('error')}: {e}"),
                sound_fx.play_error(),
                messagebox.showerror(t("burn_err_title"), str(e))
            ])

        def on_prog(v):
            self.app.after(0, lambda: [
                self.prog.set(v),
                self.lbl_status.configure(text=f"{t('burn_writing_sectors')} {int(v*100)}%")
            ])

        DvdBurnerWorker.burn(iso, target_id, self.var_spd.get(), on_prog, on_done, on_err)

class EmulatorTestPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_emu"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))

        card = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text="Quick Play Test (PCSX2):", font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(anchor="w", padx=20, pady=(20, 5))
        self.var_game = ctk.StringVar(value="Select Game...")
        self.cmb_game = ctk.CTkOptionMenu(card, variable=self.var_game, values=["Select Game..."], height=32, corner_radius=cfg.get_radius("entry"))
        self.cmb_game.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(
            card, text=t("lib_btn_test"), font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"),
            command=self.run_test
        ).pack(fill="x", padx=20, pady=20)

    def refresh(self):
        games = self.app.library.games
        vals = [g['name'] for g in games] or ["No games in library"]
        self.cmb_game.configure(values=vals)
        if self.var_game.get() not in vals and vals:
            self.var_game.set(vals[0])

    def run_test(self):
        sel = self.var_game.get()
        g = next((x for x in self.app.library.games if x['name'] == sel), None)
        if g:
            PCSX2Integration.test_iso(g['path'], lambda e: messagebox.showerror(t("error"), e))

class AppsManagerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_apps"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))

        card = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text=t("app_name"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.ent_title = ctk.CTkEntry(card, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_title.pack(fill="x", padx=20)

        ctk.CTkLabel(card, text=t("app_elf"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        btn_frm = ctk.CTkFrame(card, fg_color="transparent")
        btn_frm.pack(fill="x", padx=20)
        self.ent_elf = ctk.CTkEntry(btn_frm, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_elf.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(btn_frm, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left", padx=10)

        ctk.CTkLabel(card, text=t("app_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.var_drive = ctk.StringVar(value="Select USB...")
        self.cmb_drive = ctk.CTkOptionMenu(card, variable=self.var_drive, values=["Select USB..."], height=32, corner_radius=cfg.get_radius("entry"))
        self.cmb_drive.pack(fill="x", padx=20)

        ctk.CTkButton(
            card, text=t("app_btn"), font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"),
            command=self.install
        ).pack(fill="x", padx=20, pady=25)

    def browse(self):
        f = filedialog.askopenfilename(filetypes=[("ELF Executables", "*.elf")])
        if f:
            self.ent_elf.delete(0, 'end')
            self.ent_elf.insert(0, f)
            if not self.ent_title.get():
                self.ent_title.insert(0, os.path.splitext(os.path.basename(f))[0])

    def refresh(self):
        drives = UsbDetector.get_removable_drives()
        vals = [d['mountpoint'] for d in drives] or ["No USB connected"]
        self.cmb_drive.configure(values=vals)
        if self.var_drive.get() not in vals and vals:
            self.var_drive.set(vals[0])

    def install(self):
        res = AppManager.install_elf(self.cmb_drive.get(), self.ent_title.get(), self.ent_elf.get())
        if res is True:
            sound_fx.play_success()
            messagebox.showinfo(t("success"), t("app_succ"))
        else:
            sound_fx.play_error()
            messagebox.showerror(t("error"), res)

class IsoExtractorPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_iso"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))

        card = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text="Source ISO Image:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        src_frm = ctk.CTkFrame(card, fg_color="transparent")
        src_frm.pack(fill="x", padx=20)
        self.ent_src = ctk.CTkEntry(src_frm, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_src.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(src_frm, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=self.browse_src).pack(side="left", padx=10)

        ctk.CTkLabel(card, text="Output Directory:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        dst_frm = ctk.CTkFrame(card, fg_color="transparent")
        dst_frm.pack(fill="x", padx=20)
        self.ent_dst = ctk.CTkEntry(dst_frm, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_dst.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dst_frm, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=self.browse_dst).pack(side="left", padx=10)

        self.btn_ext = ctk.CTkButton(
            card, text="EXTRACT ISO CONTENTS", font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"),
            command=self.extract
        )
        self.btn_ext.pack(fill="x", padx=20, pady=20)

        self.prog = ctk.CTkProgressBar(card, progress_color=cfg.get_color("highlight"))
        self.prog.pack(fill="x", padx=20, pady=(0, 20))
        self.prog.set(0)

    def browse_src(self):
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso")])
        if f:
            self.ent_src.delete(0, 'end')
            self.ent_src.insert(0, f)

    def browse_dst(self):
        p = filedialog.askdirectory()
        if p:
            self.ent_dst.delete(0, 'end')
            self.ent_dst.insert(0, p)

    def extract(self):
        s, d = self.ent_src.get(), self.ent_dst.get()
        if not s or not d: return
        self.btn_ext.configure(state="disabled")
        RealIsoTool.extract(
            s, d,
            lambda v: self.app.after(0, lambda: self.prog.set(v)),
            lambda succ: self.app.after(0, lambda: [self.btn_ext.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), "Extraction finished!")]),
            lambda e: self.app.after(0, lambda: [self.btn_ext.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("error"), e)])
        )

class USBPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=t("tab_usb"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        self.list_box = ctk.CTkScrollableFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        self.list_box.grid(row=1, column=0, sticky="nsew")

    def refresh(self):
        for w in self.list_box.winfo_children(): w.destroy()
        drives = UsbDetector.get_removable_drives()
        if not drives:
            ctk.CTkLabel(self.list_box, text=t("burn_no_drives"), text_color=cfg.get_color("text_muted")).pack(pady=40)
            return
        for d in drives:
            card = HoverCard(self.list_box, height=65, corner_radius=cfg.get_radius("chip"), fg_color=cfg.get_color("bg_main"))
            card.pack(fill="x", pady=4, padx=4); card.pack_propagate(False)
            ctk.CTkLabel(card, text=f"{d['mountpoint']} [{d['fstype']}]", font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(side="left", padx=15)
            ctk.CTkLabel(card, text=f"{d['used']} / {d['total']} ({d['free']} free)", font=("Consolas", 10), text_color=cfg.get_color("text_muted")).pack(side="left", padx=10)
            ctk.CTkButton(card, text=t("inst_btn"), height=28, corner_radius=cfg.get_radius("button"), fg_color=cfg.get_color("accent"), command=lambda: self.app.show("single_install")).pack(side="right", padx=15)
            card.bind_children(card)

class IsoPatcherPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=t("tab_patcher"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))

        card = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text=t("patch_iso"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        f1 = ctk.CTkFrame(card, fg_color="transparent"); f1.pack(fill="x", padx=20)
        self.ent_iso = ctk.CTkEntry(f1, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry")); self.ent_iso.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f1, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=lambda: self.browse(self.ent_iso, [(t("iso_files"), "*.iso")])).pack(side="left", padx=10)

        ctk.CTkLabel(card, text=t("patch_file"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        f2 = ctk.CTkFrame(card, fg_color="transparent"); f2.pack(fill="x", padx=20)
        self.ent_patch = ctk.CTkEntry(f2, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry")); self.ent_patch.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f2, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=lambda: self.browse(self.ent_patch, [("Patches", "*.ips")])).pack(side="left", padx=10)

        ctk.CTkLabel(card, text=t("patch_out"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        f3 = ctk.CTkFrame(card, fg_color="transparent"); f3.pack(fill="x", padx=20)
        self.ent_out = ctk.CTkEntry(f3, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry")); self.ent_out.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f3, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=lambda: self.browse(self.ent_out, [(t("iso_files"), "*.iso")], save=True)).pack(side="left", padx=10)

        self.chk_region = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(card, text=t("patch_reg"), font=("Segoe UI", 11), variable=self.chk_region).pack(anchor="w", padx=20, pady=15)

        self.btn = ctk.CTkButton(card, text=t("patch_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"), command=self.apply_patch)
        self.btn.pack(pady=20, padx=20, fill="x")

        self.prog = ctk.CTkProgressBar(card, progress_color=cfg.get_color("highlight")); self.prog.pack(fill="x", padx=20, pady=(0, 20)); self.prog.set(0)

    def browse(self, entry, ftypes, save=False):
        f = filedialog.asksaveasfilename(filetypes=ftypes) if save else filedialog.askopenfilename(filetypes=ftypes)
        if f:
            entry.delete(0, 'end'); entry.insert(0, f)

    def apply_patch(self):
        self.btn.configure(state="disabled")
        TranslationPatcher.patch_iso(
            self.ent_iso.get().strip(), self.ent_out.get().strip(), self.ent_patch.get().strip(), self.chk_region.get(),
            lambda v: self.app.after(0, lambda: self.prog.set(v)),
            lambda s: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), t("patch_success"))]),
            lambda e: self.app.after(0, lambda: [self.btn.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("error"), e)])
        )

class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(self, text=t("tab_set"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        frm_left = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        frm_left.grid(row=1, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(frm_left, text=t("set_lang"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=15, pady=(15, 5))

        LANG_MAP = {
            "PT_BR": "Português (Brasil) [PT_BR]",
            "PT": "Português (Portugal) [PT]",
            "EN": "English [EN]",
            "ES": "Español [ES]",
            "RU": "Русский [RU]",
            "JA": "日本語 [JA]"
        }
        INV_LANG_MAP = {v: k for k, v in LANG_MAP.items()}

        cur_lang_code = cfg.data.get("language", "PT_BR")
        self.lang_var = ctk.StringVar(value=LANG_MAP.get(cur_lang_code, LANG_MAP["PT_BR"]))

        def on_lang_change(val):
            code = INV_LANG_MAP.get(val, "PT_BR")
            cfg.data["language"] = code
            cfg.save()
            self.app.after(50, self.app.refresh_all_ui)

        ctk.CTkOptionMenu(
            frm_left, variable=self.lang_var, values=list(LANG_MAP.values()), height=30,
            command=on_lang_change, corner_radius=cfg.get_radius("entry")
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(frm_left, text=t("set_theme"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=15, pady=(10, 5))
        self.theme_var = ctk.StringVar(value=cfg.data.get("theme", "Dark"))
        ctk.CTkOptionMenu(
            frm_left, variable=self.theme_var, values=list(THEMES.keys()), height=30,
            command=lambda c: [cfg.data.update({"theme": c}), cfg.save(), self.app.after(50, self.app.refresh_all_ui)],
            corner_radius=cfg.get_radius("entry")
        ).pack(anchor="w", padx=15, pady=(0, 15))

        ctk.CTkLabel(frm_left, text=t("set_beh"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("accent")).pack(anchor="w", padx=15, pady=(5, 5))
        self.snd_var = ctk.BooleanVar(value=cfg.data.get("sound_enabled", True))
        self.bgm_var = ctk.BooleanVar(value=cfg.data.get("bgm_enabled", True))
        self.anim_var = ctk.BooleanVar(value=cfg.data.get("animations", True))
        self.laptop_var = ctk.BooleanVar(value=cfg.data.get("laptop_mode", False))

        def sv():
            cfg.data.update({
                "sound_enabled": self.snd_var.get(),
                "bgm_enabled": self.bgm_var.get(),
                "animations": self.anim_var.get(),
                "laptop_mode": self.laptop_var.get()
            })
            cfg.save()
            sound_fx.enabled = self.snd_var.get()
            sound_fx.update_bgm(self.bgm_var.get())

        ctk.CTkSwitch(frm_left, text=t("set_snd"), font=("Segoe UI", 11), variable=self.snd_var, command=sv).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkSwitch(frm_left, text=t("set_bgm"), font=("Segoe UI", 11), variable=self.bgm_var, command=sv).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkSwitch(frm_left, text=t("set_anim"), font=("Segoe UI", 11), variable=self.anim_var, command=sv).pack(anchor="w", padx=15, pady=(0, 10))
        ctk.CTkSwitch(
            frm_left, text=t("set_laptop"), font=("Segoe UI", 11, "bold"),
            text_color=cfg.get_color("highlight"), variable=self.laptop_var,
            command=lambda: [sv(), self.app.after(50, self.app.refresh_all_ui)]
        ).pack(anchor="w", padx=15, pady=(0, 15))

        frm_right = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        frm_right.grid(row=1, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(frm_right, text=t("dev_tools"), font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("warning")).pack(anchor="w", padx=15, pady=(15, 10))
        r = cfg.get_radius("button")

        ctk.CTkButton(
            frm_right, text=t("roadmap_btn"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_color("accent_hover"),
            height=36, corner_radius=r, command=lambda: ChangelogTimelineModal(self.app)
        ).pack(fill="x", padx=15, pady=(0, 12))

        # Restaura o link original do formulário de avaliação do PS2Manager
        ctk.CTkButton(
            frm_right, text=t("set_rate"), font=("Segoe UI", 11, "bold"),
            fg_color="#D97706", hover_color="#B45309", height=36, corner_radius=r,
            command=lambda: webbrowser.open("https://docs.google.com/forms/d/e/1FAIpQLSdV8WZMSQGHtGOnhsdI1mxxAwzIdifNLrkBN1adfvRR9vDkYQ/viewform?usp=publish-editor")
        ).pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkButton(
            frm_right, text=t("set_log"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("card_hover"), height=36, corner_radius=r,
            command=self.export_log
        ).pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkButton(
            frm_right, text=t("ver_btn"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("card_hover"), height=36, corner_radius=r,
            command=lambda: VersionRollbackModal(self.app)
        ).pack(fill="x", padx=15, pady=(0, 12))

    def export_log(self):
        p = sys_logger.export()
        if p:
            sound_fx.play_success()
            messagebox.showinfo(t("success"), f"{t('set_log')}:\n{p}")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x680")
        self.minsize(850, 580)
        self.configure(fg_color=cfg.get_color("bg_main"))

        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.library = LibraryManager()
        self.cur = None
        self.last_usb = -1
        self.active_transfers = 0
        self.is_animating = False
        self._last_click_time = 0

        self.bind_all("<Button-1>", self._on_global_click)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        if not cfg.data.get("setup_done", False):
            self.setup_frame = SetupFrame(self, self)
        else:
            self.build_main_ui()
            self.after(500, self.check_interrupted_transfer)

    def _on_global_click(self, event):
        now = time.time()
        if now - self._last_click_time < 0.15:
            return "break"
        self._last_click_time = now
        w = event.widget
        is_sidebar = False
        while w:
            if hasattr(self, 'sb') and self.sb and str(w) == str(self.sb):
                is_sidebar = True
                break
            w = w.master
        if not is_sidebar:
            sound_fx.play_click()

    def build_main_ui(self):
        old_cur_key = next((k for k, v in getattr(self, 'pages', {}).items() if v == self.cur), None)
        if hasattr(self, 'pages'):
            for p in self.pages.values():
                p.destroy()
        if hasattr(self, 'setup_frame') and self.setup_frame:
            self.setup_frame.destroy()
            self.setup_frame = None
        if hasattr(self, 'sb'):
            self.sb.destroy()
        if hasattr(self, 'content'):
            self.content.destroy()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sb = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=cfg.get_color("bg_sidebar"))
        self.sb.grid(row=0, column=0, sticky="nsew")
        self.sb.grid_rowconfigure(25, weight=1)

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.btns, self.nav_main, self.nav_more, self.cur = {}, [], [], None

        brand = ctk.CTkFrame(self.sb, fg_color="transparent")
        brand.grid(row=0, column=0, pady=(18, 12), padx=16, sticky="w")
        ctk.CTkLabel(brand, text="PS2", font=("Segoe UI Black", 22), text_color=cfg.get_color("accent")).pack(side="left")
        ctk.CTkLabel(brand, text="MANAGER", font=("Segoe UI Black", 14), text_color=cfg.get_color("text_main")).pack(side="left", padx=(4, 6))
        ctk.CTkLabel(brand, text=APP_VERSION, font=("Consolas", 10, "bold"), text_color=cfg.get_color("highlight")).pack(side="left")

        def nav(row, k, txt, group="main"):
            b = ctk.CTkButton(
                self.sb, text=txt, font=("Segoe UI", 11, "bold"),
                fg_color="transparent", text_color=cfg.get_color("text_muted"),
                anchor="w", height=34, corner_radius=cfg.get_radius("button"),
                hover_color=cfg.get_color("card_hover"), command=lambda: self.show(k)
            )
            if group == "main":
                b.grid(row=row, column=0, padx=12, pady=2, sticky="ew")
                self.nav_main.append(k)
            else:
                self.nav_more.append(k)
            self.btns[k] = b

        nav(1, "dash", t("tab_dash"))
        nav(2, "games", t("tab_lib"))
        nav(3, "single_install", t("tab_install"))
        nav(4, "batch", t("tab_batch"))
        nav(5, "burn", t("tab_burn"))
        nav(6, "test", t("tab_emu"))
        nav(7, "usb", t("tab_usb"))
        nav(8, "apps", t("tab_apps"))

        self.btn_enter_more = ctk.CTkButton(
            self.sb, text=t("tab_more"), font=("Segoe UI", 11, "bold"),
            fg_color="transparent", text_color=cfg.get_color("highlight"),
            anchor="w", height=34, corner_radius=cfg.get_radius("button"),
            hover_color=cfg.get_color("card_hover"), command=self.enter_more_tools
        )
        self.btn_enter_more.grid(row=9, column=0, padx=12, pady=4, sticky="ew")

        self.btn_back_more = ctk.CTkButton(
            self.sb, text=t("btn_back"), font=("Segoe UI", 11, "bold"),
            fg_color=cfg.get_color("card_base"), hover_color=cfg.get_color("card_hover"),
            text_color=cfg.get_color("text_main"), anchor="w", height=38,
            corner_radius=cfg.get_radius("button"), command=self.exit_more_tools
        )

        nav(2, "iso", t("tab_iso"), group="more")
        nav(3, "patcher", t("tab_patcher"), group="more")
        nav(4, "util", t("tab_util"), group="more")
        nav(5, "rip", t("tab_rip"), group="more")
        nav(6, "disc", t("tab_disc"), group="more")
        nav(7, "clone", t("sub_clone")[2:], group="more")
        nav(8, "migrate", t("tab_mig"), group="more")
        nav(9, "cheats", t("tab_cht"), group="more")
        nav(10, "apa", t("apa_title"), group="more")
        nav(11, "art", t("art_title"), group="more")

        self.btns["settings"] = ctk.CTkButton(
            self.sb, text=t("tab_set"), font=("Segoe UI", 11, "bold"),
            fg_color="transparent", text_color=cfg.get_color("text_muted"),
            anchor="w", height=34, corner_radius=cfg.get_radius("button"),
            hover_color=cfg.get_color("card_hover"), command=lambda: self.show("settings")
        )
        self.btns["settings"].grid(row=26, column=0, padx=12, pady=(0, 16), sticky="sew")

        self.pages = {
            "dash": DashboardPage(self.content, self),
            "games": GamesPage(self.content, self),
            "single_install": SingleInstallPage(self.content, self),
            "batch": BatchInstallPage(self.content, self),
            "burn": DvdBurnerPage(self.content, self),
            "test": EmulatorTestPage(self.content, self),
            "usb": USBPage(self.content, self),
            "apps": AppsManagerPage(self.content, self),
            "iso": IsoExtractorPage(self.content, self),
            "patcher": IsoPatcherPage(self.content, self),
            "util": self._build_util_page(),
            "rip": self._build_rip_page(),
            "disc": self._build_disc_page(),
            "clone": self._build_clone_page(),
            "migrate": self._build_migrate_page(),
            "cheats": CheatManagerPage(self.content, self),
            "apa": self._build_apa_page(),
            "art": self._build_art_page(),
            "settings": SettingsPage(self.content, self)
        }

        if old_cur_key in self.nav_more:
            self.enter_more_tools()
            self.show(old_cur_key)
        else:
            self.show(old_cur_key if old_cur_key else "dash")
        self.monitor_usb()

    def _build_util_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frm, text=t("tab_util"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        card = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(card, text=t("util_iso"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        f_s = ctk.CTkFrame(card, fg_color="transparent"); f_s.pack(fill="x", padx=20)
        e_s = ctk.CTkEntry(f_s, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry")); e_s.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_s, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=lambda: [e_s.delete(0, 'end'), e_s.insert(0, filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso")]) or "")]).pack(side="left", padx=10)
        ctk.CTkLabel(card, text=t("util_dst"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        f_d = ctk.CTkFrame(card, fg_color="transparent"); f_d.pack(fill="x", padx=20)
        e_d = ctk.CTkEntry(f_d, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry")); e_d.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_d, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=lambda: [e_d.delete(0, 'end'), e_d.insert(0, filedialog.askdirectory() or "")]).pack(side="left", padx=10)
        ctk.CTkLabel(card, text=t("util_name"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        e_n = ctk.CTkEntry(card, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry")); e_n.pack(fill="x", padx=20)
        prog = ctk.CTkProgressBar(card, progress_color=cfg.get_color("accent")); prog.pack(fill="x", padx=20, pady=(20, 10)); prog.set(0)
        btn = ctk.CTkButton(card, text=t("util_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"))
        btn.pack(pady=20, padx=20, fill="x")
        def go():
            if not e_s.get() or not e_d.get(): return
            btn.configure(state="disabled")
            USBUtilWorker.split_and_generate(
                e_s.get(), e_d.get(), e_n.get() or os.path.splitext(os.path.basename(e_s.get()))[0][:32],
                lambda v: self.after(0, lambda: prog.set(v)),
                lambda s: self.after(0, lambda: [btn.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), t("util_succ"))]),
                lambda e: self.after(0, lambda: [btn.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("error"), str(e))])
            )
        btn.configure(command=go)
        return frm

    def _build_rip_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frm, text=t("tab_rip"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        card = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(card, text=t("disc_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        drvs = PhysicalDriveRipper.get_optical_drives() or [t("burn_no_drives")]
        cmb_d = ctk.CTkComboBox(card, values=drvs, height=32, corner_radius=cfg.get_radius("entry"))
        cmb_d.pack(fill="x", padx=20)
        ctk.CTkLabel(card, text=t("rip_out"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        f_o = ctk.CTkFrame(card, fg_color="transparent"); f_o.pack(fill="x", padx=20)
        e_o = ctk.CTkEntry(f_o, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry")); e_o.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_o, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=lambda: [e_o.delete(0, 'end'), e_o.insert(0, filedialog.asksaveasfilename(filetypes=[(t("iso_files"), "*.iso")]) or "")]).pack(side="left", padx=10)
        prog = ctk.CTkProgressBar(card, progress_color=cfg.get_color("accent")); prog.pack(fill="x", padx=20, pady=(20, 10)); prog.set(0)
        btn = ctk.CTkButton(card, text=t("rip_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"))
        btn.pack(pady=20, padx=20, fill="x")
        def go():
            if cmb_d.get() == t("burn_no_drives") or not e_o.get(): return
            btn.configure(state="disabled")
            PhysicalDriveRipper.rip_to_iso(
                cmb_d.get(), e_o.get(),
                lambda v: self.after(0, lambda: prog.set(v)),
                lambda s: self.after(0, lambda: [btn.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), t("rip_done"))]),
                lambda e: self.after(0, lambda: [btn.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("error"), str(e))])
            )
        btn.configure(command=go)
        return frm

    def _build_disc_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frm, text=t("tab_disc"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        card = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")
        drvs = PhysicalDriveRipper.get_optical_drives() or [t("disc_none")]
        cmb = ctk.CTkComboBox(card, values=drvs, height=32, corner_radius=cfg.get_radius("entry"))
        cmb.pack(fill="x", padx=20, pady=(20, 10))
        txt = ctk.CTkTextbox(card, font=("Consolas", 12), height=180, fg_color=cfg.get_color("bg_main"), corner_radius=cfg.get_radius("entry"))
        txt.pack(fill="x", padx=20, pady=10)
        btn = ctk.CTkButton(card, text=t("disc_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"))
        btn.pack(pady=20, padx=20, fill="x")
        def go():
            if cmb.get() == t("disc_none"): return
            txt.delete("1.0", "end"); txt.insert("end", "Analyzing optical disc sectors...\n")
            def r():
                info = PhysicalDriveRipper.analyze_disc(cmb.get())
                out = f"--- OPTICAL DISC BINARY ANALYSIS ---\nDrive:  {cmb.get()}\nStatus: {info['status']}\nVolume: {info['size_str']}\nID:     {info['game_id']}\nRegion: {info['region']}\n"
                self.after(0, lambda: [txt.delete("1.0", "end"), txt.insert("end", out), sound_fx.play_success()])
            threading.Thread(target=r, daemon=True).start()
        btn.configure(command=go)
        return frm

    def _build_clone_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frm, text=t("sub_clone")[2:], font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        card = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(card, text=t("clone_src"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        d_vals = [f"{d['device']} [{d['fstype']}]" for d in DriveManager.get_drives()] or ["None"]
        cmb_s = ctk.CTkComboBox(card, values=d_vals, height=32, corner_radius=cfg.get_radius("entry")); cmb_s.pack(fill="x", padx=20)
        ctk.CTkLabel(card, text=t("clone_dst"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        cmb_d = ctk.CTkComboBox(card, values=d_vals, height=32, corner_radius=cfg.get_radius("entry")); cmb_d.pack(fill="x", padx=20)
        chk_f = ctk.CTkCheckBox(card, text=t("clone_fmt_dst"), font=("Segoe UI", 11)); chk_f.pack(anchor="w", padx=20, pady=15)
        log_box = ctk.CTkTextbox(card, font=("Consolas", 10), height=90, fg_color=cfg.get_color("bg_main")); log_box.pack(fill="x", padx=20, pady=5)
        btn = ctk.CTkButton(card, text=t("clone_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=cfg.get_radius("button"))
        btn.pack(pady=20, padx=20, fill="x")
        def run_c():
            s_val, d_val = cmb_s.get().split(" ")[0], cmb_d.get().split(" ")[0]
            if s_val == "None" or d_val == "None" or s_val == d_val: return
            drives = DriveManager.get_drives()
            s_d, d_d = next((d for d in drives if d['device'] == s_val), None), next((d for d in drives if d['device'] == d_val), None)
            w = CloneWorker(s_d, d_d, chk_f.get(), False, {'log': lambda m: self.after(0, lambda: log_box.insert("end", m + "\n")), 'prog_total': lambda v: None})
            threading.Thread(target=w.run, daemon=True).start()
        btn.configure(command=run_c)
        return frm

    def _build_migrate_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frm, text=t("tab_mig"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        card = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(card, text=t("mig_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        d_vals = [f"{d['device']} [{d['fstype']}]" for d in DriveManager.get_drives()] or ["None"]
        cmb_d = ctk.CTkComboBox(card, values=d_vals, height=32, corner_radius=cfg.get_radius("entry")); cmb_d.pack(fill="x", padx=20)
        ctk.CTkLabel(card, text=t("mig_fs"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        cmb_f = ctk.CTkComboBox(card, values=["exFAT", "FAT32"], height=32, corner_radius=cfg.get_radius("entry")); cmb_f.pack(fill="x", padx=20)
        log_box = ctk.CTkTextbox(card, font=("Consolas", 10), height=100, fg_color=cfg.get_color("bg_main")); log_box.pack(fill="x", padx=20, pady=15)
        btn = ctk.CTkButton(card, text=t("mig_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("danger"), height=40, corner_radius=cfg.get_radius("button"))
        btn.pack(pady=20, padx=20, fill="x")
        def go():
            dev = cmb_d.get().split(" ")[0]
            drives = DriveManager.get_drives()
            d = next((x for x in drives if x['device'] == dev), None)
            if not d or not messagebox.askyesno(t("confirm"), t("mig_conf")): return
            w = MigrationWorker(d, cmb_f.get(), {'log': lambda m: self.after(0, lambda: log_box.insert("end", m + "\n")), 'prog_total': lambda v: None, 'prog_step': lambda v: None, 'done': lambda s: None})
            threading.Thread(target=w.run, daemon=True).start()
        btn.configure(command=go)
        return frm

    def _build_apa_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1); frm.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(frm, text=t("apa_title"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 15))
        top = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(top, text=t("apa_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
        d_vals = APAManager.list_physical_drives() or ["PhysicalDrive1", "PhysicalDrive2"]
        cmb_p = ctk.CTkComboBox(top, values=d_vals, height=32, corner_radius=cfg.get_radius("entry")); cmb_p.pack(fill="x", padx=15, pady=5)
        bar = ctk.CTkFrame(top, fg_color="transparent"); bar.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(bar, text=t("apa_btn_open"), width=120, height=32, corner_radius=cfg.get_radius("button"), command=lambda: open_img()).pack(side="left", padx=4)
        ctk.CTkButton(bar, text=t("apa_btn_raw"), width=180, height=32, corner_radius=cfg.get_radius("button"), command=lambda: dump_raw()).pack(side="left", padx=4)
        ctk.CTkButton(bar, text=t("apa_btn_ext"), width=140, height=32, fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"), command=lambda: ext_games()).pack(side="left", padx=4)
        list_apa = ctk.CTkScrollableFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        list_apa.grid(row=2, column=0, sticky="nsew")
        loaded_parts = []
        def open_img():
            f = filedialog.askopenfilename(filetypes=[("Disk Image", "*.img *.bin *.raw")])
            if f:
                parts = APAManager.read_apa_header(f)
                loaded_parts.clear(); loaded_parts.extend(parts)
                render_parts(parts)
        def dump_raw():
            dst = filedialog.asksaveasfilename(defaultextension=".img", filetypes=[("Raw Image", "*.img")])
            if dst:
                APAManager.dump_raw_drive(cmb_p.get(), dst, lambda m: NotificationPopup(self, m, "info"))
        def ext_games():
            dst = filedialog.askdirectory()
            if dst and loaded_parts:
                APAManager.extract_contents(cmb_p.get(), loaded_parts, dst, lambda m: NotificationPopup(self, m, "success"))
        def render_parts(parts):
            for w in list_apa.winfo_children(): w.destroy()
            for p in parts:
                r = ctk.CTkFrame(list_apa, fg_color=cfg.get_color("bg_main"), height=36, corner_radius=6)
                r.pack(fill="x", pady=2, padx=4); r.pack_propagate(False)
                ctk.CTkLabel(r, text=p['name'], font=("Consolas", 11, "bold"), text_color=cfg.get_color("accent")).pack(side="left", padx=10)
                ctk.CTkLabel(r, text=f"Start Sector: {p['start']}", font=("Consolas", 10), text_color=cfg.get_color("text_muted")).pack(side="right", padx=15)
        return frm

    def _build_art_page(self):
        frm = ctk.CTkFrame(self.content, fg_color="transparent")
        frm.grid_columnconfigure(0, weight=1); frm.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(frm, text=t("art_title"), font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        top = ctk.CTkFrame(frm, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        top.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(top, text=t("art_desc"), font=("Segoe UI", 12), text_color=cfg.get_color("text_muted")).pack(anchor="w", padx=20, pady=(15, 10))
        d_vals = [d['mountpoint'] for d in DriveManager.get_drives()] or ["None"]
        f_d = ctk.CTkFrame(top, fg_color="transparent"); f_d.pack(fill="x", padx=20, pady=5)
        cmb_d = ctk.CTkComboBox(f_d, values=d_vals, height=32, corner_radius=cfg.get_radius("entry")); cmb_d.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_d, text=t("btn_browse"), width=90, corner_radius=cfg.get_radius("button"), command=lambda: [cmb_d.set(filedialog.askdirectory() or cmb_d.get())]).pack(side="left", padx=10)
        prog = ctk.CTkProgressBar(top, progress_color=cfg.get_color("accent")); prog.pack(fill="x", padx=20, pady=15); prog.set(0)
        log_box = ctk.CTkTextbox(frm, font=("Consolas", 11), fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=1, border_color=cfg.get_color("border"))
        log_box.grid(row=2, column=0, sticky="nsew", pady=10)
        btn_bar = ctk.CTkFrame(top, fg_color="transparent"); btn_bar.pack(fill="x", padx=20, pady=(0, 15))
        det_ids = []
        def scan_art():
            mp = cmb_d.get()
            if not mp or mp == "None": return
            ids = ArtScraperWorker.scan_for_ids(mp)
            det_ids.clear(); det_ids.extend(ids)
            log_box.insert("end", f"Identified {len(ids)} games on storage drive.\n")
            if ids: btn_dl.configure(state="normal")
        def dl_art():
            btn_dl.configure(state="disabled")
            ArtScraperWorker.download_art(
                cmb_d.get(), det_ids,
                lambda v: self.after(0, lambda: prog.set(v)),
                lambda s: self.after(0, lambda: [btn_dl.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), t("art_done"))]),
                lambda e: self.after(0, lambda: [btn_dl.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("error"), e)]),
                lambda m: self.after(0, lambda: [log_box.insert("end", m + "\n"), log_box.see("end")])
            )
        ctk.CTkButton(btn_bar, text=t("art_scan"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("accent"), height=36, corner_radius=cfg.get_radius("button"), command=scan_art).pack(side="left", expand=True, padx=4)
        btn_dl = ctk.CTkButton(btn_bar, text=t("art_dl"), font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("success"), height=36, corner_radius=cfg.get_radius("button"), state="disabled", command=dl_art)
        btn_dl.pack(side="left", expand=True, padx=4)
        return frm

    def enter_more_tools(self):
        for k in self.nav_main:
            self.btns[k].grid_remove()
        self.btn_enter_more.grid_remove()
        self.btn_back_more.grid(row=1, column=0, padx=12, pady=(10, 15), sticky="ew")
        for i, k in enumerate(self.nav_more):
            self.btns[k].grid(row=2 + i, column=0, padx=12, pady=2, sticky="ew")
        self.show(self.nav_more[0])

    def exit_more_tools(self):
        self.btn_back_more.grid_remove()
        for k in self.nav_more:
            self.btns[k].grid_remove()
        for k in self.nav_main:
            self.btns[k].grid()
        self.btn_enter_more.grid()
        self.show("dash")

    def show(self, k):
        if self.cur == self.pages.get(k):
            return
        sound_fx.play_tab()
        self.library.sync_drives()
        for b in self.btns.values():
            b.configure(fg_color="transparent", text_color=cfg.get_color("text_muted"))
        if k in self.btns:
            self.btns[k].configure(fg_color=cfg.get_color("card_base"), text_color=cfg.get_color("text_main"))
        if self.cur:
            self.cur.place_forget()
        self.cur = self.pages.get(k)
        if self.cur:
            self.cur.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
            getattr(self.cur, "refresh", lambda: None)()

    def refresh_all_ui(self):
        cfg.apply_theme()
        self.configure(fg_color=cfg.get_color("bg_main"))
        if hasattr(self, 'setup_frame') and self.setup_frame:
            self.setup_frame.configure(fg_color=cfg.get_color("bg_main"))
        else:
            self.build_main_ui()

    def on_closing(self):
        # Intercepta Alt+F4 ou botão fechar se houver processos/cópias ativas
        if TransferLockManager.is_busy() or self.active_transfers > 0:
            sound_fx.play_error()
            messagebox.showwarning(t("warning"), t("msg_corruption_warn"))
            return
        self.destroy()
        sys.exit(0)

    def check_interrupted_transfer(self):
        lock_file = os.path.join(APP_DATA_DIR, "active_transfer.lock")
        if os.path.exists(lock_file):
            sound_fx.play_warning()
            if messagebox.askyesno(t("recovery_title"), t("recovery_msg")):
                try: os.remove(lock_file)
                except Exception: pass
                self.show("batch")
            else:
                try: os.remove(lock_file)
                except Exception: pass

    def refresh_all(self):
        for p in self.pages.values():
            getattr(p, "refresh", lambda: None)()

    def monitor_usb(self):
        try:
            d = UsbDetector.get_removable_drives()
            c = len(d)
            if self.last_usb != -1 and c != self.last_usb:
                sound_fx.play_usb()
                self.library.sync_drives()
                self.refresh_all()
            self.last_usb = c
        except Exception:
            pass
        self.after(3000, self.monitor_usb)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
