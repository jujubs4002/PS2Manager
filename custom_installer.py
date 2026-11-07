from __future__ import annotations

import os
import sys
import time
import shutil
import ctypes
import threading
import subprocess
import zipfile
import hashlib
import re
import customtkinter as ctk
from tkinter import messagebox, filedialog

try:
    import winsound
    SOUND_SUPPORT = True
except ImportError:
    SOUND_SUPPORT = False


def is_admin():
    """Verifica se o processo atual possui privilégios de Administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


# Se não for admin e não estiver em modo de teste, reinicia solicitando elevação
if not is_admin() and "--no-uac" not in sys.argv and "--test" not in sys.argv:
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    try:
        if getattr(sys, 'frozen', False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}" {params}', None, 1)
        sys.exit(0)
    except Exception:
        pass


def detect_system_language():
    """Detecta o idioma do Windows para selecionar a linguagem padrão."""
    try:
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage() & 0x3FF
        sub_id = (windll.GetUserDefaultUILanguage() >> 10) & 0x3F
        if lang_id == 0x16:  # Portuguese
            return "PT_BR" if sub_id == 0x01 else "PT"
        elif lang_id == 0x0A:  # Spanish
            return "ES"
        elif lang_id == 0x19:  # Russian
            return "RU"
        elif lang_id == 0x11:  # Japanese
            return "JA"
    except Exception:
        pass
    return "PT_BR"


# ==============================================================================
# DICIONÁRIO DE TRADUÇÕES COMPLETO (6 IDIOMAS)
# ==============================================================================
TRANSLATIONS = {
    "PT_BR": {
        "app_title": "PS2Manager - Assistente de Instalação Oficial",
        "wizard_step1": "Boas-vindas",
        "wizard_step2": "Destino & Opções",
        "wizard_step3": "Instalação",
        "wizard_step4": "Concluído",
        "welcome_title": "Bem-vindo ao PS2Manager",
        "welcome_desc": "A central definitiva para gerenciamento de jogos, OPL, capas, cheats e conversões para seu PlayStation 2.",
        "badge_install": "NOVA INSTALAÇÃO",
        "badge_update": "ATUALIZAÇÃO DISPONÍVEL",
        "badge_reinstall": "REINSTALAÇÃO",
        "badge_downgrade": "REVERSÃO (DOWNGRADE)",
        "info_current": "Versão Instalada:",
        "info_target": "Versão do Pacote:",
        "info_none": "Nenhuma (Não instalado)",
        "highlights_title": "Novidades e Destaques da Versão 1.07:",
        "feat_1": "✓ Suporte completo a 6 idiomas (PT_BR, PT, EN, ES, RU, JA)",
        "feat_2": "✓ Gravador de DVD integrado para mídias físicas de PS2",
        "feat_3": "✓ Fila de instalação de jogos em lote (Batch)",
        "feat_4": "✓ Gerenciador avançado de Cheats (.cht) com editor RAW",
        "feat_5": "✓ Proteção de dados ativa contra corrupção em transferências",
        "opt_title": "Configuração da Instalação",
        "opt_desc": "Escolha onde o PS2Manager será instalado e selecione os atalhos desejados.",
        "dest_label": "Pasta de Destino:",
        "browse": "Procurar...",
        "space_req": "Espaço Necessário:",
        "space_free": "Espaço Livre no Disco:",
        "chk_desktop": "Criar atalho na Área de Trabalho (Desktop)",
        "chk_start": "Criar atalho no Menu Iniciar",
        "chk_launch": "Iniciar o PS2Manager ao concluir a instalação",
        "chk_keep_data": "Preservar configurações e biblioteca do AppData",
        "installing_title": "Instalando o PS2Manager...",
        "installing_desc": "Por favor aguarde enquanto os arquivos são extraídos e configurados.",
        "status_ready": "Pronto para iniciar.",
        "status_closing": "Encerrando instâncias em execução do PS2Manager...",
        "status_clean": "Removendo versão anterior com segurança...",
        "status_calc": "Calculando estrutura do pacote...",
        "status_extracting": "Extraindo",
        "status_appdata": "Atualizando chave e biblioteca no AppData...",
        "status_shortcuts": "Criando atalhos e ícones no sistema...",
        "status_registry": "Registrando programa no Painel de Controle...",
        "status_success": "Instalação concluída com sucesso!",
        "finish_title": "Instalação Concluída com Sucesso!",
        "finish_desc": "O PS2Manager v1.07 foi instalado com sucesso e está pronto para ser utilizado.",
        "finish_path": "Local de Instalação:",
        "finish_ver": "Versão Ativa:",
        "btn_next": "Avançar >",
        "btn_back": "< Voltar",
        "btn_install": "INSTALAR PS2MANAGER",
        "btn_update": "ATUALIZAR PS2MANAGER",
        "btn_reinstall": "REINSTALAR PS2MANAGER",
        "btn_downgrade": "REVERTER VERSÃO",
        "btn_finish": "CONCLUIR",
        "btn_launch_now": "ABRIR O PS2MANAGER AGORA",
        "sound_on": "🔊 Som Ativado",
        "sound_off": "🔇 Mudo",
        "warn_downgrade": "Você está prestes a reverter o PS2Manager da versão {old} para a versão {new}.\n\nTem certeza de que deseja continuar?",
        "warn_space": "O disco selecionado não possui espaço suficiente para a instalação!\nEspaço necessário: ~{req} MB | Espaço livre: {free} MB",
        "err_title": "Erro na Instalação",
        "select_folder": "Selecione a Pasta de Instalação"
    },
    "PT": {
        "app_title": "PS2Manager - Assistente de Instalação Oficial",
        "wizard_step1": "Boas-vindas",
        "wizard_step2": "Destino & Opções",
        "wizard_step3": "Instalação",
        "wizard_step4": "Concluído",
        "welcome_title": "Bem-vindo ao PS2Manager",
        "welcome_desc": "A central definitiva para gestão de jogos, OPL, capas, cheats e conversões para o seu PlayStation 2.",
        "badge_install": "NOVA INSTALAÇÃO",
        "badge_update": "ATUALIZAÇÃO DISPONÍVEL",
        "badge_reinstall": "REINSTALAÇÃO",
        "badge_downgrade": "REVERSÃO (DOWNGRADE)",
        "info_current": "Versão Instalada:",
        "info_target": "Versão do Pacote:",
        "info_none": "Nenhuma (Não instalado)",
        "highlights_title": "Novidades e Destaques da Versão 1.07:",
        "feat_1": "✓ Suporte completo a 6 idiomas (PT_BR, PT, EN, ES, RU, JA)",
        "feat_2": "✓ Gravador de DVD integrado para suportes físicos de PS2",
        "feat_3": "✓ Fila de instalação de jogos em lote (Batch)",
        "feat_4": "✓ Gestor avançado de Cheats (.cht) com editor RAW",
        "feat_5": "✓ Proteção de dados ativa contra corrupção em transferências",
        "opt_title": "Configuração da Instalação",
        "opt_desc": "Escolha onde o PS2Manager será instalado e selecione os atalhos desejados.",
        "dest_label": "Pasta de Destino:",
        "browse": "Procurar...",
        "space_req": "Espaço Necessário:",
        "space_free": "Espaço Livre no Disco:",
        "chk_desktop": "Criar atalho no Ambiente de Trabalho",
        "chk_start": "Criar atalho no Menu Iniciar",
        "chk_launch": "Iniciar o PS2Manager ao concluir a instalação",
        "chk_keep_data": "Preservar configurações e biblioteca do AppData",
        "installing_title": "A instalar o PS2Manager...",
        "installing_desc": "Por favor aguarde enquanto os ficheiros são extraídos e configurados.",
        "status_ready": "Pronto para iniciar.",
        "status_closing": "A encerrar instâncias em execução do PS2Manager...",
        "status_clean": "A remover versão anterior com segurança...",
        "status_calc": "A calcular estrutura do pacote...",
        "status_extracting": "A extrair",
        "status_appdata": "A atualizar chave e biblioteca no AppData...",
        "status_shortcuts": "A criar atalhos e ícones no sistema...",
        "status_registry": "A registar programa no Painel de Controlo...",
        "status_success": "Instalação concluída com sucesso!",
        "finish_title": "Instalação Concluída com Sucesso!",
        "finish_desc": "O PS2Manager v1.07 foi instalado com sucesso e está pronto a ser utilizado.",
        "finish_path": "Local de Instalação:",
        "finish_ver": "Versão Ativa:",
        "btn_next": "Avançar >",
        "btn_back": "< Voltar",
        "btn_install": "INSTALAR PS2MANAGER",
        "btn_update": "ATUALIZAR PS2MANAGER",
        "btn_reinstall": "REINSTALAR PS2MANAGER",
        "btn_downgrade": "REVERTER VERSÃO",
        "btn_finish": "CONCLUIR",
        "btn_launch_now": "ABRIR O PS2MANAGER AGORA",
        "sound_on": "🔊 Som Ativado",
        "sound_off": "🔇 Mudo",
        "warn_downgrade": "Está prestes a reverter o PS2Manager da versão {old} para a versão {new}.\n\nTem a certeza de que deseja continuar?",
        "warn_space": "O disco selecionado não possui espaço suficiente para a instalação!\nEspaço necessário: ~{req} MB | Espaço livre: {free} MB",
        "err_title": "Erro na Instalação",
        "select_folder": "Selecione a Pasta de Instalação"
    },
    "EN": {
        "app_title": "PS2Manager - Official Setup Wizard",
        "wizard_step1": "Welcome",
        "wizard_step2": "Destination & Options",
        "wizard_step3": "Installation",
        "wizard_step4": "Finished",
        "welcome_title": "Welcome to PS2Manager",
        "welcome_desc": "The ultimate management suite for games, OPL, cover arts, cheats and conversions for your PlayStation 2.",
        "badge_install": "NEW INSTALLATION",
        "badge_update": "UPDATE AVAILABLE",
        "badge_reinstall": "REINSTALLATION",
        "badge_downgrade": "ROLLBACK (DOWNGRADE)",
        "info_current": "Currently Installed:",
        "info_target": "Package Version:",
        "info_none": "None (Not installed)",
        "highlights_title": "What's New in Version 1.07:",
        "feat_1": "✓ Full support for 6 languages (PT_BR, PT, EN, ES, RU, JA)",
        "feat_2": "✓ Integrated physical DVD burning engine with speed control",
        "feat_3": "✓ Batch game installation queue system",
        "feat_4": "✓ Advanced OPL Cheat (.cht) manager with RAW editor",
        "feat_5": "✓ Active anti-corruption protection for transfers",
        "opt_title": "Installation Settings",
        "opt_desc": "Choose where PS2Manager will be installed and select shortcut preferences.",
        "dest_label": "Destination Folder:",
        "browse": "Browse...",
        "space_req": "Required Space:",
        "space_free": "Available Disk Space:",
        "chk_desktop": "Create Desktop shortcut",
        "chk_start": "Create Start Menu folder",
        "chk_launch": "Launch PS2Manager when setup finishes",
        "chk_keep_data": "Preserve existing AppData configurations and library",
        "installing_title": "Installing PS2Manager...",
        "installing_desc": "Please wait while files are extracted and configured on your system.",
        "status_ready": "Ready to process.",
        "status_closing": "Closing running instances of PS2Manager...",
        "status_clean": "Safely removing previous installation...",
        "status_calc": "Calculating package size...",
        "status_extracting": "Extracting",
        "status_appdata": "Migrating AppData library and signatures...",
        "status_shortcuts": "Creating system shortcuts and icons...",
        "status_registry": "Registering in Windows Control Panel...",
        "status_success": "Installation completed successfully!",
        "finish_title": "Installation Finished Successfully!",
        "finish_desc": "PS2Manager v1.07 has been installed and is ready to use.",
        "finish_path": "Install Path:",
        "finish_ver": "Active Version:",
        "btn_next": "Next >",
        "btn_back": "< Back",
        "btn_install": "INSTALL PS2MANAGER",
        "btn_update": "UPDATE PS2MANAGER",
        "btn_reinstall": "REINSTALL PS2MANAGER",
        "btn_downgrade": "ROLLBACK VERSION",
        "btn_finish": "FINISH",
        "btn_launch_now": "LAUNCH PS2MANAGER NOW",
        "sound_on": "🔊 Sound: On",
        "sound_off": "🔇 Mute",
        "warn_downgrade": "You are about to rollback PS2Manager from version {old} to {new}.\n\nAre you sure you want to proceed?",
        "warn_space": "The selected drive does not have enough free disk space!\nRequired: ~{req} MB | Available: {free} MB",
        "err_title": "Installation Error",
        "select_folder": "Select Destination Folder"
    },
    "ES": {
        "app_title": "PS2Manager - Asistente de Instalación Oficial",
        "wizard_step1": "Bienvenido",
        "wizard_step2": "Destino y Opciones",
        "wizard_step3": "Instalación",
        "wizard_step4": "Completado",
        "welcome_title": "Bienvenido a PS2Manager",
        "welcome_desc": "La suite definitiva para administración de juegos, OPL, carátulas, trucos y conversiones para PlayStation 2.",
        "badge_install": "NUEVA INSTALACIÓN",
        "badge_update": "ACTUALIZACIÓN DISPONIBLE",
        "badge_reinstall": "REINSTALACIÓN",
        "badge_downgrade": "REVERSIÓN (DOWNGRADE)",
        "info_current": "Versión Instalada:",
        "info_target": "Versión del Paquete:",
        "info_none": "Ninguna (No instalado)",
        "highlights_title": "Novedades de la Versión 1.07:",
        "feat_1": "✓ Soporte completo para 6 idiomas (PT_BR, PT, EN, ES, RU, JA)",
        "feat_2": "✓ Grabador de DVD integrado con selector de velocidad",
        "feat_3": "✓ Cola de instalación de juegos en lote (Batch)",
        "feat_4": "✓ Gestor avanzado de Trucos (.cht) con editor RAW",
        "feat_5": "✓ Protección activa de datos contra corrupción",
        "opt_title": "Configuración de Instalación",
        "opt_desc": "Elija la carpeta de destino y sus preferencias de accesos directos.",
        "dest_label": "Carpeta de Destino:",
        "browse": "Examinar...",
        "space_req": "Espacio Requerido:",
        "space_free": "Espacio Disponible:",
        "chk_desktop": "Crear acceso directo en el Escritorio",
        "chk_start": "Crear carpeta en el Menú Inicio",
        "chk_launch": "Iniciar PS2Manager al finalizar",
        "chk_keep_data": "Preservar datos y biblioteca de AppData",
        "installing_title": "Instalando PS2Manager...",
        "installing_desc": "Espere mientras los archivos se extraen y configuran.",
        "status_ready": "Listo para iniciar.",
        "status_closing": "Cerrando instancias de PS2Manager...",
        "status_clean": "Eliminando versión anterior de forma segura...",
        "status_calc": "Calculando tamaño del paquete...",
        "status_extracting": "Extrayendo",
        "status_appdata": "Migrando datos y biblioteca de AppData...",
        "status_shortcuts": "Creando accesos directos del sistema...",
        "status_registry": "Registrando aplicación en Panel de Control...",
        "status_success": "¡Instalación completada con éxito!",
        "finish_title": "¡Instalación Completada con Éxito!",
        "finish_desc": "PS2Manager v1.07 se ha instalado y está listo para usarse.",
        "finish_path": "Ruta de Instalación:",
        "finish_ver": "Versión Activa:",
        "btn_next": "Siguiente >",
        "btn_back": "< Atrás",
        "btn_install": "INSTALAR PS2MANAGER",
        "btn_update": "ACTUALIZAR PS2MANAGER",
        "btn_reinstall": "REINSTALAR PS2MANAGER",
        "btn_downgrade": "REVERTIR VERSIÓN",
        "btn_finish": "FINALIZAR",
        "btn_launch_now": "ABRIR PS2MANAGER AHORA",
        "sound_on": "🔊 Sonido Activado",
        "sound_off": "🔇 Silencio",
        "warn_downgrade": "Está a punto de revertir PS2Manager de la versión {old} a la versión {new}.\n\n¿Seguro que desea continuar?",
        "warn_space": "¡El disco seleccionado no tiene suficiente espacio libre!\nRequerido: ~{req} MB | Disponible: {free} MB",
        "err_title": "Error de Instalación",
        "select_folder": "Seleccione la Carpeta de Destino"
    },
    "RU": {
        "app_title": "PS2Manager - Официальный мастер установки",
        "wizard_step1": "Приветствие",
        "wizard_step2": "Папка и опции",
        "wizard_step3": "Установка",
        "wizard_step4": "Готово",
        "welcome_title": "Добро пожаловать в PS2Manager",
        "welcome_desc": "Лучший центр управления играми, OPL, обложками, читами и конвертацией для вашей PlayStation 2.",
        "badge_install": "НОВАЯ УСТАНОВКА",
        "badge_update": "ДОСТУПНО ОБНОВЛЕНИЕ",
        "badge_reinstall": "ПЕРЕУСТАНОВКА",
        "badge_downgrade": "ОТКАТ ВЕРСИИ",
        "info_current": "Текущая версия:",
        "info_target": "Версия пакета:",
        "info_none": "Не установлена",
        "highlights_title": "Что нового в версии 1.07:",
        "feat_1": "✓ Полная поддержка 6 языков (PT_BR, PT, EN, ES, RU, JA)",
        "feat_2": "✓ Встроенная запись DVD с контролем скорости",
        "feat_3": "✓ Очередь пакетной установки игр (Batch)",
        "feat_4": "✓ Менеджер OPL-читов (.cht) с RAW-редактором",
        "feat_5": "✓ Активная защита от повреждения данных",
        "opt_title": "Параметры установки",
        "opt_desc": "Выберите каталог установки и желаемые ярлыки.",
        "dest_label": "Папка назначения:",
        "browse": "Обзор...",
        "space_req": "Требуется места:",
        "space_free": "Свободно на диске:",
        "chk_desktop": "Создать ярлык на Рабочем столе",
        "chk_start": "Создать пункт в меню Пуск",
        "chk_launch": "Запустить PS2Manager после завершения",
        "chk_keep_data": "Сохранить данные и библиотеку AppData",
        "installing_title": "Установка PS2Manager...",
        "installing_desc": "Пожалуйста, подождите, пока файлы распаковываются.",
        "status_ready": "Готов к установке.",
        "status_closing": "Закрытие работающих процессов PS2Manager...",
        "status_clean": "Удаление предыдущей версии...",
        "status_calc": "Расчет размера файлов...",
        "status_extracting": "Извлечение",
        "status_appdata": "Обновление AppData...",
        "status_shortcuts": "Создание ярлыков...",
        "status_registry": "Регистрация в Панели управления...",
        "status_success": "Установка успешно завершена!",
        "finish_title": "Установка успешно завершена!",
        "finish_desc": "PS2Manager v1.07 установлен и готов к использованию.",
        "finish_path": "Путь установки:",
        "finish_ver": "Активная версия:",
        "btn_next": "Далее >",
        "btn_back": "< Назад",
        "btn_install": "УСТАНОВИТЬ PS2MANAGER",
        "btn_update": "ОБНОВИТЬ PS2MANAGER",
        "btn_reinstall": "ПЕРЕУСТАНОВИТЬ PS2MANAGER",
        "btn_downgrade": "ОТКАТИТЬ ВЕРСИЮ",
        "btn_finish": "ГОТОВО",
        "btn_launch_now": "ЗАПУСТИТЬ PS2MANAGER",
        "sound_on": "🔊 Звук: Вкл",
        "sound_off": "🔇 Без звука",
        "warn_downgrade": "Вы собираетесь откатить PS2Manager с {old} до {new}.\n\nПродолжить?",
        "warn_space": "На выбранном диске недостаточно свободного места!\nТребуется: ~{req} МБ | Доступно: {free} МБ",
        "err_title": "Ошибка установки",
        "select_folder": "Выберите папку назначения"
    },
    "JA": {
        "app_title": "PS2Manager - 公式セットアップウィザード",
        "wizard_step1": "ようこそ",
        "wizard_step2": "保存先とオプション",
        "wizard_step3": "インストール",
        "wizard_step4": "完了",
        "welcome_title": "PS2Managerへようこそ",
        "welcome_desc": "PlayStation 2のゲーム、OPL、カバーアート、チート、変換を管理する究極のスイート。",
        "badge_install": "新規インストール",
        "badge_update": "アップデート利用可能",
        "badge_reinstall": "再インストール",
        "badge_downgrade": "ダウングレード",
        "info_current": "現在のバージョン:",
        "info_target": "パッケージバージョン:",
        "info_none": "未インストール",
        "highlights_title": "バージョン1.07の新機能:",
        "feat_1": "✓ 6言語の完全サポート (PT_BR, PT, EN, ES, RU, JA)",
        "feat_2": "✓ 速度調整可能な物理DVD書き込み機能",
        "feat_3": "✓ ゲームの一括バッチインストール機能",
        "feat_4": "✓ RAWエディタ付きOPLチート(.cht)マネージャー",
        "feat_5": "✓ 転送時のデータ破損防止保護",
        "opt_title": "インストール設定",
        "opt_desc": "インストール先とショートカット設定を選択してください。",
        "dest_label": "インストール先フォルダ:",
        "browse": "参照...",
        "space_req": "必要容量:",
        "space_free": "空き容量:",
        "chk_desktop": "デスクトップにショートカットを作成",
        "chk_start": "スタートメニューに登録",
        "chk_launch": "完了後にPS2Managerを起動",
        "chk_keep_data": "既存のAppDataとゲームライブラリを保持",
        "installing_title": "PS2Managerをインストール中...",
        "installing_desc": "ファイルが展開および構成されるまでお待ちください。",
        "status_ready": "準備完了",
        "status_closing": "実行中のPS2Managerを終了中...",
        "status_clean": "以前のバージョンを安全に削除中...",
        "status_calc": "パッケージサイズを計算中...",
        "status_extracting": "展開中",
        "status_appdata": "AppDataデータを更新中...",
        "status_shortcuts": "ショートカットを作成中...",
        "status_registry": "コントロールパネルに登録中...",
        "status_success": "インストールが正常に完了しました！",
        "finish_title": "インストールが完了しました！",
        "finish_desc": "PS2Manager v1.07が正常にインストールされました。",
        "finish_path": "インストール先:",
        "finish_ver": "現在のバージョン:",
        "btn_next": "次へ >",
        "btn_back": "< 戻る",
        "btn_install": "今すぐインストール",
        "btn_update": "今すぐアップデート",
        "btn_reinstall": "再インストール",
        "btn_downgrade": "バージョンをダウングレード",
        "btn_finish": "完了",
        "btn_launch_now": "PS2MANAGERを今すぐ起動",
        "sound_on": "🔊 サウンド: オン",
        "sound_off": "🔇 ミュート",
        "warn_downgrade": "バージョンを {old} から {new} にダウングレードします。\n\n続行しますか？",
        "warn_space": "選択したディスクに十分な空き容量がありません。\n必要容量: ~{req} MB | 空き容量: {free} MB",
        "err_title": "インストールエラー",
        "select_folder": "インストール先を選択"
    }
}


# ==============================================================================
# MOTOR DE SONS MODERNO (AUDIO ENGINE - ZERO BUZZER/BEEPS)
# ==============================================================================
class InstallerSoundEngine:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.enabled = True
        self.sounds_dir = os.path.join(base_dir, "sounds")
        if not os.path.exists(self.sounds_dir) and getattr(sys, 'frozen', False):
            self.sounds_dir = os.path.join(getattr(sys, '_MEIPASS', ''), "sounds")

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.play_click()
        return self.enabled

    def play_wav(self, filename):
        if not self.enabled or not SOUND_SUPPORT:
            return
        fp = os.path.join(self.sounds_dir, filename)
        if os.path.exists(fp):
            try:
                winsound.PlaySound(fp, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            except Exception:
                pass

    def play_click(self):
        self.play_wav("sound_C.wav")

    def play_action(self):
        self.play_wav("sound_A.wav")

    def play_error(self):
        self.play_wav("sound_E.wav")

    def play_success(self):
        self.play_wav("sound_FF.wav")

    def play_welcome(self):
        if not self.enabled:
            return
        mp3 = os.path.join(self.sounds_dir, "soundF.mp3")
        if os.path.exists(mp3):
            def _play_mci():
                try:
                    alias = f"ps2_inst_{int(time.time()*1000)}"
                    ctypes.windll.winmm.mciSendStringW(f'open "{mp3}" type mpegvideo alias {alias}', None, 0, 0)
                    ctypes.windll.winmm.mciSendStringW(f'play {alias}', None, 0, 0)
                    time.sleep(3.5)
                    ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, 0)
                except Exception:
                    pass
            threading.Thread(target=_play_mci, daemon=True).start()
        else:
            self.play_action()


# ==============================================================================
# FUNÇÕES UTILITÁRIAS DE SISTEMA, ÍCONE E ATALHOS
# ==============================================================================
def apply_window_icon(w, base_dir):
    """Aplica o ícone oficial multi-resolução à barra de título e tarefas."""
    icon_path = os.path.join(base_dir, "icon.ico")
    if not os.path.exists(icon_path) and getattr(sys, 'frozen', False):
        icon_path = os.path.join(getattr(sys, '_MEIPASS', ''), "icon.ico")
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


def create_shortcut(target_path, shortcut_path, icon_path=None):
    """Cria atalho nativo do Windows apontando explicitamente para o ícone."""
    working_dir = os.path.dirname(target_path)
    icon_prop = f'oLink.IconLocation = "{icon_path},0"' if icon_path and os.path.exists(icon_path) else f'oLink.IconLocation = "{target_path},0"'
    vbs_script = (
        'Set oWS = WScript.CreateObject("WScript.Shell")\n'
        f'sLinkFile = "{shortcut_path}"\n'
        'Set oLink = oWS.CreateShortcut(sLinkFile)\n'
        f'oLink.TargetPath = "{target_path}"\n'
        f'oLink.WorkingDirectory = "{working_dir}"\n'
        'oLink.Description = "PS2Manager - OPL & Library Manager"\n'
        f'{icon_prop}\n'
        'oLink.Save\n'
    )
    temp_vbs = os.path.join(os.environ.get("TEMP", "C:\\Temp"), f"shortcut_{int(time.time()*1000)}.vbs")
    try:
        with open(temp_vbs, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        subprocess.run(["cscript.exe", "//Nologo", temp_vbs], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass
    finally:
        if os.path.exists(temp_vbs):
            try:
                os.remove(temp_vbs)
            except Exception:
                pass


def register_uninstall(install_dir, version, display_icon):
    """Registra o PS2Manager no Adicionar ou Remover Programas do Windows."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PS2Manager"
        try:
            reg_key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE)
        except Exception:
            reg_key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)

        uninstaller_bat = os.path.join(install_dir, "uninstall.bat")
        winreg.SetValueEx(reg_key, "DisplayName", 0, winreg.REG_SZ, "PS2Manager")
        winreg.SetValueEx(reg_key, "DisplayVersion", 0, winreg.REG_SZ, version)
        winreg.SetValueEx(reg_key, "Publisher", 0, winreg.REG_SZ, "jujubs_4002")
        winreg.SetValueEx(reg_key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(reg_key, "DisplayIcon", 0, winreg.REG_SZ, display_icon)
        winreg.SetValueEx(reg_key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_bat}"')
        winreg.SetValueEx(reg_key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(reg_key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(reg_key)

        uninstaller_content = (
            '@echo off\n'
            'title Desinstalador PS2Manager\n'
            'color 0C\n'
            'echo ========================================================\n'
            'echo               DESINSTALADOR DO PS2MANAGER\n'
            'echo ========================================================\n'
            'echo.\n'
            'echo Tem certeza de que deseja desinstalar o PS2Manager?\n'
            'choice /C SN /M "Pressione S para SIM ou N para NAO"\n'
            'if errorlevel 2 exit\n'
            'taskkill /F /IM PS2Manager.exe >nul 2>&1\n'
            'timeout /t 1 /nobreak >nul\n'
            'reg delete "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PS2Manager" /f >nul 2>&1\n'
            'reg delete "HKLM\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PS2Manager" /f >nul 2>&1\n'
            'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PS2Manager" /f >nul 2>&1\n'
            'del /f /q "%PUBLIC%\\Desktop\\PS2Manager.lnk" >nul 2>&1\n'
            'del /f /q "%USERPROFILE%\\Desktop\\PS2Manager.lnk" >nul 2>&1\n'
            'rmdir /s /q "%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\PS2Manager" >nul 2>&1\n'
            'echo PS2Manager foi desinstalado com sucesso!\n'
            'pause\n'
            f'(goto) 2>nul & rmdir /s /q "{install_dir}"\n'
        )
        with open(uninstaller_bat, "w", encoding="utf-8") as f:
            f.write(uninstaller_content)
    except Exception:
        pass


# ==============================================================================
# CLASSE PRINCIPAL DO INSTALADOR (MODERNO, EM ETAPAS / WIZARD)
# ==============================================================================
class InstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Modo de aparência escuro elegante
        ctk.set_appearance_mode("dark")

        # Paleta de cores moderna
        self.COLORS = {
            "bg_window": "#080C16",
            "bg_sidebar": "#0D1527",
            "card": "#131C31",
            "card_sub": "#19243E",
            "border": "#203053",
            "accent": "#0099FF",
            "accent_hover": "#26A8FF",
            "text_main": "#F8FAFC",
            "text_muted": "#8EA2C6",
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444"
        }

        # Identificação de caminhos
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.audio = InstallerSoundEngine(self.base_path)
        self.lang = detect_system_language()

        # Configurações da Janela
        self.title(self.t("app_title"))
        self.geometry("820x540")
        self.resizable(False, False)
        self.configure(fg_color=self.COLORS["bg_window"])

        # Centraliza a janela
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (820 // 2)
        y = (self.winfo_screenheight() // 2) - (540 // 2)
        self.geometry(f"+{x}+{y}")

        apply_window_icon(self, self.base_path)
        self.after(100, lambda: apply_window_icon(self, self.base_path))

        # Diretório padrão
        self.install_dir = os.path.join(
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            "PS2Manager"
        )
        self.target_exe = os.path.join(self.install_dir, "PS2Manager.exe")

        # Itens do Payload
        self.payload_items = [
            {"name": "PS2Manager.exe", "is_dir": False},
            {"name": "pcsx2", "is_dir": True},
            {"name": "sounds", "is_dir": True},
            {"name": "scripts", "is_dir": True},
            {"name": "VER", "is_dir": True},
            {"name": "DO NOT DELETE DATA.JSON.txt", "is_dir": False},
            {"name": "version.txt", "is_dir": False},
            {"name": "icon.ico", "is_dir": False, "optional": True}
        ]

        # Leitura e comparação de versões
        self.new_version = self.extract_version(os.path.join(self.base_path, "version.txt"))
        self.old_version = self.extract_version(os.path.join(self.install_dir, "version.txt"))

        self.mode = "INSTALL"
        if self.old_version != "None":
            cmp = self.compare_versions(self.new_version, self.old_version)
            if cmp > 0:
                self.mode = "UPDATE"
            elif cmp < 0:
                self.mode = "DOWNGRADE"
            else:
                self.mode = "REINSTALL"

        # Variáveis de Opções
        self.var_desktop = ctk.BooleanVar(value=True)
        self.var_startmenu = ctk.BooleanVar(value=True)
        self.var_launch = ctk.BooleanVar(value=True)
        self.var_keep_data = ctk.BooleanVar(value=True)
        self.var_install_path = ctk.StringVar(value=self.install_dir)

        # Estado do Wizard (Etapa 1 a 4)
        self.current_step = 1

        # Constrói UI
        self.setup_layout()
        self.show_step(1)

        # Som suave de boas-vindas
        self.after(200, self.audio.play_welcome)

    def t(self, key):
        """Obtém o texto traduzido para o idioma ativo."""
        lang_dict = TRANSLATIONS.get(self.lang, TRANSLATIONS["PT_BR"])
        return lang_dict.get(key, TRANSLATIONS["PT_BR"].get(key, key))

    def extract_version(self, filepath):
        """Lê a versão contida em version.txt ou version_info."""
        if not os.path.exists(filepath):
            return "None"
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            match = re.search(r"StringStruct\s*\(\s*'ProductVersion'\s*,\s*'([^']+)'\s*\)", content)
            if match:
                clean = match.group(1).replace("V", "").replace("v", "")
                return f"V{clean}"
            clean = content.strip().upper()
            if 0 < len(clean) < 15:
                if not clean.startswith("V"):
                    clean = "V" + clean
                return clean
            return "V1.07"
        except Exception:
            return "V1.07"

    def compare_versions(self, v1, v2):
        if v1 == "None" or v2 == "None":
            return 0
        p1 = [int(n) for n in re.findall(r"\d+", v1)] + [0, 0, 0]
        p2 = [int(n) for n in re.findall(r"\d+", v2)] + [0, 0, 0]
        if p1[:3] > p2[:3]:
            return 1
        if p1[:3] < p2[:3]:
            return -1
        return 0

    def get_disk_free_mb(self, path):
        try:
            drive = os.path.splitdrive(os.path.abspath(path))[0]
            if not drive:
                drive = "C:"
            total, used, free = shutil.disk_usage(drive + "\\")
            return free // (1024 * 1024)
        except Exception:
            return 999999

    # ==========================================================================
    # LAYOUT GERAL E SIDEBAR
    # ==========================================================================
    def setup_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar à esquerda
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=self.COLORS["bg_sidebar"], border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Marca / Logo
        brand_frm = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frm.pack(fill="x", padx=25, pady=(35, 25))

        title_box = ctk.CTkFrame(brand_frm, fg_color="transparent")
        title_box.pack(anchor="w")

        ctk.CTkLabel(title_box, text="PS2", font=("Segoe UI Black", 32), text_color=self.COLORS["accent"]).pack(side="left")
        ctk.CTkLabel(title_box, text=" MANAGER", font=("Segoe UI Black", 20), text_color=self.COLORS["text_main"]).pack(side="left", padx=(2, 0), pady=(8, 0))

        # Chip com versão
        ver_badge = ctk.CTkFrame(brand_frm, fg_color=self.COLORS["card"], corner_radius=12, border_width=1, border_color=self.COLORS["border"])
        ver_badge.pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(ver_badge, text=f"Setup {self.new_version}", font=("Segoe UI", 11, "bold"), text_color=self.COLORS["accent"]).pack(padx=10, pady=2)

        # Divisor sutil
        ctk.CTkFrame(self.sidebar, height=1, fg_color=self.COLORS["border"]).pack(fill="x", padx=20, pady=(5, 20))

        # Indicador de Passos (Wizard Timeline)
        self.steps_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.steps_container.pack(fill="x", padx=25)

        self.step_labels = []
        step_names = [
            ("1", "wizard_step1"),
            ("2", "wizard_step2"),
            ("3", "wizard_step3"),
            ("4", "wizard_step4")
        ]

        for num, key in step_names:
            row = ctk.CTkFrame(self.steps_container, fg_color="transparent")
            row.pack(fill="x", pady=7)

            dot = ctk.CTkLabel(row, text=num, width=24, height=24, corner_radius=12,
                               fg_color=self.COLORS["card"], font=("Segoe UI", 11, "bold"),
                               text_color=self.COLORS["text_muted"])
            dot.pack(side="left", padx=(0, 10))

            lbl = ctk.CTkLabel(row, text=self.t(key), font=("Segoe UI", 12), text_color=self.COLORS["text_muted"])
            lbl.pack(side="left")

            self.step_labels.append({"dot": dot, "lbl": lbl, "key": key})

        # Rodapé da Sidebar: Botão de Mudo e Copyright
        footer_frm = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frm.pack(side="bottom", fill="x", padx=20, pady=20)

        self.btn_sound = ctk.CTkButton(
            footer_frm, text=self.t("sound_on") if self.audio.enabled else self.t("sound_off"),
            font=("Segoe UI", 11), height=28, fg_color=self.COLORS["card"],
            hover_color=self.COLORS["card_sub"], border_width=1, border_color=self.COLORS["border"],
            text_color=self.COLORS["text_main"], command=self.toggle_sound
        )
        self.btn_sound.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(footer_frm, text="© 2026 jujubs_4002\nAll Rights Reserved.", font=("Segoe UI", 9),
                     text_color=self.COLORS["text_muted"], justify="center").pack()

        # Área Principal à Direita
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=30, pady=25)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Barra Superior da Área Principal: Seletor de Idiomas
        top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        ctk.CTkLabel(top_bar, text="🌐", font=("Segoe UI", 14)).pack(side="right", padx=(0, 6))
        self.cmb_lang = ctk.CTkComboBox(
            top_bar, values=["Português (BR)", "Português (PT)", "English", "Español", "Русский", "日本語"],
            width=145, height=28, font=("Segoe UI", 11), command=self.on_language_change,
            fg_color=self.COLORS["card"], border_color=self.COLORS["border"], button_color=self.COLORS["card_sub"]
        )
        self.cmb_lang.pack(side="right")
        lang_map_rev = {"PT_BR": "Português (BR)", "PT": "Português (PT)", "EN": "English", "ES": "Español", "RU": "Русский", "JA": "日本語"}
        self.cmb_lang.set(lang_map_rev.get(self.lang, "Português (BR)"))

        # Conteúdo dinâmico das Etapas
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")

    def toggle_sound(self):
        enabled = self.audio.toggle()
        self.btn_sound.configure(text=self.t("sound_on") if enabled else self.t("sound_off"))

    def on_language_change(self, choice):
        self.audio.play_click()
        lang_map = {
            "Português (BR)": "PT_BR",
            "Português (PT)": "PT",
            "English": "EN",
            "Español": "ES",
            "Русский": "RU",
            "日本語": "JA"
        }
        self.lang = lang_map.get(choice, "PT_BR")
        self.title(self.t("app_title"))
        self.btn_sound.configure(text=self.t("sound_on") if self.audio.enabled else self.t("sound_off"))
        for s in self.step_labels:
            s["lbl"].configure(text=self.t(s["key"]))
        self.show_step(self.current_step)

    def update_sidebar_indicators(self, active_step):
        for idx, s in enumerate(self.step_labels, start=1):
            if idx == active_step:
                s["dot"].configure(fg_color=self.COLORS["accent"], text_color="#FFFFFF")
                s["lbl"].configure(text_color=self.COLORS["text_main"], font=("Segoe UI", 12, "bold"))
            elif idx < active_step:
                s["dot"].configure(fg_color=self.COLORS["success"], text_color="#FFFFFF", text="✓")
                s["lbl"].configure(text_color=self.COLORS["text_muted"], font=("Segoe UI", 12))
            else:
                s["dot"].configure(fg_color=self.COLORS["card"], text_color=self.COLORS["text_muted"], text=str(idx))
                s["lbl"].configure(text_color=self.COLORS["text_muted"], font=("Segoe UI", 12))

    # ==========================================================================
    # NAVEGAÇÃO ENTRE ETAPAS (WIZARD STEPS)
    # ==========================================================================
    def show_step(self, step_num):
        self.current_step = step_num
        self.update_sidebar_indicators(step_num)
        for w in self.content_frame.winfo_children():
            w.destroy()

        if step_num == 1:
            self.render_step_1_welcome()
        elif step_num == 2:
            self.render_step_2_options()
        elif step_num == 3:
            self.render_step_3_installing()
        elif step_num == 4:
            self.render_step_4_finished()

    # --------------------------------------------------------------------------
    # ETAPA 1: BOAS-VINDAS E DETECÇÃO DE VERSÃO
    # --------------------------------------------------------------------------
    def render_step_1_welcome(self):
        ctk.CTkLabel(self.content_frame, text=self.t("welcome_title"), font=("Segoe UI", 24, "bold"),
                     text_color=self.COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(self.content_frame, text=self.t("welcome_desc"), font=("Segoe UI", 12),
                     text_color=self.COLORS["text_muted"], wraplength=510, justify="left").pack(anchor="w", pady=(5, 18))

        # Card de Status do Sistema e Detecção
        card_status = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS["card"], corner_radius=10,
                                   border_width=1, border_color=self.COLORS["border"])
        card_status.pack(fill="x", pady=(0, 15), padx=2)

        # Header com badge de modo
        header_row = ctk.CTkFrame(card_status, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(14, 10))

        badge_txt = self.t("badge_install")
        badge_color = self.COLORS["accent"]
        if self.mode == "UPDATE":
            badge_txt = self.t("badge_update")
            badge_color = self.COLORS["success"]
        elif self.mode == "DOWNGRADE":
            badge_txt = self.t("badge_downgrade")
            badge_color = self.COLORS["warning"]
        elif self.mode == "REINSTALL":
            badge_txt = self.t("badge_reinstall")
            badge_color = "#8B5CF6"

        badge = ctk.CTkFrame(header_row, fg_color=badge_color, corner_radius=6)
        badge.pack(side="left")
        ctk.CTkLabel(badge, text=badge_txt, font=("Segoe UI", 10, "bold"), text_color="#FFFFFF").pack(padx=8, pady=3)

        # Info de Versões
        ver_row = ctk.CTkFrame(card_status, fg_color="transparent")
        ver_row.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(ver_row, text=f"{self.t('info_current')} ", font=("Segoe UI", 12), text_color=self.COLORS["text_muted"]).pack(side="left")
        old_val = self.old_version if self.old_version != "None" else self.t("info_none")
        ctk.CTkLabel(ver_row, text=old_val, font=("Consolas", 12, "bold"), text_color=self.COLORS["text_main"]).pack(side="left", padx=(0, 20))

        ctk.CTkLabel(ver_row, text=f"{self.t('info_target')} ", font=("Segoe UI", 12), text_color=self.COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(ver_row, text=self.new_version, font=("Consolas", 12, "bold"), text_color=self.COLORS["accent"]).pack(side="left")

        # Card de Novidades da Versão 1.07
        card_features = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS["card"], corner_radius=10,
                                     border_width=1, border_color=self.COLORS["border"])
        card_features.pack(fill="both", expand=True, pady=(0, 20), padx=2)

        ctk.CTkLabel(card_features, text=self.t("highlights_title"), font=("Segoe UI", 12, "bold"),
                     text_color=self.COLORS["accent"]).pack(anchor="w", padx=16, pady=(12, 8))

        features = ["feat_1", "feat_2", "feat_3", "feat_4", "feat_5"]
        for f_key in features:
            ctk.CTkLabel(card_features, text=self.t(f_key), font=("Segoe UI", 11),
                         text_color=self.COLORS["text_main"]).pack(anchor="w", padx=16, pady=2)

        # Barra de Navegação Inferior
        nav = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        nav.pack(side="bottom", fill="x")

        btn_next = ctk.CTkButton(
            nav, text=self.t("btn_next"), font=("Segoe UI", 12, "bold"), height=40, width=140,
            fg_color=self.COLORS["accent"], hover_color=self.COLORS["accent_hover"],
            command=self.on_step1_next
        )
        btn_next.pack(side="right")

    def on_step1_next(self):
        self.audio.play_click()
        if self.mode == "DOWNGRADE":
            self.audio.play_error()
            msg = self.t("warn_downgrade").format(old=self.old_version, new=self.new_version)
            if not messagebox.askyesno(self.t("badge_downgrade"), msg):
                return
        self.show_step(2)

    # --------------------------------------------------------------------------
    # ETAPA 2: DESTINO, ESPAÇO EM DISCO E OPÇÕES
    # --------------------------------------------------------------------------
    def render_step_2_options(self):
        ctk.CTkLabel(self.content_frame, text=self.t("opt_title"), font=("Segoe UI", 22, "bold"),
                     text_color=self.COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(self.content_frame, text=self.t("opt_desc"), font=("Segoe UI", 12),
                     text_color=self.COLORS["text_muted"]).pack(anchor="w", pady=(4, 15))

        # Card de Seleção de Pasta
        card_dest = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS["card"], corner_radius=10,
                                 border_width=1, border_color=self.COLORS["border"])
        card_dest.pack(fill="x", pady=(0, 15), padx=2)

        ctk.CTkLabel(card_dest, text=self.t("dest_label"), font=("Segoe UI", 11, "bold"),
                     text_color=self.COLORS["accent"]).pack(anchor="w", padx=16, pady=(12, 6))

        path_row = ctk.CTkFrame(card_dest, fg_color="transparent")
        path_row.pack(fill="x", padx=16, pady=(0, 10))

        self.ent_path = ctk.CTkEntry(
            path_row, textvariable=self.var_install_path, font=("Consolas", 11), height=36,
            fg_color=self.COLORS["bg_window"], border_color=self.COLORS["border"], text_color=self.COLORS["text_main"]
        )
        self.ent_path.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(
            path_row, text=self.t("browse"), font=("Segoe UI", 11, "bold"), width=95, height=36,
            fg_color=self.COLORS["card_sub"], hover_color=self.COLORS["border"], command=self.on_browse_path
        )
        btn_browse.pack(side="right")

        # Info de Espaço em Disco
        space_row = ctk.CTkFrame(card_dest, fg_color="transparent")
        space_row.pack(fill="x", padx=16, pady=(0, 12))

        free_mb = self.get_disk_free_mb(self.var_install_path.get())
        free_gb = free_mb / 1024.0

        ctk.CTkLabel(space_row, text=f"{self.t('space_req')} ~185 MB", font=("Segoe UI", 11),
                     text_color=self.COLORS["text_muted"]).pack(side="left", padx=(0, 20))
        self.lbl_space_free = ctk.CTkLabel(
            space_row, text=f"{self.t('space_free')} {free_gb:.1f} GB", font=("Segoe UI", 11, "bold"),
            text_color=self.COLORS["success"] if free_mb > 300 else self.COLORS["danger"]
        )
        self.lbl_space_free.pack(side="left")

        # Card de Opções (Atalhos e Preferências)
        card_opts = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS["card"], corner_radius=10,
                                 border_width=1, border_color=self.COLORS["border"])
        card_opts.pack(fill="both", expand=True, pady=(0, 20), padx=2)

        options = [
            (self.var_desktop, "chk_desktop"),
            (self.var_startmenu, "chk_start"),
            (self.var_launch, "chk_launch"),
            (self.var_keep_data, "chk_keep_data")
        ]

        for var, key in options:
            chk = ctk.CTkCheckBox(
                card_opts, text=self.t(key), variable=var, font=("Segoe UI", 12),
                fg_color=self.COLORS["accent"], hover_color=self.COLORS["accent_hover"],
                border_color=self.COLORS["border"], command=self.audio.play_click
            )
            chk.pack(anchor="w", padx=18, pady=8)

        # Barra de Navegação Inferior
        nav = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        nav.pack(side="bottom", fill="x")

        btn_back = ctk.CTkButton(
            nav, text=self.t("btn_back"), font=("Segoe UI", 12), height=40, width=110,
            fg_color=self.COLORS["card"], hover_color=self.COLORS["card_sub"],
            border_width=1, border_color=self.COLORS["border"], command=lambda: (self.audio.play_click(), self.show_step(1))
        )
        btn_back.pack(side="left")

        btn_action_txt = self.t("btn_install")
        btn_action_color = self.COLORS["accent"]
        if self.mode == "UPDATE":
            btn_action_txt = self.t("btn_update")
            btn_action_color = self.COLORS["success"]
        elif self.mode == "DOWNGRADE":
            btn_action_txt = self.t("btn_downgrade")
            btn_action_color = self.COLORS["warning"]
        elif self.mode == "REINSTALL":
            btn_action_txt = self.t("btn_reinstall")
            btn_action_color = "#8B5CF6"

        btn_start = ctk.CTkButton(
            nav, text=btn_action_txt, font=("Segoe UI", 12, "bold"), height=40, width=180,
            fg_color=btn_action_color, hover_color=self.COLORS["accent_hover"],
            command=self.on_start_install_click
        )
        btn_start.pack(side="right")

    def on_browse_path(self):
        self.audio.play_click()
        chosen = filedialog.askdirectory(initialdir=self.var_install_path.get(), title=self.t("select_folder"))
        if chosen:
            self.var_install_path.set(chosen)
            free_mb = self.get_disk_free_mb(chosen)
            free_gb = free_mb / 1024.0
            self.lbl_space_free.configure(
                text=f"{self.t('space_free')} {free_gb:.1f} GB",
                text_color=self.COLORS["success"] if free_mb > 300 else self.COLORS["danger"]
            )

    def on_start_install_click(self):
        chosen_path = self.var_install_path.get().strip()
        if not chosen_path:
            self.audio.play_error()
            return

        free_mb = self.get_disk_free_mb(chosen_path)
        if free_mb < 200:
            self.audio.play_error()
            msg = self.t("warn_space").format(req=185, free=free_mb)
            messagebox.showerror(self.t("err_title"), msg)
            return

        self.install_dir = chosen_path
        self.target_exe = os.path.join(self.install_dir, "PS2Manager.exe")
        self.audio.play_action()
        self.show_step(3)

    # --------------------------------------------------------------------------
    # ETAPA 3: INSTALAÇÃO E EXTRAÇÃO EM TEMPO REAL
    # --------------------------------------------------------------------------
    def render_step_3_installing(self):
        ctk.CTkLabel(self.content_frame, text=self.t("installing_title"), font=("Segoe UI", 22, "bold"),
                     text_color=self.COLORS["text_main"]).pack(anchor="w")
        ctk.CTkLabel(self.content_frame, text=self.t("installing_desc"), font=("Segoe UI", 12),
                     text_color=self.COLORS["text_muted"]).pack(anchor="w", pady=(4, 20))

        # Card de Progresso Principal
        prog_card = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS["card"], corner_radius=10,
                                 border_width=1, border_color=self.COLORS["border"])
        prog_card.pack(fill="x", pady=(0, 15), padx=2)

        top_row = ctk.CTkFrame(prog_card, fg_color="transparent")
        top_row.pack(fill="x", padx=18, pady=(16, 6))

        self.lbl_step_status = ctk.CTkLabel(top_row, text=self.t("status_ready"), font=("Segoe UI", 12, "bold"),
                                            text_color=self.COLORS["text_main"])
        self.lbl_step_status.pack(side="left")

        self.lbl_percent = ctk.CTkLabel(top_row, text="0%", font=("Segoe UI Black", 16),
                                        text_color=self.COLORS["accent"])
        self.lbl_percent.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(
            prog_card, height=10, corner_radius=5, fg_color=self.COLORS["bg_window"],
            progress_color=self.COLORS["accent"]
        )
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 14))
        self.progress_bar.set(0)

        # Contador de bytes / detalhes
        self.lbl_byte_counter = ctk.CTkLabel(prog_card, text="", font=("Consolas", 10), text_color=self.COLORS["text_muted"])
        self.lbl_byte_counter.pack(anchor="w", padx=18, pady=(0, 12))

        # Log Terminal de Extração em Tempo Real
        ctk.CTkLabel(self.content_frame, text="Log de Operações:", font=("Segoe UI", 11, "bold"),
                     text_color=self.COLORS["text_muted"]).pack(anchor="w", pady=(5, 4))

        self.txt_log = ctk.CTkTextbox(
            self.content_frame, font=("Consolas", 10), fg_color=self.COLORS["bg_window"],
            text_color=self.COLORS["text_muted"], border_width=1, border_color=self.COLORS["border"],
            corner_radius=8
        )
        self.txt_log.pack(fill="both", expand=True, pady=(0, 10))

        # Inicia a thread de instalação
        threading.Thread(target=self.run_installation_thread, daemon=True).start()

    def update_install_progress(self, text, prog, byte_info=""):
        def _apply():
            self.lbl_step_status.configure(text=text)
            self.lbl_percent.configure(text=f"{int(prog * 100)}%")
            self.progress_bar.set(min(max(prog, 0.0), 1.0))
            if byte_info:
                self.lbl_byte_counter.configure(text=byte_info)
            self.txt_log.insert("end", f"> {text}\n")
            self.txt_log.see("end")
        self.after(0, _apply)

    # --------------------------------------------------------------------------
    # MOTOR DE EXTRAÇÃO E INSTALAÇÃO (THREAD WORKER)
    # --------------------------------------------------------------------------
    def run_installation_thread(self):
        try:
            self.update_install_progress(self.t("status_closing"), 0.02)
            try:
                subprocess.run(["taskkill", "/F", "/IM", "PS2Manager.exe"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass
            time.sleep(0.4)

            # Limpeza prévia
            if os.path.exists(self.install_dir):
                self.update_install_progress(self.t("status_clean"), 0.05)
                shutil.rmtree(self.install_dir, ignore_errors=True)
                time.sleep(0.3)

            os.makedirs(self.install_dir, exist_ok=True)
            self.update_install_progress(self.t("status_calc"), 0.08)

            total_size = 0
            valid_payloads = []
            for item in self.payload_items:
                src = os.path.join(self.base_path, item["name"])
                if os.path.exists(src):
                    valid_payloads.append(item)
                    if item["is_dir"]:
                        for r, d, f in os.walk(src):
                            for file in f:
                                total_size += os.path.getsize(os.path.join(r, file))
                    else:
                        total_size += os.path.getsize(src)

            # Se não houver PS2Manager.exe compilado ainda e não for frozen, criamos placeholder para teste
            if not getattr(sys, 'frozen', False) and not any(it['name'] == 'PS2Manager.exe' and os.path.exists(os.path.join(self.base_path, 'PS2Manager.exe')) for it in valid_payloads):
                src_script = os.path.join(self.base_path, "ps2manager.py")
                if os.path.exists(src_script):
                    total_size += os.path.getsize(src_script)

            if total_size == 0:
                total_size = 1

            copied_size = 0
            total_mb = total_size / (1024 * 1024)

            # Extração dos Arquivos
            for item in valid_payloads:
                src = os.path.join(self.base_path, item["name"])
                dst = os.path.join(self.install_dir, item["name"])

                if item["is_dir"]:
                    os.makedirs(dst, exist_ok=True)
                    for r, d, f in os.walk(src):
                        for file in f:
                            src_file = os.path.join(r, file)
                            rel_path = os.path.relpath(r, src)
                            target_dir = os.path.join(dst, rel_path)
                            os.makedirs(target_dir, exist_ok=True)
                            dst_file = os.path.join(target_dir, file)

                            with open(src_file, "rb") as fs, open(dst_file, "wb") as fd:
                                while True:
                                    buf = fs.read(1024 * 1024)
                                    if not buf:
                                        break
                                    fd.write(buf)
                                    copied_size += len(buf)
                                    prog = 0.08 + (copied_size / total_size) * 0.78
                                    cur_mb = copied_size / (1024 * 1024)
                                    self.update_install_progress(
                                        f"{self.t('status_extracting')}: {item['name']}/{file}",
                                        prog, f"{cur_mb:.1f} MB / {total_mb:.1f} MB"
                                    )
                else:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(src, "rb") as fs, open(dst, "wb") as fd:
                        while True:
                            buf = fs.read(1024 * 1024)
                            if not buf:
                                break
                            fd.write(buf)
                            copied_size += len(buf)
                            prog = 0.08 + (copied_size / total_size) * 0.78
                            cur_mb = copied_size / (1024 * 1024)
                            self.update_install_progress(
                                f"{self.t('status_extracting')}: {item['name']}",
                                prog, f"{cur_mb:.1f} MB / {total_mb:.1f} MB"
                            )

            # Cópia do ícone garantida para shortcuts
            icon_src = os.path.join(self.base_path, "icon.ico")
            icon_dst = os.path.join(self.install_dir, "icon.ico")
            if os.path.exists(icon_src) and not os.path.exists(icon_dst):
                try:
                    shutil.copy2(icon_src, icon_dst)
                except Exception:
                    pass

            # Atualiza AppData se solicitado
            if self.var_keep_data.get():
                self.update_install_progress(self.t("status_appdata"), 0.88)
                self.patch_appdata_ps2mg()
                time.sleep(0.3)

            # Criação de Atalhos
            self.update_install_progress(self.t("status_shortcuts"), 0.93)
            icon_for_shortcut = icon_dst if os.path.exists(icon_dst) else self.target_exe

            if self.var_desktop.get():
                desktop = os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")
                if not os.path.exists(desktop):
                    desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop")
                create_shortcut(self.target_exe, os.path.join(desktop, "PS2Manager.lnk"), icon_for_shortcut)

            if self.var_startmenu.get():
                start_menu = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"),
                                          "Microsoft", "Windows", "Start Menu", "Programs", "PS2Manager")
                os.makedirs(start_menu, exist_ok=True)
                create_shortcut(self.target_exe, os.path.join(start_menu, "PS2Manager.lnk"), icon_for_shortcut)

            # Registro no Windows
            self.update_install_progress(self.t("status_registry"), 0.97)
            register_uninstall(self.install_dir, self.new_version, icon_for_shortcut)
            time.sleep(0.4)

            self.update_install_progress(self.t("status_success"), 1.0)
            self.audio.play_success()
            time.sleep(0.6)
            self.after(0, lambda: self.show_step(4))

        except Exception as e:
            self.audio.play_error()
            self.update_install_progress(f"ERRO: {str(e)}", 1.0)
            self.after(0, lambda: messagebox.showerror(self.t("err_title"), str(e)))

    def patch_appdata_ps2mg(self):
        """Atualiza a versão e a assinatura do userdata.ps2mg no AppData."""
        app_data_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PS2Manager")
        ps2mg_path = os.path.join(app_data_dir, "userdata.ps2mg")
        if not os.path.exists(ps2mg_path):
            return
        salt = b"ps2mg_master_key_2026_x!z"
        try:
            with zipfile.ZipFile(ps2mg_path, "r") as zf:
                json_data = zf.read("data.json")
            payload = json_data + self.new_version.encode("utf-8")
            checksum = hashlib.sha256(payload).hexdigest()
            signature = hashlib.sha256(payload + salt).hexdigest()
            temp_path = ps2mg_path + ".tmp"
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("data.json", json_data)
                zf.writestr("checksum.sha256", checksum)
                zf.writestr("signature.sig", signature)
                zf.writestr("version.txt", self.new_version)
            os.replace(temp_path, ps2mg_path)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # ETAPA 4: CONCLUÍDO COM SUCESSO
    # --------------------------------------------------------------------------
    def render_step_4_finished(self):
        # Card de Sucesso com Badge Grande
        card_done = ctk.CTkFrame(self.content_frame, fg_color=self.COLORS["card"], corner_radius=12,
                                 border_width=1, border_color=self.COLORS["border"])
        card_done.pack(fill="both", expand=True, pady=(10, 20), padx=2)

        # Ícone de Sucesso estilizado
        icon_badge = ctk.CTkLabel(
            card_done, text="✔", font=("Segoe UI Black", 44), width=80, height=80,
            corner_radius=40, fg_color=self.COLORS["success"], text_color="#FFFFFF"
        )
        icon_badge.pack(pady=(30, 15))

        ctk.CTkLabel(card_done, text=self.t("finish_title"), font=("Segoe UI", 22, "bold"),
                     text_color=self.COLORS["text_main"]).pack()
        ctk.CTkLabel(card_done, text=self.t("finish_desc"), font=("Segoe UI", 12),
                     text_color=self.COLORS["text_muted"], wraplength=480, justify="center").pack(pady=(6, 20))

        # Resumo da Instalação
        summary_frm = ctk.CTkFrame(card_done, fg_color=self.COLORS["card_sub"], corner_radius=8)
        summary_frm.pack(fill="x", padx=30, pady=(0, 20))

        row1 = ctk.CTkFrame(summary_frm, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(row1, text=f"{self.t('finish_path')} ", font=("Segoe UI", 11), text_color=self.COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(row1, text=self.install_dir, font=("Consolas", 11, "bold"), text_color=self.COLORS["text_main"]).pack(side="left")

        row2 = ctk.CTkFrame(summary_frm, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(row2, text=f"{self.t('finish_ver')} ", font=("Segoe UI", 11), text_color=self.COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(row2, text=self.new_version, font=("Consolas", 11, "bold"), text_color=self.COLORS["accent"]).pack(side="left")

        # Checkbox: Iniciar agora
        chk_launch_final = ctk.CTkCheckBox(
            card_done, text=self.t("chk_launch"), variable=self.var_launch, font=("Segoe UI", 12, "bold"),
            fg_color=self.COLORS["accent"], hover_color=self.COLORS["accent_hover"],
            border_color=self.COLORS["border"], command=self.audio.play_click
        )
        chk_launch_final.pack(pady=(0, 10))

        # Botão Concluir
        nav = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        nav.pack(side="bottom", fill="x")

        btn_finish = ctk.CTkButton(
            nav, text=self.t("btn_finish"), font=("Segoe UI", 13, "bold"), height=42, width=160,
            fg_color=self.COLORS["success"], hover_color="#059669",
            command=self.on_finish_click
        )
        btn_finish.pack(side="right")

    def on_finish_click(self):
        self.audio.play_click()
        if self.var_launch.get() and os.path.exists(self.target_exe):
            try:
                subprocess.Popen([self.target_exe], cwd=self.install_dir)
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
