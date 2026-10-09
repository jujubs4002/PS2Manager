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
from tkinter import messagebox

try:
    import winsound
    SOUND_SUPPORT = True
except ImportError:
    SOUND_SUPPORT = False


def is_admin():
    """Verifica se o processo atual possui privilégios de Administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# Reinicia pedindo Admin caso não tenha
if not is_admin():
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}" {params}', None, 1)
    sys.exit(0)


ctk.set_appearance_mode("dark")

COLORS = {
    "bg_window": "#060B14",
    "bg_sidebar": "#0A101D",
    "card": "#121A2F",
    "accent": "#0ea5e9",
    "accent_hover": "#0284c7",
    "text_main": "#f8fafc",
    "text_muted": "#64748b",
    "border": "#1e293b",
    "success": "#10b981",
    "danger": "#ef4444",
    "warning": "#f59e0b"
}


def play_beep(freq, duration):
    if SOUND_SUPPORT:
        threading.Thread(
            target=lambda: winsound.Beep(freq, duration),
            daemon=True
        ).start()


def create_shortcut(target_path, shortcut_path):
    working_dir = os.path.dirname(target_path)

    vbs_script = f'''
    Set oWS = WScript.CreateObject("WScript.Shell")
    sLinkFile = "{shortcut_path}"
    Set oLink = oWS.CreateShortcut(sLinkFile)
    oLink.TargetPath = "{target_path}"
    oLink.WorkingDirectory = "{working_dir}"
    oLink.Description = "PS2Manager - OPL & Library Manager"
    oLink.Save
    '''

    temp_vbs = os.path.join(
        os.environ.get("TEMP", "C:\\Temp"),
        f"shortcut_{int(time.time()*1000)}.vbs"
    )

    try:
        with open(temp_vbs, "w", encoding="utf-8") as f:
            f.write(vbs_script)

        subprocess.run(
            ["cscript.exe", "//Nologo", temp_vbs],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    finally:
        if os.path.exists(temp_vbs):
            os.remove(temp_vbs)


class InstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PS2Manager - Professional Setup")
        self.geometry("750x500")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_window"])

        self.update_idletasks()

        x = (self.winfo_screenwidth() // 2) - (750 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)

        self.geometry(f"+{x}+{y}")

        # Identifica de onde os arquivos estao vindo
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.install_dir = os.path.join(
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            "PS2Manager"
        )

        self.target_exe = os.path.join(
            self.install_dir,
            "PS2Manager.exe"
        )

        self.payload_items = [
            {"name": "PS2Manager.exe", "is_dir": False},
            {"name": "pcsx2", "is_dir": True},
            {"name": "sounds", "is_dir": True},
            {"name": "scripts", "is_dir": True},
            {"name": "VER", "is_dir": True},
            {"name": "DO NOT DELETE DATA.JSON.txt", "is_dir": False},
            {"name": "version.txt", "is_dir": False}
        ]

        # 1. Le a versao do PS2Manager embutida no instalador
        self.new_version = self.extract_version(
            os.path.join(self.base_path, "version.txt")
        )

        # 2. Le a versao ja instalada
        self.old_version = self.extract_version(
            os.path.join(self.install_dir, "version.txt")
        )

        # Define o modo apenas para a interface
        self.mode = "INSTALL"

        if self.old_version != "None":
            cmp = self.compare_versions(
                self.new_version,
                self.old_version
            )

            if cmp > 0:
                self.mode = "UPDATE"
            elif cmp < 0:
                self.mode = "DOWNGRADE"
            else:
                self.mode = "REINSTALL"

        self.setup_ui()

        play_beep(1200, 80)
        time.sleep(0.05)
        play_beep(1600, 100)

    def extract_version(self, filepath):
        """Puxa a versao de dentro do version.txt."""
        if not os.path.exists(filepath):
            return "None"

        try:
            with open(
                filepath,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:
                content = f.read()

            match = re.search(
                r"StringStruct\s*\(\s*'ProductVersion'\s*,\s*'([^']+)'\s*\)",
                content
            )

            if match:
                clean = match.group(1).replace("V", "").replace("v", "")
                return f"V{clean}"

            clean = content.strip().upper()

            if len(clean) > 0 and len(clean) < 15:
                if not clean.startswith("V"):
                    clean = "V" + clean
                return clean

            return "V1.0.0"

        except:
            return "V1.0.0"

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

    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color=COLORS["bg_sidebar"],
            border_width=0
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.sidebar.grid_rowconfigure(2, weight=1)

        brand_frm = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )

        brand_frm.pack(
            pady=(50, 0),
            padx=30,
            anchor="w",
            fill="x"
        )

        ctk.CTkLabel(
            brand_frm,
            text="PS2",
            font=("Segoe UI Black", 48),
            text_color=COLORS["accent"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_frm,
            text="MANAGER",
            font=("Segoe UI Black", 20),
            text_color=COLORS["text_main"]
        ).pack(
            anchor="w",
            pady=(0, 5)
        )

        ctk.CTkFrame(
            brand_frm,
            height=2,
            fg_color=COLORS["accent"]
        ).pack(
            fill="x",
            pady=(10, 15)
        )

        ctk.CTkLabel(
            brand_frm,
            text=f"Installer Package\nPS2Manager {self.new_version}",
            font=("Segoe UI", 12),
            text_color=COLORS["text_muted"],
            justify="left"
        ).pack(anchor="w")

        ctk.CTkLabel(
            self.sidebar,
            text="© 2026 jujubs_4002\nAll Rights Reserved.",
            font=("Segoe UI", 10),
            text_color=COLORS["text_muted"],
            justify="left"
        ).pack(
            side="bottom",
            pady=30,
            padx=30,
            anchor="w"
        )

        self.main_area = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.main_area.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=40,
            pady=40
        )

        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(3, weight=1)

        title_text = "System Installation"
        desc_text = "Configure your installation preferences below."

        if self.mode == "UPDATE":
            title_text = "System Update Available"
            desc_text = "A newer version of PS2Manager will be installed."

        elif self.mode == "DOWNGRADE":
            title_text = "System Rollback (Downgrade)"
            desc_text = "You are installing an older version of PS2Manager."

        elif self.mode == "REINSTALL":
            title_text = "System Reinstallation"
            desc_text = "Reinstalling the current version of PS2Manager."

        ctk.CTkLabel(
            self.main_area,
            text=title_text,
            font=("Segoe UI", 24, "bold"),
            text_color=COLORS["text_main"]
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ctk.CTkLabel(
            self.main_area,
            text=desc_text,
            font=("Segoe UI", 13),
            text_color=COLORS["text_muted"]
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(5, 20)
        )

        self.card_dest = ctk.CTkFrame(
            self.main_area,
            fg_color=COLORS["card"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"]
        )

        self.card_dest.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 25)
        )

        ctk.CTkLabel(
            self.card_dest,
            text="VERSION INFORMATION",
            font=("Segoe UI", 10, "bold"),
            text_color=COLORS["accent"]
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=20,
            pady=(15, 10)
        )

        ver_text_color = (
            COLORS["text_muted"]
            if self.old_version == "None"
            else COLORS["text_main"]
        )

        ctk.CTkLabel(
            self.card_dest,
            text="Currently Installed:",
            font=("Segoe UI", 12)
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 5)
        )

        ctk.CTkLabel(
            self.card_dest,
            text=self.old_version
            if self.old_version != "None"
            else "Not Installed",
            font=("Consolas", 12, "bold"),
            text_color=ver_text_color
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=10,
            pady=(0, 5)
        )

        new_color = (
            COLORS["success"]
            if self.mode == "UPDATE"
            else (
                COLORS["warning"]
                if self.mode == "DOWNGRADE"
                else COLORS["accent"]
            )
        )

        ctk.CTkLabel(
            self.card_dest,
            text="Target Version:",
            font=("Segoe UI", 12)
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 15)
        )

        ctk.CTkLabel(
            self.card_dest,
            text=self.new_version,
            font=("Consolas", 12, "bold"),
            text_color=new_color
        ).grid(
            row=2,
            column=1,
            sticky="w",
            padx=10,
            pady=(0, 15)
        )

        opt_frm = ctk.CTkFrame(
            self.main_area,
            fg_color="transparent"
        )

        opt_frm.grid(
            row=3,
            column=0,
            sticky="nw"
        )

        self.var_desktop = ctk.BooleanVar(value=True)

        self.chk_desktop = ctk.CTkCheckBox(
            opt_frm,
            text="Create Desktop shortcut",
            variable=self.var_desktop,
            font=("Segoe UI", 13),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"]
        )

        self.chk_desktop.pack(
            anchor="w",
            pady=8
        )

        self.var_startmenu = ctk.BooleanVar(value=True)

        self.chk_startmenu = ctk.CTkCheckBox(
            opt_frm,
            text="Create Start Menu folder",
            variable=self.var_startmenu,
            font=("Segoe UI", 13),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"]
        )

        self.chk_startmenu.pack(
            anchor="w",
            pady=8
        )

        self.prog_frame = ctk.CTkFrame(
            self.main_area,
            fg_color="transparent"
        )

        self.prog_frame.grid(
            row=4,
            column=0,
            sticky="ew"
        )

        self.lbl_status = ctk.CTkLabel(
            self.prog_frame,
            text="Ready to process.",
            font=("Segoe UI", 11),
            text_color=COLORS["text_muted"]
        )

        self.lbl_status.pack(
            anchor="w",
            pady=(0, 8)
        )

        self.progress = ctk.CTkProgressBar(
            self.prog_frame,
            height=6,
            progress_color=COLORS["accent"],
            fg_color=COLORS["card"]
        )

        self.progress.pack(
            fill="x",
            pady=(0, 20)
        )

        self.progress.set(0)

        btn_color = COLORS["accent"]
        btn_hover = COLORS["accent_hover"]
        btn_text = "INSTALL PS2MANAGER"

        if self.mode == "UPDATE":
            btn_color = COLORS["success"]
            btn_hover = "#059669"
            btn_text = "UPDATE PS2MANAGER"

        elif self.mode == "DOWNGRADE":
            btn_color = COLORS["warning"]
            btn_hover = "#d97706"
            btn_text = "DOWNGRADE PS2MANAGER"

        self.btn_install = ctk.CTkButton(
            self.prog_frame,
            text=btn_text,
            font=("Segoe UI", 13, "bold"),
            height=45,
            fg_color=btn_color,
            hover_color=btn_hover,
            text_color="#000"
            if self.mode == "DOWNGRADE"
            else "#fff",
            command=self.start_install
        )

        self.btn_install.pack(
            fill="x"
        )

    def start_install(self):
        if self.mode == "DOWNGRADE":
            play_beep(300, 150)

            if not messagebox.askyesno(
                "Downgrade Warning",
                f"You are about to rollback PS2Manager from {self.old_version} to {self.new_version}.\n\nAre you sure you want to proceed?"
            ):
                return

        self.btn_install.configure(state="disabled")
        self.chk_desktop.configure(state="disabled")
        self.chk_startmenu.configure(state="disabled")

        threading.Thread(
            target=self.install_process,
            daemon=True
        ).start()

    def patch_appdata_ps2mg(self):
        """Atualiza a versao e o hash do arquivo de dados no AppData."""
        app_data_dir = os.path.join(
            os.environ.get(
                "APPDATA",
                os.path.expanduser("~")
            ),
            "PS2Manager"
        )

        ps2mg_path = os.path.join(
            app_data_dir,
            "userdata.ps2mg"
        )

        if not os.path.exists(ps2mg_path):
            return

        salt = b"ps2mg_master_key_2026_x!z"

        try:
            with zipfile.ZipFile(ps2mg_path, "r") as zf:
                json_data = zf.read("data.json")

            payload = json_data + self.new_version.encode("utf-8")

            checksum = hashlib.sha256(
                payload
            ).hexdigest()

            signature = hashlib.sha256(
                payload + salt
            ).hexdigest()

            temp_path = ps2mg_path + ".tmp"

            with zipfile.ZipFile(
                temp_path,
                "w",
                zipfile.ZIP_DEFLATED
            ) as zf:
                zf.writestr(
                    "data.json",
                    json_data
                )

                zf.writestr(
                    "checksum.sha256",
                    checksum
                )

                zf.writestr(
                    "signature.sig",
                    signature
                )

                zf.writestr(
                    "version.txt",
                    self.new_version
                )

            os.replace(
                temp_path,
                ps2mg_path
            )

            self.update_status(
                "AppData successfully migrated to new version...",
                0.96
            )

            time.sleep(0.5)

        except Exception:
            pass

    def install_process(self):
        try:
            self.update_status(
                "Preparing complete reinstallation...",
                0.0
            )

            time.sleep(0.5)

            # =========================================================
            # REMOVE COMPLETELY THE EXISTING PS2MANAGER INSTALLATION
            # =========================================================

            if os.path.exists(self.install_dir):
                self.update_status(
                    "Removing previous PS2Manager installation...",
                    0.05
                )

                # Tenta encerrar o PS2Manager caso esteja aberto
                try:
                    subprocess.run(
                        [
                            "taskkill",
                            "/F",
                            "/IM",
                            "PS2Manager.exe"
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except:
                    pass

                time.sleep(0.5)

                shutil.rmtree(
                    self.install_dir,
                    ignore_errors=False
                )

                # Garante que a pasta realmente foi removida
                if os.path.exists(self.install_dir):
                    raise Exception(
                        "Could not completely remove the previous PS2Manager installation."
                    )

            # Cria a pasta limpa novamente
            os.makedirs(
                self.install_dir,
                exist_ok=True
            )

            self.update_status(
                "Calculating package size...",
                0.08
            )

            time.sleep(0.5)

            total_size = 0
            valid_payloads = []

            for item in self.payload_items:
                src = os.path.join(
                    self.base_path,
                    item["name"]
                )

                if os.path.exists(src):
                    valid_payloads.append(item)

                    if item["is_dir"]:
                        for r, d, f in os.walk(src):
                            for file in f:
                                total_size += os.path.getsize(
                                    os.path.join(r, file)
                                )
                    else:
                        total_size += os.path.getsize(src)

            if not valid_payloads and getattr(
                sys,
                "frozen",
                False
            ):
                raise Exception(
                    "Installation payload is missing or corrupted."
                )

            if total_size == 0:
                total_size = 1

            copied_size = 0

            for item in valid_payloads:
                src = os.path.join(
                    self.base_path,
                    item["name"]
                )

                dst = os.path.join(
                    self.install_dir,
                    item["name"]
                )

                if item["is_dir"]:
                    os.makedirs(
                        dst,
                        exist_ok=True
                    )

                    for r, d, f in os.walk(src):
                        for file in f:
                            src_file = os.path.join(
                                r,
                                file
                            )

                            rel_path = os.path.relpath(
                                r,
                                src
                            )

                            target_dir = os.path.join(
                                dst,
                                rel_path
                            )

                            os.makedirs(
                                target_dir,
                                exist_ok=True
                            )

                            dst_file = os.path.join(
                                target_dir,
                                file
                            )

                            with open(
                                src_file,
                                "rb"
                            ) as fs, open(
                                dst_file,
                                "wb"
                            ) as fd:

                                while True:
                                    buf = fs.read(
                                        1024 * 1024
                                    )

                                    if not buf:
                                        break

                                    fd.write(buf)
                                    copied_size += len(buf)

                                    prog = (
                                        copied_size /
                                        total_size
                                    )

                                    self.update_status(
                                        f"Extracting: {item['name']}/{file}",
                                        prog
                                    )

                else:
                    os.makedirs(
                        os.path.dirname(dst),
                        exist_ok=True
                    )

                    with open(
                        src,
                        "rb"
                    ) as fs, open(
                        dst,
                        "wb"
                    ) as fd:

                        while True:
                            buf = fs.read(
                                1024 * 1024
                            )

                            if not buf:
                                break

                            fd.write(buf)
                            copied_size += len(buf)

                            prog = (
                                copied_size /
                                total_size
                            )

                            self.update_status(
                                f"Extracting: {item['name']}",
                                prog
                            )

            self.update_status(
                "Finalizing configurations...",
                0.95
            )

            time.sleep(0.5)

            # Atualiza o pacote de dados do AppData
            self.patch_appdata_ps2mg()

            if self.var_desktop.get():
                desktop = os.path.join(
                    os.environ.get(
                        "PUBLIC",
                        "C:\\Users\\Public"
                    ),
                    "Desktop"
                )

                if not os.path.exists(desktop):
                    desktop = os.path.join(
                        os.environ.get(
                            "USERPROFILE",
                            "C:\\"
                        ),
                        "Desktop"
                    )

                create_shortcut(
                    self.target_exe,
                    os.path.join(
                        desktop,
                        "PS2Manager.lnk"
                    )
                )

            if self.var_startmenu.get():
                start_menu = os.path.join(
                    os.environ.get(
                        "ProgramData",
                        "C:\\ProgramData"
                    ),
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "PS2Manager"
                )

                os.makedirs(
                    start_menu,
                    exist_ok=True
                )

                create_shortcut(
                    self.target_exe,
                    os.path.join(
                        start_menu,
                        "PS2Manager.lnk"
                    )
                )

            msg_final = (
                "Installation completed successfully!"
                if self.mode == "INSTALL"
                else f"Version applied: {self.new_version}!"
            )

            self.update_status(
                msg_final,
                1.0
            )

            self.progress.configure(
                progress_color=COLORS["success"]
            )

            self.btn_install.configure(
                state="normal",
                text="FINISH WIZARD",
                fg_color=COLORS["success"],
                hover_color="#059669",
                text_color="#fff",
                command=self.destroy
            )

            if SOUND_SUPPORT:
                winsound.Beep(1200, 80)
                winsound.Beep(1800, 120)
                winsound.Beep(2400, 150)

        except Exception as e:
            self.update_status(
                f"Error: {str(e)}",
                1.0
            )

            self.progress.configure(
                progress_color=COLORS["danger"]
            )

            self.btn_install.configure(
                state="normal",
                text="EXIT (ERROR)",
                fg_color=COLORS["danger"],
                hover_color="#b91c1c",
                text_color="#fff",
                command=self.destroy
            )

            play_beep(
                300,
                250
            )

    def update_status(self, text, prog):
        self.after(
            0,
            lambda: self.lbl_status.configure(text=text)
        )

        self.after(
            0,
            lambda: self.progress.set(
                min(
                    max(
                        prog,
                        0.0
                    ),
                    1.0
                )
            )
        )


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()