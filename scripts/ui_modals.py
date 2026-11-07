from __future__ import annotations

import os
import sys
import json
import time
import ctypes
import shutil
import threading
import webbrowser
import subprocess
import urllib.request
import tkinter as tk
from ctypes import wintypes
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    import requests as _requests
except Exception:
    _requests = None

try:
    from PIL import (
        Image as _PILImage, ImageDraw as _PILDraw,
        ImageEnhance as _PILEnhance, ImageFilter as _PILFilter,
        ImageFont as _PILFont, ImageTk as _PILImageTk
    )
    _PIL_MODAL_OK = True
    _RESAMPLE_BILINEAR = getattr(getattr(_PILImage, "Resampling", None), "BILINEAR", getattr(_PILImage, "BILINEAR", 2))
    _RESAMPLE_LANCZOS = getattr(getattr(_PILImage, "Resampling", None), "LANCZOS", getattr(_PILImage, "LANCZOS", getattr(_PILImage, "ANTIALIAS", 1)))
    _RESAMPLE_NEAREST = getattr(getattr(_PILImage, "Resampling", None), "NEAREST", getattr(_PILImage, "NEAREST", 0))
except Exception:
    _PIL_MODAL_OK = False
    _RESAMPLE_BILINEAR = 2
    _RESAMPLE_LANCZOS = 1
    _RESAMPLE_NEAREST = 0

from scripts.core_backend import (
    APP_VERSION, BASE_DIR, LANGS, cfg, db, t, sound_fx
)
from scripts.tool_workers import (
    DriveManager, UsbDetector, ArtScraperWorker, PCSX2Integration,
    DvdBurnerWorker, AppManager
)
from scripts.ui_pages import apply_window_icon, PageHeader


class SetupFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=cfg.get_color("bg_main"))
        self.app = app
        self.pack(fill="both", expand=True)
        self.content = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
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
            self.content, text=f"PS2 MANAGER {APP_VERSION}",
            font=("Segoe UI Black", 32), text_color=cfg.get_color("accent")
        ).pack(padx=50, pady=(35, 6))
        ctk.CTkLabel(
            self.content, text=t("setup_welcome"),
            font=("Segoe UI", 15), text_color=cfg.get_color("text_muted")
        ).pack(padx=50, pady=(0, 30))
        ctk.CTkButton(
            self.content, text=t("setup_continue"),
            font=("Segoe UI", 13, "bold"), height=44, width=240,
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"),
            command=lambda: [sound_fx.play_click(), self.show_step_1()]
        ).pack(padx=50, pady=(0, 35))

    def show_step_1(self):
        self.clear()
        ctk.CTkLabel(
            self.content, text=t("setup_lang"),
            font=("Segoe UI Black", 18), text_color=cfg.get_color("text_main")
        ).pack(padx=50, pady=(28, 18))

        def set_lang(l):
            sound_fx.play_click()
            cfg.data["language"] = l
            cfg.save()
            self.show_step_2()

        r = cfg.get_radius("button")
        langs = [
            ("Português (Brasil) [PT_BR]", "PT_BR"),
            ("Português (Portugal) [PT]", "PT"),
            ("English [EN]", "EN"),
            ("Español [ES]", "ES"),
            ("Русский [RU]", "RU"),
            ("日本語 [JA]", "JA")
        ]
        for label, code in langs:
            ctk.CTkButton(
                self.content, text=label, height=38, width=300,
                corner_radius=r, fg_color=cfg.get_color("bg_main"),
                text_color=cfg.get_color("text_main"),
                hover_color=cfg.get_hover("accent", "bg_main"),
                command=lambda c=code: set_lang(c)
            ).pack(padx=45, pady=4)
        ctk.CTkFrame(self.content, height=20, fg_color="transparent").pack()

    def show_step_2(self):
        self.clear()
        ctk.CTkLabel(
            self.content, text=t("setup_model"),
            font=("Segoe UI Black", 17), text_color=cfg.get_color("text_main")
        ).pack(padx=50, pady=(28, 10))
        models = ["SCPH-10000", "SCPH-3000x", "SCPH-5000x", "SCPH-7000x", "SCPH-9000x", "PSX DESR"]
        self.cmb_model = ctk.CTkComboBox(
            self.content, values=models, font=("Segoe UI", 13),
            height=38, width=260, corner_radius=cfg.get_radius("entry")
        )
        self.cmb_model.set("SCPH-9000x")
        self.cmb_model.pack(pady=6)

        ctk.CTkLabel(
            self.content, text=t("setup_type"),
            font=("Segoe UI Black", 17), text_color=cfg.get_color("text_main")
        ).pack(padx=50, pady=(16, 10))
        self.cmb_type = ctk.CTkComboBox(
            self.content, values=["SLIM", "FAT"], font=("Segoe UI", 13),
            height=38, width=260, corner_radius=cfg.get_radius("entry")
        )
        self.cmb_type.set("SLIM")
        self.cmb_type.pack(pady=6)

        ctk.CTkButton(
            self.content, text=t("setup_continue"),
            font=("Segoe UI", 13, "bold"), height=42, width=240,
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=cfg.get_radius("button"),
            command=lambda: [sound_fx.play_click(), self.show_step_3()]
        ).pack(padx=50, pady=(24, 30))

    def show_step_3(self):
        cfg.data["ps2_model"] = self.cmb_model.get()
        cfg.data["ps2_type"] = self.cmb_type.get()
        cfg.data["setup_done"] = True
        cfg.save()
        self.clear()
        ctk.CTkLabel(
            self.content, text=t("setup_finish"),
            font=("Segoe UI Black", 19), text_color=cfg.get_color("highlight")
        ).pack(padx=50, pady=(35, 15))
        ctk.CTkButton(
            self.content, text="START PS2 MANAGER",
            font=("Segoe UI", 14, "bold"), height=46, width=250,
            fg_color=cfg.get_color("success"), corner_radius=cfg.get_radius("button"),
            command=self.finish
        ).pack(padx=50, pady=(10, 35))

    def finish(self):
        sound_fx.play_success()
        self.destroy()
        self.app.setup_frame = None
        self.app.build_main_ui()
        # Aguarda alguns segundos apos concluir a introducao para exibir qualquer aviso remoto
        if hasattr(self.app, "check_remote_news"):
            self.app.after(3500, self.app.check_remote_news)


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def _capture_dimmed_client_image(app_win, brightness=0.36):
    """Captura a area interna atual do PS2Manager e escurece suavemente para criar o fundo meio preto."""
    if not _PIL_MODAL_OK or cfg.is_potato() or sys.platform != "win32":
        return None
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    g32 = ctypes.WinDLL("gdi32", use_last_error=True)

    u32.GetParent.argtypes = [wintypes.HWND]
    u32.GetParent.restype = wintypes.HWND
    u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u32.GetClientRect.restype = wintypes.BOOL
    u32.GetDC.argtypes = [wintypes.HWND]
    u32.GetDC.restype = wintypes.HDC
    u32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    u32.ReleaseDC.restype = ctypes.c_int
    u32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    u32.PrintWindow.restype = wintypes.BOOL

    g32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    g32.CreateCompatibleDC.restype = wintypes.HDC
    g32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    g32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    g32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    g32.SelectObject.restype = wintypes.HGDIOBJ
    g32.BitBlt.argtypes = [
        wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD
    ]
    g32.BitBlt.restype = wintypes.BOOL
    g32.GetDIBits.argtypes = [
        wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
        ctypes.c_void_p, ctypes.POINTER(_BITMAPINFOHEADER), wintypes.UINT
    ]
    g32.GetDIBits.restype = ctypes.c_int
    g32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    g32.DeleteObject.restype = wintypes.BOOL
    g32.DeleteDC.argtypes = [wintypes.HDC]
    g32.DeleteDC.restype = wintypes.BOOL

    src_dc = mem_dc = bmp = old_obj = None
    hwnd = None
    try:
        app_win.update_idletasks()
        hwnd = wintypes.HWND(app_win.winfo_id())
        top_hwnd = u32.GetParent(hwnd) or hwnd
        rect = wintypes.RECT()
        if not u32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        w = int(rect.right - rect.left)
        h = int(rect.bottom - rect.top)
        if w < 200 or h < 200:
            return None

        src_dc = u32.GetDC(hwnd)
        if not src_dc:
            return None
        mem_dc = g32.CreateCompatibleDC(src_dc)
        bmp = g32.CreateCompatibleBitmap(src_dc, w, h)
        if not mem_dc or not bmp:
            return None
        old_obj = g32.SelectObject(mem_dc, bmp)

        ok = bool(u32.PrintWindow(top_hwnd, mem_dc, 3))
        if not ok:
            ok = bool(g32.BitBlt(mem_dc, 0, 0, w, h, src_dc, 0, 0, 0x00CC0020))
        if not ok:
            return None

        bmi = _BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # Top-down DIB
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        rows = g32.GetDIBits(mem_dc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
        if rows != h:
            return None
        raw = buf.raw
        if not any(raw[:4096:16]):
            return None

        img = _PILImage.frombuffer("RGBA", (w, h), raw, "raw", "BGRA", 0, 1).convert("RGB")
        img = img.filter(_PILFilter.GaussianBlur(radius=5.5))
        return _PILEnhance.Brightness(img).enhance(brightness)
    except Exception:
        return None
    finally:
        try:
            if mem_dc and old_obj:
                g32.SelectObject(mem_dc, old_obj)
            if bmp:
                g32.DeleteObject(bmp)
            if mem_dc:
                g32.DeleteDC(mem_dc)
            if hwnd and src_dc:
                u32.ReleaseDC(hwnd, src_dc)
        except Exception:
            pass


_MODAL_FONT_CACHE = {}


def _get_modal_font(px_size: int, weight: str = "semibold"):
    key = (weight, int(px_size))
    if key in _MODAL_FONT_CACHE:
        return _MODAL_FONT_CACHE[key]
    win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    candidates = {
        "bold": ("segoeuib.ttf", "seguisb.ttf", "arialbd.ttf"),
        "semibold": ("segoeuib.ttf", "seguisb.ttf", "segoeui.ttf", "arial.ttf"),
        "regular": ("segoeui.ttf", "seguisb.ttf", "arial.ttf"),
    }.get(weight, ("segoeui.ttf", "seguisb.ttf", "arial.ttf"))
    font_obj = None
    for fn in candidates:
        fp = os.path.join(win_fonts, fn)
        if os.path.exists(fp):
            try:
                font_obj = _PILFont.truetype(fp, int(px_size))
                break
            except Exception:
                continue
    if font_obj is None:
        font_obj = _PILFont.load_default()
    _MODAL_FONT_CACHE[key] = font_obj
    return font_obj


def _hex_rgba(hex_col: str, alpha: int = 255) -> tuple:
    h = hex_col.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def _wrap_styled_paragraphs(draw, paragraphs: list, max_w: float) -> list:
    """Quebra paragrafos com suporte a multiplos estilos/cores na mesma linha (ex: versao em verde)."""
    lines_out = []
    for runs in paragraphs:
        tokens = []
        for text_part, fill_rgba, fnt in runs:
            if not text_part:
                continue
            parts = text_part.split(" ")
            for idx, word in enumerate(parts):
                if idx > 0:
                    tokens.append((" ", fill_rgba, fnt))
                if word:
                    tokens.append((word, fill_rgba, fnt))
        if not tokens:
            lines_out.append([])
            continue

        cur_line = []
        cur_w = 0.0
        for tok_str, fill_rgba, fnt in tokens:
            if tok_str == " " and not cur_line:
                continue
            tw = float(draw.textlength(tok_str, font=fnt))
            if tok_str != " " and tw > max_w:
                if cur_line:
                    if cur_line[-1][0] == " ":
                        cur_line.pop()
                    lines_out.append(cur_line)
                    cur_line, cur_w = [], 0.0
                chunk = ""
                for ch in tok_str:
                    cw = float(draw.textlength(chunk + ch, font=fnt))
                    if chunk and cw > max_w:
                        lines_out.append([(chunk, fill_rgba, fnt, float(draw.textlength(chunk, font=fnt)))])
                        chunk = ch
                    else:
                        chunk += ch
                if chunk:
                    cw = float(draw.textlength(chunk, font=fnt))
                    cur_line = [(chunk, fill_rgba, fnt, cw)]
                    cur_w = cw
                continue

            if cur_line and tok_str != " " and (cur_w + tw) > max_w:
                if cur_line[-1][0] == " ":
                    cur_line.pop()
                lines_out.append(cur_line)
                cur_line = [(tok_str, fill_rgba, fnt, tw)]
                cur_w = tw
            else:
                cur_line.append((tok_str, fill_rgba, fnt, tw))
                cur_w += tw

        if cur_line:
            if cur_line[-1][0] == " ":
                cur_line.pop()
            if cur_line:
                lines_out.append(cur_line)
    return lines_out or [[]]


def _draw_centered_label(draw, cx: float, cy: float, text: str, font_obj, fill_rgba: tuple):
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw / 2.0 - bbox[0], cy - th / 2.0 - bbox[1]), text, font=font_obj, fill=fill_rgba)


def _render_unified_modal_frames(base_img, w: int, h: int, paragraphs_spec: list, upd_label: str = None):
    """Renderiza fundo fosco + janela cinza 2x anti-aliased + tipografia ClearType + botoes interativos num unico frame."""
    if not _PIL_MODAL_OK or w < 120 or h < 120:
        return None

    ss = 1 if cfg.is_potato() else 2
    scale = max(0.95, min(1.28, min(w / 1080.0, h / 720.0)))

    fnt_msg = _get_modal_font(round(16 * scale * ss), "semibold")
    fnt_bold = _get_modal_font(round(16 * scale * ss), "bold")
    fnt_btn = _get_modal_font(round(13.5 * scale * ss), "bold")

    dummy_img = _PILImage.new("RGBA", (16, 16), (0, 0, 0, 0))
    measure_draw = _PILDraw.Draw(dummy_img)

    styled_paras = []
    natural_max_w2 = 0.0
    for run_list in paragraphs_spec:
        p_runs = []
        p_w2 = 0.0
        for txt, hex_col, is_bold in run_list:
            fo = fnt_bold if is_bold else fnt_msg
            p_runs.append((txt, _hex_rgba(hex_col, 255), fo))
            p_w2 += float(measure_draw.textlength(txt, font=fo))
        styled_paras.append(p_runs)
        if p_w2 > natural_max_w2:
            natural_max_w2 = p_w2

    pad_x = int(round(38 * scale))
    pad_top = int(round(34 * scale))
    pad_mid = int(round(28 * scale))
    footer_h = int(round(68 * scale))

    min_cw = int(round((450 if upd_label else 390) * scale))
    max_cw = min(w - 48, int(round(500 * scale)))
    target_cw = int(natural_max_w2 / ss) + pad_x * 2 + 12
    card_w = max(280, min(max_cw, max(min_cw, target_cw)))

    max_text_w2 = max(120.0, float((card_w - pad_x * 2) * ss))
    wrapped = _wrap_styled_paragraphs(measure_draw, styled_paras, max_text_w2)

    line_h = int(round(25 * scale))
    max_lines = max(2, (h - 140 - pad_top - pad_mid - footer_h) // max(1, line_h))
    if len(wrapped) > max_lines:
        wrapped = wrapped[:max_lines]

    text_block_h = max(line_h, len(wrapped) * line_h)
    card_h = pad_top + text_block_h + pad_mid + footer_h

    cx, cy = w // 2, h // 2
    x0, y0 = cx - card_w // 2, cy - card_h // 2

    if base_img is not None:
        scene = base_img.resize((w, h), _RESAMPLE_BILINEAR).convert("RGBA")
    else:
        scene = _PILImage.new("RGBA", (w, h), (9, 11, 16, 255))

    # Sombra ambiente profunda e suave sob a janela cinza
    if not cfg.is_potato():
        fx_pad = 48
        sh_layer = _PILImage.new("RGBA", (card_w + fx_pad * 2, card_h + fx_pad * 2), (0, 0, 0, 0))
        sh_draw = _PILDraw.Draw(sh_layer)
        sh_draw.rounded_rectangle(
            (fx_pad, fx_pad + 14, fx_pad + card_w, fx_pad + card_h + 16),
            radius=int(round(18 * scale)), fill=(0, 0, 0, 205)
        )
        sh_layer = sh_layer.filter(_PILFilter.GaussianBlur(radius=20))
        scene.alpha_composite(sh_layer, (x0 - fx_pad, y0 - fx_pad))

    # Geometria dos botoes na barra inferior
    btn_h = int(round(38 * scale))
    btn_r = int(round(10 * scale))
    btn_y0 = y0 + card_h - footer_h + (footer_h - btn_h) // 2
    btn_y1 = btn_y0 + btn_h

    if upd_label:
        upd_tw = int(measure_draw.textlength(upd_label, font=fnt_btn) / ss)
        ok_w = int(round(126 * scale))
        upd_w = max(int(round(166 * scale)), upd_tw + int(round(42 * scale)))
        gap = int(round(12 * scale))
        tot_bw = ok_w + gap + upd_w
        bx_start = cx - tot_bw // 2
        ok_rect = (bx_start, btn_y0, bx_start + ok_w, btn_y1)
        upd_rect = (bx_start + ok_w + gap, btn_y0, bx_start + ok_w + gap + upd_w, btn_y1)
    else:
        ok_w = int(round(148 * scale))
        ok_rect = (cx - ok_w // 2, btn_y0, cx + ok_w - ok_w // 2, btn_y1)
        upd_rect = None

    # Card cinza moderno em 2x supersampling (gradiente vertical sutil #2C313D -> #222630 + dock #191C23)
    cw2, ch2, fh2 = card_w * ss, card_h * ss, footer_h * ss
    rad2 = int(round(16 * scale * ss))

    grad_strip = _PILImage.new("RGBA", (1, ch2), (0, 0, 0, 255))
    body_h2 = max(1, ch2 - fh2)
    for py in range(ch2):
        if py < body_h2:
            t_ratio = py / float(body_h2)
            r_c = int(45 - 10 * t_ratio)
            g_c = int(50 - 11 * t_ratio)
            b_c = int(62 - 13 * t_ratio)
            grad_strip.putpixel((0, py), (r_c, g_c, b_c, 255))
        else:
            grad_strip.putpixel((0, py), (25, 28, 35, 255))

    card_fill = grad_strip.resize((cw2, ch2), _RESAMPLE_NEAREST)
    mask = _PILImage.new("L", (cw2, ch2), 0)
    _PILDraw.Draw(mask).rounded_rectangle((0, 0, cw2 - 1, ch2 - 1), radius=rad2, fill=255)

    card_base_hi = _PILImage.new("RGBA", (cw2, ch2), (0, 0, 0, 0))
    card_base_hi.paste(card_fill, (0, 0), mask)
    cd = _PILDraw.Draw(card_base_hi)

    # Linha divisoria do rodape + borda fina cinza-metalica + reflexo interno superior
    cd.line((2 * ss, ch2 - fh2, cw2 - 2 * ss, ch2 - fh2), fill=(54, 60, 74, 255), width=ss)
    cd.rounded_rectangle((0, 0, cw2 - 1, ch2 - 1), radius=rad2, outline=(74, 82, 100, 255), width=ss)
    if ss > 1:
        cd.rounded_rectangle((ss, ss, cw2 - 1 - ss, ch2 - 1 - ss), radius=max(2, rad2 - ss), outline=(255, 255, 255, 22), width=1)

    # Renderiza cada linha de texto centralizada com precisao sub-pixel
    cur_ty2 = float(pad_top * ss)
    step_ty2 = float(line_h * ss)
    for line_tokens in wrapped:
        if line_tokens:
            tot_lw2 = sum(tok[3] for tok in line_tokens)
            tx2 = (cw2 - tot_lw2) / 2.0
            for tok_str, fill_rgba, fnt_tok, tok_w2 in line_tokens:
                cd.text((tx2, cur_ty2), tok_str, font=fnt_tok, fill=fill_rgba)
                tx2 += tok_w2
        cur_ty2 += step_ty2

    # Gera os frames (normal + hover nos botoes) sem recomputar fundo/texto
    states = ["none", "ok"] + (["update"] if upd_rect else [])
    frames = {}
    resample_mode = _RESAMPLE_BILINEAR if ss == 1 else _RESAMPLE_LANCZOS

    for st in states:
        c_hi = card_base_hi.copy()
        bd = _PILDraw.Draw(c_hi)

        # Botao OK
        ox0, oy0, ox1, oy1 = (
            (ok_rect[0] - x0) * ss, (ok_rect[1] - y0) * ss,
            (ok_rect[2] - x0) * ss, (ok_rect[3] - y0) * ss
        )
        ok_fill = (63, 70, 88, 255) if st == "ok" else (46, 51, 64, 255)
        ok_bord = (108, 119, 146, 255) if st == "ok" else (78, 86, 106, 255)
        bd.rounded_rectangle((ox0, oy0, ox1, oy1), radius=btn_r * ss, fill=ok_fill, outline=ok_bord, width=ss)
        _draw_centered_label(bd, (ox0 + ox1) / 2.0, (oy0 + oy1) / 2.0, "OK", fnt_btn, (255, 255, 255, 255))

        # Botao Fazer Update / Update (somente no comando /Update)
        if upd_rect:
            ux0, uy0, ux1, uy1 = (
                (upd_rect[0] - x0) * ss, (upd_rect[1] - y0) * ss,
                (upd_rect[2] - x0) * ss, (upd_rect[3] - y0) * ss
            )
            up_fill = (34, 190, 92, 255) if st == "update" else (25, 158, 75, 255)
            up_bord = (116, 236, 158, 255) if st == "update" else (62, 210, 115, 255)
            bd.rounded_rectangle((ux0, uy0, ux1, uy1), radius=btn_r * ss, fill=up_fill, outline=up_bord, width=ss)
            _draw_centered_label(bd, (ux0 + ux1) / 2.0, (uy0 + uy1) / 2.0, upd_label, fnt_btn, (255, 255, 255, 255))

        card_final = c_hi if ss == 1 else c_hi.resize((card_w, card_h), resample_mode)
        full_frame = scene.copy()
        full_frame.alpha_composite(card_final, (max(0, x0), max(0, y0)))
        frames[st] = full_frame.convert("RGB")

    return {
        "frames": frames,
        "ok_rect": ok_rect,
        "upd_rect": upd_rect,
        "card_rect": (x0, y0, x0 + card_w, y0 + card_h),
    }


class RemoteNoticeClient:
    """Cliente em tempo real com trava monotonica anti-repeticao para avisos do PS2Manager."""
    _FEED_ID = "6c47a70795044230ec17716c77757e3d"
    RELEASES_URL = "https://github.com/jujubs4002/PS2Manager/releases"
    _session = None
    _watcher_started = False
    _lock = threading.Lock()
    _dispatched_ids = set()

    @staticmethod
    def _norm_ver(v: str) -> str:
        return str(v or "").strip().lower().lstrip("v")

    @classmethod
    def _get_session(cls):
        if _requests is not None and cls._session is None:
            cls._session = _requests.Session()
        return cls._session

    @classmethod
    def _seen_state(cls) -> tuple:
        last_seen = int(cfg.data.get("last_news_id", 0) or 0)
        raw_list = cfg.data.get("seen_news_ids") or []
        seen_set = {int(x) for x in raw_list if isinstance(x, int) or str(x).isdigit()}
        return last_seen, seen_set

    @classmethod
    def mark_seen(cls, news_id: int):
        """Grava o ID de forma monotonica imediata (nunca regride mesmo se o CDN alternar revisoes)."""
        if news_id <= 0:
            return
        with cls._lock:
            cls._dispatched_ids.add(news_id)
            cur_last = int(cfg.data.get("last_news_id", 0) or 0)
            raw_list = cfg.data.get("seen_news_ids") or []
            seen_list = [int(x) for x in raw_list if isinstance(x, int) or str(x).isdigit()]
            changed = False
            if news_id > cur_last:
                cfg.data["last_news_id"] = news_id
                changed = True
            if news_id not in seen_list:
                seen_list.append(news_id)
                cfg.data["seen_news_ids"] = seen_list[-40:]
                changed = True
            if changed:
                cfg.save()

    @classmethod
    def parse_payload(cls, raw_text: str):
        if not raw_text:
            return None
        try:
            data = json.loads(raw_text)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None

        try:
            news_id = int(data.get("id", 0) or 0)
        except Exception:
            return None
        if news_id <= 0:
            return None

        with cls._lock:
            last_seen, seen_set = cls._seen_state()
            # Trava <= impede que nos de CDN atrasados reenviem mensagens antigas em loop!
            if news_id <= last_seen or news_id in seen_set:
                return None

        kind = str(data.get("k", "") or "").strip().lower()
        if kind not in ("new", "update", "warn", "warnuu"):
            return None

        if kind == "update":
            ver = str(data.get("v", "") or "").strip()[:40]
            if not ver:
                return None
            if cls._norm_ver(ver) == cls._norm_ver(APP_VERSION):
                return None
            return {"id": news_id, "k": "update", "m": "", "v": ver}

        msg = str(data.get("m", "") or "").strip()[:1200]
        if not msg:
            return None
        return {"id": news_id, "k": kind, "m": msg, "v": ""}

    @classmethod
    def _http_get_text(cls, url: str, headers: dict, timeout: int = 5):
        sess = cls._get_session()
        if sess is not None:
            r = sess.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.text
            return None
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="replace")
        return None

    @classmethod
    def fetch_sync(cls):
        ts_ms = int(time.time() * 1000)
        raw_url = f"https://gist.githubusercontent.com/jujubs4002/{cls._FEED_ID}/raw/News.json?_={ts_ms}"
        api_url = f"https://api.github.com/gists/{cls._FEED_ID}?_={ts_ms}"
        base_headers = {
            "User-Agent": f"PS2Manager/{APP_VERSION}",
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache"
        }

        content = None
        try:
            content = cls._http_get_text(raw_url, base_headers, timeout=5)
        except Exception:
            content = None

        if not content:
            try:
                api_headers = dict(base_headers)
                api_headers["Accept"] = "application/vnd.github+json"
                body = cls._http_get_text(api_url, api_headers, timeout=5)
                if body:
                    meta = json.loads(body)
                    files = meta.get("files", {}) if isinstance(meta, dict) else {}
                    f_obj = files.get("News.json") or (next(iter(files.values()), None) if files else None)
                    if isinstance(f_obj, dict):
                        content = f_obj.get("content")
            except Exception:
                content = None

        return cls.parse_payload(content)

    @classmethod
    def _claim_dispatch(cls, notice: dict) -> bool:
        if not notice:
            return False
        nid = int(notice.get("id", 0) or 0)
        with cls._lock:
            last_seen, seen_set = cls._seen_state()
            if nid <= 0 or nid <= last_seen or nid in seen_set or nid in cls._dispatched_ids:
                return False
            cls._dispatched_ids.add(nid)
            return True

    @classmethod
    def fetch_async(cls, cb_found):
        def _worker():
            notice = cls.fetch_sync()
            if cls._claim_dispatch(notice) and callable(cb_found):
                cb_found(notice)

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def start_live_watcher(cls, app_ref, cb_found):
        """Monitora apenas avisos ineditos (id > last_news_id) enquanto o PS2Manager estiver aberto."""
        if cls._watcher_started:
            return
        cls._watcher_started = True

        def _loop():
            while True:
                time.sleep(10.0 if cfg.is_potato() else 6.0)
                try:
                    if not app_ref.winfo_exists():
                        break
                except Exception:
                    break
                try:
                    if getattr(app_ref, "setup_frame", None) is None:
                        notice = cls.fetch_sync()
                        if cls._claim_dispatch(notice) and callable(cb_found):
                            cb_found(notice)
                except Exception:
                    pass

        threading.Thread(target=_loop, daemon=True).start()


class NewsOverlayModal(tk.Frame):
    """Janela interna unificada em Canvas 2x anti-aliased (mesma tarefa do PS2Manager, zero desalinhamento de DPI)."""
    COLOR_MAP = {
        "new": "#FFFFFF",
        "warn": "#FACC15",
        "warnuu": "#FF4D4D",
    }

    def __init__(self, app, notice: dict, base_dim_pil=None):
        self._base_dim_pil = base_dim_pil if base_dim_pil is not None else _capture_dimmed_client_image(app, brightness=0.25)
        super().__init__(app, bg="#090B10", bd=0, highlightthickness=0)
        self.app = app
        self.notice = notice
        self.news_id = int(notice.get("id", 0) or 0)
        self.kind = str(notice.get("k", "new")).lower()

        # Marca como visto imediatamente ao exibir: nunca repete em loop nem ao reabrir!
        if self.news_id > 0:
            RemoteNoticeClient.mark_seen(self.news_id)

        if self.kind == "update":
            self.ver_str = str(notice.get("v", "")).strip()
            self.text_color = "#FFFFFF"
            self.rendered_text = f"Version {self.ver_str} is available! Click the button below to go to the GitHub page."
            self._paragraphs_spec = [
                [("Version ", "#FFFFFF", False), (self.ver_str, "#22C55E", True), (" is available!", "#FFFFFF", False)],
                [("Click the button below to go to the GitHub page.", "#E2E8F0", False)],
            ]
            self._upd_label = t("news_btn_update")
        else:
            self.ver_str = ""
            self.text_color = self.COLOR_MAP.get(self.kind, "#FFFFFF")
            raw_msg = str(notice.get("m", "")).strip()
            self.rendered_text = raw_msg
            self._paragraphs_spec = [
                [(line_txt, self.text_color, False)] for line_txt in (raw_msg.splitlines() or [raw_msg])
            ]
            self._upd_label = None

        self._photos = {}
        self._raw_frames = {}
        self._bg_photo = None
        self._hover_state = "none"
        self._pressed_target = None
        self._ok_rect = (0, 0, 0, 0)
        self._upd_rect = None
        self._last_sig = None

        self.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
        self.lift()

        self._canvas = tk.Canvas(self, bg="#090B10", bd=0, highlightthickness=0, relief="flat")
        self._canvas.pack(fill="both", expand=True)
        self._img_item = self._canvas.create_image(0, 0, anchor="nw")

        self._canvas.bind("<Motion>", self._on_mouse_move)
        self._canvas.bind("<Leave>", lambda e: self._set_hover("none"))
        self._canvas.bind("<ButtonPress-1>", self._on_mouse_press)
        self._canvas.bind("<ButtonRelease-1>", self._on_mouse_release)
        self.bind("<Configure>", self._on_resize_backdrop)

        self.update_idletasks()
        win_w = max(400, self.app.winfo_width())
        win_h = max(300, self.app.winfo_height())
        self._render_backdrop(win_w, win_h)

        if self.kind == "warnuu":
            sound_fx.play_error()
        elif self.kind == "warn":
            sound_fx.play_warning()
        elif self.kind == "update":
            sound_fx.play_success()
        else:
            sound_fx.play_click()

    @staticmethod
    def _in_rect(x: int, y: int, rect) -> bool:
        return bool(rect and rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3])

    def _hit_target(self, x: int, y: int) -> str:
        if self._in_rect(x, y, self._ok_rect):
            return "ok"
        if self._upd_rect and self._in_rect(x, y, self._upd_rect):
            return "update"
        return "none"

    def _set_hover(self, target: str):
        if target not in self._photos:
            target = "none"
        if target != self._hover_state and target in self._photos:
            self._hover_state = target
            self._bg_photo = self._photos[target]
            self._canvas.itemconfig(self._img_item, image=self._bg_photo)
        self._canvas.configure(cursor="hand2" if target in ("ok", "update") else "")

    def _on_mouse_move(self, event):
        self._set_hover(self._hit_target(event.x, event.y))

    def _on_mouse_press(self, event):
        self._pressed_target = self._hit_target(event.x, event.y)
        return "break"

    def _on_mouse_release(self, event):
        rel_target = self._hit_target(event.x, event.y)
        pressed = self._pressed_target
        self._pressed_target = None
        if pressed == "ok" and rel_target == "ok":
            self._on_ok()
        elif pressed == "update" and rel_target == "update":
            self._on_update()
        return "break"

    def _render_backdrop(self, w: int, h: int):
        if not _PIL_MODAL_OK or w < 120 or h < 120:
            return
        sig = (w, h)
        if sig == self._last_sig:
            return
        try:
            rendered = _render_unified_modal_frames(
                self._base_dim_pil, w, h, self._paragraphs_spec, self._upd_label
            )
            if rendered is not None:
                self._raw_frames = rendered["frames"]
                self._photos = {k: _PILImageTk.PhotoImage(img) for k, img in self._raw_frames.items()}
                self._ok_rect = rendered["ok_rect"]
                self._upd_rect = rendered["upd_rect"]
                cur_st = self._hover_state if self._hover_state in self._photos else "none"
                self._bg_photo = self._photos[cur_st]
                self._canvas.itemconfig(self._img_item, image=self._bg_photo)
                self._last_sig = sig
        except Exception:
            pass

    def _on_resize_backdrop(self, event):
        if event.widget is self and event.width > 120 and event.height > 120:
            self._render_backdrop(event.width, event.height)

    def _acknowledge(self):
        if self.news_id > 0:
            RemoteNoticeClient.mark_seen(self.news_id)

    def _on_ok(self):
        sound_fx.play_click()
        self._acknowledge()
        if getattr(self.app, "_news_overlay", None) is self:
            self.app._news_overlay = None
        self.destroy()

    def _on_update(self):
        sound_fx.play_click()
        self._acknowledge()
        try:
            webbrowser.open(RemoteNoticeClient.RELEASES_URL)
        except Exception:
            pass
        self.app.after(150, self._close_app_for_update)

    def _close_app_for_update(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        sys.exit(0)


class VersionRollbackModal(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(t("modal_rollback"))
        self.geometry("460x500")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        ctk.CTkLabel(
            self, text=t("ver_btn"), font=("Segoe UI Black", 16),
            text_color=cfg.get_color("accent")
        ).pack(pady=(20, 6))
        self.sf = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.sf.pack(fill="both", expand=True, padx=20, pady=15)
        ver_dir = os.path.join(BASE_DIR, "VER")
        os.makedirs(ver_dir, exist_ok=True)
        exes = sorted(f for f in os.listdir(ver_dir) if f.lower().endswith('.exe'))
        if not exes:
            ctk.CTkLabel(self.sf, text=t("ver_empty"), text_color=cfg.get_color("text_muted")).pack(pady=30)
        else:
            for exe in exes:
                ctk.CTkButton(
                    self.sf, text=f"▶  {t('ver_launch')} {os.path.splitext(exe)[0]}",
                    fg_color=cfg.get_color("bg_main"), text_color=cfg.get_color("text_main"),
                    hover_color=cfg.get_hover("accent", "bg_main"), height=38,
                    corner_radius=cfg.get_radius("button"),
                    command=lambda e=exe: self.launch_old(e)
                ).pack(fill="x", pady=4, padx=6)

    def launch_old(self, exe_name):
        sound_fx.play_click()
        subprocess.Popen([os.path.join(BASE_DIR, "VER", exe_name)])
        sys.exit(0)


class ChangelogTimelineModal(ctk.CTkToplevel):
    """Linha do tempo interativa completa de v1.00 até v1.08 + Roadmap futuro nos 6 idiomas."""
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
            "title": ["OPL Apps & Homebrew", "OPL Apps & Homebrew", "OPL Apps & Homebrew", "OPL Apps y Homebrew", "OPL приложения", "OPLアプリ対応"],
            "desc": [
                "Support for installing homebrew ELF applications into OPL APPS menu.",
                "Suporte à instalação de aplicativos homebrew .ELF direto na aba APPS do OPL.",
                "Suporte à instalação de aplicações homebrew .ELF na aba APPS do OPL.",
                "Instalación de aplicaciones ELF directamente en el menú APPS de OPL.",
                "Поддержка установки приложений ELF в меню APPS OPL.",
                "OPLのAPPSメニューへのELFアプリ導入サポート。"
            ]
        },
        {
            "ver": "v1.03", "date": "29/09/2026",
            "title": ["Cheats & ZSO Compression", "Criador de Cheats & ZSO", "Criador de Cheats & ZSO", "Cheats y Formato ZSO", "Читы и сжатие ZSO", "チート作成＆ZSO圧縮"],
            "desc": [
                "Added .cht cheat creator for OPL/PS2RD and LZ4 ZSO ISO compression.",
                "Adicionado criador de arquivos .cht para OPL e compressão de jogos em formato ZSO.",
                "Adicionado criador de ficheiros .cht para OPL e compressão em formato ZSO.",
                "Creador de archivos .cht para OPL y compresión de juegos en formato ZSO.",
                "Создание файлов читов .cht для OPL и сжатие образов в формат ZSO.",
                "OPL用.chtチート作成機能とZSO圧縮フォーマットのサポート。"
            ]
        },
        {
            "ver": "v1.04", "date": "01/10/2026",
            "title": ["USBUtil, Disc Analyzer & BIN➔ISO", "USBUtil, Analisador & BIN➔ISO", "USBUtil, Analisador & BIN➔ISO", "USBUtil, Analizador y BIN➔ISO", "USBUtil и анализ дисков", "USBUtil分割＆ディスク解析"],
            "desc": [
                "FAT32 >4GB ISO splitting (ul.cfg), physical disc analyzer, and BIN to ISO conversion.",
                "Divisão USBUtil (>4GB em FAT32), analisador de disco físico e conversão BIN para ISO.",
                "Divisão USBUtil (>4GB em FAT32), analisador de disco físico e conversão BIN para ISO.",
                "División USBUtil (>4GB en FAT32), analizador de disco físico y conversión BIN a ISO.",
                "Разделение игр >4 ГБ для FAT32 (ul.cfg), анализатор дисков и конвертер BIN в ISO.",
                "FAT32用4GB超分割(ul.cfg)、光学ディスク解析、BIN➔ISO変換の追加。"
            ]
        },
        {
            "ver": "v1.05", "date": "04/10/2026",
            "title": ["APA HDD & OPL Covers", "Suporte HDD APA & Capas OPL", "Suporte HDD APA & Capas OPL", "Soporte HDD APA y Carátulas", "Поддержка APA HDD и обложек", "APA HDD＆OPLカバー取得"],
            "desc": [
                "PS2 APA HDD partition explorer/extractor and automatic OPL cover downloader.",
                "Explorador e extrator de HDs de PS2 em formato APA e download automático de capas OPL.",
                "Explorador e extrator de discos PS2 em formato APA e download automático de capas OPL.",
                "Explorador de discos duros PS2 APA y descargador automático de carátulas OPL.",
                "Проводник дисков PS2 APA и автоматическая загрузка обложек OPL.",
                "PS2用APAフォーマットHDDの閲覧・抽出とOPLカバー自動取得。"
            ]
        },
        {
            "ver": "v1.06", "date": "10/10/2026",
            "title": ["ZSO Modes & ISO Modding", "Modos ZSO (Fast/Ultra) & Patcher", "Modos ZSO (Fast/Ultra) & Patcher", "Modos ZSO y Parcheo ISO", "Режимы ZSO и моддинг ISO", "ZSOモード＆ISOパッチ"],
            "desc": [
                "Added Fast & Ultra ZSO compression modes, ISO patching, and region-lock removal.",
                "Modos Fast e Ultra na compressão ZSO, aplicação de patches em ISOs e remoção de região.",
                "Modos Fast e Ultra na compressão ZSO, aplicação de patches em ISOs e remoção de região.",
                "Modos Fast y Ultra para ZSO, aplicación de parches ISO y desbloqueo regional.",
                "Быстрый и Ультра режимы сжатия ZSO, патчинг ISO и снятие региональной защиты.",
                "ZSOのFast/Ultra圧縮モード、ISOパッチ適用、リージョン解除機能。"
            ]
        },
        {
            "ver": "v1.07", "date": "06/11/2026",
            "title": ["1-Click USB, Batch & DVD Burn", "Instalação 1-Clique, Lote & DVD", "Instalação 1-Clique, Lote & DVD", "1-Clic USB, Lotes y Grabador DVD", "1-Клик USB, Пакеты и DVD", "1クリック転送・一括処理・DVD書込"],
            "desc": [
                "1-Click USB installer, batch queue, real DVD burner, anti-corruption watchdog, 6 languages.",
                "Instalador 1-clique no pendrive, fila em lote, gravador real de DVD, watchdog e 6 idiomas.",
                "Instalador 1-clique na pen USB, fila por lotes, gravador real de DVD, watchdog e 6 idiomas.",
                "Instalador 1-clic en USB, cola por lotes, grabador real de DVD, watchdog y 6 idiomas.",
                "Установка на USB в 1 клик, очередь, прожиг DVD, защита файлов и 6 языков.",
                "1クリックUSB導入、一括キュー、実DVD書き込み、破損防止監視、6言語対応。"
            ]
        },
        {
            "ver": "v1.08", "date": "07/11/2026",
            "title": ["Defrag, OPL CFG, Memory Card & VCD", "Defrag USB, Modos OPL, Memory Card & VCD", "Defrag USB, Modos OPL, Cartão & VCD", "Defrag USB, Modos OPL, Memory Card y VCD", "Дефраг USB, OPL CFG, Карты памяти и VCD", "USB最適化・OPL設定・メモリーカード・VCD"],
            "desc": [
                "USB Fragmentation Checker & Optimizer, OPL Modes/GSM/16:9 CFG Editor, PS1 BIN/CUE ➔ .VCD, Permanent 16:9 & PAL➔NTSC Patcher, Art Scraper 2.0, PS2 Memory Card Manager (.ps2 ⇄ .bin / .psu), Potato Mode & UI 2.0!",
                "Verificador/Otimizador de Fragmentação USB (Anti-Tela Preta), Editor CFG de Modos OPL + GSM + 16:9, PS1 BIN/CUE ➔ .VCD, Patcher Permanente 16:9 & PAL➔NTSC, Art Scraper 2.0 com prévia, Memory Card Manager (.ps2 ⇄ .bin / .psu), Modo Batata turbinado e nova UI!",
                "Verificador/Otimizador de Fragmentação USB (Anti-Ecrã Preto), Editor CFG de Modos OPL + GSM + 16:9, PS1 BIN/CUE ➔ .VCD, Patcher Permanente 16:9 & PAL➔NTSC, Art Scraper 2.0, Gestor de Memory Card (.ps2 ⇄ .bin / .psu), Modo Batata e nova UI!",
                "Optimizador de Fragmentación USB, Editor OPL CFG + GSM + 16:9, PS1 BIN/CUE ➔ .VCD, Parche 16:9 y PAL➔NTSC, Art Scraper 2.0, Gestor de Memory Card (.ps2 ⇄ .bin / .psu) y Modo Patata!",
                "Оптимизатор фрагментации USB, редактор OPL CFG/GSM/16:9, PS1 BIN/CUE ➔ .VCD, патчер 16:9 и PAL➔NTSC, Art Scraper 2.0, менеджер карт памяти (.ps2 ⇄ .bin / .psu) и Режим Картошки!",
                "USB断片化チェッカー＆最適化、OPL互換/GSM/16:9エディタ、PS1 .VCD変換、恒久16:9＆PAL➔NTSCパッチ、Art Scraper 2.0、メモリーカード管理(.ps2⇄.bin/.psu)、ポテトモード搭載！"
            ]
        },
        {
            "ver": "v1.09+", "date": "Future",
            "title": ["Future Update", "Próxima Atualização", "Próxima Atualização", "Futura Actualización", "Будущее обновление", "将来のアップデート"],
            "desc": [
                "No future updates currently planned. Enjoy all features of PS2Manager v1.08!",
                "Nenhuma atualização planejada no momento. Aproveite todos os recursos da v1.08!",
                "Nenhuma atualização planeada no momento. Aproveite todos os recursos da v1.08!",
                "No hay actualizaciones planificadas actualmente. ¡Disfruta de PS2Manager v1.08!",
                "На данный момент обновлений не планируется. Наслаждайтесь всеми функциями v1.08!",
                "現在計画されている更新はありません。v1.08の全機能をお楽しみください！"
            ]
        }
    ]

    def __init__(self, master):
        super().__init__(master)
        self.title(t("roadmap_title"))
        self.geometry("760x580")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.resizable(False, False)
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.cur_idx = 8  # Índice da v1.08 (atual)
        lang_code = cfg.data.get("language", "PT_BR")
        self.lang_idx = LANGS.get(lang_code, 1)

        ctk.CTkLabel(
            self, text=t("roadmap_title"),
            font=("Segoe UI Black", 19), text_color=cfg.get_color("accent")
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            self, text=t("roadmap_sub"),
            font=("Segoe UI", 12), text_color=cfg.get_color("text_muted")
        ).pack(pady=(0, 12))

        timeline_frm = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        timeline_frm.pack(fill="x", padx=28, pady=8)

        nodes_frm = ctk.CTkFrame(timeline_frm, fg_color="transparent")
        nodes_frm.pack(fill="x", padx=16, pady=(14, 8))
        nodes_frm.grid_columnconfigure(tuple(range(len(self.RELEASES))), weight=1)

        self.node_lbls = []
        for idx, r_data in enumerate(self.RELEASES):
            lbl = ctk.CTkLabel(
                nodes_frm, text=r_data["ver"],
                font=("Segoe UI", 10, "bold"),
                text_color=cfg.get_color("highlight") if idx == self.cur_idx else cfg.get_color("text_muted")
            )
            lbl.grid(row=0, column=idx, padx=2)
            self.node_lbls.append(lbl)

        self.slider = ctk.CTkSlider(
            timeline_frm, from_=0, to=len(self.RELEASES) - 1, number_of_steps=len(self.RELEASES) - 1,
            command=self.on_slide, height=18, progress_color=cfg.get_color("accent")
        )
        self.slider.pack(fill="x", padx=26, pady=(0, 12))
        self.slider.set(self.cur_idx)

        self.card = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.card.pack(fill="both", expand=True, padx=28, pady=12)

        self.lbl_ver = ctk.CTkLabel(self.card, text="", font=("Segoe UI Black", 24), text_color=cfg.get_color("accent"))
        self.lbl_ver.pack(pady=(22, 2))
        self.lbl_date = ctk.CTkLabel(self.card, text="", font=("Consolas", 12, "bold"), text_color=cfg.get_color("text_muted"))
        self.lbl_date.pack(pady=(0, 14))
        self.lbl_title = ctk.CTkLabel(self.card, text="", font=("Segoe UI", 16, "bold"), text_color=cfg.get_color("text_main"))
        self.lbl_title.pack(pady=(0, 10))
        self.lbl_desc = ctk.CTkLabel(
            self.card, text="", font=("Segoe UI", 13),
            text_color=cfg.get_color("text_main"), wraplength=640, justify="center"
        )
        self.lbl_desc.pack(pady=(0, 20), padx=28)

        nav_frm = ctk.CTkFrame(self, fg_color="transparent")
        nav_frm.pack(fill="x", padx=28, pady=(0, 20))
        ctk.CTkButton(
            nav_frm, text=t("roadmap_prev"), width=150, height=36,
            fg_color=cfg.get_color("card_base"), hover_color=cfg.get_hover("card_hover", "card_base"),
            corner_radius=cfg.get_radius("button"), command=lambda: self.step(-1)
        ).pack(side="left")
        ctk.CTkButton(
            nav_frm, text=t("roadmap_next"), width=150, height=36,
            fg_color=cfg.get_color("card_base"), hover_color=cfg.get_hover("card_hover", "card_base"),
            corner_radius=cfg.get_radius("button"), command=lambda: self.step(1)
        ).pack(side="right")
        self.update_view()

    def on_slide(self, val):
        new_idx = int(round(val))
        if new_idx != self.cur_idx:
            self.cur_idx = new_idx
            sound_fx.play_click()
            self.update_view()

    def step(self, delta):
        sound_fx.play_click()
        self.cur_idx = max(0, min(len(self.RELEASES) - 1, self.cur_idx + delta))
        self.slider.set(self.cur_idx)
        self.update_view()

    def update_view(self):
        item = self.RELEASES[self.cur_idx]
        is_cur = (self.cur_idx == 8)
        self.lbl_ver.configure(
            text=f"{item['ver']} — {t('roadmap_cur')}" if is_cur else item['ver'],
            text_color=cfg.get_color("highlight") if is_cur else cfg.get_color("accent")
        )
        self.lbl_date.configure(text=f"Release Date: {item['date']}")
        t_list = item["title"]
        d_list = item["desc"]
        self.lbl_title.configure(text=t_list[self.lang_idx] if self.lang_idx < len(t_list) else t_list[0])
        self.lbl_desc.configure(text=d_list[self.lang_idx] if self.lang_idx < len(d_list) else d_list[0])
        for idx, lbl in enumerate(self.node_lbls):
            if idx == self.cur_idx:
                lbl.configure(text_color=cfg.get_color("highlight"), font=("Segoe UI", 11, "bold"))
            else:
                lbl.configure(text_color=cfg.get_color("text_muted"), font=("Segoe UI", 10))


class GameDetailsModal(ctk.CTkToplevel):
    def __init__(self, master, game_data):
        super().__init__(master)
        self.title(t("modal_game_profile"))
        self.geometry("510x490")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.resizable(False, False)
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.app, self.game_data = master, game_data
        ctk.CTkLabel(
            self, text=game_data.get('name', 'Unknown'),
            font=("Segoe UI Black", 17), text_color=cfg.get_color("text_main")
        ).pack(pady=(20, 4), padx=20)
        ctk.CTkLabel(
            self, text=game_data.get('path', ''),
            font=("Consolas", 9), text_color=cfg.get_color("text_muted")
        ).pack(pady=(0, 14), padx=20)

        frm = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        frm.pack(fill="x", padx=22, pady=4)

        def add_row(r, k, v):
            ctk.CTkLabel(frm, text=k, font=("Segoe UI", 11, "bold"), text_color=cfg.get_color("text_muted")).grid(row=r, column=0, sticky="w", padx=16, pady=5)
            ctk.CTkLabel(frm, text=v, font=("Consolas", 11, "bold"), text_color=cfg.get_color("highlight" if r == 0 else "text_main")).grid(row=r, column=1, sticky="w", padx=16, pady=5)

        add_row(0, t("game_id"), game_data.get('id', 'N/A'))
        add_row(1, t("game_format"), f"{game_data.get('format', 'N/A')} ({game_data.get('media_type', 'DVD')})")
        add_row(2, t("game_size"), game_data.get('size_str', 'N/A'))
        add_row(3, t("game_region"), game_data.get('region', 'Unknown'))

        rad = cfg.get_radius("button")
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(18, 8), padx=22)

        ctk.CTkButton(
            btn_frame, text=t("lib_btn_test"), font=("Segoe UI", 11, "bold"), height=38,
            fg_color=cfg.get_color("accent"), hover_color=cfg.get_hover("accent_hover", "accent"),
            corner_radius=rad,
            command=lambda: [sound_fx.play_click(), PCSX2Integration.test_iso(game_data['path'], lambda e: messagebox.showerror(t("error"), e))]
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))

        ctk.CTkButton(
            btn_frame, text=t("lib_btn_inst"), font=("Segoe UI", 11, "bold"), height=38,
            fg_color=cfg.get_color("success"), corner_radius=rad,
            command=self.send_to_install
        ).pack(side="left", expand=True, fill="x", padx=5)

        btn_frame_mid = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame_mid.pack(fill="x", pady=(0, 8), padx=22)
        ctk.CTkButton(
            btn_frame_mid, text=t("lib_btn_cfg"), font=("Segoe UI", 11, "bold"), height=38,
            fg_color=cfg.get_color("chip_bg"), hover_color=cfg.get_hover("card_hover", "chip_bg"),
            text_color=cfg.get_color("highlight"), corner_radius=rad,
            command=self.send_to_opl_cfg
        ).pack(fill="x")

        btn_frame2 = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame2.pack(fill="x", pady=(4, 16), padx=22)
        ctk.CTkButton(
            btn_frame2, text=t("lib_btn_rem"), font=("Segoe UI", 11, "bold"), height=36,
            fg_color=cfg.get_color("danger"), corner_radius=rad, command=self.remove_game
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(
            btn_frame2, text=t("lib_btn_close"), font=("Segoe UI", 11, "bold"), height=36,
            fg_color=cfg.get_color("border"), text_color=cfg.get_color("text_main"),
            corner_radius=rad, command=lambda: [sound_fx.play_close(), self.destroy()]
        ).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def send_to_install(self):
        sound_fx.play_click()
        self.destroy()
        self.app.show("install")
        if "install" in self.app.pages:
            self.app.pages["install"].set_iso(self.game_data['path'])

    def send_to_opl_cfg(self):
        sound_fx.play_click()
        self.destroy()
        self.app.show("opl_cfg")
        if "opl_cfg" in self.app.pages:
            self.app.pages["opl_cfg"].select_external_game(self.game_data)

    def remove_game(self):
        sound_fx.play_click()
        if messagebox.askyesno(t("confirm"), t("msg_remove_confirm")):
            self.app.library.games = [g for g in self.app.library.games if g['path'] != self.game_data['path']]
            db.save()
            sound_fx.play_success()
            self.app.refresh_all()
            self.destroy()


# ==============================================================================
# CHEAT ENGINE (.CHT) - 100% PRESERVADO E POLIDO
# ==============================================================================
class CheatEditorModal(ctk.CTkToplevel):
    def __init__(self, master, app, cht_folder, edit_file=None):
        super().__init__(master)
        self.title("PS2Manager Cheats (.CHT)")
        self.geometry("620x580")
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

        ctk.CTkLabel(self, text="Cheat Codes (RAW PS2RD):", font=("Segoe UI", 12, "bold"), text_color=cfg.get_color("text_main")).pack(pady=(15, 5), padx=20, anchor="w")
        self.txt_codes = ctk.CTkTextbox(
            self, font=("Consolas", 12), fg_color=cfg.get_color("card_base"),
            border_color=cfg.get_color("border"), border_width=cfg.get_border_width(),
            text_color=cfg.get_color("text_main"), corner_radius=cfg.get_radius("card")
        )
        self.txt_codes.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        ctk.CTkButton(
            self, text=t("cht_save"), font=("Segoe UI", 12, "bold"),
            fg_color=cfg.get_color("success"), height=40, corner_radius=cfg.get_radius("button"),
            command=self.save
        ).pack(fill="x", padx=20, pady=(0, 20))

        if self.edit_file:
            base_name = os.path.basename(self.edit_file)
            if base_name.endswith('.disabled'):
                base_name = base_name[:-9]
            if base_name.endswith('.cht'):
                base_name = base_name[:-4]
            self.ent_name.insert(0, base_name)
            try:
                with open(self.edit_file, 'r', encoding='utf-8', errors='ignore') as f:
                    self.txt_codes.insert("0.0", f.read())
            except Exception as e:
                messagebox.showerror(t("error"), str(e))

    def on_game_select(self, val):
        sound_fx.play_click()
        if val == t("cht_manual"):
            return
        game_id = ArtScraperWorker.format_opl_id(val.split(" - ")[0])
        game_name = val.split(" - ", 1)[1] if " - " in val else ""
        self.ent_name.delete(0, 'end')
        self.ent_name.insert(0, game_id)
        if not self.txt_codes.get("0.0", "end").strip():
            self.txt_codes.insert("0.0", f"\"{game_name} /ID {game_id}\"\nMastercode\n90000000 00000000\n\n// Cheat Code\n")

    def save(self):
        sound_fx.play_click()
        name = self.ent_name.get().strip()
        if not name:
            return
        if not name.lower().endswith(".cht"):
            name += ".cht"
        if self.edit_file and self.edit_file.endswith(".disabled"):
            name += ".disabled"
        out_path = os.path.join(self.cht_folder, name)
        try:
            os.makedirs(self.cht_folder, exist_ok=True)
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
        self.geometry("360x240")
        self.configure(fg_color=cfg.get_color("bg_main"))
        self.attributes("-topmost", True)
        apply_window_icon(self)
        self.after(80, lambda: apply_window_icon(self))

        self.app, self.cht_folder = app, cht_folder
        ctk.CTkLabel(self, text=t("cht_add"), font=("Segoe UI Black", 16), text_color=cfg.get_color("text_main")).pack(pady=(22, 24))
        r = cfg.get_radius("button")
        ctk.CTkButton(self, text=t("cht_import"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=40, corner_radius=r, command=self.import_cht).pack(fill="x", padx=36, pady=8)
        ctk.CTkButton(self, text=t("cht_create"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("success"), height=40, corner_radius=r, command=self.create_scratch).pack(fill="x", padx=36, pady=8)

    def import_cht(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[("Cheat Files", "*.cht")])
        if f:
            try:
                os.makedirs(self.cht_folder, exist_ok=True)
                shutil.copy2(f, self.cht_folder)
                sound_fx.play_success()
                self.app.refresh_all()
                self.destroy()
            except Exception as e:
                sound_fx.play_error()
                messagebox.showerror(t("error"), f"{t('cht_err')} {e}")

    def create_scratch(self):
        sound_fx.play_click()
        self.destroy()
        CheatEditorModal(self.master, self.app, self.cht_folder)


class CheatManagerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.current_folder = cfg.data.get("last_cht_folder", "")
        self.selected_file = None
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        PageHeader(self, t("tab_cht"), "", badge_text="PS2RD / OPL").grid(row=0, column=0, sticky="ew", pady=(0, 14))

        folder_frm = ctk.CTkFrame(
            self, fg_color=cfg.get_color("card_base"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border"),
            corner_radius=cfg.get_radius("card")
        )
        folder_frm.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(folder_frm, text=t("cht_folder"), font=("Segoe UI", 11, "bold")).pack(side="left", padx=15, pady=12)
        self.ent_folder = ctk.CTkEntry(folder_frm, fg_color=cfg.get_color("bg_main"), height=32, corner_radius=cfg.get_radius("entry"))
        self.ent_folder.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=12)
        if self.current_folder:
            self.ent_folder.insert(0, self.current_folder)
        ctk.CTkButton(folder_frm, text=t("btn_browse"), font=("Segoe UI", 11, "bold"), width=90, height=32, corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left", padx=(0, 15), pady=12)

        act_frm = ctk.CTkFrame(self, fg_color="transparent")
        act_frm.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        r = cfg.get_radius("button")
        ctk.CTkButton(act_frm, text=t("cht_add"), height=34, font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("accent"), corner_radius=r, command=self.open_add).pack(side="left", padx=(0, 6))
        ctk.CTkButton(act_frm, text=t("cht_edit"), height=34, font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("warning"), text_color="#000", corner_radius=r, command=self.open_edit).pack(side="left", padx=6)
        ctk.CTkButton(act_frm, text=t("cht_enable"), height=34, font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("success"), corner_radius=r, command=self.enable_cheat).pack(side="left", padx=6)
        ctk.CTkButton(act_frm, text=t("cht_disable"), height=34, font=("Segoe UI", 11, "bold"), fg_color=cfg.get_color("danger"), corner_radius=r, command=self.disable_cheat).pack(side="left", padx=6)

        self.list_frm = ctk.CTkScrollableFrame(
            self, fg_color=cfg.get_color("card_base"),
            corner_radius=cfg.get_radius("card"),
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        self.list_frm.grid(row=3, column=0, sticky="nsew")
        self.refresh()

    def open_add(self):
        sound_fx.play_click()
        self.current_folder = self.ent_folder.get().strip()
        if self.current_folder and os.path.exists(self.current_folder):
            AddCheatModal(self, self.app, self.current_folder)
        else:
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("cht_folder"))

    def open_edit(self):
        sound_fx.play_click()
        if self.selected_file:
            CheatEditorModal(self, self.app, self.current_folder, self.selected_file)
        else:
            sound_fx.play_warning()
            messagebox.showwarning(t("warning"), t("cht_none"))

    def browse(self):
        sound_fx.play_click()
        d = filedialog.askdirectory()
        if d:
            self.ent_folder.delete(0, 'end')
            self.ent_folder.insert(0, d)
            self.current_folder = d
            cfg.data["last_cht_folder"] = d
            cfg.save()
            self.refresh()

    def refresh(self):
        if not self.ent_folder.get().strip():
            drives = DriveManager.get_drives()
            if drives:
                cand = os.path.join(drives[0]["mountpoint"], "CHT")
                os.makedirs(cand, exist_ok=True)
                self.ent_folder.insert(0, cand)
        self.current_folder = self.ent_folder.get().strip()
        for w in self.list_frm.winfo_children():
            w.destroy()
        if not self.current_folder or not os.path.exists(self.current_folder):
            return
        self.selected_file = None
        try:
            for f in sorted(os.listdir(self.current_folder)):
                if f.lower().endswith((".cht", ".disabled")):
                    self.add_cheat_card(f)
        except Exception:
            pass

    def add_cheat_card(self, filename):
        is_disabled = filename.lower().endswith(".disabled")
        color = cfg.get_color("danger") if is_disabled else cfg.get_color("success")
        card = ctk.CTkFrame(
            self.list_frm, fg_color=cfg.get_color("bg_main"),
            corner_radius=cfg.get_radius("chip"), height=40,
            border_width=cfg.get_border_width(), border_color=cfg.get_color("border")
        )
        card.pack(fill="x", pady=3, padx=6)
        card.pack_propagate(False)
        ctk.CTkFrame(card, width=4, fg_color=color, corner_radius=0).pack(side="left", fill="y", padx=(0, 12))
        ctk.CTkLabel(card, text=filename, font=("Consolas", 12, "bold"), text_color=cfg.get_color("text_main")).pack(side="left")
        ctk.CTkLabel(card, text=t("cht_disabled") if is_disabled else t("cht_enabled"), font=("Segoe UI", 10, "bold"), text_color=color).pack(side="right", padx=15)

        def on_click(e, f=filename, c=card):
            self.selected_file = os.path.join(self.current_folder, f)
            for w in self.list_frm.winfo_children():
                w.configure(fg_color=cfg.get_color("bg_main"), border_color=cfg.get_color("border"))
            c.configure(fg_color=cfg.get_color("card_hover"), border_color=cfg.get_color("accent"))
            sound_fx.play_click()

        card.bind("<Button-1>", on_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_click)

    def enable_cheat(self):
        sound_fx.play_click()
        if self.selected_file and self.selected_file.endswith(".disabled"):
            try:
                os.rename(self.selected_file, self.selected_file[:-9])
                sound_fx.play_success()
                self.refresh()
            except Exception as e:
                messagebox.showerror(t("error"), str(e))

    def disable_cheat(self):
        sound_fx.play_click()
        if self.selected_file and self.selected_file.endswith(".cht"):
            try:
                os.rename(self.selected_file, self.selected_file + ".disabled")
                sound_fx.play_success()
                self.refresh()
            except Exception as e:
                messagebox.showerror(t("error"), str(e))


# ==============================================================================
# PCSX2 TESTER, GRAVADOR REAL DE DVD & GERENCIADOR DE APPS ELF
# ==============================================================================
class EmulatorTestPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        PageHeader(self, t("tab_emu"), t("emu_info"), badge_text="PCSX2").grid(row=0, column=0, sticky="ew", pady=(0, 15))
        card = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text=t("emu_sel"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=22, pady=(22, 6))
        self.var_game = ctk.StringVar(value="—")
        self.cmb_game = ctk.CTkOptionMenu(card, variable=self.var_game, values=["—"], height=34, corner_radius=cfg.get_radius("entry"), command=lambda _: sound_fx.play_click())
        self.cmb_game.pack(fill="x", padx=22, pady=4)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=22, pady=22)
        ctk.CTkButton(btn_row, text=t("emu_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=42, corner_radius=cfg.get_radius("button"), command=self.run_test).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btn_row, text=t("emu_browse_iso"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("chip_bg"), height=42, corner_radius=cfg.get_radius("button"), command=self.run_external).pack(side="right", expand=True, fill="x", padx=(6, 0))

    def refresh(self):
        vals = [g['name'] for g in self.app.library.games] or ["No games in library"]
        self.cmb_game.configure(values=vals)
        if self.var_game.get() not in vals:
            self.var_game.set(vals[0])

    def run_test(self):
        sound_fx.play_click()
        g = next((x for x in self.app.library.games if x['name'] == self.var_game.get()), None)
        if g:
            PCSX2Integration.test_iso(g['path'], lambda e: messagebox.showerror(t("error"), e))

    def run_external(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso *.zso *.bin")])
        if f:
            PCSX2Integration.test_iso(f, lambda e: messagebox.showerror(t("error"), e))


class DvdBurnerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        PageHeader(self, t("burn_title"), "", badge_text="IMAPI2 / ISOBURN").grid(row=0, column=0, sticky="ew", pady=(0, 15))

        frm = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"), corner_radius=cfg.get_radius("card"))
        frm.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(frm, text=t("burn_iso"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        f_iso = ctk.CTkFrame(frm, fg_color="transparent")
        f_iso.pack(fill="x", padx=20)
        self.ent_iso = ctk.CTkEntry(f_iso, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_iso.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(f_iso, text=t("btn_select"), width=90, height=34, corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left")

        ctk.CTkLabel(frm, text=t("burn_drv"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(14, 5))
        self.var_drv = ctk.StringVar(value=t("burn_no_drives"))
        self.cmb_drv = ctk.CTkOptionMenu(frm, variable=self.var_drv, values=[t("burn_no_drives")], height=34, corner_radius=cfg.get_radius("entry"))
        self.cmb_drv.pack(fill="x", padx=20)

        ctk.CTkLabel(frm, text=t("burn_spd"), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(14, 5))
        self.var_spd = ctk.StringVar(value="4x (PS2 Recommended)")
        ctk.CTkOptionMenu(frm, variable=self.var_spd, values=["2x", "4x (PS2 Recommended)", "8x", "MAX"], height=34, corner_radius=cfg.get_radius("entry")).pack(fill="x", padx=20)

        self.btn_burn = ctk.CTkButton(frm, text=t("burn_btn"), font=("Segoe UI", 13, "bold"), height=42, fg_color=cfg.get_color("danger"), corner_radius=cfg.get_radius("button"), command=self.start_burn)
        self.btn_burn.pack(pady=18, padx=20, fill="x")
        self.lbl_status = ctk.CTkLabel(frm, text=t("burn_ready"), font=("Segoe UI", 11), text_color=cfg.get_color("text_muted"))
        self.lbl_status.pack(pady=(0, 4))
        self.prog = ctk.CTkProgressBar(frm, progress_color=cfg.get_color("accent"))
        self.prog.pack(fill="x", padx=20, pady=(0, 20))
        self.prog.set(0)

    def browse(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[(t("iso_files"), "*.iso")])
        if f:
            self.ent_iso.delete(0, 'end')
            self.ent_iso.insert(0, f)

    def refresh(self):
        burners = DvdBurnerWorker.list_burners()
        vals = [b['name'] for b in burners] if burners else [t("burn_no_drives")]
        self.cmb_drv.configure(values=vals)
        if self.var_drv.get() not in vals:
            self.var_drv.set(vals[0])

    def start_burn(self):
        sound_fx.play_click()
        iso = self.ent_iso.get().strip()
        if not iso or not os.path.exists(iso):
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("burn_err_select_iso"))
            return
        drv_name = self.var_drv.get()
        if drv_name == t("burn_no_drives"):
            sound_fx.play_error()
            messagebox.showerror(t("error"), t("burn_err_nomedia"))
            return
        burners = DvdBurnerWorker.list_burners()
        target_b = next((b for b in burners if b['name'] == drv_name), None)
        self.btn_burn.configure(state="disabled")
        self.prog.set(0)
        DvdBurnerWorker.burn(
            iso, target_b['id'] if target_b else drv_name, self.var_spd.get(),
            cb_prog=lambda v: self.app.after(0, lambda: self.prog.set(v)),
            cb_done=lambda _: self.app.after(0, lambda: [self.btn_burn.configure(state="normal"), sound_fx.play_success(), messagebox.showinfo(t("success"), t("burn_done"))]),
            cb_err=lambda e: self.app.after(0, lambda: [self.btn_burn.configure(state="normal"), sound_fx.play_error(), messagebox.showerror(t("burn_err_title"), str(e))])
        )


class AppsManagerPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        PageHeader(self, t("tab_apps"), "").grid(row=0, column=0, sticky="ew", pady=(0, 15))

        card = ctk.CTkFrame(self, fg_color=cfg.get_color("card_base"), corner_radius=cfg.get_radius("card"), border_width=cfg.get_border_width(), border_color=cfg.get_color("border"))
        card.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(card, text=t("app_name"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.ent_title = ctk.CTkEntry(card, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_title.pack(fill="x", padx=20)

        ctk.CTkLabel(card, text=t("app_elf"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        btn_frm = ctk.CTkFrame(card, fg_color="transparent")
        btn_frm.pack(fill="x", padx=20)
        self.ent_elf = ctk.CTkEntry(btn_frm, fg_color=cfg.get_color("bg_main"), height=34, corner_radius=cfg.get_radius("entry"))
        self.ent_elf.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(btn_frm, text=t("btn_browse"), width=90, height=34, corner_radius=cfg.get_radius("button"), command=self.browse).pack(side="left")

        ctk.CTkLabel(card, text=t("app_drv"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.var_drive = ctk.StringVar(value=t("inst_err_nodrive"))
        self.cmb_drive = ctk.CTkOptionMenu(card, variable=self.var_drive, values=[t("inst_err_nodrive")], height=34, corner_radius=cfg.get_radius("entry"))
        self.cmb_drive.pack(fill="x", padx=20)

        ctk.CTkButton(card, text=t("app_btn"), font=("Segoe UI", 12, "bold"), fg_color=cfg.get_color("accent"), height=42, corner_radius=cfg.get_radius("button"), command=self.install).pack(fill="x", padx=20, pady=24)

    def browse(self):
        sound_fx.play_click()
        f = filedialog.askopenfilename(filetypes=[("ELF Executables", "*.elf *.ELF")])
        if f:
            self.ent_elf.delete(0, 'end')
            self.ent_elf.insert(0, f)
            if not self.ent_title.get():
                self.ent_title.insert(0, os.path.splitext(os.path.basename(f))[0])

    def refresh(self):
        vals = [d['mountpoint'] for d in UsbDetector.get_removable_drives()] or [t("inst_err_nodrive")]
        self.cmb_drive.configure(values=vals)
        if self.var_drive.get() not in vals:
            self.var_drive.set(vals[0])

    def install(self):
        sound_fx.play_click()
        res = AppManager.install_elf(self.var_drive.get(), self.ent_title.get(), self.ent_elf.get())
        if res is True:
            sound_fx.play_success()
            messagebox.showinfo(t("success"), t("app_succ"))
        else:
            sound_fx.play_error()
            messagebox.showerror(t("error"), res)
