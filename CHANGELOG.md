# Changelog — S.T.A.L.K.E.R. Anomaly 1.5.3 Studio

All notable changes to this project are documented in this file.
**Author / Maintainer**: `EternalPain`

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
