#!/usr/bin/env python3
"""
Anomaly 1.5.3 Studio — Custom Quest-Item Cloner & Gamedata Mesh/LTX/DLTX Bundler Service
Provides:
- Curated 100% Base-Anomaly-compatible quest item templates (:tch_quest) with verified .ogf meshes
- One-click cloning of quest items into LTX ([<section_id>]:tch_quest), DLTX (@[<section_id>]:tch_quest),
  and string-table XML snippets (st_<section_id>_name / st_<section_id>_descr)
- Persistent index storage in tools/_re_index/custom_quest_items.json (mirrored to _re_index/custom_quest_items.json)
- Automatic gamedata bundling (<gamedata_dir>/configs/items/items/items_studio_custom.ltx,
  <gamedata_dir>/configs/mod_system_studio_quest_items.ltx, and physical .ogf copy into <gamedata_dir>/meshes/...)
  so Base-Anomaly players without unpacked db archives never hit a ModelPool crash.
"""
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent.parent
UNPACKED_DIR = ROOT / ".studio_cache" / "vfs_mount"
UNPACKED_MESHES_DIR = UNPACKED_DIR / "meshes"
TOOLS_RE_INDEX_DIR = ROOT / "index"
MAIN_RE_INDEX_DIR = ROOT / "index"

CUSTOM_QUEST_ITEMS_PATH = TOOLS_RE_INDEX_DIR / "custom_quest_items.json"
MIRROR_QUEST_ITEMS_PATH = MAIN_RE_INDEX_DIR / "custom_quest_items.json"

VANILLA_QUEST_ITEM_TEMPLATES = [
    {
        "id": "safe_container",
        "template_id": "safe_container",
        "parent_section": "tch_quest",
        "vanilla_reference_section": "zat_b33_safe_container",
        "visual": r"dynamics\equipments\quest\safe_container.ogf",
        "mesh_rel_posix": "dynamics/equipments/quest/safe_container.ogf",
        "kind": "i_quest",
        "class": "II_ATTCH",
        "inv_grid_width": 2,
        "inv_grid_height": 2,
        "inv_grid_x": 4,
        "inv_grid_y": 11,
        "default_weight": 6.0,
        "default_cost": 100,
        "label_de": "Gepanzerter Militär-/Transceiver-Koffer (safe_container, 2x2 Grid)",
        "label_en": "Armored Military / Transceiver Case (safe_container, 2x2 Grid)",
        "label_ru": "Бронированный военный кейс / трансивер (safe_container, 2x2)",
        "descr_de": "Schwerer, versiegelter Militär-Container für Transceiver, Schlüsselkarten oder geheime Forschungsproben.",
        "descr_en": "Heavy sealed military container used for transceivers, keycards, or classified research samples.",
        "descr_ru": "Тяжёлый герметичный военный контейнер для трансиверов, ключ-карт или секретных образцов.",
    },
    {
        "id": "box_black",
        "template_id": "box_black",
        "parent_section": "tch_quest",
        "vanilla_reference_section": "jup_b9_blackbox",
        "visual": r"dynamics\equipments\quest\box_black.ogf",
        "mesh_rel_posix": "dynamics/equipments/quest/box_black.ogf",
        "kind": "i_quest",
        "class": "II_ATTCH",
        "inv_grid_width": 2,
        "inv_grid_height": 2,
        "inv_grid_x": 2,
        "inv_grid_y": 11,
        "default_weight": 3.0,
        "default_cost": 500,
        "label_de": "Flugschreiber / Blackbox (box_black, 2x2 Grid)",
        "label_en": "Flight Recorder / Blackbox (box_black, 2x2 Grid)",
        "label_ru": "Бортовой самописец / Чёрный ящик (box_black, 2x2)",
        "descr_de": "Gepanzerter Flugschreiber und Telemetrie-Datenspeicher aus einem abgestürzten Helikopter oder Konvoi.",
        "descr_en": "Armored flight recorder and telemetry data unit recovered from a crashed helicopter or convoy.",
        "descr_ru": "Бронированный бортовой самописец и блок телеметрии с разбившегося вертолёта или конвоя.",
    },
    {
        "id": "box_toolkit_3",
        "template_id": "box_toolkit_3",
        "parent_section": "tch_quest",
        "vanilla_reference_section": "quest_package_1",
        "visual": r"dynamics\equipments\quest\box_toolkit_3.ogf",
        "mesh_rel_posix": "dynamics/equipments/quest/box_toolkit_3.ogf",
        "kind": "i_quest",
        "class": "II_ATTCH",
        "inv_grid_width": 2,
        "inv_grid_height": 2,
        "inv_grid_x": 0,
        "inv_grid_y": 77,
        "default_weight": 5.42,
        "default_cost": 0,
        "label_de": "Schweres Technik-/Werkzeugpaket (box_toolkit_3, 2x2 Grid)",
        "label_en": "Heavy Technical / Toolkit Package (box_toolkit_3, 2x2 Grid)",
        "label_ru": "Тяжёлый технический / инструментальный ящик (box_toolkit_3, 2x2)",
        "descr_de": "Robuste Nachschub- und Werkzeugkiste für Techniker, Kalibrierungsgeräte oder Spezialbauteile.",
        "descr_en": "Heavy-duty supply and toolkit crate containing calibration instruments or specialized components.",
        "descr_ru": "Прочный технический ящик с калибровочными приборами и специальными деталями.",
    },
    {
        "id": "notes_writing_book_2",
        "template_id": "notes_writing_book_2",
        "parent_section": "tch_quest",
        "vanilla_reference_section": "drx_sl_quest_item_1",
        "visual": r"dynamics\equipments\quest\notes_writing_book_2.ogf",
        "mesh_rel_posix": "dynamics/equipments/quest/notes_writing_book_2.ogf",
        "kind": "i_quest",
        "class": "II_ATTCH",
        "inv_grid_width": 2,
        "inv_grid_height": 1,
        "inv_grid_x": 12,
        "inv_grid_y": 15,
        "default_weight": 0.05,
        "default_cost": 0,
        "label_de": "Geheimes Feldtagebuch / Dokumente (notes_writing_book_2, 2x1 Grid)",
        "label_en": "Classified Field Journal / Documents (notes_writing_book_2, 2x1 Grid)",
        "label_ru": "Секретный полевой дневник / Документы (notes_writing_book_2, 2x1)",
        "descr_de": "Handschriftliches Feldtagebuch und Einsatzprotokoll mit Koordinaten, Frequenzcodes und Labornotizen.",
        "descr_en": "Handwritten field journal and operational logbook with coordinates, frequency codes, and lab notes.",
        "descr_ru": "Рукописный полевой журнал с координатами, кодами частот и лабораторными записями.",
    },
    {
        "id": "item_merger",
        "template_id": "item_merger",
        "parent_section": "tch_quest",
        "vanilla_reference_section": "main_story_1_quest_case",
        "visual": r"equipments\item_merger.ogf",
        "mesh_rel_posix": "equipments/item_merger.ogf",
        "kind": "i_quest",
        "class": "II_ATTCH",
        "inv_grid_width": 2,
        "inv_grid_height": 2,
        "inv_grid_x": 2,
        "inv_grid_y": 16,
        "default_weight": 2.5,
        "default_cost": 1000,
        "label_de": "Verschlüsselter Hauptstory-Spezialkoffer (item_merger, 2x2 Grid)",
        "label_en": "Encrypted Main-Story Special Briefcase (item_merger, 2x2 Grid)",
        "label_ru": "Зашифрованный спецкейс сюжетной линии (item_merger, 2x2)",
        "descr_de": "Verschlüsselter diplomatischer Spezialkoffer der Hauptstory mit biometrischer Verriegelung.",
        "descr_en": "Encrypted main-story special briefcase protected by a biometric security lock.",
        "descr_ru": "Зашифрованный специальный кейс основной сюжетной линии с биометрическим замком.",
    },
]


def _sanitize_section_id(raw_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", (raw_id or "").strip()).strip("_").lower()
    if not cleaned:
        cleaned = "custom_quest_item"
    if cleaned[0].isdigit():
        cleaned = f"q_{cleaned}"
    return cleaned


def _load_stored_items() -> list:
    for path in (CUSTOM_QUEST_ITEMS_PATH, MIRROR_QUEST_ITEMS_PATH):
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("items"), list):
                    return data["items"]
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    return []


def _save_stored_items(items: list) -> str:
    TOOLS_RE_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    MAIN_RE_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    CUSTOM_QUEST_ITEMS_PATH.write_text(serialized, encoding="utf-8")
    try:
        MIRROR_QUEST_ITEMS_PATH.write_text(serialized, encoding="utf-8")
    except Exception:
        pass
    return str(CUSTOM_QUEST_ITEMS_PATH)


def get_vanilla_quest_item_templates() -> dict:
    """
    Returns curated 100% Base-Anomaly-compatible quest item templates (:tch_quest)
    with live mesh existence verification under tools/_unpacked/meshes/.
    Accessible via res["templates"], res["by_id"][tid], or directly via res[tid].
    """
    templates = []
    by_id = {}
    for tpl in VANILLA_QUEST_ITEM_TEMPLATES:
        entry = dict(tpl)
        src_path = UNPACKED_MESHES_DIR / entry["mesh_rel_posix"]
        entry["mesh_source_path"] = str(src_path)
        entry["mesh_exists"] = src_path.is_file()
        entry["mesh_size_bytes"] = src_path.stat().st_size if src_path.is_file() else 0
        entry["grid_size"] = f"{entry['inv_grid_width']}x{entry['inv_grid_height']}"
        templates.append(entry)
        by_id[entry["id"]] = entry

    result = {
        "ok": True,
        "count": len(templates),
        "parent_section": "tch_quest",
        "meshes_root": str(UNPACKED_MESHES_DIR),
        "templates": templates,
        "by_id": by_id,
    }
    # Also expose top-level template keys for direct dict lookup (res["safe_container"], etc.)
    for tid, entry in by_id.items():
        result[tid] = entry
    return result


def _render_item_ltx_block(item: dict) -> str:
    sec = item["section_id"]
    parent = item.get("parent_section", "tch_quest")
    quest_flag = "true" if item.get("quest_item", True) else "false"
    trade_flag = "true" if item.get("can_trade", False) else "false"
    lines = [
        f"; --- Custom Quest Item: {item.get('name_en') or sec} (Template: {item.get('template_id')}) ---",
        f"[{sec}]:{parent}",
        f'$spawn                                   = "quest_items\\{sec}"',
        f"kind                                     = {item.get('kind', 'i_quest')}",
        f"visual                                   = {item['visual']}",
        f"story_id                                 = {item.get('story_id', sec)}",
        f"quest_item                               = {quest_flag}",
        f"can_trade                                = {trade_flag}",
        f"inv_weight                               = {float(item.get('weight', 1.0)):.2f}",
        f"cost                                     = {int(item.get('cost', 0))}",
        f"inv_grid_width                           = {int(item['inv_grid_width'])}",
        f"inv_grid_height                          = {int(item['inv_grid_height'])}",
        f"inv_grid_x                               = {int(item['inv_grid_x'])}",
        f"inv_grid_y                               = {int(item['inv_grid_y'])}",
        f"inv_name                                 = {item['inv_name']}",
        f"inv_name_short                           = {item['inv_name_short']}",
        f"description                              = {item['description']}",
    ]
    return "\n".join(lines)


def _render_item_dltx_block(item: dict) -> str:
    sec = item["section_id"]
    parent = item.get("parent_section", "tch_quest")
    quest_flag = "true" if item.get("quest_item", True) else "false"
    trade_flag = "true" if item.get("can_trade", False) else "false"
    lines = [
        f"; --- DLTX Override/Autoload for [{sec}] ---",
        f"![{sec}]",
        f"@[{sec}]:{parent}",
        f'$spawn                                   = "quest_items\\{sec}"',
        f"kind                                     = {item.get('kind', 'i_quest')}",
        f"visual                                   = {item['visual']}",
        f"story_id                                 = {item.get('story_id', sec)}",
        f"quest_item                               = {quest_flag}",
        f"can_trade                                = {trade_flag}",
        f"inv_weight                               = {float(item.get('weight', 1.0)):.2f}",
        f"cost                                     = {int(item.get('cost', 0))}",
        f"inv_grid_width                           = {int(item['inv_grid_width'])}",
        f"inv_grid_height                          = {int(item['inv_grid_height'])}",
        f"inv_grid_x                               = {int(item['inv_grid_x'])}",
        f"inv_grid_y                               = {int(item['inv_grid_y'])}",
        f"inv_name                                 = {item['inv_name']}",
        f"inv_name_short                           = {item['inv_name_short']}",
        f"description                              = {item['description']}",
    ]
    return "\n".join(lines)


def _render_item_string_xml(item: dict, lang: str = "eng") -> str:
    if lang == "rus":
        title = item.get("name_ru") or item.get("name_en") or item["section_id"]
        descr = item.get("descr_ru") or item.get("descr_en") or ""
    elif lang == "ger" or lang == "de":
        title = item.get("name_de") or item.get("name_en") or item["section_id"]
        descr = item.get("descr_de") or item.get("descr_en") or ""
    else:
        title = item.get("name_en") or item.get("name_de") or item["section_id"]
        descr = item.get("descr_en") or item.get("descr_de") or ""
    return (
        f'  <string id="{item["inv_name"]}">\n'
        f"    <text>{xml_escape(str(title))}</text>\n"
        f"  </string>\n"
        f'  <string id="{item["description"]}">\n'
        f"    <text>{xml_escape(str(descr))}</text>\n"
        f"  </string>"
    )


def clone_quest_item_to_ltx(payload: dict) -> dict:
    """
    Clones a custom quest item from one of the 5 verified Base-Anomaly templates (:tch_quest),
    generates its LTX block, DLTX block, and string-table XML snippets, persists it in
    tools/_re_index/custom_quest_items.json, and optionally bundles into gamedata_dir.
    """
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload must be a dict"}

    raw_sec = payload.get("section_id") or payload.get("id") or payload.get("section") or ""
    section_id = _sanitize_section_id(raw_sec)
    if not section_id:
        return {"ok": False, "error": "section_id is required"}

    templates_info = get_vanilla_quest_item_templates()
    by_id = templates_info["by_id"]
    template_id = (payload.get("template_id") or payload.get("template") or "safe_container").strip()
    if template_id == "pda_quest":
        template_id = "safe_container"
    if template_id not in by_id:
        return {
            "ok": False,
            "error": f"Unknown template_id '{template_id}'. Valid templates: {list(by_id.keys())}",
        }

    tpl = by_id[template_id]

    name_en = (
        payload.get("name_en")
        or payload.get("title_en")
        or payload.get("title")
        or payload.get("name")
        or tpl["label_en"]
    )
    name_de = payload.get("name_de") or payload.get("title_de") or name_en
    name_ru = payload.get("name_ru") or payload.get("title_ru") or name_en

    descr_en = (
        payload.get("descr_en")
        or payload.get("description_en")
        or payload.get("description")
        or payload.get("descr")
        or tpl["descr_en"]
    )
    descr_de = payload.get("descr_de") or payload.get("description_de") or descr_en
    descr_ru = payload.get("descr_ru") or payload.get("description_ru") or descr_en

    weight = float(payload.get("weight", payload.get("inv_weight", tpl["default_weight"])))
    cost = int(payload.get("cost", tpl["default_cost"]))
    inv_grid_width = int(payload.get("inv_grid_width", tpl["inv_grid_width"]))
    inv_grid_height = int(payload.get("inv_grid_height", tpl["inv_grid_height"]))
    inv_grid_x = int(payload.get("inv_grid_x", tpl["inv_grid_x"]))
    inv_grid_y = int(payload.get("inv_grid_y", tpl["inv_grid_y"]))

    story_id = _sanitize_section_id(payload.get("story_id") or section_id)
    quest_item = bool(payload.get("quest_item", True))
    can_trade = bool(payload.get("can_trade", False))

    inv_name = payload.get("inv_name") or f"st_{section_id}_name"
    inv_name_short = payload.get("inv_name_short") or inv_name
    description_id = payload.get("description_id") or f"st_{section_id}_descr"

    item_record = {
        "section_id": section_id,
        "template_id": template_id,
        "parent_section": payload.get("parent_section") or tpl["parent_section"],
        "visual": tpl["visual"],
        "mesh_rel_posix": tpl["mesh_rel_posix"],
        "mesh_source_path": tpl["mesh_source_path"],
        "mesh_exists": tpl["mesh_exists"],
        "kind": tpl.get("kind", "i_quest"),
        "story_id": story_id,
        "quest_item": quest_item,
        "can_trade": can_trade,
        "weight": round(weight, 3),
        "cost": cost,
        "inv_grid_width": inv_grid_width,
        "inv_grid_height": inv_grid_height,
        "inv_grid_x": inv_grid_x,
        "inv_grid_y": inv_grid_y,
        "inv_name": inv_name,
        "inv_name_short": inv_name_short,
        "description": description_id,
        "name_en": str(name_en),
        "name_de": str(name_de),
        "name_ru": str(name_ru),
        "descr_en": str(descr_en),
        "descr_de": str(descr_de),
        "descr_ru": str(descr_ru),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    ltx_block = _render_item_ltx_block(item_record)
    dltx_block = _render_item_dltx_block(item_record)
    xml_snippet_en = _render_item_string_xml(item_record, "eng")
    xml_snippet_ru = _render_item_string_xml(item_record, "rus")

    item_record["ltx_block"] = ltx_block
    item_record["dltx_block"] = dltx_block
    item_record["string_xml_en"] = xml_snippet_en
    item_record["string_xml_ru"] = xml_snippet_ru

    items = _load_stored_items()
    replaced = False
    for idx, existing in enumerate(items):
        if existing.get("section_id") == section_id:
            items[idx] = item_record
            replaced = True
            break
    if not replaced:
        items.append(item_record)

    index_path = _save_stored_items(items)

    bundle_result = None
    gamedata_dir = payload.get("gamedata_dir")
    if gamedata_dir:
        bundle_result = bundle_quest_items_into_gamedata(gamedata_dir, items=items)

    return {
        "ok": True,
        "section_id": section_id,
        "template_id": template_id,
        "parent_section": item_record["parent_section"],
        "visual": item_record["visual"],
        "mesh_exists": item_record["mesh_exists"],
        "replaced": replaced,
        "item": item_record,
        "ltx_block": ltx_block,
        "dltx_block": dltx_block,
        "string_xml_en": xml_snippet_en,
        "string_xml_ru": xml_snippet_ru,
        "index_path": index_path,
        "total_custom_items": len(items),
        "bundle": bundle_result,
    }


def bundle_quest_items_into_gamedata(gamedata_dir, items: list = None) -> dict:
    """
    Writes all cloned quest items into:
      1. <gamedata_dir>/configs/items/items/items_studio_custom.ltx
      2. <gamedata_dir>/configs/mod_system_studio_quest_items.ltx (DLTX autoload)
    And copies each item's .ogf mesh from tools/_unpacked/meshes/<mesh_rel_posix>
    to <gamedata_dir>/meshes/<mesh_rel_posix> to guarantee 100% crash-free loading in Base Anomaly 1.5.3.
    """
    gd_path = Path(gamedata_dir).resolve()
    if items is None:
        items = _load_stored_items()

    ltx_dir = gd_path / "configs" / "items" / "items"
    dltx_dir = gd_path / "configs"
    ltx_dir.mkdir(parents=True, exist_ok=True)
    dltx_dir.mkdir(parents=True, exist_ok=True)

    ltx_path = ltx_dir / "items_studio_custom.ltx"
    dltx_path = dltx_dir / "mod_system_studio_quest_items.ltx"

    header_comment = [
        "; =============================================================================",
        "; Anomaly 1.5.3 Studio — Custom Quest Items (Auto-Generated)",
        "; All items inherit from [tch_quest] and bundle their .ogf meshes in gamedata/meshes/",
        "; =============================================================================",
        "",
    ]

    ltx_sections = list(header_comment)
    dltx_sections = list(header_comment)
    copied_meshes = []
    missing_meshes = []

    for item in items:
        ltx_sections.append(item.get("ltx_block") or _render_item_ltx_block(item))
        ltx_sections.append("")
        dltx_sections.append(item.get("dltx_block") or _render_item_dltx_block(item))
        dltx_sections.append("")

        mesh_rel = (item.get("mesh_rel_posix") or item.get("visual", "")).replace("\\", "/").lstrip("/")
        if mesh_rel:
            src_mesh = UNPACKED_MESHES_DIR / mesh_rel
            dst_mesh = gd_path / "meshes" / mesh_rel
            if src_mesh.is_file():
                dst_mesh.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_mesh, dst_mesh)
                copied_meshes.append({
                    "section_id": item.get("section_id"),
                    "mesh_rel": mesh_rel,
                    "source": str(src_mesh),
                    "destination": str(dst_mesh),
                    "bytes": dst_mesh.stat().st_size,
                })
            else:
                missing_meshes.append({
                    "section_id": item.get("section_id"),
                    "mesh_rel": mesh_rel,
                    "expected_source": str(src_mesh),
                })

    ltx_content = "\n".join(ltx_sections)
    dltx_content = "\n".join(dltx_sections)

    ltx_path.write_bytes(ltx_content.encode("cp1251", "replace"))
    dltx_path.write_bytes(dltx_content.encode("cp1251", "replace"))

    return {
        "ok": len(missing_meshes) == 0,
        "gamedata_dir": str(gd_path),
        "ltx_path": str(ltx_path),
        "dltx_path": str(dltx_path),
        "item_count": len(items),
        "copied_meshes": copied_meshes,
        "missing_meshes": missing_meshes,
        "items": items,
    }


def list_custom_quest_items() -> dict:
    """Returns all saved custom quest items and available vanilla templates."""
    items = _load_stored_items()
    return {
        "ok": True,
        "count": len(items),
        "index_path": str(CUSTOM_QUEST_ITEMS_PATH),
        "items": items,
        "templates": get_vanilla_quest_item_templates()["templates"],
    }


def delete_custom_quest_item(section_id: str) -> dict:
    """Deletes a custom quest item by section_id from custom_quest_items.json."""
    target = _sanitize_section_id(section_id)
    items = _load_stored_items()
    filtered = [it for it in items if it.get("section_id") != target]
    removed = len(items) - len(filtered)
    index_path = _save_stored_items(filtered)
    return {
        "ok": True,
        "deleted": removed > 0,
        "removed_count": removed,
        "section_id": target,
        "remaining_count": len(filtered),
        "index_path": index_path,
    }
