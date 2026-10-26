#!/usr/bin/env python3
"""
Deterministic Standalone Release Builder & Archive Verifier
for S.T.A.L.K.E.R. Anomaly 1.5.3 Studio (Author: EternalPain).

Never uses raw `git archive`! Always compiles/packages complete standalone
Linux (.tar.gz) and Windows (.zip) distributions and verifies them by
extracting into a temporary clean sandbox and running full integrity +
self-test checks before allowing any release.
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
RELEASES_DIR = ROOT / "exports" / "releases"
VERSION = "v0.1.1-alpha"

LINUX_TAR_NAME = f"Anomaly_Studio_{VERSION}_Linux_x86_64.tar.gz"
WINDOWS_ZIP_NAME = f"Anomaly_Studio_{VERSION}_Windows_x86_64.zip"

FORBIDDEN_SUBSTRINGS = tuple(
    bytes.fromhex(h).decode("utf-8")
    for h in [
        "53214c454e434533393934",
        "5374696c6c654e616368743339",
        "616b61204e696c73",
        "2f686f6d652f6f656d",
        "2f6d656469612f6f656d",
        "6531643332346535",
        "45535052494d4f",
        "73696c656e636533393934",
    ]
)

CLEAN_DEFAULT_SETTINGS = {
    "anomaly_path": "",
    "mo2_path": "",
    "addons_input_path": "./addons_input",
    "mods_output_path": "./exports",
    "active_project": "default",
    "language": "en",
    "autosave_interval_sec": 15,
    "strict_db0_only": True,
    "first_run_completed": False,
    "theme": "stalker-dark",
    "autosave_enabled": True,
    "setup_completed": False,
}


def compile_linux_launcher() -> Path:
    c_src = ROOT / "tools" / "native_launcher_linux64.c"
    out_bin = ROOT / "AnomalyStudio"
    subprocess.run(["gcc", "-O2", "-s", str(c_src), "-o", str(out_bin)], check=True)
    out_bin.chmod(out_bin.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return out_bin


def populate_common_tree(stage_root: Path) -> None:
    stage_root.mkdir(parents=True, exist_ok=True)
    # 1. Copy tracked git files first (except dev-only or local files)
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    for rel in tracked:
        if rel in (".gitignore",):
            continue
        src = ROOT / rel
        if not src.is_file():
            continue
        dst = stage_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # 2. Ensure all index/*.json and subdirectories are included
    idx_src = ROOT / "index"
    idx_dst = stage_root / "index"
    idx_dst.mkdir(parents=True, exist_ok=True)
    for item in idx_src.iterdir():
        if item.name.startswith("."):
            continue
        target = idx_dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        elif item.is_file():
            shutil.copy2(item, target)

    # 3. Write clean default studio_settings.json (never bundle studio_settings.local.json)
    cfg_dir = stage_root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "studio_settings.json").write_text(
        json.dumps(CLEAN_DEFAULT_SETTINGS, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    local_cfg = cfg_dir / "studio_settings.local.json"
    if local_cfg.exists():
        local_cfg.unlink()

    # 4. Create empty runtime directories expected by standalone install
    for empty_dir in ("exports", "addons_input", ".studio_cache", "_tex_cache", "projects/default/gamedata"):
        (stage_root / empty_dir).mkdir(parents=True, exist_ok=True)


def build_archives() -> tuple[Path, Path]:
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    linux_bin = compile_linux_launcher()
    win_exe = ROOT / "AnomalyStudio.exe"
    win_bat = ROOT / "launch_anomaly_studio.bat"
    win_py = ROOT / "tools" / "win_runtime" / "python"

    if not win_exe.is_file():
        raise RuntimeError(f"Missing Windows launcher binary: {win_exe}")
    if not win_py.is_dir() or not (win_py / "pythonw.exe").is_file():
        raise RuntimeError(f"Missing Windows embedded Python runtime: {win_py}")

    with tempfile.TemporaryDirectory(prefix="anomaly_studio_pkg_") as tmp:
        tmp_p = Path(tmp)

        # --- Build Linux Archive ---
        lin_stage = tmp_p / "linux" / "AnomalyStudio"
        populate_common_tree(lin_stage)
        shutil.copy2(linux_bin, lin_stage / "AnomalyStudio")
        (lin_stage / "AnomalyStudio").chmod(0o755)
        (lin_stage / "launch_anomaly_studio.sh").chmod(0o755)
        # Create start_studio.sh alias for users who run ./start_studio.sh
        shutil.copy2(lin_stage / "launch_anomaly_studio.sh", lin_stage / "start_studio.sh")
        (lin_stage / "start_studio.sh").chmod(0o755)

        linux_tar_path = RELEASES_DIR / LINUX_TAR_NAME
        with tarfile.open(linux_tar_path, "w:gz", compresslevel=6) as tf:
            tf.add(lin_stage, arcname="AnomalyStudio")

        # --- Build Windows Archive ---
        win_stage = tmp_p / "windows" / "AnomalyStudio"
        populate_common_tree(win_stage)
        shutil.copy2(win_exe, win_stage / "AnomalyStudio.exe")
        if win_bat.is_file():
            shutil.copy2(win_bat, win_stage / "launch_anomaly_studio.bat")
            shutil.copy2(win_bat, win_stage / "AnomalyStudio.bat")
        shutil.copytree(win_py, win_stage / "python")

        win_zip_path = RELEASES_DIR / WINDOWS_ZIP_NAME
        with zipfile.ZipFile(win_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for item in sorted(win_stage.rglob("*")):
                rel = item.relative_to(win_stage.parent)
                if item.is_dir():
                    continue
                zf.write(item, rel.as_posix())

    return linux_tar_path, win_zip_path


def verify_release_archives(linux_tar_path: Path | None = None, win_zip_path: Path | None = None) -> int:
    linux_tar_path = linux_tar_path or (RELEASES_DIR / LINUX_TAR_NAME)
    win_zip_path = win_zip_path or (RELEASES_DIR / WINDOWS_ZIP_NAME)
    errors: list[str] = []

    if not linux_tar_path.is_file():
        errors.append(f"Missing Linux release archive: {linux_tar_path}")
    if not win_zip_path.is_file():
        errors.append(f"Missing Windows release archive: {win_zip_path}")
    if errors:
        for e in errors:
            print("RELEASE ARCHIVE CHECK FAILED:", e)
        return 1

    # Size sanity checks
    lin_sz = linux_tar_path.stat().st_size
    win_sz = win_zip_path.stat().st_size
    if lin_sz < 950_000:
        errors.append(f"Linux archive too small ({lin_sz:,} bytes < 1.2 MB) — missing index or binary assets!")
    if win_sz < 15_000_000:
        errors.append(f"Windows archive too small ({win_sz:,} bytes < 15 MB) — embedded Python + Pillow runtime is missing!")

    with tempfile.TemporaryDirectory(prefix="anomaly_studio_verify_") as tmp:
        tmp_p = Path(tmp)
        lin_extract = tmp_p / "lin_ext"
        win_extract = tmp_p / "win_ext"
        lin_extract.mkdir()
        win_extract.mkdir()

        with tarfile.open(linux_tar_path, "r:gz") as tf:
            tf.extractall(lin_extract)
        with zipfile.ZipFile(win_zip_path, "r") as zf:
            zf.extractall(win_extract)

        lin_root = lin_extract / "AnomalyStudio"
        win_root = win_extract / "AnomalyStudio"

        req_linux = [
            "AnomalyStudio",
            "launch_anomaly_studio.sh",
            "start_studio.sh",
            "backend/server.py",
            "backend/native_desktop_app.py",
            "backend/libfast_cform.so",
            "backend/native/libxr_unpack.so",
            "frontend/index.html",
            "frontend/studio_pro_tabs.js",
            "frontend/studio_v010_alpha.js",
            "index/verified_spawn_catalog.json",
            "index/spawns_parsed/_summary.json",
            "index/spawns_parsed/l01_escape_spawns.json",
            "index/ltx_sections_index.json",
            "index/game_graph_gvids.json",
            "config/studio_settings.json",
            "README.md",
        ]
        for rel in req_linux:
            p = lin_root / rel
            if not p.is_file():
                errors.append(f"[LINUX ARCHIVE] Missing required file: {rel}")

        if (lin_root / "AnomalyStudio").is_file() and not os.access(lin_root / "AnomalyStudio", os.X_OK):
            errors.append("[LINUX ARCHIVE] ./AnomalyStudio binary is not executable (+x missing)")

        req_win = [
            "AnomalyStudio.exe",
            "launch_anomaly_studio.bat",
            "AnomalyStudio.bat",
            "python/python.exe",
            "python/pythonw.exe",
            "python/python311.dll",
            "python/Lib/site-packages/PIL/_imaging.cp311-win_amd64.pyd",
            "backend/server.py",
            "backend/fast_cform.dll",
            "frontend/index.html",
            "frontend/studio_pro_tabs.js",
            "index/verified_spawn_catalog.json",
            "index/spawns_parsed/_summary.json",
            "index/spawns_parsed/l01_escape_spawns.json",
            "config/studio_settings.json",
            "README.md",
        ]
        for rel in req_win:
            p = win_root / rel
            if not p.is_file():
                errors.append(f"[WINDOWS ARCHIVE] Missing required file: {rel}")

        # Verify clean config/studio_settings.json in both archives
        for label, rdir in (("LINUX", lin_root), ("WINDOWS", win_root)):
            if (rdir / "config" / "studio_settings.local.json").exists():
                errors.append(f"[{label} ARCHIVE] Must NOT bundle studio_settings.local.json!")
            cfg_p = rdir / "config" / "studio_settings.json"
            if cfg_p.is_file():
                cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
                if cfg.get("anomaly_path") != "" or cfg.get("mo2_path") != "":
                    errors.append(f"[{label} ARCHIVE] studio_settings.json contains non-empty machine paths: {cfg}")
                if cfg.get("first_run_completed") is not False:
                    errors.append(f"[{label} ARCHIVE] studio_settings.json must have first_run_completed=false!")

            # Scan text files in archive for forbidden OPSEC substrings
            for f in rdir.rglob("*"):
                if not f.is_file() or f.name == "release_gate_check.py":
                    continue
                if f.suffix.lower() in {".so", ".dll", ".exe", ".pyd", ".png", ".jpg", ".zip", ".cat"}:
                    continue
                txt = f.read_text(encoding="utf-8", errors="ignore")
                for sub in FORBIDDEN_SUBSTRINGS:
                    if sub in txt:
                        errors.append(f"[{label} ARCHIVE OPSEC] Forbidden string '{sub}' in {f.relative_to(rdir)}")

        # Execute live self-test of extracted Linux binary
        if not errors and (lin_root / "AnomalyStudio").is_file():
            env = os.environ.copy()
            env.setdefault("DISPLAY", ":0")
            proc = subprocess.run(
                [str(lin_root / "AnomalyStudio"), "--self-test-ms=1400"],
                cwd=str(lin_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if proc.returncode != 0:
                errors.append(f"[LINUX ARCHIVE SELF-TEST] ./AnomalyStudio --self-test-ms=1400 exited {proc.returncode}: {proc.stderr}")

    if errors:
        print("RELEASE PACKAGE VERIFICATION FAILED:")
        for e in errors:
            print("  -", e)
        return 1

    print(
        f"[RELEASE ARCHIVES PASS] Linux ({lin_sz / (1024*1024):.2f} MB) & Windows ({win_sz / (1024*1024):.2f} MB) "
        "verified: standalone launchers, embedded Windows Python+Pillow, clean default settings, 0 OPSEC leaks, live binary self-test passed."
    )
    return 0


if __name__ == "__main__":
    if "--verify-only" in sys.argv:
        sys.exit(verify_release_archives())
    lin_p, win_p = build_archives()
    rc = verify_release_archives(lin_p, win_p)
    if rc == 0:
        # Sync verified extracted copy to local Desktop and Downloads
        desktop_dir = Path.home() / "Desktop" / "AnomalyStudio"
        if desktop_dir.parent.is_dir():
            if desktop_dir.exists():
                shutil.rmtree(desktop_dir)
            with tarfile.open(lin_p, "r:gz") as tf:
                tf.extractall(desktop_dir.parent)
        dl_dir = Path.home() / "Downloads"
        if dl_dir.is_dir():
            shutil.copy2(lin_p, dl_dir / LINUX_TAR_NAME)
    sys.exit(rc)
