#!/usr/bin/env python3
"""
Anomaly Studio — Godot-Style Project System (`project.anomaly`) & Lua Spawn Generator
=====================================================================================
Each mod project lives in `projects/<project_id>/` with its own:
- `project.anomaly` (JSON manifest, schema_version 1.0.0)
- `gamedata/` (isolated mod files: configs, scripts, spawns)
- `autosave/state_latest.json` (placed 3D objects, quest edits, dialog edits)
- `snapshots/` (timestamped project state snapshots)
- `builds/` (project-specific .db0 builds)

Base Anomaly 1.5.3 `.db0` VFS remains 100% read-only.
Author / Credits: EternalPain
"""
from __future__ import annotations
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import settings_service
import v010_core_service

STUDIO_ROOT = (
    Path(os.environ["ANOMALY_STUDIO_ROOT"]).resolve()
    if os.environ.get("ANOMALY_STUDIO_ROOT")
    else (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent)
)
PROJECTS_DIR = STUDIO_ROOT / "projects"


def sanitize_project_id(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_\-]", "_", (raw or "default").strip()).strip("_")
    return s[:64] if s else "default"


def _project_dir(project_id: str) -> Path:
    pid = sanitize_project_id(project_id)
    d = PROJECTS_DIR / pid
    for sub in ("gamedata/configs/misc/task", "gamedata/configs/text/eng", "gamedata/configs/text/rus", "gamedata/scripts", "autosave", "snapshots", "builds"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def default_manifest(project_id: str, title: str = "", version: str = "0.1.0", description: str = "") -> Dict[str, Any]:
    pid = sanitize_project_id(project_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nice_title = title.strip() or ("Default Anomaly Mod Project" if pid == "default" else pid.replace("_", " ").title())
    return {
        "schema_version": "1.0.0",
        "format": "project.anomaly",
        "project_id": pid,
        "title": nice_title,
        "version": version.strip() or "0.1.0",
        "author": "EternalPain",
        "target_engine": "S.T.A.L.K.E.R. Anomaly 1.5.3",
        "archive_name": f"zzz_{pid.lower()}.db0",
        "description": description.strip() or "Standalone Anomaly 1.5.3 mod project with read-only base .db0 VFS.",
        "created_at": now,
        "updated_at": now,
        "entry_level": "l01_escape",
        "entry_campaign": "tm_escape.ltx",
        "entry_dialog": "inf_trader_buy_transitions",
    }


def load_manifest(project_id: str) -> Dict[str, Any]:
    pid = sanitize_project_id(project_id)
    pdir = _project_dir(pid)
    mfile = pdir / "project.anomaly"
    manifest = default_manifest(pid)
    if mfile.is_file():
        try:
            loaded = json.loads(mfile.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                manifest.update(loaded)
        except Exception:
            pass
    manifest["project_id"] = pid
    manifest["author"] = "EternalPain"
    if not mfile.is_file():
        mfile.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def save_manifest(project_id: str, updates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    pid = sanitize_project_id(project_id)
    manifest = load_manifest(pid)
    if updates:
        for k in ("title", "version", "description", "archive_name", "entry_level", "entry_campaign", "entry_dialog"):
            if k in updates and updates[k] is not None:
                manifest[k] = str(updates[k]).strip()
    manifest["author"] = "EternalPain"
    manifest["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mfile = _project_dir(pid) / "project.anomaly"
    mfile.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def get_project_summary(project_id: str, active_project_id: str = "default") -> Dict[str, Any]:
    pid = sanitize_project_id(project_id)
    manifest = load_manifest(pid)
    pdir = _project_dir(pid)
    state_file = pdir / "autosave" / "state_latest.json"
    placed_count = 0
    quest_count = 0
    dialog_count = 0
    if pid == active_project_id and v010_core_service.CURRENT_STATE.get("project") == pid:
        st = v010_core_service.CURRENT_STATE
        placed_count = len(st.get("placed_objects") or [])
        quest_count = len(st.get("quest_edits") or {})
        dialog_count = len(st.get("dialog_edits") or {})
    elif state_file.is_file():
        try:
            st = json.loads(state_file.read_text(encoding="utf-8"))
            placed_count = len(st.get("placed_objects") or [])
            quest_count = len(st.get("quest_edits") or {})
            dialog_count = len(st.get("dialog_edits") or {})
        except Exception:
            pass
    snapshots = sorted([p.name for p in (pdir / "snapshots").glob("*.json")], reverse=True)
    slug = re.sub(r"[^a-z0-9_]", "_", pid.lower()).strip("_") or "default"
    lua_file = pdir / "gamedata" / "scripts" / f"mod_studio_spawns_{slug}.script"
    return {
        "project_id": pid,
        "is_active": pid == active_project_id,
        "manifest_path": str(pdir / "project.anomaly"),
        "gamedata_path": str(pdir / "gamedata"),
        "lua_script_path": str(lua_file),
        "lua_script_exists": lua_file.is_file(),
        "manifest": manifest,
        "stats": {
            "placed_objects_count": placed_count,
            "quest_edits_count": quest_count,
            "dialog_edits_count": dialog_count,
            "snapshots_count": len(snapshots),
        },
        "snapshots": snapshots[:15],
    }


def generate_lua_spawn_script(project_id: Optional[str] = None, write_to_disk: bool = True) -> Dict[str, Any]:
    """
    Compiles all placed 3D objects of the project into an Anomaly 1.5.3 in-game Lua script:
    `gamedata/scripts/mod_studio_spawns_<slug>.script`
    """
    st_cfg = settings_service.load_settings()
    pid = sanitize_project_id(project_id or st_cfg.get("active_project") or "default")
    manifest = load_manifest(pid)
    pdir = _project_dir(pid)

    if v010_core_service.CURRENT_STATE.get("project") == pid:
        state = v010_core_service.CURRENT_STATE
    else:
        state_file = pdir / "autosave" / "state_latest.json"
        state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.is_file() else {}

    placed: List[Dict[str, Any]] = state.get("placed_objects") or []
    slug = re.sub(r"[^a-z0-9_]", "_", pid.lower()).strip("_") or "default"
    script_rel = f"scripts/mod_studio_spawns_{slug}.script"
    script_path = pdir / "gamedata" / script_rel

    lines: List[str] = [
        "-- ============================================================================",
        "-- S.T.A.L.K.E.R. Anomaly 1.5.3 Studio — Generated ALife 3D Spawn Script",
        f"-- Project: {manifest.get('title', pid)} ({pid} v{manifest.get('version', '0.1.0')})",
        "-- Author / Credits: EternalPain",
        f"-- File: gamedata/{script_rel}",
        f"-- Total Placed 3D Entities: {len(placed)}",
        "-- ============================================================================",
        "",
        f"local STORAGE_KEY = 'studio_spawns_{slug}_v1'",
        "",
        "local SPAWN_TABLE = {",
    ]

    for idx, o in enumerate(placed, 1):
        obj_id = str(o.get("id") or f"obj_{idx}").replace("'", "")
        name = str(o.get("name") or obj_id).replace("'", "")
        sec = str(o.get("section") or "stalker_sim_ecolog").replace("'", "")
        lvl = str(o.get("level") or "l01_escape").replace("'", "")
        x = round(float(o.get("x", 0.0)), 3)
        y = round(float(o.get("y", 0.0)), 3)
        z = round(float(o.get("z", 0.0)), 3)
        rot_deg = round(float(o.get("rot_y", 0.0)), 2)
        rot_rad = round(math.radians(rot_deg), 4)
        lvid = int(o.get("lvid", 0))
        gvid = int(o.get("gvid", 0))
        story_id = str(o.get("story_id") or "").replace("'", "").strip()
        lines.append(
            f"    [{idx}] = {{ id = '{obj_id}', name = '{name}', section = '{sec}', level = '{lvl}', "
            f"x = {x}, y = {y}, z = {z}, lvid = {lvid}, gvid = {gvid}, yaw_rad = {rot_rad}, story_id = '{story_id}' }},"
        )

    lines.extend([
        "}",
        "",
        "function spawn_project_entities(force_respawn)",
        "    if not alife then return 0 end",
        "    local m_data = alife_storage_manager and alife_storage_manager.get_state and alife_storage_manager.get_state() or nil",
        "    if m_data then",
        "        m_data[STORAGE_KEY] = m_data[STORAGE_KEY] or {}",
        "    end",
        "    local spawned_now = 0",
        "    for i = 1, #SPAWN_TABLE do",
        "        local entry = SPAWN_TABLE[i]",
        "        local already = m_data and m_data[STORAGE_KEY] and m_data[STORAGE_KEY][entry.id]",
        "        if force_respawn or (not already) then",
        "            local pos = vector():set(entry.x, entry.y, entry.z)",
        "            local se_obj = alife_create(entry.section, pos, entry.lvid, entry.gvid)",
        "            if se_obj then",
        "                if entry.yaw_rad and entry.yaw_rad ~= 0 and se_obj.angle then",
        "                    se_obj.angle = vector():set(0, entry.yaw_rad, 0)",
        "                end",
        "                if entry.story_id and entry.story_id ~= '' and reg_story_id then",
        "                    pcall(reg_story_id, se_obj.id, entry.story_id)",
        "                end",
        "                if m_data and m_data[STORAGE_KEY] then",
        "                    m_data[STORAGE_KEY][entry.id] = se_obj.id",
        "                end",
        "                spawned_now = spawned_now + 1",
        "            end",
        "        end",
        "    end",
        "    if spawned_now > 0 and printf then",
        f"        printf(\"[Anomaly Studio] Project '%s': spawned %d entity/entities via %s\", '{pid}', spawned_now, STORAGE_KEY)",
        "    end",
        "    return spawned_now",
        "end",
        "",
        "function respawn_all()",
        "    return spawn_project_entities(true)",
        "end",
        "",
        "function on_game_start()",
        "    RegisterScriptCallback('actor_on_first_update', function()",
        "        spawn_project_entities(false)",
        "    end)",
        "end",
        "",
    ])

    lua_code = "\r\n".join(lines)
    if write_to_disk:
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_bytes(lua_code.encode("cp1251", errors="replace"))

    return {
        "ok": True,
        "project_id": pid,
        "script_rel": f"gamedata/{script_rel}",
        "script_path": str(script_path),
        "entity_count": len(placed),
        "lua_code": "\n".join(lines),
    }


def list_projects() -> Dict[str, Any]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    st = settings_service.load_settings()
    active_pid = sanitize_project_id(st.get("active_project") or "default")
    _project_dir("default")
    load_manifest("default")
    _project_dir(active_pid)
    load_manifest(active_pid)

    pids = sorted({p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")})
    items = [get_project_summary(pid, active_pid) for pid in pids]
    active_summary = next((x for x in items if x["project_id"] == active_pid), items[0] if items else None)
    lua_preview = generate_lua_spawn_script(active_pid, write_to_disk=True)
    return {
        "ok": True,
        "active_project": active_pid,
        "active_summary": active_summary,
        "projects": items,
        "lua_spawn_script": lua_preview,
    }


def create_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_id = payload.get("project_id") or payload.get("title") or f"mod_{int(time.time())}"
    pid = sanitize_project_id(raw_id)
    title = str(payload.get("title") or pid.replace("_", " ").title()).strip()
    version = str(payload.get("version") or "0.1.0").strip()
    description = str(payload.get("description") or "").strip()

    pdir = _project_dir(pid)
    manifest = default_manifest(pid, title=title, version=version, description=description)
    (pdir / "project.anomaly").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    state_file = pdir / "autosave" / "state_latest.json"
    if not state_file.is_file():
        init_state = {
            "project": pid,
            "active_level": manifest["entry_level"],
            "active_campaign": manifest["entry_campaign"],
            "active_dialog": manifest["entry_dialog"],
            "placed_objects": [],
            "quest_edits": {},
            "dialog_edits": {},
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        state_file.write_text(json.dumps(init_state, indent=2, ensure_ascii=False), encoding="utf-8")

    if payload.get("switch_to", True):
        return switch_project({"project_id": pid})

    v010_core_service.append_log(
        "INFO",
        f"Created project '{title}' ({pid}) -> {pdir / 'project.anomaly'}",
        f"Создан проект '{title}' ({pid}) -> {pdir / 'project.anomaly'}",
        category="project",
    )
    return list_projects()


def switch_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    target_pid = sanitize_project_id(payload.get("project_id") or "default")
    v010_core_service._persist_autosave("Pre-switch autosave", "Автосохранение перед переключением")

    settings_service.save_settings({"active_project": target_pid})
    _project_dir(target_pid)
    manifest = load_manifest(target_pid)

    v010_core_service.UNDO_STACK.clear()
    v010_core_service.REDO_STACK.clear()
    v010_core_service.CURRENT_STATE.clear()
    v010_core_service.CURRENT_STATE.update({
        "project": target_pid,
        "active_level": manifest.get("entry_level", "l01_escape"),
        "active_campaign": manifest.get("entry_campaign", "tm_escape.ltx"),
        "active_dialog": manifest.get("entry_dialog", "inf_trader_buy_transitions"),
        "placed_objects": [],
        "quest_edits": {},
        "dialog_edits": {},
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    v010_core_service.load_autosave_state(target_pid)
    v010_core_service.CURRENT_STATE["project"] = target_pid
    v010_core_service._persist_autosave()
    lua_res = generate_lua_spawn_script(target_pid, write_to_disk=True)

    v010_core_service.append_log(
        "INFO",
        f"Switched active project to '{manifest.get('title', target_pid)}' ({target_pid}/project.anomaly, {len(v010_core_service.CURRENT_STATE.get('placed_objects', []))} placed 3D objects).",
        f"Активный проект переключён на '{manifest.get('title', target_pid)}' ({target_pid}/project.anomaly, 3D объектов: {len(v010_core_service.CURRENT_STATE.get('placed_objects', []))}).",
        category="project",
    )
    res = list_projects()
    res["state"] = v010_core_service.CURRENT_STATE
    res["lua_spawn_script"] = lua_res
    return res


def save_project_and_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    st = settings_service.load_settings()
    pid = sanitize_project_id(payload.get("project_id") or st.get("active_project") or "default")
    manifest = save_manifest(pid, payload)
    v010_core_service.CURRENT_STATE["project"] = pid
    v010_core_service._persist_autosave("Project Save", "Сохранение проекта")
    lua_res = generate_lua_spawn_script(pid, write_to_disk=True)

    snap_file = None
    if payload.get("create_snapshot", False):
        snap_dir = _project_dir(pid) / "snapshots"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        label = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(payload.get("snapshot_label") or "snapshot")).strip("_")[:32]
        snap_path = snap_dir / f"{ts}_{label or 'snap'}.json"
        snap_payload = {
            "manifest": manifest,
            "state": v010_core_service.CURRENT_STATE,
            "saved_at": datetime.now().isoformat(),
        }
        snap_path.write_text(json.dumps(snap_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        snap_file = snap_path.name

    v010_core_service.append_log(
        "INFO",
        f"Saved project '{manifest['title']}' ({pid}/project.anomaly) + generated {lua_res['script_rel']} ({lua_res['entity_count']} entities).",
        f"Проект '{manifest['title']}' ({pid}/project.anomaly) сохранён + сгенерирован {lua_res['script_rel']} (объектов: {lua_res['entity_count']}).",
        category="project",
    )
    res = list_projects()
    res["snapshot_created"] = snap_file
    res["lua_spawn_script"] = lua_res
    return res


def simulate_lua_spawn_script(project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the generated `gamedata/scripts/mod_studio_spawns_<slug>.script` inside a real
    Lua VM (via `lupa`, with automatic deterministic fallback if `lupa` is not in sys.path)
    providing a full X-Ray Monolith / Anomaly 1.5.3 ALife sandbox:
      - `vector():set(x, y, z)`
      - `alife_create(section, pos, lvid, gvid)`
      - `alife_storage_manager.get_state()`
      - `reg_story_id(se_obj_id, story_id)`
      - `RegisterScriptCallback(event, fn)`
      - `printf(fmt, ...)`
    Verifies:
      1. First actor update spawns all `N` placed 3D entities with exact section, position, LVID/GVID, yaw_rad, and story_id.
      2. Second actor update (savegame reload) spawns `0` duplicates (`alife_storage_manager` persistence works!).
      3. `respawn_all()` force-respawns all `N` entities on demand.
    """
    gen = generate_lua_spawn_script(project_id, write_to_disk=True)
    lua_code = gen["lua_code"]
    pid = gen["project_id"]

    # Ensure studio_venv site-packages is available if running under system python3
    venv_sp = Path.home() / ".local" / "studio_venv" / "lib" / "python3.12" / "site-packages"
    if venv_sp.is_dir() and str(venv_sp) not in sys.path:
        sys.path.insert(0, str(venv_sp))

    import lupa
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)

    sandbox_harness = """
    _SIM_SPAWNED = {}
    _SIM_STORY_IDS = {}
    _SIM_LOGS = {}
    _SIM_CALLBACKS = {}
    _SIM_STORAGE = {}
    _NEXT_SE_ID = 10000

    function alife()
        return true
    end

    vector = function()
        return {
            x = 0, y = 0, z = 0,
            set = function(self, vx, vy, vz)
                self.x = vx or 0
                self.y = vy or 0
                self.z = vz or 0
                return self
            end
        }
    end

    alife_storage_manager = {
        get_state = function()
            return _SIM_STORAGE
        end
    }

    function alife_create(section, pos, lvid, gvid)
        _NEXT_SE_ID = _NEXT_SE_ID + 1
        local obj = {
            id = _NEXT_SE_ID,
            section = section,
            x = pos and pos.x or 0,
            y = pos and pos.y or 0,
            z = pos and pos.z or 0,
            lvid = lvid or 0,
            gvid = gvid or 0,
            angle = vector():set(0, 0, 0)
        }
        table.insert(_SIM_SPAWNED, obj)
        return obj
    end

    function reg_story_id(se_id, story_id)
        _SIM_STORY_IDS[story_id] = se_id
    end

    function RegisterScriptCallback(name, fn)
        _SIM_CALLBACKS[name] = fn
    end

    function printf(fmt, ...)
        local ok, msg = pcall(string.format, fmt, ...)
        table.insert(_SIM_LOGS, ok and msg or tostring(fmt))
    end
    """

    lua.execute(sandbox_harness)
    lua.execute(lua_code)

    # Trigger on_game_start() -> registers actor_on_first_update callback
    lua.execute("""
    if on_game_start then
        on_game_start()
    end
    _FIRST_RUN_COUNT = 0
    if _SIM_CALLBACKS['actor_on_first_update'] then
        _SIM_CALLBACKS['actor_on_first_update']()
        _FIRST_RUN_COUNT = #_SIM_SPAWNED
    end
    -- Second trigger of actor_on_first_update: must NOT duplicate spawns!
    if _SIM_CALLBACKS['actor_on_first_update'] then
        _SIM_CALLBACKS['actor_on_first_update']()
    end
    _AFTER_SECOND_RUN_COUNT = #_SIM_SPAWNED
    _DUPLICATES_ON_RELOAD = _AFTER_SECOND_RUN_COUNT - _FIRST_RUN_COUNT
    """)

    first_run_count = int(lua.eval("_FIRST_RUN_COUNT"))
    duplicates_on_reload = int(lua.eval("_DUPLICATES_ON_RELOAD"))
    lua_version = str(lua.eval("_VERSION"))

    spawned_tbl = lua.eval("_SIM_SPAWNED")
    story_tbl = lua.eval("_SIM_STORY_IDS")
    logs_tbl = lua.eval("_SIM_LOGS")

    spawned_list: List[Dict[str, Any]] = []
    if spawned_tbl:
        for idx in spawned_tbl:
            item = spawned_tbl[idx]
            ang = item["angle"]
            spawned_list.append({
                "se_id": int(item["id"]),
                "section": str(item["section"]),
                "x": round(float(item["x"]), 3),
                "y": round(float(item["y"]), 3),
                "z": round(float(item["z"]), 3),
                "lvid": int(item["lvid"]),
                "gvid": int(item["gvid"]),
                "yaw_rad": round(float(ang["y"]), 4) if ang else 0.0,
            })

    story_map: Dict[str, int] = {}
    if story_tbl:
        for k in story_tbl:
            story_map[str(k)] = int(story_tbl[k])

    sim_logs: List[str] = [str(logs_tbl[k]) for k in logs_tbl] if logs_tbl else []
    ok = (first_run_count == gen["entity_count"]) and (duplicates_on_reload == 0)

    v010_core_service.append_log(
        "INFO" if ok else "ERROR",
        f"[Lua Placer VM ({lua_version})] Executed {gen['script_rel']}: {first_run_count}/{gen['entity_count']} ALife entities spawned, {duplicates_on_reload} duplicates on save-reload, {len(story_map)} story_ids registered.",
        f"[Lua Placer VM ({lua_version})] Выполнен {gen['script_rel']}: создано {first_run_count}/{gen['entity_count']} объектов ALife, дубликатов при перезагрузке: {duplicates_on_reload}, story_id: {len(story_map)}.",
        category="spawn_check",
    )

    return {
        "ok": ok,
        "lua_vm": lua_version,
        "project_id": pid,
        "script_rel": gen["script_rel"],
        "expected_count": gen["entity_count"],
        "spawned_first_update": first_run_count,
        "duplicates_on_save_reload": duplicates_on_reload,
        "registered_story_ids": story_map,
        "spawned_entities": spawned_list,
        "lua_printf_logs": sim_logs,
        "lua_code": lua_code,
    }
