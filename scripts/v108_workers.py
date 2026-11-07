from __future__ import annotations

import os
import re
import time
import zlib
import struct
import shutil
import ctypes
import hashlib
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

from scripts.core_backend import (
    sys_logger, cfg, t, format_size, TransferLockManager, GameAnalyzer, PYCDLIB_SUPPORT
)
from scripts.tool_workers import ArtScraperWorker, DriveManager

if PYCDLIB_SUPPORT:
    import pycdlib


# ==============================================================================
# 1. VERIFICADOR DE FRAGMENTAÇÃO & OTIMIZADOR USB (ANTI-TELA PRETA DO OPL)
# ==============================================================================
class UsbDefragWorker:
    """
    Inspeciona os extents físicos reais de arquivos no Windows via DeviceIoControl
    (FSCTL_GET_RETRIEVAL_POINTERS = 0x00090073) sem exigir privilégios de Admin,
    desfragmenta por pré-alocação contígua + escrita sequencial e valida hashes.
    """
    FSCTL_GET_RETRIEVAL_POINTERS = 0x00090073
    FILE_READ_ATTRIBUTES = 0x0080
    GENERIC_WRITE = 0x40000000
    GENERIC_READ = 0x80000000
    FILE_SHARE_ALL = 0x00000001 | 0x00000002 | 0x00000004
    OPEN_EXISTING = 3
    CREATE_ALWAYS = 2
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    ERROR_MORE_DATA = 234

    @classmethod
    def get_file_fragments(cls, filepath):
        """Retorna a quantidade exata de fragmentos físicos não-contíguos do arquivo no disco."""
        if not os.path.exists(filepath):
            return 0
        try:
            fsize = os.path.getsize(filepath)
            if fsize == 0:
                return 1
        except Exception:
            return 1

        k32 = ctypes.windll.kernel32
        k32.CreateFileW.restype = ctypes.c_void_p
        k32.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p
        ]
        k32.DeviceIoControl.restype = ctypes.c_int
        k32.DeviceIoControl.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p
        ]
        k32.CloseHandle.restype = ctypes.c_int
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = k32.CreateFileW(
            os.path.abspath(filepath),
            cls.FILE_READ_ATTRIBUTES,
            cls.FILE_SHARE_ALL,
            None,
            cls.OPEN_EXISTING,
            0,
            None
        )
        if not handle or handle in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF, cls.INVALID_HANDLE_VALUE):
            return 1

        try:
            # Buffer para até 1024 extents por chamada (16 bytes header + 1024 * 16 bytes)
            max_extents = 1024
            out_buf_size = 16 + (max_extents * 16)
            out_buf = ctypes.create_string_buffer(out_buf_size)
            bytes_returned = ctypes.c_uint32(0)

            start_vcn = 0
            fragments = 0
            prev_end_lcn = None

            while True:
                in_buf = struct.pack('<q', start_vcn)
                ok = k32.DeviceIoControl(
                    ctypes.c_void_p(handle),
                    cls.FSCTL_GET_RETRIEVAL_POINTERS,
                    in_buf,
                    8,
                    out_buf,
                    out_buf_size,
                    ctypes.byref(bytes_returned),
                    None
                )
                err = ctypes.GetLastError() if not ok else 0
                if not ok and err != cls.ERROR_MORE_DATA:
                    break

                raw = out_buf.raw
                extent_count = struct.unpack_from('<I', raw, 0)[0]
                curr_vcn = struct.unpack_from('<q', raw, 8)[0]
                if extent_count == 0:
                    break

                for i in range(extent_count):
                    off = 16 + (i * 16)
                    next_vcn, lcn = struct.unpack_from('<qq', raw, off)
                    cluster_len = next_vcn - curr_vcn
                    if lcn != -1:  # Ignora clusters esparsos/não alocados
                        if prev_end_lcn is None or lcn != prev_end_lcn:
                            fragments += 1
                        prev_end_lcn = lcn + cluster_len
                    curr_vcn = next_vcn

                start_vcn = curr_vcn
                if ok:
                    break

            return max(1, fragments)
        except Exception:
            return 1
        finally:
            k32.CloseHandle(ctypes.c_void_p(handle))

    @classmethod
    def scan_usb_games(cls, root_path):
        """Escaneia DVD/, CD/, POPS/ e partes ul.* na unidade USB informada."""
        results = []
        if not root_path or not os.path.exists(root_path):
            return results

        candidates = []
        for sub in ["DVD", "CD", "POPS"]:
            d = os.path.join(root_path, sub)
            if os.path.isdir(d):
                for fn in sorted(os.listdir(d)):
                    if fn.lower().endswith(('.iso', '.zso', '.vcd', '.bin')):
                        candidates.append(os.path.join(d, fn))

        for fn in sorted(os.listdir(root_path)):
            full = os.path.join(root_path, fn)
            if os.path.isfile(full) and (fn.lower().startswith("ul.") and fn.lower() != "ul.cfg"):
                candidates.append(full)
            elif os.path.isfile(full) and fn.lower().endswith(('.iso', '.zso')):
                candidates.append(full)

        for fp in candidates:
            try:
                sz = os.path.getsize(fp)
                frags = cls.get_file_fragments(fp)
                gid = GameAnalyzer.extract_game_id(fp)
                results.append({
                    "name": GameAnalyzer.clean_display_title(os.path.basename(fp)),
                    "filename": os.path.basename(fp),
                    "rel_path": os.path.relpath(fp, root_path),
                    "path": fp,
                    "size_bytes": sz,
                    "size_str": format_size(sz),
                    "fragments": frags,
                    "is_fragmented": frags > 1,
                    "game_id": gid
                })
            except Exception:
                pass
        return results

    @classmethod
    def _preallocate_contiguous_copy(cls, src_path, tmp_path, cb_prog):
        """Pré-aloca todo o tamanho contínuo via Win32 SetFilePointerEx + SetEndOfFile e copia em blocos de 8 MB."""
        total_size = os.path.getsize(src_path)
        k32 = ctypes.windll.kernel32
        k32.CreateFileW.restype = ctypes.c_void_p
        k32.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p
        ]
        k32.CloseHandle.restype = ctypes.c_int
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        k32.SetFilePointerEx.restype = ctypes.c_int
        k32.SetFilePointerEx.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.POINTER(ctypes.c_int64), ctypes.c_uint32]
        k32.SetEndOfFile.restype = ctypes.c_int
        k32.SetEndOfFile.argtypes = [ctypes.c_void_p]
        h_out = k32.CreateFileW(
            os.path.abspath(tmp_path),
            cls.GENERIC_WRITE | cls.GENERIC_READ,
            0,
            None,
            cls.CREATE_ALWAYS,
            cls.FILE_ATTRIBUTE_NORMAL,
            None
        )
        if h_out and h_out not in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF, cls.INVALID_HANDLE_VALUE):
            try:
                new_pos = ctypes.c_int64(0)
                k32.SetFilePointerEx(ctypes.c_void_p(h_out), ctypes.c_int64(total_size), ctypes.byref(new_pos), 0)
                k32.SetEndOfFile(ctypes.c_void_p(h_out))
            finally:
                k32.CloseHandle(ctypes.c_void_p(h_out))

        copied = 0
        chunk_sz = 8 * 1024 * 1024
        with open(src_path, 'rb') as f_in, open(tmp_path, 'r+b' if os.path.exists(tmp_path) else 'wb') as f_out:
            f_out.seek(0)
            while True:
                buf = f_in.read(chunk_sz)
                if not buf:
                    break
                f_out.write(buf)
                copied += len(buf)
                if total_size > 0 and cb_prog:
                    cb_prog(min(copied / total_size, 0.98))
            f_out.truncate(total_size)
            f_out.flush()
            os.fsync(f_out.fileno())

    @classmethod
    def defragment_files(cls, file_list, cb_prog, cb_log, cb_done, cb_err):
        def run():
            TransferLockManager.acquire("Desfragmentação OPL USB")
            try:
                total_files = len(file_list)
                if total_files == 0:
                    return cb_done([])

                summary = []
                for idx, fp in enumerate(file_list):
                    if not os.path.exists(fp):
                        continue
                    fname = os.path.basename(fp)
                    fsize = os.path.getsize(fp)
                    old_frags = cls.get_file_fragments(fp)

                    drv_root = os.path.splitdrive(os.path.abspath(fp))[0] + "\\"
                    free_bytes = shutil.disk_usage(drv_root).free if os.path.exists(drv_root) else fsize * 2
                    if free_bytes < fsize + (16 * 1024 * 1024):
                        raise Exception(
                            f"Insufficient free space on {drv_root} to rewrite '{fname}' contiguously "
                            f"(Need {format_size(fsize)}, Free {format_size(free_bytes)})."
                        )

                    cb_log(f"[{idx+1}/{total_files}] Rewriting '{fname}' ({old_frags} frags) into contiguous clusters...")
                    tmp_path = fp + ".ps2defrag_tmp"
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                        cls._preallocate_contiguous_copy(
                            fp, tmp_path,
                            lambda v, i=idx: cb_prog((i + v) / total_files)
                        )
                        if os.path.getsize(tmp_path) != fsize:
                            raise Exception("Size mismatch during contiguous rewrite; original file preserved.")
                        os.replace(tmp_path, fp)
                        new_frags = cls.get_file_fragments(fp)
                        cb_log(f"-> Optimized '{fname}': {old_frags} frags ➔ {new_frags} frag(s)")
                        summary.append((fname, old_frags, new_frags))
                    finally:
                        if os.path.exists(tmp_path):
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                    cb_prog((idx + 1) / total_files)

                cb_prog(1.0)
                cb_done(summary)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def compute_hashes(filepath, cb_prog, cb_done, cb_err):
        def run():
            try:
                total = os.path.getsize(filepath)
                md5 = hashlib.md5()
                sha1 = hashlib.sha1()
                crc = 0
                read_b = 0
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        md5.update(chunk)
                        sha1.update(chunk)
                        crc = zlib.crc32(chunk, crc)
                        read_b += len(chunk)
                        if total > 0:
                            cb_prog(min(read_b / total, 0.99))
                cb_prog(1.0)
                cb_done({
                    "filename": os.path.basename(filepath),
                    "size_str": format_size(total),
                    "crc32": f"{crc & 0xFFFFFFFF:08X}",
                    "md5": md5.hexdigest().upper(),
                    "sha1": sha1.hexdigest().upper()
                })
            except Exception as e:
                cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()


# ==============================================================================
# 2. EDITOR DE COMPATIBILIDADE & MODOS DO OPL (CFG + WIDESCREEN + GSM)
# ==============================================================================
class OplCfgManager:
    """Leitor e gravador real de arquivos CFG/<GameID>.cfg do Open PS2 Loader."""

    GSM_MODES = {
        "NTSC (60Hz Interlaced)": 0,
        "NTSC Non-Interlaced (240p)": 1,
        "PAL (50Hz Interlaced)": 2,
        "PAL Non-Interlaced (288p)": 3,
        "HDTV 480p @60Hz (Progressive)": 6,
        "HDTV 576p @50Hz (Progressive)": 7,
        "HDTV 720p @60Hz (HD)": 10,
        "HDTV 1080i @60Hz (Full HD Interlaced)": 11
    }
    INV_GSM_MODES = {v: k for k, v in GSM_MODES.items()}

    DMA_MODES = {
        "UDMA 4 (Fastest / Default)": 7,
        "UDMA 3": 6,
        "UDMA 2": 5,
        "UDMA 1": 4,
        "UDMA 0": 3,
        "MDMA 2": 2,
        "MDMA 1": 1,
        "MDMA 0 (Safe / Slow)": 0
    }
    INV_DMA_MODES = {v: k for k, v in DMA_MODES.items()}

    COMMUNITY_PRESETS = {
        "— Custom / Manual —": None,
        "God of War II (DVD9 / Cutscenes)": {"modes": [2, 5], "dma": 7, "wide": False},
        "Shadow of the Colossus (Anti-Freeze)": {"modes": [1, 3], "dma": 7, "wide": True},
        "GTA: San Andreas (USB Smoothness)": {"modes": [2, 6], "dma": 7, "wide": True},
        "Black (Bypass Boot Black Screen)": {"modes": [3, 6], "dma": 7, "wide": True},
        "Resident Evil 4 (Disable IGR Fix)": {"modes": [6], "dma": 7, "wide": True},
        "Gran Turismo 4 (DVD-DL + IGR Fix)": {"modes": [5, 6], "dma": 7, "wide": True},
        "Kingdom Hearts II (USB FMV Stutter Fix)": {"modes": [2, 4], "dma": 7, "wide": False},
        "Jak X: Combat Racing (Modes 1+2+3)": {"modes": [1, 2, 3], "dma": 7, "wide": False},
        "Ratchet: Deadlocked / Gladiator (Modes 1+3)": {"modes": [1, 3], "dma": 7, "wide": False},
        "Need for Speed: Most Wanted (Modes 2+6)": {"modes": [2, 6], "dma": 7, "wide": True},
        "Bully / Canis Canem Edit (Mode 2 Sync)": {"modes": [2], "dma": 7, "wide": True},
        "Scarface: The World Is Yours (Modes 2+3+6)": {"modes": [2, 3, 6], "dma": 7, "wide": True}
    }

    @staticmethod
    def discover_games(root_path, library_games=None):
        """Lista todos os jogos encontrados no USB/pasta OPL + biblioteca local."""
        found = {}
        if root_path and os.path.exists(root_path):
            for sub in ["DVD", "CD"]:
                p = os.path.join(root_path, sub)
                if os.path.isdir(p):
                    for fn in os.listdir(p):
                        if fn.lower().endswith(('.iso', '.zso')):
                            full = os.path.join(p, fn)
                            gid = GameAnalyzer.extract_game_id(full)
                            if gid != "Unknown":
                                opl_id = ArtScraperWorker.format_opl_id(gid)
                                found[opl_id] = {
                                    "opl_id": opl_id,
                                    "title": GameAnalyzer.clean_display_title(fn)
                                }
            ul_cfg = os.path.join(root_path, "ul.cfg")
            if os.path.exists(ul_cfg):
                try:
                    with open(ul_cfg, 'rb') as f:
                        while True:
                            ent = f.read(64)
                            if len(ent) < 64:
                                break
                            title = ent[:32].decode('ascii', 'ignore').strip('\x00')
                            raw_id = ent[32:47].decode('ascii', 'ignore').strip('\x00')
                            if raw_id.startswith("ul."):
                                opl_id = ArtScraperWorker.format_opl_id(raw_id[3:])
                                found[opl_id] = {"opl_id": opl_id, "title": title or opl_id}
                except Exception:
                    pass
            cfg_dir = os.path.join(root_path, "CFG")
            if os.path.isdir(cfg_dir):
                for fn in os.listdir(cfg_dir):
                    if fn.lower().endswith(".cfg"):
                        opl_id = os.path.splitext(fn)[0]
                        if opl_id not in found:
                            found[opl_id] = {"opl_id": opl_id, "title": opl_id}

        if library_games:
            for g in library_games:
                gid = g.get("id", "Unknown")
                if gid and gid != "Unknown":
                    opl_id = ArtScraperWorker.format_opl_id(gid)
                    if opl_id not in found:
                        found[opl_id] = {"opl_id": opl_id, "title": g.get("name", opl_id)}

        return sorted(found.values(), key=lambda x: x["title"].lower())

    @classmethod
    def load_cfg(cls, root_path, game_id_or_opl_id):
        opl_id = ArtScraperWorker.format_opl_id(game_id_or_opl_id)
        cfg_file = os.path.join(root_path, "CFG", f"{opl_id}.cfg")
        state = {
            "opl_id": opl_id,
            "title": "",
            "modes": {1: False, 2: False, 3: False, 4: False, 5: False, 6: False},
            "dma_label": "UDMA 4 (Fastest / Default)",
            "enable_gsm": False,
            "gsm_mode_label": "HDTV 480p @60Hz (Progressive)",
            "gsm_field_fix": False,
            "widescreen": False,
            "exists": os.path.exists(cfg_file),
            "path": cfg_file
        }
        if not os.path.exists(cfg_file):
            return state

        kv = {}
        try:
            with open(cfg_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        kv[k.strip()] = v.strip()
        except Exception:
            return state

        state["title"] = kv.get("Title", "")
        try:
            bitmask = int(kv.get("Modes", "0"))
            for m in range(1, 7):
                state["modes"][m] = bool(bitmask & (1 << (m - 1)))
        except Exception:
            pass

        try:
            dma_val = int(kv.get("DMA", "7"))
            state["dma_label"] = cls.INV_DMA_MODES.get(dma_val, "UDMA 4 (Fastest / Default)")
        except Exception:
            pass

        state["enable_gsm"] = kv.get("$EnableGSM", "0") == "1"
        try:
            vmode = int(kv.get("$GSMVMode", "6"))
            state["gsm_mode_label"] = cls.INV_GSM_MODES.get(vmode, "HDTV 480p @60Hz (Progressive)")
        except Exception:
            pass
        state["gsm_field_fix"] = kv.get("$GSMFIELDFix", "0") == "1"
        state["widescreen"] = (kv.get("$EnableCheat", "0") == "1") or (kv.get("Aspect", "") == "aspect/w") or (kv.get("AspectText", "") == "16:9")
        return state

    @classmethod
    def save_cfg(cls, root_path, game_id_or_opl_id, data):
        opl_id = ArtScraperWorker.format_opl_id(game_id_or_opl_id.strip())
        if not opl_id:
            raise Exception("Invalid Game ID.")
        cfg_dir = os.path.join(root_path, "CFG")
        os.makedirs(cfg_dir, exist_ok=True)
        cfg_file = os.path.join(cfg_dir, f"{opl_id}.cfg")

        # Preserva chaves extras (ex: VMC, Description, Developer, Genre) caso o arquivo já exista
        preserved = {}
        managed_keys = {
            "CfgVersion", "$ConfigSource", "Title", "Modes", "ModesText",
            "DMA", "DMAText", "$EnableGSM", "$GSMVMode", "$GSMXOffset",
            "$GSMYOffset", "$GSMFIELDFix", "$EnableCheat", "Aspect", "AspectText"
        }
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            if k.strip() not in managed_keys:
                                preserved[k.strip()] = v.strip()
            except Exception:
                pass

        modes_dict = data.get("modes", {})
        bitmask = 0
        active_nums = []
        for m in range(1, 7):
            if modes_dict.get(m, False):
                bitmask |= (1 << (m - 1))
                active_nums.append(str(m))

        dma_label = data.get("dma_label", "UDMA 4 (Fastest / Default)")
        dma_val = cls.DMA_MODES.get(dma_label, 7)
        dma_short = dma_label.split("(")[0].strip().lower()

        lines = [
            "CfgVersion=8",
            "$ConfigSource=1"
        ]
        if data.get("title"):
            lines.append(f"Title={data['title']}")
        if bitmask > 0:
            lines.append(f"Modes={bitmask}")
            lines.append(f"ModesText={'+'.join(active_nums)}")
        lines.append(f"DMA={dma_val}")
        lines.append(f"DMAText={dma_short}")

        if data.get("enable_gsm", False):
            vmode = cls.GSM_MODES.get(data.get("gsm_mode_label", ""), 6)
            lines.append("$EnableGSM=1")
            lines.append(f"$GSMVMode={vmode}")
            lines.append("$GSMXOffset=0")
            lines.append("$GSMYOffset=0")
            lines.append(f"$GSMFIELDFix={'1' if data.get('gsm_field_fix', False) else '0'}")
        else:
            lines.append("$EnableGSM=0")

        if data.get("widescreen", False):
            lines.append("$EnableCheat=1")
            lines.append("Aspect=aspect/w")
            lines.append("AspectText=16:9")
            # Garante que a pasta CHT exista para widescreen .cht do OPL PS2RD
            cht_dir = os.path.join(root_path, "CHT")
            os.makedirs(cht_dir, exist_ok=True)
            cht_file = os.path.join(cht_dir, f"{opl_id}.cht")
            if not os.path.exists(cht_file):
                with open(cht_file, "w", encoding="utf-8") as cf:
                    cf.write(f"// {data.get('title') or opl_id} - OPL Widescreen / Cheats ({opl_id})\n// Paste Mastercode (90xxxxxx) & 16:9 codes below if needed:\n\n")
        else:
            lines.append("Aspect=aspect/s")
            lines.append("AspectText=4:3")

        for k, v in preserved.items():
            lines.append(f"{k}={v}")

        with open(cfg_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")

        return cfg_file


# ==============================================================================
# 3. CONVERSOR PS1 POPSTARTER (.BIN/.CUE ➔ .VCD NA PASTA DOWNLOADS)
# ==============================================================================
class PopStarterConverter:
    """
    Converte imagens PS1 (.CUE + .BIN, único ou multi-track) para o formato binário
    oficial .VCD do POPStarter (1 MB header 0x100000 com TOC BCD POPS + setores raw 2352),
    salvando diretamente na pasta Downloads do usuário.
    """
    VCD_HEADER_SIZE = 0x100000  # 1,048,576 bytes (1 MB exato exigido pelo POPS)

    @staticmethod
    def get_user_downloads_dir():
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(dl, exist_ok=True)
        return dl

    @staticmethod
    def _to_bcd(val):
        val = max(0, min(99, int(val)))
        return ((val // 10) << 4) | (val % 10)

    @staticmethod
    def _lba_to_msf(lba):
        # Na especificação Red Book / POPS, LBA 0 corresponde a 00:02:00 (+150 frames)
        total_frames = int(lba) + 150
        minutes = total_frames // (60 * 75)
        rem = total_frames % (60 * 75)
        seconds = rem // 75
        frames = rem % 75
        return minutes, seconds, frames

    @staticmethod
    def _msf_str_to_frames(msf_str):
        parts = [int(x) for x in msf_str.strip().split(':')]
        if len(parts) != 3:
            return 0
        return (parts[0] * 60 * 75) + (parts[1] * 75) + parts[2]

    @classmethod
    def parse_cue_or_bin(cls, src_path):
        """
        Retorna (lista_de_arquivos_bin, lista_de_tracks, total_sectors).
        Suporta tanto seleção direta do .cue quanto seleção de um .bin.
        """
        ext = os.path.splitext(src_path)[1].lower()
        cue_path = None
        if ext == ".cue":
            cue_path = src_path
        elif ext == ".bin":
            candidate_cue = os.path.splitext(src_path)[0] + ".cue"
            if os.path.exists(candidate_cue):
                cue_path = candidate_cue

        if not cue_path:
            if not os.path.exists(src_path):
                raise Exception("Source PS1 BIN file not found.")
            fsize = os.path.getsize(src_path)
            total_sectors = fsize // 2352
            if total_sectors <= 0:
                raise Exception("BIN file is too small or invalid.")
            tracks = [{
                "num": 1,
                "mode": "MODE2/2352",
                "idx0_lba": 0,
                "idx1_lba": 0
            }]
            return [(src_path, 2352)], tracks, total_sectors

        base_dir = os.path.dirname(os.path.abspath(cue_path))
        files_entries = []  # (filepath, sector_size, base_lba, sectors_count)
        tracks = []

        current_file = None
        current_file_base_lba = 0
        cumulative_lba = 0
        current_track = None

        with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                m_file = re.match(r'^FILE\s+(?:"([^"]+)"|(\S+))\s+(\S+)', line, re.IGNORECASE)
                if m_file:
                    fname = m_file.group(1) or m_file.group(2)
                    resolved = os.path.join(base_dir, fname)
                    if not os.path.exists(resolved):
                        resolved = os.path.join(base_dir, os.path.basename(fname))
                    if not os.path.exists(resolved):
                        raise Exception(f"Track file referenced in CUE not found: {fname}")
                    if current_track:
                        tracks.append(current_track)
                        current_track = None
                    fsize = os.path.getsize(resolved)
                    sec_sz = 2352 if (fsize % 2352 == 0 or fsize % 2048 != 0) else 2048
                    n_secs = fsize // sec_sz
                    current_file = resolved
                    current_file_base_lba = cumulative_lba
                    files_entries.append((resolved, sec_sz))
                    cumulative_lba += n_secs
                    continue

                m_trk = re.match(r'^TRACK\s+(\d+)\s+(\S+)', line, re.IGNORECASE)
                if m_trk:
                    if current_track:
                        tracks.append(current_track)
                    t_num = int(m_trk.group(1))
                    t_mode = m_trk.group(2).upper()
                    if "2048" in t_mode and files_entries:
                        # Atualiza tamanho de setor se a track for 2048
                        last_fp, _ = files_entries[-1]
                        files_entries[-1] = (last_fp, 2048)
                    current_track = {
                        "num": t_num,
                        "mode": t_mode,
                        "idx0_lba": None,
                        "idx1_lba": current_file_base_lba
                    }
                    continue

                m_idx = re.match(r'^INDEX\s+(\d+)\s+(\d+:\d+:\d+)', line, re.IGNORECASE)
                if m_idx and current_track is not None:
                    idx_no = int(m_idx.group(1))
                    rel_frames = cls._msf_str_to_frames(m_idx.group(2))
                    abs_lba = current_file_base_lba + rel_frames
                    if idx_no == 0:
                        current_track["idx0_lba"] = abs_lba
                    elif idx_no == 1:
                        current_track["idx1_lba"] = abs_lba
                        if current_track["idx0_lba"] is None:
                            current_track["idx0_lba"] = abs_lba

        if current_track:
            tracks.append(current_track)

        if not files_entries or not tracks:
            raise Exception("No valid FILE or TRACK entries found in CUE sheet.")

        # Recalcula total exato de setores
        total_sectors = sum(os.path.getsize(fp) // ssz for fp, ssz in files_entries)
        for trk in tracks:
            if trk["idx0_lba"] is None:
                trk["idx0_lba"] = trk["idx1_lba"]

        return files_entries, tracks, total_sectors

    @classmethod
    def build_pops_header(cls, tracks, total_sectors):
        """Constrói o cabeçalho binário oficial de 1 MB (0x100000 bytes) do POPStarter/POPS."""
        hdr = bytearray(cls.VCD_HEADER_SIZE)
        first_trk = tracks[0]["num"]
        last_trk = tracks[-1]["num"]
        first_ctrl = 0x41 if "AUDIO" not in tracks[0]["mode"] else 0x01
        last_ctrl = 0x41 if "AUDIO" not in tracks[-1]["mode"] else 0x01

        # Entry A0: Primeira track e tipo de disco XA/Mode2 (0x20)
        hdr[0:10] = bytes([
            first_ctrl, 0x00, 0xA0, 0x00, 0x00, 0x00, 0x00,
            cls._to_bcd(first_trk), 0x20, 0x00
        ])
        # Entry A1: Última track
        hdr[10:20] = bytes([
            last_ctrl, 0x00, 0xA1, 0x00, 0x00, 0x00, 0x00,
            cls._to_bcd(last_trk), 0x00, 0x00
        ])
        # Entry A2: Lead-out MSF
        lo_m, lo_s, lo_f = cls._lba_to_msf(total_sectors)
        hdr[20:30] = bytes([
            last_ctrl, 0x00, 0xA2, 0x00, 0x00, 0x00, 0x00,
            cls._to_bcd(lo_m), cls._to_bcd(lo_s), cls._to_bcd(lo_f)
        ])

        # Entries das Tracks (10 bytes cada a partir de 0x01E)
        for idx, trk in enumerate(tracks[:99]):
            off = 30 + (idx * 10)
            ctrl = 0x41 if "AUDIO" not in trk["mode"] else 0x01
            m0, s0, f0 = cls._lba_to_msf(trk["idx0_lba"])
            m1, s1, f1 = cls._lba_to_msf(trk["idx1_lba"])
            hdr[off:off + 10] = bytes([
                ctrl, 0x00, cls._to_bcd(trk["num"]),
                cls._to_bcd(m0), cls._to_bcd(s0), cls._to_bcd(f0),
                0x00,
                cls._to_bcd(m1), cls._to_bcd(s1), cls._to_bcd(f1)
            ])

        # Assinatura POPS e contagem de setores em 0x400..0x410 (padrão CUE2POPS)
        hdr[0x400:0x404] = b'POPS'
        struct.pack_into('<II', hdr, 0x408, total_sectors, total_sectors)
        return hdr

    @classmethod
    def convert_to_downloads(cls, src_path, desired_name, cb_prog, cb_done, cb_err):
        def run():
            TransferLockManager.acquire("Conversão PS1 BIN/CUE para .VCD")
            try:
                files_entries, tracks, total_sectors = cls.parse_cue_or_bin(src_path)
                dl_dir = cls.get_user_downloads_dir()
                clean_base = re.sub(r'[<>:"/\\|?*]', '', (desired_name or "").strip())
                if not clean_base:
                    clean_base = os.path.splitext(os.path.basename(src_path))[0]
                if clean_base.lower().endswith(".vcd"):
                    clean_base = clean_base[:-4]
                out_vcd = os.path.join(dl_dir, f"{clean_base}.VCD")

                cb_prog(0.03)
                header = cls.build_pops_header(tracks, total_sectors)
                written_sectors = 0

                with open(out_vcd, 'wb') as f_out:
                    f_out.write(header)
                    cb_prog(0.06)

                    for bin_fp, sec_sz in files_entries:
                        with open(bin_fp, 'rb') as f_in:
                            if sec_sz == 2352:
                                # Copia rápida alinhada a múltiplos de 2352 bytes (~3.6 MB por bloco)
                                batch_bytes = 2352 * 1536
                                while True:
                                    buf = f_in.read(batch_bytes)
                                    if not buf:
                                        break
                                    rem = len(buf) % 2352
                                    if rem != 0:
                                        buf += b'\x00' * (2352 - rem)
                                    f_out.write(buf)
                                    written_sectors += len(buf) // 2352
                                    if total_sectors > 0:
                                        cb_prog(min(0.06 + 0.93 * (written_sectors / total_sectors), 0.99))
                            else:
                                # Converte setores ISO 2048 para Mode2/Form1 2352
                                sync_hdr = b'\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00'
                                while True:
                                    data = f_in.read(2048)
                                    if not data:
                                        break
                                    if len(data) < 2048:
                                        data = data.ljust(2048, b'\x00')
                                    m, s, fr = cls._lba_to_msf(written_sectors)
                                    msf_hdr = bytes([cls._to_bcd(m), cls._to_bcd(s), cls._to_bcd(fr), 0x02])
                                    sub_hdr = b'\x00\x00\x08\x00\x00\x00\x08\x00'
                                    edc_ecc = b'\x00' * 280
                                    f_out.write(sync_hdr + msf_hdr + sub_hdr + data + edc_ecc)
                                    written_sectors += 1
                                    if written_sectors % 1024 == 0 and total_sectors > 0:
                                        cb_prog(min(0.06 + 0.93 * (written_sectors / total_sectors), 0.99))

                cb_prog(1.0)
                cb_done(out_vcd)
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


# ==============================================================================
# 4. PATCHER PERMANENTE DE WIDESCREEN 16:9 & CONVERSOR PAL ➔ NTSC (+ IPS/ESR)
# ==============================================================================
class WidescreenNtscPatcher:
    """
    Aplica patches permanentes diretamente no binário ELF de boot dentro da ISO de PS2:
      - Conversor PAL (50Hz) ➔ NTSC (60Hz) via patch de syscalls SetGsCrt ($a1=3 -> $a1=2)
      - Patch Permanente Widescreen 16:9 (via arquivo .pnach do PCSX2 ou heurística 4:3->16:9)
      - Patch IPS tradicional e remoção de trava de região ESR
    """

    @staticmethod
    def _locate_boot_elf_in_iso(iso_path):
        """Encontra o offset em bytes e o tamanho do executável ELF principal dentro da ISO."""
        if PYCDLIB_SUPPORT:
            try:
                iso = pycdlib.PyCdlib()
                iso.open(iso_path)
                try:
                    cnf_rec = iso.get_record(iso_path='/SYSTEM.CNF;1')
                except Exception:
                    cnf_rec = iso.get_record(iso_path='/SYSTEM.CNF')
                cnf_off = cnf_rec.extent_location() * 2048
                cnf_len = cnf_rec.get_data_length()
                iso.close()

                with open(iso_path, 'rb') as f:
                    f.seek(cnf_off)
                    cnf_txt = f.read(min(cnf_len, 4096)).decode('latin1', errors='ignore')

                m = re.search(r'BOOT2\s*=\s*cdrom0:\\?([^\s;]+)', cnf_txt, re.IGNORECASE)
                if m:
                    elf_rel = '/' + m.group(1).replace('\\', '/').lstrip('/').upper()
                    iso2 = pycdlib.PyCdlib()
                    iso2.open(iso_path)
                    rec = None
                    for cand in [elf_rel + ';1', elf_rel]:
                        try:
                            rec = iso2.get_record(iso_path=cand)
                            break
                        except Exception:
                            pass
                    iso2.close()
                    if rec:
                        return rec.extent_location() * 2048, rec.get_data_length(), elf_rel
            except Exception:
                pass

        # Fallback: procura assinatura \x7fELF alinhada a setor de 2048 bytes nos primeiros 64 MB
        with open(iso_path, 'rb') as f:
            pos = 0
            limit = 64 * 1024 * 1024
            while pos < limit:
                buf = f.read(2 * 1024 * 1024)
                if not buf:
                    break
                idx = buf.find(b'\x7fELF\x01\x01\x01')
                if idx != -1 and (pos + idx) % 2048 == 0:
                    return pos + idx, min(16 * 1024 * 1024, os.path.getsize(iso_path) - (pos + idx)), "BOOT.ELF"
                pos += len(buf)
        return None, 0, None

    @staticmethod
    def _parse_elf_segments(elf_bytes):
        """Lê os Program Headers (PT_LOAD) de um ELF32 MIPS Little-Endian do PS2."""
        if len(elf_bytes) < 52 or elf_bytes[:4] != b'\x7fELF':
            return []
        e_phoff = struct.unpack_from('<I', elf_bytes, 28)[0]
        e_phentsize = struct.unpack_from('<H', elf_bytes, 42)[0]
        e_phnum = struct.unpack_from('<H', elf_bytes, 44)[0]
        segments = []
        for i in range(e_phnum):
            off = e_phoff + (i * e_phentsize)
            if off + 32 > len(elf_bytes):
                break
            p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<6I', elf_bytes, off)
            if p_type == 1 and p_filesz > 0:  # PT_LOAD
                segments.append((p_vaddr, p_offset, p_filesz))
        return segments

    @classmethod
    def _apply_pnach_to_elf(cls, elf_buf, pnach_path):
        """Injeta códigos de memória EE de um arquivo .pnach diretamente nas seções do ELF."""
        segments = cls._parse_elf_segments(elf_buf)
        if not segments:
            return 0
        applied = 0
        with open(pnach_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('//') or s.startswith('#'):
                    continue
                m = re.match(r'^patch\s*=\s*\d+\s*,\s*EE\s*,\s*([0-9A-Fa-f]+)\s*,\s*(\w+)\s*,\s*([0-9A-Fa-f]+)', s, re.IGNORECASE)
                if not m:
                    continue
                raw_addr = int(m.group(1), 16)
                kind = m.group(2).lower()
                val = int(m.group(3), 16)

                cmd_type = (raw_addr >> 24) & 0xFE
                ee_addr = raw_addr & 0x01FFFFFF
                if ee_addr < 0x00080000:
                    continue

                if kind == "word" or cmd_type == 0x20 or (kind == "extended" and cmd_type == 0x00 and val > 0xFFFF):
                    write_bytes = struct.pack('<I', val & 0xFFFFFFFF)
                elif kind == "short" or (kind == "extended" and cmd_type == 0x10):
                    write_bytes = struct.pack('<H', val & 0xFFFF)
                elif kind == "byte" or (kind == "extended" and cmd_type == 0x00):
                    write_bytes = struct.pack('<B', val & 0xFF)
                else:
                    continue

                for p_vaddr, p_offset, p_filesz in segments:
                    if p_vaddr <= ee_addr <= (p_vaddr + p_filesz - len(write_bytes)):
                        file_pos = p_offset + (ee_addr - p_vaddr)
                        elf_buf[file_pos:file_pos + len(write_bytes)] = write_bytes
                        applied += 1
                        break
        return applied

    @staticmethod
    def _apply_auto_widescreen_to_elf(elf_buf):
        """Substitui constantes de aspecto 4:3 (1.3333334 / MIPS lui+ori) por 16:9 (1.7777778) no ELF."""
        count = 0
        # 1) Float IEEE-754 4/3 (0x3FAAAAAB) alinhado a 4 bytes -> 16/9 (0x3FE38E39)
        old_f1 = struct.pack('<I', 0x3FAAAAAB)
        new_f1 = struct.pack('<I', 0x3FE38E39)
        old_f2 = struct.pack('<I', 0x3FAAAAAC)
        for pos in range(0, len(elf_buf) - 4, 4):
            chunk = elf_buf[pos:pos + 4]
            if chunk == old_f1 or chunk == old_f2:
                elf_buf[pos:pos + 4] = new_f1
                count += 1

        # 2) Par de instruções MIPS: lui $reg, 0x3FAA ; ori $reg, $reg, 0xAAAB
        for pos in range(0, len(elf_buf) - 8, 4):
            ins1, ins2 = struct.unpack_from('<II', elf_buf, pos)
            if (ins1 & 0xFFE0FFFF) == 0x3C003FAA:
                reg = (ins1 >> 16) & 0x1F
                expected_ori = 0x3400AAAB | (reg << 21) | (reg << 16)
                if ins2 == expected_ori:
                    new_ins1 = 0x3C003FE3 | (reg << 16)
                    new_ins2 = 0x34008E39 | (reg << 21) | (reg << 16)
                    struct.pack_into('<II', elf_buf, pos, new_ins1, new_ins2)
                    count += 1
        return count

    @staticmethod
    def _apply_pal_to_ntsc_to_elf(elf_buf):
        """
        Procura chamadas SetGsCrt (syscall 0x02: li $v1, 2 / addiu $v1, $zero, 2 + syscall)
        e altera o carregamento de $a1 = 3 (PAL 50Hz) para $a1 = 2 (NTSC 60Hz).
        """
        patched = 0
        for pos in range(32, len(elf_buf) - 16, 4):
            ins_sys = struct.unpack_from('<I', elf_buf, pos)[0]
            if ins_sys != 0x0000000C:  # MIPS 'syscall'
                continue
            # Verifica se nas 4 instruções ao redor há carga de syscall #2 (SetGsCrt) em $v1 ($3)
            window_before = [struct.unpack_from('<I', elf_buf, pos - k * 4)[0] for k in range(1, 9)]
            is_setgscrt = any(w in (0x24030002, 0x34030002, 0x2403FFFE) for w in window_before[:3])
            if not is_setgscrt:
                continue
            # Procura addiu/ori $a1 ($5), $zero, 3 nas 8 instruções anteriores
            for k in range(1, 9):
                off = pos - k * 4
                w = struct.unpack_from('<I', elf_buf, off)[0]
                if w == 0x24050003:  # addiu $a1, $zero, 3 (PAL) -> 2 (NTSC)
                    struct.pack_into('<I', elf_buf, off, 0x24050002)
                    patched += 1
                elif w == 0x34050003:  # ori $a1, $zero, 3 (PAL) -> 2 (NTSC)
                    struct.pack_into('<I', elf_buf, off, 0x34050002)
                    patched += 1
        return patched

    @classmethod
    def patch_iso(cls, iso_in, iso_out, patch_file, apply_wide, apply_ntsc, remove_region, cb_prog, cb_done, cb_err):
        def run():
            TransferLockManager.acquire("Patcher ISO 16:9 / NTSC / IPS")
            try:
                if not iso_in or not os.path.exists(iso_in):
                    raise Exception("Source ISO file not found.")
                if not iso_out:
                    raise Exception("Please choose an output ISO file path.")
                if os.path.normcase(os.path.abspath(iso_in)) == os.path.normcase(os.path.abspath(iso_out)):
                    raise Exception("Output ISO must be a different file from Source ISO to preserve your backup.")

                total_size = os.path.getsize(iso_in)
                copied = 0
                os.makedirs(os.path.dirname(os.path.abspath(iso_out)), exist_ok=True)

                with open(iso_in, 'rb') as f_src, open(iso_out, 'wb') as f_dst:
                    while True:
                        buf = f_src.read(8 * 1024 * 1024)
                        if not buf:
                            break
                        f_dst.write(buf)
                        copied += len(buf)
                        if total_size > 0:
                            cb_prog((copied / total_size) * 0.70)

                report = []

                # 1) Aplica Patch IPS se informado
                if patch_file and os.path.exists(patch_file) and patch_file.lower().endswith('.ips'):
                    ips_edits = 0
                    with open(patch_file, 'rb') as p, open(iso_out, 'r+b') as f:
                        if p.read(5) != b'PATCH':
                            raise Exception("Invalid IPS patch header (expected 'PATCH').")
                        while True:
                            offset_bytes = p.read(3)
                            if offset_bytes == b'EOF' or len(offset_bytes) < 3:
                                break
                            offset = int.from_bytes(offset_bytes, 'big')
                            size = int.from_bytes(p.read(2), 'big')
                            if size == 0:
                                rle_size = int.from_bytes(p.read(2), 'big')
                                val = p.read(1)
                                f.seek(offset)
                                f.write(val * rle_size)
                            else:
                                data = p.read(size)
                                f.seek(offset)
                                f.write(data)
                            ips_edits += 1
                    report.append(f"IPS records applied: {ips_edits}")

                cb_prog(0.80)

                # 2) Aplica Widescreen 16:9 (.pnach ou auto) e/ou Conversor PAL -> NTSC no ELF
                has_pnach = bool(patch_file and os.path.exists(patch_file) and patch_file.lower().endswith('.pnach'))
                if apply_wide or apply_ntsc or has_pnach:
                    elf_off, elf_len, elf_name = cls._locate_boot_elf_in_iso(iso_out)
                    if elf_off is None or elf_len <= 0:
                        raise Exception("Could not locate PlayStation 2 boot ELF inside the ISO image.")

                    with open(iso_out, 'r+b') as f:
                        f.seek(elf_off)
                        elf_buf = bytearray(f.read(elf_len))

                        if has_pnach:
                            n_pnach = cls._apply_pnach_to_elf(elf_buf, patch_file)
                            report.append(f"PNACH codes injected into {elf_name}: {n_pnach}")
                        elif apply_wide:
                            n_wide = cls._apply_auto_widescreen_to_elf(elf_buf)
                            report.append(f"16:9 Widescreen ELF patches ({elf_name}): {n_wide}")

                        if apply_ntsc:
                            n_ntsc = cls._apply_pal_to_ntsc_to_elf(elf_buf)
                            report.append(f"PAL ➔ NTSC 60Hz SetGsCrt patches ({elf_name}): {n_ntsc}")

                        f.seek(elf_off)
                        f.write(elf_buf)

                cb_prog(0.94)

                # 3) Remove trava de região ESR se marcado
                if remove_region and os.path.getsize(iso_out) > 0x80020:
                    with open(iso_out, 'r+b') as f:
                        f.seek(0x80000)
                        f.write(b'\x00\x00\x01\xBA' + b'\x00' * 16)
                    report.append("ESR / Region flag unlocked")

                cb_prog(1.0)
                cb_done("\n".join(report) if report else "ISO copied cleanly.")
            except Exception as e:
                cb_err(str(e))
            finally:
                TransferLockManager.release()
        threading.Thread(target=run, daemon=True).start()


# ==============================================================================
# 5. ART SCRAPER 2.0 - KIT COMPLETO DE ARTES DO OPL COM PRÉVIA VISUAL
# ==============================================================================
class ArtScraperV2Worker:
    """
    Baixa o kit completo de artes do OPL para a pasta ART/:
      - _COV (Capa Frontal)
      - _COV2 (Capa Traseira)
      - _DISC (Ícone do Disco)
      - _BG (Plano de Fundo)
      - _SCR (Screenshot In-Game)
      - _LGO (Logo Transparente)
    """

    ART_SLOTS = ["COV", "COV2", "DISC", "BG", "SCR", "LGO"]

    @staticmethod
    def get_candidate_urls(game_id):
        repo_id = ArtScraperWorker.get_repo_id(game_id)   # Ex: SLUS-20946
        opl_id = ArtScraperWorker.format_opl_id(game_id)  # Ex: SLUS_209.46
        return {
            "COV": [
                (f"https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/{repo_id}.jpg", ".jpg"),
                (f"https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/3d/{repo_id}.png", ".png"),
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_COV.png", ".png"),
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_COV.jpg", ".jpg"),
            ],
            "COV2": [
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_COV2.jpg", ".jpg"),
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_COV2.png", ".png"),
                (f"https://archive.org/download/ps2-opl-art/{opl_id}_COV2.jpg", ".jpg"),
            ],
            "DISC": [
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_ICO.png", ".png"),
                (f"https://archive.org/download/ps2-opl-art/{opl_id}_ICO.png", ".png"),
                (f"https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/3d/{repo_id}.png", ".png"),
            ],
            "BG": [
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_BG_00.jpg", ".jpg"),
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_BG.jpg", ".jpg"),
                (f"https://archive.org/download/ps2-opl-art/{opl_id}_BG.jpg", ".jpg"),
            ],
            "SCR": [
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_SCR_00.jpg", ".jpg"),
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_SCR.jpg", ".jpg"),
                (f"https://archive.org/download/ps2-opl-art/{opl_id}_SCR.jpg", ".jpg"),
            ],
            "LGO": [
                (f"https://archive.org/download/OPLM_ART_2024_09/PS2/{opl_id}/{opl_id}_LGO.png", ".png"),
                (f"https://archive.org/download/ps2-opl-art/{opl_id}_LGO.png", ".png"),
            ],
        }

    @classmethod
    def find_local_arts(cls, root_path, game_id):
        """Retorna um dict { 'COV': caminho_ou_None, ... } das artes já salvas em ART/."""
        opl_id = ArtScraperWorker.format_opl_id(game_id)
        art_dir = os.path.join(root_path, "ART") if not root_path.upper().endswith("ART") else root_path
        found = {slot: None for slot in cls.ART_SLOTS}
        if not os.path.isdir(art_dir):
            return found

        suffix_aliases = {
            "COV": ["_COV.jpg", "_COV.png"],
            "COV2": ["_COV2.jpg", "_COV2.png"],
            "DISC": ["_ICO.png", "_ICO.jpg", "_DISC.png", "_DISC.jpg"],
            "BG": ["_BG.jpg", "_BG.png", "_BG_00.jpg"],
            "SCR": ["_SCR.jpg", "_SCR.png", "_SCR_00.jpg"],
            "LGO": ["_LGO.png", "_LGO.jpg"]
        }
        for slot, exts in suffix_aliases.items():
            for suf in exts:
                cand = os.path.join(art_dir, f"{opl_id}{suf}")
                if os.path.exists(cand) and os.path.getsize(cand) > 128:
                    found[slot] = cand
                    break
        return found

    @classmethod
    def download_full_kit(cls, root_path, game_ids, selected_slots, overwrite, cb_prog, cb_log, cb_item_done, cb_done, cb_err):
        def run():
            try:
                art_dir = os.path.join(root_path, "ART") if not root_path.upper().endswith("ART") else root_path
                os.makedirs(art_dir, exist_ok=True)

                slots = [s for s in cls.ART_SLOTS if s in selected_slots]
                total_steps = max(1, len(game_ids) * max(1, len(slots)))
                done_steps = 0

                opl_suffix_map = {
                    "COV": "_COV",
                    "COV2": "_COV2",
                    "DISC": "_ICO",  # OPL usa _ICO para o disco/ícone do jogo nos temas oficiais
                    "BG": "_BG",
                    "SCR": "_SCR",
                    "LGO": "_LGO"
                }

                for gid in game_ids:
                    opl_id = ArtScraperWorker.format_opl_id(gid)
                    urls_map = cls.get_candidate_urls(gid)
                    existing = cls.find_local_arts(root_path, gid)

                    for slot in slots:
                        if not overwrite and existing.get(slot):
                            cb_log(f"[{opl_id}] {slot}: already exists, skipped.")
                            done_steps += 1
                            cb_prog(done_steps / total_steps)
                            continue

                        candidates = urls_map.get(slot, [])
                        saved = False
                        for url, ext in candidates:
                            try:
                                req = urllib.request.Request(url, headers={'User-Agent': 'PS2Manager/1.08'})
                                with urllib.request.urlopen(req, timeout=6) as resp:
                                    raw = resp.read()
                                if len(raw) > 256:
                                    out_name = f"{opl_id}{opl_suffix_map[slot]}{ext}"
                                    out_path = os.path.join(art_dir, out_name)
                                    with open(out_path, 'wb') as f:
                                        f.write(raw)
                                    cb_log(f"[{opl_id}] Downloaded {out_name} ({format_size(len(raw))})")
                                    saved = True
                                    break
                            except Exception:
                                continue

                        if not saved:
                            cb_log(f"[{opl_id}] {slot}: not available on mirrors.")

                        done_steps += 1
                        cb_prog(done_steps / total_steps)

                    if cb_item_done:
                        cb_item_done(gid)

                cb_prog(1.0)
                cb_done(True)
            except Exception as e:
                cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()


# ==============================================================================
# 6. GERENCIADOR E CONVERSOR DE SAVES DE MEMORY CARD (PCSX2 .ps2 ⇄ OPL VMC .bin)
# ==============================================================================
class MemoryCardManager:
    """
    Motor binário real do sistema de arquivos Sony PS2 Memory Card Format 1.2.0.0:
      - Suporta cartões PCSX2 (.ps2 com páginas de 528 bytes e ECC Hamming real)
      - Suporta cartões OPL VMC (.bin com páginas brutas de 512 bytes, 8/16/32/64 MB)
      - Lista saves reais lendo Superblock, Indirect FAT, FAT e entradas de diretório + icon.sys
      - Exporta e Importa saves no formato universal .PSU (EMS Memory Adapter / uLaunchELF / PCSX2)
      - Exclui saves liberando clusters na FAT
      - Converte .ps2 ⇄ .bin (removendo ou recalculando ECC oficial) e formata novos cartões do zero!
    """

    MAGIC = b"Sony PS2 Memory Card Format 1.2.0.0\x00\x00\x00\x00\x00"
    DF_READ = 0x0001
    DF_WRITE = 0x0002
    DF_EXECUTE = 0x0004
    DF_FILE = 0x0010
    DF_DIR = 0x0020
    DF_0400 = 0x0400
    DF_EXISTS = 0x8000

    # Tabela oficial de paridade de coluna Hamming usada pelo PS2 / PCSX2 para cada byte (0..255)
    _COL_PARITY_TABLE = None

    @classmethod
    def _ensure_ecc_table(cls):
        if cls._COL_PARITY_TABLE is not None:
            return
        tbl = [0] * 256
        cpmasks = [0x55, 0x33, 0x0F, 0x00, 0xAA, 0xCC, 0xF0]
        for b in range(256):
            cp = 0
            for i, mask in enumerate(cpmasks):
                # Paridade de (b & mask)
                v = b & mask
                v ^= v >> 4
                v ^= v >> 2
                v ^= v >> 1
                if v & 1:
                    cp |= (1 << i)
            # Bit 7 guarda a paridade total do byte
            p = b
            p ^= p >> 4
            p ^= p >> 2
            p ^= p >> 1
            if p & 1:
                cp |= 0x80
            tbl[b] = cp
        cls._COL_PARITY_TABLE = tbl

    @classmethod
    def calc_ecc_128(cls, chunk128):
        """Calcula os 3 bytes de ECC Hamming oficial do PS2 para um bloco de 128 bytes."""
        cls._ensure_ecc_table()
        tbl = cls._COL_PARITY_TABLE
        column_parity = 0x77
        line_parity_0 = 0x7F
        line_parity_1 = 0x7F
        for i, b in enumerate(chunk128):
            cp = tbl[b]
            column_parity ^= (cp & 0x7F)
            if cp & 0x80:
                line_parity_0 ^= (~i) & 0x7F
                line_parity_1 ^= i & 0x7F
        return bytes([column_parity, line_parity_0 & 0x7F, line_parity_1 & 0x7F])

    @classmethod
    def calc_page_spare(cls, page512):
        """Retorna os 16 bytes de spare/ECC para uma página de 512 bytes (formato .ps2 PCSX2)."""
        if page512 == b'\xFF' * 512:
            return b'\xFF' * 16
        e0 = cls.calc_ecc_128(page512[0:128])
        e1 = cls.calc_ecc_128(page512[128:256])
        e2 = cls.calc_ecc_128(page512[256:384])
        e3 = cls.calc_ecc_128(page512[384:512])
        return e0 + e1 + e2 + e3 + b'\x00\x00\x00\x00'

    @staticmethod
    def _now_ps2_tod():
        """Retorna 8 bytes de timestamp no fuso JST (UTC+9) do PS2: pad, sec, min, hour, day, month, year(u16)."""
        jst = datetime.now(timezone(timedelta(hours=9)))
        return struct.pack('<BBBBBBH', 0, jst.second, jst.minute, jst.hour, jst.day, jst.month, jst.year)

    @staticmethod
    def _format_tod(tod8):
        if len(tod8) < 8:
            return ""
        _, sec, minute, hour, day, month, year = struct.unpack('<BBBBBBH', tod8)
        if year < 1999 or year > 2100 or month < 1 or month > 12:
            return ""
        return f"{day:02d}/{month:02d}/{year:04d} {hour:02d}:{minute:02d}"

    @classmethod
    def _load_raw_image(cls, card_path):
        """
        Carrega um cartão .ps2 (528B/página) ou .bin (512B/página) e retorna
        (bytearray_sem_ecc_512, has_ecc, superblock_dict).
        """
        with open(card_path, 'rb') as f:
            raw_file = f.read()

        if len(raw_file) < 528 * 64 and len(raw_file) < 512 * 64:
            raise Exception("Memory Card file is too small or corrupted.")

        if raw_file[:28] != b"Sony PS2 Memory Card Format ":
            raise Exception("Invalid signature! Not a formatted Sony PS2 Memory Card (.ps2 / .bin).")

        page_len = struct.unpack_from('<H', raw_file, 40)[0] or 512
        pages_per_cluster = struct.unpack_from('<H', raw_file, 42)[0] or 2
        pages_per_block = struct.unpack_from('<H', raw_file, 44)[0] or 16
        clusters_per_card = struct.unpack_from('<I', raw_file, 48)[0]
        total_pages = clusters_per_card * pages_per_cluster

        expected_ecc_size = total_pages * (page_len + 16)
        expected_raw_size = total_pages * page_len

        has_ecc = False
        if len(raw_file) == expected_ecc_size or (len(raw_file) % 528 == 0 and len(raw_file) % 512 != 0):
            has_ecc = True
            stride = page_len + 16
            num_p = len(raw_file) // stride
            clean_data = bytearray(num_p * page_len)
            for p in range(num_p):
                clean_data[p * page_len:(p + 1) * page_len] = raw_file[p * stride:p * stride + page_len]
        else:
            clean_data = bytearray(raw_file[:max(len(raw_file), expected_raw_size)])

        alloc_offset, alloc_end, rootdir_cluster, backup1, backup2 = struct.unpack_from('<5I', clean_data, 52)
        ifc_list = list(struct.unpack_from('<32I', clean_data, 80))

        sb = {
            "page_len": page_len,
            "pages_per_cluster": pages_per_cluster,
            "cluster_size": page_len * pages_per_cluster,
            "pages_per_block": pages_per_block,
            "clusters_per_card": clusters_per_card,
            "alloc_offset": alloc_offset,
            "alloc_end": alloc_end,
            "rootdir_cluster": rootdir_cluster,
            "backup1": backup1,
            "backup2": backup2,
            "ifc_list": [x for x in ifc_list if x not in (0, 0xFFFFFFFF)],
            "has_ecc": has_ecc
        }
        return clean_data, has_ecc, sb

    @classmethod
    def _save_raw_image(cls, card_path, clean_data, has_ecc, page_len=512):
        """Grava o bytearray de volta em disco (recalculando ECC Hamming de 16B se for .ps2)."""
        TransferLockManager.acquire("Gravação de Memory Card PS2")
        try:
            tmp_path = card_path + ".mctmp"
            if not has_ecc:
                with open(tmp_path, 'wb') as f:
                    f.write(clean_data)
            else:
                num_pages = len(clean_data) // page_len
                out = bytearray(num_pages * (page_len + 16))
                stride = page_len + 16
                for p in range(num_pages):
                    pg = bytes(clean_data[p * page_len:(p + 1) * page_len])
                    sp = cls.calc_page_spare(pg)
                    out[p * stride:p * stride + page_len] = pg
                    out[p * stride + page_len:(p + 1) * stride] = sp
                with open(tmp_path, 'wb') as f:
                    f.write(out)
            os.replace(tmp_path, card_path)
        finally:
            TransferLockManager.release()

    @staticmethod
    def _get_fat_table(clean_data, sb):
        """Retorna lista de (fat_cluster_abs_offset, indice_local) e os valores inteiros da FAT."""
        csz = sb["cluster_size"]
        entries_per_cluster = csz // 4
        fat_clusters = []
        for ifc in sb["ifc_list"]:
            base = ifc * csz
            if base + csz > len(clean_data):
                break
            ptrs = struct.unpack_from(f'<{entries_per_cluster}I', clean_data, base)
            for ptr in ptrs:
                if ptr not in (0, 0xFFFFFFFF):
                    fat_clusters.append(ptr)

        fat_values = []
        fat_locations = []  # byte offset de cada entrada FAT i
        for fc in fat_clusters:
            f_off = fc * csz
            if f_off + csz > len(clean_data):
                break
            vals = struct.unpack_from(f'<{entries_per_cluster}I', clean_data, f_off)
            for idx, v in enumerate(vals):
                fat_values.append(v)
                fat_locations.append(f_off + idx * 4)
        return fat_values, fat_locations

    @staticmethod
    def _follow_chain(fat_values, start_rel_cluster):
        chain = []
        cur = start_rel_cluster
        visited = set()
        while cur != 0xFFFFFFFF and cur not in visited and 0 <= cur < len(fat_values):
            visited.add(cur)
            chain.append(cur)
            nxt = fat_values[cur]
            if nxt == 0xFFFFFFFF or (nxt & 0x80000000) == 0:
                break
            cur = nxt & 0x7FFFFFFF
            if cur == 0x7FFFFFFF:
                break
        return chain

    @staticmethod
    def _read_rel_clusters(clean_data, sb, chain):
        csz = sb["cluster_size"]
        alloc_off = sb["alloc_offset"]
        buf = bytearray()
        for rel_c in chain:
            off = (alloc_off + rel_c) * csz
            buf.extend(clean_data[off:off + csz])
        return bytes(buf)

    @staticmethod
    def _decode_iconsys_title(iconsys_bytes):
        """Extrai e decodifica o título do jogo em Shift-JIS/ASCII do arquivo icon.sys (offset 0xC0)."""
        if len(iconsys_bytes) < 0x104 or iconsys_bytes[:4] != b'PS2D':
            return ""
        line_break = struct.unpack_from('<H', iconsys_bytes, 6)[0]
        raw_title = iconsys_bytes[0xC0:0x104].split(b'\x00')[0]
        try:
            if 0 < line_break < len(raw_title):
                p1 = raw_title[:line_break].decode('shift_jis', errors='ignore').strip()
                p2 = raw_title[line_break:].decode('shift_jis', errors='ignore').strip()
                full = f"{p1} {p2}".strip()
            else:
                full = raw_title.decode('shift_jis', errors='ignore').strip()
            # Converte caracteres full-width japoneses ASCII (ex: Ｇｏｄ -> God) para leitura limpa
            norm = []
            for ch in full:
                code = ord(ch)
                if 0xFF01 <= code <= 0xFF5E:
                    norm.append(chr(code - 0xFEE0))
                elif code == 0x3000:
                    norm.append(' ')
                else:
                    norm.append(ch)
            return "".join(norm).strip()
        except Exception:
            return ""

    @classmethod
    def inspect_card(cls, card_path):
        """Lista todos os saves reais presentes no cartão (.ps2 ou .bin) + estatísticas de espaço."""
        clean_data, has_ecc, sb = cls._load_raw_image(card_path)
        fat_values, _ = cls._get_fat_table(clean_data, sb)
        csz = sb["cluster_size"]

        free_clusters = sum(1 for idx in range(min(sb["alloc_end"], len(fat_values))) if (fat_values[idx] & 0x80000000) == 0)
        total_alloc_bytes = sb["alloc_end"] * csz
        free_bytes = free_clusters * csz

        root_chain = cls._follow_chain(fat_values, sb["rootdir_cluster"])
        root_bytes = cls._read_rel_clusters(clean_data, sb, root_chain)
        if len(root_bytes) < 512:
            return {"saves": [], "has_ecc": has_ecc, "total_str": format_size(total_alloc_bytes), "free_str": format_size(free_bytes)}

        root_len = struct.unpack_from('<I', root_bytes, 4)[0]
        max_entries = min(root_len, len(root_bytes) // 512)
        saves = []

        for i in range(2, max_entries):  # Pula 0 ('.') e 1 ('..')
            ent = root_bytes[i * 512:(i + 1) * 512]
            mode = struct.unpack_from('<H', ent, 0)[0]
            if not (mode & cls.DF_EXISTS) or not (mode & cls.DF_DIR):
                continue
            sub_len = struct.unpack_from('<I', ent, 4)[0]
            created_tod = ent[8:16]
            start_cluster = struct.unpack_from('<I', ent, 16)[0]
            mod_tod = ent[24:32]
            dir_name = ent[64:96].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
            if not dir_name:
                continue

            sub_chain = cls._follow_chain(fat_values, start_cluster)
            sub_bytes = cls._read_rel_clusters(clean_data, sb, sub_chain)
            sub_max = min(sub_len, len(sub_bytes) // 512)

            files_count = 0
            save_bytes = len(sub_chain) * csz
            pretty_title = ""

            for j in range(2, sub_max):
                f_ent = sub_bytes[j * 512:(j + 1) * 512]
                f_mode = struct.unpack_from('<H', f_ent, 0)[0]
                if not (f_mode & cls.DF_EXISTS) or not (f_mode & cls.DF_FILE):
                    continue
                f_len = struct.unpack_from('<I', f_ent, 4)[0]
                f_clus = struct.unpack_from('<I', f_ent, 16)[0]
                f_name = f_ent[64:96].split(b'\x00')[0].decode('ascii', errors='ignore')
                files_count += 1
                f_chain = cls._follow_chain(fat_values, f_clus) if f_len > 0 else []
                save_bytes += len(f_chain) * csz
                if f_name.lower() == "icon.sys" and f_chain:
                    raw_icon = cls._read_rel_clusters(clean_data, sb, f_chain)[:f_len]
                    pretty_title = cls._decode_iconsys_title(raw_icon)

            saves.append({
                "dir_name": dir_name,
                "title": pretty_title or dir_name,
                "files_count": files_count,
                "size_bytes": save_bytes,
                "size_str": format_size(save_bytes),
                "modified": cls._format_tod(mod_tod) or cls._format_tod(created_tod),
                "root_index": i
            })

        return {
            "saves": saves,
            "has_ecc": has_ecc,
            "format_label": "PCSX2 (.ps2 + ECC)" if has_ecc else "OPL VMC (.bin Raw)",
            "total_str": format_size(len(clean_data)),
            "free_str": format_size(free_bytes),
            "used_str": format_size(max(0, total_alloc_bytes - free_bytes))
        }

    @classmethod
    def export_psu(cls, card_path, target_dir_name, out_psu_path):
        """Exporta um diretório de save do cartão para um arquivo .PSU universal de 512-byte blocks."""
        clean_data, _, sb = cls._load_raw_image(card_path)
        fat_values, _ = cls._get_fat_table(clean_data, sb)

        root_chain = cls._follow_chain(fat_values, sb["rootdir_cluster"])
        root_bytes = cls._read_rel_clusters(clean_data, sb, root_chain)
        root_len = struct.unpack_from('<I', root_bytes, 4)[0]

        dir_ent = None
        for i in range(2, min(root_len, len(root_bytes) // 512)):
            ent = bytearray(root_bytes[i * 512:(i + 1) * 512])
            mode = struct.unpack_from('<H', ent, 0)[0]
            if (mode & cls.DF_EXISTS) and (mode & cls.DF_DIR):
                dname = ent[64:96].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
                if dname == target_dir_name:
                    dir_ent = ent
                    break

        if dir_ent is None:
            raise Exception(f"Save '{target_dir_name}' not found on Memory Card.")

        sub_len = struct.unpack_from('<I', dir_ent, 4)[0]
        start_cluster = struct.unpack_from('<I', dir_ent, 16)[0]
        sub_chain = cls._follow_chain(fat_values, start_cluster)
        sub_bytes = cls._read_rel_clusters(clean_data, sb, sub_chain)
        sub_max = min(sub_len, len(sub_bytes) // 512)

        valid_files = []
        for j in range(2, sub_max):
            f_ent = bytearray(sub_bytes[j * 512:(j + 1) * 512])
            f_mode = struct.unpack_from('<H', f_ent, 0)[0]
            if (f_mode & cls.DF_EXISTS) and (f_mode & cls.DF_FILE):
                f_len = struct.unpack_from('<I', f_ent, 4)[0]
                f_clus = struct.unpack_from('<I', f_ent, 16)[0]
                f_data = cls._read_rel_clusters(clean_data, sb, cls._follow_chain(fat_values, f_clus))[:f_len] if f_len > 0 else b''
                # Zera campos internos de cluster no PSU
                struct.pack_into('<I', f_ent, 16, 0)
                valid_files.append((f_ent, f_data))

        # Cabeçalho PSU: entrada principal com length = 2 ('.' e '..') + len(valid_files)
        psu_hdr = bytearray(dir_ent)
        struct.pack_into('<I', psu_hdr, 4, 2 + len(valid_files))
        struct.pack_into('<I', psu_hdr, 16, 0)

        dot_ent = bytearray(sub_bytes[0:512]) if len(sub_bytes) >= 512 else bytearray(512)
        dotdot_ent = bytearray(sub_bytes[512:1024]) if len(sub_bytes) >= 1024 else bytearray(512)
        struct.pack_into('<I', dot_ent, 16, 0)
        struct.pack_into('<I', dotdot_ent, 16, 0)

        with open(out_psu_path, 'wb') as out:
            out.write(psu_hdr)
            out.write(dot_ent)
            out.write(dotdot_ent)
            for f_ent, f_data in valid_files:
                out.write(f_ent)
                out.write(f_data)
                pad = (1024 - (len(f_data) % 1024)) % 1024
                if pad > 0:
                    out.write(b'\x00' * pad)
        return out_psu_path

    @classmethod
    def delete_save(cls, card_path, target_dir_name):
        """Remove um save do cartão liberando todos os seus clusters na FAT."""
        clean_data, has_ecc, sb = cls._load_raw_image(card_path)
        fat_values, fat_locs = cls._get_fat_table(clean_data, sb)
        csz = sb["cluster_size"]
        alloc_off = sb["alloc_offset"]

        root_chain = cls._follow_chain(fat_values, sb["rootdir_cluster"])
        root_bytes = bytearray(cls._read_rel_clusters(clean_data, sb, root_chain))
        root_len = struct.unpack_from('<I', root_bytes, 4)[0]

        found_idx = None
        for i in range(2, min(root_len, len(root_bytes) // 512)):
            ent_off = i * 512
            mode = struct.unpack_from('<H', root_bytes, ent_off)[0]
            if (mode & cls.DF_EXISTS) and (mode & cls.DF_DIR):
                dname = root_bytes[ent_off + 64:ent_off + 96].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
                if dname == target_dir_name:
                    found_idx = i
                    break

        if found_idx is None:
            raise Exception(f"Save '{target_dir_name}' not found.")

        ent_off = found_idx * 512
        sub_len = struct.unpack_from('<I', root_bytes, ent_off + 4)[0]
        start_cluster = struct.unpack_from('<I', root_bytes, ent_off + 16)[0]
        sub_chain = cls._follow_chain(fat_values, start_cluster)
        sub_bytes = cls._read_rel_clusters(clean_data, sb, sub_chain)

        clusters_to_free = list(sub_chain)
        for j in range(2, min(sub_len, len(sub_bytes) // 512)):
            f_ent = sub_bytes[j * 512:(j + 1) * 512]
            f_mode = struct.unpack_from('<H', f_ent, 0)[0]
            f_len = struct.unpack_from('<I', f_ent, 4)[0]
            f_clus = struct.unpack_from('<I', f_ent, 16)[0]
            if (f_mode & cls.DF_EXISTS) and f_len > 0:
                clusters_to_free.extend(cls._follow_chain(fat_values, f_clus))

        for rel_c in set(clusters_to_free):
            if 0 <= rel_c < len(fat_locs):
                struct.pack_into('<I', clean_data, fat_locs[rel_c], 0x7FFFFFFF)

        # Desmarca DF_EXISTS na entrada do diretório raiz
        old_mode = struct.unpack_from('<H', root_bytes, ent_off)[0]
        struct.pack_into('<H', root_bytes, ent_off, old_mode & ~cls.DF_EXISTS)
        for idx_c, rel_c in enumerate(root_chain):
            abs_off = (alloc_off + rel_c) * csz
            clean_data[abs_off:abs_off + csz] = root_bytes[idx_c * csz:(idx_c + 1) * csz]

        cls._save_raw_image(card_path, clean_data, has_ecc, sb["page_len"])
        return True

    @classmethod
    def import_psu(cls, card_path, psu_path):
        """Importa um arquivo .PSU real para dentro de um cartão .ps2 ou .bin."""
        with open(psu_path, 'rb') as f:
            psu_raw = f.read()
        if len(psu_raw) < 1536:
            raise Exception("Invalid or truncated .PSU save file.")

        dir_hdr = bytearray(psu_raw[0:512])
        dir_mode = struct.unpack_from('<H', dir_hdr, 0)[0]
        total_entries = struct.unpack_from('<I', dir_hdr, 4)[0]
        save_name = dir_hdr[64:96].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
        if not (dir_mode & cls.DF_DIR) or not save_name or total_entries < 2:
            raise Exception("Invalid .PSU directory header.")

        dot_ent = bytearray(psu_raw[512:1024])
        dotdot_ent = bytearray(psu_raw[1024:1536])
        pos = 1536
        files_to_write = []
        for _ in range(total_entries - 2):
            if pos + 512 > len(psu_raw):
                break
            f_hdr = bytearray(psu_raw[pos:pos + 512])
            pos += 512
            f_len = struct.unpack_from('<I', f_hdr, 4)[0]
            padded = ((f_len + 1023) // 1024) * 1024 if f_len > 0 else 0
            f_data = psu_raw[pos:pos + f_len]
            pos += padded
            files_to_write.append((f_hdr, f_data))

        # Se o save já existir no cartão, substitui limpando o anterior
        info = cls.inspect_card(card_path)
        if any(s["dir_name"] == save_name for s in info["saves"]):
            cls.delete_save(card_path, save_name)

        clean_data, has_ecc, sb = cls._load_raw_image(card_path)
        fat_values, fat_locs = cls._get_fat_table(clean_data, sb)
        csz = sb["cluster_size"]
        alloc_off = sb["alloc_offset"]
        max_c = min(sb["alloc_end"], len(fat_values))

        free_pool = [c for c in range(max_c) if (fat_values[c] & 0x80000000) == 0]

        def alloc_chain(n_clusters):
            if n_clusters <= 0:
                return []
            if len(free_pool) < n_clusters:
                raise Exception("Not enough free space on Memory Card for this save.")
            taken = [free_pool.pop(0) for _ in range(n_clusters)]
            for idx_k, c in enumerate(taken):
                nxt_val = 0xFFFFFFFF if idx_k == len(taken) - 1 else (0x80000000 | taken[idx_k + 1])
                fat_values[c] = nxt_val
                struct.pack_into('<I', clean_data, fat_locs[c], nxt_val)
            return taken

        def write_chain_bytes(chain, payload):
            for idx_k, rel_c in enumerate(chain):
                chunk = payload[idx_k * csz:(idx_k + 1) * csz]
                if len(chunk) < csz:
                    chunk = chunk + (b'\x00' * (csz - len(chunk)))
                abs_off = (alloc_off + rel_c) * csz
                clean_data[abs_off:abs_off + csz] = chunk

        # 1) Aloca e grava cada arquivo do save
        built_sub_entries = [dot_ent, dotdot_ent]
        for f_hdr, f_data in files_to_write:
            if len(f_data) > 0:
                n_clus = (len(f_data) + csz - 1) // csz
                f_chain = alloc_chain(n_clus)
                write_chain_bytes(f_chain, f_data)
                struct.pack_into('<I', f_hdr, 16, f_chain[0])
            else:
                struct.pack_into('<I', f_hdr, 16, 0xFFFFFFFF)
            struct.pack_into('<H', f_hdr, 0, struct.unpack_from('<H', f_hdr, 0)[0] | cls.DF_EXISTS | cls.DF_FILE)
            built_sub_entries.append(f_hdr)

        # 2) Aloca e grava os clusters do subdiretório do save
        sub_dir_bytes = b"".join(bytes(e) for e in built_sub_entries)
        sub_n_clus = (len(sub_dir_bytes) + csz - 1) // csz
        sub_chain = alloc_chain(sub_n_clus)

        # Ajusta '.' na entrada 0 do subdiretório
        root_chain = cls._follow_chain(fat_values, sb["rootdir_cluster"])
        root_bytes = bytearray(cls._read_rel_clusters(clean_data, sb, root_chain))
        root_len = struct.unpack_from('<I', root_bytes, 4)[0]

        # Procura slot livre no root_dir ou expande root_dir em +1 cluster
        slot_idx = None
        for i in range(2, min(root_len, len(root_bytes) // 512)):
            m_val = struct.unpack_from('<H', root_bytes, i * 512)[0]
            if not (m_val & cls.DF_EXISTS):
                slot_idx = i
                break

        if slot_idx is None:
            slot_idx = root_len
            if (slot_idx + 1) * 512 > len(root_bytes):
                new_rc = alloc_chain(1)[0]
                last_rc = root_chain[-1]
                fat_values[last_rc] = 0x80000000 | new_rc
                struct.pack_into('<I', clean_data, fat_locs[last_rc], fat_values[last_rc])
                root_chain.append(new_rc)
                root_bytes.extend(b'\x00' * csz)
            struct.pack_into('<I', root_bytes, 4, root_len + 1)

        struct.pack_into('<I', built_sub_entries[0], 16, sb["rootdir_cluster"])
        struct.pack_into('<I', built_sub_entries[0], 20, slot_idx)
        sub_dir_bytes = b"".join(bytes(e) for e in built_sub_entries)
        write_chain_bytes(sub_chain, sub_dir_bytes)

        # 3) Grava a entrada na tabela raiz
        struct.pack_into('<H', dir_hdr, 0, dir_mode | cls.DF_EXISTS | cls.DF_DIR)
        struct.pack_into('<I', dir_hdr, 4, len(built_sub_entries))
        struct.pack_into('<I', dir_hdr, 16, sub_chain[0])
        root_bytes[slot_idx * 512:(slot_idx + 1) * 512] = dir_hdr
        write_chain_bytes(root_chain, bytes(root_bytes))

        cls._save_raw_image(card_path, clean_data, has_ecc, sb["page_len"])
        return save_name

    @classmethod
    def create_blank_card(cls, out_path, size_mb=8, with_ecc=False):
        """
        Cria e formata um Memory Card PS2 100% autêntico do zero (8, 16, 32 ou 64 MB).
        Se with_ecc=True, gera no formato .ps2 do PCSX2 (528 bytes/página com ECC Hamming).
        Se with_ecc=False, gera no formato .bin VMC do OPL (512 bytes/página).
        """
        page_len = 512
        pages_per_cluster = 2
        cluster_size = page_len * pages_per_cluster  # 1024 bytes
        pages_per_block = 16
        clusters_per_block = pages_per_block // pages_per_cluster  # 8 clusters = 8 KB por erase block

        clusters_per_card = (size_mb * 1024 * 1024) // cluster_size
        blocks_per_card = clusters_per_card // clusters_per_block

        entries_per_cluster = cluster_size // 4  # 256 entradas de 32-bits por cluster
        n_fat_clusters = (clusters_per_card + entries_per_cluster - 1) // entries_per_cluster
        n_ifc_clusters = (n_fat_clusters + entries_per_cluster - 1) // entries_per_cluster

        ifc_start = 8  # Primeiro bloco (clusters 0..7) reservado ao Superblock
        fat_start = ifc_start + n_ifc_clusters
        # Alinha alloc_offset ao próximo erase block (múltiplo de 8 clusters)
        alloc_offset = ((fat_start + n_fat_clusters + clusters_per_block - 1) // clusters_per_block) * clusters_per_block
        backup1 = blocks_per_card - 1
        backup2 = blocks_per_card - 2
        alloc_end = (backup2 * clusters_per_block) - alloc_offset

        clean_data = bytearray(b'\xFF' * (clusters_per_card * cluster_size))

        # 1) Monta Superblock (Cluster 0, Página 0)
        sb_page = bytearray(cluster_size)
        sb_page[0:40] = cls.MAGIC
        struct.pack_into('<HHHH', sb_page, 40, page_len, pages_per_cluster, pages_per_block, 0xFF00)
        struct.pack_into('<6I', sb_page, 48, clusters_per_card, alloc_offset, alloc_end, 0, backup1, backup2)

        ifc_list = [ifc_start + i for i in range(n_ifc_clusters)] + [0] * (32 - n_ifc_clusters)
        struct.pack_into('<32I', sb_page, 80, *ifc_list[:32])
        struct.pack_into('<32i', sb_page, 208, *([-1] * 32))
        struct.pack_into('<BBHII', sb_page, 336, 2, 0x2B, 0, 1, 0)
        clean_data[0:cluster_size] = sb_page

        # 2) Monta Indirect FAT (IFC)
        ifc_bytes = bytearray(b'\xFF' * (n_ifc_clusters * cluster_size))
        for i in range(n_fat_clusters):
            struct.pack_into('<I', ifc_bytes, i * 4, fat_start + i)
        clean_data[ifc_start * cluster_size:(ifc_start + n_ifc_clusters) * cluster_size] = ifc_bytes

        # 3) Monta FAT (cluster 0 alocado para Root Dir = 0xFFFFFFFF; demais livres = 0x7FFFFFFF)
        fat_bytes = bytearray(b'\xFF' * (n_fat_clusters * cluster_size))
        for c in range(alloc_end):
            val = 0xFFFFFFFF if c == 0 else 0x7FFFFFFF
            struct.pack_into('<I', fat_bytes, c * 4, val)
        clean_data[fat_start * cluster_size:(fat_start + n_fat_clusters) * cluster_size] = fat_bytes

        # 4) Monta Root Directory (alloc_offset + 0) com '.' e '..'
        tod = cls._now_ps2_tod()
        root_cluster = bytearray(cluster_size)
        root_mode = cls.DF_READ | cls.DF_WRITE | cls.DF_EXECUTE | cls.DF_DIR | cls.DF_0400 | cls.DF_EXISTS

        dot = bytearray(512)
        struct.pack_into('<HHI', dot, 0, root_mode, 0, 2)
        dot[8:16] = tod
        struct.pack_into('<II', dot, 16, 0, 0)
        dot[24:32] = tod
        dot[64:66] = b'.\x00'

        dotdot = bytearray(512)
        struct.pack_into('<HHI', dotdot, 0, (root_mode & ~0x0400) | 0x1000, 0, 0)
        dotdot[8:16] = tod
        struct.pack_into('<II', dotdot, 16, 0, 0)
        dotdot[24:32] = tod
        dotdot[64:67] = b'..\x00'

        root_cluster[0:512] = dot
        root_cluster[512:1024] = dotdot
        clean_data[alloc_offset * cluster_size:(alloc_offset + 1) * cluster_size] = root_cluster

        cls._save_raw_image(out_path, clean_data, with_ecc, page_len)
        return out_path

    @classmethod
    def convert_card(cls, src_path, dst_path, target_ecc, cb_prog, cb_done, cb_err):
        """Converte entre PCSX2 .ps2 (ECC 528B) e OPL VMC .bin (Raw 512B)."""
        def run():
            try:
                cb_prog(0.15)
                clean_data, _, sb = cls._load_raw_image(src_path)
                cb_prog(0.50)
                os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
                cls._save_raw_image(dst_path, clean_data, bool(target_ecc), sb["page_len"])
                cb_prog(1.0)
                cb_done(dst_path)
            except Exception as e:
                cb_err(str(e))
        threading.Thread(target=run, daemon=True).start()
