# Changelog — S.T.A.L.K.E.R. Anomaly 1.5.3 Studio

All notable changes to this project are documented in this file.
**Author / Maintainer**: `EternalPain`

---

## [v0.1.1-alpha] — 2026-10-26 (Hotfix & Standalone Packaging Update)

### Fixed
- **3D Map & Level Loader Crash on Fresh Standalone Installs (`frontend/index.html` & `backend/server.py`)**:
  - Fixed a `TypeError` in `renderLevelList()` and `filterLevels()` when `overviewData.spawns_summary.levels` was undefined on freshly extracted installations, which previously prevented the 34 levels and the 3D viewport from initializing.
  - Bundled all 70 pre-indexed S.T.A.L.K.E.R. Anomaly 1.5.3 level spawn and patrol tables (`index/spawns_parsed/`) directly into the standalone Linux and Windows release packages so all 18,652 base-game spawns load out of the box.
  - Fixed `currentPatrols` normalization in `loadLevel3D()` so both dictionary and array patrol structures render cleanly without blocking spawn marker creation.
- **3D Viewport Streaming & `level.geom` Memory Optimization (`backend/server.py` & `frontend/index.html`)**:
  - Filtered redundant multi-LOD SpeedTree instances (`mtype 7/11`) out of the static building/prop `level.geom` payload (`load_level_geom_binary_payload()`), reducing `l01_escape` static geometry transfer size from `222 MB` to `57 MB` (`~800 ms`).
  - Converted 2048x2048 terrain splat (`terrain_splat`) and building texture atlas (`level_geom_atlas`) loading in `loadLevel3D()` to non-blocking asynchronous streaming so CFORM collision meshes, static buildings, AI NavMesh nodes, and level spawns appear immediately (`< 1.5s`).
  - Deferred initial background `.ogf` preview loading in `initApp()` so startup prioritizes the level list and active workspace.
- **Standalone Release Packaging & Local Config Isolation (`cli/build_releases.py`, `cli/release_gate_check.py`, `backend/settings_service.py`)**:
  - Replaced `git archive` packaging with deterministic release builder `cli/build_releases.py` + Stage 11 release archive verification (`verify_release_archives()`).
  - Linux (`Anomaly_Studio_v0.1.1-alpha_Linux_x86_64.tar.gz`) and Windows (`Anomaly_Studio_v0.1.1-alpha_Windows_x86_64.zip`) archives now include compiled native launchers (`./AnomalyStudio`, `start_studio.sh`, `AnomalyStudio.exe`, `AnomalyStudio.bat`) and the embedded Windows Python 3.11 + Pillow runtime (`python/`).
  - Separated runtime machine settings into git-ignored `config/studio_settings.local.json` so release archives always ship with a clean default `config/studio_settings.json` (`first_run_completed: false`).

---

## [v0.1.0-alpha] — 2026-10-26 (Early Alpha / Tech Demo)

> **Note**: `v0.1.0-alpha` is an **early Alpha and Technical Preview (Tech Demo)** for **S.T.A.L.K.E.R. Anomaly 1.5.3 (64-bit Monolith Engine)**.

### Added
- **Direct `.db0` Virtual File System (`backend/db0_vfs.py` & `cli/anomaly_db_tool.py`)**:
  - Mounts all 68 S.T.A.L.K.E.R. Anomaly 1.5.3 `.db0` archives directly from the game directory in read-only mode without requiring an unpacked `gamedata/` folder.
  - Standalone `.db0` archive packer and Mod Organizer 2 (`.zip`) exporter.
- **First-Launch Path Setup & Workspace Manager (`backend/settings_service.py` & `backend/project_service.py`)**:
  - Configures and remembers Anomaly 1.5.3 root path, Mod Organizer 2 directory, Addons Input folder, and Mods Output folder, plus `.anomaly` project files.
- **Tab 1 — Story, Dialog & Quest Builder**:
  - Visual node-graph editor with drag-and-drop wire connections, single-click wire disconnect, `24px` grid snap, and hierarchical auto-layout.
  - Resizable Quest/Dialog Inspector, pre-flight syntax & softlock checks, Quest Logic Guide, and 1-Click 3D Quest Target coordinate picker (`LVID` / `GVID`).
- **Tab 2 — 3D World & Object Placement Preview**:
  - Hardware-accelerated 3D level viewer with native C acceleration (`libfast_cform`) for `level.cform`, `level + level.geom`, 3D trees, `level.ai`, and `level.spawn`.
  - Progressive `.ogf` entity model loading and individual static 3D world object selection on `Left-Click`.
  - 3D Transform Gizmo (`Move`, `Rotate`, `Scale`, `Place`) with `Snap to Ground (G)`, `Surface Normal Alignment (N)`, `Grid Snap`, and automated `alife_create` Lua spawn script generation.
- **Tab 3 & Tab 4 — `.OGF` Viewer, Pre-Flight Check & `.db0` Packer**:
  - Direct `.db0` `.ogf` model browser with `.dds` texture decoding, pre-flight spawn/config validation, bottom diagnostic console, `Ctrl+Z` / `Ctrl+Y` Undo/Redo, and crash-recovery autosave.
