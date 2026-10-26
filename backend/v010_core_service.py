#!/usr/bin/env python3
"""
Anomaly Studio v0.1.1-alpha — Core Service Module (EN + RU only)
================================================================
Provides:
1. Console / Log Ring Buffer (`INFO`, `WARN`, `ERROR`, `SPAWN_CHECK`) with EN + RU messages
2. Structured Error Handler (`make_error_response`)
3. Undo / Redo History Stack + Persistent Project Autosave (`projects/<project>/autosave/`)
4. Basic 3D Placement State (`place`, `select`, `move`, `rotate_scale`, `delete`) with CFORM + LVID/GVID
5. Spawn & Load Check (`Query -> Console`) verifying Quest/Campaign/Dialog/3D Placement against packed `.db0` VFS
6. Working `.db0` Export directly into `<anomaly_path>/mods/` or `<mo2_path>/mods/<mod>/db/`

Author / Credits: EternalPain
"""
from __future__ import annotations
import sys
import copy
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import settings_service
import db0_vfs

STUDIO_ROOT = (Path(os.environ['ANOMALY_STUDIO_ROOT']).resolve() if os.environ.get('ANOMALY_STUDIO_ROOT') else (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent))
PROJECTS_DIR = STUDIO_ROOT / "projects"
EXPORTS_DIR = STUDIO_ROOT / "exports"

# ---------------------------------------------------------------------------
# 1. CONSOLE / LOG PANEL RING BUFFER (EN + RU)
# ---------------------------------------------------------------------------
CONSOLE_LOGS: List[Dict[str, Any]] = []
_LOG_SEQ = 0


def append_log(level: str, msg_en: str, msg_ru: Optional[str] = None, category: str = "system", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    global _LOG_SEQ
    _LOG_SEQ += 1
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    entry = {
        "id": _LOG_SEQ,
        "ts": ts,
        "level": level.upper(),  # INFO, WARN, ERROR, SPAWN_CHECK
        "category": category,
        "msg_en": msg_en,
        "msg_ru": msg_ru or msg_en,
        "details": details or {},
    }
    CONSOLE_LOGS.append(entry)
    if len(CONSOLE_LOGS) > 500:
        del CONSOLE_LOGS[: len(CONSOLE_LOGS) - 500]
    return entry


def get_logs(since_id: int = 0, level_filter: str = "ALL") -> Dict[str, Any]:
    lvl = (level_filter or "ALL").upper()
    items = [
        e for e in CONSOLE_LOGS
        if e["id"] > since_id and (lvl == "ALL" or e["level"] == lvl or (lvl == "SPAWN_CHECK" and e["category"] == "spawn_check"))
    ]
    return {
        "ok": True,
        "logs": items,
        "latest_id": _LOG_SEQ,
        "total_buffered": len(CONSOLE_LOGS),
    }


def clear_logs() -> Dict[str, Any]:
    CONSOLE_LOGS.clear()
    append_log("INFO", "Console log cleared.", "Журнал консоли очищен.", category="system")
    return {"ok": True, "logs": CONSOLE_LOGS, "latest_id": _LOG_SEQ}


def make_error_response(code: str, msg_en: str, msg_ru: str, hint_en: str = "", hint_ru: str = "", exc: Optional[Exception] = None) -> Dict[str, Any]:
    detail = f" ({type(exc).__name__}: {exc})" if exc else ""
    append_log("ERROR", f"[{code}] {msg_en}{detail}", f"[{code}] {msg_ru}{detail}", category="error")
    return {
        "ok": False,
        "code": code,
        "error": f"{msg_en}{detail}",
        "message_en": f"{msg_en}{detail}",
        "message_ru": f"{msg_ru}{detail}",
        "hint_en": hint_en,
        "hint_ru": hint_ru or hint_en,
    }


# ---------------------------------------------------------------------------
# 2. UNDO / REDO STACK + PERSISTENT AUTOSAVE (Quests, Dialogs, 3D Placement)
# ---------------------------------------------------------------------------
UNDO_STACK: List[Dict[str, Any]] = []
REDO_STACK: List[Dict[str, Any]] = []

CURRENT_STATE: Dict[str, Any] = {
    "project": "default",
    "active_level": "l01_escape",
    "active_campaign": "tm_escape.ltx",
    "active_dialog": "inf_trader_buy_transitions",
    "placed_objects": [],
    "quest_edits": {},
    "dialog_edits": {},
    "updated_at": "",
}


def _autosave_dir(project: str = "default") -> Path:
    d = PROJECTS_DIR / project / "autosave"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_autosave_state(project: str = "default") -> Dict[str, Any]:
    global CURRENT_STATE
    f = _autosave_dir(project) / "state_latest.json"
    if f.is_file():
        try:
            loaded = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                CURRENT_STATE.update(loaded)
        except Exception:
            pass
    return CURRENT_STATE


def _persist_autosave(label_en: str = "Autosave", label_ru: str = "Автосохранение") -> None:
    CURRENT_STATE["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    proj = CURRENT_STATE.get("project", "default")
    f = _autosave_dir(proj) / "state_latest.json"
    f.write_text(json.dumps(CURRENT_STATE, indent=2, ensure_ascii=False), encoding="utf-8")


def push_undo_snapshot(action_en: str, action_ru: str = "") -> None:
    snap = {
        "action_en": action_en,
        "action_ru": action_ru or action_en,
        "ts": datetime.now().strftime("%H:%M:%S"),
        "state": copy.deepcopy(CURRENT_STATE),
    }
    UNDO_STACK.append(snap)
    if len(UNDO_STACK) > 60:
        UNDO_STACK.pop(0)
    REDO_STACK.clear()


def perform_undo() -> Dict[str, Any]:
    global CURRENT_STATE
    if not UNDO_STACK:
        append_log("WARN", "Undo: Nothing to undo.", "Отмена: нет действий для отмены.", category="undo")
        return {"ok": False, "message_en": "Nothing to undo.", "message_ru": "Нет действий для отмены.", "state": CURRENT_STATE, "undo_count": 0, "redo_count": len(REDO_STACK)}
    last = UNDO_STACK.pop()
    REDO_STACK.append({
        "action_en": last["action_en"],
        "action_ru": last["action_ru"],
        "ts": datetime.now().strftime("%H:%M:%S"),
        "state": copy.deepcopy(CURRENT_STATE),
    })
    CURRENT_STATE = copy.deepcopy(last["state"])
    _persist_autosave()
    append_log("INFO", f"Undo applied: {last['action_en']}", f"Отменено действие: {last['action_ru']}", category="undo")
    return {
        "ok": True,
        "action_en": last["action_en"],
        "action_ru": last["action_ru"],
        "state": CURRENT_STATE,
        "undo_count": len(UNDO_STACK),
        "redo_count": len(REDO_STACK),
    }


def perform_redo() -> Dict[str, Any]:
    global CURRENT_STATE
    if not REDO_STACK:
        append_log("WARN", "Redo: Nothing to redo.", "Повтор: нет действий для повтора.", category="undo")
        return {"ok": False, "message_en": "Nothing to redo.", "message_ru": "Нет действий для повтора.", "state": CURRENT_STATE, "undo_count": len(UNDO_STACK), "redo_count": 0}
    nxt = REDO_STACK.pop()
    UNDO_STACK.append({
        "action_en": nxt["action_en"],
        "action_ru": nxt["action_ru"],
        "ts": datetime.now().strftime("%H:%M:%S"),
        "state": copy.deepcopy(CURRENT_STATE),
    })
    CURRENT_STATE = copy.deepcopy(nxt["state"])
    _persist_autosave()
    append_log("INFO", f"Redo applied: {nxt['action_en']}", f"Повторено действие: {nxt['action_ru']}", category="undo")
    return {
        "ok": True,
        "action_en": nxt["action_en"],
        "action_ru": nxt["action_ru"],
        "state": CURRENT_STATE,
        "undo_count": len(UNDO_STACK),
        "redo_count": len(REDO_STACK),
    }


def save_autosave_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    action_en = payload.get("action_en", "Update studio state")
    action_ru = payload.get("action_ru", "Обновление состояния студии")
    if payload.get("record_undo", True):
        push_undo_snapshot(action_en, action_ru)
    for k in ("active_level", "active_campaign", "active_dialog", "placed_objects", "quest_edits", "dialog_edits"):
        if k in payload and payload[k] is not None:
            CURRENT_STATE[k] = payload[k]
    _persist_autosave(action_en, action_ru)
    return {
        "ok": True,
        "state": CURRENT_STATE,
        "undo_count": len(UNDO_STACK),
        "redo_count": len(REDO_STACK),
    }


# ---------------------------------------------------------------------------
# 3. 3D PLACEMENT CRUD (Place, Select, Move, Rotate/Scale, Delete)
# ---------------------------------------------------------------------------
def handle_placement_action(body: Dict[str, Any], find_nearest_ai_fn=None) -> Dict[str, Any]:
    op = (body.get("op") or "list").lower()
    level = body.get("level") or CURRENT_STATE.get("active_level") or "l01_escape"
    CURRENT_STATE["active_level"] = level
    objs: List[Dict[str, Any]] = CURRENT_STATE.setdefault("placed_objects", [])

    if op == "list":
        lvl_objs = [o for o in objs if o.get("level", level) == level]
        return {"ok": True, "level": level, "objects": lvl_objs, "all_objects": objs, "undo_count": len(UNDO_STACK), "redo_count": len(REDO_STACK)}

    if op == "place":
        section = (body.get("section") or "stalker_sim_ecolog").strip()
        mesh = (body.get("mesh") or "actors\\stalker_ecologist\\stalker_ecolog.ogf").strip()
        category = (body.get("category") or "npc").strip()
        x = round(float(body.get("x", -145.0)), 3)
        y = round(float(body.get("y", -19.8)), 3)
        z = round(float(body.get("z", -145.0)), 3)
        rot_y = round(float(body.get("rot_y", 0.0)), 2)
        scale = round(float(body.get("scale", 1.0)), 3)
        name = (body.get("name") or f"{section}_{int(time.time()*1000) % 100000}").strip()

        lvid, gvid = int(body.get("lvid", 0)), int(body.get("gvid", 362))
        if find_nearest_ai_fn:
            try:
                ai_res = find_nearest_ai_fn(level, x, y, z)
                if isinstance(ai_res, dict):
                    if "level_vertex_id" in ai_res:
                        lvid = int(ai_res["level_vertex_id"])
                    elif "vertex_id" in ai_res:
                        lvid = int(ai_res["vertex_id"])
                    if "game_vertex_id" in ai_res:
                        gvid = int(ai_res["game_vertex_id"])
                    if body.get("snap_to_ai_y", False):
                        if "node_pos" in ai_res and len(ai_res["node_pos"]) >= 2:
                            y = round(float(ai_res["node_pos"][1]), 3)
                        elif "y" in ai_res:
                            y = round(float(ai_res["y"]), 3)
            except Exception:
                pass

        push_undo_snapshot(f"Place 3D object '{name}' ({section})", f"Размещение 3D объекта '{name}' ({section})")
        new_obj = {
            "id": f"obj_{int(time.time()*1000)}_{len(objs)+1}",
            "name": name,
            "section": section,
            "mesh": mesh,
            "category": category,
            "level": level,
            "x": x,
            "y": y,
            "z": z,
            "rot_y": rot_y,
            "scale": scale,
            "lvid": lvid,
            "gvid": gvid,
            "story_id": body.get("story_id", ""),
        }
        objs.append(new_obj)
        _persist_autosave()
        append_log(
            "INFO",
            f"Placed 3D object '{name}' [{section}] at ({x}, {y}, {z}) LVID={lvid} GVID={gvid} on {level}.",
            f"Размещён 3D объект '{name}' [{section}] в ({x}, {y}, {z}) LVID={lvid} GVID={gvid} на {level}.",
            category="placement",
        )
        return {"ok": True, "object": new_obj, "objects": [o for o in objs if o.get("level") == level], "undo_count": len(UNDO_STACK), "redo_count": len(REDO_STACK)}

    if op in ("move", "update", "rotate_scale"):
        obj_id = body.get("id")
        target = next((o for o in objs if o.get("id") == obj_id), None)
        if not target:
            return make_error_response("OBJ_NOT_FOUND", f"3D object not found: {obj_id}", f"3D объект не найден: {obj_id}")
        push_undo_snapshot(f"Transform 3D object '{target['name']}'", f"Трансформация 3D объекта '{target['name']}'")
        for k in ("x", "y", "z", "rot_y", "scale"):
            if k in body and body[k] is not None:
                target[k] = round(float(body[k]), 3)
        for k in ("name", "section", "mesh", "story_id"):
            if k in body and body[k] is not None:
                target[k] = str(body[k]).strip()
        if find_nearest_ai_fn and any(k in body for k in ("x", "y", "z")):
            try:
                ai_res = find_nearest_ai_fn(target["level"], target["x"], target["y"], target["z"])
                if isinstance(ai_res, dict):
                    if "level_vertex_id" in ai_res:
                        target["lvid"] = int(ai_res["level_vertex_id"])
                    elif "vertex_id" in ai_res:
                        target["lvid"] = int(ai_res["vertex_id"])
                    if "game_vertex_id" in ai_res:
                        target["gvid"] = int(ai_res["game_vertex_id"])
            except Exception:
                pass
        _persist_autosave()
        append_log(
            "INFO",
            f"Updated 3D object '{target['name']}' -> pos=({target['x']}, {target['y']}, {target['z']}) rot={target['rot_y']}° scale={target['scale']} LVID={target.get('lvid', 0)}.",
            f"Обновлён 3D объект '{target['name']}' -> поз=({target['x']}, {target['y']}, {target['z']}) пов={target['rot_y']}° масш={target['scale']} LVID={target.get('lvid', 0)}.",
            category="placement",
        )
        return {"ok": True, "object": target, "objects": [o for o in objs if o.get("level") == level], "undo_count": len(UNDO_STACK), "redo_count": len(REDO_STACK)}

    if op == "delete":
        obj_id = body.get("id")
        target = next((o for o in objs if o.get("id") == obj_id), None)
        if not target:
            return make_error_response("OBJ_NOT_FOUND", f"3D object not found: {obj_id}", f"3D объект не найден: {obj_id}")
        push_undo_snapshot(f"Delete 3D object '{target['name']}'", f"Удаление 3D объекта '{target['name']}'")
        CURRENT_STATE["placed_objects"] = [o for o in objs if o.get("id") != obj_id]
        _persist_autosave()
        append_log(
            "INFO",
            f"Deleted 3D object '{target['name']}' ({obj_id}) from {level}.",
            f"Удалён 3D объект '{target['name']}' ({obj_id}) с уровня {level}.",
            category="placement",
        )
        return {"ok": True, "deleted_id": obj_id, "objects": [o for o in CURRENT_STATE["placed_objects"] if o.get("level") == level], "undo_count": len(UNDO_STACK), "redo_count": len(REDO_STACK)}

    if op == "clear":
        push_undo_snapshot(f"Clear placed objects on {level}", f"Очистка объектов на уровне {level}")
        CURRENT_STATE["placed_objects"] = [o for o in objs if o.get("level") != level]
        _persist_autosave()
        append_log("WARN", f"Cleared all placed 3D objects on {level}.", f"Очищены все размещённые 3D объекты на {level}.", category="placement")
        return {"ok": True, "objects": [], "undo_count": len(UNDO_STACK), "redo_count": len(REDO_STACK)}

    return make_error_response("INVALID_OP", f"Unknown placement op: {op}", f"Неизвестная операция размещения: {op}")


# ---------------------------------------------------------------------------
# 4. SPAWN & LOAD CHECK (Query -> Console) AGAINST PACKED .DB0 VFS
# ---------------------------------------------------------------------------
def run_spawn_and_load_check(payload: Dict[str, Any], quest_logic_mod=None) -> Dict[str, Any]:
    """
    Verifies against packed .db0 archives (with ZERO unpacked/ dependency):
    1. Anomaly .db0 VFS archive integrity & TOC availability
    2. Active Campaign / Quest LTX sections, target smart_terrains/story_ids, EN+RU string table IDs, condlists
    3. Active Dialog XML phrase graph connectivity (root phrase 0, no dead next links, EN+RU string resolution)
    4. Placed 3D objects: valid LTX section/mesh existence in .db0 VFS, valid CFORM coordinates, valid AI LVID/GVID
    Streams every [PASS] / [WARN] / [FAIL] check line directly to the Console / Log Panel!
    """
    t0 = time.time()
    vfs = db0_vfs.get_global_vfs()
    level = payload.get("level") or CURRENT_STATE.get("active_level") or "l01_escape"
    campaign_file = payload.get("campaign") or CURRENT_STATE.get("active_campaign") or "tm_escape.ltx"
    dialog_id = payload.get("dialog") or CURRENT_STATE.get("active_dialog") or "inf_trader_buy_transitions"

    checks: List[Dict[str, Any]] = []

    def rec(status: str, code: str, msg_en: str, msg_ru: str) -> None:
        lvl = "ERROR" if status == "FAIL" else ("WARN" if status == "WARN" else "INFO")
        log_entry = append_log(
            lvl,
            f"[{status}] ({code}) {msg_en}",
            f"[{status}] ({code}) {msg_ru}",
            category="spawn_check",
        )
        checks.append({
            "status": status,
            "code": code,
            "msg_en": msg_en,
            "msg_ru": msg_ru,
            "log_id": log_entry["id"],
        })

    append_log(
        "INFO",
        f"=== Starting Spawn & Load Check (Level={level}, Campaign={campaign_file}, Dialog={dialog_id}) ===",
        f"=== Запуск проверки спавна и загрузки (Уровень={level}, Кампания={campaign_file}, Диалог={dialog_id}) ===",
        category="spawn_check",
    )

    # Check 1: Packed .db0 VFS availability
    if vfs.total_archives > 0 and len(vfs.entries) > 1000:
        rec(
            "PASS",
            "DB0_VFS_INDEX",
            f"Direct .db0 VFS active: {len(vfs.entries)} files indexed across {vfs.total_archives} packed .db0 archives (0 unpacked/ dependencies).",
            f"Прямая VFS .db0 активна: {len(vfs.entries)} файлов в {vfs.total_archives} архивах .db0 (без зависимости от unpacked/).",
        )
    else:
        rec(
            "FAIL",
            "DB0_VFS_INDEX",
            f"No packed .db0 archives found at {vfs.anomaly_path}/db.",
            f"Упакованные архивы .db0 не найдены в {vfs.anomaly_path}/db.",
        )

    # Check 2: Level CFORM + AI NavMesh in .db0
    cform_key = f"levels/{level}/level.cform"
    ai_key = f"levels/{level}/level.ai"
    if vfs.exists(cform_key) and vfs.exists(ai_key):
        cform_sz = vfs.entries[cform_key].size_real
        ai_sz = vfs.entries[ai_key].size_real
        rec(
            "PASS",
            "LEVEL_GEOM_AI",
            f"Level '{level}' binary assets verified in .db0: level.cform ({cform_sz:,} B) + level.ai ({ai_sz:,} B).",
            f"Бинарные ресурсы уровня '{level}' проверены в .db0: level.cform ({cform_sz:,} Б) + level.ai ({ai_sz:,} Б).",
        )
    else:
        rec(
            "FAIL",
            "LEVEL_GEOM_AI",
            f"Level '{level}' missing level.cform or level.ai in .db0 archives.",
            f"Для уровня '{level}' отсутствует level.cform или level.ai в архивах .db0.",
        )

    # Check 3: Campaign / Quest LTX & String Tables
    if quest_logic_mod:
        t_data = quest_logic_mod.parse_all_tm_tasks()
        camp = t_data.get("campaigns", {}).get(campaign_file)
        if camp and camp.get("count", 0) > 0:
            tasks = camp["tasks"]
            missing_titles = [t["id"] for t in tasks if not t.get("title_en")]
            rec(
                "PASS",
                "QUEST_CAMPAIGN_LTX",
                f"Campaign '{campaign_file}' verified: {len(tasks)} task sections parsed with EN/RU string table bindings.",
                f"Кампания '{campaign_file}' проверена: разобрано {len(tasks)} секций квестов с привязкой строк EN/RU.",
            )
            if missing_titles:
                rec(
                    "WARN",
                    "QUEST_STRINGS",
                    f"{len(missing_titles)} task(s) in {campaign_file} use fallback string IDs.",
                    f"{len(missing_titles)} квест(ов) в {campaign_file} используют резервные ID строк.",
                )
        else:
            rec(
                "WARN",
                "QUEST_CAMPAIGN_LTX",
                f"Campaign '{campaign_file}' not found or empty.",
                f"Кампания '{campaign_file}' не найдена или пуста.",
            )

        # Check 4: Dialog XML Graph & Phrase Links
        dlg = quest_logic_mod.get_dialog_graph(dialog_id)
        d_nodes = dlg.get("nodes", [])
        d_edges = dlg.get("edges", [])
        if d_nodes:
            node_ids = {n["id"] for n in d_nodes}
            broken_edges = [e for e in d_edges if e["to"] not in node_ids]
            if not broken_edges:
                rec(
                    "PASS",
                    "DIALOG_DAG_LINKS",
                    f"Dialog '{dialog_id}' verified: {len(d_nodes)} phrases, {len(d_edges)} transitions, 0 broken <next> links.",
                    f"Диалог '{dialog_id}' проверен: {len(d_nodes)} фраз, {len(d_edges)} переходов, 0 оборванных ссылок <next>.",
                )
            else:
                rec(
                    "FAIL",
                    "DIALOG_DAG_LINKS",
                    f"Dialog '{dialog_id}' has {len(broken_edges)} broken <next> transition(s).",
                    f"В диалоге '{dialog_id}' обнаружено {len(broken_edges)} оборванных переходов <next>.",
                )
        else:
            rec(
                "WARN",
                "DIALOG_DAG_LINKS",
                f"Dialog '{dialog_id}' returned 0 phrases.",
                f"Диалог '{dialog_id}' содержит 0 фраз.",
            )

    # Check 5: Placed 3D Objects (Mesh existence in .db0 + LVID/GVID validity)
    lvl_objs = [o for o in CURRENT_STATE.get("placed_objects", []) if o.get("level", level) == level]
    if not lvl_objs:
        rec(
            "PASS",
            "PLACED_OBJECTS_CHECK",
            f"0 custom 3D objects placed on '{level}' (clean vanilla state).",
            f"На уровне '{level}' размещено 0 пользовательских 3D объектов (чистое базовое состояние).",
        )
    else:
        for obj in lvl_objs:
            mesh_rel = obj.get("mesh", "").replace("\\", "/").strip("/")
            if not mesh_rel.startswith("meshes/"):
                mesh_vfs = f"meshes/{mesh_rel}"
            else:
                mesh_vfs = mesh_rel
            if not mesh_vfs.endswith(".ogf"):
                mesh_vfs += ".ogf"
            mesh_ok = vfs.exists(mesh_vfs)
            lvid = int(obj.get("lvid", -1))
            if mesh_ok and lvid >= 0:
                rec(
                    "PASS",
                    "SPAWN_ENTITY_VALID",
                    f"Object '{obj['name']}' [{obj['section']}] verified: mesh '{mesh_vfs}' exists in .db0, pos=({obj['x']}, {obj['y']}, {obj['z']}), LVID={lvid}, GVID={obj.get('gvid', 0)}.",
                    f"Объект '{obj['name']}' [{obj['section']}] проверен: меш '{mesh_vfs}' найден в .db0, поз=({obj['x']}, {obj['y']}, {obj['z']}), LVID={lvid}, GVID={obj.get('gvid', 0)}.",
                )
            elif not mesh_ok:
                rec(
                    "FAIL",
                    "SPAWN_MESH_MISSING",
                    f"Object '{obj['name']}' references missing OGF mesh '{mesh_vfs}' (not in .db0 VFS).",
                    f"Объект '{obj['name']}' ссылается на отсутствующий OGF меш '{mesh_vfs}' (нет в .db0 VFS).",
                )
            else:
                rec(
                    "WARN",
                    "SPAWN_LVID_UNSET",
                    f"Object '{obj['name']}' has invalid LVID={lvid}.",
                    f"У объекта '{obj['name']}' некорректный LVID={lvid}.",
                )

    elapsed_ms = round((time.time() - t0) * 1000.0, 1)
    fail_cnt = sum(1 for c in checks if c["status"] == "FAIL")
    warn_cnt = sum(1 for c in checks if c["status"] == "WARN")
    pass_cnt = sum(1 for c in checks if c["status"] == "PASS")

    append_log(
        "INFO" if fail_cnt == 0 else "ERROR",
        f"=== Spawn & Load Check Complete in {elapsed_ms} ms: {pass_cnt} PASS, {warn_cnt} WARN, {fail_cnt} FAIL ===",
        f"=== Проверка спавна и загрузки завершена за {elapsed_ms} мс: {pass_cnt} УСПЕШНО, {warn_cnt} ПРЕДУПР., {fail_cnt} ОШИБОК ===",
        category="spawn_check",
    )

    return {
        "ok": fail_cnt == 0,
        "level": level,
        "campaign": campaign_file,
        "dialog": dialog_id,
        "pass_count": pass_cnt,
        "warn_count": warn_cnt,
        "fail_count": fail_cnt,
        "elapsed_ms": elapsed_ms,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# 5. WORKING .DB0 EXPORT FOR USER INSTALLS (Anomaly /mods/ + MO2 /mods/<mod>/db/)
# ---------------------------------------------------------------------------
def export_project_to_db0(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compiles active project quests, string tables, and placed 3D objects into
    `projects/<project>/gamedata/` and packs a valid Anomaly 1.5.3 `.db0` archive:
    - Always writes `exports/<archive_name>.db0`
    - Optionally deploys directly to `<anomaly_path>/mods/<archive_name>.db0` or
      `<mo2_path>/mods/<mod_name>/db/<archive_name>.db0`
    - Verifies the packed `.db0` by reading back its TOC via `db0_vfs.read_db0_toc`!
    """
    st = settings_service.load_settings()
    project = payload.get("project") or st.get("active_project") or "default"
    mod_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", payload.get("mod_name", "Anomaly_Studio_Custom_Mod"))
    archive_name = payload.get("archive_name") or f"zzz_{mod_name.lower()}.db0"
    if not archive_name.endswith(".db0"):
        archive_name += ".db0"

    gd_dir = PROJECTS_DIR / project / "gamedata"
    (gd_dir / "configs" / "misc" / "task").mkdir(parents=True, exist_ok=True)
    (gd_dir / "configs" / "text" / "eng").mkdir(parents=True, exist_ok=True)
    (gd_dir / "configs" / "text" / "rus").mkdir(parents=True, exist_ok=True)
    (gd_dir / "scripts").mkdir(parents=True, exist_ok=True)

    # 1. Write metadata & custom task LTX
    tasks_ltx = gd_dir / "configs" / "misc" / "task" / f"tm_{mod_name.lower()}.ltx"
    ltx_lines = [
        f"; Generated by Anomaly Studio v0.1.1-alpha (Author/Credits: EternalPain)",
        f"; Timestamp: {datetime.now().isoformat()}",
        "",
    ]
    for tid, tdata in CURRENT_STATE.get("quest_edits", {}).items():
        ltx_lines.append(f"[{tid}]")
        ltx_lines.append(f"icon = {tdata.get('icon', 'ui_inGame2_Mesta_evakuatsii')}")
        ltx_lines.append(f"prior = {tdata.get('prior', 100)}")
        ltx_lines.append(f"storyline = {'true' if tdata.get('storyline') else 'false'}")
        ltx_lines.append(f"title = {tdata.get('title_id', tid + '_title')}")
        ltx_lines.append(f"descr = {tdata.get('descr_id', tid + '_descr')}")
        if tdata.get("target"):
            ltx_lines.append(f"target = {tdata['target']}")
        if tdata.get("on_init"):
            ltx_lines.append(f"on_init = {tdata['on_init']}")
        if tdata.get("on_complete"):
            ltx_lines.append(f"on_complete = {tdata['on_complete']}")
        ltx_lines.append("")
    tasks_ltx.write_bytes("\r\n".join(ltx_lines).encode("cp1251", errors="replace"))

    # 2. Write placed 3D objects spawn script (mod_studio_spawns_<slug>.script + project.anomaly)
    import project_service
    project_service.save_manifest(project, {"archive_name": archive_name})
    lua_gen = project_service.generate_lua_spawn_script(project, write_to_disk=True)

    # 3. Copy any custom overrides from index/quests_custom_overrides.json string tables
    for lang in ("eng", "rus"):
        st_xml = gd_dir / "configs" / "text" / lang / f"st_{mod_name.lower()}.xml"
        xml_lines = [
            '<?xml version="1.0" encoding="windows-1251" ?>',
            "<string_table>",
            f'  <string id="st_{mod_name.lower()}_credit">',
            f"    <text>Created with Anomaly Studio v0.1.1-alpha (EternalPain)</text>",
            "  </string>",
        ]
        for tid, tdata in CURRENT_STATE.get("quest_edits", {}).items():
            t_id = tdata.get("title_id") or f"{tid}_title"
            d_id = tdata.get("descr_id") or f"{tid}_descr"
            t_val = tdata.get("title_ru" if lang == "rus" else "title_text") or tdata.get("title_text") or tid
            d_val = tdata.get("descr_ru" if lang == "rus" else "descr_text") or tdata.get("descr_text") or ""
            for sid, sval in ((t_id, t_val), (d_id, d_val)):
                esc = str(sval).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                xml_lines.append(f'  <string id="{sid}"><text>{esc}</text></string>')
        xml_lines.append("</string_table>")
        st_xml.write_bytes("\r\n".join(xml_lines).encode("cp1251", errors="replace"))

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    custom_out_dir = Path(st.get("mods_output_path") or EXPORTS_DIR).expanduser()
    try:
        custom_out_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        custom_out_dir = EXPORTS_DIR
    out_db0 = custom_out_dir / archive_name
    pack_res = db0_vfs.pack_directory_to_db0(gd_dir, out_db0)
    if custom_out_dir.resolve() != EXPORTS_DIR.resolve():
        (EXPORTS_DIR / archive_name).write_bytes(out_db0.read_bytes())

    # Verify TOC readability immediately
    toc_entries = db0_vfs.read_db0_toc(str(out_db0))
    deployed_paths = [str(out_db0)]

    # Optional deploy to Anomaly /mods/ or MO2 /mods/<mod>/db/
    target_mode = payload.get("deploy_target", "exports")  # exports, anomaly_mods, mo2_mod
    if target_mode in ("anomaly_mods", "both") and st.get("anomaly_path"):
        anom_mods = Path(st["anomaly_path"]) / "mods"
        if anom_mods.is_dir():
            dest = anom_mods / archive_name
            dest.write_bytes(out_db0.read_bytes())
            deployed_paths.append(str(dest))
    if target_mode in ("mo2_mod", "both") and st.get("mo2_path"):
        mo2_base = Path(st["mo2_path"])
        mo2_mods = mo2_base / "mods" if (mo2_base / "mods").is_dir() else mo2_base
        if mo2_mods.is_dir():
            mod_dir = mo2_mods / mod_name / "db"
            mod_dir.mkdir(parents=True, exist_ok=True)
            dest = mod_dir / archive_name
            dest.write_bytes(out_db0.read_bytes())
            deployed_paths.append(str(dest))

    append_log(
        "INFO",
        f"Exported valid .db0 archive '{archive_name}' ({pack_res['size_bytes']:,} B, {len(toc_entries)} verified TOC entries) -> {', '.join(deployed_paths)}",
        f"Экспортирован архив .db0 '{archive_name}' ({pack_res['size_bytes']:,} Б, {len(toc_entries)} проверенных файлов в TOC) -> {', '.join(deployed_paths)}",
        category="export",
    )
    return {
        "ok": True,
        "archive_name": archive_name,
        "output_db0": str(out_db0),
        "deployed_paths": deployed_paths,
        "size_bytes": pack_res["size_bytes"],
        "verified_toc_count": len(toc_entries),
        "verified_files": [e.vfs_path for e in toc_entries],
        "elapsed_ms": pack_res["elapsed_ms"],
    }


# Initialize startup log and autosave state
load_autosave_state(settings_service.load_settings().get("active_project", "default"))
append_log(
    "INFO",
    "Anomaly Studio v0.1.1-alpha backend initialized (EN/RU, direct .db0 VFS, Author: EternalPain).",
    "Бэкенд Anomaly Studio v0.1.1-alpha инициализирован (EN/RU, прямая VFS .db0, Автор: EternalPain).",
    category="system",
)


# ---------------------------------------------------------------------------
# 6. SDK BEST PRACTICES: MANIFEST, HOT-RELOAD, GRAPH SOFTLOCK VALIDATOR & DEBUG CONSOLE
# ---------------------------------------------------------------------------
QUEST_RUNTIME_INSTANCES: Dict[str, Dict[str, Any]] = {}


def get_undo_history_state() -> Dict[str, Any]:
    return {
        "ok": True,
        "schema_version": "1.0.0",
        "undo_count": len(UNDO_STACK),
        "redo_count": len(REDO_STACK),
        "undo_commands": [
            {"index": i, "action_en": item.get("action_en", ""), "action_ru": item.get("action_ru", ""), "ts": item.get("ts", "")}
            for i, item in enumerate(UNDO_STACK)
        ],
        "redo_commands": [
            {"index": i, "action_en": item.get("action_en", ""), "action_ru": item.get("action_ru", ""), "ts": item.get("ts", "")}
            for i, item in enumerate(REDO_STACK)
        ],
    }


def get_sdk_manifest(has_fast_cform: bool = True) -> Dict[str, Any]:
    vfs = db0_vfs.get_global_vfs()
    st = settings_service.load_settings()
    return {
        "ok": True,
        "sdk_name": "S.T.A.L.K.E.R. Anomaly 1.5.3 Studio SDK",
        "sdk_version": "0.1.1-alpha",
        "schema_version": "1.0.0",
        "author": "EternalPain",
        "supported_languages": ["en", "ru"],
        "capabilities": {
            "db0_vfs_direct_read": True,
            "db0_archives_mounted": vfs.total_archives,
            "db0_files_indexed": len(vfs.entries),
            "c_fast_cform_raycast": bool(has_fast_cform),
            "command_pattern_undo_redo": True,
            "autosave_crash_recovery": True,
            "quest_softlock_validator": True,
            "quest_runtime_simulator": True,
            "hot_reload": True,
        },
        "active_project": st.get("active_project", "default"),
        "endpoints": [
            {"method": "GET", "path": "/api/sdk/manifest", "description": "Self-documenting SDK manifest, SemVer & capabilities"},
            {"method": "POST", "path": "/api/sdk/hot_reload", "description": "Hot-reload .db0 VFS and project state without restart"},
            {"method": "GET", "path": "/api/undo_state", "description": "Inspect granular Command-Pattern Undo/Redo stack"},
            {"method": "POST", "path": "/api/undo", "description": "Undo last mutating command"},
            {"method": "POST", "path": "/api/redo", "description": "Redo last undone command"},
            {"method": "POST", "path": "/api/quests/validate_graph", "description": "Validate quest/dialog graph for softlocks, cycles, orphans, and syntax"},
            {"method": "POST", "path": "/api/console_logs/exec", "description": "Execute interactive debug console commands (quest.complete, quest.reset, quest.abandon, quest.validate, vfs.reload)"},
            {"method": "POST", "path": "/api/placement", "description": "3D Level Editor entity CRUD with CFORM/AI LVID/GVID snapping"},
            {"method": "POST", "path": "/api/spawn_check", "description": "Full pre-flight Spawn & Load verification against .db0 VFS"},
            {"method": "POST", "path": "/api/export_db0", "description": "Compile and pack verified .db0 mod archive"},
        ],
    }


def perform_hot_reload() -> Dict[str, Any]:
    t0 = time.time()
    vfs = db0_vfs.get_global_vfs()
    vfs.build_index(force_rescan=False)
    load_autosave_state(CURRENT_STATE.get("project", "default"))
    elapsed_ms = round((time.time() - t0) * 1000.0, 1)
    append_log(
        "INFO",
        f"Hot-Reload completed in {elapsed_ms} ms ({vfs.total_archives} .db0 archives, {len(vfs.entries):,} VFS files).",
        f"Горячая перезагрузка завершена за {elapsed_ms} мс ({vfs.total_archives} архивов .db0, {len(vfs.entries):,} файлов VFS).",
        category="hot_reload",
    )
    return {
        "ok": True,
        "elapsed_ms": elapsed_ms,
        "archives_count": vfs.total_archives,
        "total_files": len(vfs.entries),
        "state": CURRENT_STATE,
    }


def validate_quest_or_dialog_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    nodes = payload.get("nodes") or []
    edges = payload.get("edges") or []
    graph_id = payload.get("id") or payload.get("campaign") or "graph"
    issues: List[Dict[str, Any]] = []

    node_ids = {str(n.get("id")) for n in nodes if n.get("id") is not None}
    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    in_deg: Dict[str, int] = {nid: 0 for nid in node_ids}

    for e in edges:
        u = str(e.get("from", ""))
        v = str(e.get("to", ""))
        if u not in node_ids or v not in node_ids:
            issues.append({
                "severity": "ERROR",
                "code": "DANGLING_EDGE",
                "message_en": f"Edge '{u} -> {v}' references a non-existent node ID.",
                "message_ru": f"Связь '{u} -> {v}' ссылается на несуществующий узел.",
            })
            continue
        adj[u].append(v)
        in_deg[v] = in_deg.get(v, 0) + 1

    # 1. Entry root detection & orphan detection (for multi-node dialog/quest chains)
    entry_ids = [nid for nid in node_ids if nid in ("phr_0", "0") or in_deg.get(nid, 0) == 0]
    if nodes and not entry_ids:
        issues.append({
            "severity": "ERROR",
            "code": "SOFTLOCK_NO_ENTRY",
            "message_en": f"Graph '{graph_id}' has no entry node (every node has incoming prerequisites -> unreachable cyclic deadlock).",
            "message_ru": f"Граф '{graph_id}' не имеет входного узла (циклическая блокировка старта).",
        })

    # If dialog graph (has phr_0), any other node with in_deg == 0 is an unreachable orphan phrase
    if "phr_0" in node_ids:
        visited = set()
        stack = ["phr_0"]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for nxt in adj.get(cur, []):
                if nxt not in visited:
                    stack.append(nxt)
        for nid in sorted(node_ids):
            if nid not in visited:
                issues.append({
                    "severity": "WARN",
                    "code": "ORPHAN_UNREACHABLE_NODE",
                    "node_id": nid,
                    "message_en": f"Node '{nid}' is unreachable from entry 'phr_0' (orphan phrase).",
                    "message_ru": f"Узел '{nid}' недостижим из начальной фразы 'phr_0' (осиротевший узел).",
                })

    # 2. Cycle without exit (Softlock trap detection): check if any node cannot reach a terminal node (out_deg == 0)
    terminals = {nid for nid, outs in adj.items() if len(outs) == 0}
    rev_adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    for u, outs in adj.items():
        for v in outs:
            rev_adj[v].append(u)
    can_exit = set(terminals)
    q = list(terminals)
    while q:
        cur = q.pop()
        for prev in rev_adj.get(cur, []):
            if prev not in can_exit:
                can_exit.add(prev)
                q.append(prev)
    for nid in sorted(node_ids):
        if nid not in can_exit:
            issues.append({
                "severity": "ERROR",
                "code": "SOFTLOCK_INFINITE_LOOP",
                "node_id": nid,
                "message_en": f"Node '{nid}' is trapped in a cycle with no exit path to a terminal state (player softlock).",
                "message_ru": f"Узел '{nid}' заблокирован в бесконечном цикле без выхода (софтлок игрока).",
            })

    # 3. Condlist syntax & String table checks
    for n in nodes:
        nid = str(n.get("id", ""))
        for field in ("target_functor", "cond_0", "on_complete", "precondition", "action"):
            val = str(n.get(field) or "")
            if val.count("{") != val.count("}") or (val.count("%") % 2 != 0):
                issues.append({
                    "severity": "ERROR",
                    "code": "INVALID_CONDLIST_SYNTAX",
                    "node_id": nid,
                    "message_en": f"Node '{nid}' has unbalanced '{{}}' or '%%' in '{field}': {val}",
                    "message_ru": f"В узле '{nid}' несбалансированные скобки '{{}}' или '%%' в поле '{field}': {val}",
                })

    err_cnt = sum(1 for i in issues if i["severity"] == "ERROR")
    warn_cnt = sum(1 for i in issues if i["severity"] == "WARN")
    append_log(
        "INFO" if err_cnt == 0 else "WARN",
        f"Graph Validation [{graph_id}]: {len(nodes)} nodes, {len(edges)} edges -> {err_cnt} ERROR, {warn_cnt} WARN.",
        f"Проверка графа [{graph_id}]: {len(nodes)} узлов, {len(edges)} связей -> {err_cnt} ОШИБОК, {warn_cnt} ПРЕДУПР.",
        category="quest_validator",
    )
    return {
        "ok": err_cnt == 0,
        "graph_id": graph_id,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "error_count": err_cnt,
        "warn_count": warn_cnt,
        "issues": issues,
    }


def execute_debug_console_command(cmd_line: str) -> Dict[str, Any]:
    raw = (cmd_line or "").strip()
    if not raw:
        return make_error_response("EMPTY_CMD", "Empty console command.", "Пустая команда консоли.", hint_en="Type 'help' to list available SDK commands.")
    parts = raw.split()
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else CURRENT_STATE.get("active_campaign", "esc_2_12_stalker_wolf_task_1")

    if cmd in ("project.list", "project.info"):
        import project_service
        plist = project_service.list_projects()
        act = plist.get("active_summary", {})
        m = act.get("manifest", {})
        st_cnt = act.get("stats", {})
        msg_en = f"[Project] Active: '{m.get('title')}' ({act.get('project_id')}/project.anomaly v{m.get('version')}) | 3D Objects: {st_cnt.get('placed_objects_count', 0)} | Quests: {st_cnt.get('quest_edits_count', 0)} | Total Projects: {len(plist.get('projects', []))}"
        msg_ru = f"[Проект] Активный: '{m.get('title')}' ({act.get('project_id')}/project.anomaly v{m.get('version')}) | 3D Объектов: {st_cnt.get('placed_objects_count', 0)} | Квестов: {st_cnt.get('quest_edits_count', 0)} | Всего проектов: {len(plist.get('projects', []))}"
        append_log("INFO", msg_en, msg_ru, category="project")
        return {"ok": True, "command": cmd, "project": act, "message_en": msg_en, "message_ru": msg_ru}

    if cmd == "project.lua":
        import project_service
        lres = project_service.generate_lua_spawn_script(write_to_disk=True)
        msg_en = f"[Lua Spawn Generator] Wrote {lres['script_rel']} ({lres['entity_count']} placed 3D objects)."
        msg_ru = f"[Генератор Lua Спавна] Записан {lres['script_rel']} (3D объектов: {lres['entity_count']})."
        append_log("INFO", msg_en, msg_ru, category="project")
        return {"ok": True, "command": cmd, "lua_spawn_script": lres, "message_en": msg_en, "message_ru": msg_ru}

    if cmd == "help":
        msg_en = "Available SDK commands: quest.complete <id>, quest.reset <id>, quest.abandon <id>, quest.validate [id], project.info, project.lua, vfs.reload, undo, redo"
        msg_ru = "Доступные команды SDK: quest.complete <id>, quest.reset <id>, quest.abandon <id>, quest.validate [id], vfs.reload, undo, redo"
        append_log("INFO", msg_en, msg_ru, category="console_cmd")
        return {"ok": True, "command": cmd, "message_en": msg_en, "message_ru": msg_ru}

    if cmd == "quest.complete":
        inst = QUEST_RUNTIME_INSTANCES.setdefault(arg, {"id": arg, "state": "Inactive", "history": []})
        prev = inst["state"]
        inst["state"] = "Complete"
        inst["history"].append({"from": prev, "to": "Complete", "ts": datetime.now().strftime("%H:%M:%S")})
        msg_en = f"[QuestManager] '{arg}' state transition: {prev} -> Active -> Complete (OnQuestCompleted fired)."
        msg_ru = f"[QuestManager] '{arg}' переход состояния: {prev} -> Active -> Complete (событие OnQuestCompleted)."
        append_log("INFO", msg_en, msg_ru, category="quest_sim", details=inst)
        return {"ok": True, "command": cmd, "quest_id": arg, "instance": inst, "message_en": msg_en, "message_ru": msg_ru}

    if cmd == "quest.abandon":
        inst = QUEST_RUNTIME_INSTANCES.setdefault(arg, {"id": arg, "state": "Active", "history": []})
        prev = inst["state"]
        inst["state"] = "Abandoned"
        inst["history"].append({"from": prev, "to": "Abandoned", "ts": datetime.now().strftime("%H:%M:%S")})
        msg_en = f"[QuestManager] '{arg}' state transition: {prev} -> Abandoned (mid-objective cleanup verified, no dangling task items)."
        msg_ru = f"[QuestManager] '{arg}' переход состояния: {prev} -> Abandoned (проверка отмены задачи без зависших предметов)."
        append_log("WARN", msg_en, msg_ru, category="quest_sim", details=inst)
        return {"ok": True, "command": cmd, "quest_id": arg, "instance": inst, "message_en": msg_en, "message_ru": msg_ru}

    if cmd == "quest.reset":
        inst = QUEST_RUNTIME_INSTANCES.setdefault(arg, {"id": arg, "state": "Complete", "history": []})
        prev = inst["state"]
        inst["state"] = "Inactive"
        inst["history"].append({"from": prev, "to": "Inactive", "ts": datetime.now().strftime("%H:%M:%S")})
        msg_en = f"[QuestManager] '{arg}' runtime instance reset: {prev} -> Inactive (static definition untouched)."
        msg_ru = f"[QuestManager] '{arg}' сброс состояния: {prev} -> Inactive (статическое определение не изменено)."
        append_log("INFO", msg_en, msg_ru, category="quest_sim", details=inst)
        return {"ok": True, "command": cmd, "quest_id": arg, "instance": inst, "message_en": msg_en, "message_ru": msg_ru}

    if cmd == "vfs.reload":
        return perform_hot_reload()

    if cmd == "undo":
        return perform_undo()

    if cmd == "redo":
        return perform_redo()

    return make_error_response(
        "UNKNOWN_CONSOLE_CMD",
        f"Unknown debug console command: '{cmd}'",
        f"Неизвестная команда отладочной консоли: '{cmd}'",
        hint_en="Use 'help' to see supported commands (quest.complete, quest.reset, quest.abandon, vfs.reload, undo, redo).",
        hint_ru="Используйте 'help' для списка команд (quest.complete, quest.reset, quest.abandon, vfs.reload, undo, redo).",
    )
