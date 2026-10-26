#!/usr/bin/env python3
"""
S.T.A.L.K.E.R. Anomaly 1.5.3 Studio — 7-Stage X-Ray Mod Typechecker Service
(`xray_typechecker_service.py`)

Validates a `gamedata/` mod directory across 7 stages before export to prevent
common X-Ray Monolith 1.5.3 engine crashes and quest/logic bugs:
  1. gvid_check: Validates all GVID values in scripts & LTX against level_name range
     in `anomaly_studio/index/game_graph_gvids.json` (e.g. l01_escape = 362..640).
  2. dialog_xml_include_check: Verifies all dialog IDs added via
     `on_specific_character_dialog_list` (`dialog_list:add("...")`) are reachable
     via `gamedata/configs/gameplay/dialogs_<level>.xml` (including `#include` resolution)
     for `CXML_IdToIndex<CPhraseDialog>::GetById`.
  3. lua_callback_check: Verifies all `<action>` and `<precondition>` references
     (`module.func_name`) in dialog XMLs exist as `function func_name(` in
     `gamedata/scripts/module.script` (or vanilla unpacked scripts).
  4. string_table_check: Verifies all `<text>` IDs in dialog XMLs and `title`, `descr`,
     `inv_name`, `description` keys in mod LTX files against `gamedata/configs/text/eng/*.xml`.
  5. ogf_visual_check: Verifies all `visual = ...` paths in `gamedata/configs/**/*.ltx`
     exist in `tools/_unpacked/meshes/` and/or `gamedata/meshes/`, and automatically
     copies missing meshes from `tools/_unpacked/meshes/` into `gamedata/meshes/`.
  6. pickup_callback_check: Checks quest scripts for `actor_on_item_take` and
     `story_objects.register` usage so quest item pickups advance reliably across levels.
  7. alao_lua_check: Runs an ALAO-style static Lua analyzer (`db.actor` caching,
     `table.insert` usage, and bracket/block syntax balance) over `gamedata/scripts/*.script`.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

ROOT_DIR = Path(__file__).resolve().parent.parent
GVID_INDEX_PATH = ROOT_DIR / "anomaly_studio" / "index" / "game_graph_gvids.json"
UNPACKED_DIR = ROOT_DIR / ".studio_cache" / "vfs_mount"
UNPACKED_MESHES_DIR = UNPACKED_DIR / "meshes"
UNPACKED_CONFIGS_DIR = UNPACKED_DIR / "configs"
UNPACKED_SCRIPTS_DIR = UNPACKED_DIR / "scripts"

_GVID_CACHE: Optional[Dict[str, Any]] = None
_VANILLA_ENG_STRINGS_CACHE: Optional[Set[str]] = None


def _resolve_gamedata_dir(gamedata_dir: Union[str, Path]) -> Path:
    """Accepts either a direct `gamedata` path or a parent directory containing `gamedata/`."""
    p = Path(gamedata_dir)
    if p.name != "gamedata" and (p / "gamedata").is_dir():
        return p / "gamedata"
    return p


def _strip_lua_comments(code: str) -> str:
    """Removes Lua block comments `--[[ ... ]]` and single-line comments `--...` while keeping line count."""
    def _repl_block(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")

    s = re.sub(r"--\[(=*)\[[\s\S]*?\]\1\]", _repl_block, code)
    out_lines = []
    for line in s.splitlines():
        # Remove single-line comment outside simple strings
        in_sq = False
        in_dq = False
        esc = False
        cut_idx = None
        i = 0
        while i < len(line):
            ch = line[i]
            if esc:
                esc = False
                i += 1
                continue
            if ch == "\\":
                esc = True
                i += 1
                continue
            if ch == "'" and not in_dq:
                in_sq = not in_sq
            elif ch == '"' and not in_sq:
                in_dq = not in_dq
            elif ch == "-" and not in_sq and not in_dq and i + 1 < len(line) and line[i + 1] == "-":
                cut_idx = i
                break
            i += 1
        out_lines.append(line[:cut_idx] if cut_idx is not None else line)
    return "\n".join(out_lines)


def _strip_lua_comments_and_strings(code: str) -> str:
    """Removes Lua comments and string contents (preserving newlines) for bracket/keyword balance checking."""
    def _repl_newlines(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")

    # Strip block comments first
    s = re.sub(r"--\[(=*)\[[\s\S]*?\]\1\]", _repl_newlines, code)
    # Strip long bracket strings [[ ... ]] or [=[ ... ]=]
    s = re.sub(r"\[(=*)\[[\s\S]*?\]\1\]", _repl_newlines, s)
    out_lines = []
    for line in s.splitlines():
        res = []
        in_sq = False
        in_dq = False
        esc = False
        i = 0
        while i < len(line):
            ch = line[i]
            if esc:
                esc = False
                i += 1
                continue
            if ch == "\\":
                esc = True
                i += 1
                continue
            if not in_sq and not in_dq and ch == "-" and i + 1 < len(line) and line[i + 1] == "-":
                break
            if ch == "'" and not in_dq:
                in_sq = not in_sq
                res.append(" ")
            elif ch == '"' and not in_sq:
                in_dq = not in_dq
                res.append(" ")
            elif in_sq or in_dq:
                res.append(" ")
            else:
                res.append(ch)
            i += 1
        out_lines.append("".join(res))
    return "\n".join(out_lines)


def _load_gvid_index() -> Dict[str, Any]:
    """Loads and caches `game_graph_gvids.json`."""
    global _GVID_CACHE
    if _GVID_CACHE is not None:
        return _GVID_CACHE

    candidates = [
        GVID_INDEX_PATH,
        Path(__file__).resolve().parent.parent / "index" / "game_graph_gvids.json",
        Path("/workspace/game_graph_gvids.json"),
    ]
    raw_data: Dict[str, Any] = {"by_level": {}, "vertices": []}
    for cand in candidates:
        if cand.is_file():
            try:
                raw_data = json.loads(cand.read_text(encoding="utf-8", errors="ignore"))
                break
            except Exception:
                pass

    by_level_ranges: Dict[str, Tuple[int, int]] = {}
    by_level_sets: Dict[str, Set[int]] = {}
    gvid_to_level: Dict[int, str] = {}

    by_level = raw_data.get("by_level", {})
    if isinstance(by_level, dict):
        for lvl, entries in by_level.items():
            gset: Set[int] = set()
            if isinstance(entries, list):
                for item in entries:
                    if isinstance(item, dict) and "gvid" in item:
                        g = int(item["gvid"])
                        gset.add(g)
                        gvid_to_level[g] = lvl
                    elif isinstance(item, int):
                        gset.add(item)
                        gvid_to_level[item] = lvl
            elif isinstance(entries, dict) and "min_gvid" in entries and "max_gvid" in entries:
                mn, mx = int(entries["min_gvid"]), int(entries["max_gvid"])
                gset = set(range(mn, mx + 1))
                for g in gset:
                    gvid_to_level[g] = lvl
            if gset:
                by_level_sets[lvl] = gset
                by_level_ranges[lvl] = (min(gset), max(gset))

    for v in raw_data.get("vertices", []):
        if isinstance(v, dict) and "gvid" in v and "level" in v:
            g = int(v["gvid"])
            lvl = str(v["level"])
            gvid_to_level[g] = lvl
            by_level_sets.setdefault(lvl, set()).add(g)

    for lvl, gset in by_level_sets.items():
        if gset and lvl not in by_level_ranges:
            by_level_ranges[lvl] = (min(gset), max(gset))

    _GVID_CACHE = {
        "by_level_ranges": by_level_ranges,
        "by_level_sets": by_level_sets,
        "gvid_to_level": gvid_to_level,
    }
    return _GVID_CACHE


def _resolve_level_name(level_name: str, by_level_ranges: Dict[str, Tuple[int, int]]) -> str:
    """Resolves either full level name (`l01_escape`) or short name (`escape`)."""
    if level_name in by_level_ranges:
        return level_name
    short = re.sub(r"^[kluy]\d+[u]?_", "", level_name)
    for k in by_level_ranges:
        if k == short or re.sub(r"^[kluy]\d+[u]?_", "", k) == short:
            return k
    return level_name


def _level_short_name(level_name: str) -> str:
    """Converts e.g. `l01_escape` -> `escape`, `k00_marsh` -> `marsh` for `dialogs_<level>.xml`."""
    return re.sub(r"^[kluy]\d+[u]?_", "", level_name)


# ============================================================================
# CHECK 1: GVID Check
# ============================================================================
def gvid_check(gamedata_dir: Union[str, Path], level_name: str = "l01_escape") -> Dict[str, Any]:
    gd_dir = _resolve_gamedata_dir(gamedata_dir)
    idx = _load_gvid_index()
    ranges = idx["by_level_ranges"]
    sets = idx["by_level_sets"]
    gvid_to_level = idx["gvid_to_level"]

    resolved_lvl = _resolve_level_name(level_name, ranges)
    lvl_range = ranges.get(resolved_lvl, (362, 640) if "escape" in level_name else (0, 65535))
    valid_set = sets.get(resolved_lvl, set(range(lvl_range[0], lvl_range[1] + 1)))

    errors: List[str] = []
    warnings: List[str] = []
    checked_gvids: List[Dict[str, Any]] = []

    # 1a. Check gamedata/scripts/*.script
    scripts_dir = gd_dir / "scripts"
    if scripts_dir.is_dir():
        rx_kv_gvid = re.compile(r"\b(?:gvid|game_vertex_id|graph_id)\s*=\s*(\d+)\b", re.I)
        rx_alife_create = re.compile(
            r"(?:alife_create|alife\(\)\s*:\s*create)\s*\(\s*[^,]+,\s*vector\(\)\s*:\s*set\([^)]*\)\s*,\s*\d+\s*,\s*(\d+)\s*\)"
        )
        for sf in sorted(scripts_dir.glob("*.script")):
            raw = sf.read_text(encoding="utf-8", errors="ignore")
            clean = _strip_lua_comments(raw)
            for lineno, line in enumerate(clean.splitlines(), start=1):
                found_in_line: List[int] = []
                for m in rx_kv_gvid.finditer(line):
                    found_in_line.append(int(m.group(1)))
                for m in rx_alife_create.finditer(line):
                    val = int(m.group(1))
                    if val not in found_in_line:
                        found_in_line.append(val)
                for gval in found_in_line:
                    actual_lvl = gvid_to_level.get(gval, "unknown")
                    is_valid = gval in valid_set
                    checked_gvids.append({
                        "file": f"scripts/{sf.name}",
                        "line": lineno,
                        "gvid": gval,
                        "ok": is_valid,
                        "actual_level": actual_lvl,
                    })
                    if not is_valid:
                        errors.append(
                            f"[gvid_check] scripts/{sf.name}:{lineno}: Ungültige GVID {gval} "
                            f"(gehört zu Level '{actual_lvl}'). Erlaubter Bereich für '{resolved_lvl}': "
                            f"{lvl_range[0]}..{lvl_range[1]}."
                        )

    # 1b. Check gamedata/configs/**/*.ltx
    configs_dir = gd_dir / "configs"
    if configs_dir.is_dir():
        rx_ltx_gvid = re.compile(r"^\s*(?:game_vertex_id|gvid|graph_id)\s*=\s*(\d+)\b", re.I)
        for lf in sorted(configs_dir.rglob("*.ltx")):
            raw = lf.read_text(encoding="cp1251", errors="ignore")
            rel_path = lf.relative_to(gd_dir)
            for lineno, line in enumerate(raw.splitlines(), start=1):
                code_part = line.split(";", 1)[0]
                m = rx_ltx_gvid.search(code_part)
                if m:
                    gval = int(m.group(1))
                    actual_lvl = gvid_to_level.get(gval, "unknown")
                    is_valid = gval in valid_set
                    checked_gvids.append({
                        "file": str(rel_path),
                        "line": lineno,
                        "gvid": gval,
                        "ok": is_valid,
                        "actual_level": actual_lvl,
                    })
                    if not is_valid:
                        errors.append(
                            f"[gvid_check] {rel_path}:{lineno}: Ungültige GVID {gval} "
                            f"(gehört zu Level '{actual_lvl}'). Erlaubter Bereich für '{resolved_lvl}': "
                            f"{lvl_range[0]}..{lvl_range[1]}."
                        )

    return {
        "id": "gvid_check",
        "name": "Check 1: Game Graph GVID Range Verification",
        "ok": len(errors) == 0,
        "status": "passed" if not errors else "failed",
        "level": resolved_lvl,
        "valid_gvid_range": [lvl_range[0], lvl_range[1]],
        "checked_count": len(checked_gvids),
        "checked_gvids": checked_gvids,
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================================
# CHECK 2: Dialog XML & #include Resolution Check
# ============================================================================
def _collect_dialogs_from_xml_with_includes(
    xml_path: Path,
    gd_configs: Path,
    visited: Optional[Set[Path]] = None,
) -> Tuple[Set[str], List[str]]:
    if visited is None:
        visited = set()
    resolved = xml_path.resolve()
    if resolved in visited or not xml_path.is_file():
        return set(), []
    visited.add(resolved)

    raw = xml_path.read_text(encoding="cp1251", errors="ignore")
    raw_no_comments = re.sub(r"<!--[\s\S]*?-->", "", raw)

    dialog_ids = set(
        m.strip()
        for m in re.findall(r'<dialog\s+id\s*=\s*["\']([^"\']+)["\']', raw_no_comments)
    )
    missing_includes: List[str] = []

    # Resolve #include "gameplay\..." or #include "gameplay/..."
    for inc in re.findall(r'#include\s+"([^"]+)"', raw_no_comments):
        inc_rel = inc.replace("\\", "/").lstrip("/")
        cand_mod = gd_configs / inc_rel
        cand_unpacked = UNPACKED_CONFIGS_DIR / inc_rel
        if cand_mod.is_file():
            sub_ids, sub_missing = _collect_dialogs_from_xml_with_includes(cand_mod, gd_configs, visited)
            dialog_ids.update(sub_ids)
            missing_includes.extend(sub_missing)
        elif cand_unpacked.is_file():
            sub_ids, sub_missing = _collect_dialogs_from_xml_with_includes(cand_unpacked, gd_configs, visited)
            dialog_ids.update(sub_ids)
            missing_includes.extend(sub_missing)
        else:
            missing_includes.append(f"{xml_path.name} -> #include \"{inc}\" (Datei existiert nicht)")

    return dialog_ids, missing_includes


def dialog_xml_include_check(gamedata_dir: Union[str, Path], level_name: str = "l01_escape") -> Dict[str, Any]:
    gd_dir = _resolve_gamedata_dir(gamedata_dir)
    scripts_dir = gd_dir / "scripts"
    gd_configs = gd_dir / "configs"
    gp_dir = gd_configs / "gameplay"

    errors: List[str] = []
    warnings: List[str] = []
    registered_dialogs: List[Dict[str, Any]] = []

    # 2a. Extract all dialog_list:add("...") in scripts
    if scripts_dir.is_dir():
        rx_add = re.compile(r'dialog_list\s*:\s*add\s*\(\s*["\']([^"\']+)["\']\s*\)')
        for sf in sorted(scripts_dir.glob("*.script")):
            clean = _strip_lua_comments(sf.read_text(encoding="utf-8", errors="ignore"))
            has_hook = "on_specific_character_dialog_list" in clean
            for lineno, line in enumerate(clean.splitlines(), start=1):
                for m in rx_add.finditer(line):
                    registered_dialogs.append({
                        "dialog_id": m.group(1),
                        "script": f"scripts/{sf.name}",
                        "line": lineno,
                        "in_character_dialog_hook": has_hook,
                    })

    short_lvl = _level_short_name(level_name)
    primary_xml_names = [f"dialogs_{short_lvl}.xml"]
    if f"dialogs_{level_name}.xml" not in primary_xml_names:
        primary_xml_names.append(f"dialogs_{level_name}.xml")

    reachable_ids: Set[str] = set()
    all_mod_gp_ids: Dict[str, str] = {}

    if gp_dir.is_dir():
        for xf in sorted(gp_dir.glob("*.xml")):
            raw_nc = re.sub(r"<!--[\s\S]*?-->", "", xf.read_text(encoding="cp1251", errors="ignore"))
            for did in re.findall(r'<dialog\s+id\s*=\s*["\']([^"\']+)["\']', raw_nc):
                all_mod_gp_ids[did.strip()] = xf.name

        # Collect only from official engine entrypoints: dialogs_<short_lvl>.xml, dialogs_<level_name>.xml, dialogs.xml
        found_primary = False
        for px_name in primary_xml_names + ["dialogs.xml"]:
            px_mod = gp_dir / px_name
            if px_mod.is_file():
                if px_name in primary_xml_names:
                    found_primary = True
                ids, miss_inc = _collect_dialogs_from_xml_with_includes(px_mod, gd_configs)
                reachable_ids.update(ids)
                for mi in miss_inc:
                    errors.append(f"[dialog_xml_include_check] Fehlende #include-Datei in {mi}")

        if not found_primary and registered_dialogs:
            errors.append(
                f"[dialog_xml_include_check] '{primary_xml_names[0]}' fehlt in 'gamedata/configs/gameplay/' "
                f"(CXML_IdToIndex<CPhraseDialog>::GetById benötigt dialogs_{short_lvl}.xml inkl. #include)."
            )

    # Also collect vanilla unpacked dialog IDs for dialogs_<short_lvl>.xml
    vanilla_ids: Set[str] = set()
    if UNPACKED_CONFIGS_DIR.is_dir():
        unp_gp = UNPACKED_CONFIGS_DIR / "gameplay"
        if unp_gp.is_dir():
            for xf in sorted(unp_gp.glob("dialogs*.xml")):
                raw_nc = re.sub(r"<!--[\s\S]*?-->", "", xf.read_text(encoding="cp1251", errors="ignore"))
                for did in re.findall(r'<dialog\s+id\s*=\s*["\']([^"\']+)["\']', raw_nc):
                    vanilla_ids.add(did.strip())

    for reg in registered_dialogs:
        did = reg["dialog_id"]
        if did in reachable_ids or did in vanilla_ids:
            reg["ok"] = True
        elif did in all_mod_gp_ids:
            reg["ok"] = False
            errors.append(
                f"[dialog_xml_include_check] Dialog '{did}' (aus {reg['script']}:{reg['line']}) "
                f"ist zwar in '{all_mod_gp_ids[did]}' definiert, wird aber NICHT über "
                f"'gamedata/configs/gameplay/{primary_xml_names[0]}' (oder #include) eingebunden -> "
                f"Crash in CXML_IdToIndex<CPhraseDialog>::GetById!"
            )
        else:
            reg["ok"] = False
            errors.append(
                f"[dialog_xml_include_check] Dialog '{did}' (registriert in {reg['script']}:{reg['line']}) "
                f"wurde in keiner gamedata/configs/gameplay/dialogs_{short_lvl}.xml gefunden -> "
                f"Crash in CXML_IdToIndex<CPhraseDialog>::GetById!"
            )

    return {
        "id": "dialog_xml_include_check",
        "name": "Check 2: Dialog XML & #include Reachability (CXML_IdToIndex<CPhraseDialog>::GetById)",
        "ok": len(errors) == 0,
        "status": "passed" if not errors else "failed",
        "expected_dialog_xml": f"gamedata/configs/gameplay/{primary_xml_names[0]}",
        "registered_dialogs": registered_dialogs,
        "reachable_dialog_ids": sorted(reachable_ids),
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================================
# CHECK 3: Lua Callback Check (<action> & <precondition> in Dialog XMLs)
# ============================================================================
def _script_has_function(script_path: Path, func_name: str, module_name: str) -> bool:
    if not script_path.is_file():
        return False
    clean = _strip_lua_comments(script_path.read_text(encoding="utf-8", errors="ignore"))
    patterns = [
        rf"\bfunction\s+{re.escape(func_name)}\s*\(",
        rf"\bfunction\s+{re.escape(module_name)}\s*\.\s*{re.escape(func_name)}\s*\(",
        rf"\b{re.escape(func_name)}\s*=\s*function\s*\(",
    ]
    return any(re.search(p, clean) for p in patterns)


def lua_callback_check(gamedata_dir: Union[str, Path], level_name: str = "l01_escape") -> Dict[str, Any]:
    gd_dir = _resolve_gamedata_dir(gamedata_dir)
    gp_dir = gd_dir / "configs" / "gameplay"
    scripts_dir = gd_dir / "scripts"

    errors: List[str] = []
    warnings: List[str] = []
    checked_callbacks: List[Dict[str, Any]] = []

    if gp_dir.is_dir():
        rx_tag = re.compile(r"<(action|precondition)>\s*([^<]+?)\s*</\1>", re.I)
        for xf in sorted(gp_dir.rglob("*.xml")):
            raw_nc = re.sub(r"<!--[\s\S]*?-->", "", xf.read_text(encoding="cp1251", errors="ignore"))
            rel_xml = xf.relative_to(gd_dir)
            for m in rx_tag.finditer(raw_nc):
                tag_type = m.group(1).lower()
                raw_refs = [r.strip() for r in m.group(2).split(";") if r.strip()]
                for ref in raw_refs:
                    if "." not in ref:
                        continue
                    mod_name, func_name = ref.split(".", 1)
                    mod_name = mod_name.strip()
                    func_name = func_name.strip()
                    if not mod_name or not func_name:
                        continue

                    mod_script = scripts_dir / f"{mod_name}.script"
                    unp_script = UNPACKED_SCRIPTS_DIR / f"{mod_name}.script"

                    found_in_mod = _script_has_function(mod_script, func_name, mod_name)
                    found_in_vanilla = False if found_in_mod else _script_has_function(unp_script, func_name, mod_name)
                    ok = found_in_mod or found_in_vanilla

                    checked_callbacks.append({
                        "xml": str(rel_xml),
                        "tag": tag_type,
                        "reference": f"{mod_name}.{func_name}",
                        "found_in_mod": found_in_mod,
                        "found_in_vanilla": found_in_vanilla,
                        "ok": ok,
                    })

                    if not ok:
                        if not mod_script.is_file() and not unp_script.is_file():
                            errors.append(
                                f"[lua_callback_check] {rel_xml}: <{tag_type}>{mod_name}.{func_name}</{tag_type}> "
                                f"verweist auf fehlendes Skript 'gamedata/scripts/{mod_name}.script'."
                            )
                        else:
                            errors.append(
                                f"[lua_callback_check] {rel_xml}: <{tag_type}>{mod_name}.{func_name}</{tag_type}> "
                                f"verweist auf fehlende Funktion 'function {func_name}(' in '{mod_name}.script'."
                            )

    return {
        "id": "lua_callback_check",
        "name": "Check 3: Dialog XML <action> & <precondition> Lua Callback Verification",
        "ok": len(errors) == 0,
        "status": "passed" if not errors else "failed",
        "checked_count": len(checked_callbacks),
        "checked_callbacks": checked_callbacks,
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================================
# CHECK 4: String Table Check (<text> in XMLs + title/descr/inv_name/description in LTX)
# ============================================================================
def _load_vanilla_eng_string_ids() -> Set[str]:
    global _VANILLA_ENG_STRINGS_CACHE
    if _VANILLA_ENG_STRINGS_CACHE is not None:
        return _VANILLA_ENG_STRINGS_CACHE
    ids: Set[str] = set()
    eng_dir = UNPACKED_CONFIGS_DIR / "text" / "eng"
    if eng_dir.is_dir():
        rx = re.compile(r'<string\s+id\s*=\s*["\']([^"\']+)["\']')
        for xf in eng_dir.glob("*.xml"):
            try:
                raw = xf.read_text(encoding="cp1251", errors="ignore")
                ids.update(m.strip() for m in rx.findall(raw))
            except Exception:
                pass
    _VANILLA_ENG_STRINGS_CACHE = ids
    return ids


def _extract_ltx_string_ids(raw_val: str) -> List[str]:
    """Extracts candidate string-table IDs from an LTX value (stripping `{...}` condlists)."""
    val = re.sub(r"\{[^}]*\}", " ", raw_val)
    val = re.sub(r"%[^%]*%", " ", val)
    tokens: List[str] = []
    for part in val.split(","):
        tok = part.strip().strip('"').strip("'")
        if not tok:
            continue
        if tok.lower() in {"nil", "none", "true", "false"}:
            continue
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", tok):
            continue
        # Only treat single-token identifiers (no spaces) as string table IDs
        if re.fullmatch(r"[A-Za-z0-9_.\-]+", tok):
            tokens.append(tok)
    return tokens


def string_table_check(gamedata_dir: Union[str, Path], level_name: str = "l01_escape") -> Dict[str, Any]:
    gd_dir = _resolve_gamedata_dir(gamedata_dir)
    configs_dir = gd_dir / "configs"
    eng_dir = configs_dir / "text" / "eng"
    gp_dir = configs_dir / "gameplay"

    errors: List[str] = []
    warnings: List[str] = []

    mod_string_ids: Set[str] = set()
    rx_str_id = re.compile(r'<string\s+id\s*=\s*["\']([^"\']+)["\']')
    if eng_dir.is_dir():
        for xf in sorted(eng_dir.glob("*.xml")):
            raw_nc = re.sub(r"<!--[\s\S]*?-->", "", xf.read_text(encoding="cp1251", errors="ignore"))
            mod_string_ids.update(m.strip() for m in rx_str_id.findall(raw_nc))

    vanilla_string_ids = _load_vanilla_eng_string_ids()

    referenced_ids: List[Dict[str, Any]] = []

    # 4a. Collect <text>...</text> in Dialog XMLs (gamedata/configs/gameplay/**/*.xml)
    if gp_dir.is_dir():
        rx_text = re.compile(r"<text>\s*([^<]+?)\s*</text>", re.I)
        for xf in sorted(gp_dir.rglob("*.xml")):
            raw_nc = re.sub(r"<!--[\s\S]*?-->", "", xf.read_text(encoding="cp1251", errors="ignore"))
            rel_xml = xf.relative_to(gd_dir)
            for m in rx_text.finditer(raw_nc):
                tid = m.group(1).strip()
                if not tid:
                    continue
                in_mod = tid in mod_string_ids
                in_vanilla = tid in vanilla_string_ids
                ok = in_mod or in_vanilla
                referenced_ids.append({
                    "source": str(rel_xml),
                    "kind": "dialog_text",
                    "string_id": tid,
                    "in_mod_eng": in_mod,
                    "in_vanilla_eng": in_vanilla,
                    "ok": ok,
                })
                if not ok:
                    errors.append(
                        f"[string_table_check] {rel_xml}: <text>{tid}</text> fehlt in "
                        f"'gamedata/configs/text/eng/*.xml'."
                    )

    # 4b. Collect title, descr, inv_name, inv_name_short, description in gamedata/configs/**/*.ltx
    if configs_dir.is_dir():
        rx_ltx_key = re.compile(r"^\s*(title|descr|inv_name|inv_name_short|description)\s*=\s*(.+)$", re.I)
        for lf in sorted(configs_dir.rglob("*.ltx")):
            raw = lf.read_text(encoding="cp1251", errors="ignore")
            rel_ltx = lf.relative_to(gd_dir)
            for lineno, line in enumerate(raw.splitlines(), start=1):
                code_part = line.split(";", 1)[0].strip()
                m = rx_ltx_key.match(code_part)
                if not m:
                    continue
                key_name = m.group(1).lower()
                for sid in _extract_ltx_string_ids(m.group(2)):
                    in_mod = sid in mod_string_ids
                    in_vanilla = sid in vanilla_string_ids
                    ok = in_mod or in_vanilla
                    referenced_ids.append({
                        "source": f"{rel_ltx}:{lineno}",
                        "kind": f"ltx_{key_name}",
                        "string_id": sid,
                        "in_mod_eng": in_mod,
                        "in_vanilla_eng": in_vanilla,
                        "ok": ok,
                    })
                    if not ok:
                        errors.append(
                            f"[string_table_check] {rel_ltx}:{lineno} ({key_name} = {sid}): "
                            f"String-ID '{sid}' fehlt in 'gamedata/configs/text/eng/*.xml'."
                        )

    return {
        "id": "string_table_check",
        "name": "Check 4: String Table ID Verification (Dialog XMLs & LTX -> text/eng/*.xml)",
        "ok": len(errors) == 0,
        "status": "passed" if not errors else "failed",
        "mod_eng_string_count": len(mod_string_ids),
        "referenced_count": len(referenced_ids),
        "referenced_ids": referenced_ids,
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================================
# CHECK 5: OGF Visual Check & Auto-Copy to gamedata/meshes/
# ============================================================================
def ogf_visual_check(gamedata_dir: Union[str, Path], level_name: str = "l01_escape") -> Dict[str, Any]:
    gd_dir = _resolve_gamedata_dir(gamedata_dir)
    configs_dir = gd_dir / "configs"
    mod_meshes_dir = gd_dir / "meshes"

    errors: List[str] = []
    warnings: List[str] = []
    checked_visuals: List[Dict[str, Any]] = []
    auto_copied: List[str] = []

    if configs_dir.is_dir():
        rx_vis = re.compile(r"^\s*visual\s*=\s*([^\s;]+)", re.I)
        for lf in sorted(configs_dir.rglob("*.ltx")):
            raw = lf.read_text(encoding="cp1251", errors="ignore")
            rel_ltx = lf.relative_to(gd_dir)
            for lineno, line in enumerate(raw.splitlines(), start=1):
                code_part = line.split(";", 1)[0].strip()
                m = rx_vis.match(code_part)
                if not m:
                    continue
                vis_raw = m.group(1).strip().strip('"').strip("'")
                vis_norm = vis_raw.replace("\\", "/").lstrip("/")
                if not vis_norm.lower().endswith(".ogf"):
                    vis_norm += ".ogf"

                unp_path = UNPACKED_MESHES_DIR / vis_norm
                mod_path = mod_meshes_dir / vis_norm

                exists_unpacked = unp_path.is_file()
                exists_mod = mod_path.is_file()
                copied_now = False

                if exists_unpacked and not exists_mod:
                    try:
                        mod_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(unp_path, mod_path)
                        exists_mod = True
                        copied_now = True
                        auto_copied.append(vis_norm)
                    except Exception as exc:
                        warnings.append(
                            f"[ogf_visual_check] Konnte '{vis_norm}' nicht automatisch nach "
                            f"gamedata/meshes/ kopieren: {exc}"
                        )

                ok = exists_unpacked or exists_mod
                checked_visuals.append({
                    "source": f"{rel_ltx}:{lineno}",
                    "visual": vis_norm,
                    "exists_in_unpacked": exists_unpacked,
                    "exists_in_gamedata": exists_mod,
                    "auto_copied": copied_now,
                    "ok": ok,
                })

                if not ok:
                    errors.append(
                        f"[ogf_visual_check] {rel_ltx}:{lineno}: OGF-Mesh '{vis_norm}' existiert weder in "
                        f"'{UNPACKED_MESHES_DIR}' noch in 'gamedata/meshes/' -> Engine-Crash beim Spawnen!"
                    )

    return {
        "id": "ogf_visual_check",
        "name": "Check 5: OGF Visual Mesh Verification & Auto-Bundle into gamedata/meshes/",
        "ok": len(errors) == 0,
        "status": "passed" if not errors else "failed",
        "checked_count": len(checked_visuals),
        "auto_copied_meshes": auto_copied,
        "checked_visuals": checked_visuals,
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================================
# CHECK 6: Quest Item Pickup Callback & story_objects.register Check
# ============================================================================
def pickup_callback_check(gamedata_dir: Union[str, Path], level_name: str = "l01_escape") -> Dict[str, Any]:
    gd_dir = _resolve_gamedata_dir(gamedata_dir)
    scripts_dir = gd_dir / "scripts"

    errors: List[str] = []
    warnings: List[str] = []
    script_reports: List[Dict[str, Any]] = []

    has_any_item_take = False
    has_any_story_reg = False
    script_files = sorted(scripts_dir.glob("*.script")) if scripts_dir.is_dir() else []

    for sf in script_files:
        clean = _strip_lua_comments(sf.read_text(encoding="utf-8", errors="ignore"))
        has_take = "actor_on_item_take" in clean
        has_story_reg = bool(re.search(r"story_objects\s*\.\s*register", clean))
        spawns_entities = bool(re.search(r"\b(?:alife_create|alife\(\)\s*:\s*create)\s*\(", clean))

        if has_take:
            has_any_item_take = True
        if has_story_reg:
            has_any_story_reg = True

        script_reports.append({
            "script": f"scripts/{sf.name}",
            "has_actor_on_item_take": has_take,
            "has_story_objects_register": has_story_reg,
            "spawns_entities": spawns_entities,
        })

    if script_files:
        if not has_any_item_take:
            errors.append(
                "[pickup_callback_check] Kein Skript in 'gamedata/scripts/*.script' registriert "
                "'actor_on_item_take' (benötigt, damit Quest-Item-Pickups sofort unabhängig vom Level weiterschalten)."
            )
        if not has_any_story_reg:
            errors.append(
                "[pickup_callback_check] Kein Skript in 'gamedata/scripts/*.script' nutzt "
                "'story_objects.register' (benötigt für zuverlässige Story-ID-Registrierung von gespawnten Quest-Objekten)."
            )

    return {
        "id": "pickup_callback_check",
        "name": "Check 6: Quest Item Pickup Callback (actor_on_item_take & story_objects.register)",
        "ok": len(errors) == 0,
        "status": "passed" if not errors else "failed",
        "has_actor_on_item_take": has_any_item_take,
        "has_story_objects_register": has_any_story_reg,
        "scripts": script_reports,
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================================
# CHECK 7: ALAO Lua Static Check (db.actor caching, table.insert, syntax/balance)
# ============================================================================
def alao_lua_check(gamedata_dir: Union[str, Path], level_name: str = "l01_escape") -> Dict[str, Any]:
    gd_dir = _resolve_gamedata_dir(gamedata_dir)
    scripts_dir = gd_dir / "scripts"

    errors: List[str] = []
    warnings: List[str] = []
    file_results: List[Dict[str, Any]] = []

    if scripts_dir.is_dir():
        for sf in sorted(scripts_dir.glob("*.script")):
            raw = sf.read_text(encoding="utf-8", errors="ignore")
            clean_code = _strip_lua_comments(raw)
            structural = _strip_lua_comments_and_strings(raw)

            file_errs: List[str] = []
            file_warns: List[str] = []

            # 7a. Bracket / Parenthesis / Brace balance
            pairs = {")": "(", "}": "{", "]": "["}
            openers = set(pairs.values())
            stack: List[Tuple[str, int]] = []
            for lineno, line in enumerate(structural.splitlines(), start=1):
                for ch in line:
                    if ch in openers:
                        stack.append((ch, lineno))
                    elif ch in pairs:
                        if not stack or stack[-1][0] != pairs[ch]:
                            file_errs.append(
                                f"[alao_lua_check] scripts/{sf.name}:{lineno}: Unbalancierte Klammer '{ch}'."
                            )
                        else:
                            stack.pop()
            for op_ch, op_line in stack:
                file_errs.append(
                    f"[alao_lua_check] scripts/{sf.name}:{op_line}: Nicht geschlossene Klammer '{op_ch}'."
                )

            # 7b. Lua block keyword balance (function / if / do / repeat vs end / until)
            # In Lua: `function`, `if ... then`, `do` (standalone or in while/for ... do) each close with `end`;
            # `repeat` closes with `until`.
            tokens = re.findall(r"\b(?:function|if|do|repeat|end|until)\b", structural)
            open_blocks = 0
            repeat_blocks = 0
            for tok in tokens:
                if tok in {"function", "if", "do"}:
                    open_blocks += 1
                elif tok == "end":
                    open_blocks -= 1
                elif tok == "repeat":
                    repeat_blocks += 1
                elif tok == "until":
                    repeat_blocks -= 1

            if open_blocks != 0:
                file_errs.append(
                    f"[alao_lua_check] scripts/{sf.name}: Lua-Block-Imbalance (function/if/do vs. end Differenz = {open_blocks:+d})."
                )
            if repeat_blocks != 0:
                file_errs.append(
                    f"[alao_lua_check] scripts/{sf.name}: Lua repeat/until-Imbalance (Differenz = {repeat_blocks:+d})."
                )

            # 7c. db.actor caching check
            db_actor_hits = len(re.findall(r"\bdb\.actor\b", clean_code))
            has_local_actor_cache = bool(
                re.search(r"\blocal\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*db\.actor\b", clean_code)
            )
            if db_actor_hits > 2 and not has_local_actor_cache:
                file_warns.append(
                    f"[alao_lua_check] scripts/{sf.name}: 'db.actor' wird {db_actor_hits}x ohne lokales Caching "
                    f"('local actor = db.actor') aufgerufen (ALAO Performance-Hinweis)."
                )

            # 7d. table.insert check
            table_insert_hits = len(re.findall(r"\btable\.insert\s*\(", clean_code))
            if table_insert_hits > 0:
                file_warns.append(
                    f"[alao_lua_check] scripts/{sf.name}: 'table.insert' wird {table_insert_hits}x verwendet "
                    f"(ALAO-Empfehlung: 't[#t + 1] = v' für schnelleren LuaJIT-Zugriff)."
                )

            errors.extend(file_errs)
            warnings.extend(file_warns)
            file_results.append({
                "script": f"scripts/{sf.name}",
                "ok": len(file_errs) == 0,
                "db_actor_count": db_actor_hits,
                "has_local_actor_cache": has_local_actor_cache,
                "table_insert_count": table_insert_hits,
                "errors": file_errs,
                "warnings": file_warns,
            })

    return {
        "id": "alao_lua_check",
        "name": "Check 7: ALAO Static Lua Check (Syntax Balance, db.actor Caching, table.insert)",
        "ok": len(errors) == 0,
        "status": "passed" if not errors else "failed",
        "files": file_results,
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================================
# MAIN ENTRY POINT: 7-Stage X-Ray Mod Typechecker
# ============================================================================
def run_xray_mod_typechecker(
    gamedata_dir: Union[str, Path],
    level_name: str = "l01_escape",
) -> Dict[str, Any]:
    """
    Runs all 7 X-Ray Anomaly 1.5.3 pre-export validation checks on `gamedata_dir`
    and returns `{"ok": bool, "checks": [...], "errors": [...], "warnings": [...]}`.
    """
    gd_dir = _resolve_gamedata_dir(gamedata_dir)

    checks = [
        gvid_check(gd_dir, level_name=level_name),
        dialog_xml_include_check(gd_dir, level_name=level_name),
        lua_callback_check(gd_dir, level_name=level_name),
        string_table_check(gd_dir, level_name=level_name),
        ogf_visual_check(gd_dir, level_name=level_name),
        pickup_callback_check(gd_dir, level_name=level_name),
        alao_lua_check(gd_dir, level_name=level_name),
    ]

    all_errors: List[str] = []
    all_warnings: List[str] = []
    for chk in checks:
        all_errors.extend(chk.get("errors", []))
        all_warnings.extend(chk.get("warnings", []))

    return {
        "ok": len(all_errors) == 0,
        "level_name": level_name,
        "gamedata_dir": str(gd_dir),
        "checks": checks,
        "errors": all_errors,
        "warnings": all_warnings,
        "summary": {
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks if c.get("ok")),
            "failed_checks": sum(1 for c in checks if not c.get("ok")),
            "error_count": len(all_errors),
            "warning_count": len(all_warnings),
        },
    }


if __name__ == "__main__":
    import sys

    target_dir = sys.argv[1] if len(sys.argv) > 1 else str(ROOT_DIR / "gamedata")
    target_lvl = sys.argv[2] if len(sys.argv) > 2 else "l01_escape"
    res = run_xray_mod_typechecker(target_dir, target_lvl)
    print(json.dumps(res, indent=2, ensure_ascii=False))
