#!/usr/bin/env python3
"""
Anomaly Studio v0.1.0-alpha — Persistent Settings, Path Setup Wizard & MO2/Addon Importer (EN + RU)
====================================================================================================
Author / Credits: EternalPain
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List

STUDIO_ROOT = (
    Path(os.environ["ANOMALY_STUDIO_ROOT"]).resolve()
    if os.environ.get("ANOMALY_STUDIO_ROOT")
    else (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent)
)
CONFIG_DIR = STUDIO_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "studio_settings.json"
CACHE_DIR = STUDIO_ROOT / ".studio_cache"
PROJECTS_DIR = STUDIO_ROOT / "projects"
EXPORTS_DIR = STUDIO_ROOT / "exports"
ADDONS_INPUT_DIR = STUDIO_ROOT / "addons_input"


def auto_detect_paths() -> Dict[str, str]:
    """Scans common user directories to pre-fill Anomaly 1.5.3, MO2, Addons Input, and Mods Output paths on first start."""
    home = Path.home()
    anom_candidates = [
        home / "Downloads" / "Anomaly-1.5.3-Full.2",
        home / "Games" / "Anomaly",
        home / "Anomaly",
        Path.home() / "Games" / "Anomaly",
        Path("C:/Games/Anomaly"),
        Path("D:/Games/Anomaly"),
    ]
    mo2_candidates = [
        home / "Downloads" / "Mod.Organizer-2.5.2",
        home / "Games" / "MO2",
        home / "ModOrganizer2",
        Path("C:/Modding/MO2"),
    ]
    detected_anom = ""
    for c in anom_candidates:
        if c.is_dir() and (c / "db").is_dir():
            detected_anom = str(c)
            break
    detected_mo2 = ""
    for c in mo2_candidates:
        if c.is_dir() and ((c / "mods").is_dir() or (c / "ModOrganizer.exe").is_file()):
            detected_mo2 = str(c)
            break
    default_input = str(( Path(detected_mo2) / "mods" ) if (detected_mo2 and (Path(detected_mo2) / "mods").is_dir()) else ADDONS_INPUT_DIR)
    default_output = str(EXPORTS_DIR)
    return {
        "anomaly_path": detected_anom,
        "mo2_path": detected_mo2,
        "addons_input_path": default_input,
        "mods_output_path": default_output,
    }


DEFAULT_SETTINGS: Dict[str, Any] = {
    "anomaly_path": "",
    "mo2_path": "",
    "addons_input_path": str(ADDONS_INPUT_DIR),
    "mods_output_path": str(EXPORTS_DIR),
    "active_project": "default",
    "language": "en",
    "autosave_interval_sec": 15,
    "strict_db0_only": True,
    "first_run_completed": False,
}


def ensure_dirs() -> None:
    for d in (CONFIG_DIR, CACHE_DIR, PROJECTS_DIR, EXPORTS_DIR, ADDONS_INPUT_DIR, PROJECTS_DIR / "default" / "gamedata"):
        d.mkdir(parents=True, exist_ok=True)


def load_settings() -> Dict[str, Any]:
    ensure_dirs()
    detected = auto_detect_paths()
    data = dict(DEFAULT_SETTINGS)
    for k, v in detected.items():
        if v:
            data[k] = v
    file_existed = SETTINGS_FILE.is_file()
    if file_existed:
        try:
            loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    if k in ("anomaly_path", "mo2_path", "addons_input_path", "mods_output_path") and not v:
                        continue
                    data[k] = v
                if "first_run_completed" in loaded:
                    data["first_run_completed"] = bool(loaded["first_run_completed"])
                elif "setup_completed" in loaded:
                    data["first_run_completed"] = bool(loaded["setup_completed"])
                else:
                    data["first_run_completed"] = False
        except Exception:
            pass
    else:
        data["first_run_completed"] = False
    if not data.get("addons_input_path"):
        data["addons_input_path"] = detected.get("addons_input_path") or str(ADDONS_INPUT_DIR)
    if not data.get("mods_output_path"):
        data["mods_output_path"] = str(EXPORTS_DIR)
    if data.get("language") not in ("en", "ru"):
        data["language"] = "en"
    return data


def _normalize_anomaly_root(raw_path: str) -> str:
    if not raw_path:
        return ""
    p = Path(raw_path).expanduser()
    if p.is_file():
        p = p.parent
    # Walk up ancestors if the user selected db/, db/configs/, db/levels/, bin/, gamedata/, etc.
    for anc in [p] + list(p.parents)[:4]:
        if (anc / "db").is_dir() and any((anc / "db").rglob("*.db*")):
            return str(anc)
    # Check immediate child folders if user selected a parent directory like Downloads/
    if p.is_dir():
        for sub in (p / "Anomaly-1.5.3-Full.2", p / "Anomaly"):
            if sub.is_dir() and (sub / "db").is_dir():
                return str(sub)
        try:
            for child in sorted(p.iterdir()):
                if child.is_dir() and (child / "db").is_dir() and any((child / "db").rglob("*.db*")):
                    return str(child)
        except Exception:
            pass
    return str(p)


def validate_paths(
    anomaly_path: str,
    mo2_path: str,
    addons_input_path: str = "",
    mods_output_path: str = "",
) -> Dict[str, Any]:
    anomaly_path = _normalize_anomaly_root(anomaly_path)
    anom_p = Path(anomaly_path).expanduser() if anomaly_path else Path("")
    mo2_p = Path(mo2_path).expanduser() if mo2_path else Path("")
    in_p = Path(addons_input_path).expanduser() if addons_input_path else ADDONS_INPUT_DIR
    out_p = Path(mods_output_path).expanduser() if mods_output_path else EXPORTS_DIR

    anom_db = anom_p / "db"
    db0_files = list(anom_db.rglob("*.db*")) if anom_db.is_dir() else []
    anom_valid = anom_p.is_dir() and anom_db.is_dir() and len(db0_files) > 0

    mo2_mods = mo2_p / "mods" if (mo2_p / "mods").is_dir() else (mo2_p if mo2_p.is_dir() else None)
    mo2_valid = mo2_p.is_dir() and (
        (mo2_p / "ModOrganizer.exe").is_file()
        or (mo2_p / "mods").is_dir()
        or mo2_p.name.lower() == "mods"
    )
    mo2_mod_count = 0
    if mo2_mods and mo2_mods.is_dir():
        mo2_mod_count = sum(1 for x in mo2_mods.iterdir() if x.is_dir() and not x.name.startswith("."))

    try:
        in_p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        out_p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    input_valid = in_p.is_dir()
    output_valid = out_p.is_dir() and os.access(str(out_p), os.W_OK)

    return {
        "anomaly_path": str(anom_p) if anomaly_path else "",
        "anomaly_valid": anom_valid,
        "anomaly_db_dir": str(anom_db) if anom_db.is_dir() else "",
        "anomaly_db0_count": len(db0_files),
        "db0_count": len(db0_files),
        "mo2_path": str(mo2_p) if mo2_path else "",
        "mo2_valid": mo2_valid,
        "mo2_mods_dir": str(mo2_mods) if mo2_mods else "",
        "mo2_mod_count": mo2_mod_count,
        "mo2_mods_Count": mo2_mod_count,
        "addons_input_path": str(in_p),
        "addons_input_valid": input_valid,
        "addons_input_count": sum(1 for x in in_p.iterdir() if not x.name.startswith(".")) if in_p.is_dir() else 0,
        "mods_output_path": str(out_p),
        "mods_output_valid": output_valid,
    }


def save_settings(updates: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    updates = dict(updates or {})
    updates.update(kwargs)
    current = load_settings()
    if updates.get("auto_detect"):
        for dk, dv in auto_detect_paths().items():
            if dv:
                current[dk] = dv
    for k in (
        "anomaly_path",
        "mo2_path",
        "addons_input_path",
        "mods_output_path",
        "active_project",
        "language",
        "autosave_interval_sec",
        "strict_db0_only",
        "first_run_completed",
    ):
        if k in updates and updates[k] is not None:
            current[k] = updates[k]
    if current.get("anomaly_path"):
        current["anomaly_path"] = _normalize_anomaly_root(str(current["anomaly_path"]))
    elif auto_detect_paths().get("anomaly_path"):
        current["anomaly_path"] = auto_detect_paths()["anomaly_path"]
    if current.get("anomaly_path"):
        current["first_run_completed"] = True
    if current.get("language") not in ("en", "ru"):
        current["language"] = "en"
    SETTINGS_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    val = validate_paths(
        current.get("anomaly_path", ""),
        current.get("mo2_path", ""),
        current.get("addons_input_path", ""),
        current.get("mods_output_path", ""),
    )
    return {"ok": True, "settings": current, "validation": val}


def browse_directory_dialog(title: str = "Select Directory", initial_dir: str = "") -> Dict[str, Any]:
    """Opens a native OS folder selection dialog on Windows (WinForms FolderBrowserDialog) and Linux (zenity/kdialog/tkinter)."""
    init_p = str(Path(initial_dir).expanduser()) if initial_dir and Path(initial_dir).expanduser().is_dir() else str(Path.home())
    if os.name == "nt":
        try:
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
                f"$f.Description = {json.dumps(title)}; "
                f"$f.SelectedPath = {json.dumps(init_p)}; "
                "$f.ShowNewFolderButton = $true; "
                "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=120,
            )
            chosen = (res.stdout or "").strip()
            if chosen:
                return {"ok": True, "path": chosen}
            return {"ok": False, "cancelled": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    env = os.environ.copy()
    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":0"
    if shutil.which("zenity"):
        try:
            res = subprocess.run(
                ["zenity", "--file-selection", "--directory", f"--title={title}", f"--filename={init_p}/"],
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if res.returncode == 0 and res.stdout.strip():
                return {"ok": True, "path": res.stdout.strip()}
            return {"ok": False, "cancelled": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askdirectory(title=title, initialdir=init_p)
        root.destroy()
        if selected:
            return {"ok": True, "path": selected}
        return {"ok": False, "cancelled": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_importable_mods() -> Dict[str, Any]:
    """
    Lists all importable mods from:
    1. Mod Organizer 2 `mods/` folder (`mo2_path/mods/*`)
    2. Configured `addons_input_path` (folders, `.zip`, `.db0`)
    """
    st = load_settings()
    val = validate_paths(
        st.get("anomaly_path", ""),
        st.get("mo2_path", ""),
        st.get("addons_input_path", ""),
        st.get("mods_output_path", ""),
    )
    mods: List[Dict[str, Any]] = []
    seen_paths = set()

    def _scan_dir(base_dir: Path, source_tag: str) -> None:
        if not base_dir or not base_dir.is_dir():
            return
        for item in sorted(base_dir.iterdir(), key=lambda p: p.name.lower()):
            if item.name.startswith("."):
                continue
            rp = str(item.resolve())
            if rp in seen_paths:
                continue
            seen_paths.add(rp)
            if item.is_dir():
                gd = item / "gamedata" if (item / "gamedata").is_dir() else item
                files_count = sum(1 for f in gd.rglob("*") if f.is_file() and not f.name.startswith("."))
                has_ltx = any(gd.rglob("*.ltx"))
                has_scripts = any(gd.rglob("*.script"))
                has_ogf = any(gd.rglob("*.ogf"))
                mods.append({
                    "name": item.name,
                    "source": source_tag,
                    "type": "folder",
                    "path": str(item),
                    "files_count": files_count,
                    "tags": [t for t, cond in [("LTX", has_ltx), ("Lua", has_scripts), ("3D/OGF", has_ogf)] if cond],
                })
            elif item.is_file() and item.suffix.lower() in (".zip", ".db0", ".db"):
                mods.append({
                    "name": item.name,
                    "source": source_tag,
                    "type": item.suffix.lower().lstrip("."),
                    "path": str(item),
                    "size_bytes": item.stat().st_size,
                    "tags": [item.suffix.upper().lstrip(".")],
                })

    if val.get("mo2_mods_dir"):
        _scan_dir(Path(val["mo2_mods_dir"]), "MO2")
    if val.get("addons_input_path"):
        _scan_dir(Path(val["addons_input_path"]), "Addons Input")

    return {
        "ok": True,
        "count": len(mods),
        "mods": mods,
        "mo2_mods_dir": val.get("mo2_mods_dir", ""),
        "addons_input_path": val.get("addons_input_path", ""),
        "mods_output_path": val.get("mods_output_path", ""),
    }


def import_mod_into_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Imports an existing MO2 mod or Addon (folder, .zip, or .db0) into a Studio project's `gamedata/`
    workspace (either into the currently active project or as a newly created project).
    """
    import project_service
    import v010_core_service
    import db0_vfs

    mod_path_str = (payload.get("mod_path") or "").strip()
    if not mod_path_str:
        return {"ok": False, "error": "Missing mod_path"}
    src = Path(mod_path_str).expanduser().resolve()
    if not src.exists():
        return {"ok": False, "error": f"Mod path not found: {src}"}

    create_new = bool(payload.get("create_new_project", False))
    st = load_settings()
    if create_new:
        proj_id = project_service.sanitize_project_id(src.stem)
        project_service.create_project({
            "project_id": proj_id,
            "title": src.stem.replace("_", " "),
            "description": f"Imported from {src}",
        })
    else:
        proj_id = project_service.sanitize_project_id(payload.get("project_id") or st.get("active_project") or "default")

    dest_gamedata = PROJECTS_DIR / proj_id / "gamedata"
    dest_gamedata.mkdir(parents=True, exist_ok=True)
    copied_files: List[str] = []

    if src.is_dir():
        src_root = src / "gamedata" if (src / "gamedata").is_dir() else src
        for f in sorted(src_root.rglob("*")):
            if f.is_file() and not f.name.startswith(".") and f.name != "meta.ini":
                rel = f.relative_to(src_root)
                target = dest_gamedata / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
                copied_files.append(rel.as_posix())
    elif src.is_file() and src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src, "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                norm = member.filename.replace("\\", "/").lstrip("/")
                if norm.lower().startswith("gamedata/"):
                    norm = norm[len("gamedata/"):]
                if not norm or norm.startswith(".") or norm == "meta.ini":
                    continue
                target = (dest_gamedata / norm).resolve()
                if str(target).startswith(str(dest_gamedata.resolve())):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(member))
                    copied_files.append(norm)
    elif src.is_file() and src.suffix.lower().startswith(".db"):
        entries = db0_vfs.read_db0_toc(str(src))
        for e in entries:
            if e.size_real > 0:
                target = (dest_gamedata / e.vfs_path).resolve()
                if str(target).startswith(str(dest_gamedata.resolve())):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(db0_vfs.extract_db0_entry(e))
                    copied_files.append(e.vfs_path)
    else:
        return {"ok": False, "error": f"Unsupported mod format: {src}"}

    v010_core_service.append_log(
        "INFO",
        f"Imported mod '{src.name}' -> project '{proj_id}' ({len(copied_files)} files copied into gamedata/).",
        f"Импортирован мод '{src.name}' -> проект '{proj_id}' ({len(copied_files)} файлов скопировано в gamedata/).",
        category="mod_import",
    )
    return {
        "ok": True,
        "project_id": proj_id,
        "source_name": src.name,
        "source_mod_name": src.name,
        "imported_count": len(copied_files),
        "copied_files": len(copied_files),
        "sample_files": copied_files[:25],
    }


def list_filesystem_dirs(current_path: str = "") -> Dict[str, Any]:
    """
    Cross-platform directory browser API (works identically on Windows C:\\/D:\\, Linux /, and macOS
    inside both the Native Zero-Socket Desktop App and the Web Edition).
    """
    is_win = os.name == "nt"
    roots: List[str] = []
    if is_win:
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drv = f"{letter}:\\"
            if Path(drv).is_dir():
                roots.append(drv)
    else:
        roots = [str(Path.home()), "/media", "/mnt", "/"]

    target = Path(current_path).expanduser() if current_path else Path.home()
    if not target.is_dir():
        target = Path.home()
    target = target.resolve()

    subdirs: List[Dict[str, Any]] = []
    try:
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir() and not child.name.startswith("."):
                has_db0 = (child / "db").is_dir()
                has_mo2 = (child / "mods").is_dir() or (child / "ModOrganizer.exe").is_file()
                subdirs.append({
                    "name": child.name,
                    "path": str(child),
                    "is_anomaly_candidate": has_db0,
                    "is_mo2_candidate": has_mo2,
                })
    except Exception:
        pass

    parent = str(target.parent) if target.parent != target else str(target)
    return {
        "ok": True,
        "platform": "windows" if is_win else sys.platform,
        "current_path": str(target),
        "parent_path": parent,
        "roots": roots,
        "subdirs": subdirs[:250],
    }
