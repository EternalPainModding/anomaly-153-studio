#!/usr/bin/env python3
"""
Anomaly 1.5.3 Studio — Smart-Terrain, Gulag-Job & 3D-Waypoint-Chain Generator
Provides SDK 0.7 LevelEditor parity for Smart Terrains + Waypoint Chains:
1. list_level_smart_terrains(level_name="l01_escape") -> dict
2. generate_smart_terrain_and_waypoints(payload) -> dict
"""
import ctypes
import json
import re
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STUDIO_DIR = ROOT
TOOLS_INDEX_DIR = ROOT / "tools" / "_index"
RE_INDEX_DIR = ROOT / "index"
UNPACKED_DIR = ROOT / ".studio_cache" / "vfs_mount"
CONFIGS_DIR = UNPACKED_DIR / "configs"
SCRIPTS_DIR = CONFIGS_DIR / "scripts"

LEVEL_SCRIPT_FOLDER_ALIASES = {
    "k00_marsh": "marsh",
    "k01_darkscape": "darkscape",
    "k02_trucks_cemetery": "trucks_cemetery",
    "l01_escape": "escape",
    "l02_garbage": "garbage",
    "l03_agroprom": "agroprom",
    "l03u_agr_underground": "agroprom_underground",
    "l04_darkvalley": "darkvalley",
    "l04u_labx18": "labx18",
    "l05_bar": "bar",
    "l06_rostok": "rostok",
    "l07_military": "military",
    "l08_yantar": "yantar",
    "l08u_brainlab": "brainlab",
    "l09_deadcity": "dead_city",
    "l10_limansk": "limansk",
    "l10_radar": "radar",
    "l10_red_forest": "red_forest",
    "l10u_bunker": "bunker",
    "l11_hospital": "hospital",
    "l11_pripyat": "pripyat",
    "l12_stancia": "stancia_1",
    "l12_stancia_2": "stancia_2",
    "l12u_control_monolith": "control_monolith",
    "l12u_sarcofag": "sarcofag",
    "l13_generators": "generators",
    "l13u_warlab": "warlab",
    "zaton": "zaton",
    "jupiter": "jupiter",
    "jupiter_underground": "jupiter_underground",
    "pripyat": "pripyat",
    "labx8": "labx8",
}

_FAST_CFORM_LIB = None
_FAST_CFORM_SO = Path(__file__).resolve().parent / "libfast_cform.so"
if _FAST_CFORM_SO.is_file():
    try:
        _FAST_CFORM_LIB = ctypes.CDLL(str(_FAST_CFORM_SO))
        _FAST_CFORM_LIB.find_nearest_ai_node.argtypes = [
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        ]
        _FAST_CFORM_LIB.find_nearest_ai_node.restype = ctypes.c_uint32
    except Exception:
        _FAST_CFORM_LIB = None

_GVID_CACHE: dict[str, list[dict[str, Any]]] | None = None
_LEVEL_AI_CACHE: dict[str, bytes] = {}


def _load_gvid_table() -> dict[str, list[dict[str, Any]]]:
    global _GVID_CACHE
    if _GVID_CACHE is not None:
        return _GVID_CACHE
    for candidate in (
        STUDIO_DIR / "index" / "game_graph_gvids.json",
        RE_INDEX_DIR / "game_graph_gvids.json",
        TOOLS_INDEX_DIR / "game_graph_gvids.json",
    ):
        if candidate.is_file():
            try:
                raw = json.loads(candidate.read_text(encoding="utf-8"))
                _GVID_CACHE = raw.get("by_level", raw if isinstance(raw, dict) else {})
                return _GVID_CACHE
            except Exception:
                pass
    _GVID_CACHE = {}
    return _GVID_CACHE


def _load_level_ai_bytes(level_name: str) -> bytes | None:
    if level_name in _LEVEL_AI_CACHE:
        return _LEVEL_AI_CACHE[level_name]
    for candidate in (
        UNPACKED_DIR / "levels" / level_name / "level.ai",
        ROOT / "gamedata" / "levels" / level_name / "level.ai",
    ):
        if candidate.is_file():
            data = candidate.read_bytes()
            if len(data) >= 56:
                _LEVEL_AI_CACHE[level_name] = data
                return data
    return None


def resolve_lvid_and_gvid(level_name: str, pos: list[float] | tuple[float, float, float]) -> dict[str, Any]:
    """Resolves exact level_vertex_id (level.ai) and game_vertex_id (game_graph_gvids.json) for a 3D point."""
    qx = float(pos[0]) if len(pos) > 0 else 0.0
    qy = float(pos[1]) if len(pos) > 1 else 0.0
    qz = float(pos[2]) if len(pos) > 2 else 0.0

    # 1. Resolve GVID
    gvid = 0
    gvid_min = 0
    gvid_max = 0
    gvid_table = _load_gvid_table()
    verts = gvid_table.get(level_name, [])
    if verts:
        gvid_min = int(verts[0]["gvid"])
        gvid_max = int(verts[-1]["gvid"])
        best_v = min(
            verts,
            key=lambda v: (
                (float(v["local_pos"][0]) - qx) ** 2
                + (float(v["local_pos"][1]) - qy) ** 2
                + (float(v["local_pos"][2]) - qz) ** 2
            ),
        )
        gvid = int(best_v["gvid"])

    # 2. Resolve LVID
    lvid = 0
    node_pos = [round(qx, 4), round(qy, 4), round(qz, 4)]
    dist = 0.0
    ai_data = _load_level_ai_bytes(level_name)
    if ai_data is not None:
        version, vertex_count, cell_size, factor_y, min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack_from(
            "<IIffffffff", ai_data, 0
        )
        if vertex_count > 0:
            rec_size = (len(ai_data) - 56) // vertex_count
            if rec_size not in (21, 23, 25):
                rec_size = 25 if version == 13 else (21 if version <= 8 else 23)
            row_length = int((max_z - min_z) / cell_size + 1.5001)
            nodes_bytes = ai_data[56:]

            if _FAST_CFORM_LIB is not None:
                out_pos = (ctypes.c_float * 3)()
                out_dist = ctypes.c_float()
                best_id = int(
                    _FAST_CFORM_LIB.find_nearest_ai_node(
                        nodes_bytes,
                        vertex_count,
                        rec_size,
                        row_length,
                        cell_size,
                        factor_y,
                        min_x,
                        min_y,
                        min_z,
                        qx,
                        qy,
                        qz,
                        out_pos,
                        ctypes.byref(out_dist),
                    )
                )
                lvid = best_id
                node_pos = [round(float(out_pos[0]), 4), round(float(out_pos[1]), 4), round(float(out_pos[2]), 4)]
                dist = round(float(out_dist.value), 4)
            else:
                pxz_off = 19 if rec_size == 25 else (rec_size - 5)
                inv_65535 = factor_y / 65535.0
                best_d2 = 1e30
                for i in range(vertex_count):
                    off = i * rec_size + pxz_off
                    b0, b1, b2, b3, b4 = nodes_bytes[off : off + 5]
                    packed_xz = b0 | (b1 << 8) | (b2 << 16)
                    packed_y = b3 | (b4 << 8)
                    row = packed_xz // row_length
                    col = packed_xz % row_length
                    nx = row * cell_size + min_x
                    ny = packed_y * inv_65535 + min_y
                    nz = col * cell_size + min_z
                    d2 = (nx - qx) ** 2 + (ny - qy) ** 2 + (nz - qz) ** 2
                    if d2 < best_d2:
                        best_d2 = d2
                        lvid = i
                        node_pos = [round(nx, 4), round(ny, 4), round(nz, 4)]
                dist = round(best_d2 ** 0.5, 4)

    return {
        "level_vertex_id": lvid,
        "game_vertex_id": gvid,
        "gvid_min": gvid_min,
        "gvid_max": gvid_max,
        "node_pos": node_pos,
        "distance": dist,
    }


def _find_spawns_parsed_file(level_name: str, suffix: str) -> Path | None:
    file_key = level_name.replace(":", "_")
    for base in (STUDIO_DIR / ".studio_cache" / "spawns_parsed", TOOLS_INDEX_DIR / "spawns_parsed", RE_INDEX_DIR / "spawns_parsed"):
        candidate = base / f"{file_key}_{suffix}.json"
        if candidate.is_file():
            return candidate
    return None


def _find_smart_script_dirs(level_name: str) -> list[Path]:
    dirs = []
    short_alias = LEVEL_SCRIPT_FOLDER_ALIASES.get(level_name, re.sub(r"^[kl]\d+u?_", "", level_name))
    for folder in dict.fromkeys([level_name, short_alias]):
        d = SCRIPTS_DIR / folder / "smart"
        if d.is_dir():
            dirs.append(d)
    return dirs


def _parse_smart_ltx_file(ltx_path: Path) -> dict[str, Any]:
    raw = ltx_path.read_bytes().decode("cp1251", errors="ignore")
    sections: dict[str, dict[str, str]] = {}
    exclusive_jobs: list[dict[str, str]] = []
    current_sec = None

    for line in raw.splitlines():
        clean = line.split(";")[0].strip()
        if not clean:
            continue
        if clean.startswith("[") and "]" in clean:
            current_sec = clean[1 : clean.index("]")].strip()
            sections.setdefault(current_sec, {})
            continue
        if current_sec is not None:
            if "=" in clean:
                k, v = clean.split("=", 1)
                k, v = k.strip(), v.strip()
                sections[current_sec][k] = v
                if current_sec == "exclusive":
                    exclusive_jobs.append({"job": k, "logic_cfg": v})
            else:
                sections[current_sec][clean] = ""

    st_sec = sections.get("smart_terrain", {})
    respawn_sec_name = st_sec.get("respawn_params", "")
    respawn_Squad_blocks = []
    if respawn_sec_name and respawn_sec_name in sections:
        for sub_sec in sections[respawn_sec_name]:
            if sub_sec in sections:
                respawn_Squad_blocks.append(
                    {
                        "section": sub_sec,
                        "spawn_squads": sections[sub_sec].get("spawn_squads", ""),
                        "spawn_num": sections[sub_sec].get("spawn_num", "1"),
                    }
                )

    return {
        "name": ltx_path.stem,
        "file": str(ltx_path.relative_to(CONFIGS_DIR)) if ltx_path.is_relative_to(CONFIGS_DIR) else str(ltx_path),
        "squad_id": int(st_sec["squad_id"]) if st_sec.get("squad_id", "").isdigit() else st_sec.get("squad_id", 1),
        "max_population": int(st_sec["max_population"]) if st_sec.get("max_population", "").isdigit() else st_sec.get("max_population", 3),
        "respawn_params": respawn_sec_name,
        "respawn_idle": int(st_sec["respawn_idle"]) if st_sec.get("respawn_idle", "").isdigit() else st_sec.get("respawn_idle", 86400),
        "safe_restr": st_sec.get("safe_restr", ""),
        "def_restr": st_sec.get("def_restr", ""),
        "respawn_squad_blocks": respawn_Squad_blocks,
        "exclusive_jobs": exclusive_jobs,
    }


def list_level_smart_terrains(level_name: str = "l01_escape") -> dict[str, Any]:
    """
    Reads existing Smart Terrains and Patrol-Paths of a level from:
    - tools/_index/spawns_parsed/<level>_spawns.json (or _re_index/spawns_parsed/<level>_spawns.json)
    - <level>_patrols.json
    - tools/_unpacked/configs/scripts/<level>/smart/*.ltx
    """
    sp_file = _find_spawns_parsed_file(level_name, "spawns")
    pt_file = _find_spawns_parsed_file(level_name, "patrols")

    spawns = json.loads(sp_file.read_text(encoding="utf-8")) if sp_file else []
    patrols = json.loads(pt_file.read_text(encoding="utf-8")) if pt_file else []

    smart_configs_by_name: dict[str, dict[str, Any]] = {}
    for sdir in _find_smart_script_dirs(level_name):
        for ltx_file in sorted(sdir.glob("*.ltx")):
            parsed_cfg = _parse_smart_ltx_file(ltx_file)
            smart_configs_by_name[parsed_cfg["name"]] = parsed_cfg

    smart_terrains = []
    seen_names = set()
    for sp in spawns:
        sec = sp.get("section") or sp.get("section_name") or ""
        name = sp.get("name") or sp.get("entity_name") or ""
        if sec == "smart_terrain":
            seen_names.add(name)
            cfg_info = smart_configs_by_name.get(name, {})
            # Match patrol paths belonging to this smart terrain
            matched_patrols = [
                p["name"]
                for p in patrols
                if isinstance(p, dict) and p.get("name", "").startswith(name)
            ]
            smart_terrains.append(
                {
                    "name": name,
                    "spawn_id": sp.get("spawn_id", sp.get("idx", -1)),
                    "section": sec,
                    "position": sp.get("position", [0.0, 0.0, 0.0]),
                    "rotation": sp.get("rotation", sp.get("angle", [0.0, 0.0, 0.0])),
                    "level_vertex_id": sp.get("level_vertex_id", sp.get("node_id", 0)),
                    "game_vertex_id": sp.get("game_vertex_id", sp.get("graph_id", 0)),
                    "custom_data": sp.get("custom_data", ""),
                    "squad_id": cfg_info.get("squad_id", 1),
                    "max_population": cfg_info.get("max_population", 3),
                    "respawn_params": cfg_info.get("respawn_params", ""),
                    "respawn_idle": cfg_info.get("respawn_idle", 86400),
                    "respawn_squad_blocks": cfg_info.get("respawn_squad_blocks", []),
                    "exclusive_jobs": cfg_info.get("exclusive_jobs", []),
                    "cfg_file": cfg_info.get("file", ""),
                    "patrol_names": matched_patrols,
                }
            )

    # Also include any smart terrain LTX configs that did not have a direct spawn match
    for cfg_name, cfg_info in smart_configs_by_name.items():
        if cfg_name not in seen_names:
            smart_terrains.append(
                {
                    "name": cfg_name,
                    "spawn_id": -1,
                    "section": "smart_terrain",
                    "position": [0.0, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "level_vertex_id": 0,
                    "game_vertex_id": 0,
                    "custom_data": f"[smart_terrain]\ncfg = {cfg_info.get('file', '')}",
                    **cfg_info,
                }
            )

    return {
        "ok": True,
        "level": level_name,
        "total_smart_terrains": len(smart_terrains),
        "total_patrols": len(patrols),
        "total_smart_configs": len(smart_configs_by_name),
        "smart_terrains": smart_terrains,
        "patrols": patrols,
    }


def _normalize_chains(payload: dict[str, Any], smart_name: str, center_pos: list[float]) -> list[dict[str, Any]]:
    """
    Normalizes waypoint chains from payload into a structured list supporting:
    guard_walk, guard_look, patrol_walk, sniper_walk, camp_work.
    """
    raw_chains = payload.get("waypoint_chains") or payload.get("chains") or payload.get("waypoints") or []
    cx, cy, cz = float(center_pos[0]), float(center_pos[1]), float(center_pos[2])

    normalized: list[dict[str, Any]] = []

    if isinstance(raw_chains, dict):
        for role_key, pts in raw_chains.items():
            if isinstance(pts, list):
                normalized.append({"role": role_key, "name": f"{smart_name}_{role_key}", "points": pts})
            elif isinstance(pts, dict):
                normalized.append(
                    {
                        "role": pts.get("role", role_key),
                        "name": pts.get("name", f"{smart_name}_{role_key}"),
                        "points": pts.get("points", []),
                    }
                )
    elif isinstance(raw_chains, list):
        for item in raw_chains:
            if isinstance(item, dict):
                role = item.get("role") or item.get("type") or item.get("chain_type") or item.get("name", "patrol_walk")
                cname = item.get("name") or f"{smart_name}_{role}"
                if not cname.startswith(smart_name) and role in (
                    "guard_walk",
                    "guard_look",
                    "patrol_walk",
                    "sniper_walk",
                    "camp_work",
                ):
                    cname = f"{smart_name}_{role}"
                normalized.append(
                    {
                        "role": role,
                        "name": cname,
                        "points": item.get("points", []),
                        "prior": item.get("prior"),
                        "move_state": item.get("move_state"),
                    }
                )

    # Also check direct top-level keys (`guard_walk`, `guard_look`, `patrol_walk`, `sniper_walk`, `camp_work`)
    for key in ("guard_walk", "guard_look", "patrol_walk", "sniper_walk", "camp_work"):
        if key in payload and not any(c["role"] == key for c in normalized):
            val = payload[key]
            pts = val if isinstance(val, list) else (val.get("points", []) if isinstance(val, dict) else [])
            normalized.append({"role": key, "name": f"{smart_name}_{key}", "points": pts})

    # Default complete 5-chain layout around center_pos if caller passed empty chains
    if not normalized:
        normalized = [
            {
                "role": "guard_walk",
                "name": f"{smart_name}_guard_1_walk",
                "points": [{"name": "wp00", "position": [cx + 3.5, cy, cz + 2.0], "flags": 1}],
            },
            {
                "role": "guard_look",
                "name": f"{smart_name}_guard_1_look",
                "points": [{"name": "look00", "position": [cx + 12.0, cy, cz + 8.0], "flags": 1}],
            },
            {
                "role": "patrol_walk",
                "name": f"{smart_name}_patrol_1_walk",
                "points": [
                    {"name": "wp00", "position": [cx - 6.0, cy, cz - 4.0], "flags": 0},
                    {"name": "wp01", "position": [cx + 6.0, cy, cz - 4.0], "flags": 0},
                    {"name": "wp02", "position": [cx + 6.0, cy, cz + 6.0], "flags": 0},
                ],
            },
            {
                "role": "sniper_walk",
                "name": f"{smart_name}_sniper_1_walk",
                "points": [
                    {"name": "sn00", "position": [cx - 4.0, cy + 1.5, cz + 5.0], "flags": 1},
                    {"name": "sn01", "position": [cx + 18.0, cy, cz + 22.0], "flags": 1},
                ],
            },
            {
                "role": "camp_work",
                "name": f"{smart_name}_camp_work_1",
                "points": [{"name": "camp00", "position": [cx, cy, cz], "flags": 0}],
            },
        ]

    return normalized


def generate_smart_terrain_and_waypoints(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Generates a complete S.T.A.L.K.E.R. Anomaly 1.5.3 Smart-Terrain + Gulag-Job + 3D-Waypoint-Chain bundle:
    - Resolves exact LVID (level.ai) and GVID (game_graph_gvids.json) for center_pos and every waypoint.
    - Generates:
      a) configs/scripts/<level>/smart/<smart_name>.ltx ([smart_terrain], squad_id, max_population, [exclusive] jobs)
      b) configs/scripts/<level>/<smart_name>_logic.ltx ([logic@...], [walker@...], [camper@...], [animpoint@...])
      c) Waypoint definitions (SDK 0.7 / all.spawn patrol format + JSON patrol graph) and Lua registration script.
    """
    level_name = (payload.get("level_name") or payload.get("level") or "l01_escape").strip()
    smart_name = (payload.get("smart_name") or payload.get("name") or "esc_smart_terrain_convoy_outpost").strip()
    center_pos = payload.get("center_pos") or payload.get("position") or [-145.0, -12.0, -110.0]
    max_population = int(payload.get("max_population", 5))
    squad_id = int(payload.get("squad_id", 55))
    respawn_idle = int(payload.get("respawn_idle", 86400))
    arrival_dist = int(payload.get("arrive_dist", 45))

    respawn_params = payload.get("respawn_params") or {}
    if isinstance(respawn_params, str):
        respawn_sec_name = respawn_params.strip() or f"respawn@{smart_name}"
        spawn_subsec = "spawn_stalker@advanced"
        spawn_squads = payload.get("spawn_squads", "stalker_sim_squad_novice, stalker_sim_squad_advanced")
        spawn_num = int(payload.get("spawn_num", 2))
    elif isinstance(respawn_params, dict):
        respawn_sec_name = respawn_params.get("section_name") or f"respawn@{smart_name}"
        spawn_subsec = respawn_params.get("preset") or "spawn_stalker@advanced"
        spawn_squads = respawn_params.get("spawn_squads") or "stalker_sim_squad_novice, stalker_sim_squad_advanced"
        spawn_num = int(respawn_params.get("spawn_num", 2))
        if "respawn_idle" in respawn_params:
            respawn_idle = int(respawn_params["respawn_idle"])
    else:
        respawn_sec_name = f"respawn@{smart_name}"
        spawn_subsec = "spawn_stalker@advanced"
        spawn_squads = "stalker_sim_squad_novice, stalker_sim_squad_advanced"
        spawn_num = 2

    # Resolve center_pos LVID & GVID
    center_resolved = resolve_lvid_and_gvid(level_name, center_pos)

    # Normalize & resolve all waypoint chains
    chains = _normalize_chains(payload, smart_name, center_pos)
    resolved_chains = []
    patrol_json_entries = []
    way_ltx_blocks = []

    for c_idx, chain in enumerate(chains):
        role = chain.get("role", "patrol_walk")
        cname = chain.get("name", f"{smart_name}_{role}_{c_idx + 1}")
        raw_pts = chain.get("points", [])
        if not raw_pts:
            raw_pts = [{"name": "wp00", "position": center_pos, "flags": 0}]

        res_pts = []
        edges = []
        for p_idx, pt in enumerate(raw_pts):
            if isinstance(pt, (list, tuple)):
                p_pos = [float(pt[0]), float(pt[1]), float(pt[2])]
                p_name = f"wp{p_idx:02d}|a=patrol"
                p_flags = 0
            else:
                p_pos = pt.get("position") or pt.get("pos") or [pt.get("x", center_pos[0]), pt.get("y", center_pos[1]), pt.get("z", center_pos[2])]
                p_pos = [float(p_pos[0]), float(p_pos[1]), float(p_pos[2])]
                p_name = pt.get("name") or f"wp{p_idx:02d}"
                p_flags = int(pt.get("flags", 1 if "look" in role or "sniper" in role else 0))

            nav = resolve_lvid_and_gvid(level_name, p_pos)
            pt_obj = {
                "id": p_idx,
                "name": p_name,
                "position": [round(p_pos[0], 4), round(p_pos[1], 4), round(p_pos[2], 4)],
                "snapped_node_pos": nav["node_pos"],
                "lvid": nav["level_vertex_id"],
                "gvid": nav["game_vertex_id"],
                "flags": p_flags,
            }
            res_pts.append(pt_obj)
            if p_idx + 1 < len(raw_pts):
                edges.append({"from": p_idx, "to": p_idx + 1, "probability": 1.0})
            elif len(raw_pts) > 2 and "walk" in role:
                edges.append({"from": p_idx, "to": 0, "probability": 1.0})

        resolved_chains.append(
            {
                "role": role,
                "name": cname,
                "points": res_pts,
                "edges": edges,
            }
        )
        patrol_json_entries.append(
            {
                "name": cname,
                "role": role,
                "points": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "position": p["position"],
                        "flags": p["flags"],
                        "lvid": p["lvid"],
                        "gvid": p["gvid"],
                    }
                    for p in res_pts
                ],
                "edges": edges,
            }
        )

        # Build SDK 0.7 / all.spawn compatible .way / LTX representation
        way_lines = [
            f"[{cname}]",
            f"points = {', '.join(f'p{p['id']}' for p in res_pts)}",
        ]
        for p in res_pts:
            links_for_p = [f"p{e['to']}(1)" for e in edges if e["from"] == p["id"]]
            way_lines.extend(
                [
                    f"[p{p['id']}]",
                    f"name = {p['name']}",
                    f"flags = {hex(p['flags'])}",
                    f"position = {p['position'][0]:.4f}, {p['position'][1]:.4f}, {p['position'][2]:.4f}",
                    f"level_vertex_id = {p['lvid']}",
                    f"game_vertex_id = {p['gvid']}",
                ]
            )
            if links_for_p:
                way_lines.append(f"links = {', '.join(links_for_p)}")
        way_ltx_blocks.append("\n".join(way_lines))

    # Build Gulag Jobs & Logic Sections from resolved chains
    logic_rel_path = f"{level_name}\\{smart_name}_logic.ltx"
    exclusive_lines = []
    logic_blocks = [
        "; ============================================================================",
        f"; Smart-Terrain Exclusive Gulag Logic: {smart_name} ({level_name})",
        f"; Center LVID={center_resolved['level_vertex_id']}, GVID={center_resolved['game_vertex_id']}",
        "; ============================================================================",
        "",
    ]

    # Lookup helper for guard_look chain if paired with guard_walk
    look_chains = {c["role"]: c["name"] for c in resolved_chains if "look" in c["role"]}
    default_look_path = look_chains.get("guard_look")

    job_definitions = []
    guard_idx = 0
    patrol_idx = 0
    sniper_idx = 0
    camp_idx = 0

    for c in resolved_chains:
        role = c["role"]
        cname = c["name"]
        first_pt = c["points"][0]

        if role == "guard_look":
            # Look chain is paired with guard_walk or sniper_walk
            continue

        if role == "guard_walk" or role.startswith("guard"):
            guard_idx += 1
            job_sec = f"{smart_name}_guard_{guard_idx}"
            look_path = default_look_path or f"{cname}_look"
            exclusive_lines.append(f"{job_sec} = {logic_rel_path}")
            logic_blocks.extend(
                [
                    f"[logic@{job_sec}]",
                    f"active = walker@{job_sec}",
                    "prior = 110",
                    "",
                    f"[walker@{job_sec}]",
                    f"path_walk = {cname}",
                    f"path_look = {look_path}",
                    "def_state_standing = guard",
                    "def_state_moving = patrol",
                    f"meet = meet@{smart_name}",
                    "",
                ]
            )
            job_definitions.append(
                {
                    "job_section": job_sec,
                    "scheme": "walker",
                    "role": "guard_walk",
                    "prior": 110,
                    "path_walk": cname,
                    "path_look": look_path,
                    "lvid": first_pt["lvid"],
                    "gvid": first_pt["gvid"],
                    "position": first_pt["position"],
                }
            )

        elif role == "sniper_walk" or role.startswith("sniper"):
            sniper_idx += 1
            job_sec = f"{smart_name}_sniper_{sniper_idx}"
            look_path = default_look_path or f"{cname}_look"
            exclusive_lines.append(f"{job_sec} = {logic_rel_path}")
            logic_blocks.extend(
                [
                    f"[logic@{job_sec}]",
                    f"active = camper@{job_sec}",
                    "prior = 120",
                    "",
                    f"[camper@{job_sec}]",
                    f"path_walk = {cname}",
                    f"path_look = {look_path}",
                    "radius = 25",
                    "def_state_moving = sneak",
                    "def_state_campering = hide_na",
                    "def_state_campering_fire = hide_sniper_fire",
                    "sniper = true",
                    "",
                ]
            )
            job_definitions.append(
                {
                    "job_section": job_sec,
                    "scheme": "camper",
                    "role": "sniper_walk",
                    "prior": 120,
                    "path_walk": cname,
                    "path_look": look_path,
                    "lvid": first_pt["lvid"],
                    "gvid": first_pt["gvid"],
                    "position": first_pt["position"],
                }
            )

        elif role == "camp_work" or role.startswith("camp") or role.startswith("animpoint"):
            camp_idx += 1
            job_sec = f"{smart_name}_camp_work_{camp_idx}"
            cover_name = f"{smart_name}_animpoint_kamp{camp_idx}"
            exclusive_lines.append(f"{job_sec} = {logic_rel_path}")
            logic_blocks.extend(
                [
                    f"[logic@{job_sec}]",
                    f"active = animpoint@{job_sec}",
                    "prior = 75",
                    "",
                    f"[animpoint@{job_sec}]",
                    f"cover_name = {cover_name}",
                    "use_camp = true",
                    f"meet = meet@{smart_name}",
                    "",
                ]
            )
            job_definitions.append(
                {
                    "job_section": job_sec,
                    "scheme": "animpoint",
                    "role": "camp_work",
                    "prior": 75,
                    "cover_name": cover_name,
                    "lvid": first_pt["lvid"],
                    "gvid": first_pt["gvid"],
                    "position": first_pt["position"],
                }
            )

        else:
            patrol_idx += 1
            job_sec = f"{smart_name}_patrol_{patrol_idx}"
            exclusive_lines.append(f"{job_sec} = {logic_rel_path}")
            logic_blocks.extend(
                [
                    f"[logic@{job_sec}]",
                    f"active = walker@{job_sec}",
                    "prior = 95",
                    "",
                    f"[walker@{job_sec}]",
                    f"path_walk = {cname}",
                    *([f"path_look = {default_look_path}"] if default_look_path else []),
                    "def_state_moving1 = patrol",
                    "def_state_moving2 = assault",
                    f"meet = meet@{smart_name}",
                    "",
                ]
            )
            job_definitions.append(
                {
                    "job_section": job_sec,
                    "scheme": "walker",
                    "role": "patrol_walk",
                    "prior": 95,
                    "path_walk": cname,
                    "path_look": default_look_path or "",
                    "lvid": first_pt["lvid"],
                    "gvid": first_pt["gvid"],
                    "position": first_pt["position"],
                }
            )

    logic_blocks.extend(
        [
            f"[meet@{smart_name}]",
            "close_anim = nil",
            "close_victim = nil",
            "far_anim = nil",
            "far_victim = nil",
            "close_distance = 0",
            "far_distance = 0",
            "use = true",
            "allow_break = true",
            "meet_on_talking = false",
            "",
        ]
    )

    smart_ltx_lines = [
        "[smart_terrain]",
        f"squad_id = {squad_id}",
        f"max_population = {max_population}",
        f"respawn_params = {respawn_sec_name}",
        f"respawn_idle = {respawn_idle}",
        f"arrive_dist = {arrival_dist}",
        "",
        f"[{respawn_sec_name}]",
        f"{spawn_subsec}",
        "",
        f"[{spawn_subsec}]",
        f"spawn_squads = {spawn_squads}",
        f"spawn_num = {spawn_num}",
        "",
        "[exclusive]",
        *exclusive_lines,
        "",
    ]

    smart_ltx_content = "\n".join(smart_ltx_lines)
    logic_ltx_content = "\n".join(logic_blocks)
    waypoints_ltx_content = "\n\n".join(way_ltx_blocks) + "\n"

    # Build Lua registration & runtime patrol/gulag spawner script
    lua_waypoints_entries = []
    for c in resolved_chains:
        pts_lua = ", ".join(
            f"{{name={json.dumps(p['name'])}, pos={{x={p['position'][0]:.3f}, y={p['position'][1]:.3f}, z={p['position'][2]:.3f}}}, lvid={p['lvid']}, gvid={p['gvid']}, flags={p['flags']}}}"
            for p in c["points"]
        )
        lua_waypoints_entries.append(f"    [{json.dumps(c['name'])}] = {{ role = {json.dumps(c['role'])}, points = {{ {pts_lua} }} }}")

    lua_script_content = f"""-- ============================================================================
-- Anomaly 1.5.3 Studio — Smart-Terrain & 3D Waypoint Registration Script
-- Smart Terrain: {smart_name} ({level_name})
-- Center Pos   : ({center_pos[0]:.3f}, {center_pos[1]:.3f}, {center_pos[2]:.3f})
-- Center LVID  : {center_resolved['level_vertex_id']} | Center GVID: {center_resolved['game_vertex_id']}
-- ============================================================================

local SMART_NAME = {json.dumps(smart_name)}
local LEVEL_NAME = {json.dumps(level_name)}
local CENTER_POS = vector():set({center_pos[0]:.3f}, {center_pos[1]:.3f}, {center_pos[2]:.3f})
local CENTER_LVID = {center_resolved['level_vertex_id']}
local CENTER_GVID = {center_resolved['game_vertex_id']}
local MAX_POPULATION = {max_population}

SMART_WAYPOINT_CHAINS = {{
{",\n".join(lua_waypoints_entries)}
}}

function get_smart_terrain_descriptor()
    return {{
        name = SMART_NAME,
        level = LEVEL_NAME,
        lvid = CENTER_LVID,
        gvid = CENTER_GVID,
        max_population = MAX_POPULATION,
        chains = SMART_WAYPOINT_CHAINS,
    }}
end

local function on_game_load()
    if level.name() ~= LEVEL_NAME then return end
    printf("[Anomaly Studio] Registered Smart Terrain %s on %s (LVID=%d, GVID=%d, chains=%d)",
        SMART_NAME, LEVEL_NAME, CENTER_LVID, CENTER_GVID, #{len(resolved_chains)})
end

function on_game_start()
    RegisterScriptCallback("on_game_load", on_game_load)
end
"""

    smart_rel = f"configs/scripts/{level_name}/smart/{smart_name}.ltx"
    logic_rel = f"configs/scripts/{level_name}/{smart_name}_logic.ltx"
    waypoints_rel = f"configs/scripts/{level_name}/{smart_name}_waypoints.ltx"
    lua_rel = f"scripts/{smart_name}_register.script"

    written_files = []
    if payload.get("write_files", True):
        export_root = Path(
            payload.get("output_dir")
            or (STUDIO_DIR / "exports" / f"SmartTerrain_{smart_name}_{level_name}" / "gamedata")
        )
        for rel_p, text_content, enc in (
            (smart_rel, smart_ltx_content, "cp1251"),
            (logic_rel, logic_ltx_content, "cp1251"),
            (waypoints_rel, waypoints_ltx_content, "cp1251"),
            (lua_rel, lua_script_content, "utf-8"),
        ):
            target = export_root / rel_p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text_content.encode(enc, errors="replace"))
            written_files.append(str(target))

        # Also mirror into tools/_unpacked/configs/scripts/<level>/smart/ so list_level_smart_terrains sees it
        unpacked_smart = UNPACKED_DIR / smart_rel
        unpacked_logic = UNPACKED_DIR / logic_rel
        unpacked_smart.parent.mkdir(parents=True, exist_ok=True)
        unpacked_smart.write_bytes(smart_ltx_content.encode("cp1251", errors="replace"))
        unpacked_logic.parent.mkdir(parents=True, exist_ok=True)
        unpacked_logic.write_bytes(logic_ltx_content.encode("cp1251", errors="replace"))

    return {
        "ok": True,
        "level_name": level_name,
        "smart_name": smart_name,
        "center_pos": [round(float(center_pos[0]), 4), round(float(center_pos[1]), 4), round(float(center_pos[2]), 4)],
        "center_lvid": center_resolved["level_vertex_id"],
        "center_gvid": center_resolved["game_vertex_id"],
        "gvid_range": [center_resolved["gvid_min"], center_resolved["gvid_max"]],
        "max_population": max_population,
        "squad_id": squad_id,
        "jobs": job_definitions,
        "waypoint_chains": resolved_chains,
        "patrols_json": patrol_json_entries,
        "files": {
            smart_rel: smart_ltx_content,
            logic_rel: logic_ltx_content,
            waypoints_rel: waypoints_ltx_content,
            lua_rel: lua_script_content,
        },
        "smart_ltx_path": smart_rel,
        "logic_ltx_path": logic_rel,
        "waypoints_ltx_path": waypoints_rel,
        "lua_script_path": lua_rel,
        "smart_ltx": smart_ltx_content,
        "logic_ltx": logic_ltx_content,
        "waypoints_ltx": waypoints_ltx_content,
        "lua_script": lua_script_content,
        "written_files": written_files,
    }
