from __future__ import annotations

import os
import sys
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

from scripts.core_backend import (
    sys_logger, APP_DATA_DIR, BASE_DIR, MEIPASS_DIR, get_res_path,
    cfg, t, format_size, TransferLockManager, TransferStateManager,
    GameAnalyzer, db, sound_fx,
    LZ4_SUPPORT, PYCDLIB_SUPPORT, WIN32COM_SUPPORT, SOUND_SUPPORT, PYGAME_SUPPORT
)

if LZ4_SUPPORT:
    import lz4.block
if PYCDLIB_SUPPORT:
    import pycdlib
if WIN32COM_SUPPORT:
    import win32com.client


def _throttle_prog(cb, min_step=0.008, min_interval=0.05):
    """Evita inundar a fila de eventos do Tkinter centenas de vezes por segundo em SSDs/NVMe rapidos."""
    state = [-1.0, 0.0]

    def _wrapped(val):
        if not cb:
            return
        now = time.monotonic()
        if val >= 0.999 or val <= 0.001 or abs(val - state[0]) >= min_step or (now - state[1]) >= min_interval:
            state[0] = val
            state[1] = now
            cb(val)

    return _wrapped


class APAManager:
    _phys_cache = (0.0, [])

    @staticmethod
    def _clean_device_path(source):
        s = source.strip()
        if " " in s and s.startswith("\\\\.\\"):
            return s.split(" ")[0].strip()
        if s.upper().startswith("PHYSICALDRIVE"):
            return "\\\\.\\" + s.split(" ")[0].strip()
        return s

    @staticmethod
    def list_physical_drives():
        now = time.monotonic()
        if APAManager._phys_cache[1] and (now - APAManager._phys_cache[0]) < 5.0:
            return list(APAManager._phys_cache[1])
        drives = []
        # Leitura Win32 nativa em <1ms compatível com Windows 7 ate 11 (32-bit e 64-bit)
        if sys.platform == "win32":
            try:
                k32 = ctypes.WinDLL("kernel32", use_last_error=True)
                k32.CreateFileW.restype = ctypes.c_void_p
                k32.CreateFileW.argtypes = [
                    ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                    ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p
                ]
                k32.DeviceIoControl.restype = ctypes.c_int
                k32.DeviceIoControl.argtypes = [
                    ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
                    ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p
                ]
                k32.CloseHandle.restype = ctypes.c_int
                k32.CloseHandle.argtypes = [ctypes.c_void_p]

                for idx in range(16):
                    dev = f"\\\\.\\PhysicalDrive{idx}"
                    h = k32.CreateFileW(dev, 0, 3, None, 3, 0, None)
                    if not h or h in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
                        continue
                    try:
                        model = "Disk Drive"
                        q = ctypes.create_string_buffer(12)
                        out = ctypes.create_string_buffer(512)
                        ret = ctypes.c_ulong(0)
                        if k32.DeviceIoControl(ctypes.c_void_p(h), 0x002D1400, q, 12, out, 512, ctypes.byref(ret), None) and ret.value >= 32:
                            raw = out.raw[:ret.value]
                            v_off, p_off = struct.unpack_from("<II", raw, 12)
                            parts_m = []
                            for off in (v_off, p_off):
                                if 0 < off < len(raw):
                                    end = raw.find(b"\x00", off)
                                    s = raw[off:(end if end != -1 else len(raw))].decode("ascii", "ignore").strip()
                                    if s:
                                        parts_m.append(s)
                            if parts_m:
                                model = " ".join(parts_m)
                        sz_buf = ctypes.create_string_buffer(8)
                        if k32.DeviceIoControl(ctypes.c_void_p(h), 0x0007405C, None, 0, sz_buf, 8, ctypes.byref(ret), None) and ret.value >= 8:
                            sz_val = struct.unpack("<Q", sz_buf.raw)[0]
                            drives.append(f"{dev} ({format_size(sz_val)}) - {model}")
                        else:
                            drives.append(f"{dev} - {model}")
                    finally:
                        k32.CloseHandle(ctypes.c_void_p(h))
                if drives:
                    APAManager._phys_cache = (now, drives)
                    return list(drives)
            except Exception:
                pass
        # Fallback PowerShell compatível com Windows 7 (PowerShell 2.0 via Get-WmiObject) e Windows 8.1/10/11
        try:
            ps_cmd = 'powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-WmiObject Win32_DiskDrive | ForEach-Object { \\\"$($_.DeviceID)|$($_.Size)|$($_.Model)\\\" }"'
            res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().split('\n'):
                    parts = line.strip().split('|')
                    if len(parts) >= 3:
                        dev_id, sz, model = parts[0], parts[1], parts[2]
                        try:
                            drives.append(f"{dev_id} ({format_size(int(sz))}) - {model}")
                        except Exception:
                            drives.append(f"{dev_id} - {model}")
                if drives:
                    APAManager._phys_cache = (now, drives)
                    return drives
        except Exception:
            pass

        try:
            out = subprocess.check_output(
                'wmic diskdrive get Name, Size, Model /value',
                shell=True, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW
            ).decode(errors='ignore')
            current = {}
            for line in out.strip().split('\n'):
                line = line.strip()
                if not line:
                    if 'Name' in current and 'Size' in current and 'Model' in current:
                        try:
                            drives.append(f"{current['Name']} ({format_size(int(current['Size']))}) - {current['Model']}")
                        except Exception:
                            pass
                    current = {}
                else:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        current[parts[0]] = parts[1]
            if current and 'Name' in current and 'Size' in current:
                drives.append(f"{current['Name']} ({format_size(int(current['Size']))}) - {current.get('Model', '')}")
        except Exception:
            pass
        return drives

    @staticmethod
    def create_fake_vhd():
        desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        filepath = os.path.join(desktop, "PS2_APA_Sample.img")
        try:
            with open(filepath, 'wb') as f:
                f.truncate(512 * 1024 * 1024)

                def write_apa(offset, part_id, ptype, length_sectors=262144):
                    f.seek(offset)
                    part_id_bytes = part_id.encode('utf-8').ljust(32, b'\x00')
                    header = struct.pack('<I 4s I I 32s 8s I I', 0, b'APA\x00', length_sectors, 0, part_id_bytes, b'', 0, ptype)
                    f.write(header)

                write_apa(0, "__mbr", 0x0000)
                write_apa(134217728, "+OPL", 0x0001)
                f.seek(134217728 + 1024)
                f.write(b"DIR: ART\nDIR: APPS\nDIR: CFG\nFILE: ART/SLUS_209.46_COV.png\n")
                write_apa(268435456, "PP.HDL.God_of_War_II", 0x0100)
            return filepath
        except Exception:
            return None

    @staticmethod
    def read_apa_partitions(drive_path):
        clean_path = APAManager._clean_device_path(drive_path)
        partitions = []
        try:
            with open(clean_path, 'rb') as f:
                for i in range(0, 4096):
                    offset = i * 134217728
                    try:
                        f.seek(offset)
                        header = f.read(1024)
                    except IOError:
                        break
                    if not header or len(header) < 64:
                        break
                    if header[4:8] in [b'APA\x00', b'APA ', b'APA\x01']:
                        part_id = header[16:48].decode('utf-8', 'ignore').strip('\x00')
                        part_type = struct.unpack('<I', header[60:64])[0]
                        length_sectors = 0
                        try:
                            length_sectors = struct.unpack('<I', header[8:12])[0]
                        except Exception:
                            pass
                        real_size_bytes = (length_sectors * 512) if length_sectors > 0 else (134217728)
                        partitions.append({
                            "id": part_id,
                            "name": part_id,
                            "offset": offset,
                            "start": offset // 512,
                            "type": part_type,
                            "size_bytes": real_size_bytes,
                            "size_str": format_size(real_size_bytes),
                            "is_game": part_id.startswith("PP.HDL.")
                        })
        except Exception:
            pass
        return partitions

    read_apa_header = read_apa_partitions

    @staticmethod
    def get_raw_size(source):
        clean_src = APAManager._clean_device_path(source)
        if clean_src.startswith("\\\\.\\"):
            if sys.platform == "win32":
                try:
                    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
                    k32.CreateFileW.restype = ctypes.c_void_p
                    k32.CreateFileW.argtypes = [
                        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p
                    ]
                    k32.DeviceIoControl.restype = ctypes.c_int
                    k32.DeviceIoControl.argtypes = [
                        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
                        ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p
                    ]
                    k32.CloseHandle.restype = ctypes.c_int
                    k32.CloseHandle.argtypes = [ctypes.c_void_p]
                    h = k32.CreateFileW(clean_src, 0, 3, None, 3, 0, None)
                    if h and h not in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
                        try:
                            ret = ctypes.c_ulong(0)
                            sz_buf = ctypes.create_string_buffer(8)
                            if k32.DeviceIoControl(ctypes.c_void_p(h), 0x0007405C, None, 0, sz_buf, 8, ctypes.byref(ret), None) and ret.value >= 8:
                                sz_val = struct.unpack("<Q", sz_buf.raw)[0]
                                if sz_val > 0:
                                    return int(sz_val)
                        finally:
                            k32.CloseHandle(ctypes.c_void_p(h))
                except Exception:
                    pass
            try:
                ps_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-WmiObject Win32_DiskDrive | Where-Object {{ $_.DeviceID -eq \'{clean_src}\' }}).Size"'
                res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if res.returncode == 0 and res.stdout.strip().isdigit():
                    return int(res.stdout.strip())
            except Exception:
                pass
            return 80 * 1024 * 1024 * 1024
        return os.path.getsize(clean_src) if os.path.exists(clean_src) else 0

    @staticmethod
    def backup_raw(source, dest, cb_prog, cb_done, cb_err):
        def run():
            clean_src = APAManager._clean_device_path(source)
            TransferLockManager.acquire("Backup APA Raw")
            try:
                if clean_src.startswith("\\\\.\\"):
                    try:
                        open(clean_src, 'rb').close()
                    except PermissionError:
                        return cb_err("Permission Denied! Run PS2Manager as Administrator.")
                total_size = APAManager.get_raw_size(clean_src)
                copied = 0
                with open(clean_src, 'rb') as f_src, open(dest, 'wb') as f_dst:
                    while True:
                        buf = f_src.read(4 * 1024 * 1024)
                        if not buf:
                            break
                        f_dst.write(buf)
                        copied += len(buf)
                        if total_size > 0:
                            cb_prog(min(copied / total_size, 1.0))
                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def extract_contents(source, dest_folder, cb_prog, cb_done, cb_err):
        def run():
            clean_src = APAManager._clean_device_path(source)
            TransferLockManager.acquire("Extração de Jogos APA")
            try:
                if clean_src.startswith("\\\\.\\"):
                    try:
                        open(clean_src, 'rb').close()
                    except PermissionError:
                        return cb_err("Permission Denied! Run PS2Manager as Administrator.")
                cb_prog(0.05)
                parts = APAManager.read_apa_partitions(clean_src)
                if not parts:
                    return cb_err("No APA signature detected on source!")
                game_parts = [p for p in parts if p['is_game']]
                if not game_parts:
                    return cb_err("No HDL games (PP.HDL.*) found on image/drive.")
                total_games = len(game_parts)
                with open(clean_src, 'rb') as f_src:
                    for i, p in enumerate(game_parts):
                        clean_title = p['id'].replace("PP.HDL.", "")
                        out_path = os.path.join(dest_folder, f"{clean_title}.iso")
                        data_offset = p['offset'] + (4 * 1024 * 1024)
                        target_size = max(2048, p.get('size_bytes', 134217728) - (4 * 1024 * 1024))
                        f_src.seek(data_offset)
                        with open(out_path, 'wb') as f_out:
                            read_bytes = 0
                            while read_bytes < target_size:
                                buf = f_src.read(min(4 * 1024 * 1024, target_size - read_bytes))
                                if not buf:
                                    break
                                f_out.write(buf)
                                read_bytes += len(buf)
                                prog = (i / total_games) + ((read_bytes / target_size) / total_games)
                                cb_prog(min(prog, 0.99))
                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


class ArtScraperWorker:
    @staticmethod
    def format_opl_id(game_id):
        clean = game_id.replace('-', '').replace('_', '').replace('.', '').upper()
        if len(clean) == 9:
            return f"{clean[:4]}_{clean[4:7]}.{clean[7:]}"
        return game_id

    @staticmethod
    def get_repo_id(game_id):
        clean = game_id.replace('-', '').replace('_', '').replace('.', '').upper()
        if len(clean) == 9:
            return f"{clean[:4]}-{clean[4:]}"
        return game_id

    @staticmethod
    def scan_for_ids(mountpoint):
        ids = set()
        for folder in [os.path.join(mountpoint, "DVD"), os.path.join(mountpoint, "CD")]:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    if f.lower().endswith(('.iso', '.zso')):
                        game_id = GameAnalyzer.extract_game_id(os.path.join(folder, f))
                        if game_id != "Unknown":
                            ids.add(game_id)
        ul_path = os.path.join(mountpoint, "ul.cfg")
        if os.path.exists(ul_path):
            try:
                with open(ul_path, 'rb') as f:
                    while True:
                        entry = f.read(64)
                        if not entry or len(entry) < 64:
                            break
                        game_id_raw = entry[32:47].decode('ascii', 'ignore').strip('\x00')
                        if game_id_raw.startswith("ul."):
                            ids.add(game_id_raw[3:])
            except Exception:
                pass
        return sorted(ids)

    @staticmethod
    def download_single_art(mountpoint, game_id):
        try:
            art_folder = os.path.join(mountpoint, "ART")
            os.makedirs(art_folder, exist_ok=True)
            opl_id = ArtScraperWorker.format_opl_id(game_id)
            target_file = os.path.join(art_folder, f"{opl_id}_COV.jpg")
            if os.path.exists(target_file):
                return True
            url = f"https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/{ArtScraperWorker.get_repo_id(game_id)}.jpg"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as response, open(target_file, 'wb') as out_file:
                out_file.write(response.read())
            return True
        except Exception:
            return False


class BinConverter:
    @staticmethod
    def convert(bin_path, iso_path, progress_cb, done_cb, err_cb, ps1_mode=True):
        def run():
            TransferLockManager.acquire("Conversão BIN para ISO")
            try:
                total_size = os.path.getsize(bin_path)
                # Detecta modo 1 (offset 16) vs modo 2 XA/PS1/PS2 CD (offset 24) pelo cabeçalho ISO9660 CD001 no setor 16
                sector_size = 2352
                data_offset = 24 if ps1_mode else 16
                try:
                    with open(bin_path, 'rb') as probe:
                        probe.seek(16 * 2352)
                        sec16 = probe.read(64)
                        if len(sec16) >= 32:
                            if sec16[16:22] == b'\x01CD001':
                                data_offset = 16
                            elif sec16[24:30] == b'\x01CD001':
                                data_offset = 24
                except Exception:
                    pass

                data_size = 2048
                processed = 0
                with open(bin_path, 'rb') as f_in, open(iso_path, 'wb') as f_out:
                    while True:
                        sector = f_in.read(sector_size)
                        if not sector or len(sector) < data_offset + data_size:
                            break
                        f_out.write(sector[data_offset:data_offset + data_size])
                        processed += len(sector)
                        if processed % (sector_size * 2000) == 0 and total_size > 0:
                            progress_cb(min(processed / total_size, 0.99))
                progress_cb(1.0)
                done_cb(iso_path)
            except Exception as e:
                err_cb(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


class USBUtilWorker:
    @staticmethod
    def _split_sync(iso_path, dst_dir, game_name, cb_prog, cancel_flag_ref=None):
        if not os.path.exists(iso_path) or not os.path.exists(dst_dir):
            raise Exception("Invalid source or destination paths.")
        game_id = GameAnalyzer.extract_game_id(iso_path)
        if game_id == "Unknown" or len(game_id) < 8:
            clean_id = "SLUS_200.00"
        else:
            clean_id = ArtScraperWorker.format_opl_id(game_id)
        safe_name = game_name.strip()[:32]
        crc = zlib.crc32(safe_name.encode('utf-8')) & 0xFFFFFFFF
        total_size = os.path.getsize(iso_path)
        chunk_size = 1073741824  # 1 GB
        num_parts = (total_size + chunk_size - 1) // chunk_size
        media_type = 0x14 if total_size >= 700 * 1024 * 1024 else 0x12
        cb_t = _throttle_prog(cb_prog)
        with open(iso_path, 'rb') as f_in:
            for i in range(num_parts):
                if cancel_flag_ref and cancel_flag_ref():
                    raise Exception("Operation cancelled by user.")
                part_path = os.path.join(dst_dir, f"ul.{crc:08X}.{clean_id}.{i:02d}")
                with open(part_path, 'wb') as f_out:
                    bytes_to_write = min(chunk_size, total_size - (i * chunk_size))
                    written = 0
                    while written < bytes_to_write:
                        if cancel_flag_ref and cancel_flag_ref():
                            raise Exception("Operation cancelled by user.")
                        buf = f_in.read(min(4 * 1024 * 1024, bytes_to_write - written))
                        if not buf:
                            break
                        f_out.write(buf)
                        written += len(buf)
                        if total_size > 0:
                            cb_t((i * chunk_size + written) / total_size)
        cfg_path = os.path.join(dst_dir, "ul.cfg")
        entry = struct.pack(
            '<32s 15s B B 15x',
            safe_name.encode('ascii', 'ignore'),
            f"ul.{clean_id}".encode('ascii', 'ignore'),
            num_parts,
            media_type
        )
        # Garante tamanho exato de 64 bytes da entrada ul.cfg oficial
        if len(entry) < 64:
            entry = entry.ljust(64, b'\x00')
        else:
            entry = entry[:64]
        with open(cfg_path, 'ab') as f_cfg:
            f_cfg.write(entry)

    @staticmethod
    def split_and_generate(iso_path, dst_dir, game_name, cb_prog, cb_done, cb_err, cancel_flag_ref=None):
        def run():
            TransferLockManager.acquire("Divisão USBUtil (FAT32)")
            try:
                USBUtilWorker._split_sync(iso_path, dst_dir, game_name, cb_prog, cancel_flag_ref)
                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


class RealIsoTool:
    @staticmethod
    def extract(src, dst, cb_prog, cb_done, cb_err):
        def run():
            TransferLockManager.acquire("Extração de ISO")
            try:
                os.makedirs(dst, exist_ok=True)
                abs_iso = os.path.abspath(src)

                # 1) Extração nativa via pycdlib (100% Python embutido, sem depender de ferramentas externas)
                if PYCDLIB_SUPPORT:
                    try:
                        iso = pycdlib.PyCdlib()
                        iso.open(abs_iso)
                        entries = []

                        def walk_iso(iso_dir):
                            for child in iso.list_children(iso_path=iso_dir):
                                if child is None or child.is_dot() or child.is_dotdot():
                                    continue
                                ident = child.file_identifier().decode('latin1', errors='ignore')
                                child_iso_path = (iso_dir.rstrip('/') + '/' + ident) if iso_dir != '/' else ('/' + ident)
                                clean_rel = ident.split(';')[0]
                                if child.is_dir():
                                    os.makedirs(os.path.join(dst, child_iso_path.lstrip('/').replace(';1', '')), exist_ok=True)
                                    walk_iso(child_iso_path)
                                else:
                                    rel_out = os.path.join(
                                        *[p.split(';')[0] for p in child_iso_path.lstrip('/').split('/')]
                                    ) if '/' in child_iso_path.lstrip('/') else clean_rel
                                    entries.append((child_iso_path, os.path.join(dst, rel_out)))

                        walk_iso('/')
                        total = len(entries) or 1
                        for idx, (i_path, out_file) in enumerate(entries):
                            os.makedirs(os.path.dirname(out_file), exist_ok=True)
                            with open(out_file, 'wb') as fo:
                                iso.get_file_from_iso_fp(fo, iso_path=i_path)
                            cb_prog((idx + 1) / total)
                        iso.close()
                        cb_prog(1.0)
                        return cb_done(True)
                    except Exception:
                        pass

                # 2) Fallback via 7-Zip caso seja UDF puro sem árvore ISO9660
                sz_path = r"C:\Windows\System32\7z.exe" if os.path.exists(r"C:\Windows\System32\7z.exe") else (
                    r"C:\Program Files\7-Zip\7z.exe" if os.path.exists(r"C:\Program Files\7-Zip\7z.exe") else None
                )
                if sz_path:
                    res = subprocess.run(f'"{sz_path}" x "{abs_iso}" -o"{dst}" -y', shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    if res.returncode == 0:
                        cb_prog(1.0)
                        return cb_done(True)

                # 3) Fallback nativo Windows PowerShell Mount-DiskImage
                ps_mount = f'powershell -ExecutionPolicy Bypass -Command "$img = Mount-DiskImage -ImagePath \'{abs_iso}\' -PassThru; $vol = $img | Get-Volume; if ($vol) {{ echo $vol.DriveLetter }} else {{ echo \'\' }}"'
                result = subprocess.run(ps_mount, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                drive_letter = result.stdout.strip()
                if not drive_letter:
                    raise Exception("Could not extract ISO structure.")
                source_dir = f"{drive_letter}:\\"
                files_list = []
                for r, _, files in os.walk(source_dir):
                    for file in files:
                        files_list.append(os.path.join(r, file))
                total_size = sum(os.path.getsize(f) for f in files_list) or 1
                copied = 0
                for s_path in files_list:
                    rel = os.path.relpath(s_path, source_dir)
                    d_path = os.path.join(dst, rel)
                    os.makedirs(os.path.dirname(d_path), exist_ok=True)
                    with open(s_path, 'rb') as fsrc, open(d_path, 'wb') as fdst:
                        while True:
                            buf = fsrc.read(4 * 1024 * 1024)
                            if not buf:
                                break
                            fdst.write(buf)
                            copied += len(buf)
                            cb_prog(copied / total_size)
                try:
                    subprocess.run(f'powershell -Command "Dismount-DiskImage -ImagePath \'{abs_iso}\'"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass
                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def repack(src_dir, dst_iso, cb_prog, cb_done, cb_err):
        """Reempacota uma pasta extraída para ISO9660 nível 3 compatível com PS2 e OPL."""
        def run():
            TransferLockManager.acquire("Reempacotamento de Pasta para ISO")
            try:
                if not os.path.exists(src_dir):
                    raise Exception("Source folder does not exist.")
                if not PYCDLIB_SUPPORT:
                    raise Exception("pycdlib library is not available.")
                iso = pycdlib.PyCdlib()
                iso.new(interchange_level=3, vol_ident="PS2_GAME")
                cb_prog(0.1)
                files_to_add = []
                for root, _, files in os.walk(src_dir):
                    for f in files:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, src_dir).replace('\\', '/').upper()
                        # Sanitiza caracteres para ISO9660
                        rel_parts = [re.sub(r'[^A-Z0-9_.]', '_', p) for p in rel_path.split('/')]
                        files_to_add.append((full_path, "/" + "/".join(rel_parts)))
                # Ordena colocando SYSTEM.CNF primeiro (boa prática de boot do PS2)
                files_to_add.sort(key=lambda x: (0 if x[1] == "/SYSTEM.CNF" else 1, x[1]))
                total = len(files_to_add) or 1
                added_dirs = set()
                for idx, (local_file, iso_entry) in enumerate(files_to_add):
                    iso_parts = iso_entry.strip('/').split('/')
                    current_dir = ""
                    for part in iso_parts[:-1]:
                        current_dir = (current_dir + "/" + part) if current_dir else ("/" + part)
                        if current_dir not in added_dirs:
                            try:
                                iso.add_directory(iso_path=current_dir)
                                added_dirs.add(current_dir)
                            except Exception:
                                pass
                    final_iso_name = iso_entry if ";" in iso_entry else (iso_entry + ";1")
                    iso.add_file(local_file, iso_path=final_iso_name)
                    cb_prog(0.1 + (0.55 * ((idx + 1) / total)))
                cb_prog(0.75)
                iso.write(dst_iso)
                iso.close()
                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def compress_zso(src, dst, level_str, cb_prog, cb_done, cb_err):
        def run():
            if not LZ4_SUPPORT:
                return cb_err("LZ4 Python module is absent.")
            TransferLockManager.acquire("Compressão ZSO")
            try:
                sector_size = 2048
                iso_size = os.path.getsize(src)
                total_blocks = (iso_size + sector_size - 1) // sector_size
                fast_mode = "Fast" in level_str
                with open(src, 'rb') as f_in, open(dst, 'wb') as f_out:
                    f_out.write(b'\x00' * 24)
                    f_out.write(b'\x00' * ((total_blocks + 1) * 4))
                    indices, write_pos = [], 24 + ((total_blocks + 1) * 4)
                    for i in range(total_blocks):
                        block_data = f_in.read(sector_size)
                        if not block_data:
                            break
                        if len(block_data) < sector_size:
                            block_data = block_data.ljust(sector_size, b'\x00')
                        pad = ((write_pos + 3) & ~3) - write_pos
                        if pad > 0:
                            f_out.write(b'\x00' * pad)
                            write_pos += pad
                        idx_val = write_pos >> 2
                        compressed = lz4.block.compress(
                            block_data, store_size=False,
                            mode='fast' if fast_mode else 'high_compression'
                        )
                        if len(compressed) >= len(block_data):
                            idx_val |= 0x80000000
                            f_out.write(block_data)
                            write_pos += len(block_data)
                        else:
                            f_out.write(compressed)
                            write_pos += len(compressed)
                        indices.append(idx_val)
                        if i % 1000 == 0 and total_blocks > 0:
                            cb_prog(i / total_blocks)
                    pad = ((write_pos + 3) & ~3) - write_pos
                    if pad > 0:
                        f_out.write(b'\x00' * pad)
                        write_pos += pad
                    indices.append(write_pos >> 2)
                    f_out.seek(24)
                    f_out.write(struct.pack(f'<{len(indices)}I', *indices))
                    f_out.seek(0)
                    f_out.write(struct.pack('<4s I Q I B B H', b'ZISO', 24, iso_size, sector_size, 1, 2, 0))
                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


class DriveManager:
    OPL_FOLDERS = ['DVD', 'CD', 'ART', 'CFG', 'VMC', 'CHT', 'APPS', 'THM', 'POPS']
    _drv_cache = (0.0, [])

    @staticmethod
    def get_drives(force=False):
        now = time.monotonic()
        if not force and (now - DriveManager._drv_cache[0]) < 1.2:
            return list(DriveManager._drv_cache[1])
        drives = []
        for p in psutil.disk_partitions(all=False):
            if p.fstype.lower() in ['fat32', 'exfat', 'ntfs', 'fat', 'fat16']:
                if p.device.upper().startswith('C:'):
                    continue
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    drives.append({
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype.upper(),
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "total_str": format_size(usage.total),
                        "used_str": format_size(usage.used),
                        "free_str": format_size(usage.free),
                        "percent": usage.percent
                    })
                except Exception:
                    continue
        DriveManager._drv_cache = (now, drives)
        return list(drives)

    @staticmethod
    def analyze_opl_structure(mountpoint):
        core_folders = ['DVD', 'CD', 'ART', 'CFG', 'VMC', 'CHT', 'APPS', 'POPS']
        struct_info = {d: os.path.isdir(os.path.join(mountpoint, d)) for d in core_folders}
        return {
            "folders": struct_info,
            "status": "VALID" if all(struct_info.values()) else ("PARTIAL" if any(struct_info.values()) else "EMPTY")
        }

    @staticmethod
    def create_opl_structure(mountpoint):
        created = []
        for f in DriveManager.OPL_FOLDERS:
            target = os.path.join(mountpoint, f)
            if not os.path.exists(target):
                os.makedirs(target, exist_ok=True)
                created.append(f)
        return created


class PhysicalDriveRipper:
    @staticmethod
    def get_optical_drives():
        drives = []
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                if bitmask & 1 and ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\") == 5:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
        except Exception:
            pass
        return drives

    @staticmethod
    def rip_drive(drive_letter, output_target, force_iso, cb_prog, cb_done, cb_err):
        def run():
            TransferLockManager.acquire("Ripar Disco Óptico")
            try:
                drive_path = f"\\\\.\\{drive_letter[0]}:"
                if output_target.lower().endswith(".iso"):
                    output_file = output_target
                    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                else:
                    os.makedirs(output_target, exist_ok=True)
                    output_file = os.path.join(output_target, f"PS2_DISC_{int(time.time())}.iso")
                try:
                    total_size = psutil.disk_usage(drive_letter).total
                except Exception:
                    total_size = 4 * 1024 * 1024 * 1024
                copied = 0
                with open(drive_path, 'rb') as f_in, open(output_file, 'wb') as f_out:
                    while True:
                        chunk = f_in.read(2 * 1024 * 1024)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        copied += len(chunk)
                        if total_size > 0:
                            cb_prog(min(copied / total_size, 1.0))
                cb_prog(1.0)
                cb_done(output_file)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def rip_to_iso(drive_letter, output_target, cb_prog, cb_done, cb_err):
        return PhysicalDriveRipper.rip_drive(drive_letter, output_target, True, cb_prog, cb_done, cb_err)

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
        except Exception:
            pass
        return info


class DvdBurnerWorker:
    """Gravação real de DVD com suporte a isoburn.exe e IMAPI2."""
    @staticmethod
    def list_burners():
        burners = []
        if WIN32COM_SUPPORT:
            try:
                disc_master = win32com.client.Dispatch("IMAPI2.MsftDiscMaster2")
                for i in range(disc_master.Count):
                    rec_id = disc_master.Item(i)
                    rec = win32com.client.Dispatch("IMAPI2.MsftDiscRecorder2")
                    rec.InitializeDiscRecorder(rec_id)
                    mps = rec.VolumeMountPoints
                    mp_str = mps[0] if len(mps) > 0 else f"Drive_{i}"
                    name = f"{rec.VendorId.strip()} {rec.ProductId.strip()}".strip()
                    burners.append({"id": mp_str, "mount": mp_str, "name": f"{mp_str} ({name or 'DVD-RW'})"})
            except Exception:
                pass
        if not burners:
            for d in PhysicalDriveRipper.get_optical_drives():
                burners.append({"id": d, "mount": d, "name": f"{d} (Optical Drive)"})
        return burners

    @staticmethod
    def burn(iso_path, drive_id, speed_str, cb_prog, cb_done, cb_err):
        def run():
            TransferLockManager.acquire(t("tab_burn"))
            try:
                if not os.path.exists(iso_path):
                    raise Exception(t("burn_err_select_iso"))
                drive_letter = drive_id[0] if drive_id else ""
                if not drive_letter or not os.path.exists(f"{drive_letter}:\\"):
                    raise Exception(t("burn_err_nomedia"))

                cb_prog(0.1)
                cmd = ["isoburn.exe", "/Q", f"{drive_letter}:", os.path.abspath(iso_path)]
                proc = subprocess.Popen(cmd)
                proc.wait()
                if proc.returncode == 0:
                    cb_prog(1.0)
                    cb_done(True)
                else:
                    raise Exception(t("burn_err_title"))
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


class SingleInstallWorker:
    """Instalador 1-Clique real: detecta CD/DVD, FAT32 vs exFAT, divide se > 4GB e baixa capa."""
    @staticmethod
    def install(iso_path, target_drive, game_name, auto_cover, cb_prog, cb_done, cb_err):
        def run():
            TransferLockManager.acquire("Instalação de Jogo no Pendrive")
            try:
                if not os.path.exists(iso_path):
                    raise Exception("ISO file not found.")
                mp = target_drive.get('mountpoint', target_drive.get('device', ''))
                if not os.path.exists(mp):
                    raise Exception("Target drive not accessible.")

                DriveManager.create_opl_structure(mp)
                size = os.path.getsize(iso_path)
                fs = target_drive.get('fstype', 'FAT32').upper()
                game_id = GameAnalyzer.extract_game_id(iso_path)
                opl_id = ArtScraperWorker.format_opl_id(game_id) if game_id != "Unknown" else ""
                clean_name = re.sub(r'[^a-zA-Z0-9_\-\. ]', '', game_name).strip()[:32] or "PS2_Game"
                ext = os.path.splitext(iso_path)[1].lower()
                if ext not in ('.iso', '.zso'):
                    ext = '.iso'

                cb_t = _throttle_prog(cb_prog)
                cb_t(0.05)
                if fs == "FAT32" and size > 4294967295 and ext == '.iso':
                    USBUtilWorker._split_sync(
                        iso_path, mp, clean_name,
                        cb_prog=lambda v: cb_t(0.05 + 0.85 * v)
                    )
                else:
                    target_folder = os.path.join(mp, "CD" if size < (700 * 1024 * 1024) else "DVD")
                    os.makedirs(target_folder, exist_ok=True)
                    final_filename = f"{opl_id}.{clean_name}{ext}" if opl_id else f"{clean_name}{ext}"
                    dest_file = os.path.join(target_folder, final_filename)
                    copied = 0
                    with open(iso_path, 'rb') as f_src, open(dest_file, 'wb') as f_dst:
                        while True:
                            buf = f_src.read(4 * 1024 * 1024)
                            if not buf:
                                break
                            f_dst.write(buf)
                            copied += len(buf)
                            if size > 0:
                                cb_t(0.05 + (0.85 * (copied / size)))

                if auto_cover and game_id != "Unknown":
                    ArtScraperWorker.download_single_art(mp, game_id)

                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


class BatchInstallWorker:
    """Fila de processamento em lote sequencial real."""
    def __init__(self, items, target_drive, auto_cover, cb_item_prog, cb_total_prog, cb_log, cb_done):
        self.items = items
        self.target_drive = target_drive
        self.auto_cover = auto_cover
        self.cb_item_prog = cb_item_prog
        self.cb_total_prog = cb_total_prog
        self.cb_log = cb_log
        self.cb_done = cb_done
        self.cancel_flag = False

    def cancel(self):
        self.cancel_flag = True

    def start(self):
        def run():
            TransferLockManager.acquire("Fila de Instalação em Lote")
            try:
                total_items = len(self.items)
                if total_items == 0:
                    self.cb_done(True)
                    return
                for idx, item in enumerate(self.items):
                    if self.cancel_flag:
                        self.cb_log("Batch cancelled by user.")
                        break
                    iso_path = item.get('path', '')
                    title = item.get('name', os.path.splitext(os.path.basename(iso_path))[0])
                    self.cb_log(f"[{idx+1}/{total_items}] Installing: {title}...")

                    done_event = threading.Event()
                    item_error = []

                    def on_done(s):
                        done_event.set()

                    def on_err(e):
                        item_error.append(e)
                        done_event.set()

                    SingleInstallWorker.install(
                        iso_path, self.target_drive, title, self.auto_cover,
                        cb_prog=lambda v, i=idx: [
                            self.cb_item_prog(v),
                            self.cb_total_prog((i + v) / total_items)
                        ],
                        cb_done=on_done,
                        cb_err=on_err
                    )
                    done_event.wait()
                    if item_error:
                        self.cb_log(f"-> ERROR on {title}: {item_error[0]}")
                    else:
                        self.cb_log(f"-> SUCCESS: {title} installed.")
                    self.cb_total_prog((idx + 1) / total_items)

                self.cb_total_prog(1.0)
                self.cb_done(True)
            except Exception as e:
                self.cb_log(f"Fatal error in batch: {e}")
                self.cb_done(False)
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


class PCSX2Integration:
    @staticmethod
    def get_pcsx2_docs_dir():
        return os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Documents", "PCSX2")

    @staticmethod
    def test_iso(iso_path, err_cb):
        def run():
            try:
                clean_iso_path = os.path.normpath(os.path.abspath(iso_path))
                if not os.path.exists(clean_iso_path):
                    return err_cb("Game ISO file not found.")
                docs_path = PCSX2Integration.get_pcsx2_docs_dir()
                etc_src = get_res_path(os.path.join("pcsx2", "ETC", "PCSX2"))
                if not os.path.exists(os.path.join(docs_path, "bios")) and os.path.exists(etc_src):
                    shutil.copytree(etc_src, docs_path, dirs_exist_ok=True)
                base_pcsx2 = get_res_path("pcsx2")
                exe_path = next(
                    (os.path.join(base_pcsx2, e) for e in ["pcsx2-qt.exe", "pcsx2-qtx64.exe", "pcsx2.exe"]
                     if os.path.exists(os.path.join(base_pcsx2, e))),
                    None
                )
                if not exe_path:
                    return err_cb(t("emu_err_notfound") if "emu_err_notfound" in dir() else "PCSX2 executable not found in 'pcsx2' folder.")
                subprocess.Popen([exe_path, clean_iso_path], cwd=base_pcsx2)
            except Exception as e:
                err_cb(str(e))
        threading.Thread(target=run, daemon=True).start()


class MigrationWorker:
    def __init__(self, drive, target_fs, callbacks, resume_data=None):
        self.drive = drive
        self.target_fs = target_fs
        self.cb_log = callbacks['log']
        self.cb_prog_total = callbacks['prog_total']
        self.cb_prog_step = callbacks['prog_step']
        self.cb_done = callbacks['done']
        self.tmp_dir = os.path.join(APP_DATA_DIR, "jogos.tmp")
        self.cancel_flag = False
        self.resume_data = resume_data

    def _copy_dir_with_progress(self, src_dir, dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
        for r, _, f in os.walk(src_dir):
            for file in f:
                s_path = os.path.join(r, file)
                d_path = os.path.join(dst_dir, os.path.relpath(s_path, src_dir))
                os.makedirs(os.path.dirname(d_path), exist_ok=True)
                offset = self.resume_data.get("copied", 0) if self.resume_data and self.resume_data.get("file") == s_path else 0
                self.resume_data = None
                size = os.path.getsize(s_path)
                copied = offset
                cb_t = _throttle_prog(self.cb_prog_step)
                last_save_ts = 0.0
                with open(s_path, 'rb') as fsrc, open(d_path, 'ab' if offset > 0 else 'wb') as fdst:
                    fsrc.seek(offset)
                    while True:
                        if self.cancel_flag:
                            raise Exception("Cancelled by user.")
                        buf = fsrc.read(4 * 1024 * 1024)
                        if not buf:
                            break
                        fdst.write(buf)
                        copied += len(buf)
                        cb_t(copied / size if size > 0 else 1)
                        now_s = time.monotonic()
                        if (now_s - last_save_ts) >= 1.0 or copied >= size:
                            last_save_ts = now_s
                            TransferStateManager.save("migration", self.drive['mountpoint'], self.target_fs, s_path, copied, size)

    def run(self):
        TransferLockManager.acquire("Migração e Formatação de Unidade")
        try:
            self.cb_prog_total(0.0)
            if not self.resume_data:
                self.cb_log("Backing up drive data...")
                self.cb_prog_total(0.1)
                if os.path.exists(self.tmp_dir):
                    shutil.rmtree(self.tmp_dir)
                self._copy_dir_with_progress(self.drive['mountpoint'], self.tmp_dir)
                self.cb_log(f"Formatting partition as {self.target_fs} via DiskPart...")
                self.cb_prog_total(0.45)
                script_path = os.path.join(os.environ.get("TEMP", APP_DATA_DIR), f"dp_{int(time.time())}.txt")
                vol_letter = self.drive['device'].replace(':', '').replace('\\', '')
                with open(script_path, "w") as f:
                    f.write(f"select volume {vol_letter}\nformat fs={self.target_fs} label=PS2USB quick\n")
                subprocess.run(f'diskpart /s "{script_path}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if os.path.exists(script_path):
                    os.remove(script_path)
            self.cb_log("Restoring files & OPL folders to target drive...")
            self.cb_prog_total(0.55)
            self._copy_dir_with_progress(self.tmp_dir, self.drive['mountpoint'])
            DriveManager.create_opl_structure(self.drive['mountpoint'])
            self.cb_prog_total(0.95)
            if os.path.exists(self.tmp_dir):
                shutil.rmtree(self.tmp_dir)
            TransferStateManager.clear()
            self.cb_prog_total(1.0)
            self.cb_prog_step(1.0)
            self.cb_log("Migration completed successfully!")
            self.cb_done(True)
        except Exception as e:
            self.cb_log(f"ERROR: {str(e)}")
            self.cb_done(False)
        finally:
            TransferLockManager.release()


class CloneWorker:
    def __init__(self, src_drive, dst_drive, format_dst, format_src, callbacks, resume_data=None):
        self.src = src_drive
        self.dst = dst_drive
        self.f_dst = format_dst
        self.f_src = format_src
        self.cb_log = callbacks['log']
        self.cb_prog_total = callbacks['prog_total']
        self.cb_done = callbacks.get('done', lambda s: None)
        self.cancel_flag = False
        self.resume_data = resume_data

    def _diskpart_format(self, drive, fs, label):
        script_path = os.path.join(os.environ.get("TEMP", APP_DATA_DIR), f"dp_clone_{int(time.time())}.txt")
        vol_letter = drive.replace(':', '').replace('\\', '')
        with open(script_path, "w") as f:
            f.write(f"select volume {vol_letter}\nformat fs={fs} label={label} quick\n")
        subprocess.run(f'diskpart /s "{script_path}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if os.path.exists(script_path):
            os.remove(script_path)

    def run(self):
        TransferLockManager.acquire("Clonagem de Pendrive")
        try:
            self.cb_prog_total(0.0)
            if self.f_dst and not self.resume_data:
                self.cb_log("Formatting destination drive...")
                self._diskpart_format(self.dst['device'], self.src.get('fstype', 'FAT32'), "PS2USB")
            all_files = []
            for r, dirs, files in os.walk(self.src['mountpoint']):
                for d in dirs:
                    os.makedirs(os.path.join(self.dst['mountpoint'], os.path.relpath(os.path.join(r, d), self.src['mountpoint'])), exist_ok=True)
                for f in files:
                    all_files.append(os.path.join(r, f))
            total_bytes = sum(os.path.getsize(p) for p in all_files) or 1
            done_bytes = 0
            for s_file in all_files:
                rel = os.path.relpath(s_file, self.src['mountpoint'])
                d_file = os.path.join(self.dst['mountpoint'], rel)
                os.makedirs(os.path.dirname(d_file), exist_ok=True)
                self.cb_log(f"Copying {rel}...")
                size = os.path.getsize(s_file)
                with open(s_file, 'rb') as fsrc, open(d_file, 'wb') as fdst:
                    while True:
                        if self.cancel_flag:
                            raise Exception("Cancelled by user.")
                        buf = fsrc.read(4 * 1024 * 1024)
                        if not buf:
                            break
                        fdst.write(buf)
                        done_bytes += len(buf)
                        self.cb_prog_total(min(done_bytes / total_bytes, 0.99))
            if self.f_src:
                self._diskpart_format(self.src['device'], "FAT32", "EMPTY_USB")
            TransferStateManager.clear()
            self.cb_prog_total(1.0)
            self.cb_log("Clone finished successfully!")
            self.cb_done(True)
        except Exception as e:
            self.cb_log(f"ERROR: {str(e)}")
            self.cb_done(False)
        finally:
            TransferLockManager.release()


class OplAppsManager:
    @staticmethod
    def install_app(app_name, elf_path, usb_mountpoint):
        try:
            if not app_name or not elf_path or not os.path.exists(elf_path):
                return "Invalid ELF file or app title."
            if not usb_mountpoint or not os.path.exists(usb_mountpoint):
                return "Target USB drive not accessible."
            apps_dir = os.path.join(usb_mountpoint, "APPS")
            safe_name = "".join(c for c in app_name if c.isalnum() or c in (' ', '_', '-')).strip()
            target_dir = os.path.join(apps_dir, safe_name)
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(elf_path, os.path.join(target_dir, "boot.elf"))
            with open(os.path.join(target_dir, "title.cfg"), "w", encoding="utf-8") as f:
                f.write(f"title={app_name}\nboot=boot.elf\n")
            return True
        except Exception as e:
            return str(e)


UsbDetector = DriveManager
DriveManager.get_removable_drives = staticmethod(DriveManager.get_drives)
AppManager = OplAppsManager
OplAppsManager.install_elf = staticmethod(lambda mp, title, elf: OplAppsManager.install_app(title, elf, mp))
