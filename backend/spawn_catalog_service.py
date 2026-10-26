#!/usr/bin/env python3
"""
Anomaly 1.5.3 Studio — Verified Spawn Catalog Service
=====================================================
Scans unpacked S.T.A.L.K.E.R. Anomaly 1.5.3 configs (`tools/_unpacked/configs/`)
and meshes (`tools/_unpacked/meshes/`) with full LTX `[section]:parent` inheritance
and XML character profile resolution (`npc_profile.xml` + `character_desc_*.xml`)
to produce a 100% mesh-verified catalog of spawnable sections:
  1. `stalker_sections`     — Verified NPC sections per faction (sim_default_<faction>_0..4, etc.)
  2. `mutant_sections`      — Verified mutant sections (bloodsucker_normal, boar_normal, dog_normal,
                              pseudodog_normal, snork_normal, chimera_normal, controller_normal,
                              burer_normal, plus all other verified standard mutant sections)
  3. `quest_and_loot_items` — Verified quest items, medkits, weapons, containers (inventory_box,
                              inv_backpack, etc.), ammo, artefacts, devices, outfits, consumables, tools

Every entry in `verified_spawn_catalog.json` is guaranteed to reference an existing `.ogf` file
under `tools/_unpacked/meshes/` so `CModelPool::Instance_Load`
never crashes in Base Anomaly 1.5.3 or the 3D World & Quest Director.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
UNPACKED_DIR = ROOT / ".studio_cache" / "vfs_mount"
CONFIGS_DIR = UNPACKED_DIR / "configs"
MESHES_DIR = UNPACKED_DIR / "meshes"
STUDIO_INDEX_DIR = ROOT / "index"
CATALOG_JSON_PATH = STUDIO_INDEX_DIR / "verified_spawn_catalog.json"

_CATALOG_CACHE: Optional[Dict[str, Any]] = None

REQUIRED_STALKER_SECTIONS: List[Tuple[str, str, str, int]] = [
    # (section_name, canonical_ltx_section, faction_key, tier)
    ("sim_default_stalker_0", "sim_default_stalker_0", "stalker", 0),
    ("sim_default_stalker_1", "sim_default_stalker_1", "stalker", 1),
    ("sim_default_stalker_2", "sim_default_stalker_2", "stalker", 2),
    ("sim_default_stalker_3", "sim_default_stalker_3", "stalker", 3),
    ("sim_default_stalker_4", "sim_default_stalker_4", "stalker", 4),
    ("sim_default_killer_0", "sim_default_killer_0", "killer", 0),
    ("sim_default_killer_1", "sim_default_killer_1", "killer", 1),
    ("sim_default_killer_2", "sim_default_killer_2", "killer", 2),
    ("sim_default_killer_3", "sim_default_killer_3", "killer", 3),
    ("sim_default_killer_4", "sim_default_killer_4", "killer", 4),
    ("sim_default_bandit_0", "sim_default_bandit_0", "bandit", 0),
    ("sim_default_bandit_1", "sim_default_bandit_1", "bandit", 1),
    ("sim_default_bandit_2", "sim_default_bandit_2", "bandit", 2),
    ("sim_default_bandit_3", "sim_default_bandit_3", "bandit", 3),
    ("sim_default_bandit_4", "sim_default_bandit_4", "bandit", 4),
    ("sim_default_military_0", "sim_default_military_0", "military", 0),
    ("sim_default_military_1", "sim_default_military_1", "military", 1),
    ("sim_default_military_2", "sim_default_military_2", "military", 2),
    ("sim_default_military_3", "sim_default_military_3", "military", 3),
    ("sim_default_military_4", "sim_default_military_4", "military", 4),
    ("sim_default_dolg_0", "sim_default_duty_0", "dolg", 0),
    ("sim_default_dolg_1", "sim_default_duty_1", "dolg", 1),
    ("sim_default_dolg_2", "sim_default_duty_2", "dolg", 2),
    ("sim_default_dolg_3", "sim_default_duty_3", "dolg", 3),
    ("sim_default_dolg_4", "sim_default_duty_4", "dolg", 4),
    ("sim_default_freedom_0", "sim_default_freedom_0", "freedom", 0),
    ("sim_default_freedom_1", "sim_default_freedom_1", "freedom", 1),
    ("sim_default_freedom_2", "sim_default_freedom_2", "freedom", 2),
    ("sim_default_freedom_3", "sim_default_freedom_3", "freedom", 3),
    ("sim_default_freedom_4", "sim_default_freedom_4", "freedom", 4),
    ("sim_default_monolith_0", "sim_default_monolith_0", "monolith", 0),
    ("sim_default_monolith_1", "sim_default_monolith_1", "monolith", 1),
    ("sim_default_monolith_2", "sim_default_monolith_2", "monolith", 2),
    ("sim_default_monolith_3", "sim_default_monolith_3", "monolith", 3),
    ("sim_default_monolith_4", "sim_default_monolith_4", "monolith", 4),
    ("sim_default_ecolog_0", "sim_default_ecolog_0", "ecolog", 0),
    ("sim_default_ecolog_1", "sim_default_ecolog_1", "ecolog", 1),
    ("sim_default_ecolog_2", "sim_default_ecolog_2", "ecolog", 2),
]

FACTION_LABELS: Dict[str, Dict[str, str]] = {
    "stalker": {"de": "Freie Stalker (Loner)", "en": "Free Stalker (Loner)", "ru": "Вольный сталкер (Одиночка)"},
    "killer": {"de": "Söldner (Mercenary)", "en": "Mercenary (Killer)", "ru": "Наёмник (Синдикат)"},
    "bandit": {"de": "Bandit", "en": "Bandit", "ru": "Бандит"},
    "military": {"de": "Militär (Armee)", "en": "Military (Army)", "ru": "Военный (ВСУ)"},
    "army": {"de": "Militär (Armee)", "en": "Military (Army)", "ru": "Военный (ВСУ)"},
    "dolg": {"de": "Wächter (Duty / Dolg)", "en": "Duty (Dolg)", "ru": "Долг"},
    "duty": {"de": "Wächter (Duty / Dolg)", "en": "Duty (Dolg)", "ru": "Долг"},
    "freedom": {"de": "Freiheit (Freedom)", "en": "Freedom", "ru": "Свобода"},
    "monolith": {"de": "Monolith", "en": "Monolith", "ru": "Монолит"},
    "ecolog": {"de": "Ökologen (Wissenschaftler)", "en": "Ecologist (Scientist)", "ru": "Эколог (Учёный)"},
    "csky": {"de": "Clear Sky (Klarer Himmel)", "en": "Clear Sky", "ru": "Чистое Небо"},
    "renegade": {"de": "Renegaten", "en": "Renegade", "ru": "Ренегат"},
    "greh": {"de": "Sünde (Sin / Greh)", "en": "Sin (Greh)", "ru": "Грех"},
    "isg": {"de": "UNISG (Spezialeinheit)", "en": "UNISG (Special Forces)", "ru": "ИИГ (UNISG)"},
    "zombied": {"de": "Zombifizierter Stalker", "en": "Zombified Stalker", "ru": "Зомбированный сталкер"},
}

TIER_LABELS: Dict[int, Dict[str, str]] = {
    0: {"de": "Rang 0 (Rookie / Neuling)", "en": "Tier 0 (Novice / Rookie)", "ru": "Ранг 0 (Новичок)"},
    1: {"de": "Rang 1 (Erfahren)", "en": "Tier 1 (Experienced)", "ru": "Ранг 1 (Опытный)"},
    2: {"de": "Rang 2 (Veteran)", "en": "Tier 2 (Veteran)", "ru": "Ранг 2 (Ветеран)"},
    3: {"de": "Rang 3 (Experte / Meister)", "en": "Tier 3 (Master)", "ru": "Ранг 3 (Мастер)"},
    4: {"de": "Rang 4 (Legende / Elite)", "en": "Tier 4 (Legend / Elite)", "ru": "Ранг 4 (Легенда / Элита)"},
    5: {"de": "Rang 5 (Spezialist)", "en": "Tier 5 (Specialist)", "ru": "Ранг 5 (Специалист)"},
}

REQUIRED_MUTANT_SECTIONS: List[Tuple[str, str, Dict[str, str]]] = [
    (
        "bloodsucker_normal",
        "bloodsucker_normal",
        {
            "species": "bloodsucker",
            "de": "Blutsauger (Normal)",
            "en": "Bloodsucker (Normal)",
            "ru": "Кровосос (Обычный)",
        },
    ),
    (
        "boar_normal",
        "boar_normal",
        {
            "species": "boar",
            "de": "Wildschwein / Keiler (Normal)",
            "en": "Boar (Normal)",
            "ru": "Кабан (Обычный)",
        },
    ),
    (
        "dog_normal",
        "dog_normal",
        {
            "species": "dog",
            "de": "Blinder Hund (Normal)",
            "en": "Blind Dog (Normal)",
            "ru": "Слепой пёс (Обычный)",
        },
    ),
    (
        "pseudodog_normal",
        "pseudodog_normal",
        {
            "species": "pseudodog",
            "de": "Pseudohund (Normal)",
            "en": "Pseudodog (Normal)",
            "ru": "Псевдособака (Обычная)",
        },
    ),
    (
        "snork_normal",
        "snork_normal",
        {
            "species": "snork",
            "de": "Snork (Normal)",
            "en": "Snork (Normal)",
            "ru": "Снорк (Обычный)",
        },
    ),
    (
        "chimera_normal",
        "chimera_normal",
        {
            "species": "chimera",
            "de": "Chimäre (Normal)",
            "en": "Chimera (Normal)",
            "ru": "Химера (Обычная)",
        },
    ),
    (
        "controller_normal",
        "m_controller_normal",
        {
            "species": "controller",
            "de": "Controller (Normal)",
            "en": "Controller (Normal)",
            "ru": "Контролёр (Обычный)",
        },
    ),
    (
        "burer_normal",
        "burer_normal",
        {
            "species": "burer",
            "de": "Burer (Normal)",
            "en": "Burer (Normal)",
            "ru": "Бюрер (Обычный)",
        },
    ),
]

MUTANT_SPECIES_LABELS: Dict[str, Dict[str, str]] = {
    "bloodsucker": {"de": "Blutsauger", "en": "Bloodsucker", "ru": "Кровосос"},
    "boar": {"de": "Wildschwein / Keiler", "en": "Boar", "ru": "Кабан"},
    "dog": {"de": "Blinder Hund", "en": "Blind Dog", "ru": "Слепой пёс"},
    "pseudodog": {"de": "Pseudohund", "en": "Pseudodog", "ru": "Псевдособака"},
    "psy_dog": {"de": "Psi-Hund", "en": "Psy-Dog", "ru": "Пси-собака"},
    "snork": {"de": "Snork", "en": "Snork", "ru": "Снорк"},
    "chimera": {"de": "Chimäre", "en": "Chimera", "ru": "Химера"},
    "controller": {"de": "Controller", "en": "Controller", "ru": "Контролёр"},
    "burer": {"de": "Burer", "en": "Burer", "ru": "Бюрер"},
    "flesh": {"de": "Fleisch (Flesh)", "en": "Flesh", "ru": "Плоть"},
    "gigant": {"de": "Pseudoriese", "en": "Pseudogiant", "ru": "Псевдогигант"},
    "giant": {"de": "Pseudoriese", "en": "Pseudogiant", "ru": "Псевдогигант"},
    "tushkano": {"de": "Tushkano (Nager)", "en": "Tushkano (Rodent)", "ru": "Тушкан"},
    "zombie": {"de": "Zombie", "en": "Zombie", "ru": "Зомби"},
    "fracture": {"de": "Izlom (Fracture)", "en": "Fracture (Izlom)", "ru": "Излом"},
    "cat": {"de": "Bayun-Katze", "en": "Cat (Bayun)", "ru": "Кот-баюн"},
    "psysucker": {"de": "Psi-Blutsauger (Psysucker)", "en": "Psysucker", "ru": "Пси-кровосос"},
    "lurker": {"de": "Lurker", "en": "Lurker", "ru": "Люркер"},
    "poltergeist": {"de": "Poltergeist", "en": "Poltergeist", "ru": "Полтергейст"},
    "rat": {"de": "Ratte", "en": "Rat", "ru": "Крыса"},
    "karlik": {"de": "Karlik (Zwerg)", "en": "Karlik (Dwarf)", "ru": "Карлик"},
    "bibliotekar": {"de": "Bibliothekar", "en": "Librarian (Bibliotekar)", "ru": "Библиотекарь"},
    "borya": {"de": "Borya", "en": "Borya", "ru": "Боря"},
}

SUBCATEGORY_DE_LABELS: Dict[str, str] = {
    "quest_item": "Quest-Gegenstand",
    "medkit": "Medizin / Medkit",
    "weapon": "Waffe",
    "container": "Container / Stash-Box",
    "ammo": "Munition",
    "artefact": "Artefakt",
    "device": "Gerät / Detektor / PDA",
    "outfit": "Anzug / Helm / Rucksack",
    "consumable": "Nahrung / Getränk / Medikament",
    "tool": "Werkzeug / Reparaturset",
    "explosive": "Sprengstoff / Mine",
}


def normalize_mesh_rel_path(raw_visual: str) -> str:
    """Normalizes an LTX/XML visual string into a POSIX path relative to `meshes/` with `.ogf` suffix."""
    cleaned = (raw_visual or "").strip().strip('"').strip("'").replace("\\", "/").lstrip("/")
    if not cleaned:
        return ""
    if not cleaned.lower().endswith(".ogf"):
        cleaned = f"{cleaned}.ogf"
    return cleaned


def verify_mesh_exists(raw_visual: str, meshes_dir: Path = MESHES_DIR) -> Tuple[str, bool]:
    """Returns `(normalized_posix_ogf_path, exists_on_disk)`."""
    norm = normalize_mesh_rel_path(raw_visual)
    if not norm:
        return "", False
    full_path = meshes_dir / norm
    return norm, full_path.is_file()


def _load_string_tables(configs_dir: Path = CONFIGS_DIR) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Loads English and Russian string tables from `configs/text/{eng,rus}/*.xml`."""
    rx = re.compile(r'<string\s+id="([^"]+)"\s*>\s*<text>(.*?)</text>\s*</string>', re.S)
    tables: Dict[str, Dict[str, str]] = {"eng": {}, "rus": {}}
    for lang in ("eng", "rus"):
        st_dir = configs_dir / "text" / lang
        if not st_dir.is_dir():
            continue
        for xf in sorted(st_dir.glob("*.xml")):
            try:
                raw = xf.read_bytes().decode("cp1251", "ignore")
                for sid, txt in rx.findall(raw):
                    tables[lang][sid.strip()] = re.sub(r"\s+", " ", txt.strip())
            except Exception:
                pass
    return tables["eng"], tables["rus"]


def _parse_all_ltx_configs(configs_dir: Path = CONFIGS_DIR) -> Tuple[Dict[str, Dict[str, str]], Dict[str, List[str]], Dict[str, str]]:
    """
    Parses `system.ltx` and all `#include`d LTX files in `configs_dir`, resolving `[section]:parent1,parent2`
    inheritance. Returns `(resolved_sections, parents_map, source_file_map)`.
    """
    raw_sections: Dict[str, Dict[str, str]] = {}
    parents_map: Dict[str, List[str]] = {}
    source_map: Dict[str, str] = {}
    visited: set[Path] = set()

    def _load_file(fpath: Path) -> None:
        try:
            resolved_path = fpath.resolve()
        except Exception:
            return
        if resolved_path in visited or not resolved_path.is_file():
            return
        visited.add(resolved_path)

        try:
            raw_text = resolved_path.read_bytes().decode("cp1251", "ignore")
        except Exception:
            return

        try:
            rel_src = str(resolved_path.relative_to(configs_dir.resolve())).replace("\\", "/")
        except ValueError:
            rel_src = resolved_path.name

        cur_sec: Optional[str] = None
        for line in raw_text.splitlines():
            s = line.split(";")[0].strip()
            if not s:
                continue
            if s.lower().startswith("#include"):
                m = re.search(r'"([^"]+)"', s)
                if m:
                    inc_rel = m.group(1).replace("\\", "/")
                    inc_target = resolved_path.parent / inc_rel
                    if inc_target.is_file():
                        _load_file(inc_target)
                    else:
                        for g in sorted(resolved_path.parent.glob(inc_rel)):
                            _load_file(g)
                continue
            if s.startswith("[") and "]" in s:
                rb = s.index("]")
                sec_name = s[1:rb].strip()
                after = s[rb + 1 :].strip()
                p_list: List[str] = []
                if after.startswith(":"):
                    p_list = [p.strip() for p in after[1:].split(",") if p.strip()]
                cur_sec = sec_name
                raw_sections.setdefault(cur_sec, {})
                if p_list:
                    parents_map[cur_sec] = p_list
                source_map.setdefault(cur_sec, rel_src)
            elif "=" in s and cur_sec is not None:
                k, v = s.split("=", 1)
                raw_sections[cur_sec][k.strip()] = v.strip()
            elif cur_sec is not None:
                raw_sections[cur_sec][s] = ""

    # Start from system.ltx, then scan any remainingcreatures/items/weapons LTX files
    sys_ltx = configs_dir / "system.ltx"
    if sys_ltx.is_file():
        _load_file(sys_ltx)
    for extra_ltx in sorted(configs_dir.rglob("*.ltx")):
        if extra_ltx.resolve() not in visited:
            _load_file(extra_ltx)

    resolved_memo: Dict[str, Dict[str, str]] = {}

    def _resolve_section(sec: str, stack: Optional[set[str]] = None) -> Dict[str, str]:
        if sec in resolved_memo:
            return resolved_memo[sec]
        if stack is None:
            stack = set()
        if sec in stack:
            return dict(raw_sections.get(sec, {}))
        stack.add(sec)
        merged: Dict[str, str] = {}
        for parent in parents_map.get(sec, []):
            merged.update(_resolve_section(parent, stack))
        merged.update(raw_sections.get(sec, {}))
        resolved_memo[sec] = merged
        return merged

    for sec_key in list(raw_sections.keys()):
        _resolve_section(sec_key)

    return resolved_memo, parents_map, source_map


def _parse_character_profile_visuals(
    configs_dir: Path = CONFIGS_DIR, meshes_dir: Path = MESHES_DIR
) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, str]]:
    """
    Parses `gameplay/npc_profile.xml`, `gameplay/profiles/*.xml`, and `gameplay/character_desc_*.xml`
    to map each character profile / class to its verified `.ogf` visuals.
    Returns `(profile_to_class, class_to_verified_visuals, class_to_xml_file)`.
    """
    profile_to_class: Dict[str, str] = {}
    npc_prof_path = configs_dir / "gameplay" / "npc_profile.xml"
    if npc_prof_path.is_file():
        raw = npc_prof_path.read_bytes().decode("cp1251", "ignore")
        for m in re.finditer(r'<character\s+id="([^"]+)"\s*>(.*?)</character>', raw, re.S):
            cid = m.group(1).strip()
            body = m.group(2)
            cls_m = re.search(r"<class>\s*([^<\s]+)\s*</class>", body)
            spec_m = re.search(r"<specific_character>\s*([^<\s]+)\s*</specific_character>", body)
            if cls_m:
                profile_to_class[cid] = cls_m.group(1).strip()
            elif spec_m:
                profile_to_class[cid] = spec_m.group(1).strip()

    include_to_class: Dict[str, str] = {}
    profiles_dir = configs_dir / "gameplay" / "profiles"
    if profiles_dir.is_dir():
        for pf in sorted(profiles_dir.glob("*.xml")):
            raw = pf.read_bytes().decode("cp1251", "ignore")
            cls_m = re.search(r"<class>\s*([^<\s]+)\s*</class>", raw)
            if cls_m:
                include_to_class[pf.name] = cls_m.group(1).strip()

    class_to_visuals: Dict[str, List[str]] = {}
    class_to_xml: Dict[str, str] = {}
    gameplay_dir = configs_dir / "gameplay"
    if gameplay_dir.is_dir():
        for xf in sorted(gameplay_dir.glob("character_desc*.xml")):
            raw = xf.read_bytes().decode("cp1251", "ignore")
            rel_xml = f"gameplay/{xf.name}"
            for m in re.finditer(r'<specific_character\s+id="([^"]+)"[^>]*>(.*?)</specific_character>', raw, re.S):
                sc_id = m.group(1).strip()
                body = m.group(2)
                vis_m = re.search(r"<visual>\s*([^<\s]+)\s*</visual>", body)
                if not vis_m:
                    continue
                norm_vis, exists = verify_mesh_exists(vis_m.group(1), meshes_dir)
                if not exists:
                    continue
                cls_m = re.search(r"<class>\s*([^<\s]+)\s*</class>", body)
                cls_name = cls_m.group(1).strip() if cls_m else ""
                if not cls_name:
                    inc_m = re.search(r'#include\s+"([^"]+)"', body)
                    if inc_m:
                        inc_fname = Path(inc_m.group(1).replace("\\", "/")).name
                        cls_name = include_to_class.get(inc_fname, "")
                for key in {cls_name, sc_id}:
                    if key:
                        lst = class_to_visuals.setdefault(key, [])
                        if norm_vis not in lst:
                            lst.append(norm_vis)
                        class_to_xml.setdefault(key, rel_xml)

    return profile_to_class, class_to_visuals, class_to_xml


def _build_stalker_sections(
    resolved_ltx: Dict[str, Dict[str, str]],
    parents_map: Dict[str, List[str]],
    source_map: Dict[str, str],
    profile_to_class: Dict[str, str],
    class_to_visuals: Dict[str, List[str]],
    class_to_xml: Dict[str, str],
    meshes_dir: Path = MESHES_DIR,
) -> List[Dict[str, Any]]:
    stalker_entries: List[Dict[str, Any]] = []
    seen_sections: set[str] = set()

    def _make_stalker_entry(
        sec_name: str,
        canonical_sec: str,
        faction_key: Optional[str] = None,
        tier_override: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        kv = resolved_ltx.get(canonical_sec)
        if not kv:
            return None
        char_prof = kv.get("character_profile", canonical_sec).strip()
        prof_cls = profile_to_class.get(char_prof, char_prof)
        verified_visuals = list(class_to_visuals.get(prof_cls, []) or class_to_visuals.get(char_prof, []))

        ltx_vis_raw = kv.get("visual", r"actors\stalker_hero\stalker_hero_1.ogf")
        ltx_vis_norm, ltx_vis_ok = verify_mesh_exists(ltx_vis_raw, meshes_dir)

        primary_visual = verified_visuals[0] if verified_visuals else (ltx_vis_norm if ltx_vis_ok else "")
        if not primary_visual:
            return None
        primary_visual, mesh_ok = verify_mesh_exists(primary_visual, meshes_dir)
        if not mesh_ok:
            return None

        corpse_raw = kv.get("corpse_visual", r"dynamics\equipments\item_rukzak.ogf")
        corpse_norm, corpse_ok = verify_mesh_exists(corpse_raw, meshes_dir)

        community = kv.get("community", faction_key or "stalker").strip()
        spec_rank = kv.get("spec_rank", "novice").strip()
        faction = faction_key or ("dolg" if community == "dolg" else community)

        tier = tier_override
        if tier is None:
            m_tier = re.search(r"_(\d+)$", sec_name)
            tier = int(m_tier.group(1)) if m_tier else 0

        fac_lbl = FACTION_LABELS.get(faction, FACTION_LABELS.get(community, {"de": faction, "en": faction, "ru": faction}))
        tier_lbl = TIER_LABELS.get(tier, {"de": f"Spezial ({spec_rank})", "en": f"Special ({spec_rank})", "ru": f"Спец ({spec_rank})"})

        role_suffix = ""
        for role_k, role_de, role_en, role_ru in [
            ("_trader", "Händler", "Trader", "Торговец"),
            ("_mechanic", "Techniker", "Mechanic", "Техник"),
            ("_medic", "Sanitäter", "Medic", "Медик"),
            ("_barman", "Barkeeper", "Barman", "Бармен"),
            ("_sniper", "Scharfschütze", "Sniper", "Снайпер"),
            ("_dead", "Leiche / Gefallener", "Corpse / Dead", "Погибший"),
        ]:
            if sec_name.endswith(role_k):
                tier_lbl = {"de": role_de, "en": role_en, "ru": role_ru}
                role_suffix = role_k.lstrip("_")
                break

        src_file = source_map.get(canonical_sec, "creatures/spawn_sections_general.ltx")
        xml_file = class_to_xml.get(prof_cls, class_to_xml.get(char_prof, "gameplay/character_desc_general.xml"))

        entry: Dict[str, Any] = {
            "section": sec_name,
            "canonical_section": canonical_sec,
            "category": "stalker_sections",
            "sub_category": "stalker",
            "faction": faction,
            "community": community,
            "spec_rank": spec_rank,
            "tier": tier,
            "role": role_suffix or f"tier_{tier}",
            "parent_section": (parents_map.get(canonical_sec) or ["stalker"])[0],
            "character_profile": char_prof,
            "visual": primary_visual,
            "visual_ltx": primary_visual[:-4].replace("/", "\\"),
            "fallback_visual": ltx_vis_norm if ltx_vis_ok else primary_visual,
            "profile_visuals": verified_visuals[:12] if verified_visuals else [primary_visual],
            "profile_visuals_count": len(verified_visuals) if verified_visuals else 1,
            "corpse_visual": corpse_norm if corpse_ok else "",
            "mesh_exists": True,
            "source_file": src_file,
            "profile_xml": xml_file,
            "label_de": f"{fac_lbl['de']} — {tier_lbl['de']} [{sec_name}]",
            "label_en": f"{fac_lbl['en']} — {tier_lbl['en']} [{sec_name}]",
            "label_ru": f"{fac_lbl['ru']} — {tier_lbl['ru']} [{sec_name}]",
            "name_de": f"{fac_lbl['de']} ({tier_lbl['de']})",
            "name_en": f"{fac_lbl['en']} ({tier_lbl['en']})",
            "name_ru": f"{fac_lbl['ru']} ({tier_lbl['ru']})",
        }
        return entry

    # 1. Required 38 faction tier sections first
    for req_sec, canon_sec, fac_key, tier_num in REQUIRED_STALKER_SECTIONS:
        entry = _make_stalker_entry(req_sec, canon_sec, fac_key, tier_num)
        if entry:
            stalker_entries.append(entry)
            seen_sections.add(req_sec)

    # 2. Additional verified sim_default_* sections from spawn_sections_general.ltx
    for sec_name, src_file in sorted(source_map.items()):
        if sec_name in seen_sections:
            continue
        if not sec_name.startswith("sim_default_"):
            continue
        if src_file != "creatures/spawn_sections_general.ltx":
            continue
        entry = _make_stalker_entry(sec_name, sec_name)
        if entry:
            stalker_entries.append(entry)
            seen_sections.add(sec_name)

    return stalker_entries


def _build_mutant_sections(
    resolved_ltx: Dict[str, Dict[str, str]],
    parents_map: Dict[str, List[str]],
    source_map: Dict[str, str],
    en_st: Dict[str, str],
    ru_st: Dict[str, str],
    meshes_dir: Path = MESHES_DIR,
) -> List[Dict[str, Any]]:
    mutant_entries: List[Dict[str, Any]] = []
    seen_sections: set[str] = set()

    def _make_mutant_entry(
        sec_name: str,
        canonical_sec: str,
        custom_labels: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        kv = resolved_ltx.get(canonical_sec)
        if not kv:
            return None
        vis_raw = kv.get("visual", "")
        vis_norm, vis_ok = verify_mesh_exists(vis_raw, meshes_dir)
        if not vis_ok:
            return None

        corpse_raw = kv.get("corpse_visual", "")
        corpse_norm, corpse_ok = verify_mesh_exists(corpse_raw, meshes_dir)

        species = (
            (custom_labels or {}).get("species")
            or kv.get("species")
            or kv.get("community")
            or canonical_sec.split("_")[0]
        ).strip()
        spec_rank = kv.get("spec_rank", "normal").strip()
        cls_name = kv.get("class", "SM_MONST").strip()
        try:
            rank_val = int(float(kv.get("rank", "1") or 1))
        except ValueError:
            rank_val = 1

        sp_lbl = MUTANT_SPECIES_LABELS.get(
            species,
            {
                "de": species.replace("_", " ").title(),
                "en": species.replace("_", " ").title(),
                "ru": ru_st.get(f"enc_mutant_{species}", species.replace("_", " ").title()),
            },
        )
        rank_de = {"weak": "Schwach", "normal": "Normal", "strong": "Stark"}.get(spec_rank, spec_rank.title())
        rank_en = {"weak": "Weak", "normal": "Normal", "strong": "Strong"}.get(spec_rank, spec_rank.title())
        rank_ru = {"weak": "Слабый", "normal": "Обычный", "strong": "Сильный"}.get(spec_rank, spec_rank)

        name_de = (custom_labels or {}).get("de") or f"{sp_lbl['de']} ({rank_de})"
        name_en = (custom_labels or {}).get("en") or f"{sp_lbl['en']} ({rank_en})"
        name_ru = (custom_labels or {}).get("ru") or f"{sp_lbl['ru']} ({rank_ru})"

        src_file = source_map.get(canonical_sec, "creatures/monsters.ltx")
        return {
            "section": sec_name,
            "canonical_section": canonical_sec,
            "category": "mutant_sections",
            "sub_category": "mutant",
            "species": species,
            "kind": cls_name,
            "class": cls_name,
            "community": kv.get("community", species).strip(),
            "spec_rank": spec_rank,
            "rank": rank_val,
            "parent_section": (parents_map.get(canonical_sec) or ["monster_base"])[0],
            "visual": vis_norm,
            "visual_ltx": vis_norm[:-4].replace("/", "\\"),
            "corpse_visual": corpse_norm if corpse_ok else "",
            "corpse_mesh_exists": corpse_ok,
            "mesh_exists": True,
            "icon": kv.get("icon", ""),
            "source_file": src_file,
            "label_de": f"{name_de} [{sec_name}]",
            "label_en": f"{name_en} [{sec_name}]",
            "label_ru": f"{name_ru} [{sec_name}]",
            "name_de": name_de,
            "name_en": name_en,
            "name_ru": name_ru,
        }

    # 1. Place the 8 required mutant sections front and center
    for req_sec, canon_sec, lbl_info in REQUIRED_MUTANT_SECTIONS:
        entry = _make_mutant_entry(req_sec, canon_sec, lbl_info)
        if entry:
            mutant_entries.append(entry)
            seen_sections.add(req_sec)

    # 2. Scan remaining standard mutant sections in creatures/m_*.ltx
    skip_files = {
        "creatures/m_stalker.ltx",
        "creatures/m_stalker_monolith.ltx",
        "creatures/m_stalker_zombied.ltx",
        "creatures/m_person.ltx",
        "creatures/m_phantom.ltx",
        "creatures/m_crow.ltx",
    }
    for sec_name, src_file in sorted(source_map.items()):
        if sec_name in seen_sections:
            continue
        if not src_file.startswith("creatures/m_") or src_file in skip_files:
            continue
        if sec_name.endswith("_e") or "critical_wound" in sec_name or "step_params" in sec_name:
            continue
        kv = resolved_ltx.get(sec_name, {})
        if not kv.get("visual"):
            continue
        if not kv.get("class", "").startswith("SM_"):
            continue
        entry = _make_mutant_entry(sec_name, sec_name)
        if entry:
            mutant_entries.append(entry)
            seen_sections.add(sec_name)

    return mutant_entries


def _classify_item_subcategory(sec_name: str, kv: Dict[str, str], src_file: str) -> Optional[str]:
    """Classifies an item/weapon/container section from `configs/items/` into a clean `sub_category`."""
    cls_val = kv.get("class", "").strip()
    kind_val = kv.get("kind", "").strip().lower()
    quest_flag = kv.get("quest_item", "false").strip().lower() == "true"

    if cls_val in ("S_INVBOX", "O_INVBOX") or sec_name in (
        "inventory_box",
        "hidden_box",
        "inv_backpack",
        "inv_actor_backpack",
        "inv_backpack_fake",
    ):
        return "container"
    if src_file.startswith("items/items/items_container_"):
        # Base container items (af_aac, af_aam, af_iam, af_llmc)
        if sec_name in ("af_aac", "af_aam", "af_iam", "af_llmc"):
            return "container"
        return None  # Skip per-artefact container permutation sections
    if src_file == "items/items/items_quest.ltx" or kind_val == "i_quest" or quest_flag:
        return "quest_item"
    if src_file == "items/items/items_medical.ltx" or kind_val == "i_medical":
        return "medkit"
    if src_file.startswith("items/weapons/"):
        if src_file == "items/weapons/weapon_ammo.ltx" or cls_val.startswith("AMMO"):
            return "ammo"
        if src_file in ("items/weapons/weapon_addons.ltx", "items/weapons/weapon_scopes.ltx", "items/weapons/weapon_silencers.ltx"):
            return "weapon_addon"
        if cls_val.startswith("WP_") or cls_val.startswith("G_") or sec_name.startswith("wpn_"):
            # Skip sight permutation variants (e.g. wpn_ak74_ac10632) to keep catalog clean and fast,
            # while keeping all primary weapon sections defined at top of w_*.ltx
            return "weapon"
        return None
    if src_file.startswith("items/items/items_artefacts"):
        return "artefact"
    if src_file == "items/items/items_devices.ltx" or kind_val in ("i_device", "i_kit"):
        return "device"
    if src_file.startswith("items/outfits/"):
        return "outfit"
    if src_file in ("items/items/items_food.ltx", "items/items/items_drink.ltx", "items/items/items_drugs.ltx"):
        return "consumable"
    if src_file in ("items/items/items_tools.ltx", "items/items/items_repair.ltx"):
        return "tool"
    if src_file.startswith("items/items/items_explosives"):
        return "explosive"
    return None


def _build_quest_and_loot_items(
    resolved_ltx: Dict[str, Dict[str, str]],
    parents_map: Dict[str, List[str]],
    source_map: Dict[str, str],
    en_st: Dict[str, str],
    ru_st: Dict[str, str],
    meshes_dir: Path = MESHES_DIR,
) -> List[Dict[str, Any]]:
    items_list: List[Dict[str, Any]] = []
    seen_sections: set[str] = set()

    # Priority sections to feature at the top of quest_and_loot_items
    priority_sections = [
        # Containers / Stashes
        "inventory_box",
        "hidden_box",
        "inv_backpack",
        "inv_actor_backpack",
        "af_aac",
        "af_aam",
        "af_iam",
        "af_llmc",
        # Quest items
        "zat_b33_safe_container",
        "jup_b9_blackbox",
        "quest_package_1",
        "drx_sl_quest_item_1",
        "main_story_1_quest_case",
        "broken_pda",
        "jup_b10_ufo_memory",
        "jup_b209_monster_scanner",
        "pri_a19_lab_x16_info",
        "val_key_to_underground",
        # Medkits & Medical
        "medkit",
        "medkit_army",
        "medkit_scientic",
        "bandage",
        "jgut",
        "stimpack",
        "stimpack_army",
        "stimpack_scientic",
        "survival_kit",
        "rebirth",
        "morphine",
        "adrenalin",
        # Weapons
        "wpn_pm",
        "wpn_fort",
        "wpn_beretta",
        "wpn_colt1911",
        "wpn_usp",
        "wpn_desert_eagle",
        "wpn_bm16",
        "wpn_toz34",
        "wpn_wincheaster1300",
        "wpn_spas12",
        "wpn_saiga12s",
        "wpn_protecta",
        "wpn_mp5",
        "wpn_bizon",
        "wpn_p90",
        "wpn_ak74u",
        "wpn_ak74",
        "wpn_ak74m",
        "wpn_abakan",
        "wpn_groza",
        "wpn_val",
        "wpn_vintorez",
        "wpn_lr300",
        "wpn_m4",
        "wpn_m4a1",
        "wpn_sig550",
        "wpn_g36",
        "wpn_fn2000",
        "wpn_scar",
        "wpn_svd",
        "wpn_svu",
        "wpn_l96a1",
        "wpn_gauss",
        "wpn_pkm",
        "wpn_rpg7",
        "wpn_rg-6",
        "wpn_knife",
        "grenade_rgd5",
        "grenade_f1",
        # Devices
        "device_pda_1",
        "device_pda_2",
        "device_pda_3",
        "detector_simple",
        "detector_advanced",
        "detector_elite",
        "detector_scientific",
        "detector_anomaly",
        "detector_geiger",
        "device_flashlight",
        # Artefacts
        "af_medusa",
        "af_cristall_flower",
        "af_night_star",
        "af_vyvert",
        "af_gravi",
        "af_gold_fish",
        "af_cristall",
        "af_fireball",
        "af_blood",
        "af_soul",
        "af_electra_sparkler",
        "af_electra_flash",
        "af_electra_moonlight",
        "af_compass",
        "af_oasis_heart",
    ]

    # Determine primary weapon sections vs scope attachment sub-variants
    scope_suffixes = (
        "_ac10632", "_acog", "_eot", "_c-more", "_kobra", "_1p29", "_pso1m21",
        "_ps01", "_pso2", "_1pn93", "_pka", "_ekp8_02", "_okp", "_ekp8_18",
        "_0kp2", "_d0cter", "_mepro", "_aimpoint", "_aim_low", "_point_aimpro",
        "_specter", "_leupold", "_marchf", "_pn23", "_gauss_sight", "_susat",
        "_barska", "_rmr", "_deltapoint", "_rakurs", "_p1x42", "_kemper",
    )

    def _make_item_entry(sec_name: str) -> Optional[Dict[str, Any]]:
        if sec_name.endswith("_hud") or sec_name.startswith("tch_") or sec_name.startswith("mp_"):
            return None
        kv = resolved_ltx.get(sec_name)
        if not kv:
            return None
        src_file = source_map.get(sec_name, "")
        sub_cat = _classify_item_subcategory(sec_name, kv, src_file)
        if not sub_cat:
            return None

        # Filter out scope attachment permutations on weapons unless in priority_sections
        if sub_cat == "weapon" and sec_name not in priority_sections:
            if any(sec_name.endswith(sfx) for sfx in scope_suffixes):
                return None

        vis_raw = kv.get("visual", "")
        vis_norm, vis_ok = verify_mesh_exists(vis_raw, meshes_dir)
        if not vis_ok:
            return None

        inv_name_id = kv.get("inv_name", kv.get("inv_name_short", "")).strip()
        name_en = en_st.get(inv_name_id, "")
        name_ru = ru_st.get(inv_name_id, "")
        if not name_en:
            if sec_name == "inventory_box":
                name_en = "Inventory Box / Stash Case"
                name_ru = "Инвентарный ящик / Тайник"
            elif sec_name == "hidden_box":
                name_en = "Hidden Stash Box"
                name_ru = "Скрытый тайник"
            elif sec_name in ("inv_backpack", "inv_actor_backpack", "inv_backpack_fake"):
                name_en = f"Backpack Stash ({sec_name})"
                name_ru = f"Рюкзак-тайник ({sec_name})"
            else:
                name_en = inv_name_id or sec_name
        if not name_ru:
            name_ru = name_en

        sub_de = SUBCATEGORY_DE_LABELS.get(sub_cat, sub_cat)
        name_de = f"{name_en} ({sub_de})"

        try:
            cost_val = int(float(kv.get("cost", "0").split()[0] or 0))
        except Exception:
            cost_val = 0
        try:
            weight_val = round(float(kv.get("inv_weight", "0").split()[0] or 0.0), 3)
        except Exception:
            weight_val = 0.0

        cls_val = kv.get("class", "").strip()
        kind_val = kv.get("kind", sub_cat).strip()
        quest_flag = kv.get("quest_item", "false").strip().lower() == "true" or sub_cat == "quest_item"

        return {
            "section": sec_name,
            "category": "quest_and_loot_items",
            "sub_category": sub_cat,
            "parent_section": (parents_map.get(sec_name) or [""])[0],
            "visual": vis_norm,
            "visual_ltx": vis_norm[:-4].replace("/", "\\"),
            "mesh_exists": True,
            "inv_name": inv_name_id,
            "class": cls_val,
            "kind": kind_val,
            "cost": cost_val,
            "weight": weight_val,
            "quest_item": quest_flag,
            "source_file": src_file,
            "label_de": f"{name_de} [{sec_name}]",
            "label_en": f"{name_en} [{sec_name}]",
            "label_ru": f"{name_ru} [{sec_name}]",
            "name_de": name_de,
            "name_en": name_en,
            "name_ru": name_ru,
        }

    # 1. Priority items first
    for p_sec in priority_sections:
        if p_sec in seen_sections:
            continue
        entry = _make_item_entry(p_sec)
        if entry:
            items_list.append(entry)
            seen_sections.add(p_sec)

    # 2. All other verified items across configs/items/ and configs/weapons/
    for sec_name in sorted(source_map.keys()):
        if sec_name in seen_sections:
            continue
        entry = _make_item_entry(sec_name)
        if entry:
            items_list.append(entry)
            seen_sections.add(sec_name)

    return items_list


def build_verified_spawn_catalog(save_to_disk: bool = True) -> Dict[str, Any]:
    """
    Scans `tools/_unpacked/configs/` and `tools/_unpacked/meshes/`, builds the complete
    100% mesh-verified spawn catalog, and writes `anomaly_studio/index/verified_spawn_catalog.json`.
    """
    global _CATALOG_CACHE

    en_st, ru_st = _load_string_tables(CONFIGS_DIR)
    resolved_ltx, parents_map, source_map = _parse_all_ltx_configs(CONFIGS_DIR)
    profile_to_class, class_to_visuals, class_to_xml = _parse_character_profile_visuals(
        CONFIGS_DIR, MESHES_DIR
    )

    stalker_sections = _build_stalker_sections(
        resolved_ltx,
        parents_map,
        source_map,
        profile_to_class,
        class_to_visuals,
        class_to_xml,
        MESHES_DIR,
    )
    mutant_sections = _build_mutant_sections(
        resolved_ltx,
        parents_map,
        source_map,
        en_st,
        ru_st,
        MESHES_DIR,
    )
    quest_and_loot_items = _build_quest_and_loot_items(
        resolved_ltx,
        parents_map,
        source_map,
        en_st,
        ru_st,
        MESHES_DIR,
    )

    by_sub_category: Dict[str, int] = {}
    for it in quest_and_loot_items:
        sc = it.get("sub_category", "other")
        by_sub_category[sc] = by_sub_category.get(sc, 0) + 1

    by_faction: Dict[str, int] = {}
    for st in stalker_sections:
        fac = st.get("faction", "other")
        by_faction[fac] = by_faction.get(fac, 0) + 1

    all_entries = stalker_sections + mutant_sections + quest_and_loot_items
    all_verified = all(
        bool(e.get("mesh_exists")) and (MESHES_DIR / e["visual"]).is_file()
        for e in all_entries
    )

    catalog: Dict[str, Any] = {
        "ok": True,
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configs_root": str(CONFIGS_DIR),
        "meshes_root": str(MESHES_DIR),
        "index_path": str(CATALOG_JSON_PATH),
        "all_meshes_verified": all_verified,
        "counts": {
            "stalker_sections": len(stalker_sections),
            "mutant_sections": len(mutant_sections),
            "quest_and_loot_items": len(quest_and_loot_items),
            "total": len(all_entries),
            "by_faction": by_faction,
            "by_sub_category": by_sub_category,
        },
        "stalker_sections": stalker_sections,
        "mutant_sections": mutant_sections,
        "quest_and_loot_items": quest_and_loot_items,
    }

    if save_to_disk:
        STUDIO_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        CATALOG_JSON_PATH.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    _CATALOG_CACHE = catalog
    return catalog


def _load_or_build_catalog(force_rebuild: bool = False) -> Dict[str, Any]:
    global _CATALOG_CACHE
    if not force_rebuild and _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    if not force_rebuild and CATALOG_JSON_PATH.is_file():
        try:
            data = json.loads(CATALOG_JSON_PATH.read_text(encoding="utf-8"))
            if (
                isinstance(data, dict)
                and isinstance(data.get("stalker_sections"), list)
                and isinstance(data.get("mutant_sections"), list)
                and isinstance(data.get("quest_and_loot_items"), list)
            ):
                _CATALOG_CACHE = data
                return data
        except Exception:
            pass
    return build_verified_spawn_catalog(save_to_disk=True)


def _matches_query(entry: Dict[str, Any], q_lower: str) -> bool:
    if not q_lower:
        return True
    haystack_fields = (
        entry.get("section", ""),
        entry.get("canonical_section", ""),
        entry.get("category", ""),
        entry.get("sub_category", ""),
        entry.get("faction", ""),
        entry.get("community", ""),
        entry.get("species", ""),
        entry.get("spec_rank", ""),
        entry.get("visual", ""),
        entry.get("inv_name", ""),
        entry.get("class", ""),
        entry.get("kind", ""),
        entry.get("source_file", ""),
        entry.get("label_de", ""),
        entry.get("label_en", ""),
        entry.get("label_ru", ""),
        entry.get("name_de", ""),
        entry.get("name_en", ""),
        entry.get("name_ru", ""),
    )
    for val in haystack_fields:
        if val and q_lower in str(val).lower():
            return True
    return False


def get_verified_spawn_catalog(category: str = None, query: str = "") -> dict:
    """
    Returns the 100% mesh-verified spawn catalog for the 3D World & Quest Director.

    Args:
        category: Optional category filter:
          - `None`, `""`, `"all"`, `"*"` -> all three categories
          - `"stalker_sections"` (or `"stalkers"`, `"stalker"`, `"npc"`, `"npcs"`)
          - `"mutant_sections"` (or `"mutants"`, `"mutant"`, `"monsters"`, `"monster"`)
          - `"quest_and_loot_items"` (or `"items"`, `"loot"`)
          - Any item `sub_category` (`"quest_item"`, `"medkit"`, `"weapon"`, `"container"`,
            `"ammo"`, `"artefact"`, `"device"`, `"outfit"`, `"consumable"`, `"tool"`, `"explosive"`)
          - Any stalker `faction` (`"dolg"`, `"duty"`, `"freedom"`, `"monolith"`, `"killer"`,
            `"bandit"`, `"military"`, `"ecolog"`, `"csky"`, `"renegade"`, `"greh"`, `"isg"`, `"zombied"`)
        query: Optional case-insensitive search substring matched against section ID,
               visual `.ogf` path, faction, species, sub_category, inv_name, and DE/EN/RU labels.
    """
    base_catalog = _load_or_build_catalog(force_rebuild=False)
    cat_norm = (category or "").strip().lower()
    q_norm = (query or "").strip().lower()

    stalkers = list(base_catalog.get("stalker_sections", []))
    mutants = list(base_catalog.get("mutant_sections", []))
    loot_items = list(base_catalog.get("quest_and_loot_items", []))

    # Category filtering
    if cat_norm in ("", "all", "*"):
        pass
    elif cat_norm in ("stalker_sections", "stalkers", "stalker", "npc", "npcs"):
        mutants = []
        loot_items = []
    elif cat_norm in ("mutant_sections", "mutants", "mutant", "monsters", "monster"):
        stalkers = []
        loot_items = []
    elif cat_norm in ("quest_and_loot_items", "items", "loot", "quest_and_loot"):
        stalkers = []
        mutants = []
    else:
        # Check subcategory aliases for quest_and_loot_items or faction/species filters
        subcat_aliases = {
            "quest_item": "quest_item",
            "quest_items": "quest_item",
            "quest": "quest_item",
            "medkit": "medkit",
            "medkits": "medkit",
            "medical": "medkit",
            "weapon": "weapon",
            "weapons": "weapon",
            "weapon_addon": "weapon_addon",
            "container": "container",
            "containers": "container",
            "stash": "container",
            "inventory_box": "container",
            "ammo": "ammo",
            "artefact": "artefact",
            "artefacts": "artefact",
            "artifact": "artefact",
            "artifacts": "artefact",
            "device": "device",
            "devices": "device",
            "outfit": "outfit",
            "outfits": "outfit",
            "consumable": "consumable",
            "consumables": "consumable",
            "tool": "tool",
            "tools": "tool",
            "explosive": "explosive",
            "explosives": "explosive",
        }
        if cat_norm in subcat_aliases:
            target_sub = subcat_aliases[cat_norm]
            stalkers = []
            mutants = []
            loot_items = [it for it in loot_items if it.get("sub_category") == target_sub]
        elif cat_norm in FACTION_LABELS:
            target_fac = "dolg" if cat_norm == "duty" else ("military" if cat_norm == "army" else cat_norm)
            stalkers = [
                st for st in stalkers
                if st.get("faction") == target_fac or st.get("community") == cat_norm
            ]
            mutants = []
            loot_items = []
        elif cat_norm in MUTANT_SPECIES_LABELS:
            stalkers = []
            mutants = [m for m in mutants if m.get("species") == cat_norm]
            loot_items = []
        else:
            # Generic category match against category, sub_category, faction, or species
            stalkers = [
                st for st in stalkers
                if cat_norm in (st.get("category", "").lower(), st.get("sub_category", "").lower(), st.get("faction", "").lower())
            ]
            mutants = [
                m for m in mutants
                if cat_norm in (m.get("category", "").lower(), m.get("sub_category", "").lower(), m.get("species", "").lower())
            ]
            loot_items = [
                it for it in loot_items
                if cat_norm in (it.get("category", "").lower(), it.get("sub_category", "").lower(), it.get("kind", "").lower())
            ]

    # Query filtering
    if q_norm:
        stalkers = [st for st in stalkers if _matches_query(st, q_norm)]
        mutants = [m for m in mutants if _matches_query(m, q_norm)]
        loot_items = [it for it in loot_items if _matches_query(it, q_norm)]

    combined = stalkers + mutants + loot_items
    by_section = {entry["section"]: entry for entry in combined}
    by_sub_cat: Dict[str, int] = {}
    for it in loot_items:
        sc = it.get("sub_category", "other")
        by_sub_cat[sc] = by_sub_cat.get(sc, 0) + 1

    return {
        "ok": True,
        "category_filter": category,
        "query": query,
        "index_path": str(CATALOG_JSON_PATH),
        "configs_root": str(CONFIGS_DIR),
        "meshes_root": str(MESHES_DIR),
        "all_meshes_verified": base_catalog.get("all_meshes_verified", True),
        "counts": {
            "stalker_sections": len(stalkers),
            "mutant_sections": len(mutants),
            "quest_and_loot_items": len(loot_items),
            "total": len(combined),
            "by_sub_category": by_sub_cat,
        },
        "stalker_sections": stalkers,
        "mutant_sections": mutants,
        "quest_and_loot_items": loot_items,
        "items": combined,
        "by_section": by_section,
    }


if __name__ == "__main__":
    cat = build_verified_spawn_catalog(save_to_disk=True)
    print(f"[spawn_catalog_service] Built {CATALOG_JSON_PATH}")
    print(f"  all_meshes_verified:  {cat['all_meshes_verified']}")
    print(f"  stalker_sections:     {cat['counts']['stalker_sections']}")
    print(f"  mutant_sections:      {cat['counts']['mutant_sections']}")
    print(f"  quest_and_loot_items: {cat['counts']['quest_and_loot_items']}")
    print(f"  total verified:       {cat['counts']['total']}")
    print(f"  by_sub_category:      {cat['counts']['by_sub_category']}")
