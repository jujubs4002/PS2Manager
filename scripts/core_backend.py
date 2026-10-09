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
        if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 5 if show else 0)
    except: pass

class AppLogger:
    def __init__(self):
        self.logs = []
        self.log("PS2Manager Backend Engine Initialized.", "INFO")

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
        except Exception as e: return None

sys_logger = AppLogger()

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    MEIPASS_DIR = sys._MEIPASS
else:
    # Volta uma pasta atrás já que estamos dentro de /scripts
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MEIPASS_DIR = BASE_DIR

APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PS2Manager")
os.makedirs(APP_DATA_DIR, exist_ok=True)

def get_res_path(rel_path):
    p1 = os.path.join(MEIPASS_DIR, rel_path)
    if os.path.exists(p1): return p1
    return os.path.join(BASE_DIR, rel_path)

try:
    import winsound
    SOUND_SUPPORT = True
except: SOUND_SUPPORT = False

try:
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    import pygame
    pygame.mixer.init()
    PYGAME_SUPPORT = True
except: PYGAME_SUPPORT = False

try:
    import lz4.block
    LZ4_SUPPORT = True
except: LZ4_SUPPORT = False

APP_NAME = "PS2 MANAGER"
APP_VERSION = "V1.06" 
VERSION_COLOR_CODE = '5' 

THEMES = {
    "Dark": {"bg_main": "#0D1117", "bg_sidebar": "#010409", "card_base": "#161B22", "card_hover": "#21262D", "accent": "#2F81F7", "text_main": "#E6EDF3", "text_muted": "#8B949E", "success": "#238636", "warning": "#D29922", "danger": "#DA3633", "border": "#30363D"},
    "Light": {"bg_main": "#F6F8FA", "bg_sidebar": "#E5E7EB", "card_base": "#FFFFFF", "card_hover": "#F3F4F6", "accent": "#0969DA", "text_main": "#1F2328", "text_muted": "#656D76", "success": "#1A7F37", "warning": "#9A6700", "danger": "#D1242F", "border": "#D0D7DE"},
    "Ocean": {"bg_main": "#0f172a", "bg_sidebar": "#020617", "card_base": "#1e293b", "card_hover": "#334155", "accent": "#0ea5e9", "text_main": "#f8fafc", "text_muted": "#94a3b8", "success": "#10b981", "warning": "#f59e0b", "danger": "#ef4444", "border": "#334155"}
}

LANGS = {"EN": 0, "PT": 1, "ES": 2}
TRANSLATIONS = {
    "tab_dash": ["DASHBOARD", "PAINEL", "PANEL PRINCIPAL"],
    "tab_lib": ["LIBRARY DB", "BIBLIOTECA", "BIBLIOTECA"],
    "tab_emu": ["PCSX2 EMULATOR", "EMULADOR PCSX2", "EMULADOR PCSX2"],
    "tab_usb": ["USB MANAGER", "GERENCIADOR USB", "GESTOR USB"],
    "sub_clone": ["  ↳ CLONE DRIVE", "  ↳ CLONAR PENDRIVE", "  ↳ CLONAR PENDRIVE"],
    "tab_mig": ["FORMAT & MIGRATE", "FORMATAR E MIGRAR", "FORMATEAR Y MIGRAR"],
    "tab_apps": ["OPL APPS (HOMEBREWS)", "OPL APPS (HOMEBREWS)", "OPL APPS (HOMEBREWS)"],
    "tab_iso": ["ISO EXTRACT / REPACK", "EXTRAIR / REEMPACOTAR", "EXTRAER / REEMPAQUETAR"],
    "tab_rip": ["DVD/CD RIPPER", "RIPADOR DVD/CD", "RIPEAR DVD/CD"],
    "tab_util": ["USB UTIL (SPLIT)", "USB UTIL (DIVIDIR)", "USB UTIL (DIVIDIR)"],
    "tab_disc": ["DISC ANALYZER", "ANALISADOR DE DISCO", "ANALIZADOR DE DISCO"],
    "tab_set": ["SETTINGS", "CONFIGURAÇÕES", "AJUSTES"],
    "tab_more": ["MORE TOOLS", "MAIS FERRAMENTAS", "MÁS HERRAMIENTAS"],
    "tab_patcher": ["ISO PATCHER & ESR", "ISO PATCHER E ESR", "ISO PATCHER Y ESR"],
    "btn_back": ["<- GO BACK", "<- VOLTAR", "<- VOLVER"],
    "dash_games": ["LIBRARY GAMES", "JOGOS NA BIBLIOTECA", "JUEGOS EN BIBLIOTECA"],
    "dash_usb": ["CONNECTED DRIVES", "UNIDADES CONECTADAS", "UNIDADES CONECTADAS"],
    "dash_size": ["TOTAL SIZE", "TAMANHO TOTAL", "TAMAÑO TOTAL"],
    "lib_scan": ["+ SCAN DIR", "+ ESCANEAR PASTA", "+ ESCANEAR CARPETA"],
    "lib_search": ["Search by name or ID...", "Pesquisar por nome ou ID...", "Buscar por nombre o ID..."],
    "lib_scan_done": ["Scan complete!", "Escaneamento concluído!", "¡Escaneo completado!"],
    "lib_btn_close": ["CLOSE", "FECHAR", "CERRAR"],
    "lib_btn_test": ["TEST ON PCSX2", "TESTAR NO PCSX2", "PROBAR EN PCSX2"],
    "lib_btn_conv": ["CONVERT TO ISO", "CONVERTER PARA ISO", "CONVERTIR A ISO"],
    "lib_btn_rem": ["REMOVE", "REMOVER", "ELIMINAR"],
    "lib_conv_succ": ["Game successfully converted to ISO!", "Jogo convertido para ISO com sucesso!", "¡Juego convertido a ISO con éxito!"],
    "emu_sel": ["SELECT A GAME TO TEST", "SELECIONE UM JOGO PARA TESTAR", "SELECCIONE UN JUEGO PARA PROBAR"],
    "emu_btn": ["LAUNCH EMULATOR", "INICIAR EMULADOR", "INICIAR EMULADOR"],
    "emu_info": ["When starting for the first time, the system will copy BIOS from ETC.", "Ao iniciar pela primeira vez, o sistema copiará a BIOS da pasta ETC.", "Al iniciar por primera vez, el sistema copiará la BIOS de la carpeta ETC."],
    "emu_err_notfound": ["Emulator executable not found in 'pcsx2' folder.", "Executável do emulador não encontrado na pasta 'pcsx2'.", "Ejecutable del emulador no encontrado en la carpeta 'pcsx2'."],
    "usb_ref": ["REFRESH", "ATUALIZAR", "ACTUALIZAR"],
    "usb_nodrv": ["No drive selected", "Nenhuma unidade selecionada", "Ninguna unidad seleccionada"],
    "usb_cap": ["Capacity:", "Capacidade:", "Capacidad:"],
    "usb_free": ["Free:", "Livre:", "Libre:"],
    "iso_mode_ext": ["EXTRACT ISO", "EXTRAIR ISO", "EXTRAER ISO"],
    "iso_mode_rep": ["REPACK TO ISO", "REEMPACOTAR PARA ISO", "REEMPAQUETAR A ISO"],
    "iso_mode_zso": ["COMPRESS TO ZSO", "COMPRIMIR PARA ZSO", "COMPRIMIR A ZSO"],
    "iso_mode_bin": ["PS1 BIN -> ISO", "PS1 BIN -> ISO", "PS1 BIN -> ISO"],
    "iso_file": ["Source File/Folder:", "Arquivo/Pasta de Origem:", "Archivo/Carpeta de Origen:"],
    "iso_out": ["Output Location:", "Local de Destino:", "Lugar de Destino:"],
    "iso_btn_ext": ["START EXTRACTION", "INICIAR EXTRAÇÃO", "INICIAR EXTRACCIÓN"],
    "iso_btn_rep": ["START REPACK", "INICIAR REEMPACOTAMENTO", "INICIAR REEMPAQUETADO"],
    "iso_btn_zso": ["START COMPRESSION", "INICIAR COMPRESSÃO", "INICIAR COMPRESIÓN"],
    "iso_btn_bin": ["CONVERT PS1 BIN", "CONVERTER PS1 BIN", "CONVERTIR PS1 BIN"],
    "iso_wait": ["This may take a long time.", "Isso pode demorar muito.", "Esto puede tardar mucho."],
    "iso_succ": ["Process completed successfully!", "Processo concluído com sucesso!", "¡Proceso completado con éxito!"],
    "iso_err": ["Error during process: ", "Erro durante o processo: ", "Error durante el proceso: "],
    "iso_empty": ["Please select source and destination!", "Por favor, selecione a origem e o destino!", "¡Por favor seleccione origen y destino!"],
    "util_iso": ["Select Original ISO:", "Selecionar ISO Original:", "Seleccionar ISO Original:"],
    "util_dst": ["Destination HDD/USB Folder:", "Pasta HDD/USB de Destino:", "Carpeta HDD/USB de Destino:"],
    "util_name": ["Game Name (Max 32 chars):", "Nome do Jogo (Máx 32 letras):", "Nombre del Juego (Máx 32):"],
    "util_btn": ["SPLIT & GENERATE UL.CFG", "DIVIDIR E GERAR UL.CFG", "DIVIDIR Y GENERAR UL.CFG"],
    "util_succ": ["Game split successfully for OPL (FAT32)!", "Jogo dividido com sucesso para o OPL (FAT32)!", "¡Juego dividido con éxito para OPL (FAT32)!"],
    "disc_drv": ["Optical Drive:", "Leitor Óptico:", "Lector Óptico:"],
    "disc_btn": ["ANALYZE DISC", "ANALISAR DISCO", "ANALIZAR DISCO"],
    "disc_none": ["No Disc Detected", "Nenhum Disco Detectado", "Ningún Disco Detectado"],
    "set_app": ["APPEARANCE & LANGUAGE", "APARÊNCIA E IDIOMA", "APARIENCIA Y IDIOMA"],
    "set_beh": ["BEHAVIOR", "COMPORTAMENTO", "COMPORTAMIENTO"],
    "set_snd": ["Enable interaction sounds", "Ativar sons de interação", "Activar sonidos de interacción"],
    "set_anim": ["Enable UI animations", "Ativar animações da interface", "Activar animaciones de interfaz"],
    "set_sync": ["Auto-Sync (Remove deleted games)", "Auto-Sync (Remover jogos deletados)", "Auto-Sync (Quitar juegos borrados)"],
    "set_bgm": ["Play background music", "Tocar música de fundo", "Reproducir música de fondo"],
    "set_beta": ["Enable Beta UI (Modern & Fluid)", "Ativar Interface Beta (Moderna e Fluida)", "Activar Interfaz Beta (Moderna y Fluida)"],
    "set_cmd": ["Show Console Window (CMD)", "Mostrar Janela do Console (CMD)", "Mostrar Ventana de Consola (CMD)"],
    "set_lang": ["LANGUAGE", "IDIOMA", "IDIOMA"],
    "set_rate": ["⭐ RATE PS2MANAGER", "⭐ AVALIAR PS2MANAGER", "⭐ CALIFICAR PS2MANAGER"],
    "dev_tools": ["DEVELOPER TOOLS", "FERRAMENTAS DE DESENVOLVEDOR", "HERRAMIENTAS DE DESARROLLADOR"],
    "dev_apa_sim": ["Simulate APA HDD", "Simular HDD APA", "Simular HDD APA"],
    "apa_title": ["APA HDD EXPLORER", "EXPLORADOR HDD APA", "EXPLORADOR HDD APA"],
    "apa_drv": ["Select Physical Drive or Image:", "Selecione Unidade Física ou Imagem:", "Seleccione Unidad Física o Imagen:"],
    "apa_btn_raw": ["BACKUP TO IMG", "BACKUP PARA IMG", "COPIA A IMG"],
    "apa_btn_ext": ["EXTRACT CONTENT", "EXTRAIR CONTEÚDO", "EXTRAER CONTENIDO"],
    "apa_btn_rest": ["RESTORE TO HDD", "RESTAURAR PARA HDD", "RESTAURAR A HDD"],
    "apa_warn": ["Extract Content will COPY files.", "Extrair Conteúdo irá COPIAR os arquivos.", "Extraer Contenido COPIARÁ los archivos."],
    "msg_restart": ["Please restart PS2Manager.", "Reinicie o ps2manager.", "Reinicie ps2manager."],
    "setup_welcome": ["Hello, Welcome!", "Olá, Seja Bem Vindo!", "¡Hola, Bienvenido!"],
    "setup_continue": ["CONTINUE", "CONTINUAR", "CONTINUAR"],
    "setup_lang": ["What language do you speak?", "Qual idioma você fala?", "¿Qué idioma hablas?"],
    "setup_model": ["What is your PS2 model?", "Qual é o modelo do seu PS2?", "¿Cuál é el modelo de tu PS2?"],
    "setup_model_desc": ["(This helps tools work better!)", "(Isso ajuda as ferramentas!)", "(¡Ayuda a las herramientas!)"],
    "setup_type": ["FAT or SLIM?", "FAT ou SLIM?", "¿FAT o SLIM?"],
    "setup_finish": ["Thank you! You can now start using it!", "Obrigado! Você já pode começar a usar!", "¡Gracias! ¡Ya puedes empezar a usarlo!"],
    "clone_src": ["Source Drive (Copy From):", "Origem (Copiar De):", "Origen (Copiar De):"],
    "clone_dst": ["Destination Drive (Copy To):", "Destino (Copiar Para):", "Destino (Copiar Para):"],
    "clone_fmt_dst": ["Format DESTINATION before copying", "Formatar DESTINO antes de copiar", "Formatear DESTINO antes de copiar"],
    "clone_fmt_src": ["Format SOURCE after finishing", "Formatar ORIGEM ao terminar", "Formatear ORIGEN al terminar"],
    "clone_btn": ["START CLONING", "INICIAR CLONAGEM", "INICIAR CLONACIÓN"],
    "cfg_vid": ["Video Mode:", "Modo de Vídeo:", "Modo de Video:"],
    "cfg_res": ["GSM Resolution:", "Resolução GSM:", "Resolución GSM:"],
    "cfg_save": ["SAVE CFG", "SALVAR CFG", "GUARDAR CFG"],
    "tab_cht": ["CREATE CHEATS", "CRIAR CHEATS", "CREAR CHEATS"],
    "cht_folder": ["CHT Folder:", "Pasta CHT:", "Carpeta CHT:"],
    "cht_add": ["ADD CHEAT", "ADICIONAR CHEAT", "AÑADIR CHEAT"],
    "cht_edit": ["EDIT CHEAT", "EDITAR CHEAT", "EDITAR CHEAT"],
    "cht_enable": ["ENABLE", "HABILITAR", "HABILITAR"],
    "cht_disable": ["DISABLE", "DESABILITAR", "DESHABILITAR"],
    "cht_import": ["Import .cht File", "Importar arquivo .cht", "Importar archivo .cht"],
    "cht_create": ["Create from Scratch", "Criar do Zero", "Crear desde Cero"],
    "cht_name": ["Cheat Name (Game ID):", "Nome (ID do Jogo):", "Nombre (ID de Juego):"],
    "cht_save": ["SAVE CHEAT", "SALVAR CHEAT", "GUARDAR CHEAT"],
    "cht_none": ["No cheat selected!", "Nenhum cheat selecionado!", "¡Ningún cheat seleccionado!"],
    "cht_err": ["Error processing cheat:", "Erro ao processar cheat:", "Error al procesar cheat:"],
    "cht_succ": ["Cheat saved successfully!", "Cheat salvo com sucesso!", "¡Cheat guardado con éxito!"],
    "cht_sel_game": ["Select Game from Library:", "Selecionar Jogo da Biblioteca:", "Seleccionar Juego de la Biblioteca:"],
    "cht_manual": ["Custom / Manual", "Personalizado / Manual", "Personalizado / Manual"],
    "rip_out": ["Save to Folder:", "Salvar na Pasta:", "Guardar en Carpeta:"],
    "rip_fmt": ["Output Format:", "Formato de Saída:", "Formato de Salida:"],
    "rip_btn": ["RIP DISC TO PC", "RIPAR DISCO PARA O PC", "RIPEAR DISCO AL PC"],
    "rip_orig": ["Keep Original", "Manter Original", "Mantener Original"],
    "rip_fiso": ["Force Convert to ISO", "Forçar Conversão ISO", "Forzar ISO"],
    "set_log": ["GENERATE LOG REPORT", "GERAR RELATÓRIO DE LOG", "GENERAR REPORTE DE REGISTRO"],
    "ver_btn": ["VERSION ROLLBACK", "VOLTAR VERSÃO", "VOLVER VERSIÓN"],
    "ver_title": ["Select a previous version from /VER folder", "Selecione uma versão anterior da pasta /VER", "Seleccione una versión de la carpeta /VER"],
    "ver_empty": ["No executables found in /VER folder.", "Nenhum executável encontrado na pasta /VER.", "No se encontraron executables en la carpeta /VER."],
    "res_warn": ["Interrupted Transfer Detected!\nResume?", "Transferência Interrompida Detectada!\nContinuar?", "¡Transferencia Interrumpida Detectada!\n¿Continuar?"],
    "msg_bg_close": ["A transfer is active! Keep running in the background?", "Transferência ativa! Continuar em segundo plano?", "¡Transferencia activa! ¿Continuar en segundo plano?"],
    "mig_drv": ["1. Select Target Drive", "1. Selecione a Unidade", "1. Seleccione la Unidad"],
    "mig_fs": ["2. Target File System", "2. Sistema de Arquivos", "2. Sistema de Archivos"],
    "mig_btn": ["START MIGRATION", "INICIAR MIGRAÇÃO", "INICIAR MIGRACIÓN"],
    "mig_warn": ["WARNING: This will format the drive.", "AVISO: Isso irá formatar a unidade.", "ADVERTENCIA: Esto formateará la unidad."],
    "mig_conf": ["Are you sure you want to format this drive?", "Tem certeza que deseja formatar esta unidade?", "¿Seguro que quieres formatear esta unidad?"],
    "app_name": ["App Name:", "Nome do App:", "Nombre de App:"],
    "app_elf": ["Select .ELF File:", "Selecione o .ELF:", "Seleccione .ELF:"],
    "app_drv": ["Select Drive:", "Selecione a Unidade:", "Seleccione la Unidad:"],
    "app_btn": ["INSTALL HOMEBREW", "INSTALAR HOMEBREW", "INSTALAR HOMEBREW"],
    "app_succ": ["App installed successfully!", "App instalado com sucesso!", "¡App instalada con éxito!"],
    "art_title": ["OPL ART DOWNLOADER", "BAIXADOR DE CAPAS OPL", "DESCARGADOR DE CARÁTULAS OPL"],
    "art_desc": ["Automatically download missing covers.", "Baixa capas ausentes automaticamente.", "Descarga carátulas faltantes automáticamente."],
    "art_drv": ["Select Target Drive:", "Selecione a Unidade:", "Seleccione la Unidad:"],
    "art_scan": ["SCAN GAMES", "ESCANEAR JOGOS", "ESCANEAR JUEGOS"],
    "art_dl": ["DOWNLOAD ART", "BAIXAR CAPAS", "DESCARGAR CARÁTULAS"],
    "patch_iso": ["Original ISO File:", "Arquivo ISO Original:", "Archivo ISO Original:"],
    "patch_file": ["Patch File (IPS):", "Arquivo do Patch (IPS):", "Archivo Parche (IPS):"],
    "patch_out": ["Output Patched ISO:", "ISO Final Traduzida:", "ISO Traducida:"],
    "patch_btn": ["APPLY PATCH", "APLICAR PATCH", "APLICAR PARCHE"],
    "patch_reg": ["Remove Region Lock (ESR)", "Remover Trava de Região (ESR)", "Quitar Bloqueo de Región (ESR)"],
    "tour_btn_prev": ["PREVIOUS", "ANTERIOR", "ANTERIOR"],
    "tour_btn_next": ["NEXT", "PRÓXIMO", "SIGUIENTE"],
    "tour_btn_skip": ["SKIP TOUR", "PULAR TOUR", "SALTAR TOUR"],
    "tour_btn_finish": ["FINISH & START", "CONCLUIR E INICIAR", "FINALIZAR E INICIAR"]
}

class DataManager:
    def __init__(self):
        self.filepath = os.path.join(APP_DATA_DIR, "data.json")
        self.config = {"theme": "Dark", "sound_enabled": True, "auto_sync": True, "custom_pcsx2_path": "", "language": "EN", "setup_done": False, "ps2_model": "SCPH-9000x", "ps2_type": "SLIM", "animations": True, "bgm_enabled": True, "last_cht_folder": "", "beta_ui": False, "show_console": False}
        self.library = []
        self.state = None
        self.load()

    def save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump({"config": self.config, "library": self.library, "state": self.state}, f, indent=4)
        except: pass

    def load(self):
        if not os.path.exists(self.filepath): return
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f: parsed = json.load(f)
            self.config.update(parsed.get("config", {}))
            self.library = parsed.get("library", [])
            self.state = parsed.get("state", None)
        except: pass

db = DataManager()
apply_console_visibility(db.config.get("show_console", False))

class ConfigManager:
    @property
    def data(self): return db.config
    def save(self): db.save()

    def apply_theme(self):
        t = self.data.get("theme", "Dark")
        if t in THEMES: ctk.set_appearance_mode("dark") if t != "Light" else ctk.set_appearance_mode("light")
        else: ctk.set_appearance_mode("System")

    def get_color(self, key):
        t = self.data.get("theme", "Dark")
        if t not in THEMES: t = "Dark"
        return THEMES[t].get(key, "#000000")
        
    def get_radius(self, widget_type="default"):
        is_beta = self.data.get("beta_ui", False)
        if not is_beta: return 4
        if widget_type == "button": return 20
        if widget_type == "card": return 15
        if widget_type == "entry": return 10
        return 12

    def get_border_width(self): return 2 if self.data.get("beta_ui", False) else 1

cfg = ConfigManager()
cfg.apply_theme()

def t(key): return TRANSLATIONS.get(key, [key, key, key])[LANGS.get(cfg.data.get("language", "EN"), 0)]
def format_size(bytes_size):
    if bytes_size == 0: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0: return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0

class TransferStateManager:
    @staticmethod
    def save(job_type, src, dst, current_file, copied_bytes, total_bytes, extra_data=None):
        data = {"type": job_type, "src": src, "dst": dst, "file": current_file, "copied": copied_bytes, "total": total_bytes}
        if extra_data: data.update(extra_data)
        db.state = data; db.save()
            
    @staticmethod
    def clear(): db.state = None; db.save()
    @staticmethod
    def load(): return db.state

class SoundManager:
    def __init__(self):
        self.enabled = cfg.data.get("sound_enabled", True)
        self.bgm_enabled = cfg.data.get("bgm_enabled", True)
        self.snd_click = self.snd_tab = self.snd_close = self.snd_success = self.snd_error = None
        
        if PYGAME_SUPPORT:
            self.ch_sfx = pygame.mixer.Channel(1)
            def load_snd(name):
                p = get_res_path(os.path.join("sounds", name))
                return pygame.mixer.Sound(p) if os.path.exists(p) else None
            self.snd_click, self.snd_tab, self.snd_close, self.snd_success, self.snd_error = load_snd("sound_C.wav"), load_snd("sound_A.wav"), load_snd("sound_FF.wav"), load_snd("sound_CC.wav"), load_snd("sound_E.wav")
            self.update_bgm(self.bgm_enabled)

    def update_bgm(self, state):
        self.bgm_enabled = state
        if not PYGAME_SUPPORT: return
        bgm_path = get_res_path(os.path.join("sounds", "soundF.mp3"))
        if state and os.path.exists(bgm_path):
            if not pygame.mixer.music.get_busy():
                try: pygame.mixer.music.load(bgm_path); pygame.mixer.music.play(-1)
                except: pass
            else: pygame.mixer.music.unpause()
        else: pygame.mixer.music.pause()

    def _play_freq(self, freqs_durations):
        if not self.enabled or not SOUND_SUPPORT: return
        threading.Thread(target=lambda: [winsound.Beep(f, d) for f, d in freqs_durations], daemon=True).start()

    def play_click(self): self.ch_sfx.play(self.snd_click) if PYGAME_SUPPORT and self.snd_click else self._play_freq([(4000, 10)])
    def play_tab(self): self.ch_sfx.play(self.snd_tab) if PYGAME_SUPPORT and self.snd_tab else self._play_freq([(3000, 15)])
    def play_close(self): self.ch_sfx.play(self.snd_close) if PYGAME_SUPPORT and self.snd_close else self._play_freq([(1000, 100), (800, 150)])
    def play_success(self): self.ch_sfx.play(self.snd_success) if PYGAME_SUPPORT and self.snd_success else self._play_freq([(1200, 40), (1800, 60)])
    def play_error(self): self.ch_sfx.play(self.snd_error) if PYGAME_SUPPORT and self.snd_error else self._play_freq([(200, 150), (200, 150)])
    def play_usb(self, connected=True): self._play_freq([(800, 40), (1200, 40), (1800, 80)]) if connected else self._play_freq([(1800, 40), (1200, 40), (800, 80)])

sound_fx = SoundManager()

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
    def analyze(file_path):
        size = os.stat(file_path).st_size
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        game_id = GameAnalyzer.extract_game_id(file_path)
        return {
            "path": file_path, "name": os.path.splitext(filename)[0].replace('_', ' '),
            "id": game_id, "region": GameAnalyzer.REGION_MAP.get(game_id[:4], "Unknown") if game_id != "Unknown" and len(game_id)>=4 else "Unknown",
            "size_bytes": size, "size_str": format_size(size), "format": ext[1:].upper() if ext else "N/A",
            "status": "BAD" if game_id == "Unknown" else "EXCELLENT", "video_mode": "Auto", "resolution": "Default"
        }

class LibraryManager:
    @property
    def games(self): return db.library
    @games.setter
    def games(self, val): db.library = val
    def __init__(self): self.sync()
    def sync(self):
        if not cfg.data.get("auto_sync", True): return
        valid = [g for g in self.games if os.path.exists(g['path'])]
        if len(valid) != len(self.games): self.games = valid; db.save()
    def add(self, game_data):
        for i, g in enumerate(self.games):
            if g['path'] == game_data['path']:
                game_data['video_mode'] = g.get('video_mode', 'Auto')
                game_data['resolution'] = g.get('resolution', 'Default')
                self.games[i] = game_data; db.save(); return False
        self.games.append(game_data); db.save(); return True
    def stats(self): return {"total": len(self.games), "size_str": format_size(sum(g.get("size_bytes", 0) for g in self.games))}

class APAManager:
    @staticmethod
    def list_physical_drives():
        drives = []
        try:
            out = subprocess.check_output('wmic diskdrive get Name, Size, Model /value', shell=True, creationflags=subprocess.CREATE_NO_WINDOW).decode(errors='ignore')
            current = {}
            for line in out.strip().split('\n'):
                line = line.strip()
                if not line:
                    if 'Name' in current and 'Size' in current and 'Model' in current:
                        try: drives.append(f"{current['Name']} ({format_size(int(current['Size']))}) - {current['Model']}")
                        except: pass
                    current = {}
                else:
                    parts = line.split('=', 1)
                    if len(parts) == 2: current[parts[0]] = parts[1]
            if current and 'Name' in current and 'Size' in current: drives.append(f"{current['Name']} ({format_size(int(current['Size']))}) - {current.get('Model', '')}")
        except: pass
        return drives

    @staticmethod
    def create_fake_vhd():
        desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop")
        filepath = os.path.join(desktop, "Fake_PS2_HDD.img")
        try:
            with open(filepath, 'wb') as f:
                f.truncate(1024 * 1024 * 1024) 
                def write_apa(offset, part_id, ptype):
                    f.seek(offset)
                    part_id_bytes = part_id.encode('utf-8').ljust(32, b'\x00')
                    header = struct.pack('<I 4s I I 32s 8s I I', 0, b'APA\x00', 0, 0, part_id_bytes, b'', 0, ptype)
                    f.write(header)
                write_apa(0, "__mbr", 0x0000)
                write_apa(134217728, "+OPL", 0x0001)
                f.seek(134217728 + 1024); f.write(b"DIR: ART\nDIR: APPS\nDIR: CFG\nFILE: ART/SLUS_209.46_COV.png\n")
                write_apa(268435456, "PP.HDL.Crash_Bandicoot", 0x0100)
                write_apa(536870912, "PP.HDL.God_of_War_II", 0x0100)
            return filepath
        except: return None

    @staticmethod
    def read_apa_partitions(drive_path):
        partitions = []
        try:
            with open(drive_path, 'rb') as f:
                for i in range(0, 4096): 
                    offset = i * 134217728 
                    try: f.seek(offset); header = f.read(1024)
                    except IOError: break
                    if not header or len(header) < 64: break
                    if header[4:8] in [b'APA\x00', b'APA ', b'APA\x01']:
                        part_id = header[16:48].decode('utf-8', 'ignore').strip('\x00')
                        part_type = struct.unpack('<I', header[60:64])[0]
                        partitions.append({"id": part_id, "offset": offset, "type": part_type, "size_str": "128 MB" if part_type != 0x0100 else "Approx 4.0 GB", "is_game": part_id.startswith("PP.HDL.")})
        except: pass
        return partitions

    @staticmethod
    def get_raw_size(source):
        if source.startswith("\\\\.\\"):
            try:
                out = subprocess.check_output(f'wmic diskdrive where DeviceID="{source.replace("\\", "\\\\")}" get Size /value', shell=True, creationflags=subprocess.CREATE_NO_WINDOW).decode()
                for line in out.split('\n'):
                    if "Size=" in line: return int(line.split('=')[1].strip())
            except: return 500 * 1024 * 1024 * 1024 
        else: return os.path.getsize(source)
        return 0

    @staticmethod
    def backup_raw(source, dest, cb_prog, cb_done, cb_err):
        def run():
            try:
                if source.startswith("\\\\.\\"):
                    try: open(source, 'rb').close()
                    except PermissionError: return cb_err("Permission Denied! Run PS2Manager as Administrator.")
                total_size = APAManager.get_raw_size(source)
                copied = 0
                with open(source, 'rb') as f_src, open(dest, 'wb') as f_dst:
                    while True:
                        try:
                            buf = f_src.read(4 * 1024 * 1024)
                            if not buf: break
                            f_dst.write(buf)
                            copied += len(buf)
                            if total_size > 0: cb_prog(min(copied / total_size, 1.0))
                        except IOError: break
                cb_prog(1.0); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def restore_raw(img_source, dest, cb_prog, cb_done, cb_err):
        def run():
            try:
                if dest.startswith("\\\\.\\"):
                    try: open(dest, 'wb').close()
                    except PermissionError: return cb_err("Permission Denied! Run PS2Manager as Administrator.")
                total_size = APAManager.get_raw_size(img_source)
                copied = 0
                with open(img_source, 'rb') as f_src, open(dest, 'wb') as f_dst:
                    while True:
                        try:
                            buf = f_src.read(4 * 1024 * 1024)
                            if not buf: break
                            f_dst.write(buf)
                            copied += len(buf)
                            if total_size > 0: cb_prog(min(copied / total_size, 1.0))
                        except IOError: break
                cb_prog(1.0); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def extract_contents(source, dest_folder, cb_prog, cb_done, cb_err):
        def run():
            try:
                if source.startswith("\\\\.\\"):
                    try: open(source, 'rb').close()
                    except PermissionError: return cb_err("Permission Denied! Run PS2Manager as Administrator.")
                cb_prog(0.1)
                parts = APAManager.read_apa_partitions(source)
                if not parts: return cb_err("No APA signature detected! Extraction aborted.")
                cb_prog(0.2)
                with open(source, 'rb') as f_src:
                    for i, p in enumerate(parts):
                        if p['is_game']:
                            out_path = os.path.join(dest_folder, f"{p['id']}_Extracted.iso")
                            data_offset = p['offset'] + (4 * 1024 * 1024) 
                            try:
                                f_src.seek(data_offset)
                                with open(out_path, 'wb') as f_out:
                                    read_size, target_size = 0, 128 * 1024 * 1024 
                                    while read_size < target_size:
                                        chunk = f_src.read(min(4 * 1024 * 1024, target_size - read_size))
                                        if not chunk: break
                                        f_out.write(chunk)
                                        read_size += len(chunk)
                            except IOError: pass
                        cb_prog(0.2 + (0.8 * ((i + 1) / len(parts))))
                cb_prog(1.0); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

class TranslationPatcher:
    @staticmethod
    def patch_iso(iso_in, iso_out, patch_file, remove_region, cb_prog, cb_done, cb_err):
        def run():
            try:
                total_size = os.path.getsize(iso_in)
                copied = 0
                with open(iso_in, 'rb') as f_src, open(iso_out, 'wb') as f_dst:
                    while True:
                        buf = f_src.read(4 * 1024 * 1024)
                        if not buf: break
                        f_dst.write(buf)
                        copied += len(buf)
                        cb_prog((copied / total_size) * 0.8)
                if patch_file.lower().endswith('.ips'):
                    with open(patch_file, 'rb') as p, open(iso_out, 'r+b') as f:
                        if p.read(5) != b'PATCH': raise Exception("Invalid IPS file format.")
                        while True:
                            offset_bytes = p.read(3)
                            if offset_bytes == b'EOF': break
                            offset = int.from_bytes(offset_bytes, 'big')
                            size = int.from_bytes(p.read(2), 'big')
                            if size == 0:
                                rle_size = int.from_bytes(p.read(2), 'big')
                                val = p.read(1)
                                f.seek(offset); f.write(val * rle_size)
                            else:
                                data = p.read(size)
                                f.seek(offset); f.write(data)
                elif patch_file.lower().endswith(('.bps', '.xdelta')): return cb_err("BPS/XDelta requires external tools.")
                cb_prog(0.9)
                if remove_region:
                    with open(iso_out, 'r+b') as f:
                        f.seek(0x80000); f.write(b'\x00\x00\x01\xBA' + b'\x00'*16) 
                cb_prog(1.0); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

class ArtScraperWorker:
    @staticmethod
    def format_opl_id(game_id):
        clean = game_id.replace('-', '').replace('_', '').replace('.', '')
        if len(clean) == 9: return f"{clean[:4]}_{clean[4:7]}.{clean[7:]}"
        return game_id

    @staticmethod
    def get_repo_id(game_id):
        clean = game_id.replace('-', '').replace('_', '').replace('.', '')
        if len(clean) == 9: return f"{clean[:4]}-{clean[4:]}"
        return game_id

    @staticmethod
    def scan_for_ids(mountpoint):
        ids = set()
        for folder in [os.path.join(mountpoint, "DVD"), os.path.join(mountpoint, "CD")]:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    if f.lower().endswith('.iso'):
                        game_id = GameAnalyzer.extract_game_id(os.path.join(folder, f))
                        if game_id != "Unknown": ids.add(game_id)
        ul_path = os.path.join(mountpoint, "ul.cfg")
        if os.path.exists(ul_path):
            try:
                with open(ul_path, 'rb') as f:
                    while True:
                        entry = f.read(64)
                        if not entry or len(entry) < 64: break
                        game_id_raw = entry[32:47].decode('ascii', 'ignore').strip('\x00')
                        if game_id_raw.startswith("ul."): ids.add(game_id_raw[3:])
            except: pass
        return list(ids)

    @staticmethod
    def download_art(mountpoint, ids, cb_prog, cb_done, cb_err, cb_log):
        def run():
            try:
                art_folder = os.path.join(mountpoint, "ART")
                os.makedirs(art_folder, exist_ok=True)
                total = len(ids)
                if total == 0: cb_done(True); return
                base_url = "https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/{}.jpg"
                for i, game_id in enumerate(ids):
                    opl_id = ArtScraperWorker.format_opl_id(game_id)
                    target_file = os.path.join(art_folder, f"{opl_id}_COV.jpg")
                    if not os.path.exists(target_file):
                        url = base_url.format(ArtScraperWorker.get_repo_id(game_id))
                        cb_log(f"Fetching COVER for {opl_id}...")
                        try:
                            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=5) as response, open(target_file, 'wb') as out_file:
                                out_file.write(response.read())
                            cb_log(f"-> SUCCESS: Saved {opl_id}_COV.jpg")
                        except: cb_log(f"-> FAILED: Cover not found")
                    else: cb_log(f"Skipped {opl_id}")
                    cb_prog((i + 1) / total); time.sleep(0.1) 
                cb_log("Art download sequence complete."); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

class BinConverter:
    @staticmethod
    def convert(bin_path, iso_path, progress_cb, done_cb, err_cb, ps1_mode=False):
        def run():
            try:
                sector_size, data_offset, data_size = 2352, 24 if ps1_mode else 16, 2048
                total_size = os.path.getsize(bin_path)
                processed = 0
                with open(bin_path, 'rb') as f_in, open(iso_path, 'wb') as f_out:
                    while True:
                        sector = f_in.read(sector_size)
                        if not sector or len(sector) != sector_size: break
                        f_out.write(sector[data_offset:data_offset+data_size])
                        processed += len(sector)
                        if processed % (sector_size * 2000) == 0: progress_cb(processed / total_size)
                progress_cb(1.0); done_cb(iso_path)
            except Exception as e: err_cb(str(e))
        threading.Thread(target=run, daemon=True).start()

class USBUtilWorker:
    @staticmethod
    def split_and_generate(iso_path, dst_dir, game_name, cb_prog, cb_done, cb_err):
        def run():
            try:
                if not os.path.exists(iso_path) or not os.path.exists(dst_dir): raise Exception("Invalid paths.")
                game_id = GameAnalyzer.extract_game_id(iso_path)
                if game_id == "Unknown" or len(game_id) < 10: raise Exception("Invalid game ID in ISO.")
                safe_name = game_name.strip()[:32]
                crc = zlib.crc32(safe_name.encode('utf-8')) & 0xFFFFFFFF
                total_size = os.path.getsize(iso_path)
                chunk_size = 1073741824 
                num_parts = (total_size + chunk_size - 1) // chunk_size
                media_type = 0x14 if total_size >= 700 * 1024 * 1024 else 0x12 
                with open(iso_path, 'rb') as f_in:
                    for i in range(num_parts):
                        part_path = os.path.join(dst_dir, f"ul.{crc:08X}.{game_id}.{i:02d}")
                        with open(part_path, 'wb') as f_out:
                            bytes_to_write = min(chunk_size, total_size - (i * chunk_size))
                            written = 0
                            while written < bytes_to_write:
                                buf = f_in.read(1024 * 1024 * 4)
                                if not buf: break
                                f_out.write(buf)
                                written += len(buf)
                                cb_prog((i * chunk_size + written) / total_size)
                cfg_path = os.path.join(dst_dir, "ul.cfg")
                entry = struct.pack('<32s 15s B B 23x', safe_name.encode('ascii', 'ignore'), f"ul.{game_id}".encode('ascii', 'ignore'), num_parts, media_type)
                with open(cfg_path, 'ab') as f_cfg: f_cfg.write(entry)
                cb_prog(1.0); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

class RealIsoTool:
    @staticmethod
    def extract(src, dst, cb_prog, cb_done, cb_err):
        def run():
            try:
                os.makedirs(dst, exist_ok=True)
                abs_iso = os.path.abspath(src)
                ps_mount = f'powershell -ExecutionPolicy Bypass -Command "$img = Mount-DiskImage -ImagePath \'{abs_iso}\' -PassThru; $vol = $img | Get-Volume; if ($vol) {{ echo $vol.DriveLetter }} else {{ echo \'\' }}"'
                result = subprocess.run(ps_mount, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                drive_letter = result.stdout.strip()
                if not drive_letter:
                    sz_exe = r"C:\Program Files\7-Zip\7z.exe" if os.path.exists(r"C:\Program Files\7-Zip\7z.exe") else (r"C:\Program Files (x86)\7-Zip\7z.exe" if os.path.exists(r"C:\Program Files (x86)\7-Zip\7z.exe") else None)
                    if sz_exe:
                        res = subprocess.run(f'"{sz_exe}" x "{abs_iso}" -o"{dst}" -y', shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        if res.returncode == 0: cb_prog(1.0); return cb_done(True)
                        else: raise Exception(f"7-Zip extraction failed: {res.stderr}")
                    else: raise Exception("Failed to mount virtual disk. Windows 7 requires 7-Zip installed.")
                source_dir = f"{drive_letter}:\\"
                total_size = sum(os.path.getsize(os.path.join(r, f)) for r, d, files in os.walk(source_dir) for f in files)
                copied = 0
                for r, d, f in os.walk(source_dir):
                    for file in f:
                        s_path, d_path = os.path.join(r, file), os.path.join(dst, os.path.relpath(os.path.join(r, file), source_dir))
                        os.makedirs(os.path.dirname(d_path), exist_ok=True)
                        with open(s_path, 'rb') as fsrc, open(d_path, 'wb') as fdst:
                            while True:
                                buf = fsrc.read(1024 * 1024 * 4) 
                                if not buf: break
                                fdst.write(buf)
                                copied += len(buf)
                                if total_size > 0: cb_prog(copied / total_size)
                try: subprocess.run(f'powershell -Command "Dismount-DiskImage -ImagePath \'{abs_iso}\'"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                except: pass
                cb_prog(1.0); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def compress_zso(src, dst, level_str, cb_prog, cb_done, cb_err):
        def run():
            if not LZ4_SUPPORT: return cb_err("LZ4 Python module is absent.")
            try:
                sector_size = 2048
                iso_size = os.path.getsize(src)
                total_blocks = (iso_size + sector_size - 1) // sector_size
                fast_mode = "Fast" in level_str
                with open(src, 'rb') as f_in, open(dst, 'wb') as f_out:
                    f_out.write(b'\x00' * 24); f_out.write(b'\x00' * ((total_blocks + 1) * 4))
                    indices, write_pos = [], 24 + ((total_blocks + 1) * 4)
                    for i in range(total_blocks):
                        block_data = f_in.read(sector_size)
                        if not block_data: break
                        pad = ( (write_pos + 3) & ~3 ) - write_pos
                        if pad > 0: f_out.write(b'\x00' * pad); write_pos += pad
                        idx_val = write_pos >> 2
                        compressed = lz4.block.compress(block_data, store_size=False, mode='fast' if fast_mode else 'high_compression')
                        if len(compressed) >= len(block_data):
                            idx_val |= 0x80000000; f_out.write(block_data); write_pos += len(block_data)
                        else: f_out.write(compressed); write_pos += len(compressed)
                        indices.append(idx_val)
                        if i % 1000 == 0: cb_prog(i / total_blocks)
                    pad = ( (write_pos + 3) & ~3 ) - write_pos
                    if pad > 0: f_out.write(b'\x00' * pad); write_pos += pad
                    indices.append(write_pos >> 2)
                    f_out.seek(24); f_out.write(struct.pack(f'<{len(indices)}I', *indices))
                    f_out.seek(0); f_out.write(struct.pack('<4s I Q I B B H', b'ZISO', 24, iso_size, sector_size, 1, 2, 0))
                cb_prog(1.0); cb_done(True)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

class DriveManager:
    @staticmethod
    def get_drives():
        drives = []
        for p in psutil.disk_partitions(all=False):
            if p.fstype.lower() in ['fat32', 'exfat', 'ntfs', 'fat', 'fat16']:
                if p.device.startswith('C:'): continue 
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    drives.append({"device": p.device, "mountpoint": p.mountpoint, "fstype": p.fstype, "total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent})
                except: continue
        return drives

    @staticmethod
    def analyze_opl_structure(mountpoint):
        struct_info = {d: os.path.isdir(os.path.join(mountpoint, d)) for d in ['DVD', 'CD', 'ART', 'CFG', 'VMC', 'APPS']}
        return {"folders": struct_info, "status": "VALID" if all(struct_info.values()) else ("INCOMPLETE" if struct_info['DVD'] or struct_info['CD'] else "INVALID")}

class PhysicalDriveRipper:
    @staticmethod
    def get_optical_drives():
        drives = []
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                if bitmask & 1 and ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\") == 5: drives.append(f"{letter}:\\")
                bitmask >>= 1
        except: pass
        return drives

    @staticmethod
    def rip_drive(drive_letter, output_dir, force_iso, cb_prog, cb_done, cb_err):
        def run():
            try:
                drive_path = f"\\\\.\\{drive_letter[0]}:"
                output_file = os.path.join(output_dir, f"PS2_DISC_{int(time.time())}.iso")
                try: total_size = psutil.disk_usage(drive_letter).total
                except: total_size = 4 * 1024 * 1024 * 1024 
                copied = 0
                with open(drive_path, 'rb') as f_in, open(output_file, 'wb') as f_out:
                    while True:
                        try:
                            chunk = f_in.read(2048 * 1024)
                            if not chunk: break
                            f_out.write(chunk)
                            copied += len(chunk)
                            if total_size > 0: cb_prog(min(copied / total_size, 1.0))
                        except IOError: break
                cb_prog(1.0); cb_done(output_file)
            except Exception as e: cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def analyze_disc(drive_letter):
        info = {"game_id": "Unknown", "region": "Unknown", "size_str": "Unknown", "status": "No Disc / Unreadable"}
        try:
            info["size_str"] = format_size(psutil.disk_usage(drive_letter).total)
            info["status"] = "Readable Disc"
            cnf_path = os.path.join(drive_letter, "SYSTEM.CNF")
            if os.path.exists(cnf_path):
                with open(cnf_path, "r", encoding="utf-8", errors="ignore") as f:
                    m = re.search(r'BOOT2\s*=\s*cdrom0:\\(.*?);', f.read(), re.IGNORECASE)
                    if m:
                        info["game_id"] = m.group(1).replace('_', '-').replace('.', '').upper()
                        info["region"] = GameAnalyzer.REGION_MAP.get(info["game_id"][:4], "Unknown")
                        info["status"] = "Valid PS2 Disc"
        except: pass
        return info

class PCSX2Integration:
    @staticmethod
    def test_iso(iso_path, err_cb):
        def run():
            try:
                clean_iso_path = os.path.normpath(os.path.abspath(iso_path))
                if not os.path.exists(clean_iso_path): return err_cb("File not found")
                docs_path = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Documents", "PCSX2")
                if not os.path.exists(os.path.join(docs_path, "bios")): shutil.copytree(get_res_path(os.path.join("pcsx2", "ETC", "PCSX2")), docs_path, dirs_exist_ok=True)
                base_pcsx2 = get_res_path("pcsx2")
                exe_path = next((os.path.join(base_pcsx2, e) for e in ["pcsx2-qt.exe", "pcsx2-qtx64.exe", "pcsx2.exe"] if os.path.exists(os.path.join(base_pcsx2, e))), None)
                if not exe_path: return err_cb("Emulator executable not found.")
                subprocess.Popen([exe_path, clean_iso_path], cwd=base_pcsx2)
            except Exception as e: err_cb(str(e))
        threading.Thread(target=run, daemon=True).start()

class MigrationWorker:
    def __init__(self, drive, target_fs, callbacks, resume_data=None):
        self.drive, self.target_fs, self.cb_log, self.cb_prog_total, self.cb_prog_step, self.cb_done, self.tmp_dir, self.cancel_flag, self.resume_data = drive, target_fs, callbacks['log'], callbacks['prog_total'], callbacks['prog_step'], callbacks['done'], os.path.join(APP_DATA_DIR, "jogos.tmp"), False, resume_data
    def _copy_dir_with_progress(self, src_dir, dst_dir):
        if not os.path.exists(dst_dir): os.makedirs(dst_dir)
        for r, d, f in os.walk(src_dir):
            for file in f:
                s_path, d_path = os.path.join(r, file), os.path.join(dst_dir, os.path.relpath(os.path.join(r, file), src_dir))
                os.makedirs(os.path.dirname(d_path), exist_ok=True)
                offset = self.resume_data.get("copied", 0) if self.resume_data and self.resume_data.get("file") == s_path else 0
                self.resume_data = None
                size = os.path.getsize(s_path)
                copied = offset
                with open(s_path, 'rb') as fsrc, open(d_path, 'ab' if offset > 0 else 'wb') as fdst:
                    fsrc.seek(offset)
                    while True:
                        if self.cancel_flag: raise Exception("Cancelled")
                        buf = fsrc.read(1024 * 1024 * 4)
                        if not buf: break
                        fdst.write(buf); copied += len(buf); self.cb_prog_step(copied / size if size > 0 else 1)
                        TransferStateManager.save("migration", self.drive['mountpoint'], self.target_fs, s_path, copied, size)
    def run(self):
        try:
            self.cb_prog_total(0.0)
            if not self.resume_data:
                self.cb_log("Backup in progress..."); self.cb_prog_total(0.1)
                if os.path.exists(self.tmp_dir): shutil.rmtree(self.tmp_dir)
                self._copy_dir_with_progress(self.drive['mountpoint'], self.tmp_dir)
                self.cb_log("Formatting via DiskPart..."); self.cb_prog_total(0.4)
                script_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"dp_{int(time.time())}.txt")
                with open(script_path, "w") as f: f.write(f"select volume {self.drive['device'].replace(':', '').replace('\\', '')}\nformat fs={self.target_fs} label=PS2USB quick\n")
                subprocess.run(f'diskpart /s "{script_path}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if os.path.exists(script_path): os.remove(script_path)
            self.cb_log("Restoring files..."); self.cb_prog_total(0.5)
            self._copy_dir_with_progress(self.tmp_dir, self.drive['mountpoint'])
            self.cb_prog_total(0.9)
            if os.path.exists(self.tmp_dir): shutil.rmtree(self.tmp_dir)
            TransferStateManager.clear(); self.cb_prog_total(1.0); self.cb_prog_step(1.0); self.cb_done(True)
        except Exception as e: self.cb_log(f"ERROR: {str(e)}"); self.cb_done(False)

class CloneWorker:
    def __init__(self, src_drive, dst_drive, format_dst, format_src, callbacks, resume_data=None):
        self.src, self.dst, self.f_dst, self.f_src, self.cb_log, self.cb_prog_total, self.cancel_flag, self.resume_data = src_drive, dst_drive, format_dst, format_src, callbacks['log'], callbacks['prog_total'], False, resume_data
    def _diskpart_format(self, drive, fs, label):
        script_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"dp_clone_{int(time.time())}.txt")
        with open(script_path, "w") as f: f.write(f"select volume {drive.replace(':', '').replace('\\', '')}\nformat fs={fs} label={label} quick\n")
        subprocess.run(f'diskpart /s "{script_path}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if os.path.exists(script_path): os.remove(script_path)
    def run(self):
        try:
            self.cb_prog_total(0.0)
            if self.f_dst and not self.resume_data: self._diskpart_format(self.dst['device'], "FAT32", "PS2USB")
            for r, dirs, files in os.walk(self.src['mountpoint']):
                for d in dirs: os.makedirs(os.path.join(self.dst['mountpoint'], os.path.relpath(os.path.join(r, d), self.src['mountpoint'])), exist_ok=True)
                for f in files:
                    s_file, d_file = os.path.join(r, f), os.path.join(self.dst['mountpoint'], os.path.relpath(os.path.join(r, f), self.src['mountpoint']))
                    offset = self.resume_data.get("copied", 0) if self.resume_data and self.resume_data.get("file") == s_file else 0
                    self.resume_data, size, copied = None, os.path.getsize(s_file), offset
                    with open(s_file, 'rb') as fsrc, open(d_file, 'ab' if offset > 0 else 'wb') as fdst:
                        fsrc.seek(offset)
                        while True:
                            if self.cancel_flag: raise Exception("Cancelled")
                            buf = fsrc.read(1024 * 1024 * 4)
                            if not buf: break
                            fdst.write(buf); copied += len(buf)
                            TransferStateManager.save("clone", self.src['mountpoint'], self.dst['mountpoint'], s_file, copied, size, {"fmt_after": self.f_src})
            if self.f_src: self._diskpart_format(self.src['device'], "FAT32", "EMPTY_USB")
            TransferStateManager.clear(); self.cb_prog_total(1.0)
        except Exception as e: self.cb_log(f"ERROR: {str(e)}")

class OplAppsManager:
    @staticmethod
    def install_app(app_name, elf_path, usb_mountpoint):
        try:
            apps_dir = os.path.join(usb_mountpoint, "APPS")
            safe_name = "".join(c for c in app_name if c.isalnum() or c in (' ', '_')).rstrip()
            target_dir = os.path.join(apps_dir, safe_name)
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(elf_path, os.path.join(target_dir, "boot.elf"))
            with open(os.path.join(target_dir, "title.cfg"), "w") as f: f.write(f"title={app_name}\nboot=boot.elf\n")
            return True
        except Exception as e: return str(e)