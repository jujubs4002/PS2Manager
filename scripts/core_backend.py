from __future__ import annotations

import os
import sys
import json
import time
import re
import runpy
import threading
import shutil
import psutil
import subprocess
import ctypes
import struct
import zlib
import hashlib
import urllib.request
import urllib.error
import customtkinter as ctk


def apply_console_visibility(show):
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5 if show else 0)
    except Exception:
        pass


def get_system_arch():
    """Retorna a arquitetura do Sistema Operacional Windows ('x64' ou 'x86')."""
    if os.environ.get("PROCESSOR_ARCHITECTURE") == "AMD64" or os.environ.get("PROCESSOR_ARCHITEW6432") == "AMD64":
        return "x64"
    return "x86"


def get_python_arch():
    """Retorna se o Python atual é 64-bit ou 32-bit."""
    return "x64" if sys.maxsize > 2**32 else "x86"


def is_legacy_windows():
    """Verifica se o Windows é anterior ao Windows 10 (ex: Windows 7, 8 ou 8.1)."""
    try:
        return sys.getwindowsversion().major < 10
    except Exception:
        return False


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    MEIPASS_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MEIPASS_DIR = BASE_DIR

APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PS2Manager")
os.makedirs(APP_DATA_DIR, exist_ok=True)


def get_res_path(rel_path):
    p1 = os.path.join(MEIPASS_DIR, rel_path)
    if os.path.exists(p1):
        return p1
    return os.path.join(BASE_DIR, rel_path)


def build_internal_python_cmd(*cli_args):
    """
    Garante que qualquer processo auxiliar ou script interno rode SEMPRE usando
    o interpretador Python EMBUTIDO dentro do executável (quando compilado)
    ou o próprio sys.executable atual (em desenvolvimento), NUNCA exigindo
    Python instalado no PC do usuário.
    """
    if getattr(sys, 'frozen', False):
        return [sys.executable, *cli_args]
    entry_script = os.path.join(BASE_DIR, "ps2manager.py")
    return [sys.executable, entry_script, *cli_args]


def run_internal_script(script_rel_path, run_name="__main__"):
    """Executa um script interno dentro de scripts/ usando o próprio runtime embutido."""
    target = get_res_path(script_rel_path)
    if not os.path.exists(target):
        target = os.path.join(BASE_DIR, "scripts", os.path.basename(script_rel_path))
    return runpy.run_path(target, run_name=run_name)


def run_watchdog_loop(pid, lock_file, warn_msg):
    """Modo Watchdog executado pelo próprio binário embutido (--watchdog)."""
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.CloseHandle.restype = ctypes.c_int
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    while True:
        handle = k32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            break
        exit_code = ctypes.c_ulong()
        k32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(exit_code))
        k32.CloseHandle(ctypes.c_void_p(handle))
        if exit_code.value != 259:
            break
        time.sleep(0.4)

    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except Exception:
            pass
        if warn_msg:
            try:
                ctypes.windll.user32.MessageBoxW(0, warn_msg, "PS2Manager", 0x10 | 0x40000 | 0x1000)
            except Exception:
                pass


class AppLogger:
    def __init__(self):
        self.logs = []
        self.log("PS2Manager V1.08 Core Engine Initialized.", "INFO")

    def log(self, msg, level="INFO"):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{timestamp}] [{level}] {msg}"
        self.logs.append(entry)
        if len(self.logs) > 1000:
            del self.logs[:200]
        try:
            print(entry)
        except Exception:
            pass

    def export(self):
        try:
            desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
            os.makedirs(desktop, exist_ok=True)
            filename = os.path.join(desktop, f"PS2Manager_Diagnostic_Report_{int(time.time())}.log")
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(self.logs))
            return filename
        except Exception:
            return None


sys_logger = AppLogger()

try:
    import winsound
    SOUND_SUPPORT = True
except Exception:
    SOUND_SUPPORT = False

try:
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    import pygame
    pygame.mixer.init()
    PYGAME_SUPPORT = True
except Exception:
    PYGAME_SUPPORT = False

try:
    import lz4.block
    LZ4_SUPPORT = True
except Exception:
    LZ4_SUPPORT = False

try:
    import pycdlib
    PYCDLIB_SUPPORT = True
except Exception:
    PYCDLIB_SUPPORT = False

try:
    from PIL import Image
    PIL_SUPPORT = True
except Exception:
    PIL_SUPPORT = False

try:
    import win32com.client
    WIN32COM_SUPPORT = True
except Exception:
    WIN32COM_SUPPORT = False

APP_NAME = "PS2 MANAGER"
APP_VERSION = "V1.08"
VERSION_COLOR_CODE = '8'

THEMES = {
    "Midnight Neon": {
        "bg_main": "#060913", "bg_sidebar": "#04060C", "card_base": "#0E1525",
        "card_hover": "#16213A", "accent": "#3B82F6", "accent_hover": "#2563EB",
        "text_main": "#F8FAFC", "text_muted": "#7C8BA1", "success": "#10B981",
        "warning": "#F59E0B", "danger": "#EF4444", "border": "#1E2D4A",
        "chip_bg": "#152036", "highlight": "#22D3EE"
    },
    "Dark": {
        "bg_main": "#090D16", "bg_sidebar": "#05080F", "card_base": "#111827",
        "card_hover": "#1B253B", "accent": "#2563EB", "accent_hover": "#1D4ED8",
        "text_main": "#F1F5F9", "text_muted": "#94A3B8", "success": "#10B981",
        "warning": "#F59E0B", "danger": "#EF4444", "border": "#1F2937",
        "chip_bg": "#1E293B", "highlight": "#38BDF8"
    },
    "Ocean": {
        "bg_main": "#071124", "bg_sidebar": "#040A17", "card_base": "#10213E",
        "card_hover": "#183059", "accent": "#00B4D8", "accent_hover": "#0096C7",
        "text_main": "#F0F9FF", "text_muted": "#8DA4C4", "success": "#06D6A0",
        "warning": "#FFD166", "danger": "#EF476F", "border": "#1E3A66",
        "chip_bg": "#162C50", "highlight": "#72EFDD"
    },
    "Obsidian": {
        "bg_main": "#09090B", "bg_sidebar": "#050507", "card_base": "#141418",
        "card_hover": "#1F1F26", "accent": "#E11D48", "accent_hover": "#BE123C",
        "text_main": "#FAFAFA", "text_muted": "#A1A1AA", "success": "#22C55E",
        "warning": "#EAB308", "danger": "#EF4444", "border": "#27272A",
        "chip_bg": "#1E1E24", "highlight": "#FB7185"
    },
    "Light": {
        "bg_main": "#F1F5F9", "bg_sidebar": "#E2E8F0", "card_base": "#FFFFFF",
        "card_hover": "#F8FAFC", "accent": "#0284C7", "accent_hover": "#0369A1",
        "text_main": "#0F172A", "text_muted": "#64748B", "success": "#059669",
        "warning": "#D97706", "danger": "#DC2626", "border": "#CBD5E1",
        "chip_bg": "#E2E8F0", "highlight": "#0369A1"
    }
}

ANIM_STYLES = ["Slide", "Rise", "Zoom", "Step"]

# Idiomas oficiais: EN=English, PT_BR=Português (Brasil), PT=Português (Portugal), ES=Español, RU=Русский, JA=日本語
LANGS = {"EN": 0, "PT_BR": 1, "PT": 2, "ES": 3, "RU": 4, "JA": 5}

TRANSLATIONS = {
    # Navegação Principal e Sub-menus
    "nav_sec_main": ["MAIN WORKSPACE", "ÁREA PRINCIPAL", "ÁREA PRINCIPAL", "ÁREA PRINCIPAL", "ОСНОВНОЕ МЕНЮ", "メインメニュー"],
    "nav_sec_tools": ["SPECIALIST TOOLS", "FERRAMENTAS AVANÇADAS", "FERRAMENTAS AVANÇADAS", "HERRAMIENTAS AVANZADAS", "ИНСТРУМЕНТЫ", "高度なツール"],
    "tab_dash": ["DASHBOARD", "PAINEL", "PAINEL", "PANEL", "ПАНЕЛЬ", "ダッシュボード"],
    "tab_lib": ["LIBRARY", "BIBLIOTECA", "BIBLIOTECA", "BIBLIOTECA", "БИБЛИОТЕКА", "ライブラリ"],
    "tab_install": ["INSTALL TO USB", "INSTALAR NO PENDRIVE", "INSTALAR NA PEN USB", "INSTALAR EN USB", "УСТАНОВКА НА USB", "USBへインストール"],
    "tab_batch": ["BATCH QUEUE", "FILA EM LOTE", "FILA POR LOTES", "COLA POR LOTES", "ПАКЕТНАЯ ОЧЕРЕДЬ", "一括キュー"],
    "tab_usb": ["USB & DEFRAG", "USB & OTIMIZADOR", "USB & OTIMIZADOR", "USB Y OPTIMIZADOR", "USB И ДЕФРАГ", "USB＆最適化"],
    "tab_opl_cfg": ["OPL MODES & GSM", "MODOS OPL & GSM", "MODOS OPL & GSM", "MODOS OPL Y GSM", "РЕЖИМЫ OPL И GSM", "OPL設定＆GSM"],
    "tab_art": ["ART SCRAPER 2.0", "ARTES DO OPL 2.0", "ARTES DO OPL 2.0", "ARTES OPL 2.0", "ОБЛОЖКИ OPL 2.0", "OPLアート取得 2.0"],
    "tab_mc": ["MEMORY CARD", "MEMORY CARD", "CARTÃO DE MEMÓRIA", "MEMORY CARD", "КАРТА ПАМЯТИ", "メモリーカード"],
    "tab_emu": ["PCSX2 EMULATOR", "EMULADOR PCSX2", "EMULADOR PCSX2", "EMULADOR PCSX2", "ЭМУЛЯТОР PCSX2", "PCSX2エミュレータ"],
    "tab_burn": ["BURN DVD", "GRAVAR DVD", "GRAVAR DVD", "GRABAR DVD", "ЗАПИСЬ DVD", "DVD書き込み"],
    "sub_clone": ["  ↳ CLONE DRIVE", "  ↳ CLONAR PENDRIVE", "  ↳ CLONAR UNIDADE", "  ↳ CLONAR UNIDAD", "  ↳ КЛОНИРОВАТЬ ДИСК", "  ↳ ドライブ複製"],
    "tab_mig": ["DISK CLONE & FORMAT", "CLONAR & FORMATAR", "CLONAR & FORMATAR", "CLONAR Y FORMATEAR", "КЛОН И ФОРМАТ", "複製＆フォーマット"],
    "tab_apps": ["OPL APPS (.ELF)", "OPL APPS (.ELF)", "OPL APPS (.ELF)", "OPL APPS (.ELF)", "OPL ПРИЛОЖЕНИЯ", "OPLアプリ (.ELF)"],
    "tab_iso": ["ISO / ZSO STUDIO", "EXTRAIR / ZSO / ISO", "EXTRAIR / ZSO / ISO", "ESTUDIO ISO / ZSO", "СТУДИЯ ISO / ZSO", "ISO / ZSOスタジオ"],
    "tab_pops": ["PS1 POPSTARTER (.VCD)", "PS1 POPSTARTER (.VCD)", "PS1 POPSTARTER (.VCD)", "PS1 POPSTARTER (.VCD)", "PS1 POPSTARTER (.VCD)", "PS1 POPSTARTER (.VCD)"],
    "tab_rip": ["DISC RIP & ANALYZE", "DISCO FÍSICO (RIP)", "DISCO FÍSICO (RIP)", "DISCO FÍSICO (RIP)", "ПРИВОД DVD/CD", "光学ディスク抽出・分析"],
    "tab_util": ["USB UTIL (SPLIT)", "USB UTIL (DIVIDIR)", "USB UTIL (DIVIDIR)", "USB UTIL (DIVIDIR)", "USB UTIL (РАЗДЕЛЕНИЕ)", "USB UTIL（分割）"],
    "tab_disc": ["DISC ANALYZER", "ANALISADOR DE DISCO", "ANALISADOR DE DISCO", "ANALIZADOR DE DISCO", "АНАЛИЗАТОР ДИСКА", "ディスク分析"],
    "tab_set": ["SETTINGS", "CONFIGURAÇÕES", "DEFINIÇÕES", "AJUSTES", "НАСТРОЙКИ", "設定"],
    "tab_more": ["MORE TOOLS  ➔", "MAIS FERRAMENTAS  ➔", "MAIS FERRAMENTAS  ➔", "MÁS HERRAMIENTAS  ➔", "ЕЩЁ ИНСТРУМЕНТЫ  ➔", "その他のツール  ➔"],
    "tab_patcher": ["16:9 / NTSC / PATCHER", "PATCHER 16:9 & NTSC", "PATCHER 16:9 & NTSC", "PARCHE 16:9 Y NTSC", "ПАТЧЕР 16:9 И NTSC", "16:9・NTSCパッチャー"],
    "tab_cht": ["CHEAT ENGINE (.CHT)", "CRIADOR DE CHEATS", "CRIADOR DE CHEATS", "GESTOR DE CHEATS", "ЧИТЫ ДЛЯ OPL", "チート管理 (.CHT)"],
    "tab_apa": ["APA HDD EXPLORER", "EXPLORADOR HDD APA", "EXPLORADOR HDD APA", "EXPLORADOR HDD APA", "ПРОВОДНИК APA HDD", "APA HDDエクスプローラー"],

    # Botões Gerais
    "btn_back": ["◀  BACK TO MAIN", "◀  VOLTAR AO INÍCIO", "◀  VOLTAR AO INÍCIO", "◀  VOLVER AL INICIO", "◀  НАЗАД В МЕНЮ", "◀  メインに戻る"],
    "btn_select": ["SELECT", "SELECIONAR", "SELECIONAR", "SELECCIONAR", "ВЫБРАТЬ", "選択"],
    "btn_browse": ["BROWSE", "PROCURAR", "PROCURAR", "EXAMINAR", "ОБЗОР", "参照"],
    "btn_cancel": ["CANCEL", "CANCELAR", "CANCELAR", "CANCELAR", "ОТМЕНА", "キャンセル"],
    "btn_close": ["CLOSE", "FECHAR", "FECHAR", "CERRAR", "ЗАКРЫТЬ", "閉じる"],
    "btn_refresh": ["REFRESH", "ATUALIZAR", "ATUALIZAR", "ACTUALIZAR", "ОБНОВИТЬ", "更新"],
    "btn_save": ["SAVE", "SALVAR", "GUARDAR", "GUARDAR", "СОХРАНИТЬ", "保存"],
    "btn_open_folder": ["OPEN FOLDER", "ABRIR PASTA", "ABRIR PASTA", "ABRIR CARPETA", "ОТКРЫТЬ ПАПКУ", "フォルダを開く"],
    "confirm": ["Confirm", "Confirmar", "Confirmar", "Confirmar", "Подтверждение", "確認"],
    "success": ["Success", "Sucesso", "Sucesso", "Éxito", "Успешно", "成功"],
    "error": ["Error", "Erro", "Erro", "Error", "Ошибка", "エラー"],
    "warning": ["Warning", "Aviso", "Aviso", "Aviso", "Предупреждение", "警告"],
    "warn_title": ["Important Warning", "Aviso Importante", "Aviso Importante", "Aviso Importante", "Важное предупреждение", "重要なお知らせ"],

    # Dashboard
    "dash_sub": ["Overview of your PlayStation 2 library, connected OPL drives, and quick actions.", "Visão geral da sua biblioteca de PS2, pendrives OPL conectados e atalhos rápidos.", "Visão geral da sua biblioteca PS2, unidades OPL ligadas e atalhos rápidos.", "Resumen de tu biblioteca de PS2, unidades OPL conectadas y accesos rápidos.", "Обзор вашей библиотеки PS2, подключенных накопителей OPL и быстрых действий.", "PS2ライブラリ、接続中のOPLドライブ、クイックアクションの概要。"],
    "dash_games": ["LIBRARY GAMES", "JOGOS NA BIBLIOTECA", "JOGOS NA BIBLIOTECA", "JUEGOS EN BIBLIOTECA", "ИГР В БИБЛИОТЕКЕ", "登録済みゲーム"],
    "dash_usb": ["CONNECTED DRIVES", "UNIDADES CONECTADAS", "UNIDADES LIGADAS", "UNIDADES CONECTADAS", "ПОДКЛЮЧЕННЫЕ ДИСКИ", "接続ドライブ"],
    "dash_size": ["TOTAL LIBRARY SIZE", "TAMANHO DA BIBLIOTECA", "TAMANHO DA BIBLIOTECA", "TAMAÑO TOTAL", "ОБЩИЙ РАЗМЕР", "合計容量"],
    "dash_console": ["CONSOLE PROFILE", "MEU CONSOLE PS2", "A MINHA CONSOLA PS2", "PERFIL CONSOLA", "ПРОФИЛЬ КОНСОЛИ", "本体プロファイル"],
    "dash_quick": ["QUICK ACTIONS", "ATALHOS RÁPIDOS", "ATALHOS RÁPIDOS", "ACCIONES RÁPIDAS", "БЫСТРЫЕ ДЕЙСТВИЯ", "クイックアクション"],
    "dash_storage": ["CONNECTED OPL STORAGE", "DISPOSITIVOS OPL CONECTADOS", "DISPOSITIVOS OPL LIGADOS", "UNIDADES OPL CONECTADAS", "ПОДКЛЮЧЕННЫЕ НАКОПИТЕЛИ OPL", "接続中のOPLストレージ"],
    "dash_no_usb": ["Connect a FAT32 or exFAT USB drive to manage OPL games.", "Conecte um pendrive ou HD USB (FAT32 / exFAT) para gerenciar seus jogos do OPL.", "Ligue uma pen USB ou disco (FAT32 / exFAT) para gerir os seus jogos do OPL.", "Conecta una unidad USB FAT32 o exFAT para gestionar juegos OPL.", "Подключите USB-накопитель FAT32 или exFAT для управления играми OPL.", "FAT32またはexFATのUSBドライブを接続してOPLゲームを管理します。"],

    # Biblioteca
    "lib_sub": ["Manage your PS2 ISO/ZSO games, inspect IDs, configure GSM, or send to USB.", "Gerencie seus jogos ISO/ZSO, verifique IDs, ajuste GSM ou envie para o pendrive.", "Gira os seus jogos ISO/ZSO, verifique IDs, ajuste GSM ou envie para a pen USB.", "Gestiona tus juegos ISO/ZSO, revisa IDs, ajusta GSM o envía al USB.", "Управляйте играми ISO/ZSO, проверяйте ID, настраивайте GSM или копируйте на USB.", "ISO/ZSOゲームの管理、ID確認、GSM設定、USB転送を行います。"],
    "lib_scan": ["+ SCAN FOLDER", "+ ESCANEAR PASTA", "+ VERIFICAR PASTA", "+ ESCANEAR CARPETA", "+ СКАНИРОВАТЬ ПАПКУ", "+ フォルダをスキャン"],
    "lib_add_iso": ["+ ADD FILE", "+ ADICIONAR JOGO", "+ ADICIONAR JOGO", "+ AÑADIR JUEGO", "+ ДОБАВИТЬ ФАЙЛ", "+ ゲーム追加"],
    "lib_search": ["Search game by title, ID, or region...", "Pesquisar jogo por nome, ID ou região...", "Pesquisar jogo por nome, ID ou região...", "Buscar juego por título, ID o región...", "Поиск по названию, ID или региону...", "タイトル・ID・リージョンで検索..."],
    "lib_empty": ["No games in library yet. Click '+ SCAN FOLDER' to add your ISOs/ZSOs.", "Nenhum jogo na biblioteca ainda. Clique em '+ ESCANEAR PASTA' para adicionar suas ISOs.", "Nenhum jogo na biblioteca. Clique em '+ VERIFICAR PASTA' para adicionar as suas ISOs.", "No hay juegos en la biblioteca. Haz clic en '+ ESCANEAR CARPETA'.", "Библиотека пуста. Нажмите '+ СКАНИРОВАТЬ ПАПКУ' для добавления ISO.", "ライブラリにゲームがありません。「+ フォルダをスキャン」から追加してください。"],
    "lib_scan_done": ["Scan complete!", "Escaneamento concluído!", "Verificação concluída!", "¡Escaneo completado!", "Сканирование завершено!", "スキャン完了！"],
    "lib_btn_close": ["CLOSE", "FECHAR", "FECHAR", "CERRAR", "ЗАКРЫТЬ", "閉じる"],
    "lib_btn_test": ["TEST ON PCSX2", "TESTAR NO PCSX2", "TESTAR NO PCSX2", "PROBAR EN PCSX2", "ТЕСТ В PCSX2", "PCSX2でテスト"],
    "lib_btn_inst": ["INSTALL TO USB", "INSTALAR NO PENDRIVE", "INSTALAR NA PEN USB", "INSTALAR EN USB", "УСТАНОВИТЬ НА USB", "USBに転送"],
    "lib_btn_cfg": ["OPL MODES / CFG", "MODOS OPL / CFG", "MODOS OPL / CFG", "MODOS OPL / CFG", "РЕЖИМЫ OPL / CFG", "OPLモード設定"],
    "lib_btn_rem": ["REMOVE", "REMOVER", "REMOVER", "ELIMINAR", "УДАЛИТЬ", "削除"],
    "msg_remove_confirm": ["Do you want to remove this game from the library view?", "Deseja remover este jogo da visualização da biblioteca?", "Deseja remover este jogo da biblioteca?", "¿Deseas eliminar este juego de la biblioteca?", "Удалить эту игру из списка библиотеки?", "このゲームをライブラリ表示から削除しますか？"],
    "cfg_vid": ["Video Output Mode:", "Modo de Saída de Vídeo:", "Modo de Saída de Vídeo:", "Modo de Video:", "Режим видеовыхода:", "ビデオ出力モード:"],
    "cfg_res": ["GSM Resolution Override:", "Resolução Forçada GSM:", "Resolução Forçada GSM:", "Resolución GSM:", "Разрешение GSM:", "GSM解像度指定:"],
    "cfg_save": ["SAVE CONFIG", "SALVAR CONFIG", "GUARDAR CONFIG", "GUARDAR CFG", "СОХРАНИТЬ", "設定保存"],
    "cfg_succ": ["Config saved successfully at:", "Configuração salva com sucesso em:", "Configuração guardada com sucesso em:", "Configuración guardada en:", "Конфигурация успешно сохранена в:", "設定が保存されました:"],

    # Instalação unificada no USB (1-Clique, Lote e USBUtil)
    "inst_sub": ["Install single games, process a batch queue, or split >4GB ISOs for FAT32 drives.", "Instale jogos individuais, processe vários em fila ou divida ISOs >4GB para FAT32.", "Instale jogos individuais, processe uma fila ou divida ISOs >4GB para FAT32.", "Instala juegos individuales, procesa colas por lotes o divide ISOs >4GB para FAT32.", "Одиночная установка, пакетная очередь или разделение ISO >4 ГБ для FAT32.", "単体インストール、一括キュー処理、FAT32用4GB超ISO分割を統合。"],
    "inst_mode_single": ["1-Click Install", "Instalação 1-Clique", "Instalação 1-Clique", "Instalación 1-Clic", "В 1 клик", "1クリック転送"],
    "inst_mode_batch": ["Batch Queue", "Fila em Lote", "Fila por Lotes", "Cola por Lotes", "Очередь", "一括キュー"],
    "inst_mode_split": ["USBUtil Split (FAT32)", "Dividir >4GB (USBUtil)", "Dividir >4GB (USBUtil)", "Dividir >4GB (USBUtil)", "USBUtil (FAT32)", "USBUtil分割"],
    "inst_step1": ["1. Select ISO / Game File:", "1. Selecione o arquivo ISO / Jogo:", "1. Selecione o ficheiro ISO / Jogo:", "1. Seleccione archivo ISO / Juego:", "1. Выберите файл ISO / Игру:", "1. ISO / ゲームファイルを選択:"],
    "inst_step2": ["2. Game Title (Max 32 chars):", "2. Nome do Jogo (Máx 32 caracteres):", "2. Nome do Jogo (Máx 32 caracteres):", "2. Nombre del Juego (Máx 32):", "2. Название игры (до 32 симв.):", "2. ゲーム名（最大32文字）:"],
    "inst_step3": ["3. Target USB Drive:", "3. Dispositivo USB de Destino:", "3. Dispositivo USB de Destino:", "3. Unidad USB Destino:", "3. Целевой USB накопитель:", "3. 対象USBドライブ:"],
    "inst_auto_art": ["Automatically download cover art for OPL", "Baixar capa automaticamente para o OPL", "Descarregar capa automaticamente para o OPL", "Descargar carátula para OPL automáticamente", "Автоматически скачать обложку для OPL", "OPL用ジャケット画像を自動取得"],
    "inst_btn": ["INSTALL GAME TO USB", "INICIAR INSTALAÇÃO NO PENDRIVE", "INICIAR INSTALAÇÃO NA PEN USB", "INSTALAR JUEGO EN USB", "УСТАНОВИТЬ ИГРУ НА USB", "USBにゲームをインストール"],
    "inst_ready": ["Ready to install.", "Pronto para instalar.", "Pronto a instalar.", "Listo para instalar.", "Готов к установке.", "インストールの準備ができました。"],
    "inst_err_select": ["Please select an ISO file and target USB drive.", "Selecione o arquivo ISO e o pendrive de destino.", "Selecione o ficheiro ISO e a pen USB de destino.", "Seleccione el archivo ISO y la unidad USB.", "Выберите файл ISO и целевой накопитель USB.", "ISOファイルと対象USBドライブを選択してください。"],
    "inst_err_nodrive": ["No USB drive detected", "Nenhum pendrive detectado", "Nenhuma pen USB detetada", "Ningún USB detectado", "USB не обнаружен", "USBドライブ未検出"],
    "inst_starting": ["Starting installation to USB drive...", "Iniciando instalação no pendrive...", "A iniciar a instalação na pen USB...", "Iniciando instalación en USB...", "Запуск установки на USB...", "USBへのインストールを開始中..."],
    "inst_done": ["Installation completed successfully!", "Instalação concluída com sucesso!", "Instalação concluída com sucesso!", "¡Instalación completada con éxito!", "Установка успешно завершена!", "インストールが正常に完了しました！"],
    "inst_succ_msg": ["Game installed successfully to USB drive!", "Jogo instalado com sucesso no pendrive!", "Jogo instalado com sucesso na pen USB!", "¡Juego instalado con éxito en USB!", "Игра успешно установлена на USB!", "ゲームがUSBに正常にインストールされました！"],
    "inst_err_fail": ["Installation failed:", "Falha na instalação:", "Falha na instalação:", "Fallo en la instalación:", "Ошибка установки:", "インストールに失敗しました:"],

    # Fila em Lote
    "batch_add": ["+ ADD FILES", "+ ADICIONAR ISOS", "+ ADICIONAR ISOS", "+ AÑADIR ISOS", "+ ДОБАВИТЬ ФАЙЛЫ", "+ ファイル追加"],
    "batch_folder": ["+ ADD FOLDER", "+ ADICIONAR PASTA", "+ ADICIONAR PASTA", "+ AÑADIR CARPETA", "+ ДОБАВИТЬ ПАПКУ", "+ フォルダ追加"],
    "batch_clear": ["CLEAR", "LIMPAR", "LIMPAR", "LIMPIAR", "ОЧИСТИТЬ", "クリア"],
    "batch_start": ["PROCESS ENTIRE QUEUE", "INSTALAR TODA A FILA", "INSTALAR TODA A FILA", "PROCESAR TODA LA COLA", "УСТАНОВИТЬ ВСЮ ОЧЕРЕДЬ", "キューを一括インストール"],
    "batch_prog_total": ["Overall Queue Progress:", "Progresso Geral da Fila:", "Progresso Geral da Fila:", "Progreso General de la Cola:", "Общий прогресс очереди:", "キュー全体の進捗:"],
    "batch_prog_cur": ["Current Game Progress:", "Progresso do Jogo Atual:", "Progresso do Jogo Atual:", "Progreso del Juego Actual:", "Прогресс текущей игры:", "現在のゲームの進捗:"],
    "batch_empty": ["Queue is empty. Add ISO/ZSO files or folders above.", "Fila vazia. Adicione arquivos ISO/ZSO ou pastas acima.", "Fila vazia. Adicione ficheiros ISO/ZSO ou pastas acima.", "Cola vacía. Agregue archivos o carpetas arriba.", "Очередь пуста. Добавьте файлы или папки выше.", "キューは空です。上部のボタンからファイルまたはフォルダを追加してください。"],
    "batch_warn_empty": ["Please add games to the queue first.", "Adicione jogos à fila primeiro.", "Adicione jogos à fila primeiro.", "Agregue juegos a la cola primero.", "Сначала добавьте игры в очередь.", "最初にキューにゲームを追加してください。"],
    "batch_err_nodrive": ["Please select a target USB drive.", "Selecione a unidade USB de destino.", "Selecione a unidade USB de destino.", "Seleccione la unidad USB de destino.", "Выберите целевой накопитель USB.", "対象USBドライブを選択してください。"],
    "batch_done_title": ["Batch Complete", "Fila Finalizada", "Fila Finalizada", "Cola Completada", "Очередь завершена", "一括処理完了"],
    "batch_done_msg": ["All queued games have been processed!", "Todos os jogos da fila foram processados!", "Todos os jogos da fila foram processados!", "¡Todos los juegos han sido procesados!", "Все игры из очереди успешно обработаны!", "キュー内のすべてのゲームが処理されました！"],

    # USB Manager & Otimizador Anti-Tela Preta (Feature 1)
    "usb_sub": ["Manage OPL folder structure, verify MD5/SHA-1 hashes, and fix USB game fragmentation.", "Gerencie pastas do OPL, verifique integridade MD5/SHA-1 e corrija fragmentação (Anti-Tela Preta).", "Gira pastas do OPL, verifique hashes MD5/SHA-1 e corrija a fragmentação USB (Anti-Ecrã Preto).", "Gestiona carpetas OPL, verifica hashes y repara la fragmentación USB (Anti-Pantalla Negra).", "Структура папок OPL, проверка MD5/SHA-1 и дефрагментация игр (защита от черного экрана).", "OPLフォルダ管理、ハッシュ検証、USB断片化の解消（ブラックスクリーン対策）。"],
    "usb_mode_drives": ["OPL Drives & Folders", "Unidades & Estrutura OPL", "Unidades & Estrutura OPL", "Unidades y Carpetas OPL", "Диски и папки OPL", "ドライブ＆OPL構造"],
    "usb_mode_defrag": ["Anti-Black Screen (Defrag & Hash)", "Anti-Tela Preta (Fragmentação & Hash)", "Anti-Ecrã Preto (Fragmentação & Hash)", "Anti-Pantalla Negra (Defrag y Hash)", "Дефрагментация и Хеш", "断片化チェック＆最適化"],
    "usb_ref": ["REFRESH", "ATUALIZAR", "ATUALIZAR", "ACTUALIZAR", "ОБНОВИТЬ", "更新"],
    "usb_fix_btn": ["CREATE / FIX OPL FOLDERS", "CRIAR / REPARAR PASTAS OPL", "CRIAR / REPARAR PASTAS OPL", "CREAR CARPETAS OPL", "СОЗДАТЬ ПАПКИ OPL", "OPLフォルダを作成・修復"],
    "usb_fix_done": ["OPL folders verified & created!", "Estrutura de pastas do OPL criada/verificada com sucesso!", "Estrutura de pastas do OPL criada/verificada com sucesso!", "¡Carpetas OPL verificadas con éxito!", "Папки OPL успешно созданы!", "OPLフォルダ構造を作成・確認しました！"],
    "notif_usb_connected": ["USB Device Connected", "Dispositivo USB Conectado", "Dispositivo USB Ligado", "Dispositivo USB Conectado", "USB-накопитель подключен", "USBデバイスが接続されました"],
    "defrag_scan_btn": ["SCAN USB FRAGMENTATION", "ANALISAR FRAGMENTAÇÃO", "ANALISAR FRAGMENTAÇÃO", "ANALIZAR FRAGMENTACIÓN", "ПРОВЕРИТЬ ФРАГМЕНТАЦИЮ", "断片化をスキャン"],
    "defrag_fix_one": ["OPTIMIZE SELECTED", "DESFRAGMENTAR SELECIONADO", "DESFRAGMENTAR SELECIONADO", "OPTIMIZAR SELECCIONADO", "ОПТИМИЗИРОВАТЬ ВЫБРАННЫЙ", "選択項目を最適化"],
    "defrag_fix_all": ["OPTIMIZE ALL FRAGMENTED", "OTIMIZAR TODOS FRAGMENTADOS", "OTIMIZAR TODOS FRAGMENTADOS", "OPTIMIZAR TODOS", "ОПТИМИЗИРОВАТЬ ВСЕ", "断片化ファイルを一括最適化"],
    "defrag_hash_btn": ["VERIFY HASH (MD5/SHA1)", "VERIFICAR HASH (MD5/SHA1)", "VERIFICAR HASH (MD5/SHA1)", "VERIFICAR HASH (MD5/SHA1)", "ПРОВЕРИТЬ ХЕШ (MD5/SHA1)", "ハッシュ検証 (MD5/SHA1)"],
    "defrag_ok": ["CONTIGUOUS (1 Frag)", "ÍNTEGRO (1 Frag)", "ÍNTEGRO (1 Frag)", "ÓPTIMO (1 Frag)", "ЦЕЛЬНЫЙ (1 фрагм.)", "連続領域 (断片なし)"],
    "defrag_bad": ["FRAGMENTED ({n} Frags - Black Screen Risk!)", "FRAGMENTADO ({n} Frags - Risco Tela Preta!)", "FRAGMENTADO ({n} Frags - Risco Ecrã Preto!)", "FRAGMENTADO ({n} Frags - ¡Riesgo!)", "ФРАГМЕНТИРОВАН ({n} фрагм.!)", "断片化 ({n}個 - 起動不良の恐れ)"],
    "defrag_empty": ["Select a USB drive or OPL folder and click Scan to inspect game extents.", "Selecione o pendrive/pasta OPL acima e clique em Analisar Fragmentação.", "Selecione a pen USB/pasta OPL acima e clique em Analisar Fragmentação.", "Selecciona la unidad USB y haz clic en Analizar Fragmentación.", "Выберите USB-диск выше и нажмите Проверить фрагментацию.", "USBドライブを選択して「断片化をスキャン」をクリックしてください。"],
    "defrag_done": ["Optimization finished! Contiguous clusters rewritten.", "Otimização concluída! Arquivo regravado em blocos contínuos.", "Otimização concluída! Ficheiro regravado em blocos contínuos.", "¡Optimización completada en bloques contiguos!", "Оптимизация завершена! Кластеры перезаписаны последовательно.", "最適化が完了しました！連続クラスタとして再配置されました。"],

    # Editor de Compatibilidade & Modos do OPL (Feature 2)
    "opl_cfg_sub": ["Configure per-game OPL Compatibility Modes (1–6), DMA, GSM HD Upscaling, and Widescreen.", "Configure Modos de Compatibilidade (1 a 6), DMA, GSM (480p/720p/1080i) e Widescreen por jogo.", "Configure Modos de Compatibilidade (1 a 6), DMA, GSM (480p/720p/1080i) e Widescreen por jogo.", "Configura Modos OPL (1 a 6), DMA, GSM HD y Widescreen para cada juego.", "Настройка режимов совместимости OPL (1–6), DMA, GSM и широкоэкранного режима.", "ゲーム別のOPL互換モード(1〜6)、DMA、GSM解像度、ワイド画面を設定します。"],
    "opl_target_root": ["OPL Drive / Folder:", "Pendrive / Pasta do OPL:", "Pen USB / Pasta do OPL:", "Unidad / Carpeta OPL:", "Диск / Папка OPL:", "OPLドライブ / フォルダ:"],
    "opl_game_sel": ["Detected Game:", "Jogo Detectado:", "Jogo Detetado:", "Juego Detectado:", "Обнаруженная игра:", "対象ゲーム:"],
    "opl_preset_lbl": ["Community Fix Preset:", "Preset de Correção Rápida:", "Predefinição de Correção:", "Preset de Compatibilidad:", "Готовый пресет:", "互換プリセット:"],
    "opl_modes_hdr": ["OPL COMPATIBILITY MODES (MODES 1–6)", "MODOS DE COMPATIBILIDADE DO OPL (1 A 6)", "MODOS DE COMPATIBILIDADE DO OPL (1 A 6)", "MODOS DE COMPATIBILIDAD OPL (1 A 6)", "РЕЖИМЫ СОВМЕСТИМОСТИ OPL (1–6)", "OPL互換性モード (モード1〜6)"],
    "opl_m1": ["Mode 1 — Accurate Reads (Fixes audio/loading glitches)", "Modo 1 — Leituras Precisas (Corrige falhas de áudio/loading)", "Modo 1 — Leituras Precisas (Corrige falhas de áudio/loading)", "Modo 1 — Lecturas Precisas (Corrige audio/carga)", "Режим 1 — Точное чтение (исправляет звук/загрузку)", "モード1 — 正確な読み込み（音声・ロード不具合修正）"],
    "opl_m2": ["Mode 2 — Synchronous Mode (Fixes freezes in cutscenes)", "Modo 2 — Modo Síncrono (Evita travamentos em cutscenes)", "Modo 2 — Modo Síncrono (Evita bloqueios em cutscenes)", "Modo 2 — Modo Síncrono (Evita cuelgues en videos)", "Режим 2 — Синхронный режим (против зависаний)", "モード2 — 同期モード（ムービーフリーズ対策）"],
    "opl_m3": ["Mode 3 — Unhook Syscalls (Fixes black screen after boot)", "Modo 3 — Desvincular Syscalls (Corrige tela preta pós-boot)", "Modo 3 — Desvincular Syscalls (Corrige ecrã preto pós-boot)", "Modo 3 — Desvincular Syscalls (Corrige pantalla negra)", "Режим 3 — Сброс Syscalls (против черного экрана)", "モード3 — Syscall解除（起動直後の暗転対策）"],
    "opl_m4": ["Mode 4 — Skip Videos / PSS (Fixes FMV stutter on USB)", "Modo 4 — Pular Vídeos PSS (Evita engasgos em CGs via USB)", "Modo 4 — Saltar Vídeos PSS (Evita lentidão em CGs via USB)", "Modo 4 — Saltar Videos PSS (Fluidez en USB)", "Режим 4 — Пропуск видео PSS (для медленных USB)", "モード4 — PSSムービースキップ（USB再生カクつき対策）"],
    "opl_m5": ["Mode 5 — Emulate DVD-DL (For DVD9 games like GoW II / GT4)", "Modo 5 — Emular DVD-DL (Para jogos DVD9 como GoW II / GT4)", "Modo 5 — Emular DVD-DL (Para jogos DVD9 como GoW II / GT4)", "Modo 5 — Emular DVD-DL (Para juegos DVD9: GoW II / GT4)", "Режим 5 — Эмуляция DVD-DL (для игр DVD9)", "モード5 — DVD-DLエミュレート（GoW2・GT4等のDVD9用）"],
    "opl_m6": ["Mode 6 — Disable IGR (In-Game Reset compatibility)", "Modo 6 — Desativar IGR (Corrige jogos incompatíveis com Reset)", "Modo 6 — Desativar IGR (Corrige incompatibilidade com Reset)", "Modo 6 — Desactivar IGR (Reinicio en juego)", "Режим 6 — Отключить IGR (совместимость)", "モード6 — IGR無効化（ゲーム内リセット競合回避）"],
    "opl_gsm_hdr": ["GSM VIDEO UPSCALER & WIDESCREEN", "VÍDEO GSM, WIDESCREEN & DMA", "VÍDEO GSM, WIDESCREEN & DMA", "VIDEO GSM, WIDESCREEN Y DMA", "ВИДЕО GSM, 16:9 И DMA", "GSM映像出力・ワイド画面・DMA"],
    "opl_enable_gsm": ["Enable GSM Video Override ($EnableGSM)", "Ativar Forçamento de Vídeo GSM ($EnableGSM)", "Ativar Forçamento de Vídeo GSM ($EnableGSM)", "Activar Video GSM ($EnableGSM)", "Включить GSM видео ($EnableGSM)", "GSM映像強制出力を有効化 ($EnableGSM)"],
    "opl_gsm_vmode": ["Target GSM Video Mode:", "Resolução / Sistema GSM:", "Resolução / Sistema GSM:", "Modo de Video GSM:", "Видеорежим GSM:", "GSM出力解像度モード:"],
    "opl_field_fix": ["GSM Field Flipping / VSync Fix", "Correção de Campo Entrelaçado (Field Fix)", "Correção de Campo Entrelaçado (Field Fix)", "Corrección de Campo GSM", "Исправление полей GSM", "GSMフィールド反転補正"],
    "opl_wide_chk": ["Enable PS2RD Widescreen / Cheats ($EnableCheat + 16:9 Flag)", "Ativar Flag Widescreen 16:9 + PS2RD ($EnableCheat)", "Ativar Flag Widescreen 16:9 + PS2RD ($EnableCheat)", "Activar Widescreen 16:9 + PS2RD ($EnableCheat)", "Включить 16:9 Widescreen + PS2RD ($EnableCheat)", "16:9ワイド設定＆PS2RD有効化 ($EnableCheat)"],
    "opl_dma_lbl": ["Transfer DMA Mode (HDD/SMB):", "Modo de Transferência DMA:", "Modo de Transferência DMA:", "Modo DMA:", "Режим DMA:", "DMA転送モード:"],
    "opl_load_btn": ["LOAD EXISTING .CFG", "CARREGAR .CFG", "CARREGAR .CFG", "CARGAR .CFG", "ЗАГРУЗИТЬ .CFG", "既存.CFG読込"],
    "opl_save_btn": ["SAVE GAME .CFG TO OPL", "SALVAR .CFG NO OPL", "GUARDAR .CFG NO OPL", "GUARDAR .CFG EN OPL", "СОХРАНИТЬ .CFG В OPL", "OPL用.CFGを保存"],

    # PS1 POPStarter (.BIN/.CUE -> .VCD em Downloads) (Feature 3)
    "pops_sub": ["Converts PS1 .CUE/.BIN discs into POPStarter .VCD format and saves directly to your Downloads folder.", "Converte jogos de PS1 (.BIN/.CUE) para o formato .VCD do POPStarter e salva direto na sua pasta Downloads.", "Converte jogos PS1 (.BIN/.CUE) para o formato .VCD do POPStarter e guarda na sua pasta Transferências/Downloads.", "Convierte juegos de PS1 (.BIN/.CUE) a formato .VCD de POPStarter y lo guarda en tu carpeta Descargas.", "Конвертирует диски PS1 (.BIN/.CUE) в формат .VCD (POPStarter) и сохраняет прямо в папку Загрузки.", "PS1の.BIN/.CUEイメージをPOPStarter用.VCDに変換し、ダウンロードフォルダへ直接保存します。"],
    "pops_src": ["Select PS1 .CUE or .BIN Image:", "Selecione o arquivo .CUE ou .BIN de PS1:", "Selecione o ficheiro .CUE ou .BIN de PS1:", "Selecciona imagen .CUE o .BIN de PS1:", "Выберите образ PS1 (.CUE или .BIN):", "PS1の.CUEまたは.BINファイルを選択:"],
    "pops_name": ["Output .VCD Filename (saved in Downloads):", "Nome do arquivo .VCD (será salvo em Downloads):", "Nome do ficheiro .VCD (guardado em Downloads):", "Nombre del archivo .VCD (en Descargas):", "Имя файла .VCD (в папку Загрузки):", "出力.VCDファイル名（Downloadsに保存）:"],
    "pops_dest_note": ["Destination locked to User Downloads folder (does not install POPStarter ELFs):", "Destino automático na pasta Downloads do usuário (apenas converte para .VCD):", "Destino automático na pasta Downloads do utilizador (apenas converte para .VCD):", "Destino automático en la carpeta Descargas del usuario:", "Автоматическое сохранение в папку Загрузки пользователя:", "保存先はユーザーのDownloadsフォルダに固定されています（変換のみ）:"],
    "pops_btn": ["CONVERT TO .VCD IN DOWNLOADS", "CONVERTER PARA .VCD EM DOWNLOADS", "CONVERTER PARA .VCD EM DOWNLOADS", "CONVERTIR A .VCD EN DESCARGAS", "КОНВЕРТИРОВАТЬ В .VCD (ЗАГРУЗКИ)", ".VCDに変換してDownloadsへ保存"],
    "pops_done": ["PS1 .VCD created in your Downloads folder!", "Arquivo .VCD criado com sucesso na sua pasta Downloads!", "Ficheiro .VCD criado com sucesso na sua pasta Downloads!", "¡Archivo .VCD creado en tu carpeta Descargas!", "Файл .VCD успешно создан в папке Загрузки!", "Downloadsフォルダに.VCDファイルを作成しました！"],

    # Patcher Permanente Widescreen 16:9 & PAL -> NTSC (Feature 4b)
    "patch_sub": ["Apply permanent 16:9 Widescreen (.pnach or auto), PAL 50Hz ➔ NTSC 60Hz video fix, IPS patches, and ESR unlock.", "Aplique Widescreen 16:9 definitivo, conversão PAL (50Hz) ➔ NTSC (60Hz), traduções IPS e desbloqueio ESR.", "Aplique Widescreen 16:9 definitivo, conversão PAL (50Hz) ➔ NTSC (60Hz), patches IPS e desbloqueio ESR.", "Aplica Widescreen 16:9 permanente, conversión PAL ➔ NTSC 60Hz, parches IPS y desbloqueo ESR.", "Постоянный патч 16:9 Widescreen, конвертер PAL ➔ NTSC 60 Гц, IPS патчи и снятие защиты ESR.", "恒久的な16:9ワイド化、PAL➔NTSC(60Hz)変換、IPSパッチ、ESRリージョン解除をISOへ直接適用します。"],
    "patch_iso": ["1. Source PS2 ISO Image:", "1. Imagem ISO Original de PS2:", "1. Imagem ISO Original de PS2:", "1. Imagen ISO Original de PS2:", "1. Исходный образ ISO PS2:", "1. 元のPS2 ISOイメージ:"],
    "patch_out": ["2. Output Patched ISO:", "2. Salvar Nova ISO Modificada Como:", "2. Guardar Nova ISO Modificada Como:", "2. Guardar ISO Modificada Como:", "2. Куда сохранить новый ISO:", "2. パッチ適用後のISO保存先:"],
    "patch_file": ["Optional Patch (.IPS or PCSX2 .PNACH):", "Patch Opcional (.IPS ou Widescreen .PNACH):", "Patch Opcional (.IPS ou Widescreen .PNACH):", "Parche Opcional (.IPS o .PNACH):", "Доп. патч (.IPS или .PNACH):", "追加パッチ（.IPS または .PNACH 任意）:"],
    "patch_wide": ["Permanent Widescreen 16:9 Patch (ELF Aspect / .pnach injection)", "Patch Permanente Widescreen 16:9 (Injeção direta no ELF da ISO)", "Patch Permanente Widescreen 16:9 (Injeção direta no ELF da ISO)", "Parche Permanente Widescreen 16:9 (Inyección ELF)", "Постоянный патч Widescreen 16:9 (в ELF образа)", "恒久16:9ワイドスクリーン化パッチ（ELF直接書換）"],
    "patch_ntsc": ["Convert Video PAL (50Hz) ➔ NTSC (60Hz) in Boot ELF", "Converter Vídeo PAL (50Hz) ➔ NTSC (60Hz) no ELF Principal", "Converter Vídeo PAL (50Hz) ➔ NTSC (60Hz) no ELF Principal", "Convertir Video PAL (50Hz) ➔ NTSC (60Hz) en ELF", "Конвертировать видео PAL (50 Гц) ➔ NTSC (60 Гц)", "映像方式をPAL(50Hz)からNTSC(60Hz)へ恒久変換"],
    "patch_reg": ["Remove Region Protection (ESR Disc Signature)", "Remover Trava de Região (Assinatura ESR)", "Remover Bloqueio de Região (Assinatura ESR)", "Quitar Bloqueo de Región (ESR)", "Снять региональную защиту (ESR)", "リージョンロック解除 (ESR署名)"],
    "patch_btn": ["BUILD PATCHED ISO", "GERAR ISO MODIFICADA", "GERAR ISO MODIFICADA", "GENERAR ISO PARCHEADA", "СОЗДАТЬ ПРОПАТЧЕННЫЙ ISO", "パッチ適用ISOを生成"],
    "patch_success": ["ISO patched successfully!", "ISO modificada com sucesso!", "ISO modificada com sucesso!", "¡ISO parcheada con éxito!", "Образ ISO успешно пропатчен!", "ISOへのパッチ適用が完了しました！"],

    # Art Scraper 2.0 - Kit Completo (Feature 5)
    "art_title": ["OPL ART SCRAPER 2.0", "BAIXADOR DE ARTES DO OPL 2.0", "DESCARREGADOR DE ARTES OPL 2.0", "DESCARGADOR DE ARTES OPL 2.0", "ЗАГРУЗЧИК ОБЛОЖЕК OPL 2.0", "OPLアートダウンローダー 2.0"],
    "art_desc": ["Download full OPL art kits (Front/Back Cover, Disc, Background, Screenshot, Logo) with live preview.", "Baixe o kit completo de artes do OPL (Capa, Verso, Disco, Fundo, Print e Logo) com prévia visual.", "Descarregue o kit completo de artes do OPL (Capa, Verso, Disco, Fundo, Captura e Logo) com pré-visualização.", "Descarga el kit completo de artes OPL (Carátula, Reverso, Disco, Fondo, Captura, Logo) con vista previa.", "Полный набор графики OPL (обложки, диск, фон, скриншот, логотип) с предпросмотром.", "OPL用フルアートキット（表紙・裏面・ディスク・背景・スクショ・ロゴ）を一括取得＆プレビュー。"],
    "art_scan": ["1. SCAN GAMES", "1. ESCANEAR JOGOS", "1. VERIFICAR JOGOS", "1. ESCANEAR JUEGOS", "1. СКАНИРОВАТЬ ИГРЫ", "1. ゲーム検出"],
    "art_dl": ["2. DOWNLOAD SELECTED ARTS", "2. BAIXAR KIT DE ARTES", "2. DESCARREGAR ARTES", "2. DESCARGAR KIT DE ARTES", "2. СКАЧАТЬ ВЫБРАННЫЕ АРТЫ", "2. 選択アートを一括取得"],
    "art_preview_hdr": ["LIVE ARTWORK PREVIEW", "PRÉ-VISUALIZAÇÃO DAS ARTES", "PRÉ-VISUALIZAÇÃO DAS ARTES", "VISTA PREVIA DE ARTES", "ПРЕДПРОСМОТР ГРАФИКИ", "アートワーク・プレビュー"],
    "art_cov": ["Front Cover (_COV)", "Capa Frontal (_COV)", "Capa Frontal (_COV)", "Portada (_COV)", "Обложка (_COV)", "表面カバー (_COV)"],
    "art_cov2": ["Back Cover (_COV2)", "Capa Traseira (_COV2)", "Capa Traseira (_COV2)", "Contraportada (_COV2)", "Задняя обложка (_COV2)", "裏面カバー (_COV2)"],
    "art_disc": ["Disc Icon (_DISC)", "Disco / Mídia (_DISC)", "Disco / Multimédia (_DISC)", "Disco (_DISC)", "Диск (_DISC)", "ディスク画像 (_DISC)"],
    "art_bg": ["Background (_BG)", "Plano de Fundo (_BG)", "Plano de Fundo (_BG)", "Fondo (_BG)", "Фон (_BG)", "背景画像 (_BG)"],
    "art_scr": ["Screenshot (_SCR)", "Screenshot (_SCR)", "Captura (_SCR)", "Captura (_SCR)", "Скриншот (_SCR)", "スクリーンショット (_SCR)"],
    "art_lgo": ["Game Logo (_LGO)", "Logo do Jogo (_LGO)", "Logótipo (_LGO)", "Logo (_LGO)", "Логотип (_LGO)", "タイトルロゴ (_LGO)"],
    "art_no_img": ["No local image yet", "Sem imagem local", "Sem imagem local", "Sin imagen local", "Нет изображения", "画像なし"],
    "art_done": ["Artwork kit download completed!", "Download do kit de artes concluído!", "Descarregamento do kit de artes concluído!", "¡Descarga de artes completada!", "Загрузка графики завершена!", "アートキットのダウンロードが完了しました！"],

    # Memory Card Manager & Converter (Feature 6)
    "mc_sub": ["Manage PS2 saves (.psu import/export) and convert between PCSX2 (.ps2 ECC) and OPL VMC (.bin).", "Gerencie saves de PS2 (.psu) e converta cartões entre PCSX2 (.ps2 com ECC) e VMC do OPL (.bin).", "Gira gravações PS2 (.psu) e converta cartões entre PCSX2 (.ps2 com ECC) e VMC do OPL (.bin).", "Gestiona partidas PS2 (.psu) y convierte tarjetas entre PCSX2 (.ps2) y VMC de OPL (.bin).", "Управление сохранениями PS2 (.psu) и конвертация карт между PCSX2 (.ps2) и OPL VMC (.bin).", "PS2セーブデータ(.psu)の管理と、PCSX2(.ps2)⇄OPL VMC(.bin)の相互変換・新規作成。"],
    "mc_mode_exp": ["Save Explorer (.ps2 / .bin)", "Explorador de Saves (.ps2 / .bin)", "Explorador de Saves (.ps2 / .bin)", "Explorador de Saves (.ps2 / .bin)", "Проводник сохранений", "セーブデータ管理"],
    "mc_mode_conv": ["Converter & VMC Creator", "Conversor & Criador de VMC", "Conversor & Criador de VMC", "Conversor y Creador VMC", "Конвертер и создание VMC", "変換＆VMC新規作成"],
    "mc_open_card": ["OPEN CARD (.PS2 / .BIN)", "ABRIR CARTÃO (.PS2 / .BIN)", "ABRIR CARTÃO (.PS2 / .BIN)", "ABRIR TARJETA (.PS2 / .BIN)", "ОТКРЫТЬ КАРТУ (.PS2/.BIN)", "カードを開く (.PS2/.BIN)"],
    "mc_find_pcsx2": ["OPEN PCSX2 MEMCARDS", "PASTA MEMCARDS DO PCSX2", "PASTA MEMCARDS DO PCSX2", "CARPETA MEMCARDS PCSX2", "ПАПКА КАРТ PCSX2", "PCSX2カードフォルダ"],
    "mc_export_psu": ["EXPORT SAVE (.PSU)", "EXPORTAR SAVE (.PSU)", "EXPORTAR SAVE (.PSU)", "EXPORTAR SAVE (.PSU)", "ЭКСПОРТ (.PSU)", "セーブ書き出し (.PSU)"],
    "mc_import_psu": ["IMPORT SAVE (.PSU)", "IMPORTAR SAVE (.PSU)", "IMPORTAR SAVE (.PSU)", "IMPORTAR SAVE (.PSU)", "ИМПОРТ (.PSU)", "セーブ取り込み (.PSU)"],
    "mc_del_save": ["DELETE SAVE", "EXCLUIR SAVE", "ELIMINAR SAVE", "ELIMINAR SAVE", "УДАЛИТЬ", "セーブ削除"],
    "mc_empty_card": ["No saves found on this Memory Card (or no card opened yet).", "Nenhum save encontrado neste Memory Card (ou nenhum cartão aberto).", "Nenhum save encontrado neste Cartão de Memória.", "No se encontraron partidas en esta tarjeta.", "Сохранения не найдены (или карта не открыта).", "セーブデータが見つからないか、カードが開かれていません。"],
    "mc_conv_hdr": ["CONVERT PCSX2 (.PS2 ECC) ⇄ OPL VMC (.BIN RAW)", "CONVERTER PCSX2 (.PS2 ECC) ⇄ VMC DO OPL (.BIN)", "CONVERTER PCSX2 (.PS2 ECC) ⇄ VMC DO OPL (.BIN)", "CONVERTIR PCSX2 (.PS2) ⇄ OPL VMC (.BIN)", "КОНВЕРТЕР PCSX2 (.PS2) ⇄ OPL VMC (.BIN)", "PCSX2 (.PS2) ⇄ OPL VMC (.BIN) フォーマット変換"],
    "mc_conv_btn": ["CONVERT MEMORY CARD", "CONVERTER CARTÃO AGORA", "CONVERTER CARTÃO AGORA", "CONVERTIR TARJETA", "КОНВЕРТИРОВАТЬ КАРТУ", "メモリーカードを変換"],
    "mc_new_hdr": ["CREATE BLANK FORMATTED MEMORY CARD / VMC", "CRIAR NOVO MEMORY CARD / VMC FORMATADO", "CRIAR NOVO CARTÃO / VMC FORMATADO", "CREAR NUEVA TARJETA / VMC FORMATEADA", "СОЗДАТЬ НОВУЮ ОТФОРМАТИРОВАННУЮ КАРТУ", "フォーマット済み新規メモリーカード / VMC作成"],
    "mc_new_btn": ["CREATE NEW CARD", "CRIAR CARTÃO FORMATADO", "CRIAR CARTÃO FORMATADO", "CREAR TARJETA", "СОЗДАТЬ КАРТУ", "新規カードを作成"],

    # Gravação de DVD
    "burn_title": ["DISC BURN ENGINE", "GRAVAÇÃO DE DVD", "GRAVAÇÃO DE DVD", "GRABACIÓN DE DVD", "ПРОЖИГ DVD ДИСКОВ", "DVD書き込みエンジン"],
    "burn_iso": ["1. Select ISO Image to Burn:", "1. Selecione a Imagem ISO para Gravar:", "1. Selecione a Imagem ISO para Gravar:", "1. Selecciona la Imagen ISO:", "1. Выберите образ ISO для записи:", "1. 書き込むISOイメージを選択:"],
    "burn_drv": ["2. Optical Writer Drive:", "2. Gravador de DVD Óptico:", "2. Gravador de DVD Óptico:", "2. Grabadora de DVD:", "2. Привод для записи диска:", "2. 光学書き込みドライブ:"],
    "burn_spd": ["3. Burning Speed:", "3. Velocidade de Gravação:", "3. Velocidade de Gravação:", "3. Velocidad de Grabación:", "3. Скорость записи:", "3. 書き込み速度:"],
    "burn_btn": ["BURN DISC NOW", "GRAVAR DISCO AGORA", "GRAVAR DISCO AGORA", "GRABAR DISCO AHORA", "ЗАПИСАТЬ ДИСК СЕЙЧАС", "今すぐディスクを書き込む"],
    "burn_ready": ["Ready to burn disc.", "Pronto para gravação.", "Pronto para gravação.", "Listo para grabar.", "Готов к записи.", "書き込み準備完了。"],
    "burn_done": ["Disc burned successfully!", "Disco gravado com sucesso!", "Disco gravado com sucesso!", "¡Disco grabado con éxito!", "Диск успешно записан!", "書き込みが完了しました！"],
    "burn_err_nomedia": ["No optical recorder drive detected on this computer.", "Nenhum gravador de DVD óptico detectado neste computador.", "Nenhum gravador de DVD óptico detetado neste computador.", "No se detectó grabadora de DVD en este ordenador.", "Оптический привод для записи не обнаружен на этом ПК.", "光学書き込みドライブが検出されませんでした。"],
    "burn_err_select_iso": ["Select an ISO file to burn.", "Selecione o arquivo ISO para gravar.", "Selecione o ficheiro ISO para gravar.", "Seleccione un archivo ISO para grabar.", "Выберите файл ISO для записи.", "書き込むISOファイルを選択してください。"],
    "burn_progress_msg": ["Burning disc... Do not eject media.", "Gravando disco... Não ejete a mídia.", "A gravar disco... Não ejete o disco.", "Grabando disco... No expulse el medio.", "Идет запись диска... Не извлекайте носитель.", "書き込み中... ディスクを取り出さないでください。"],
    "burn_err_title": ["Burn Error", "Erro de Gravação", "Erro de Gravação", "Error de Grabación", "Ошибка записи", "書き込みエラー"],
    "burn_no_drives": ["No optical burner detected", "Nenhum gravador de DVD/CD detectado", "Nenhum gravador de DVD/CD detetado", "No se detectó grabadora de DVD/CD", "Оптический привод не обнаружен", "光学ドライブが検出されませんでした"],
    "burn_writing_sectors": ["Writing sectors...", "Gravando setores...", "A gravar setores...", "Escribiendo sectores...", "Запись секторов...", "セクター書き込み中..."],

    # Emulador PCSX2
    "emu_sel": ["SELECT GAME TO TEST ON PCSX2", "SELECIONE UM JOGO PARA TESTAR NO PCSX2", "SELECIONE UM JOGO PARA TESTAR NO PCSX2", "SELECCIONA UN JUEGO PARA PROBAR", "ВЫБЕРИТЕ ИГРУ ДЛЯ ТЕСТА В PCSX2", "PCSX2でテストするゲームを選択"],
    "emu_btn": ["LAUNCH PCSX2 EMULATOR", "INICIAR EMULADOR PCSX2", "INICIAR EMULADOR PCSX2", "INICIAR EMULADOR PCSX2", "ЗАПУСТИТЬ ЭМУЛЯТОР PCSX2", "PCSX2エミュレータ起動"],
    "emu_browse_iso": ["OR TEST EXTERNAL ISO...", "OU TESTAR ISO AVULSA...", "OU TESTAR ISO EXTERNA...", "O PROBAR ISO EXTERNA...", "ИЛИ ВЫБРАТЬ ДРУГОЙ ISO...", "外部ISOを直接起動..."],
    "emu_info": ["First launch automatically configures PCSX2 BIOS from internal resources.", "Na primeira execução, a BIOS do PCSX2 será configurada automaticamente.", "No primeiro arranque, a BIOS do PCSX2 será configurada automaticamente.", "El primer inicio configurará automáticamente la BIOS de PCSX2.", "При первом запуске BIOS PCSX2 настроится автоматически.", "初回起動時に内蔵リソースからPCSX2のBIOSが自動設定されます。"],

    # Extração / Repack / ZSO / BIN->ISO
    "iso_mode_ext": ["Extract ISO", "Extrair ISO", "Extrair ISO", "Extraer ISO", "Извлечь ISO", "ISO展開"],
    "iso_mode_rep": ["Repack Folder ➔ ISO", "Reempacotar ➔ ISO", "Reempacotar ➔ ISO", "Reempaquetar ➔ ISO", "Собрать в ISO", "フォルダ➔ISO再構築"],
    "iso_mode_zso": ["Compress ZSO", "Comprimir ZSO", "Comprimir ZSO", "Comprimir ZSO", "Сжать в ZSO", "ZSO圧縮"],
    "iso_mode_bin": ["BIN ➔ ISO", "BIN ➔ ISO", "BIN ➔ ISO", "BIN ➔ ISO", "BIN ➔ ISO", "BIN ➔ ISO変換"],
    "iso_file": ["Source File or Folder:", "Arquivo ou Pasta de Origem:", "Ficheiro ou Pasta de Origem:", "Archivo o Carpeta de Origen:", "Исходный файл / папка:", "ソースファイル / フォルダ:"],
    "iso_out": ["Output Destination:", "Local de Saída / Destino:", "Local de Saída / Destino:", "Destino de Salida:", "Куда сохранить:", "出力先:"],
    "iso_zso_lvl": ["ZSO Compression Mode:", "Modo de Compressão ZSO:", "Modo de Compressão ZSO:", "Modo de Compresión ZSO:", "Режим сжатия ZSO:", "ZSO圧縮モード:"],
    "iso_btn_ext": ["START EXTRACTION", "INICIAR EXTRAÇÃO", "INICIAR EXTRAÇÃO", "INICIAR EXTRACCIÓN", "НАЧАТЬ ИЗВЛЕЧЕНИЕ", "展開を開始"],
    "iso_btn_rep": ["BUILD ISO FROM FOLDER", "GERAR ISO DA PASTA", "GERAR ISO DA PASTA", "CREAR ISO DESDE CARPETA", "СОБРАТЬ ОБРАЗ ISO", "ISOを再構築"],
    "iso_btn_zso": ["COMPRESS TO ZSO", "COMPRIMIR PARA ZSO", "COMPRIMIR PARA ZSO", "COMPRIMIR A ZSO", "СЖАТЬ В ZSO", "ZSOへ圧縮"],
    "iso_btn_bin": ["CONVERT BIN TO ISO", "CONVERTER BIN PARA ISO", "CONVERTER BIN PARA ISO", "CONVERTIR BIN A ISO", "КОНВЕРТИРОВАТЬ BIN В ISO", "BINをISOに変換"],
    "iso_succ": ["Process completed successfully!", "Processo concluído com sucesso!", "Processo concluído com sucesso!", "¡Proceso completado!", "Процесс успешно завершен!", "処理が正常に完了しました！"],
    "iso_empty": ["Please select source and destination paths.", "Selecione a origem e o destino primeiro.", "Selecione a origem e o destino primeiro.", "Seleccione origen y destino.", "Укажите пути источника и назначения.", "ソースと出力先を指定してください。"],

    # USB Util
    "util_iso": ["Original ISO Image (>4GB):", "Imagem ISO Original (>4GB):", "Imagem ISO Original (>4GB):", "Imagen ISO Original (>4GB):", "Оригинальный образ ISO (>4 ГБ):", "元のISOイメージ (>4GB):"],
    "util_dst": ["Target FAT32 USB Drive / Folder:", "Unidade USB FAT32 / Pasta de Destino:", "Unidade USB FAT32 / Pasta de Destino:", "Carpeta / USB FAT32 Destino:", "Целевой USB-накопитель FAT32:", "対象FAT32ドライブ / フォルダ:"],
    "util_name": ["Game Title (Max 32 chars):", "Nome do Jogo (Máx 32 caracteres):", "Nome do Jogo (Máx 32 caracteres):", "Nombre del Juego (Máx 32):", "Название игры (до 32 симв.):", "ゲーム名（最大32文字）:"],
    "util_btn": ["SPLIT & GENERATE UL.CFG", "DIVIDIR E GERAR UL.CFG", "DIVIDIR E GERAR UL.CFG", "DIVIDIR Y CREAR UL.CFG", "РАЗДЕЛИТЬ И СОЗДАТЬ UL.CFG", "分割してUL.CFGを生成"],
    "util_succ": ["Game split successfully for OPL FAT32!", "Jogo dividido com sucesso para OPL (FAT32)!", "Jogo dividido com sucesso para OPL (FAT32)!", "¡Juego dividido con éxito para FAT32!", "Игра успешно разделена для FAT32!", "OPL FAT32用に分割が完了しました！"],

    # Analisador / Ripper de Disco Óptico
    "disc_drv": ["Optical Drive:", "Leitor Óptico (DVD/CD):", "Leitor Óptico (DVD/CD):", "Lector Óptico:", "Оптический привод:", "光学ドライブ:"],
    "disc_btn": ["ANALYZE PHYSICAL DISC", "ANALISAR DISCO FÍSICO", "ANALISAR DISCO FÍSICO", "ANALIZAR DISCO", "АНАЛИЗИРОВАТЬ ДИСК", "ディスクを解析"],
    "disc_none": ["No optical disc detected", "Nenhum leitor óptico detectado", "Nenhum leitor óptico detetado", "Ningún lector detectado", "Привод не обнаружен", "光学ドライブ未検出"],
    "rip_out": ["Save Extracted ISO Folder:", "Pasta para Salvar a ISO:", "Pasta para Guardar a ISO:", "Carpeta de Destino:", "Папка для сохранения:", "ISO保存先フォルダ:"],
    "rip_btn": ["RIP DISC TO ISO", "EXTRAIR DISCO PARA ISO", "EXTRAIR DISCO PARA ISO", "RIPEAR DISCO A ISO", "РИПНУТЬ ДИСК В ISO", "ディスクをISOとして抽出"],
    "rip_done": ["Disc ripped successfully!", "Disco extraído para ISO com sucesso!", "Disco extraído para ISO com sucesso!", "¡Disco extraído con éxito!", "Диск успешно скопирован в ISO!", "ディスクのISO抽出が完了しました！"],

    # Clonar e Migrar
    "clone_src": ["Source Drive (Copy From):", "Unidade de Origem (Copiar De):", "Unidade de Origem (Copiar De):", "Unidad Origen (Copiar De):", "Исходный диск (копировать из):", "コピー元ドライブ:"],
    "clone_dst": ["Destination Drive (Copy To):", "Unidade de Destino (Copiar Para):", "Unidade de Destino (Copiar Para):", "Unidad Destino (Copiar A):", "Целевой диск (копировать в):", "コピー先ドライブ:"],
    "clone_fmt_dst": ["Format destination drive prior to clone", "Formatar unidade de destino antes de clonar", "Formatar unidade de destino antes de clonar", "Formatear destino antes de copiar", "Форматировать целевой диск перед копированием", "コピー前にコピー先をフォーマット"],
    "clone_btn": ["START DRIVE CLONE", "INICIAR CLONAGEM DE PENDRIVE", "INICIAR CLONAGEM DE UNIDADE", "INICIAR CLONACIÓN", "НАЧАТЬ КЛОНИРОВАНИЕ", "ドライブ複製を開始"],
    "mig_drv": ["Target Removable Drive:", "Unidade USB de Destino:", "Unidade USB de Destino:", "Unidad Destino:", "Целевой накопитель:", "対象USBドライブ:"],
    "mig_fs": ["Target Filesystem:", "Novo Sistema de Arquivos:", "Novo Sistema de Ficheiros:", "Sistema de Archivos:", "Файловая система:", "変換先ファイルシステム:"],
    "mig_btn": ["BACKUP, FORMAT & RESTORE DRIVE", "FAZER BACKUP, FORMATAR E MIGRAR", "FAZER BACKUP, FORMATAR E MIGRAR", "FORMATEAR Y MIGRAR UNIDAD", "ФОРМАТ И МИГРАЦИЯ ДИСКА", "退避・フォーマット・復元を開始"],
    "mig_conf": ["Formatting will erase and rebuild the partition (files are backed up temporarily). Continue?", "O pendrive será formatado e os arquivos restaurados automaticamente. Deseja continuar?", "A unidade será formatada e os ficheiros restaurados automaticamente. Continuar?", "¿Seguro que deseas formatear y migrar la unidad?", "Диск будет отформатирован с переносом данных. Продолжить?", "一時バックアップ後にフォーマットして復元します。続行しますか？"],

    # Cheats
    "cht_folder": ["CHT Folder:", "Pasta CHT:", "Pasta CHT:", "Carpeta CHT:", "Папка CHT:", "CHTフォルダ:"],
    "cht_disabled": ["DISABLED", "DESATIVADO", "DESATIVADO", "DESACTIVADO", "ОТКЛЮЧЕНО", "無効"],
    "cht_enabled": ["ENABLED", "ATIVO", "ATIVO", "ACTIVADO", "АКТИВНО", "有効"],
    "cht_add": ["+ ADD CHEAT", "+ ADICIONAR CHEAT", "+ ADICIONAR CHEAT", "+ AÑADIR CHEAT", "+ ДОБАВИТЬ ЧИТ", "+ チート追加"],
    "cht_edit": ["EDIT CHEAT", "EDITAR CHEAT", "EDITAR CHEAT", "EDITAR CHEAT", "РЕДАКТИРОВАТЬ", "チート編集"],
    "cht_enable": ["ENABLE", "HABILITAR", "ATIVAR", "HABILITAR", "ВКЛЮЧИТЬ", "有効化"],
    "cht_disable": ["DISABLE", "DESABILITAR", "DESATIVAR", "DESHABILITAR", "ОТКЛЮЧИТЬ", "無効化"],
    "cht_import": ["Import .cht File", "Importar arquivo .cht", "Importar ficheiro .cht", "Importar archivo .cht", "Импортировать файл .cht", ".chtファイルをインポート"],
    "cht_create": ["Create from Scratch", "Criar do Zero", "Criar de Raiz", "Crear desde Cero", "Создать с нуля", "新規作成"],
    "cht_name": ["Cheat Filename (Game ID):", "Nome do Arquivo (ID do Jogo):", "Nome do Ficheiro (ID do Jogo):", "Nombre (ID de Juego):", "Имя файла (ID игры):", "ファイル名 (ゲームID):"],
    "cht_save": ["SAVE CHEAT", "SALVAR CHEAT", "GUARDAR CHEAT", "GUARDAR CHEAT", "СОХРАНИТЬ ЧИТ", "チート保存"],
    "cht_none": ["No cheat selected!", "Nenhum cheat selecionado!", "Nenhum cheat selecionado!", "¡Ningún cheat seleccionado!", "Чит не выбран!", "チートが選択されていません！"],
    "cht_err": ["Error processing cheat:", "Erro ao processar cheat:", "Erro ao processar cheat:", "Error al procesar cheat:", "Ошибка обработки чита:", "チート処理エラー:"],
    "cht_succ": ["Cheat saved successfully!", "Cheat salvo com sucesso!", "Cheat guardado com sucesso!", "¡Cheat guardado con éxito!", "Чит успешно сохранен!", "チートが正常に保存されました！"],
    "cht_sel_game": ["Select Game from Library:", "Selecionar Jogo da Biblioteca:", "Selecionar Jogo da Biblioteca:", "Seleccionar Juego de la Biblioteca:", "Выбрать игру из библиотеки:", "ライブラリからゲームを選択:"],
    "cht_manual": ["Custom / Manual", "Personalizado / Manual", "Personalizado / Manual", "Personalizado / Manual", "Пользовательский / Вручную", "カスタム / 手動"],

    # APA HDD
    "apa_title": ["APA HDD EXPLORER", "EXPLORADOR DE HDD APA", "EXPLORADOR DE HDD APA", "EXPLORADOR HDD APA", "ПРОВОДНИК APA HDD", "APA HDDエクスプローラー"],
    "apa_drv": ["Physical PS2 Drive or Raw .IMG:", "HD Físico de PS2 ou Imagem .IMG:", "Disco Físico PS2 ou Imagem .IMG:", "Unidad Física o Imagen .IMG:", "Физический диск или образ .IMG:", "PS2物理ドライブまたは.IMGイメージ:"],
    "apa_btn_open": ["INSPECT .IMG", "ABRIR .IMG", "ABRIR .IMG", "ABRIR .IMG", "ОТКРЫТЬ .IMG", ".IMGを開く"],
    "apa_btn_scan_drv": ["SCAN DRIVE", "LER HD FÍSICO", "LER DISCO FÍSICO", "LEER DISCO", "ЧИТАТЬ ДИСК", "物理ドライブ読込"],
    "apa_btn_raw": ["BACKUP RAW .IMG", "CRIAR IMAGEM .IMG", "CRIAR IMAGEM .IMG", "COPIA A .IMG", "ДАМП В .IMG", "RAW .IMGバックアップ"],
    "apa_btn_ext": ["EXTRACT HDL GAMES", "EXTRAIR JOGOS DO HD", "EXTRAIR JOGOS DO DISCO", "EXTRAER JUEGOS", "ИЗВЛЕЧЬ ИГРЫ", "HDLゲーム抽出"],

    # Homebrews Apps
    "app_name": ["Application Display Title:", "Nome do Aplicativo no OPL:", "Nome da Aplicação no OPL:", "Nombre de Aplicación:", "Имя приложения в OPL:", "OPL上の表示アプリ名:"],
    "app_elf": ["Path to .ELF Binary:", "Arquivo Executável .ELF:", "Ficheiro Executável .ELF:", "Ejecutable .ELF:", "Путь к файлу .ELF:", ".ELFバイナリのパス:"],
    "app_drv": ["Target OPL USB Drive:", "Pendrive OPL de Destino:", "Pen USB OPL de Destino:", "Unidad USB Destino:", "Целевой диск OPL:", "インストール先USBドライブ:"],
    "app_btn": ["INSTALL HOMEBREW TO OPL APPS", "INSTALAR APLICATIVO NO OPL", "INSTALAR APLICAÇÃO NO OPL", "INSTALAR EN MENÚ APPS", "УСТАНОВИТЬ В OPL APPS", "OPLのAPPSへインストール"],
    "app_succ": ["Homebrew installed successfully!", "Aplicativo instalado com sucesso!", "Aplicação instalada com sucesso!", "¡Instalado con éxito!", "Приложение успешно установлено!", "正常にインストールされました！"],

    # Configurações (com Modo Batata, Som de Aba e Variações de Animação!)
    "set_sub": ["Customize theme, language, audio channels, animation style, and Potato Mode performance.", "Personalize tema, idioma, canais de áudio, estilo de animação e desempenho do Modo Batata.", "Personalize tema, idioma, canais de áudio, estilo de animação e desempenho do Modo Batata.", "Personaliza tema, idioma, canales de audio, estilo de animación y Modo Patata.", "Настройте тему, язык, звуковые эффекты, стиль анимации и Режим Картошки.", "テーマ、言語、効果音・タブ切替音、アニメーション種類、ポテトモードを設定します。"],
    "set_app": ["APPEARANCE & LANGUAGE", "APARÊNCIA, TEMA & IDIOMA", "APARÊNCIA, TEMA & IDIOMA", "APARIENCIA E IDIOMA", "ВНЕШНИЙ ВИД И ЯЗЫК", "外観・テーマ・言語"],
    "set_theme": ["INTERFACE THEME", "TEMA VISUAL", "TEMA VISUAL", "TEMA DE LA INTERFAZ", "ТЕМА ИНТЕРФЕЙСА", "インターフェーステーマ"],
    "set_anim_style": ["PAGE ANIMATION VARIATION", "VARIAÇÃO DA ANIMAÇÃO DE ABAS", "VARIAÇÃO DA ANIMAÇÃO DE ABAS", "ESTILO DE ANIMACIÓN", "ВАРИАНТ АНИМАЦИИ ВКЛАДОК", "画面切替アニメーションの種類"],
    "anim_slide": ["Horizontal Slide", "Deslize Lateral (Slide)", "Deslize Lateral (Slide)", "Deslizamiento Lateral", "Горизонтальный слайд", "横スライド (Slide)"],
    "anim_rise": ["Vertical Rise", "Subida Suave (Rise)", "Subida Suave (Rise)", "Elevación Suave", "Плавный подъем", "縦ライズ (Rise)"],
    "anim_zoom": ["Center Pop / Zoom", "Expansão Central (Zoom)", "Expansão Central (Zoom)", "Zoom Central", "Масштабирование (Zoom)", "ズームポップ (Zoom)"],
    "anim_step": ["Crisp Flash Step", "Transição Rápida (Step)", "Transição Rápida (Step)", "Paso Rápido", "Быстрый переход", "高速ステップ (Step)"],
    "set_beh": ["AUDIO & PERFORMANCE", "ÁUDIO & DESEMPENHO", "ÁUDIO & DESEMPENHO", "AUDIO Y RENDIMIENTO", "ЗВУК И ПРОИЗВОДИТЕЛЬНОСТЬ", "サウンド＆パフォーマンス"],
    "set_snd": ["Enable sound effects (clicks & alerts)", "Ativar efeitos sonoros (cliques e avisos)", "Ativar efeitos sonoros (cliques e avisos)", "Activar efectos de sonido", "Звуковые эффекты (клики и уведомления)", "操作音・通知サウンドを有効化"],
    "set_tab_snd": ["Play sound when switching tabs", "Tocar som ao mudar de aba", "Tocar som ao mudar de separador", "Sonido al cambiar de pestaña", "Звук при переключении вкладок", "タブ切り替え時の効果音を鳴らす"],
    "set_bgm": ["Background ambience music", "Música ambiente de fundo", "Música ambiente de fundo", "Música ambiental de fondo", "Фоновая музыка", "BGM（環境音楽）を再生"],
    "set_anim": ["Smooth interface transitions", "Animações suaves na interface", "Animações suaves na interface", "Animaciones suaves", "Плавные анимации интерфейса", "スムーズな画面アニメーション"],
    "set_potato": ["🥔 Potato Mode (Ultra Low-Spec / Max FPS)", "🥔 Modo Batata (PC Fraco / Desempenho Máximo)", "🥔 Modo Batata (PC Fraco / Desempenho Máximo)", "🥔 Modo Patata (PC Bajo Recursos / Máx FPS)", "🥔 Режим Картошки (Слабый ПК / Макс. скорость)", "🥔 ポテトモード（超軽量・低スペックPC向け）"],
    "set_potato_badge": ["🥔 POTATO MODE ACTIVE", "🥔 MODO BATATA ATIVO", "🥔 MODO BATATA ATIVO", "🥔 MODO PATATA ACTIVO", "🥔 РЕЖИМ КАРТОШКИ", "🥔 ポテトモード有効"],
    "set_lang": ["LANGUAGE / IDIOMA", "IDIOMA DO SISTEMA", "IDIOMA DO SISTEMA", "IDIOMA DEL SISTEMA", "ЯЗЫК СИСТЕМЫ", "表示言語"],
    "set_rate": ["⭐ RATE PROJECT", "⭐ AVALIAR O PS2MANAGER", "⭐ AVALIAR O PS2MANAGER", "⭐ CALIFICAR PROYECTO", "⭐ ОЦЕНИТЬ ПРОЕКТ", "⭐ プロジェクトを評価"],
    "dev_tools": ["SYSTEM & DIAGNOSTICS", "SISTEMA, HISTÓRICO & DIAGNÓSTICO", "SISTEMA, HISTÓRICO & DIAGNÓSTICO", "SISTEMA Y DIAGNÓSTICO", "СИСТЕМА И ДИАГНОСТИКА", "システム＆診断ツール"],
    "dev_apa_sim": ["Create Test APA HDD Image (.IMG)", "Gerar Imagem APA de Teste (.IMG)", "Gerar Imagem APA de Teste (.IMG)", "Crear Imagen APA de Prueba", "Создать тестовый образ APA (.IMG)", "テスト用APA HDDイメージ生成"],
    "set_log": ["EXPORT DIAGNOSTIC REPORT", "EXPORTAR RELATÓRIO DE DIAGNÓSTICO", "EXPORTAR RELATÓRIO DE DIAGNÓSTICO", "EXPORTAR REPORTE DE LOG", "ЭКСПОРТИРОВАТЬ ОТЧЕТ", "診断ログレポートを出力"],
    "ver_btn": ["VERSION ROLLBACK", "REVERTER VERSÃO (/VER)", "REVERTER VERSÃO (/VER)", "VOLVER A VERSIÓN PREVIA", "ОТКАТ ВЕРСИИ", "以前のバージョンを起動"],
    "roadmap_btn": ["ROADMAP & UPDATES TIMELINE", "LINHA DO TEMPO DE VERSÕES", "LINHA DO TEMPO DE VERSÕES", "CRONOGRAMA DE VERSIONES", "ТАЙМЛАЙН ОБНОВЛЕНИЙ", "アップデート履歴＆ロードマップ"],

    # Roadmap
    "roadmap_title": ["UPDATE ROADMAP & HISTORY", "LINHA DO TEMPO & HISTÓRICO", "HISTÓRICO & ROADMAP", "HISTORIAL Y CRONOGRAMA", "ИСТОРИЯ И ПЛАНЫ ОБНОВЛЕНИЙ", "アップデート履歴とロードマップ"],
    "roadmap_sub": ["Drag the timeline to explore past and current releases.", "Arraste a linha do tempo para explorar todas as versões do PS2Manager.", "Arraste a linha do tempo para explorar todas as versões do PS2Manager.", "Arrastra la línea temporal para ver las versiones.", "Перемещайте ползунок для просмотра версий.", "スライダーを動かして各バージョンを確認できます。"],
    "roadmap_prev": ["◀ Previous Version", "◀ Versão Anterior", "◀ Versão Anterior", "◀ Versión Anterior", "◀ Предыдущая версия", "◀ 前のバージョン"],
    "roadmap_next": ["Next Version ▶", "Próxima Versão ▶", "Próxima Versão ▶", "Siguiente Versión ▶", "Следующая версия ▶", "次のバージョン ▶"],
    "roadmap_cur": ["CURRENT VERSION", "VERSÃO ATUAL", "VERSÃO ATUAL", "VERSIÓN ACTUAL", "ТЕКУЩАЯ ВЕРСИЯ", "現在のバージョン"],

    # Setup inicial
    "setup_welcome": ["Welcome to PS2Manager V1.08", "Bem-vindo ao PS2Manager V1.08", "Bem-vindo ao PS2Manager V1.08", "Bienvenido a PS2Manager V1.08", "Добро пожаловать в PS2Manager V1.08", "PS2Manager V1.08へようこそ"],
    "setup_continue": ["CONTINUE", "CONTINUAR", "CONTINUAR", "CONTINUAR", "ПРОДОЛЖИТЬ", "次へ進む"],
    "setup_lang": ["Select your language:", "Selecione o seu idioma:", "Selecione o seu idioma:", "Selecciona tu idioma:", "Выберите ваш язык:", "言語を選択してください:"],
    "setup_model": ["Select your PS2 model:", "Qual o modelo do seu PS2?", "Qual o modelo da sua PS2?", "¿Cuál es el modelo de tu PS2?", "Модель вашей PS2:", "PS2本体の型番:"],
    "setup_type": ["Console Form Factor:", "Versão do Console:", "Versão da Consola:", "Tipo de Consola:", "Тип консоли:", "本体タイプ:"],
    "setup_finish": ["Configuration ready! Let's get started.", "Tudo pronto! Vamos começar.", "Tudo pronto! Vamos começar.", "¡Todo listo! Comencemos.", "Все готово! Начинаем работу.", "準備完了！始めましょう。"],

    # Mensagens de Integridade e Modais
    "msg_corruption_warn": [
        "Active disk operation in progress! Closing now may corrupt your game files.",
        "Há uma gravação em andamento! Fechar agora pode corromper seus arquivos.",
        "Há uma gravação em curso! Fechar agora pode corromper os seus ficheiros.",
        "¡Operación en curso! Cerrar ahora podría dañar tus archivos.",
        "Идет запись файлов! Закрытие программы может повредить данные.",
        "ディスク書き込み処理中です！今閉じるとファイルが破損する恐れがあります。"
    ],
    "msg_warned": [
        "I tried to warn you.",
        "Eu tentei avisar.",
        "Tentei avisar.",
        "Intenté avisar.",
        "Я пытался предупредить.",
        "警告しました。"
    ],
    "modal_game_profile": ["PS2Manager - Game Profile", "PS2Manager - Perfil do Jogo", "PS2Manager - Perfil do Jogo", "PS2Manager - Perfil del Juego", "PS2Manager - Профиль игры", "PS2Manager - ゲームプロファイル"],
    "modal_rollback": ["PS2Manager - Version Rollback", "PS2Manager - Histórico de Versões", "PS2Manager - Histórico de Versões", "PS2Manager - Historial de Versiones", "PS2Manager - Откат версии", "PS2Manager - バージョン履歴"],
    "ver_empty": ["No previous executables in /VER folder.", "Nenhum executável anterior na pasta /VER.", "Nenhum executável anterior na pasta /VER.", "No hay ejecutables anteriores en /VER.", "Нет предыдущих исполняемых файлов в /VER.", "/VERフォルダに以前の実行ファイルがありません。"],
    "ver_launch": ["Launch", "Executar", "Executar", "Ejecutar", "Запустить", "実行"],
    "game_id": ["Game ID", "ID do Jogo", "ID do Jogo", "ID del Juego", "ID игры", "ゲームID"],
    "game_format": ["Format / Media", "Formato / Mídia", "Formato / Multimédia", "Formato / Medio", "Формат / Носитель", "フォーマット/メディア"],
    "game_size": ["Size", "Tamanho", "Tamanho", "Tamaño", "Размер", "サイズ"],
    "game_region": ["Region", "Região", "Região", "Región", "Регион", "リージョン"],
    "recovery_title": ["Recovery", "Recuperação", "Recuperação", "Recuperación", "Восстановление", "復元"],
    "recovery_msg": ["Interrupted file transfer detected from a previous session!\nDo you want to open the queue?", "Transferência interrompida anteriormente detectada!\nDeseja abrir a área de instalação?", "Transferência interrompida anteriormente detetada!\nDeseja abrir a área de instalação?", "¡Se detectó una transferencia interrumpida anterior!\n¿Desea revisar?", "Обнаружена прерванная передача файлов!\nОткрыть установщик?", "以前の中断されたファイル転送が検出されました！\nインストール画面を開きますか？"],
    "iso_files": ["PS2 Game Images", "Jogos de PS2 (*.iso *.zso *.bin)", "Jogos de PS2 (*.iso *.zso *.bin)", "Juegos de PS2 (*.iso *.zso *.bin)", "Образы PS2 (*.iso *.zso *.bin)", "PS2イメージ (*.iso *.zso *.bin)"],
    "news_btn_update": ["Update", "Fazer Update", "Fazer Update", "Actualizar", "Обновить", "アップデート"],
    "set_bg_title": ["CUSTOM BACKGROUND, TRANSPARENCY & BLUR", "PERSONALIZAR FUNDO, TRANSPARÊNCIA & BORRÃO", "PERSONALIZAR FUNDO, TRANSPARÊNCIA & DESFOQUE", "FONDO PERSONALIZADO, TRANSPARENCIA Y DESENFOQUE", "ФОН, ПРОЗРАЧНОСТЬ И РАЗМЫТИЕ", "カスタム背景・透明度・ぼかし設定"],
    "set_bg_img": ["🖼 Background Image", "🖼 Imagem de Fundo", "🖼 Imagem de Fundo", "🖼 Imagen de Fondo", "🖼 Фоновое фото", "🖼 背景画像を選択"],
    "set_bg_col": ["🎨 Background Color", "🎨 Cor do Fundo", "🎨 Cor do Fundo", "🎨 Color de Fondo", "🎨 Цвет фона", "🎨 背景色を選択"],
    "set_bg_reset": ["↺ Reset", "↺ Padrão", "↺ Padrão", "↺ Restablecer", "↺ Сброс", "↺ リセット"],
    "set_bg_transp": ["Global Background Transparency", "Transparência do Fundo", "Transparência do Fundo", "Transparencia del Fondo", "Прозрачность фона", "全体の背景透明度"],
    "set_bg_blur": ["Background Frosted Blur", "Borrão do Fundo (Blur)", "Desfoque do Fundo (Blur)", "Desenfoque del Fondo (Blur)", "Размытие фона (Blur)", "背景のぼかし (Blur)"]
}


class DataManager:
    def __init__(self):
        self.filepath = os.path.join(APP_DATA_DIR, "data.json")
        self.config = {
            "theme": "Midnight Neon",
            "sound_enabled": True,
            "tab_sound_enabled": True,
            "custom_pcsx2_path": "",
            "language": "PT_BR",
            "setup_done": False,
            "ps2_model": "SCPH-9000x",
            "ps2_type": "SLIM",
            "animations": True,
            "anim_style": "Slide",
            "laptop_mode": False,  # Mantém a chave no JSON para compatibilidade; representa o Modo Batata!
            "bgm_enabled": True,
            "last_cht_folder": "",
            "show_console": False,
            "last_news_id": 0,
            "bg_transparency": 0,
            "bg_blur": 0,
            "custom_bg_color": "",
            "custom_bg_image": ""
        }
        self.library = []
        self.state = None
        self.load()

    def save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump({"config": self.config, "library": self.library, "state": self.state}, f, indent=4)
        except Exception:
            pass

    def load(self):
        if not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                parsed = json.load(f)
            self.config.update(parsed.get("config", {}))
            if self.config.get("language") not in LANGS:
                self.config["language"] = "PT_BR"
            if self.config.get("theme") not in THEMES:
                self.config["theme"] = "Midnight Neon"
            if self.config.get("anim_style") not in ANIM_STYLES:
                self.config["anim_style"] = "Slide"
            self.library = parsed.get("library", [])
            self.state = parsed.get("state", None)
        except Exception:
            pass


db = DataManager()
apply_console_visibility(db.config.get("show_console", False))


class ConfigManager:
    _pal_key = None
    _pal_cache = None

    @property
    def data(self):
        return db.config

    def save(self):
        self._pal_key = None
        db.save()

    def invalidate_palette(self):
        self._pal_key = None

    def is_potato(self):
        """Retorna True se o Modo Batata estiver ativado."""
        return bool(self.data.get("laptop_mode", False))

    def apply_theme(self):
        self._pal_key = None
        th = self.data.get("theme", "Midnight Neon")
        if th in THEMES:
            ctk.set_appearance_mode("light" if th == "Light" else "dark")
        else:
            ctk.set_appearance_mode("dark")

    @staticmethod
    def _hex_rgb(h):
        s = str(h or "").strip().lstrip("#")
        if len(s) == 6:
            try:
                return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
            except Exception:
                pass
        return None

    @staticmethod
    def _rgb_hex(rgb):
        r, g, b = [max(0, min(255, int(round(x)))) for x in rgb]
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def _mix(c1, c2, ratio):
        return tuple(c1[i] * (1.0 - ratio) + c2[i] * ratio for i in range(3))

    def _build_palette(self):
        th = self.data.get("theme", "Midnight Neon")
        if th not in THEMES:
            th = "Midnight Neon"
        pal = dict(THEMES[th])
        is_light = (th == "Light")

        c_col = str(self.data.get("custom_bg_color", "") or "").strip()
        c_img = str(self.data.get("custom_bg_image", "") or "").strip()
        blur_pct = max(0, min(100, int(self.data.get("bg_blur", 0) or 0)))
        transp_pct = max(0, min(100, int(self.data.get("bg_transparency", 0) or 0)))

        base_rgb = self._hex_rgb(c_col)
        if base_rgb is None and c_img and PIL_SUPPORT and os.path.exists(c_img):
            try:
                with Image.open(c_img) as im:
                    px = list(im.convert("RGB").resize((8, 8)).getdata())
                avg = [sum(p[i] for p in px) / len(px) for i in range(3)]
                base_rgb = self._mix(avg, (240, 244, 248) if is_light else (8, 11, 18), 0.58)
            except Exception:
                base_rgb = None

        if base_rgb is None and blur_pct == 0 and transp_pct == 0:
            return pal

        if base_rgb is None:
            base_rgb = self._hex_rgb(pal["bg_main"]) or (9, 13, 22)

        if blur_pct > 0:
            frost = (232, 238, 246) if is_light else (24, 30, 44)
            base_rgb = self._mix(base_rgb, frost, (blur_pct / 100.0) * 0.34)

        lum = 0.299 * base_rgb[0] + 0.587 * base_rgb[1] + 0.114 * base_rgb[2]
        light_surface = lum > 155
        sb_rgb = self._mix(base_rgb, (215, 223, 234) if light_surface else (2, 4, 8), 0.30)
        elev = 0.14 * (1.0 - (transp_pct / 100.0) * 0.55)
        card_rgb = self._mix(base_rgb, (255, 255, 255) if not light_surface else (255, 255, 255), elev if not light_surface else 0.45)
        hover_rgb = self._mix(card_rgb, (255, 255, 255) if not light_surface else (200, 212, 226), 0.08)
        chip_rgb = self._mix(card_rgb, self._hex_rgb(pal["accent"]) or (59, 130, 246), 0.14)
        brd_rgb = self._mix(card_rgb, (255, 255, 255) if not light_surface else (148, 163, 184), 0.16 + (blur_pct / 100.0) * 0.10)

        pal["bg_main"] = self._rgb_hex(base_rgb)
        pal["bg_sidebar"] = self._rgb_hex(sb_rgb)
        pal["card_base"] = self._rgb_hex(card_rgb)
        pal["card_hover"] = self._rgb_hex(hover_rgb)
        pal["chip_bg"] = self._rgb_hex(chip_rgb)
        pal["border"] = self._rgb_hex(brd_rgb)
        pal["text_main"] = "#0F172A" if light_surface else "#F8FAFC"
        pal["text_muted"] = "#475569" if light_surface else "#94A3B8"
        return pal

    def get_color(self, key):
        c_img = str(self.data.get("custom_bg_image", "") or "")
        k_sig = (
            self.data.get("theme", "Midnight Neon"),
            self.data.get("custom_bg_color", ""),
            c_img,
            int(self.data.get("bg_blur", 0) or 0),
            int(self.data.get("bg_transparency", 0) or 0),
        )
        if k_sig != self._pal_key or self._pal_cache is None:
            self._pal_cache = self._build_palette()
            self._pal_key = k_sig
        return self._pal_cache.get(key, "#000000")

    def get_hover(self, hover_key="card_hover", base_key="card_base"):
        if self.is_potato():
            return self.get_color(base_key)
        return self.get_color(hover_key)

    def get_radius(self, widget_type="default"):
        # Modo Batata: 0 arredondamento em todos os widgets (renderização GDI reta ultra-rápida!)
        if self.is_potato():
            return 0
        if widget_type == "button":
            return 10
        if widget_type == "card":
            return 14
        if widget_type == "entry":
            return 9
        if widget_type == "chip":
            return 8
        return 10

    def get_border_width(self):
        # Modo Batata elimina bordas extras para reduzir camadas do Canvas pela metade
        return 0 if self.is_potato() else 1


cfg = ConfigManager()
cfg.apply_theme()


def t(key):
    lang_code = cfg.data.get("language", "PT_BR")
    idx = LANGS.get(lang_code, 1)
    items = TRANSLATIONS.get(key)
    if not items:
        return key
    if idx < len(items):
        return items[idx]
    return items[0]


def format_size(bytes_size):
    if bytes_size <= 0:
        return "0 B"
    sz = float(bytes_size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if sz < 1024.0:
            return f"{sz:.2f} {unit}"
        sz /= 1024.0
    return f"{sz:.2f} PB"


class TransferLockManager:
    """Proteção ativa contra corrupção de arquivos usando o Python embutido."""
    _active_count = 0
    _lock_path = os.path.join(APP_DATA_DIR, "active_transfer.lock")
    _watchdog_proc = None

    @classmethod
    def is_busy(cls):
        return cls._active_count > 0

    @classmethod
    def acquire(cls, task_desc="Operação em andamento"):
        cls._active_count += 1
        try:
            with open(cls._lock_path, "w", encoding="utf-8") as f:
                f.write(f"PID={os.getpid()}\nTASK={task_desc}\nTIME={time.time()}\n")
            if not cls._watchdog_proc or cls._watchdog_proc.poll() is not None:
                cls._spawn_watchdog()
        except Exception:
            pass

    @classmethod
    def release(cls):
        cls._active_count = max(0, cls._active_count - 1)
        if cls._active_count == 0:
            try:
                if os.path.exists(cls._lock_path):
                    os.remove(cls._lock_path)
            except Exception:
                pass

    @classmethod
    def _spawn_watchdog(cls):
        try:
            cmd = build_internal_python_cmd("--watchdog", str(os.getpid()), cls._lock_path, t("msg_warned"))
            cls._watchdog_proc = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW | getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
            )
        except Exception:
            pass


class TransferStateManager:
    @staticmethod
    def save(job_type, src, dst, current_file, copied_bytes, total_bytes, extra_data=None):
        data = {
            "type": job_type, "src": src, "dst": dst, "file": current_file,
            "copied": copied_bytes, "total": total_bytes
        }
        if extra_data:
            data.update(extra_data)
        db.state = data
        db.save()

    @staticmethod
    def clear():
        db.state = None
        db.save()

    @staticmethod
    def load():
        return db.state


class SoundManager:
    """Gerenciador de Áudio corrigido: respeita mudo global, som de aba separado e Modo Batata."""
    def __init__(self):
        self.enabled = bool(cfg.data.get("sound_enabled", True))
        self.tab_sound_enabled = bool(cfg.data.get("tab_sound_enabled", True))
        self.bgm_enabled = bool(cfg.data.get("bgm_enabled", True))
        self.ch_sfx = None
        self.snd_click = self.snd_tab = self.snd_close = self.snd_success = self.snd_error = None
        if PYGAME_SUPPORT:
            try:
                self.ch_sfx = pygame.mixer.Channel(1)

                def load_snd(name):
                    p = get_res_path(os.path.join("sounds", name))
                    return pygame.mixer.Sound(p) if os.path.exists(p) else None

                self.snd_click = load_snd("sound_C.wav")
                self.snd_tab = load_snd("sound_A.wav")
                self.snd_close = load_snd("sound_FF.wav")
                self.snd_success = load_snd("sound_CC.wav")
                self.snd_error = load_snd("sound_E.wav")
                self.update_bgm(self.bgm_enabled)
            except Exception:
                pass

    def sync_from_config(self):
        self.enabled = bool(cfg.data.get("sound_enabled", True))
        self.tab_sound_enabled = bool(cfg.data.get("tab_sound_enabled", True))
        if not self.enabled and PYGAME_SUPPORT and self.ch_sfx:
            try:
                self.ch_sfx.stop()
            except Exception:
                pass
        effective_bgm = bool(cfg.data.get("bgm_enabled", True)) and not cfg.is_potato()
        self.update_bgm(effective_bgm)

    def update_bgm(self, state):
        self.bgm_enabled = bool(state) and not cfg.is_potato()
        if not PYGAME_SUPPORT:
            return
        bgm_path = get_res_path(os.path.join("sounds", "soundF.mp3"))
        if self.bgm_enabled and os.path.exists(bgm_path):
            try:
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(bgm_path)
                    pygame.mixer.music.set_volume(0.35)
                    pygame.mixer.music.play(-1)
                else:
                    pygame.mixer.music.unpause()
            except Exception:
                pass
        else:
            try:
                pygame.mixer.music.pause()
                pygame.mixer.music.stop()
            except Exception:
                pass

    def _play_freq(self, freqs_durations):
        if not self.enabled or not SOUND_SUPPORT:
            return
        threading.Thread(
            target=lambda: [winsound.Beep(f, d) for f, d in freqs_durations],
            daemon=True
        ).start()

    def play_click(self):
        if not self.enabled:
            return
        if PYGAME_SUPPORT and self.snd_click and self.ch_sfx:
            try:
                self.ch_sfx.play(self.snd_click)
                return
            except Exception:
                pass
        self._play_freq([(4000, 10)])

    def play_tab(self):
        if not self.enabled or not self.tab_sound_enabled:
            return
        if PYGAME_SUPPORT and self.snd_tab and self.ch_sfx:
            try:
                self.ch_sfx.play(self.snd_tab)
                return
            except Exception:
                pass
        self._play_freq([(3000, 15)])

    def play_close(self):
        if not self.enabled:
            return
        if PYGAME_SUPPORT and self.snd_close and self.ch_sfx:
            try:
                self.ch_sfx.play(self.snd_close)
                return
            except Exception:
                pass
        self._play_freq([(1000, 100), (800, 150)])

    def play_success(self):
        if not self.enabled:
            return
        if PYGAME_SUPPORT and self.snd_success and self.ch_sfx:
            try:
                self.ch_sfx.play(self.snd_success)
                return
            except Exception:
                pass
        self._play_freq([(1200, 40), (1800, 60)])

    def play_warning(self):
        if not self.enabled:
            return
        if PYGAME_SUPPORT and self.snd_error and self.ch_sfx:
            try:
                self.ch_sfx.play(self.snd_error)
                return
            except Exception:
                pass
        self._play_freq([(900, 70), (650, 90)])

    def play_error(self):
        if not self.enabled:
            return
        if PYGAME_SUPPORT and self.snd_error and self.ch_sfx:
            try:
                self.ch_sfx.play(self.snd_error)
                return
            except Exception:
                pass
        self._play_freq([(220, 140), (180, 160)])

    def play_usb(self, connected=True):
        if not self.enabled:
            return
        if connected:
            self._play_freq([(800, 40), (1200, 40), (1800, 80)])
        else:
            self._play_freq([(1800, 40), (1200, 40), (800, 80)])


sound_fx = SoundManager()


class GameAnalyzer:
    REGION_MAP = {
        'SLUS': 'USA', 'SCUS': 'USA', 'SLES': 'Europe', 'SCES': 'Europe',
        'SLPS': 'Japan', 'SLPM': 'Japan', 'SCPS': 'Japan', 'SCAJ': 'Asia', 'SLKA': 'Korea'
    }

    @staticmethod
    def extract_game_id(file_path):
        """Extrai o Game ID oficial limpo da imagem ISO/ZSO/BIN ou do nome do arquivo."""
        fname = os.path.basename(file_path)
        m_name = re.search(r'([Ss][LClc][UEPAKuepak][SMJAsmja][_\-]?\d{3}\.?\d{2})', fname)
        if m_name:
            raw = m_name.group(1).upper().replace('_', '-').replace('.', '')
            if len(raw) == 9 and raw[4] != '-':
                raw = raw[:4] + '-' + raw[4:]
            return raw
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(4 * 1024 * 1024)
                match = re.search(rb'([Ss][LClc][UEPAKuepak][SMJAsmja]_?\d{3}\.?\d{2})', chunk)
                if match:
                    raw = match.group(1).decode('latin1', errors='ignore').upper().replace('_', '-').replace('.', '')
                    if len(raw) == 9 and raw[4] != '-':
                        raw = raw[:4] + '-' + raw[4:]
                    return raw
        except Exception:
            pass
        return "Unknown"

    @staticmethod
    def clean_display_title(filename):
        base = os.path.splitext(filename)[0]
        base = re.sub(r'^[Ss][LClc][UEPAKuepak][SMJAsmja][_\-]?\d{3}\.?\d{2}\.', '', base)
        return base.replace('_', ' ').strip() or os.path.splitext(filename)[0]

    @staticmethod
    def analyze(file_path):
        size = os.stat(file_path).st_size
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        game_id = GameAnalyzer.extract_game_id(file_path)
        reg = "Unknown"
        if game_id != "Unknown" and len(game_id) >= 4:
            reg = GameAnalyzer.REGION_MAP.get(game_id[:4], "Unknown")
        media_type = "CD" if size < (700 * 1024 * 1024) else "DVD"
        return {
            "path": file_path,
            "name": GameAnalyzer.clean_display_title(filename),
            "id": game_id,
            "region": reg,
            "size_bytes": size,
            "size_str": format_size(size),
            "format": ext[1:].upper() if ext else "N/A",
            "media_type": media_type,
            "status": "BAD" if game_id == "Unknown" else "EXCELLENT",
            "video_mode": "Auto",
            "resolution": "Default"
        }


class LibraryManager:
    @property
    def games(self):
        return db.library

    @games.setter
    def games(self, val):
        db.library = val

    def __init__(self):
        self._last_sync_ts = 0.0
        self.sync_drives(force=True)

    def sync_drives(self, force=False):
        """Remove jogos fantasmas cujos arquivos foram apagados ou desconectados."""
        now = time.monotonic()
        if not force and (now - self._last_sync_ts) < 4.0:
            return
        self._last_sync_ts = now
        valid = []
        for g in self.games:
            p = g.get('path', '')
            if p and os.path.exists(p):
                valid.append(g)
        if len(valid) != len(self.games):
            self.games = valid
            db.save()

    def sync(self):
        self.sync_drives(force=True)

    def scan_directory(self, folder_path):
        """Escaneia recursivamente uma pasta por arquivos .iso, .zso e .bin de PS2."""
        if not folder_path or not os.path.exists(folder_path):
            return 0
        added = 0
        for root, _, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith(('.iso', '.zso', '.bin')):
                    full_p = os.path.join(root, f)
                    try:
                        info = GameAnalyzer.analyze(full_p)
                        if self.add(info):
                            added += 1
                    except Exception:
                        pass
        db.save()
        return added

    def add(self, game_data):
        for i, g in enumerate(self.games):
            if os.path.normcase(g['path']) == os.path.normcase(game_data['path']):
                game_data['video_mode'] = g.get('video_mode', 'Auto')
                game_data['resolution'] = g.get('resolution', 'Default')
                self.games[i] = game_data
                db.save()
                return False
        self.games.append(game_data)
        db.save()
        return True

    def stats(self):
        return {
            "total": len(self.games),
            "size_str": format_size(sum(g.get("size_bytes", 0) for g in self.games))
        }
