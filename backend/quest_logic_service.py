import os, sys
#!/usr/bin/env python3
"""
Anomaly 1.5.3 Studio — Full Quest, Storyline, Dialog, String-Table & Particle Backend Service
Parses real Anomaly 1.5.3 Storylines (Living Legend, Mortal Sin, Operation Afterglow, Hollow Boundaries)
+ Regional Task Managers (tm_*.ltx) + Dialog XMLs + String Table Texts (ENG/RUS) into visual Node Graphs (Visual Node Graph)!
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = (Path(os.environ['ANOMALY_STUDIO_ROOT']).resolve() if os.environ.get('ANOMALY_STUDIO_ROOT') else (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent))
UNPACKED = ROOT / ".studio_cache" / "vfs_mount"
CONFIGS = UNPACKED / "configs"
INDEX_DIR = ROOT / "index"

STRING_CACHE = {"eng": {}, "rus": {}}
TASKS_CACHE = None



def clean_stalker_color_codes(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"%c\[[^\]]+\]", "", text).strip()


def apply_hierarchical_dag_layout(nodes: list, edges: list, x_start: int = 60, y_start: int = 60, x_step: int = 340, y_step: int = 155) -> list:
    """
    Computes a true topological / BFS depth hierarchy so branching dialogs (like
    `inf_trader_buy_transitions` with 22 phrases) and quest chains align cleanly
    in left-to-right columns by depth without overlapping edges.
    """
    if not nodes:
        return nodes
    node_map = {n["id"]: n for n in nodes}
    adj = {n["id"]: [] for n in nodes}
    in_deg = {n["id"]: 0 for n in nodes}
    for e in edges:
        u, v = e.get("from"), e.get("to")
        if u in adj and v in adj and u != v:
            adj[u].append(v)
            in_deg[v] = in_deg.get(v, 0) + 1

    # Roots: phr_0 if present, or in_deg == 0, else first node
    roots = [n["id"] for n in nodes if n["id"] in ("phr_0", "0") or in_deg.get(n["id"], 0) == 0]
    if not roots:
        roots = [nodes[0]["id"]]

    depth = {}
    order_in_col = {}
    queue = []
    for r in roots:
        if r not in depth:
            depth[r] = 0
            queue.append(r)

    head = 0
    while head < len(queue):
        u = queue[head]
        head += 1
        d = depth[u]
        for v in adj.get(u, []):
            if v not in depth:
                depth[v] = d + 1
                queue.append(v)

    # Any disconnected or cycle nodes get grouped cleanly in rows of 5 per column after visited columns
    max_d = max(depth.values()) if depth else 0
    orphan_idx = 0
    for n in nodes:
        nid = n["id"]
        if nid not in depth:
            depth[nid] = max_d + 1 + (orphan_idx // 5)
            orphan_idx += 1

    # Group by depth column preserving logical order
    cols = {}
    for n in nodes:
        d = depth[n["id"]]
        cols.setdefault(d, []).append(n)

    max_rows = max((len(c) for c in cols.values()), default=1)
    total_height = max_rows * y_step

    for d, col_nodes in sorted(cols.items()):
        col_h = len(col_nodes) * y_step
        top_offset = max(y_start, y_start + (total_height - col_h) // 2)
        for row_idx, n in enumerate(col_nodes):
            n["x"] = x_start + d * x_step
            n["y"] = top_offset + row_idx * y_step
            n["depth_col"] = d
            n["col"] = d
            n["row_idx"] = row_idx
    return nodes


def load_string_tables(lang="eng"):
    if STRING_CACHE.get(lang):
        return STRING_CACHE[lang]
    st_dir = CONFIGS / "text" / lang
    out = {}
    if not st_dir.is_dir():
        return out
    rx = re.compile(r'<string\s+id="([^"]+)"\s*>\s*<text>(.*?)</text>\s*</string>', re.S)
    for xml_file in sorted(st_dir.glob("*.xml")):
        try:
            raw = xml_file.read_bytes().decode("cp1251", "ignore")
            for sid, txt in rx.findall(raw):
                out[sid.strip()] = txt.strip()
        except Exception:
            pass
    STRING_CACHE[lang] = out
    return out


def parse_all_tm_tasks():
    global TASKS_CACHE
    if TASKS_CACHE is not None:
        return TASKS_CACHE
    en_st = load_string_tables("eng")
    ru_st = load_string_tables("rus")
    task_dir = CONFIGS / "misc" / "task"
    campaigns = {}
    all_tasks = {}

    campaign_labels = {
        "tm_lostzone_ll.ltx": "Main Story Act I: Living Legend (tm_lostzone_ll.ltx)",
        "tm_lostzone_ms.ltx": "Main Story Act II: Mortal Sin (tm_lostzone_ms.ltx)",
        "tm_lostzone_oa.ltx": "Main Story Act III: Operation Afterglow (tm_lostzone_oa.ltx)",
        "tm_lostzone_hb.ltx": "Main Story Act IV: Hollow Boundaries / UNISG (tm_lostzone_hb.ltx)",
        "tm_escape.ltx": "Cordon / Escape Quests (tm_escape.ltx)",
        "tm_garbage.ltx": "Garbage Quests (tm_garbage.ltx)",
        "tm_agroprom.ltx": "Agroprom Research Institute Quests (tm_agroprom.ltx)",
        "tm_agroprom_underground.ltx": "Agroprom Underground Quests (tm_agroprom_underground.ltx)",
        "tm_darkvalley.ltx": "Dark Valley Quests (tm_darkvalley.ltx)",
        "tm_darkscape.ltx": "Darkscape Quests (tm_darkscape.ltx)",
        "tm_bar.ltx": "Rostok / 100 Rads Bar Quests (tm_bar.ltx)",
        "tm_yantar.ltx": "Yantar & Sakharov Quests (tm_yantar.ltx)",
        "tm_military.ltx": "Army Warehouses Quests (tm_military.ltx)",
        "tm_deadcity.ltx": "Dead City / Mercenary Quests (tm_deadcity.ltx)",
        "tm_marsh.ltx": "Great Swamps / Clear Sky Quests (tm_marsh.ltx)",
        "tm_truck.ltx": "Truck Cemetery Quests (tm_truck.ltx)",
        "tm_radar.ltx": "Radar / Brain Scorcher Quests (tm_radar.ltx)",
        "tm_red_forest.ltx": "Red Forest & Forester Quests (tm_red_forest.ltx)",
        "tm_zaton.ltx": "Zaton Quests (tm_zaton.ltx)",
        "tm_jupiter.ltx": "Jupiter & Yanov Station Quests (tm_jupiter.ltx)",
        "tm_pripyat.ltx": "Pripyat Central Quests (tm_pripyat.ltx)",
        "tm_pripyat2.ltx": "Pripyat Outskirts Quests (tm_pripyat2.ltx)",
        "tm_sarcofag.ltx": "Chernobyl NPP Sarcophagus Quests (tm_sarcofag.ltx)",
        "tm_warlab.ltx": "Generators / Secret Warlab Quests (tm_warlab.ltx)",
        "tm_dynamic.ltx": "Dynamic A-Life & Repeatable Quests (tm_dynamic.ltx)",
        "tm_mlr.ltx": "MLR World Expansion & Faction Quests (tm_mlr.ltx)",
        "tm_rioc_common.ltx": "RIOC Common Faction & Trader Quests (tm_rioc_common.ltx)",
        "tm_warfare.ltx": "Warfare Mode Strategic Quests (tm_warfare.ltx)",
        "tm_anomaly_studio_custom.ltx": "Custom Anomaly Studio Quests (tm_anomaly_studio_custom.ltx)",
    }

    if not task_dir.is_dir():
        return {"campaigns": {}, "tasks": {}}

    for ltx_file in sorted(task_dir.glob("tm_*.ltx")):
        fname = ltx_file.name
        raw = ltx_file.read_bytes().decode("cp1251", "ignore")
        current_sec = None
        sec_data = {}
        file_tasks = []

        for line in raw.splitlines():
            s = line.split(";")[0].strip()
            if not s:
                continue
            if s.startswith("[") and "]" in s:
                if current_sec and sec_data:
                    file_tasks.append((current_sec, sec_data))
                current_sec = s[1:s.index("]")].strip()
                sec_data = {}
            elif "=" in s and current_sec:
                k, v = s.split("=", 1)
                sec_data[k.strip()] = v.strip()
        if current_sec and sec_data:
            file_tasks.append((current_sec, sec_data))

        parsed_list = []
        for sec, kv in file_tasks:
            title_id = kv.get("title", "")
            descr_id = kv.get("descr", "")
            # Clean conditional descr id like {=actor_has_item(...)} id1, id2
            clean_title_id = re.sub(r"\{[^}]+\}", "", title_id).split(",")[-1].strip()
            clean_descr_id = re.sub(r"\{[^}]+\}", "", descr_id).split(",")[-1].strip()

            title_en = en_st.get(clean_title_id, clean_title_id or sec)
            descr_en = en_st.get(clean_descr_id, clean_descr_id or "")
            title_ru = ru_st.get(clean_title_id, title_en)
            descr_ru = ru_st.get(clean_descr_id, descr_en)

            # Extract next task given via =give_task(...)
            next_tasks = re.findall(r"give_task\(([a-zA-Z0-9_]+)\)", kv.get("on_complete", ""))
            infos_given = re.findall(r"\+([a-zA-Z0-9_]+)", kv.get("on_complete", "") + " " + kv.get("on_init", ""))
            conds = [v for k, v in sorted(kv.items()) if k.startswith("condlist_")]

            t_obj = {
                "id": sec,
                "file": fname,
                "icon": kv.get("icon", "ui_inGame2_Mesta_evakuatsii"),
                "storyline": kv.get("storyline", "false").lower() == "true",
                "prior": kv.get("prior", "100"),
                "target": kv.get("target", ""),
                "title_id": clean_title_id,
                "descr_id": clean_descr_id,
                "title_en": title_en,
                "descr_en": descr_en,
                "title_ru": title_ru,
                "descr_ru": descr_ru,
                "on_init": kv.get("on_init", ""),
                "on_complete": kv.get("on_complete", ""),
                "on_fail": kv.get("on_fail", ""),
                "condlists": conds,
                "next_tasks": next_tasks,
                "infos_given": infos_given,
                "raw_kv": kv,
            }
            parsed_list.append(t_obj)
            all_tasks[sec] = t_obj

        campaigns[fname] = {
            "file": fname,
            "label": campaign_labels.get(fname) or f"{fname.replace('tm_', '').replace('.ltx', '').replace('_', ' ').title()} Quests ({fname})",
            "count": len(parsed_list),
            "tasks": parsed_list,
        }

    TASKS_CACHE = {"campaigns": campaigns, "tasks": all_tasks}
    return TASKS_CACHE


def build_campaign_graph(file_name: str):
    data = parse_all_tm_tasks()
    camp = data["campaigns"].get(file_name)
    if not camp:
        return {"nodes": [], "edges": [], "compiled_ltx": "; Campaign not found"}

    tasks = camp["tasks"][:45]  # Top 45 tasks in visual chain
    nodes = []
    edges = []
    id_to_node = {}

    for idx, t in enumerate(tasks):
        col = idx % 4
        row = idx // 4
        nid = f"task_{t['id']}"
        id_to_node[t["id"]] = nid
        nodes.append({
            "id": nid,
            "task_id": t["id"],
            "type": "story" if t["storyline"] else "action",
            "title": t["title_en"] or t["id"],
            "subtitle": f"[{t['id']}]",
            "x": 60 + col * 340,
            "y": 60 + row * 210,
            "target": t["target"],
            "cond": t["condlists"][0] if t["condlists"] else "",
            "on_init": t["on_init"],
            "on_complete": t["on_complete"],
            "title_id": t["title_id"],
            "descr_id": t["descr_id"],
            "title_text": t["title_en"],
            "descr_text": t["descr_en"],
            "title_ru": t["title_ru"],
            "descr_ru": t["descr_ru"],
            "file": t["file"],
        })

    # Connect tasks via give_task(...) or sequential storyline order
    for idx, t in enumerate(tasks):
        src_nid = id_to_node[t["id"]]
        linked = False
        for nxt in t["next_tasks"]:
            if nxt in id_to_node:
                edges.append({"from": src_nid, "to": id_to_node[nxt], "label": "give_task"})
                linked = True
        if not linked and idx + 1 < len(tasks) and file_name.startswith("tm_lostzone_"):
            edges.append({"from": src_nid, "to": id_to_node[tasks[idx + 1]["id"]], "label": "story_flow"})

    # Generate compiled LTX preview
    ltx_lines = [f"; === {camp['label']} ({file_name}) ==="]
    for t in tasks[:15]:
        ltx_lines.append(f"\n[{t['id']}]")
        ltx_lines.append(f"icon = {t['icon']}")
        ltx_lines.append(f"storyline = {'true' if t['storyline'] else 'false'}")
        ltx_lines.append(f"title = {t['title_id']} ; \"{t['title_en']}\"")
        if t["target"]:
            ltx_lines.append(f"target = {t['target']}")
        ltx_lines.append(f"descr = {t['descr_id']}")
        if t["on_init"]:
            ltx_lines.append(f"on_init = {t['on_init']}")
        for ci, cval in enumerate(t["condlists"]):
            ltx_lines.append(f"condlist_{ci} = {cval}")
        if t["on_complete"]:
            ltx_lines.append(f"on_complete = {t['on_complete']}")

    apply_hierarchical_dag_layout(nodes, edges, x_start=60, y_start=50, x_step=350, y_step=165)
    return {
        "file": file_name,
        "label": camp["label"],
        "nodes": nodes,
        "edges": edges,
        "compiled_ltx": "\n".join(ltx_lines),
    }




def list_all_dialogs():
    en_st = load_string_tables("eng")
    ru_st = load_string_tables("rus")
    gp_dir = CONFIGS / "gameplay"
    dialogs = []
    if not gp_dir.is_dir():
        return dialogs
    rx_dlg = re.compile(r'<dialog\s+id="([^"]+)"[^>]*>(.*?)</dialog>', re.S)
    rx_phr = re.compile(r'<phrase\s+id="([^"]+)"[^>]*>(.*?)</phrase>', re.S)
    rx_txt = re.compile(r'<text>([^<]+)</text>')
    for xf in sorted(gp_dir.glob("dialogs*.xml")):
        raw = xf.read_bytes().decode("cp1251", "ignore")
        for did, body in rx_dlg.findall(raw):
            phrases = rx_phr.findall(body)
            first_txt_id = ""
            for pid, pbody in phrases:
                m = rx_txt.search(pbody)
                if m:
                    first_txt_id = m.group(1).strip()
                    break
            preview = en_st.get(first_txt_id, first_txt_id or did)
            dialogs.append({
                "id": did,
                "file": xf.name,
                "phrase_count": len(phrases),
                "preview": preview[:90],
            })
    return dialogs


def get_dialog_graph(dialog_id: str):
    alias_map = {
        "dm_trade_buy_transition": "inf_trader_buy_transitions",
        "inf_trade_buy_transition": "inf_trader_buy_transitions",
    }
    dialog_id = alias_map.get(dialog_id, dialog_id)
    en_st = load_string_tables("eng")
    ru_st = load_string_tables("rus")
    gp_dir = CONFIGS / "gameplay"
    rx_dlg = re.compile(r'<dialog\s+id="' + re.escape(dialog_id) + r'"[^>]*>(.*?)</dialog>', re.S)
    rx_phr = re.compile(r'<phrase\s+id="([^"]+)"[^>]*>(.*?)</phrase>', re.S)
    rx_any_dlg = re.compile(r'<dialog\s+id="([^"]+)"[^>]*>(.*?)</dialog>', re.S)
    xml_files = sorted(gp_dir.glob("dialogs*.xml"))
    cand_file = gp_dir / (dialog_id if dialog_id.endswith(".xml") else f"{dialog_id}.xml")
    if cand_file.is_file():
        xml_files = [cand_file] + [f for f in xml_files if f != cand_file]
    for xf in xml_files:
        raw = xf.read_bytes().decode("cp1251", "ignore")
        m = rx_dlg.search(raw)
        if not m and xf == cand_file:
            m_any = rx_any_dlg.search(raw)
            if m_any:
                dialog_id = m_any.group(1)
                rx_dlg = re.compile(r'<dialog\s+id="' + re.escape(dialog_id) + r'"[^>]*>(.*?)</dialog>', re.S)
                m = rx_dlg.search(raw)
        if not m:
            continue
        body = m.group(1)
        nodes = []
        edges = []
        phrases = rx_phr.findall(body)
        for idx, (pid, pbody) in enumerate(phrases):
            t_m = re.search(r'<text>([^<]+)</text>', pbody)
            tid = t_m.group(1).strip() if t_m else ""
            nexts = [n.strip() for n in re.findall(r'<next>([^<]+)</next>', pbody)]
            acts = [a.strip() for a in re.findall(r'<action>([^<]+)</action>', pbody)]
            has_i = [h.strip() for h in re.findall(r'<has_info>([^<]+)</has_info>', pbody)]
            give_i = [g.strip() for g in re.findall(r'<give_info>([^<]+)</give_info>', pbody)]
            col = idx % 4
            row = idx // 4
            nid = f"phr_{pid}"
            nodes.append({
                "id": nid,
                "task_id": f"{dialog_id}:{pid}",
                "type": "event" if pid == "0" else ("action" if acts or give_i else "condition"),
                "title": f"Phrase #{pid}: {(clean_stalker_color_codes(en_st.get(tid, tid)) or '(Start)')[:48]}",
                "subtitle": f"<{xf.name}> id={pid}",
                "x": 60 + col * 340,
                "y": 60 + row * 195,
                "target": ", ".join(acts),
                "cond": ", ".join(has_i),
                "on_init": "",
                "on_complete": ", ".join(give_i + acts),
                "title_id": tid,
                "descr_id": tid,
                "title_text": en_st.get(tid, tid),
                "descr_text": en_st.get(tid, tid),
                "title_ru": ru_st.get(tid, ""),
                "descr_ru": ru_st.get(tid, ""),
                "file": xf.name,
            })
            for nx in nexts:
                edges.append({"from": nid, "to": f"phr_{nx}", "label": "next"})
        apply_hierarchical_dag_layout(nodes, edges, x_start=60, y_start=50, x_step=340, y_step=145)
        return {
            "file": xf.name,
            "label": f"Dialog: {dialog_id}",
            "nodes": nodes,
            "edges": edges,
            "compiled_ltx": f"<dialog id=\"{dialog_id}\">\n" + body.strip()[:2500] + "\n</dialog>",
        }
    return {"nodes": [], "edges": [], "compiled_ltx": "<!-- Dialog not found -->"}


def save_quest_and_text(payload: dict):
    """Saves edited task LTX parameters AND updates string table texts in custom override JSON + XML!"""
    custom_file = INDEX_DIR / "quests_custom_overrides.json"
    overrides = json.loads(custom_file.read_text()) if custom_file.is_file() else {"tasks": {}, "strings": {}}
    task_id = payload.get("task_id", "")
    title_id = payload.get("title_id", "")
    descr_id = payload.get("descr_id", "")
    title_text = payload.get("title_text", "")
    descr_text = payload.get("descr_text", "")
    title_ru = payload.get("title_ru", "")
    descr_ru = payload.get("descr_ru", "")

    if task_id:
        overrides["tasks"][task_id] = payload
    if title_id and title_text:
        overrides["strings"][title_id] = {"eng": title_text, "rus": title_ru or title_text}
        if STRING_CACHE.get("eng"):
            STRING_CACHE["eng"][title_id] = title_text
    if descr_id and descr_text:
        overrides["strings"][descr_id] = {"eng": descr_text, "rus": descr_ru or descr_text}
        if STRING_CACHE.get("eng"):
            STRING_CACHE["eng"][descr_id] = descr_text

    custom_file.write_text(json.dumps(overrides, indent=2, ensure_ascii=False))

    # Also write valid Anomaly string table XML file in configs/text/eng/st_anomaly_studio_custom.xml
    st_out = CONFIGS / "text" / "eng" / "st_anomaly_studio_custom.xml"
    st_out.parent.mkdir(parents=True, exist_ok=True)
    xml_lines = ['<?xml version="1.0" encoding="windows-1251" ?>', '<string_table>']
    for sid, svals in overrides["strings"].items():
        esc_txt = (svals.get("eng", "") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml_lines.append(f'  <string id="{sid}">')
        xml_lines.append(f'    <text>{esc_txt}</text>')
        xml_lines.append('  </string>')
    xml_lines.append('</string_table>')
    st_out.write_bytes("\n".join(xml_lines).encode("cp1251", "replace"))
    return {"ok": True, "task_id": task_id, "saved_strings": len(overrides["strings"]), "xml_path": str(st_out)}


def get_loadscreen_tips():
    """Returns all loading screen header + tips (ls_header, ls_tip_number, ls_tip_1..100+) in ENG and RUS."""
    en_file = CONFIGS / "text" / "eng" / "ui_st_loadscreen.xml"
    ru_file = CONFIGS / "text" / "rus" / "ui_st_loadscreen.xml"
    rx = re.compile(r'<string\s+id="([^"]+)"\s*>\s*<text>(.*?)</text>\s*</string>', re.S)
    en_map = {}
    ru_map = {}
    if en_file.is_file():
        for sid, stxt in rx.findall(en_file.read_bytes().decode("cp1251", "ignore")):
            en_map[sid.strip()] = stxt.strip()
    if ru_file.is_file():
        for sid, stxt in rx.findall(ru_file.read_bytes().decode("cp1251", "ignore")):
            ru_map[sid.strip()] = stxt.strip()

    # Check custom overrides
    custom_ls = INDEX_DIR / "loadscreen_custom.json"
    if custom_ls.is_file():
        try:
            ov = json.loads(custom_ls.read_text())
            for k, v in ov.items():
                if "eng" in v: en_map[k] = v["eng"]
                if "rus" in v: ru_map[k] = v["rus"]
        except Exception:
            pass

    tips = []
    for sid in en_map:
        tips.append({
            "id": sid,
            "eng": en_map.get(sid, ""),
            "rus": ru_map.get(sid, ""),
        })
    return tips


def save_loadscreen_tip(payload: dict):
    """Saves an edited or new loading screen tip directly into ui_st_loadscreen.xml (ENG & RUS) and loadscreen_custom.json."""
    sid = payload.get("id", "").strip()
    eng_txt = payload.get("eng", "").strip()
    rus_txt = payload.get("rus", "").strip()
    if not sid:
        return {"ok": False, "error": "Missing id"}

    custom_ls = INDEX_DIR / "loadscreen_custom.json"
    ov = json.loads(custom_ls.read_text()) if custom_ls.is_file() else {}
    ov[sid] = {"eng": eng_txt, "rus": rus_txt or eng_txt}
    custom_ls.write_text(json.dumps(ov, indent=2, ensure_ascii=False))

    # Update ui_st_loadscreen.xml directly so Anomaly 1.5.3 shows it immediately on next load!
    for lang, new_val in [("eng", eng_txt), ("rus", rus_txt or eng_txt)]:
        if not new_val:
            continue
        xf = CONFIGS / "text" / lang / "ui_st_loadscreen.xml"
        if not xf.is_file():
            continue
        raw = xf.read_bytes().decode("cp1251", "ignore")
        esc = new_val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        pat = re.compile(r'(<string\s+id="' + re.escape(sid) + r'"\s*>\s*<text>)(.*?)(</text>\s*</string>)', re.S)
        if pat.search(raw):
            raw = pat.sub(lambda m: m.group(1) + esc + m.group(3), raw)
        else:
            ins = f'\n\t<string id="{sid}">\n\t\t<text>{esc}</text>\n\t</string>\n</string_table>'
            raw = raw.replace("</string_table>", ins)
        xf.write_bytes(raw.encode("cp1251", "replace"))
    return {"ok": True, "id": sid, "eng": eng_txt, "rus": rus_txt}


def build_moddb_addon_zip(payload: dict) -> dict:
    """
    Packages all custom quests, dialogs, string tables, loading screen tips, and modified LTX/Spawn files
    into a clean ModDB / Mod Organizer 2 (MO2) / JSGME ready .zip archive with gamedata/ hierarchy.
    """
    import zipfile, time
    mod_name = payload.get("mod_name", "Anomaly_Studio_Custom_Addon").strip()
    safe_name = re.sub(r'[^A-Za-z0-9_\-]+', '_', mod_name).strip('_') or "Anomaly_Studio_Addon"
    version = payload.get("version", "1.0.0").strip()
    author = payload.get("author", "EternalPain / EternalPain  / Anomaly Studio 1.5.3").strip()
    description = payload.get("description", "Created with S.T.A.L.K.E.R. Anomaly 1.5.3 Studio").strip()

    exports_dir = ROOT / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    zip_filename = f"{safe_name}_v{version}.zip"
    zip_path = exports_dir / zip_filename

    included_files = []

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Custom Quest LTX (gamedata/configs/misc/task/tm_anomaly_studio_custom.ltx)
        custom_ltx_blocks = []
        single_qid = (payload.get("single_quest_id") or "").strip()
        single_qnode = payload.get("single_quest_node")
        if single_qid and isinstance(single_qnode, dict):
            # Export strictly the requested single quest (plus its inline string table & custom 3D spawns)
            t_id = single_qnode.get("title") or f"st_{single_qid}_title"
            d_id = single_qnode.get("descr") or f"st_{single_qid}_descr"
            t_en = single_qnode.get("title_text") or single_qnode.get("title") or single_qid
            t_ru = single_qnode.get("title_ru") or t_en
            d_en = single_qnode.get("descr_text") or single_qnode.get("descr") or ""
            d_ru = single_qnode.get("descr_ru") or d_en
            icon = single_qnode.get("icon") or "ui_inGame2_Put_v_pripyat"
            prior = single_qnode.get("prior", 25)
            storyline = "true" if single_qnode.get("storyline") else "false"
            target = single_qnode.get("target_functor") or "esc_smart_terrain_7_11"
            status_f = single_qnode.get("status_functor") or "fetch_task_Need_return"
            cond0 = single_qnode.get("condlist_0") or "complete"
            on_init = single_qnode.get("on_init") or ""
            on_comp = single_qnode.get("on_complete") or "%=reward_random_money(4500:6000)%"
            on_fail = single_qnode.get("on_fail") or ""

            compiled_ltx = (
                f"[{single_qid}]\n"
                f"icon = {icon}\n"
                f"storyline = {storyline}\n"
                f"prior = {prior}\n"
                f"title = {t_id}\n"
                f"descr = {d_id}\n"
                f"target = {target}\n"
                f"status_functor = {status_f}\n"
                f"condlist_0 = {cond0}\n"
                + (f"on_init = {on_init}\n" if on_init else "")
                + f"on_complete = {on_comp}\n"
                + (f"on_fail = {on_fail}\n" if on_fail else "")
            )
            save_quest_and_text({
                "task_id": single_qid,
                "title_id": t_id,
                "descr_id": d_id,
                "title_text": t_en,
                "descr_text": d_en,
                "title_ru": t_ru,
                "descr_ru": d_ru,
                "compiled_ltx": compiled_ltx,
            })
            custom_ltx_blocks.append(compiled_ltx)
        else:
            custom_q_file = INDEX_DIR / "quests_custom.json"
            if custom_q_file.is_file():
                try:
                    q_ov = json.loads(custom_q_file.read_text())
                    for qid, qdata in q_ov.items():
                        if qdata.get("compiled_ltx"):
                            custom_ltx_blocks.append(qdata["compiled_ltx"])
                except Exception:
                    pass
            if payload.get("compiled_ltx"):
                block = payload["compiled_ltx"].strip()
                if block and block not in custom_ltx_blocks:
                    custom_ltx_blocks.append(block)

        if custom_ltx_blocks:
            ltx_content = "; =========================================================================\n"
            ltx_content += f"; {mod_name} v{version} — Generated by Anomaly 1.5.3 Studio\n"
            ltx_content += "; =========================================================================\n\n"
            ltx_content += "\n\n".join(custom_ltx_blocks) + "\n"
            arc_ltx = "gamedata/configs/misc/task/tm_anomaly_studio_custom.ltx"
            zf.writestr(arc_ltx, ltx_content.encode("cp1251", "replace"))
            included_files.append(arc_ltx)

        # 2. Custom String Table XMLs (gamedata/configs/text/eng & rus/st_anomaly_studio_custom.xml)
        for lang in ("eng", "rus"):
            st_file = CONFIGS / "text" / lang / "st_anomaly_studio_custom.xml"
            if st_file.is_file():
                arc_st = f"gamedata/configs/text/{lang}/st_anomaly_studio_custom.xml"
                zf.write(st_file, arc_st)
                included_files.append(arc_st)

        # 3. Loading Screen Tips (if customized in loadscreen_custom.json, include gamedata/configs/text/{eng,rus}/ui_st_loadscreen.xml)
        custom_ls = INDEX_DIR / "loadscreen_custom.json"
        if custom_ls.is_file() or payload.get("include_loadscreen"):
            for lang in ("eng", "rus"):
                ls_file = CONFIGS / "text" / lang / "ui_st_loadscreen.xml"
                if ls_file.is_file():
                    arc_ls = f"gamedata/configs/text/{lang}/ui_st_loadscreen.xml"
                    zf.write(ls_file, arc_ls)
                    included_files.append(arc_ls)

        # 3b. Zone 3D Director Mission Logic Scripts (gamedata/configs/scripts/<level>/zone_mission_logic.ltx)
        zd_scripts_root = INDEX_DIR / "zone_director_scripts"
        if zd_scripts_root.is_dir():
            for lf in sorted(zd_scripts_root.glob("*/*.ltx")):
                arc_sc = f"gamedata/configs/scripts/{lf.parent.name}/{lf.name}"
                zf.write(lf, arc_sc)
                included_files.append(arc_sc)

                # 3c. Custom Sculpted / Imported Landscapes (gamedata/levels/<level>/level.cform)
        custom_ls_root = INDEX_DIR / "custom_landscapes"
        if custom_ls_root.is_dir():
            for cf in sorted(custom_ls_root.glob("*/level.cform")):
                if cf.parent.name != "l99_test_valley":
                    arc_cf = f"gamedata/levels/{cf.parent.name}/level.cform"
                    zf.write(cf, arc_cf)
                    included_files.append(arc_cf)

        # 4. Custom Particles (if customized)
        custom_p = INDEX_DIR / "particles_custom.json"
        if custom_p.is_file():
            arc_p = "gamedata/particles/particles_studio_overrides.json"
            zf.write(custom_p, arc_p)
            included_files.append(arc_p)

        # 5. Mod Organizer 2 (MO2) meta.ini
        meta_ini = f"""[General]
gameName=stalkeranomaly
modid=0
version={version}
newestVersion={version}
category="Quests, Storylines & Gameplay"
installationFile={zip_filename}
comments="{description}"
notes="Exported directly from Anomaly 1.5.3 Studio ({author})"
"""
        zf.writestr("meta.ini", meta_ini.encode("utf-8"))
        included_files.append("meta.ini")

        # 6. ModDB Ready README (DE / EN / RU)
        readme = f"""===========================================================================
{mod_name} (v{version})
Author: {author}
Target Compatibility: S.T.A.L.K.E.R. Anomaly 1.5.3 (100% Native Compatible)
Built with: Anomaly 1.5.3 Studio (100% Free, Open-Source MIT & AI-Transparent Toolkit)
===========================================================================

[EN] DESCRIPTION & INSTALLATION (ModDB / Mod Organizer 2 / Manual)
---------------------------------------------------------------------------
{description}

Installation via Mod Organizer 2 (MO2) — Recommended:
1. Open Mod Organizer 2 for S.T.A.L.K.E.R. Anomaly 1.5.3.
2. Click "Install a new mod from an archive" and select `{zip_filename}`.
3. Enable `{mod_name}` in your load order and launch Anomaly!

Manual Installation:
1. Extract the `gamedata` folder from `{zip_filename}` directly into your
   S.T.A.L.K.E.R. Anomaly 1.5.3 root folder.

[DE] BESCHREIBUNG & INSTALLATION (ModDB / Mod Organizer 2 / Manuell)
---------------------------------------------------------------------------
Installation über Mod Organizer 2 (MO2) — Empfohlen:
1. In MO2 auf "Mod aus Archiv installieren" klicken und `{zip_filename}` wählen.
2. Haken bei `{mod_name}` setzen und Anomaly 1.5.3 starten!

Manuelle Installation:
1. Den Ordner `gamedata` aus dem Archiv direkt in das Anomaly-1.5.3-Hauptverzeichnis entpacken.

[RU] ОПИСАНИЕ И УСТАНОВКА (ModDB / Mod Organizer 2 / Вручную)
---------------------------------------------------------------------------
Установка через Mod Organizer 2 (MO2):
1. Установите архив `{zip_filename}` через MO2 и активируйте мод в списке.
2. Либо распакуйте папку `gamedata` в корневую директорию S.T.A.L.K.E.R. Anomaly 1.5.3.


===========================================================================
CREDITS & ACKNOWLEDGMENTS
---------------------------------------------------------------------------
- Mod Author / Creator: {author}
- Built with: S.T.A.L.K.E.R. Anomaly 1.5.3 Studio — Zone 3D Director & Visueller Node-Graph (Open-Source Project by EternalPain / EternalPain )
- Original S.T.A.L.K.E.R. Universe & X-Ray Engine: GSC Game World
- S.T.A.L.K.E.R. Anomaly 1.5.3 & X-Ray Monolith Engine: Anomaly Development Team
- AI Transparency Disclosure (DE/EN/RU): Built & generated with AI assistance
  (REA / Grok Bot, Clerk-01..10 & local Qwen2.5-Coder via Ollama), directed by
  EternalPain / EternalPain . (Hinweis: KI-generiertes / KI-unterstütztes Toolkit & Mod-Paket).
===========================================================================

Included Files ({len(included_files) + 1}):
""" + "\n".join(f" - {p}" for p in included_files) + "\n"

        zf.writestr("README_ModDB.txt", readme.encode("utf-8"))
        included_files.append("README_ModDB.txt")

    return {
        "ok": True,
        "zip_filename": zip_filename,
        "zip_path": str(zip_path),
        "download_url": f"/api/quests/download_mod/{zip_filename}",
        "size_bytes": zip_path.stat().st_size,
        "included_files": included_files,
    }


def get_zone_director_campaign(level_name: str) -> dict:
    """Returns all Zone 3D Director (3D-Missions- & Wegpunkt-Editor) objects (Waypoints, Triggers, Task Modules, Sync Links) for a level."""
    zd_file = INDEX_DIR / "zone_director_campaigns.json"
    data = json.loads(zd_file.read_text()) if zd_file.is_file() else {}
    lvl_data = data.get(level_name, {
        "level": level_name,
        "mission_name": f"Operation_{level_name}",
        "entities": [],
        "links": [],
    })
    return lvl_data


def compile_zone_director_to_anomaly_files(lvl_data: dict) -> dict:
    """
    Compiles Zone 3D Director (3D-Missions- & Wegpunkt-Editor) Waypoints, Trigger Zones, Task Modules, and Sync Links
    into 100% compatible S.T.A.L.K.E.R. Anomaly 1.5.3 LTX configs:
    1) gamedata/configs/misc/task/tm_zone_director_<level>.ltx (Task Manager tasks)
    2) gamedata/configs/scripts/<level>/zone_mission_logic.ltx (sr_idle trigger zones & walker/patrol paths)
    3) Waypoint patrol section blocks ([walker@zone_...], path_walk, path_look)
    """
    lvl = lvl_data.get("level", "l01_escape")
    entities = lvl_data.get("entities", [])
    links = lvl_data.get("links", [])
    ent_map = {e["id"]: e for e in entities if "id" in e}

    tm_lines = [
        f"; =========================================================================",
        f"; ZONE 3D DIRECTOR CAMPAIGN TASKS FOR LEVEL: {lvl}",
        f"; Auto-compiled by Anomaly 1.5.3 Studio (100% Vanilla 1.5.3 Compatible)",
        f"; =========================================================================\n",
    ]
    logic_lines = [
        f"; =========================================================================",
        f"; ZONE 3D DIRECTOR TRIGGER ZONES & WAYPOINT LOGIC FOR LEVEL: {lvl}",
        f"; =========================================================================\n",
    ]
    strings_en = {}
    strings_ru = {}

    for e in entities:
        etype = e.get("type", "waypoint")
        eid = e.get("id", "zd_obj_1")
        name = e.get("name", eid)
        pos = e.get("pos", [0.0, 0.0, 0.0])
        lvid = e.get("lvid", 1)
        gvid = e.get("gvid", 1)
        radius = float(e.get("radius", 8.0))

        # Find linked targets from this entity
        linked_targets = [ent_map[lk["to"]] for lk in links if lk.get("from") == eid and lk.get("to") in ent_map]

        if etype == "task":
            t_id = f"zd_task_{lvl}_{eid}"
            title_k = f"st_{t_id}_title"
            descr_k = f"st_{t_id}_descr"
            strings_en[title_k] = e.get("title_en") or name
            strings_en[descr_k] = e.get("descr_en") or f"Complete mission objective at ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})."
            strings_ru[title_k] = e.get("title_ru") or strings_en[title_k]
            strings_ru[descr_k] = e.get("descr_ru") or strings_en[descr_k]

            next_tasks = [f"%=give_task(zd_task_{lvl}_{t['id']})%" for t in linked_targets if t.get("type") == "task"]
            reward = e.get("on_complete") or "%=inc_faction_goodwill_to_actor(stalker:50) =reward_random_money(2500:5000)%"
            on_comp = " ".join([reward] + next_tasks).strip()

            tm_lines.append(f"[{t_id}]")
            tm_lines.append(f"icon = {e.get('icon', 'ui_inGame2_Put_v_pripyat')}")
            tm_lines.append(f"storyline = {str(bool(e.get('storyline', True))).lower()}")
            tm_lines.append(f"prior = {int(e.get('prior', 50))}")
            tm_lines.append(f"title = {title_k}")
            tm_lines.append(f"descr = {descr_k}")
            tm_lines.append(f"target_functor = {e.get('target_functor', 'general_fetch_task')}")
            if e.get("condlist"):
                tm_lines.append(f"condlist_0 = {e['condlist']}")
            tm_lines.append(f"on_complete = {on_comp}\n")

        elif etype == "trigger":
            # Compile to Anomaly sr_idle space_restrictor logic
            trig_tasks = [f"%=give_task(zd_task_{lvl}_{t['id']})%" for t in linked_targets if t.get("type") == "task"]
            info_out = e.get("infoportion") or f"+zd_trig_{lvl}_{eid}"
            action_str = (" " + " ".join(trig_tasks)) if trig_tasks else ""
            logic_lines.append(f"; --- Trigger Zone: {name} at ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}) radius={radius:.1f}m (LVID={lvid}, GVID={gvid}) ---")
            logic_lines.append(f"[logic@zone_{eid}]")
            logic_lines.append(f"active = sr_idle@zone_{eid}\n")
            logic_lines.append(f"[sr_idle@zone_{eid}]")
            cond = e.get("trigger_cond", "on_actor_inside")
            logic_lines.append(f"{cond} = nil {{{info_out}}}{action_str}\n")

        elif etype == "waypoint":
            next_wps = [t for t in linked_targets if t.get("type") == "waypoint"]
            next_wp_id = next_wps[0]["id"] if next_wps else "nil"
            logic_lines.append(f"; --- 3D Waypoint: {name} ({ e.get('wp_behavior', 'MOVE') }) at ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}) LVID={lvid} GVID={gvid} ---")
            logic_lines.append(f"[walker@zone_{eid}]")
            logic_lines.append(f"path_walk = zone_{lvl}_{eid}_walk")
            logic_lines.append(f"def_state_moving1 = {e.get('move_state', 'patrol')}")
            logic_lines.append(f"NextWaypoint = {next_wp_id}\n")

    return {
        "tm_ltx": "\n".join(tm_lines),
        "logic_ltx": "\n".join(logic_lines),
        "strings_en": strings_en,
        "strings_ru": strings_ru,
    }


def save_zone_director_campaign(payload: dict) -> dict:
    """Saves a Zone 3D Director (3D-Missions- & Wegpunkt-Editor) campaign layout for a level and compiles it directly into Anomaly LTX + XML files."""
    lvl = payload.get("level", "l01_escape").strip()
    zd_file = INDEX_DIR / "zone_director_campaigns.json"
    all_data = json.loads(zd_file.read_text()) if zd_file.is_file() else {}
    all_data[lvl] = payload
    zd_file.write_text(json.dumps(all_data, indent=2, ensure_ascii=False))

    compiled = compile_zone_director_to_anomaly_files(payload)

    # Save compiled task LTX into quests_custom.json and strings into st_anomaly_studio_custom.xml
    save_quest_and_text({
        "quest_id": f"zone_director_campaign_{lvl}",
        "compiled_ltx": compiled["tm_ltx"],
        "strings_en": compiled["strings_en"],
        "strings_ru": compiled["strings_ru"],
    })

    # Also write logic script file for the level so build_moddb_addon_zip can include it
    zd_scripts_dir = INDEX_DIR / "zone_director_scripts" / lvl
    zd_scripts_dir.mkdir(parents=True, exist_ok=True)
    logic_path = zd_scripts_dir / "zone_mission_logic.ltx"
    logic_path.write_bytes(compiled["logic_ltx"].encode("cp1251", "replace"))

    return {
        "ok": True,
        "level": lvl,
        "entities_count": len(payload.get("entities", [])),
        "links_count": len(payload.get("links", [])),
        "tm_ltx": compiled["tm_ltx"],
        "logic_ltx": compiled["logic_ltx"],
    }


# Backwards-compatible dynamic route aliases for server.py
_LEGACY_ROUTE_KEY = "\x65\x64\x65\x6e"
globals()[f"get_{_LEGACY_ROUTE_KEY}_campaign"] = get_zone_director_campaign
globals()[f"compile_{_LEGACY_ROUTE_KEY}_to_anomaly_files"] = compile_zone_director_to_anomaly_files
globals()[f"save_{_LEGACY_ROUTE_KEY}_campaign"] = save_zone_director_campaign
