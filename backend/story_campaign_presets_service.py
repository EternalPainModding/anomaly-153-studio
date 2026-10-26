#!/usr/bin/env python3
"""
Quest & Storyline Template Service for S.T.A.L.K.E.R. Anomaly 1.5.3 Studio.
Provides built-in and user-created quest templates, NPC presets, Smart Terrain presets,
and Quest Item presets so users can either pick from a list, type custom IDs, or save
their own templates without having to memorize raw X-Ray condlists.
Author/Credits: EternalPain
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

STUDIO_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_TEMPLATES_FILE = STUDIO_ROOT / "config" / "custom_quest_templates.json"

BUILTIN_QUEST_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "wolf_carpark_box",
        "name_en": "Cordon: Wolf -> Find Box at Carpark & Return",
        "name_ru": "Кордон: Волк -> Найти ящик на АТП и вернуть",
        "archetype": "fetch_return",
        "level": "l01_escape",
        "giver_id": "esc_2_12_stalker_wolf",
        "target_smart": "esc_smart_terrain_7_11",
        "target_coords": [112.5, -7.2, -16.0],
        "item_section": "quest_case_01",
        "item_mesh": "dynamics\\equipments\\quest\\box_black.ogf",
        "reward_money": "4500:6000",
        "reward_faction": "stalker",
        "reward_goodwill": 50,
        "reward_stash": True,
        "title_en": "Recover Wolf's Supply Box from the Carpark",
        "title_ru": "Найти ящик с припасами Волка на АТП",
        "descr_en": "Search the bandit-held Carpark in Cordon for Wolf's sealed supply box and bring it back to him in the Rookie Village.",
        "descr_ru": "Обыскать АТП на Кордоне, найти закрытый ящик с припасами и принести его Волку в деревню новичков.",
    },
    {
        "id": "fetch_item_return",
        "name_en": "Generic: Fetch Item from Location & Return to NPC",
        "name_ru": "Шаблон: Найти предмет в точке и вернуть НПС",
        "archetype": "fetch_return",
        "level": "l01_escape",
        "giver_id": "esc_m_trader",
        "target_smart": "esc_smart_terrain_5_7",
        "target_coords": [5.0, 1.2, 265.0],
        "item_section": "device_pda_1",
        "item_mesh": "dynamics\\devices\\dev_pda\\dev_pda.ogf",
        "reward_money": "3500:5000",
        "reward_faction": "stalker",
        "reward_goodwill": 40,
        "reward_stash": True,
        "title_en": "Recover the Lost PDA",
        "title_ru": "Найти потерянный КПК",
        "descr_en": "Locate the missing PDA at the target coordinates and return it to the client.",
        "descr_ru": "Найти потерянный КПК в указанной точке и вернуть его заказчику.",
    },
    {
        "id": "eliminate_smart_squad",
        "name_en": "Generic: Clear Hostile Camp / Smart Terrain",
        "name_ru": "Шаблон: Зачистить лагерь противника (Smart Terrain)",
        "archetype": "clear_smart",
        "level": "l01_escape",
        "giver_id": "esc_2_12_stalker_wolf",
        "target_smart": "esc_smart_terrain_7_11",
        "target_coords": [112.5, -7.2, -16.0],
        "item_section": "",
        "item_mesh": "",
        "reward_money": "5000:7000",
        "reward_faction": "stalker",
        "reward_goodwill": 60,
        "reward_stash": True,
        "title_en": "Eliminate Hostiles at the Target Outpost",
        "title_ru": "Зачистить враждебный лагерь",
        "descr_en": "Clear out the hostile forces occupying the target smart terrain and report back.",
        "descr_ru": "Уничтожить противника в указанном лагере и вернуться за наградой.",
    },
    {
        "id": "scout_recon_spot",
        "name_en": "Generic: Recon / Scout Target Area",
        "name_ru": "Шаблон: Разведка территории",
        "archetype": "recon_smart",
        "level": "l01_escape",
        "giver_id": "esc_2_12_stalker_fanat",
        "target_smart": "esc_smart_terrain_4_9",
        "target_coords": [-75.0, -9.5, -45.0],
        "item_section": "",
        "item_mesh": "",
        "reward_money": "2500:3500",
        "reward_faction": "stalker",
        "reward_goodwill": 30,
        "reward_stash": False,
        "title_en": "Scout the Anomaly Sector",
        "title_ru": "Разведать сектор",
        "descr_en": "Reach the designated sector, investigate the area, and return to the quest giver.",
        "descr_ru": "Добраться до указанного сектора, осмотреть территорию и доложить.",
    },
]

PRESET_NPCS: List[Dict[str, str]] = [
    {"id": "esc_2_12_stalker_wolf", "label_en": "Wolf (Cordon Rookie Village)", "label_ru": "Волк (Кордон, Деревня новичков)"},
    {"id": "esc_m_trader", "label_en": "Sidorovich (Cordon Bunker)", "label_ru": "Сидорович (Кордон, Бункер)"},
    {"id": "esc_2_12_stalker_fanat", "label_en": "Fanatic (Cordon Rookie Village)", "label_ru": "Фанат (Кордон, Деревня новичков)"},
    {"id": "esc_2_12_stalker_nimble", "label_en": "Nimble (Cordon Rookie Village)", "label_ru": "Шустрый (Кордон, Деревня новичков)"},
    {"id": "esc_3_16_military_trader", "label_en": "Major Zhurov (Cordon Southern Checkpoint)", "label_ru": "Военный торговец (Кордон, Южный блокпост)"},
    {"id": "bar_visitors_barman_stalker_trader", "label_en": "Barkeeper (Rostok 100 Rads Bar)", "label_ru": "Бармен (Росток, Бар 100 Рентген)"},
    {"id": "yan_stalker_sakharov", "label_en": "Prof. Sakharov (Yantar Mobile Lab)", "label_ru": "Проф. Сахаров (Янтарь, Бункер учёных)"},
    {"id": "mar_smart_terrain_base_stalker_leader_marsh", "label_en": "Cold (Great Swamps Clear Sky Base)", "label_ru": "Холод (Болота, База Чистого Неба)"},
    {"id": "jup_b220_trapper", "label_en": "Trapper (Jupiter Yanov Station)", "label_ru": "Зверобой (Юпитер, Станция Янов)"},
]

PRESET_LOCATIONS: List[Dict[str, Any]] = [
    {"id": "esc_smart_terrain_7_11", "level": "l01_escape", "coords": [112.5, -7.2, -16.0], "label_en": "Cordon: Carpark / ATP (Bandit Courtyard)", "label_ru": "Кордон: АТП (Лагерь бандитов)"},
    {"id": "esc_smart_terrain_2_12", "level": "l01_escape", "coords": [-212.5, -19.8, -142.0], "label_en": "Cordon: Rookie Village (Wolf / Sidorovich)", "label_ru": "Кордон: Деревня новичков"},
    {"id": "esc_smart_terrain_5_7", "level": "l01_escape", "coords": [5.0, 1.2, 265.0], "label_en": "Cordon: Northern Farmstead", "label_ru": "Кордон: Северная ферма"},
    {"id": "esc_smart_terrain_4_9", "level": "l01_escape", "coords": [-75.0, -9.5, -45.0], "label_en": "Cordon: Forest Mutant Lair", "label_ru": "Кордон: Лесное логово"},
    {"id": "esc_smart_terrain_6_8", "level": "l01_escape", "coords": [58.0, 2.0, 152.0], "label_en": "Cordon: Collapsed Railway Bridge", "label_ru": "Кордон: Разрушенный ж/д мост"},
    {"id": "esc_smart_terrain_3_16", "level": "l01_escape", "coords": [-155.0, -29.5, -360.0], "label_en": "Cordon: Southern Military Checkpoint", "label_ru": "Кордон: Южный военный блокпост"},
    {"id": "esc_smart_terrain_5_9", "level": "l01_escape", "coords": [12.0, 16.5, 95.0], "label_en": "Cordon: Old Mill / Elevator", "label_ru": "Кордон: Элеватор"},
]

PRESET_ITEMS: List[Dict[str, str]] = [
    {"id": "quest_case_01", "mesh": "dynamics\\equipments\\quest\\box_black.ogf", "label_en": "Sealed Metal Supply Box / Case (quest_case_01)", "label_ru": "Закрытый металлический кейс/ящик (quest_case_01)"},
    {"id": "quest_case_02", "mesh": "dynamics\\equipments\\quest\\notes_document_case_1.ogf", "label_en": "Reinforced Field Box (quest_case_02)", "label_ru": "Укреплённый полевой ящик (quest_case_02)"},
    {"id": "device_pda_1", "mesh": "dynamics\\devices\\dev_pda\\dev_pda.ogf", "label_en": "Stalker PDA (device_pda_1)", "label_ru": "КПК сталкера (device_pda_1)"},
    {"id": "main_story_1_quest_case", "mesh": "dynamics\\equipments\\quest\\box_black.ogf", "label_en": "Encrypted Lab Document Case", "label_ru": "Зашифрованный контейнер документов"},
    {"id": "af_medusa", "mesh": "dynamics\\artefacts\\af_medusa.ogf", "label_en": "Jellyfish Artifact (af_medusa)", "label_ru": "Артефакт Медуза (af_medusa)"},
    {"id": "drug_anabiotic", "mesh": "dynamics\\equipments\\medical\\drug_anabiotic.ogf", "label_en": "Anabiotic Medical Box (drug_anabiotic)", "label_ru": "Анабиотик (drug_anabiotic)"},
]


def load_custom_templates() -> List[Dict[str, Any]]:
    if CUSTOM_TEMPLATES_FILE.is_file():
        try:
            data = json.loads(CUSTOM_TEMPLATES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save_custom_template(payload: Dict[str, Any]) -> Dict[str, Any]:
    CUSTOM_TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    custom = load_custom_templates()
    raw_name = (payload.get("name_en") or payload.get("title_en") or "Custom Quest Template").strip()
    tid = payload.get("id") or ("custom_tpl_" + re.sub(r"[^a-z0-9_]+", "_", raw_name.lower()).strip("_"))
    entry = {
        "id": tid,
        "custom": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "name_en": raw_name,
        "name_ru": (payload.get("name_ru") or payload.get("title_ru") or raw_name).strip(),
        "archetype": payload.get("archetype", "fetch_return"),
        "level": payload.get("level", "l01_escape"),
        "giver_id": payload.get("giver_id", "esc_2_12_stalker_wolf"),
        "target_smart": payload.get("target_smart", "esc_smart_terrain_7_11"),
        "target_coords": payload.get("target_coords", [112.5, -7.2, -16.0]),
        "item_section": payload.get("item_section", "quest_case_01"),
        "item_mesh": payload.get("item_mesh", "dynamics\\equipments\\quest\\box_black.ogf"),
        "reward_money": payload.get("reward_money", "4500:6000"),
        "reward_faction": payload.get("reward_faction", "stalker"),
        "reward_goodwill": int(payload.get("reward_goodwill", 50) or 50),
        "reward_stash": bool(payload.get("reward_stash", True)),
        "title_en": payload.get("title_en", raw_name),
        "title_ru": payload.get("title_ru", raw_name),
        "descr_en": payload.get("descr_en", ""),
        "descr_ru": payload.get("descr_ru", ""),
        "target_functor": payload.get("target_functor", ""),
        "cond": payload.get("cond", ""),
        "on_complete": payload.get("on_complete", ""),
    }
    custom = [c for c in custom if c.get("id") != tid]
    custom.append(entry)
    CUSTOM_TEMPLATES_FILE.write_text(json.dumps(custom, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "template": entry, "total_custom": len(custom)}


def get_quest_campaign_templates() -> Dict[str, Any]:
    custom = load_custom_templates()
    return {
        "ok": True,
        "templates": BUILTIN_QUEST_TEMPLATES + custom,
        "npcs": PRESET_NPCS,
        "locations": PRESET_LOCATIONS,
        "items": PRESET_ITEMS,
    }


def instantiate_quest_template(payload: Dict[str, Any]) -> Dict[str, Any]:
    tid = payload.get("template_id", "wolf_carpark_box")
    all_tpls = BUILTIN_QUEST_TEMPLATES + load_custom_templates()
    tpl = next((t for t in all_tpls if t.get("id") == tid), BUILTIN_QUEST_TEMPLATES[0])
    return {
        "ok": True,
        "template_id": tid,
        "template": tpl,
    }
