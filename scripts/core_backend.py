import os
import sys
import json
import time
import re
import threading
import shutil
import psutil
import subprocess
import ctypes
import struct
import zlib
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

class AppLogger:
    def __init__(self):
        self.logs = []
        self.log("PS2Manager Core Engine Initialized.", "INFO")

    def log(self, msg, level="INFO"):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{timestamp}] [{level}] {msg}"
        self.logs.append(entry)
        print(entry)

    def export(self):
        try:
            desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop")
            filename = os.path.join(desktop, f"PS2Manager_Diagnostic_Report_{int(time.time())}.log")
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(self.logs))
            return filename
        except Exception:
            return None

sys_logger = AppLogger()

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
    import win32com.client
    WIN32COM_SUPPORT = True
except Exception:
    WIN32COM_SUPPORT = False

APP_NAME = "PS2 MANAGER"
APP_VERSION = "V1.07"
VERSION_COLOR_CODE = '7'

THEMES = {
    "Dark": {
        "bg_main": "#080C14", "bg_sidebar": "#04070D", "card_base": "#101623",
        "card_hover": "#172033", "accent": "#2563EB", "accent_hover": "#1D4ED8",
        "text_main": "#F1F5F9", "text_muted": "#64748B", "success": "#10B981",
        "warning": "#F59E0B", "danger": "#EF4444", "border": "#1E293B",
        "chip_bg": "#1E293B", "highlight": "#38BDF8"
    },
    "Light": {
        "bg_main": "#F8FAFC", "bg_sidebar": "#EDEFE8", "card_base": "#FFFFFF",
        "card_hover": "#F1F5F9", "accent": "#0284C7", "accent_hover": "#0369A1",
        "text_main": "#0F172A", "text_muted": "#64748B", "success": "#059669",
        "warning": "#D97706", "danger": "#DC2626", "border": "#CBD5E1",
        "chip_bg": "#E2E8F0", "highlight": "#0284C7"
    },
    "Ocean": {
        "bg_main": "#0B132B", "bg_sidebar": "#070C1E", "card_base": "#1C2541",
        "card_hover": "#253259", "accent": "#00B4D8", "accent_hover": "#0096C7",
        "text_main": "#FFFFFF", "text_muted": "#8D99AE", "success": "#06D6A0",
        "warning": "#FFD166", "danger": "#EF476F", "border": "#28385E",
        "chip_bg": "#223152", "highlight": "#90E0EF"
    }
}

# Idiomas oficiais: EN=English, PT_BR=Português (Brasil), PT=Português (Portugal), ES=Español, RU=Русский, JA=日本語
LANGS = {"EN": 0, "PT_BR": 1, "PT": 2, "ES": 3, "RU": 4, "JA": 5}

TRANSLATIONS = {
    # Navegação
    "tab_dash": ["DASHBOARD", "PAINEL", "PAINEL", "PANEL", "ПАНЕЛЬ", "ダッシュボード"],
    "tab_lib": ["LIBRARY", "BIBLIOTECA", "BIBLIOTECA", "BIBLIOTECA", "БИБЛИОТЕКА", "ライブラリ"],
    "tab_install": ["INSTALL TO USB", "INSTALAR NO PENDRIVE", "INSTALAR NO PENDRIVE", "INSTALAR EN USB", "УСТАНОВКА НА USB", "USBにインストール"],
    "tab_batch": ["BATCH QUEUE", "FILA EM LOTE", "FILA EM LOTE", "COLA POR LOTES", "ПАКЕТНАЯ ОЧЕРЕДЬ", "一括キュー"],
    "tab_burn": ["BURN DVD", "GRAVAR DVD", "GRAVAR DVD", "GRABAR DVD", "ЗАПИСЬ DVD", "DVD書き込み"],
    "tab_emu": ["PCSX2 EMULATOR", "EMULADOR PCSX2", "EMULADOR PCSX2", "EMULADOR PCSX2", "ЭМУЛЯТОР PCSX2", "PCSX2エミュレータ"],
    "tab_usb": ["USB MANAGER", "GERENCIADOR USB", "GESTOR USB", "GESTOR USB", "USB МЕНЕДЖЕР", "USBマネージャー"],
    "sub_clone": ["  ↳ CLONE DRIVE", "  ↳ CLONAR PENDRIVE", "  ↳ CLONAR PENDRIVE", "  ↳ CLONAR PENDRIVE", "  ↳ КЛОНИРОВАТЬ ДИСК", "  ↳ ドライブ複製"],
    "tab_mig": ["FORMAT & MIGRATE", "FORMATAR E MIGRAR", "FORMATAR E MIGRAR", "FORMATEAR Y MIGRAR", "ФОРМАТ И МИГРАЦИЯ", "フォーマット＆移行"],
    "tab_apps": ["OPL APPS", "OPL APPS", "OPL APPS", "OPL APPS", "OPL ПРИЛОЖЕНИЯ", "OPLアプリ"],
    "tab_iso": ["ISO EXTRACT / REPACK", "EXTRAIR / REEMPACOTAR", "EXTRAIR / REEMPACOTAR", "EXTRAER / REEMPAQUETAR", "ИЗВЛЕЧЕНИЕ / СБОРКА ISO", "ISO展開/再パック"],
    "tab_rip": ["DVD/CD RIPPER", "RIPADOR DVD/CD", "RIPADOR DVD/CD", "RIPEAR DVD/CD", "РИППЕР DVD/CD", "DVD/CDリッパー"],
    "tab_util": ["USB UTIL (SPLIT)", "USB UTIL (DIVIDIR)", "USB UTIL (DIVIDIR)", "USB UTIL (DIVIDIR)", "USB UTIL (РАЗДЕЛЕНИЕ)", "USB UTIL（分割）"],
    "tab_disc": ["DISC ANALYZER", "ANALISADOR DE DISCO", "ANALISADOR DE DISCO", "ANALIZADOR DE DISCO", "АНАЛИЗАТОР ДИСКА", "ディスク分析"],
    "tab_set": ["SETTINGS", "CONFIGURAÇÕES", "DEFINIÇÕES", "AJUSTES", "НАСТРОЙКИ", "設定"],
    "tab_more": ["MORE TOOLS", "MAIS FERRAMENTAS", "MAIS FERRAMENTAS", "MÁS HERRAMIENTAS", "ДРУГИЕ ИНСТРУМЕНТЫ", "その他のツール"],
    "tab_patcher": ["ISO PATCHER & ESR", "ISO PATCHER E ESR", "ISO PATCHER E ESR", "ISO PATCHER Y ESR", "ПАТЧЕР ISO И ESR", "ISOパッチャー＆ESR"],
    "tab_cht": ["CHEAT ENGINE", "CRIADOR DE CHEATS", "CRIADOR DE CHEATS", "GESTOR DE CHEATS", "ЧИТЫ ДЛЯ OPL", "チート管理"],
    "tab_apa": ["APA HDD EXPLORER", "EXPLORADOR HDD APA", "EXPLORADOR HDD APA", "EXPLORADOR HDD APA", "ПРОВОДНИК APA HDD", "APA HDDエクスプローラー"],
    "tab_art": ["COVER DOWNLOADER", "BAIXADOR DE CAPAS", "DESCARREGADOR DE CAPAS", "DESCARGADOR DE CARÁTULAS", "ЗАГРУЗЧИК ОБЛОЖЕК", "ジャケット画像取得"],
    "btn_back": ["<- GO BACK", "<- VOLTAR", "<- VOLTAR", "<- VOLVER", "<- НАЗАД", "<- 戻る"],
    "btn_select": ["SELECT", "SELECIONAR", "SELECIONAR", "SELECCIONAR", "ВЫБРАТЬ", "選択"],
    "btn_browse": ["BROWSE", "PROCURAR", "PROCURAR", "EXAMINAR", "ОБЗОР", "参照"],
    "btn_cancel": ["CANCEL", "CANCELAR", "CANCELAR", "CANCELAR", "ОТМЕНА", "キャンセル"],
    "btn_close": ["CLOSE", "FECHAR", "FECHAR", "CERRAR", "ЗАКРЫТЬ", "閉じる"],
    "btn_refresh": ["REFRESH", "ATUALIZAR", "ATUALIZAR", "ACTUALIZAR", "ОБНОВИТЬ", "更新"],
    "btn_save": ["SAVE", "SALVAR", "GUARDAR", "GUARDAR", "СОХРАНИТЬ", "保存"],
    "confirm": ["Confirm", "Confirmar", "Confirmar", "Confirmar", "Подтверждение", "確認"],
    "success": ["Success", "Sucesso", "Sucesso", "Éxito", "Успешно", "成功"],
    "error": ["Error", "Erro", "Erro", "Error", "Ошибка", "エラー"],
    "warning": ["Warning", "Aviso", "Aviso", "Aviso", "Предупреждение", "警告"],
    "warn_title": ["Important Warning", "Aviso Importante", "Aviso Importante", "Aviso Importante", "Важное предупреждение", "重要なお知らせ"],

    # Dashboard
    "dash_games": ["LIBRARY GAMES", "JOGOS NA BIBLIOTECA", "JOGOS NA BIBLIOTECA", "JUEGOS EN BIBLIOTECA", "ИГР В БИБЛИОТЕКЕ", "登録済みゲーム"],
    "dash_usb": ["CONNECTED DRIVES", "UNIDADES CONECTADAS", "UNIDADES LIGADAS", "UNIDADES CONECTADAS", "ПОДКЛЮЧЕННЫЕ ДИСКИ", "接続ドライブ"],
    "dash_size": ["TOTAL SIZE", "TAMANHO TOTAL", "TAMANHO TOTAL", "TAMAÑO TOTAL", "ОБЩИЙ РАЗМЕР", "合計容量"],

    # Biblioteca
    "lib_scan": ["+ SCAN FOLDER", "+ ESCANEAR PASTA", "+ VERIFICAR PASTA", "+ ESCANEAR CARPETA", "+ СКАНИРОВАТЬ ПАПКУ", "+ フォルダをスキャン"],
    "lib_search": ["Search game by title or ID...", "Pesquisar por título ou ID...", "Pesquisar por título ou ID...", "Buscar por título o ID...", "Поиск по названию или ID...", "タイトルまたはIDで検索..."],
    "lib_scan_done": ["Scan complete!", "Escaneamento concluído!", "Verificação concluída!", "¡Escaneo completado!", "Сканирование завершено!", "スキャン完了！"],
    "lib_btn_close": ["CLOSE", "FECHAR", "FECHAR", "CERRAR", "ЗАКРЫТЬ", "閉じる"],
    "lib_btn_test": ["TEST ON PCSX2", "TESTAR NO PCSX2", "TESTAR NO PCSX2", "PROBAR EN PCSX2", "ТЕСТ В PCSX2", "PCSX2でテスト"],
    "lib_btn_inst": ["INSTALL TO USB", "INSTALAR NO PENDRIVE", "INSTALAR NO PENDRIVE", "INSTALAR EN USB", "УСТАНОВИТЬ НА USB", "USBに転送"],
    "lib_btn_rem": ["REMOVE", "REMOVER", "REMOVER", "ELIMINAR", "УДАЛИТЬ", "削除"],
    "msg_remove_confirm": ["Do you want to remove this game from the library view?", "Deseja remover este jogo da visualização da biblioteca?", "Deseja remover este jogo da biblioteca?", "¿Deseas eliminar este juego de la biblioteca?", "Удалить эту игру из списка библиотеки?", "このゲームをライブラリ表示から削除しますか？"],
    "cfg_vid": ["Video Output Mode:", "Modo de Saída de Vídeo:", "Modo de Saída de Vídeo:", "Modo de Video:", "Режим видеовыхода:", "ビデオ出力モード:"],
    "cfg_res": ["GSM Resolution Override:", "Resolução Forçada GSM:", "Resolução Forçada GSM:", "Resolución GSM:", "Разрешение GSM:", "GSM解像度指定:"],
    "cfg_save": ["SAVE CONFIG", "SALVAR CONFIGURAÇÃO", "GUARDAR CONFIGURAÇÃO", "GUARDAR CFG", "СОХРАНИТЬ", "設定保存"],
    "cfg_succ": ["Config saved successfully at:", "Configuração salva com sucesso em:", "Configuração guardada com sucesso em:", "Configuración guardada en:", "Конфигурация успешно сохранена в:", "設定が保存されました:"],

    # Instalação 1-Clique no USB
    "inst_step1": ["1. Select Game ISO / Image:", "1. Selecione o arquivo ISO / Jogo:", "1. Selecione o ficheiro ISO / Jogo:", "1. Selecciona la imagen ISO / Juego:", "1. Выберите файл ISO / образ игры:", "1. ゲームISO/イメージを選択:"],
    "inst_step2": ["2. Game Title (Max 32 chars):", "2. Nome do Jogo (Máx 32 letras):", "2. Nome do Jogo (Máx 32 letras):", "2. Nombre del Juego (Máx 32):", "2. Название игры (до 32 симв.):", "2. ゲーム名（最大32文字）:"],
    "inst_step3": ["3. Target USB Storage Drive:", "3. Dispositivo USB de Destino:", "3. Dispositivo USB de Destino:", "3. Unidad USB de Destino:", "3. Целевой USB-накопитель:", "3. 対象USBストレージドライブ:"],
    "inst_chk_art": ["Download high-res cover art automatically", "Baixar capa em alta resolução automaticamente", "Descarregar capa em alta resolução automaticamente", "Descargar carátula automáticamente", "Скачивать обложку автоматически", "高画質ジャケット画像を自動取得する"],
    "inst_btn_start": ["START INSTALLATION TO USB", "INICIAR INSTALAÇÃO NO PENDRIVE", "INICIAR INSTALAÇÃO NO PENDRIVE", "INICIAR INSTALACIÓN EN USB", "НАЧАТЬ УСТАНОВКУ НА USB", "USBへのインストールを開始"],
    "inst_status_ready": ["Ready to install.", "Pronto para instalar.", "Pronto para instalar.", "Listo para instalar.", "Готов к установке.", "インストールの準備完了。"],
    "inst_status_writing": ["Writing game to storage...", "Gravando jogo no dispositivo...", "A gravar jogo no dispositivo...", "Escribiendo en la unidad...", "Запись игры на накопитель...", "ストレージに書き込み中..."],
    "inst_succ_msg": ["Game installed successfully to USB!", "Jogo instalado com sucesso no pendrive!", "Jogo instalado com sucesso no pendrive!", "¡Juego instalado con éxito en USB!", "Игра успешно установлена на USB!", "USBにゲームが正常にインストールされました！"],
    "inst_err_select": ["Please select game file and target USB.", "Selecione o arquivo do jogo e o pendrive.", "Selecione o ficheiro do jogo e o pendrive.", "Selecciona el archivo y la unidad USB.", "Выберите файл игры и целевой USB.", "ゲームファイルと対象USBを選択してください。"],

    # Fila em Lote (Batch)
    "batch_add": ["+ ADD ISO FILES", "+ ADICIONAR ARQUIVOS ISO", "+ ADICIONAR FICHEIROS ISO", "+ AÑADIR ARCHIVOS ISO", "+ ДОБАВИТЬ ISO ФАЙЛЫ", "+ ISOファイル追加"],
    "batch_folder": ["+ ADD FOLDER", "+ ADICIONAR PASTA", "+ ADICIONAR PASTA", "+ AÑADIR CARPETA", "+ ДОБАВИТЬ ПАПКУ", "+ フォルダ追加"],
    "batch_clear": ["CLEAR QUEUE", "LIMPAR FILA", "LIMPAR FILA", "LIMPIAR COLA", "ОЧИСТИТЬ ОЧЕРЕДЬ", "キューをクリア"],
    "batch_drv": ["Target USB Drive:", "Dispositivo de Destino:", "Dispositivo de Destino:", "Unidad Destino:", "Целевой USB-накопитель:", "対象USBドライブ:"],
    "batch_empty": ["Queue is empty. Add games or folders above.", "Fila vazia. Adicione jogos ou pastas acima.", "Fila vazia. Adicione jogos ou pastas acima.", "Cola vacía. Añade juegos arriba.", "Очередь пуста. Добавьте игры выше.", "キューは空です。上からゲームを追加してください。"],
    "batch_prog_total": ["Overall Queue Progress:", "Progresso Geral da Fila:", "Progresso Geral da Fila:", "Progreso General:", "Общий прогресс очереди:", "キュー全体の進行状況:"] ,
    "batch_prog_item": ["Current Game Progress:", "Progresso do Jogo Atual:", "Progresso do Jogo Atual:", "Progreso del Juego Actual:", "Прогресс текущей игры:", "現在のゲームの進行状況:"],
    "batch_start": ["PROCESS ENTIRE QUEUE", "PROCESSAR FILA COMPLETA", "PROCESSAR FILA COMPLETA", "PROCESAR TODA LA COLA", "ЗАПУСТИТЬ ВСЮ ОЧЕРЕДЬ", "キュー全体を処理"],
    "batch_done_msg": ["All queued games have been processed!", "Todos os jogos da fila foram processados!", "Todos os jogos da fila foram processados!", "¡Todos los juegos han sido procesados!", "Все игры из очереди обработаны!", "キュー内のすべてのゲームが処理されました！"],

    # Gravação de DVD
    "burn_title": ["DISC BURN ENGINE", "GRAVAÇÃO DE DVD", "GRAVAÇÃO DE DVD", "GRABACIÓN DE DVD", "ПРОЖИГ DVD ДИСКОВ", "DVD書き込みエンジン"],
    "burn_iso": ["1. Select ISO Image to Burn:", "1. Selecione a Imagem ISO para Gravar:", "1. Selecione a Imagem ISO para Gravar:", "1. Selecciona la Imagen ISO:", "1. Выберите образ ISO для записи:", "1. 書き込むISOイメージを選択:"],
    "burn_drv": ["2. Optical Writer Drive:", "2. Gravador de DVD Óptico:", "2. Gravador de DVD Óptico:", "2. Grabadora de DVD:", "2. Привод для записи диска:", "2. 光学書き込みドライブ:"],
    "burn_spd": ["3. Burning Speed:", "3. Velocidade de Gravação:", "3. Velocidade de Gravação:", "3. Velocidad de Grabación:", "3. Скорость записи:", "3. 書き込み速度:"],
    "burn_spd_rec": ["4x (Recommended for PS2)", "4x (Recomendado para PS2)", "4x (Recomendado para PS2)", "4x (Recomendado PS2)", "4x (Рекомендуется для PS2)", "4x（PS2推奨）"],
    "burn_spd_max": ["Maximum Speed", "Velocidade Máxima", "Velocidade Máxima", "Velocidad Máxima", "Максимальная скорость", "最高速度"],
    "burn_btn": ["BURN DISC NOW", "GRAVAR DISCO AGORA", "GRAVAR DISCO AGORA", "GRABAR DISCO AHORA", "ЗАПИСАТЬ ДИСК СЕЙЧАС", "今すぐディスクを書き込む"],
    "burn_status_ready": ["Ready to burn disc.", "Pronto para gravar.", "Pronto para gravar.", "Listo para grabar.", "Готов к записи.", "書き込み準備完了。"],
    "burn_status_burning": ["Burning disc... Do not eject tray.", "Gravando disco... Não ejete a bandeja.", "A gravar disco... Não ejete a bandeja.", "Grabando disco... No expulsar.", "Идет запись диска... Не извлекайте лоток.", "ディスク書き込み中... トレイを取り出さないでください。"],
    "burn_done": ["Disc burned successfully!", "Disco gravado com sucesso!", "Disco gravado com sucesso!", "¡Disco grabado con éxito!", "Диск успешно записан!", "書き込みが完了しました！"],
    "burn_err_nomedia": ["No optical recorder drive detected on this computer.", "Nenhum gravador de DVD óptico detectado neste computador.", "Nenhum gravador de DVD óptico detetado neste computador.", "No se detectó grabadora de DVD en este ordenador.", "Оптический привод для записи не обнаружен на этом ПК.", "光学書き込みドライブが検出されませんでした。"],
    "burn_err_select": ["Please select an ISO file first.", "Selecione um arquivo ISO primeiro.", "Selecione um ficheiro ISO primeiro.", "Selecciona un archivo ISO primero.", "Сначала выберите файл ISO.", "まずISOファイルを選択してください。"],

    # Emulador PCSX2
    "emu_sel": ["SELECT GAME TO TEST", "SELECIONE UM JOGO PARA TESTAR", "SELECIONE UM JOGO PARA TESTAR", "SELECCIONE UN JUEGO", "ВЫБЕРИТЕ ИГРУ ДЛЯ ТЕСТА", "テストするゲームを選択"],
    "emu_btn": ["LAUNCH EMULATOR", "INICIAR EMULADOR", "INICIAR EMULADOR", "INICIAR EMULADOR", "ЗАПУСТИТЬ ЭМУЛЯТОР", "エミュレータ起動"],
    "emu_info": ["Initial launch will copy BIOS from internal resources.", "Ao iniciar pela primeira vez, o sistema configurará a BIOS.", "No primeiro arranque, o sistema configurará a BIOS.", "Al iniciar, el sistema configurará la BIOS.", "При первом запуске скопируется BIOS.", "初回起動時に内蔵リソースからBIOSが設定されます。"],
    "emu_err_notfound": ["Emulator executable not found in 'pcsx2' directory.", "Executável do emulador não encontrado na pasta 'pcsx2'.", "Executável do emulador não encontrado na pasta 'pcsx2'.", "Ejecutable no encontrado en la carpeta 'pcsx2'.", "Исполняемый файл эмулятора не найден в папке 'pcsx2'.", "pcsx2フォルダにエミュレータ実行ファイルが見つかりません。"],

    # Gerenciador USB
    "usb_ref": ["REFRESH", "ATUALIZAR", "ATUALIZAR", "ACTUALIZAR", "ОБНОВИТЬ", "更新"],
    "usb_nodrv": ["No drive selected", "Nenhuma unidade selecionada", "Nenhuma unidade selecionada", "Ninguna unidad seleccionada", "Диск не выбран", "ドライブ未選択"],
    "usb_cap": ["Capacity:", "Capacidade:", "Capacidade:", "Capacidad:", "Объем:", "容量:"],
    "usb_free": ["Free:", "Livre:", "Livre:", "Libre:", "Свободно:", "空き:"],
    "usb_fix_btn": ["CREATE / FIX OPL FOLDERS", "CRIAR / CORRIGIR ESTRUTURA DO OPL", "CRIAR / CORRIGIR ESTRUTURA DO OPL", "CREAR CARPETAS OPL", "СОЗДАТЬ СТРУКТУРУ OPL", "OPLフォルダ構造を作成"],
    "usb_fix_done": ["OPL folders created successfully!", "Pastas do OPL criadas com sucesso!", "Pastas do OPL criadas com sucesso!", "¡Carpetas OPL creadas con éxito!", "Папки OPL успешно созданы!", "OPLフォルダが正常に作成されました！"],
    "notif_usb_connected": ["USB Device Connected", "Dispositivo USB Conectado", "Dispositivo USB Ligado", "Dispositivo USB Conectado", "USB-накопитель подключен", "USBデバイスが接続されました"],

    # Extração / Repack ISO
    "iso_mode_ext": ["EXTRACT ISO", "EXTRAIR ISO", "EXTRAIR ISO", "EXTRAER ISO", "ИЗВЛЕЧЬ ISO", "ISO展開"],
    "iso_mode_rep": ["REPACK TO ISO", "REEMPACOTAR PARA ISO", "REEMPACOTAR PARA ISO", "REEMPAQUETAR A ISO", "СОБРАТЬ В ISO", "ISO再パック"],
    "iso_mode_zso": ["COMPRESS TO ZSO", "COMPRIMIR PARA ZSO", "COMPRIMIR PARA ZSO", "COMPRIMIR A ZSO", "СЖАТЬ В ZSO", "ZSO圧縮"],
    "iso_mode_bin": ["PS1 BIN -> ISO", "PS1 BIN -> ISO", "PS1 BIN -> ISO", "PS1 BIN -> ISO", "PS1 BIN -> ISO", "PS1 BIN -> ISO"],
    "iso_file": ["Source File or Folder:", "Arquivo ou Pasta de Origem:", "Ficheiro ou Pasta de Origem:", "Archivo o Carpeta de Origen:", "Исходный файл / папка:", "ソースファイル/フォルダ:"],
    "iso_out": ["Output Location:", "Local de Destino:", "Local de Destino:", "Destino:", "Куда сохранить:", "出力先:"],
    "iso_btn_ext": ["START EXTRACTION", "INICIAR EXTRAÇÃO", "INICIAR EXTRAÇÃO", "INICIAR EXTRACCIÓN", "НАЧАТЬ ИЗВЛЕЧЕНИЕ", "展開開始"],
    "iso_btn_rep": ["START REPACK", "INICIAR REEMPACOTAMENTO", "INICIAR REEMPACOTAMENTO", "INICIAR REEMPAQUETADO", "НАЧАТЬ СБОРКУ", "再パック開始"],
    "iso_btn_zso": ["START COMPRESSION", "INICIAR COMPRESSÃO", "INICIAR COMPRESSÃO", "INICIAR COMPRESIÓN", "НАЧАТЬ СЖАТИЕ", "圧縮開始"],
    "iso_btn_bin": ["CONVERT PS1 BIN", "CONVERTER PS1 BIN", "CONVERTER PS1 BIN", "CONVERTIR PS1 BIN", "КОНВЕРТИРОВАТЬ BIN", "PS1 BIN変換"],
    "iso_succ": ["Process completed successfully!", "Processo concluído com sucesso!", "Processo concluído com sucesso!", "¡Proceso completado!", "Процесс успешно завершен!", "処理が正常に完了しました！"],
    "iso_err": ["Error during process: ", "Erro durante o processo: ", "Erro durante o processo: ", "Error durante el proceso: ", "Ошибка процесса: ", "処理エラー: "],
    "iso_empty": ["Please select source and destination paths.", "Por favor, selecione origem e destino.", "Por favor, selecione origem e destino.", "Seleccione origen y destino.", "Укажите пути источника и назначения.", "ソースと出力先を指定してください。"],

    # USB Util
    "util_iso": ["Original ISO Image:", "Imagem ISO Original:", "Imagem ISO Original:", "Imagen ISO Original:", "Оригинальный образ ISO:", "元のISOイメージ:"],
    "util_dst": ["Target USB Drive / Folder:", "Pasta ou Unidade USB de Destino:", "Pasta ou Unidade USB de Destino:", "Carpeta / USB Destino:", "Целевой USB-накопитель:", "対象USBドライブ/フォルダ:"],
    "util_name": ["Game Name (Max 32 chars):", "Nome do Jogo (Máximo 32 caracteres):", "Nome do Jogo (Máximo 32 caracteres):", "Nombre del Juego (Máx 32):", "Название игры (до 32 симв.):", "ゲーム名（最大32文字）:"],
    "util_btn": ["SPLIT & GENERATE UL.CFG", "DIVIDIR E GERAR UL.CFG", "DIVIDIR E GERAR UL.CFG", "DIVIDIR Y CREAR UL.CFG", "РАЗДЕЛИТЬ И СОЗДАТЬ UL.CFG", "分割してUL.CFGを生成"],
    "util_succ": ["Game split successfully for OPL FAT32!", "Jogo dividido com sucesso para OPL (FAT32)!", "Jogo dividido com sucesso para OPL (FAT32)!", "¡Juego dividido con éxito para FAT32!", "Игра успешно разделена для FAT32!", "OPL FAT32用に分割が完了しました！"],

    # Analisador / Ripper de Disco Óptico
    "disc_drv": ["Optical Drive:", "Leitor Óptico:", "Leitor Óptico:", "Lector Óptico:", "Оптический привод:", "光学ドライブ:"],
    "disc_btn": ["ANALYZE DISC", "ANALISAR DISCO", "ANALISAR DISCO", "ANALIZAR DISCO", "АНАЛИЗИРОВАТЬ ДИСК", "ディスク分析"],
    "disc_none": ["No optical disc detected", "Nenhum disco detectado", "Nenhum disco detetado", "Ningún disco detectado", "Диск не обнаружен", "ディスクが検出されません"],
    "rip_out": ["Save to Directory:", "Salvar na Pasta:", "Guardar na Pasta:", "Guardar en:", "Папка для сохранения:", "保存先フォルダ:"],
    "rip_btn": ["RIP DISC TO IMAGE", "EXTRAIR DISCO PARA PC", "EXTRAIR DISCO PARA PC", "RIPEAR DISCO AL PC", "РИПНУТЬ ДИСК В ОБРАЗ", "ディスクをPCに抽出"],

    # Clonar e Migrar
    "clone_src": ["Source Drive (Copy From):", "Unidade de Origem (Copiar De):", "Unidade de Origem (Copiar De):", "Unidad Origen (Copiar De):", "Исходный диск (копировать из):", "コピー元ドライブ:"],
    "clone_dst": ["Destination Drive (Copy To):", "Unidade de Destino (Copiar Para):", "Unidade de Destino (Copiar Para):", "Unidad Destino (Copiar A):", "Целевой диск (копировать в):", "コピー先ドライブ:"],
    "clone_fmt_dst": ["Format destination drive prior to clone", "Formatar destino antes de iniciar", "Formatar destino antes de iniciar", "Formatear destino antes de copiar", "Форматировать целевой диск перед копированием", "コピー前にコピー先を初期化"],
    "clone_btn": ["START DRIVE CLONE", "INICIAR CLONAGEM", "INICIAR CLONAGEM", "INICIAR CLONACIÓN", "НАЧАТЬ КЛОНИРОВАНИЕ", "クローン開始"],
    "mig_drv": ["Target Removable Drive:", "Unidade USB de Destino:", "Unidade USB de Destino:", "Unidad Destino:", "Целевой накопитель:", "対象USBドライブ:"],
    "mig_fs": ["Target Filesystem:", "Sistema de Arquivos Alvo:", "Sistema de Ficheiros Alvo:", "Sistema de Archivos:", "Файловая система:", "ファイルシステム:"],
    "mig_btn": ["FORMAT & MIGRATE DRIVE", "INICIAR MIGRAÇÃO E FORMATAÇÃO", "INICIAR MIGRAÇÃO E FORMATAÇÃO", "INICIAR MIGRACIÓN", "НАЧАТЬ ФОРМАТИРОВАНИЕ", "フォーマット＆移行開始"],
    "mig_conf": ["Are you sure you want to proceed with formatting?", "Tem certeza de que deseja formatar este dispositivo?", "Tem a certeza de que deseja formatar este dispositivo?", "¿Seguro que deseas formatear la unidad?", "Вы уверены, что хотите отформатировать?", "フォーマットを続行してもよろしいですか？"],

    # Cheats
    "cht_folder": ["CHT Folder Location:", "Diretório de Cheats (CHT):", "Diretório de Cheats (CHT):", "Carpeta CHT:", "Папка CHT:", "CHTフォルダの場所:"],
    "cht_disabled": ["DISABLED", "DESATIVADO", "DESATIVADO", "DESACTIVADO", "ОТКЛЮЧЕНО", "無効"],
    "cht_enabled": ["ENABLED", "ATIVO", "ATIVO", "ACTIVADO", "АКТИВНО", "有効"],

    # APA HDD
    "apa_title": ["APA HDD EXPLORER", "EXPLORADOR DE HDD APA", "EXPLORADOR DE HDD APA", "EXPLORADOR HDD APA", "ПРОВОДНИК APA HDD", "APA HDDエクスプローラー"],
    "apa_drv": ["Physical Drive or Raw Image:", "Unidade Física ou Imagem Bruta:", "Unidade Física ou Imagem Bruta:", "Unidad Física o Imagen:", "Физический диск или образ:", "物理ドライブまたはイメージ:"],
    "apa_btn_open": ["OPEN IMG", "ABRIR IMG", "ABRIR IMG", "ABRIR IMG", "ОТКРЫТЬ IMG", "IMGを開く"],
    "apa_btn_raw": ["BACKUP TO RAW IMG", "BACKUP COMPLETO PARA IMG", "CÓPIA INTEGRAL PARA IMG", "COPIA COMPLETA A IMG", "ДАМП В RAW ОБРАЗ", "RAWイメージにバックアップ"],
    "apa_btn_ext": ["EXTRACT GAMES", "EXTRAIR JOGOS", "EXTRAIR JOGOS", "EXTRAER JUEGOS", "ИЗВЛЕЧЬ ИГРЫ", "ゲーム抽出"],

    # Capas
    "art_title": ["COVER ART DOWNLOADER", "BAIXADOR DE CAPAS DO OPL", "DESCARREGADOR DE CAPAS DO OPL", "DESCARGADOR DE CARÁTULAS", "ЗАГРУЗЧИК ОБЛОЖЕК OPL", "OPLジャケット画像ダウンローダー"],
    "art_desc": ["Fetches high-resolution game box covers automatically.", "Localiza e baixa capas em alta definição para seus jogos.", "Localiza e descarrega capas em alta definição para os seus jogos.", "Descarga carátulas en alta calidad automáticamente.", "Автоматическая загрузка обложек высокого разрешения.", "高画質ゲームパッケージ画像を自動取得します。"],
    "art_scan": ["SCAN GAMES", "ESCANEAR JOGOS", "VERIFICAR JOGOS", "ESCANEAR JUEGOS", "СКАНИРОВАТЬ", "ゲームスキャン"],
    "art_dl": ["DOWNLOAD COVERS", "BAIXAR CAPAS", "DESCARREGAR CAPAS", "DESCARGAR CARÁTULAS", "СКАЧАТЬ ОБЛОЖКИ", "画像ダウンロード"],

    # ISO Patcher
    "patch_iso": ["Original ISO File:", "Arquivo ISO Original:", "Ficheiro ISO Original:", "Archivo ISO Original:", "Оригинальный ISO:", "元のISOファイル:"],
    "patch_file": ["Patch File (IPS):", "Arquivo de Patch (IPS):", "Ficheiro de Patch (IPS):", "Archivo Parche (IPS):", "Файл патча (IPS):", "パッチファイル (IPS):"],
    "patch_out": ["Output Patched ISO:", "ISO Final Corrigida:", "ISO Final Corrigida:", "ISO Resultante:", "Готовый пропатченный ISO:", "出力先ISO:"],
    "patch_btn": ["APPLY PATCH", "APLICAR PATCH", "APLICAR PATCH", "APLICAR PARCHE", "ПРИМЕНИТЬ ПАТЧ", "パッチ適用"],
    "patch_reg": ["Remove Region Protection (ESR Disc Flag)", "Remover Trava de Região (Modo ESR)", "Remover Bloqueio de Região (Modo ESR)", "Quitar Bloqueo de Región (ESR)", "Снять региональную защиту (ESR)", "リージョンロック解除 (ESR)"],

    # Homebrews Apps
    "app_name": ["Application Name:", "Nome do Aplicativo:", "Nome da Aplicação:", "Nombre de Aplicación:", "Имя приложения:", "アプリ名:"],
    "app_elf": ["Path to .ELF Binary:", "Executável .ELF:", "Executável .ELF:", "Ejecutable .ELF:", "Путь к файлу .ELF:", ".ELFバイナリのパス:"],
    "app_drv": ["Target Storage Drive:", "Dispositivo de Destino:", "Dispositivo de Destino:", "Unidad Destino:", "Целевой диск:", "インストール先ドライブ:"],
    "app_btn": ["INSTALL HOMEBREW TO OPL", "INSTALAR NO MENU APPS", "INSTALAR NO MENU APPS", "INSTALAR EN APPS", "УСТАНОВИТЬ В APPS", "OPLにインストール"],
    "app_succ": ["Homebrew installed successfully!", "Aplicativo instalado com sucesso!", "Aplicação instalada com sucesso!", "¡Instalado con éxito!", "Приложение успешно установлено!", "正常にインストールされました！"],

    # Configurações
    "set_app": ["APPEARANCE & LANGUAGE", "APARÊNCIA E IDIOMA", "APARÊNCIA E IDIOMA", "APARIENCIA E IDIOMA", "ВНЕШНИЙ ВИД И ЯЗЫК", "外観と言語"],
    "set_theme": ["INTERFACE THEME", "TEMA DA INTERFACE", "TEMA DA INTERFACE", "TEMA DE LA INTERFAZ", "ТЕМА ИНТЕРФЕЙСА", "インターフェーステーマ"],
    "set_beh": ["SYSTEM PREFERENCES", "PREFERÊNCIAS DO SISTEMA", "PREFERÊNCIAS DO SISTEMA", "PREFERENCIAS DEL SISTEMA", "СИСТЕМНЫЕ НАСТРОЙКИ", "システム設定"],
    "set_snd": ["Interaction sound effects", "Efeitos sonoros de clique e ação", "Efeitos sonoros de clique e ação", "Efectos de sonido", "Звуковые эффекты интерфейса", "操作音効果"],
    "set_anim": ["Smooth animations", "Animações suaves da interface", "Animações suaves da interface", "Animaciones suaves", "Плавные анимации", "アニメーション効果"],
    "set_laptop": ["Laptop Mode (Low-Spec / Eco)", "Modo para Notebook (Leve e Econômico)", "Modo para Portátil (Leve e Económico)", "Modo Portátil (Bajo Consumo)", "Режим ноутбука (Экономный/Быстрый)", "ノートPCモード（軽量・省電力）"],
    "set_bgm": ["Background ambience music", "Música ambiente de fundo", "Música ambiente de fundo", "Música de fondo", "Фоновая музыка", "BGM再生"],
    "set_lang": ["LANGUAGE / IDIOMA", "IDIOMA", "IDIOMA", "IDIOMA", "ЯЗЫК", "言語"],
    "set_rate": ["⭐ RATE PROJECT", "⭐ AVALIAR O PROJETO", "⭐ AVALIAR O PROJETO", "⭐ CALIFICAR PROYECTO", "⭐ ОЦЕНИТЬ ПРОЕКТ", "⭐ 評価する"],
    "dev_tools": ["SYSTEM & TOOLS", "FERRAMENTAS DO SISTEMA", "FERRAMENTAS DO SISTEMA", "HERRAMIENTAS DEL SISTEMA", "СИСТЕМНЫЕ ИНСТРУМЕНТЫ", "システムツール"],
    "dev_apa_sim": ["Create Raw APA HDD Image", "Criar Imagem Bruta de HDD APA", "Criar Imagem Bruta de HDD APA", "Crear Imagen APA Bruta", "Создать образ APA диска", "仮想APA HDDイメージ作成"],
    "set_log": ["EXPORT DIAGNOSTIC REPORT", "GERAR RELATÓRIO DE DIAGNÓSTICO", "GERAR RELATÓRIO DE DIAGNÓSTICO", "GENERAR REPORTE", "ЭКСПОРТИРОВАТЬ ЛОГ", "診断レポート出力"],
    "ver_btn": ["VERSION ROLLBACK", "HISTÓRICO DE VERSÕES", "HISTÓRICO DE VERSÕES", "VOLVER A VERSIÓN PREVIA", "ОТКАТ ВЕРСИИ", "以前のバージョンに戻す"],
    "roadmap_btn": ["ROADMAP & UPDATES TIMELINE", "LINHA DO TEMPO & ROADMAP", "HISTÓRICO & ROADMAP", "CRONOGRAMA Y ROADMAP", "ТАЙМЛАЙН ОБНОВЛЕНИЙ", "ロードマップと履歴"],

    # Roadmap
    "roadmap_title": ["UPDATE ROADMAP & HISTORY", "LINHA DO TEMPO & HISTÓRICO", "HISTÓRICO & ROADMAP", "HISTORIAL Y CRONOGRAMA", "ИСТОРИЯ И ПЛАНЫ ОБНОВЛЕНИЙ", "アップデート履歴とロードマップ"],
    "roadmap_sub": ["Drag the timeline to explore past and current releases.", "Arraste a linha do tempo para explorar as versões.", "Arraste a linha do tempo para explorar as versões.", "Arrastra la línea temporal para ver las versiones.", "Перемещайте ползунок для просмотра версий.", "スライダーを動かして各バージョンを確認できます。"],
    "roadmap_prev": ["◀ Previous Version", "◀ Versão Anterior", "◀ Versão Anterior", "◀ Versión Anterior", "◀ Предыдущая версия", "◀ 前のバージョン"],
    "roadmap_next": ["Next Version ▶", "Próxima Versão ▶", "Próxima Versão ▶", "Siguiente Versión ▶", "Следующая версия ▶", "次のバージョン ▶"],
    "roadmap_cur": ["CURRENT VERSION", "VERSÃO ATUAL", "VERSÃO ATUAL", "VERSIÓN ACTUAL", "ТЕКУЩАЯ ВЕРСИЯ", "現在のバージョン"],
    "roadmap_future_title": ["Future Update", "Próxima Atualização", "Próxima Atualização", "Futura Actualización", "Будущее обновление", "将来のアップデート"],
    "roadmap_future_desc": ["No future updates currently planned. Enjoy all features of v1.07!", "Nenhuma atualização planejada no momento. Aproveite a v1.07!", "Nenhuma atualização planeada no momento. Aproveite a v1.07!", "No hay actualizaciones planificadas actualmente. ¡Disfruta la v1.07!", "На данный момент обновлений не планируется. Наслаждайтесь v1.07!", "現在計画されている更新はありません。v1.07をお楽しみください！"],

    # Setup inicial
    "setup_welcome": ["Welcome to PS2Manager", "Bem-vindo ao PS2Manager", "Bem-vindo ao PS2Manager", "Bienvenido a PS2Manager", "Добро пожаловать в PS2Manager", "PS2Managerへようこそ"],
    "setup_continue": ["CONTINUE", "CONTINUAR", "CONTINUAR", "CONTINUAR", "ПРОДОЛЖИТЬ", "次へ進む"],
    "setup_lang": ["Select your language:", "Selecione o seu idioma:", "Selecione o seu idioma:", "Selecciona tu idioma:", "Выберите ваш язык:", "言語を選択してください:"],
    "setup_model": ["Select your PS2 model:", "Qual o modelo do seu PS2?", "Qual o modelo da sua PS2?", "¿Cuál es el modelo de tu PS2?", "Модель вашей PS2:", "PS2本体の型番:"],
    "setup_type": ["Console Form Factor:", "Versão do Console:", "Versão da Consola:", "Tipo de Consola:", "Тип консоли:", "本体タイプ:"],
    "setup_finish": ["Configuration ready! Let's get started.", "Tudo pronto! Vamos começar.", "Tudo pronto! Vamos começar.", "¡Todo listo! Comencemos.", "Все готово! Начинаем работу.", "準備完了！始めましょう。"],

    # Mensagens de Integridade
    "msg_corruption_warn": [
        "I don't think you want your files corrupted.",
        "Eu acho que você não quer seus arquivos corrompidos.",
        "Penso que não quer os seus ficheiros corrompidos.",
        "Creo que no quieres tus archivos dañados.",
        "Думаю, вы не хотите повреждения файлов.",
        "ファイルが破損する恐れがあります。"
    ],
    "msg_warned": [
        "I tried to warn you.",
        "Eu tentei avisar.",
        "Tentei avisar.",
        "Intenté avisar.",
        "Я пытался предупредить.",
        "警告しました。"
    ],

    # Modais e detalhes de jogos
    "modal_game_profile": ["PS2Manager - Game Profile", "PS2Manager - Perfil do Jogo", "PS2Manager - Perfil do Jogo", "PS2Manager - Perfil del Juego", "PS2Manager - Профиль игры", "PS2Manager - ゲームプロファイル"],
    "modal_rollback": ["PS2Manager - Version Rollback", "PS2Manager - Histórico de Versões", "PS2Manager - Histórico de Versões", "PS2Manager - Historial de Versiones", "PS2Manager - Откат версии", "PS2Manager - バージョン履歴"],
    "ver_empty": ["No previous executables in /VER folder.", "Nenhum executável anterior na pasta /VER.", "Nenhum executável anterior na pasta /VER.", "No hay ejecutables anteriores en /VER.", "Нет предыдущих исполняемых файлов в /VER.", "/VERフォルダに以前の実行ファイルがありません。"],
    "ver_launch": ["Launch", "Executar", "Executar", "Ejecutar", "Запустить", "実行"],
    "game_id": ["Game ID", "ID do Jogo", "ID do Jogo", "ID del Juego", "ID игры", "ゲームID"],
    "game_format": ["Format / Media", "Formato / Mídia", "Formato / Multimédia", "Formato / Medio", "Формат / Носитель", "フォーマット/メディア"],
    "game_size": ["Size", "Tamanho", "Tamanho", "Tamaño", "Размер", "サイズ"],
    "game_region": ["Region", "Região", "Região", "Región", "Регион", "リージョン"],

    # Instalação no Pendrive
    "inst_step1": ["1. Select ISO / Game File:", "1. Selecione o arquivo ISO / Jogo:", "1. Selecione o ficheiro ISO / Jogo:", "1. Seleccione archivo ISO / Juego:", "1. Выберите файл ISO / Игру:", "1. ISO / ゲームファイルを選択:"],
    "inst_step2": ["2. Game Title:", "2. Nome do Jogo:", "2. Nome do Jogo:", "2. Nombre del Juego:", "2. Название игры:", "2. ゲーム名:"],
    "inst_step3": ["3. Target USB Drive:", "3. Dispositivo USB de Destino:", "3. Dispositivo USB de Destino:", "3. Unidad USB Destino:", "3. Целевой USB накопитель:", "3. 対象USBドライブ:"],
    "inst_auto_art": ["Automatically download cover art for OPL", "Baixar capa automaticamente para o OPL", "Descarregar capa automaticamente para o OPL", "Descargar carátula para OPL automáticamente", "Автоматически скачать обложку для OPL", "OPL用ジャケット画像を自動取得"],
    "inst_btn": ["INSTALL GAME TO USB", "INICIAR INSTALAÇÃO NO PENDRIVE", "INICIAR INSTALAÇÃO NO PENDRIVE", "INSTALAR JUEGO EN USB", "УСТАНОВИТЬ ИГРУ НА USB", "USBにゲームをインストール"],
    "inst_ready": ["Ready to install.", "Pronto para instalar.", "Pronto a instalar.", "Listo para instalar.", "Готов к установке.", "インストールの準備ができました。"],
    "inst_err_select": ["Please select an ISO file and target USB drive.", "Selecione o arquivo ISO e o pendrive de destino.", "Selecione o ficheiro ISO e o pendrive de destino.", "Seleccione el archivo ISO y la unidad USB.", "Выберите файл ISO и целевой накопитель USB.", "ISOファイルと対象USBドライブを選択してください。"],
    "inst_err_nodrive": ["Target USB device not found or disconnected.", "Dispositivo USB não encontrado ou desconectado.", "Dispositivo USB não encontrado ou desligado.", "Unidad USB no encontrada o desconectada.", "USB накопитель не найден или отключен.", "対象USBデバイスが見つからないか切断されています。"],
    "inst_starting": ["Starting installation to USB drive...", "Iniciando instalação no pendrive...", "A iniciar a instalação no pendrive...", "Iniciando instalación en USB...", "Запуск установки на USB...", "USBへのインストールを開始中..."],
    "inst_done": ["Installation completed successfully!", "Instalação concluída com sucesso!", "Instalação concluída com sucesso!", "¡Instalación completada con éxito!", "Установка успешно завершена!", "インストールが正常に完了しました！"],
    "inst_succ_msg": ["Game installed successfully to USB drive!", "Jogo instalado com sucesso no pendrive!", "Jogo instalado com sucesso no pendrive!", "¡Juego instalado con éxito en USB!", "Игра успешно установлена на USB!", "ゲームがUSBに正常にインストールされました！"],
    "inst_err_fail": ["Installation failed:", "Falha na instalação:", "Falha na instalação:", "Fallo en la instalación:", "Ошибка установки:", "インストールに失敗しました:"],

    # Fila em Lote
    "batch_prog_total": ["Overall Queue Progress:", "Progresso Geral da Fila:", "Progresso Geral da Fila:", "Progreso General de la Cola:", "Общий прогресс очереди:", "キュー全体の進捗:"],
    "batch_prog_cur": ["Current Game Progress:", "Progresso do Jogo Atual:", "Progresso do Jogo Atual:", "Progreso del Juego Actual:", "Прогресс текущей игры:", "現在のゲームの進捗:"],
    "batch_empty": ["Queue is empty. Add ISO files or folders above.", "Fila vazia. Adicione arquivos ou pastas de jogos acima.", "Fila vazia. Adicione ficheiros ou pastas de jogos acima.", "Cola vacía. Agregue archivos o carpetas arriba.", "Очередь пуста. Добавьте файлы или папки выше.", "キューは空です。上部のボタンからファイルまたはフォルダを追加してください。"],
    "batch_warn_empty": ["Please add games to the queue first.", "Adicione jogos à fila primeiro.", "Adicione jogos à fila primeiro.", "Agregue juegos a la cola primero.", "Сначала добавьте игры в очередь.", "最初にキューにゲームを追加してください。"],
    "batch_err_nodrive": ["Please select a target USB drive.", "Selecione a unidade USB de destino.", "Selecione a unidade USB de destino.", "Seleccione la unidad USB de destino.", "Выберите целевой накопитель USB.", "対象USBドライブを選択してください。"],
    "batch_done_title": ["Batch Complete", "Fila Finalizada", "Fila Finalizada", "Cola Completada", "Очередь завершена", "一括処理完了"],
    "batch_done_msg": ["All queued games have been processed!", "Todos os jogos da fila foram processados!", "Todos os jogos da fila foram processados!", "¡Todos los juegos han sido procesados!", "Все игры из очереди успешно обработаны!", "キュー内のすべてのゲームが処理されました！"],

    # Gravador de DVD Real
    "burn_ready": ["Ready to burn disc.", "Pronto para gravação.", "Pronto para gravação.", "Listo para grabar.", "Готов к записи.", "書き込み準備完了。"],
    "burn_err_select_iso": ["Select an ISO file to burn.", "Selecione o arquivo ISO para gravar.", "Selecione o ficheiro ISO para gravar.", "Seleccione un archivo ISO para grabar.", "Выберите файл ISO для записи.", "書き込むISOファイルを選択してください。"],
    "burn_progress_msg": ["Burning disc... Do not eject media.", "Gravando disco... Não ejete a mídia.", "A gravar disco... Não ejete o disco.", "Grabando disco... No expulse el medio.", "Идет запись диска... Не извлекайте носитель.", "書き込み中... ディスクを取り出さないでください。"],
    "burn_err_title": ["Burn Error", "Erro de Gravação", "Erro de Gravação", "Error de Grabación", "Ошибка записи", "書き込みエラー"],
    "burn_no_drives": ["No optical burner detected", "Nenhum gravador de DVD/CD detectado", "Nenhum gravador de DVD/CD detetado", "No se detectó grabadora de DVD/CD", "Оптический привод не обнаружен", "光学ドライブが検出されませんでした"],
    "burn_writing_sectors": ["Writing sectors...", "Gravando setores...", "A gravar setores...", "Escribiendo sectores...", "Запись секторов...", "セクター書き込み中..."],

    # Outros
    "recovery_title": ["Recovery", "Recuperação", "Recuperação", "Recuperación", "Восстановление", "復元"],
    "recovery_msg": ["Interrupted file transfer detected from a previous session!\nDo you want to retry/resume?", "Transferência interrompida anteriormente detectada!\nDeseja continuar?", "Transferência interrompida anteriormente detetada!\nDeseja continuar?", "¡Se detectó una transferencia interrumpida anterior!\n¿Desea continuar?", "Обнаружена прерванная передача файлов!\nХотите продолжить?", "以前の中断されたファイル転送が検出されました！\n続行しますか？"],
    "patch_success": ["Patch applied successfully!", "Patch aplicado com sucesso!", "Patch aplicado com sucesso!", "¡Parche aplicado con éxito!", "Патч успешно применен!", "パッチが正常に適用されました！"],
    "art_done": ["Cover art download completed!", "Download de capas concluído!", "Descarregamento de capas concluído!", "¡Descarga de carátulas completada!", "Загрузка обложек завершена!", "ジャケット画像のダウンロードが完了しました！"],
    "iso_files": ["PS2 Game ISO", "Jogos de PS2 (*.iso)", "Jogos de PS2 (*.iso)", "Juegos de PS2 (*.iso)", "Образы PS2 (*.iso)", "PS2ゲームISO (*.iso)"],

    # Cheat Engine Translations
    "cht_folder": ["CHT Folder:", "Pasta CHT:", "Pasta CHT:", "Carpeta CHT:", "Папка CHT:", "CHTフォルダ:"],
    "cht_add": ["ADD CHEAT", "ADICIONAR CHEAT", "ADICIONAR CHEAT", "AÑADIR CHEAT", "ДОБАВИТЬ ЧИТ", "チート追加"],
    "cht_edit": ["EDIT CHEAT", "EDITAR CHEAT", "EDITAR CHEAT", "EDITAR CHEAT", "РЕДАКТИРОВАТЬ ЧИТ", "チート編集"],
    "cht_enable": ["ENABLE", "HABILITAR", "ATIVAR", "HABILITAR", "ВКЛЮЧИТЬ", "有効化"],
    "cht_disable": ["DISABLE", "DESABILITAR", "DESATIVAR", "DESHABILITAR", "ОТКЛЮЧИТЬ", "無効化"],
    "cht_import": ["Import .cht File", "Importar arquivo .cht", "Importar ficheiro .cht", "Importar archivo .cht", "Импортировать файл .cht", ".chtファイルをインポート"],
    "cht_create": ["Create from Scratch", "Criar do Zero", "Criar de Raiz", "Crear desde Cero", "Создать с нуля", "新規作成"],
    "cht_name": ["Cheat Name (Game ID):", "Nome (ID do Jogo):", "Nome (ID do Jogo):", "Nombre (ID de Juego):", "Имя (ID игры):", "チート名 (ゲームID):"],
    "cht_save": ["SAVE CHEAT", "SALVAR CHEAT", "GUARDAR CHEAT", "GUARDAR CHEAT", "СОХРАНИТЬ ЧИТ", "チート保存"],
    "cht_none": ["No cheat selected!", "Nenhum cheat selecionado!", "Nenhum cheat selecionado!", "¡Ningún cheat seleccionado!", "Чит не выбран!", "チートが選択されていません！"],
    "cht_err": ["Error processing cheat:", "Erro ao processar cheat:", "Erro ao processar cheat:", "Error al procesar cheat:", "Ошибка обработки чита:", "チート処理エラー:"],
    "cht_succ": ["Cheat saved successfully!", "Cheat salvo com sucesso!", "Cheat guardado com sucesso!", "¡Cheat guardado con éxito!", "Чит успешно сохранен!", "チートが正常に保存されました！"],
    "cht_sel_game": ["Select Game from Library:", "Selecionar Jogo da Biblioteca:", "Selecionar Jogo da Biblioteca:", "Seleccionar Juego de la Biblioteca:", "Выбрать игру из библиотеки:", "ライブラリからゲームを選択:"],
    "cht_manual": ["Custom / Manual", "Personalizado / Manual", "Personalizado / Manual", "Personalizado / Manual", "Пользовательский / Вручную", "カスタム / 手動"],

}

class DataManager:
    def __init__(self):
        self.filepath = os.path.join(APP_DATA_DIR, "data.json")
        self.config = {
            "theme": "Dark",
            "sound_enabled": True,
            "custom_pcsx2_path": "",
            "language": "PT_BR",
            "setup_done": False,
            "ps2_model": "SCPH-9000x",
            "ps2_type": "SLIM",
            "animations": True,
            "laptop_mode": False,
            "bgm_enabled": True,
            "last_cht_folder": "",
            "show_console": False
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
            # Corrige chave legada PT para PT_BR se necessário
            if self.config.get("language") not in LANGS:
                self.config["language"] = "PT_BR"
            self.library = parsed.get("library", [])
            self.state = parsed.get("state", None)
        except Exception:
            pass

db = DataManager()
apply_console_visibility(db.config.get("show_console", False))

class ConfigManager:
    @property
    def data(self):
        return db.config

    def save(self):
        db.save()

    def apply_theme(self):
        t = self.data.get("theme", "Dark")
        if t in THEMES:
            ctk.set_appearance_mode("dark" if t != "Light" else "light")
        else:
            ctk.set_appearance_mode("System")

    def get_color(self, key):
        t = self.data.get("theme", "Dark")
        if t not in THEMES:
            t = "Dark"
        return THEMES[t].get(key, "#000000")

    def get_radius(self, widget_type="default"):
        if self.data.get("laptop_mode", False):
            return 4
        if widget_type == "button":
            return 8
        if widget_type == "card":
            return 12
        if widget_type == "entry":
            return 8
        if widget_type == "chip":
            return 6
        return 8

    def get_border_width(self):
        return 1

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
    if bytes_size == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

class TransferLockManager:
    """Proteção ativa contra corrupção de arquivos e fechamento abrupto."""
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
        helper_code = f"""
import sys, time, ctypes, os
pid = {os.getpid()}
lock_file = r"{cls._lock_path}"

while True:
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        break
    exit_code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    ctypes.windll.kernel32.CloseHandle(handle)
    if exit_code.value != 259:
        break
    time.sleep(0.4)

if os.path.exists(lock_file):
    try:
        os.remove(lock_file)
    except:
        pass
    ctypes.windll.user32.MessageBoxW(0, "Eu tentei avisar.", "PS2Manager", 0x10 | 0x40000 | 0x1000)
"""
        try:
            cls._watchdog_proc = subprocess.Popen(
                [sys.executable, "-c", helper_code],
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
    def __init__(self):
        self.enabled = cfg.data.get("sound_enabled", True)
        self.bgm_enabled = cfg.data.get("bgm_enabled", True)
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

    def update_bgm(self, state):
        self.bgm_enabled = state
        if not PYGAME_SUPPORT:
            return
        bgm_path = get_res_path(os.path.join("sounds", "soundF.mp3"))
        if state and os.path.exists(bgm_path):
            if not pygame.mixer.music.get_busy():
                try:
                    pygame.mixer.music.load(bgm_path)
                    pygame.mixer.music.play(-1)
                except Exception:
                    pass
            else:
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
        else:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass

    def _play_freq(self, freqs_durations):
        if not self.enabled or not SOUND_SUPPORT:
            return
        threading.Thread(target=lambda: [winsound.Beep(f, d) for f, d in freqs_durations], daemon=True).start()

    def play_click(self):
        if PYGAME_SUPPORT and self.snd_click:
            self.ch_sfx.play(self.snd_click)
        else:
            self._play_freq([(4000, 10)])

    def play_tab(self):
        if PYGAME_SUPPORT and self.snd_tab:
            self.ch_sfx.play(self.snd_tab)
        else:
            self._play_freq([(3000, 15)])

    def play_close(self):
        if PYGAME_SUPPORT and self.snd_close:
            self.ch_sfx.play(self.snd_close)
        else:
            self._play_freq([(1000, 100), (800, 150)])

    def play_success(self):
        if PYGAME_SUPPORT and self.snd_success:
            self.ch_sfx.play(self.snd_success)
        else:
            self._play_freq([(1200, 40), (1800, 60)])

    def play_error(self):
        if PYGAME_SUPPORT and self.snd_error:
            self.ch_sfx.play(self.snd_error)
        else:
            self._play_freq([(200, 150), (200, 150)])

    def play_usb(self, connected=True):
        if connected:
            self._play_freq([(800, 40), (1200, 40), (1800, 80)])
        else:
            self._play_freq([(1800, 40), (1200, 40), (800, 80)])

sound_fx = SoundManager()

class GameAnalyzer:
    REGION_MAP = {
        'SLUS': 'USA', 'SCUS': 'USA', 'SLES': 'Europe', 'SCES': 'Europe',
        'SLPS': 'Japan', 'SLPM': 'Japan', 'SCPS': 'Japan', 'SLKA': 'Korea'
    }

    @staticmethod
    def extract_game_id(file_path):
        """Extrai o Game ID oficial limpo sem falsos positivos ou caracteres pipe."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(2 * 1024 * 1024)
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
            "name": os.path.splitext(filename)[0].replace('_', ' '),
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
        self.sync_drives()

    def sync_drives(self):
        """Remove jogos fantasmas cujos arquivos foram apagados ou cujo drive foi removido."""
        valid = []
        for g in self.games:
            p = g.get('path', '')
            if p and os.path.exists(p):
                valid.append(g)
        if len(valid) != len(self.games):
            self.games = valid
            db.save()

    def sync(self):
        self.sync_drives()

    def add(self, game_data):
        for i, g in enumerate(self.games):
            if g['path'] == game_data['path']:
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



# Importa todos os motores e workers divididos em tool_workers.py
from scripts.tool_workers import *
