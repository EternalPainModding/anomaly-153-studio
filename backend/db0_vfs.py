#!/usr/bin/env python3
"""
Anomaly Studio v0.1.0-alpha — Direct .db0 Virtual File System (VFS) & Packer
============================================================================
Reads and packs S.T.A.L.K.E.R. Anomaly 1.5.3 `.db0` archives directly from the
user's installation (`<anomaly_path>/db/**/*.db*` and `<anomaly_path>/mods/*.db*`)
plus active project overrides (`projects/<project>/gamedata/`), with ZERO
dependency on any `unpacked/` directory.

Author / Credits: EternalPain
"""
from __future__ import annotations
import ctypes
import glob
import json
import os
import struct
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

STUDIO_ROOT = Path(__file__).resolve().parent.parent
NATIVE_DIR = STUDIO_ROOT / "backend" / "native"
CACHE_DIR = STUDIO_ROOT / ".studio_cache"

_libxr = ctypes.CDLL(str(NATIVE_DIR / "libxr_unpack.so"))
_libxr.xr_decompress_lzhuf.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
]
_libxr.xr_decompress_lzhuf.restype = ctypes.c_void_p
_libxr.xr_free_buf.argtypes = [ctypes.c_void_p]

_lzo = ctypes.CDLL("/usr/lib/x86_64-linux-gnu/liblzo2.so.2")
_lzo.lzo1x_decompress_safe.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.c_void_p,
]
_lzo.lzo1x_decompress_safe.restype = ctypes.c_int


@dataclass
class Db0Entry:
    vfs_path: str
    archive_path: str
    offset: int
    size_real: int
    size_compr: int
    crc: int
    prefix: str


def normalize_vfs_path(path_str: str) -> str:
    p = path_str.strip().replace("\\", "/").lower()
    while p.startswith("/"):
        p = p[1:]
    if p.startswith("gamedata/"):
        p = p[len("gamedata/"):]
    return p


def infer_archive_prefix(archive_path: str) -> str:
    """
    In Anomaly 1.5.3:
    - `db/configs/configs.db0` has `[header] prefix = configs` (or files relative to configs/)
    - We read chunk 666 (`[header]`) if present to get exact `prefix`!
    """
    return ""


def read_archive_header_prefix(f, chunk_size: int) -> str:
    try:
        raw = f.read(chunk_size).decode("cp1251", errors="ignore")
        for line in raw.splitlines():
            line = line.strip()
            if line.lower().startswith("prefix"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    pref = parts[1].strip().replace("\\", "/").strip("/")
                    if pref.lower().startswith("gamedata/"):
                        pref = pref[len("gamedata/"):]
                    elif pref.lower() == "gamedata":
                        pref = ""
                    return pref.lower()
    except Exception:
        pass
    return ""


def parse_toc_bytes(toc: bytes, archive_path: str, prefix: str) -> List[Db0Entry]:
    entries: List[Db0Entry] = []
    p, n = 0, len(toc)
    while p + 2 <= n:
        bsz = struct.unpack_from("<H", toc, p)[0]
        p += 2
        if bsz < 16 or p + bsz > n:
            break
        s_real, s_compr, crc = struct.unpack_from("<III", toc, p)
        name_len = bsz - 16
        raw_name = toc[p + 12 : p + 12 + name_len].decode("cp1251", errors="replace").rstrip("\x00")
        offset = struct.unpack_from("<I", toc, p + 12 + name_len)[0]
        rel = normalize_vfs_path(raw_name)
        if prefix and not rel.startswith(prefix + "/"):
            vfs_path = f"{prefix}/{rel}" if rel else prefix
        else:
            vfs_path = rel
        entries.append(
            Db0Entry(
                vfs_path=vfs_path,
                archive_path=archive_path,
                offset=offset,
                size_real=s_real,
                size_compr=s_compr,
                crc=crc,
                prefix=prefix,
            )
        )
        p += bsz
    return entries


def read_db0_toc(archive_path: str) -> List[Db0Entry]:
    sz = os.path.getsize(archive_path)
    prefix = ""
    with open(archive_path, "rb") as f:
        pos = 0
        while pos + 8 <= sz:
            f.seek(pos)
            cid, csz = struct.unpack("<II", f.read(8))
            comp = bool(cid & 0x80000000)
            chunk_id = cid & 0x7FFFFFFF
            if chunk_id == 666 and not comp and csz <= 4096:
                prefix = read_archive_header_prefix(f, csz)
            elif chunk_id == 1:
                raw_bytes = f.read(csz)
                if not comp:
                    toc = raw_bytes
                else:
                    raw = ctypes.create_string_buffer(raw_bytes, csz)
                    out_sz = ctypes.c_uint32(0)
                    ptr = _libxr.xr_decompress_lzhuf(raw, csz, ctypes.byref(out_sz))
                    if not ptr or out_sz.value == 0:
                        return []
                    toc = ctypes.string_at(ptr, out_sz.value)
                    _libxr.xr_free_buf(ptr)
                return parse_toc_bytes(toc, archive_path, prefix)
            pos += 8 + csz
    return []


def extract_db0_entry(entry: Db0Entry) -> bytes:
    if entry.size_real == 0 or entry.offset == 0:
        return b""
    with open(entry.archive_path, "rb") as f:
        f.seek(entry.offset)
        comp = f.read(entry.size_compr)
    if entry.size_real == entry.size_compr:
        return comp
    # Try LZO1X first (standard Anomaly/CoP chunk payload compression)
    out_buf = ctypes.create_string_buffer(entry.size_real + 64)
    out_len = ctypes.c_size_t(entry.size_real + 64)
    rc = _lzo.lzo1x_decompress_safe(comp, len(comp), out_buf, ctypes.byref(out_len), None)
    if rc == 0 and out_len.value == entry.size_real:
        return out_buf.raw[: entry.size_real]
    # Fallback: LZHUF if compressed with xr_compress LZHUF
    raw = ctypes.create_string_buffer(comp, len(comp))
    out_sz = ctypes.c_uint32(0)
    ptr = _libxr.xr_decompress_lzhuf(raw, len(comp), ctypes.byref(out_sz))
    if ptr and out_sz.value > 0:
        res = ctypes.string_at(ptr, out_sz.value)
        _libxr.xr_free_buf(ptr)
        return res
    raise RuntimeError(f"Failed to decompress {entry.vfs_path} from {os.path.basename(entry.archive_path)} (LZO rc={rc})")


class AnomalyDb0VFS:
    """
    High-speed indexed VFS over all packed Anomaly `.db0` archives + project overrides.
    Never touches or requires any `unpacked/` folder.
    """

    def __init__(self, anomaly_path: str, mo2_path: str = "", log_fn: Optional[Callable[[str, str, str], None]] = None):
        self.anomaly_path = anomaly_path
        self.mo2_path = mo2_path
        self.log_fn = log_fn
        self.entries: Dict[str, Db0Entry] = {}
        self.archive_counts: Dict[str, int] = {}
        self.total_archives = 0
        self.scan_ms = 0.0
        self._text_cache: Dict[str, str] = {}

    def _log(self, level: str, msg_en: str, msg_ru: str = "") -> None:
        if self.log_fn:
            self.log_fn(level, msg_en, msg_ru or msg_en)

    def build_index(self, force_rescan: bool = False) -> Dict[str, Any]:
        t0 = time.time()
        self.entries.clear()
        self.archive_counts.clear()
        self._text_cache.clear()

        anom_root = Path(self.anomaly_path)
        db_dir = anom_root / "db"
        mods_dir = anom_root / "mods"
        if not db_dir.is_dir():
            self._log(
                "ERROR",
                f"Anomaly db/ directory not found at: {db_dir}",
                f"Папка db/ Anomaly не найдена по пути: {db_dir}",
            )
            return {"ok": False, "archives": 0, "files": 0}

        # Collect archives in Anomaly load priority order: db/** then mods/**
        db_files = sorted(glob.glob(str(db_dir / "**" / "*.db*"), recursive=True))
        if mods_dir.is_dir():
            db_files.extend(sorted(glob.glob(str(mods_dir / "**" / "*.db*"), recursive=True)))

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / "db0_vfs_index.json"

        # Check fast signature cache
        sig = [(p, os.path.getsize(p), int(os.path.getmtime(p))) for p in db_files if os.path.isfile(p)]
        if not force_rescan and cache_file.is_file():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                if cached.get("sig") == [list(x) for x in sig]:
                    for item in cached.get("entries", []):
                        e = Db0Entry(*item)
                        self.entries[e.vfs_path] = e
                    self.archive_counts = cached.get("archive_counts", {})
                    self.total_archives = len(sig)
                    self.scan_ms = round((time.time() - t0) * 1000.0, 1)
                    self._log(
                        "INFO",
                        f"Loaded .db0 VFS index from cache: {len(self.entries)} files across {self.total_archives} packed .db0 archives ({self.scan_ms} ms, 0 unpacked dependencies).",
                        f"Индекс .db0 VFS загружен из кэша: {len(self.entries)} файлов в {self.total_archives} архивах .db0 ({self.scan_ms} мс, без папки unpacked).",
                    )
                    return {"ok": True, "archives": self.total_archives, "files": len(self.entries), "scan_ms": self.scan_ms, "cached": True}
            except Exception:
                pass

        for p in db_files:
            if not os.path.isfile(p):
                continue
            ents = read_db0_toc(p)
            self.archive_counts[os.path.basename(p)] = len(ents)
            for e in ents:
                if e.size_real > 0:
                    self.entries[e.vfs_path] = e

        self.total_archives = len(sig)
        self.scan_ms = round((time.time() - t0) * 1000.0, 1)

        try:
            serializable = [
                [e.vfs_path, e.archive_path, e.offset, e.size_real, e.size_compr, e.crc, e.prefix]
                for e in self.entries.values()
            ]
            cache_file.write_text(
                json.dumps({"sig": [list(x) for x in sig], "archive_counts": self.archive_counts, "entries": serializable}),
                encoding="utf-8",
            )
        except Exception:
            pass

        self._log(
            "INFO",
            f"Indexed {len(self.entries)} files directly from {self.total_archives} packed .db0 archives in {self.scan_ms} ms.",
            f"Проиндексировано {len(self.entries)} файлов напрямую из {self.total_archives} архивов .db0 за {self.scan_ms} мс.",
        )
        return {"ok": True, "archives": self.total_archives, "files": len(self.entries), "scan_ms": self.scan_ms, "cached": False}

    def exists(self, vfs_path: str, project_gamedata: Optional[Path] = None) -> bool:
        norm = normalize_vfs_path(vfs_path)
        if project_gamedata:
            cand = project_gamedata / norm
            if cand.is_file():
                return True
        return norm in self.entries

    def read_bytes(self, vfs_path: str, project_gamedata: Optional[Path] = None) -> bytes:
        norm = normalize_vfs_path(vfs_path)
        if project_gamedata:
            cand = project_gamedata / norm
            if cand.is_file():
                return cand.read_bytes()
        entry = self.entries.get(norm)
        if not entry:
            raise FileNotFoundError(f"VFS file not found in .db0 archives: {norm}")
        return extract_db0_entry(entry)

    def read_text(self, vfs_path: str, project_gamedata: Optional[Path] = None, encoding: str = "cp1251") -> str:
        norm = normalize_vfs_path(vfs_path)
        if project_gamedata:
            cand = project_gamedata / norm
            if cand.is_file():
                raw = cand.read_bytes()
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    return raw.decode(encoding, errors="replace")
        cache_key = f"{norm}:{encoding}"
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]
        raw = self.read_bytes(norm)
        try:
            txt = raw.decode("utf-8")
        except UnicodeDecodeError:
            txt = raw.decode(encoding, errors="replace")
        if len(self._text_cache) < 2048:
            self._text_cache[cache_key] = txt
        return txt

    def list_matching(self, prefix: str = "", suffix: str = "", limit: int = 5000) -> List[str]:
        pref = normalize_vfs_path(prefix)
        suf = suffix.lower()
        out: List[str] = []
        for k in self.entries.keys():
            if pref and not k.startswith(pref):
                continue
            if suf and not k.endswith(suf):
                continue
            out.append(k)
            if len(out) >= limit:
                break
        out.sort()
        return out


def pack_directory_to_db0(source_dir: Path, output_db0: Path, header_prefix: str = "") -> Dict[str, Any]:
    """
    Packs a `gamedata/` folder into a valid S.T.A.L.K.E.R. Anomaly 1.5.3 `.db0` archive:
    - Chunk 666: `[header]\nauto_load = true\nlevel_name = single\n...`
    - Chunk 0: Uncompressed file payload stream (100% compatible with Anomaly 1.5.3 CFileSystem::Register)
    - Chunk 1 (uncompressed TOC): `[uint16 block_size][uint32 size_real][uint32 size_compr][uint32 crc32][char name[]][uint32 offset]`
    """
    t0 = time.time()
    source_dir = Path(source_dir).resolve()
    output_db0 = Path(output_db0).resolve()
    output_db0.parent.mkdir(parents=True, exist_ok=True)

    # If source_dir has a `gamedata` child, pack relative to `gamedata`
    root_for_rel = source_dir / "gamedata" if (source_dir / "gamedata").is_dir() else source_dir

    files_to_pack: List[Tuple[str, Path]] = []
    for p in sorted(root_for_rel.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            rel = p.relative_to(root_for_rel).as_posix().replace("/", "\\").lower()
            files_to_pack.append((rel, p))

    header_str = (
        "[header]\r\n"
        "auto_load = true\r\n"
        "level_name = single\r\n"
        "level_ver = 1.0\r\n"
        "entry_point = $fs_root$\\gamedata\\\r\n"
        "creator = \"Anomaly Studio v0.1.0-alpha (EternalPain)\"\r\n"
        "link = \"https://discord.com\"\r\n"
    )
    if header_prefix:
        header_str += f"prefix = {header_prefix}\r\n"
    header_bytes = header_str.encode("cp1251", errors="replace")

    chunk666_header = struct.pack("<II", 666, len(header_bytes))
    # Chunk 0 starts right after chunk 666
    chunk0_header_offset = 8 + len(header_bytes)
    payload_start_offset = chunk0_header_offset + 8

    payload_parts: List[bytes] = []
    toc_parts: List[bytes] = []
    cur_offset = payload_start_offset

    for rel_win, fpath in files_to_pack:
        data = fpath.read_bytes()
        sz = len(data)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        name_bytes = rel_win.encode("cp1251", errors="replace")
        # block_size = 4(s_real) + 4(s_compr) + 4(crc) + len(name_bytes) + 4(offset)
        block_size = 16 + len(name_bytes)
        entry_bin = (
            struct.pack("<HIII", block_size, sz, sz, crc)
            + name_bytes
            + struct.pack("<I", cur_offset)
        )
        toc_parts.append(entry_bin)
        payload_parts.append(data)
        cur_offset += sz

    payload_blob = b"".join(payload_parts)
    toc_blob = b"".join(toc_parts)

    chunk0_header = struct.pack("<II", 0, len(payload_blob))
    # Uncompressed TOC chunk (chunk_id = 1, bit 31 = 0 -> Anomaly supports uncompressed TOC natively)
    chunk1_header = struct.pack("<II", 1, len(toc_blob))

    with open(output_db0, "wb") as out_f:
        out_f.write(chunk666_header)
        out_f.write(header_bytes)
        out_f.write(chunk0_header)
        out_f.write(payload_blob)
        out_f.write(chunk1_header)
        out_f.write(toc_blob)

    dt_ms = round((time.time() - t0) * 1000.0, 1)
    return {
        "ok": True,
        "output_db0": str(output_db0),
        "file_count": len(files_to_pack),
        "size_bytes": output_db0.stat().st_size,
        "elapsed_ms": dt_ms,
        "files": [x[0].replace("\\", "/") for x in files_to_pack],
    }


VFS_MOUNT_DIR = CACHE_DIR / "vfs_mount"
_GLOBAL_VFS: Optional[AnomalyDb0VFS] = None


def get_vfs_mount_dir() -> Path:
    VFS_MOUNT_DIR.mkdir(parents=True, exist_ok=True)
    return VFS_MOUNT_DIR


def get_global_vfs(anomaly_path: Optional[str] = None, mo2_path: Optional[str] = None) -> AnomalyDb0VFS:
    global _GLOBAL_VFS
    if anomaly_path is None:
        from settings_service import load_settings
        st = load_settings()
        anomaly_path = st.get("anomaly_path", "")
        mo2_path = st.get("mo2_path", "")
    if _GLOBAL_VFS is None or _GLOBAL_VFS.anomaly_path != anomaly_path:
        _GLOBAL_VFS = AnomalyDb0VFS(anomaly_path, mo2_path or "")
        _GLOBAL_VFS.build_index(force_rescan=False)
        ensure_core_configs_mounted(_GLOBAL_VFS)
    return _GLOBAL_VFS


def ensure_core_configs_mounted(vfs: Optional[AnomalyDb0VFS] = None) -> Path:
    """
    Ensures configs/, scripts/, and ai/ are materialized from packed .db0 archives
    into .studio_cache/vfs_mount/ so all legacy & SDK 0.7 services work with zero
    dependency on any external `tools/_unpacked` directory.
    """
    mount = get_vfs_mount_dir()
    marker = mount / ".core_mounted_v1"
    if marker.is_file() and (mount / "configs" / "system.ltx").is_file():
        return mount
    if vfs is None:
        vfs = get_global_vfs()
    anom_db = Path(vfs.anomaly_path) / "db" / "configs"
    if not anom_db.is_dir():
        return mount
    count = 0
    for arc_name in ("configs.db0", "scripts.db0", "ai.db0", "files.db0"):
        arc = anom_db / arc_name
        if arc.is_file():
            for e in read_db0_toc(str(arc)):
                if e.size_real > 0:
                    dest = mount / e.vfs_path
                    if not dest.is_file():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(extract_db0_entry(e))
                    count += 1
    marker.write_text(f"mounted={count}\n", encoding="utf-8")
    return mount


def ensure_vfs_file(rel_path: str, vfs: Optional[AnomalyDb0VFS] = None) -> Path:
    """
    On-demand materializes a single file (e.g. `meshes/...`, `textures/...`, `levels/...`, `spawns/all.spawn`)
    from the packed .db0 archives into `.studio_cache/vfs_mount/<rel_path>` and returns its Path.
    """
    norm = normalize_vfs_path(rel_path)
    mount = get_vfs_mount_dir()
    dest = mount / norm
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    if vfs is None:
        vfs = get_global_vfs()
    entry = vfs.entries.get(norm)
    if entry and entry.size_real > 0:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(extract_db0_entry(entry))
    return dest


def ensure_vfs_level(level_id: str, vfs: Optional[AnomalyDb0VFS] = None) -> Path:
    """
    On-demand materializes all level files (`level`, `level.cform`, `level.ai`, `level.details`,
    `level.hom`, `level.snd_env`, `level.ps_static`, `level.ltx`) for `level_id` directly from
    the packed `db/levels/level_*.db0` archive into `.studio_cache/vfs_mount/levels/<level_id>/`.
    """
    mount = get_vfs_mount_dir()
    lvl_dir = mount / "levels" / level_id
    if (lvl_dir / "level.cform").is_file() and (lvl_dir / "level.ai").is_file() and (lvl_dir / "terrain").is_dir():
        return lvl_dir
    if vfs is None:
        vfs = get_global_vfs()
    prefix = f"levels/{level_id.lower()}/"
    for k, entry in vfs.entries.items():
        if k.startswith(prefix) and entry.size_real > 0:
            # Extract terrain/*.dds and build_details.dds, skip only lmap# lightmaps and level_lods
            if k.endswith(".dds") and ("/lmap#" in k or "level_lods" in k):
                continue
            dest = mount / k
            if not dest.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(extract_db0_entry(entry))
    return lvl_dir
