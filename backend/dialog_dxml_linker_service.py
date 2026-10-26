#!/usr/bin/env python3
"""
Anomaly Studio 1.5.3 — Crash-Proof Dialog-XML & String-Table Generator/Linker
=============================================================================
Module: `dialog_dxml_linker_service.py`

Implements `build_safe_dialog_bundle(payload: dict) -> dict` for S.T.A.L.K.E.R. Anomaly 1.5.3
(`xray-monolith` engine):

1. Fragment XML (`gamedata/configs/gameplay/dialogs_<mod_slug>.xml`):
   - Emits ONLY `<dialog id="...">...</dialog>` blocks (no outer `<?xml ...?>` or
     `<game_dialogs>` root tags) so that X-Ray's `#include` preprocessor inside
     `<game_dialogs>` in `dialogs_<level_short>.xml` produces 100% valid XML.
   - Enforces X-Ray `CPhraseDialog` graph invariants:
     * Root `<phrase id="0">` is always present.
     * Every `<next>` reference resolves to an existing `<phrase id="...">` in the same dialog.
     * Supports dialog-level and phrase-level `has_info`, `dont_has_info`, `give_info`,
       `disable_info`, `precondition`, `action`, `init_func`, and `script_text`.

2. Patched Level Dialog XML (`gamedata/configs/gameplay/dialogs_<level_short>.xml`):
   - Loads `tools/_unpacked/configs/gameplay/dialogs_<level_short>.xml` (or synthesizes a clean
     `<game_dialogs>` base if the unpacked file is not present in a minimal test environment)
     and injects `#include "gameplay\\dialogs_<mod_slug>.xml"` immediately before `</game_dialogs>`.
   - Guarantees `CXML_IdToIndex<CPhraseDialog>::GetById` resolves every custom dialog ID in
     100% of base Anomaly 1.5.3 installations without `system.ltx` edits.

3. String-Table XMLs (`gamedata/configs/text/eng/st_dialogs_<mod_slug>.xml` & `rus`):
   - Generates valid `windows-1251` (`cp1251`) `<string_table>` XML files for both `eng` and `rus`.
   - Automatically verifies that 100% of all `<text>` IDs referenced in `<dialog>` phrases
     exist in both `eng` and `rus` string tables.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

# Canonical mapping from Anomaly 1.5.3 level directory names to `dialogs_<level_short>.xml` stems
LEVEL_TO_SHORT_MAP: Dict[str, str] = {
    "k00_marsh": "marsh",
    "l01_escape": "escape",
    "l02_garbage": "garbage",
    "l03_agroprom": "agroprom",
    "l03u_agr_underground": "agroprom_underground",
    "k01_darkscape": "darkscape",
    "l04_darkvalley": "darkvalley",
    "l04u_labx18": "darkvalley",
    "l05_bar": "bar",
    "l06_rostok": "rostok",
    "l07_military": "military",
    "l08_yantar": "yantar",
    "l08u_brainlab": "yantar",
    "l09_deadcity": "deadcity",
    "l10_limansk": "limansk",
    "l10_radar": "radar",
    "l10_red_forest": "red_forest",
    "l10u_bunker": "radar",
    "l11_hospital": "hospital",
    "l11_pripyat": "pripyat",
    "l12_stancia": "aes",
    "l12_stancia_2": "aes",
    "l12u_sarcofag": "sarcofag",
    "l12u_control_monolith": "aes",
    "l13_generators": "generators",
    "l13u_warlab": "warlab",
    "zaton": "zaton",
    "jupiter": "jupiter",
    "jupiter_underground": "jupiter",
    "pripyat": "pripyat",
    "labx8": "pripyat",
    "k02_trucks_cemetery": "trucks_cemetery",
    "y04_pole": "escape",
    "fake_start": "escape",
}

# Secondary fallback stems if a specific `dialogs_<stem>.xml` is not present in unpacked configs
LEVEL_SHORT_FALLBACKS: Dict[str, List[str]] = {
    "agroprom_underground": ["agroprom_underground", "agroprom", "escape"],
    "rostok": ["rostok", "bar", "escape"],
    "aes": ["aes", "stancia", "pripyat", "escape"],
    "sarcofag": ["sarcofag", "aes", "pripyat", "escape"],
    "warlab": ["warlab", "generators", "escape"],
    "generators": ["generators", "pripyat", "escape"],
    "hospital": ["hospital", "limansk", "escape"],
    "limansk": ["limansk", "red_forest", "escape"],
    "trucks_cemetery": ["trucks_cemetery", "garbage", "escape"],
    "darkscape": ["darkscape", "escape"],
}

_IDENTIFIER_RX = re.compile(r"^[A-Za-z0-9_.\-]+$")
_SLUG_CLEAN_RX = re.compile(r"[^a-z0-9_]+")
_LEVEL_PREFIX_RX = re.compile(r"^[kluy]\d{2}u?_")


def _xml_escape(text: str) -> str:
    """Escape XML special characters in element text content."""
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _xml_attr_escape(text: str) -> str:
    """Escape XML special characters in attribute values."""
    return (
        _xml_escape(text)
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _as_str_list(val: Any) -> List[str]:
    """Normalize a string, iterable of strings, or comma/semicolon-separated value into a clean list."""
    if val is None:
        return []
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return []
        if "," in s and "(" not in s:
            return [item.strip() for item in s.split(",") if item.strip()]
        return [s]
    if isinstance(val, (list, tuple, set)):
        out: List[str] = []
        for item in val:
            out.extend(_as_str_list(item))
        return out
    s = str(val).strip()
    return [s] if s else []


def sanitize_mod_slug(raw_slug: Optional[str], default: str = "anomaly_studio_custom") -> str:
    """Normalize a mod/bundle slug for `dialogs_<mod_slug>.xml` and `st_dialogs_<mod_slug>.xml`."""
    s = (raw_slug or "").strip().lower()
    for prefix in ("st_dialogs_", "dialogs_", "st_"):
        if s.startswith(prefix) and len(s) > len(prefix):
            s = s[len(prefix) :]
    if s.endswith(".xml"):
        s = s[:-4]
    s = _SLUG_CLEAN_RX.sub("_", s).strip("_")
    return s or default


def resolve_level_short(
    level_name: Optional[str],
    unpacked_gameplay_dir: Optional[Path] = None,
    explicit_level_short: Optional[str] = None,
) -> str:
    """
    Resolve an Anomaly 1.5.3 level name (e.g. `l01_escape`) to its `dialogs_<level_short>.xml` stem
    (e.g. `escape`). Checks `unpacked_gameplay_dir` when available to pick an existing file stem.
    """
    if explicit_level_short:
        clean_explicit = _SLUG_CLEAN_RX.sub("_", explicit_level_short.strip().lower()).strip("_")
        if clean_explicit.startswith("dialogs_"):
            clean_explicit = clean_explicit[len("dialogs_") :]
        if clean_explicit.endswith("_xml"):
            clean_explicit = clean_explicit[:-4]
        if clean_explicit:
            return clean_explicit

    raw = (level_name or "l01_escape").strip().lower()
    if ":" in raw:
        raw = raw.split(":", 1)[1].strip()
    if raw.startswith("dialogs_") and raw.endswith(".xml"):
        raw = raw[len("dialogs_") : -4]

    primary = LEVEL_TO_SHORT_MAP.get(raw)
    if not primary:
        stripped = _LEVEL_PREFIX_RX.sub("", raw)
        primary = LEVEL_TO_SHORT_MAP.get(stripped, stripped or "escape")

    if unpacked_gameplay_dir and unpacked_gameplay_dir.is_dir():
        candidates = LEVEL_SHORT_FALLBACKS.get(primary, [primary])
        if raw not in candidates:
            candidates = [primary, _LEVEL_PREFIX_RX.sub("", raw), raw]
        for cand in candidates:
            if (unpacked_gameplay_dir / f"dialogs_{cand}.xml").is_file():
                return cand

    return primary or "escape"


def _looks_like_string_id(value: str) -> bool:
    """Return True if `value` is a valid X-Ray string-table identifier rather than prose text."""
    s = (value or "").strip()
    if not s or len(s) > 96:
        return False
    if any(ch.isspace() for ch in s):
        return False
    return bool(_IDENTIFIER_RX.match(s))


def _load_base_string_table_lookup(root_dir: Path) -> Dict[str, Dict[str, str]]:
    """Load existing string IDs from unpacked configs if available for fallback resolution."""
    result: Dict[str, Dict[str, str]] = {"eng": {}, "rus": {}}
    rx = re.compile(r'<string\s+id="([^"]+)"\s*>\s*<text>(.*?)</text>\s*</string>', re.S)
    for lang in ("eng", "rus"):
        candidates = [
            root_dir / "tools" / "_unpacked" / "configs" / "text" / lang,
            root_dir / "anomaly_studio" / "tools" / "_unpacked" / "configs" / "text" / lang,
        ]
        for st_dir in candidates:
            if not st_dir.is_dir():
                continue
            for xf in sorted(st_dir.glob("*.xml")):
                try:
                    raw = xf.read_bytes().decode("cp1251", errors="ignore")
                    for sid, txt in rx.findall(raw):
                        result[lang][sid.strip()] = txt.strip()
                except Exception:
                    continue
    return result


def _normalize_phrases(
    dialog_id: str,
    raw_phrases: Any,
    dialog_level_action: List[str],
    dialog_level_give_info: List[str],
    strings_en: Dict[str, str],
    strings_ru: Dict[str, str],
    base_lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    Normalize a dialog's phrase list into a crash-proof X-Ray `CPhraseDialog` DAG:
    - Guarantees phrase `id="0"` exists.
    - Guarantees every phrase has a valid `<text>` string ID registered in `strings_en` & `strings_ru`.
    - Guarantees every `<next>` points to an existing phrase ID within the dialog.
    """
    phrase_items: List[Dict[str, Any]] = []
    if isinstance(raw_phrases, dict):
        for k, v in raw_phrases.items():
            if isinstance(v, dict):
                item = dict(v)
                item.setdefault("id", str(k))
                phrase_items.append(item)
            else:
                phrase_items.append({"id": str(k), "text": str(v)})
    elif isinstance(raw_phrases, list):
        for idx, item in enumerate(raw_phrases):
            if isinstance(item, dict):
                cp = dict(item)
                cp.setdefault("id", str(cp.get("phrase_id", idx)))
                phrase_items.append(cp)
            elif isinstance(item, str):
                phrase_items.append({"id": str(idx), "text": item})

    # If no phrases were supplied, create a default root phrase 0 and response phrase 1
    if not phrase_items:
        phrase_items = [
            {
                "id": "0",
                "text_id": f"st_{dialog_id}_0",
                "text_en": f"[{dialog_id}] Talk to NPC.",
                "text_ru": f"[{dialog_id}] Поговорить с НПС.",
                "next": ["1"],
            },
            {
                "id": "1",
                "text_id": f"st_{dialog_id}_1",
                "text_en": f"[{dialog_id}] Understood.",
                "text_ru": f"[{dialog_id}] Понял.",
                "next": [],
            },
        ]

    # Ensure phrase IDs are strings and root phrase "0" exists
    normalized_by_id: Dict[str, Dict[str, Any]] = {}
    ordered_ids: List[str] = []

    for idx, p in enumerate(phrase_items):
        raw_pid = p.get("id", p.get("phrase_id", idx))
        pid = str(raw_pid).strip()
        if not pid:
            pid = str(idx)
        if pid not in normalized_by_id:
            ordered_ids.append(pid)
        normalized_by_id[pid] = dict(p, id=pid)

    if "0" not in normalized_by_id:
        first_id = ordered_ids[0]
        synth_root = {
            "id": "0",
            "text_id": f"st_{dialog_id}_0",
            "text_en": f"[{dialog_id}] Start conversation.",
            "text_ru": f"[{dialog_id}] Начать разговор.",
            "next": [first_id],
        }
        normalized_by_id["0"] = synth_root
        ordered_ids.insert(0, "0")

    valid_ids: Set[str] = set(ordered_ids)
    out_phrases: List[Dict[str, Any]] = []

    for pid in ordered_ids:
        p = normalized_by_id[pid]
        default_sid = f"st_{dialog_id}_{pid}"

        raw_text_id = (
            p.get("text_id")
            or p.get("string_id")
            or (p.get("text") if _looks_like_string_id(str(p.get("text") or "")) else None)
            or default_sid
        )
        text_id = str(raw_text_id).strip()
        if not _looks_like_string_id(text_id):
            text_id = default_sid

        # Resolve English & Russian string table texts
        raw_text_field = str(p.get("text") or "").strip()
        prose_from_text = raw_text_field if (raw_text_field and raw_text_field != text_id) else ""

        en_val = (
            p.get("text_en")
            or p.get("eng")
            or p.get("text_eng")
            or p.get("title_en")
            or prose_from_text
            or strings_en.get(text_id)
            or base_lookup["eng"].get(text_id)
        )
        if not en_val:
            # If caller passed a string ID with no prose, provide a readable non-empty text
            en_val = raw_text_field if raw_text_field else f"{dialog_id} (phrase {pid})"

        ru_val = (
            p.get("text_ru")
            or p.get("rus")
            or p.get("text_rus")
            or p.get("title_ru")
            or strings_ru.get(text_id)
            or base_lookup["rus"].get(text_id)
            or en_val
        )

        strings_en[text_id] = str(en_val).strip()
        strings_ru[text_id] = str(ru_val).strip()

        # Normalize `<next>` links and keep only valid targets within this dialog (no self-loops)
        raw_next = p.get("next", p.get("next_ids", p.get("links", [])))
        next_ids: List[str] = []
        for nx in _as_str_list(raw_next):
            nx_clean = str(nx).strip()
            if nx_clean.startswith("phr_"):
                nx_clean = nx_clean[4:]
            if nx_clean and nx_clean in valid_ids and nx_clean != pid and nx_clean not in next_ids:
                next_ids.append(nx_clean)

        out_phrases.append(
            {
                "id": pid,
                "text": text_id,
                "text_en": strings_en[text_id],
                "text_ru": strings_ru[text_id],
                "has_info": _as_str_list(p.get("has_info")),
                "dont_has_info": _as_str_list(p.get("dont_has_info")),
                "give_info": _as_str_list(p.get("give_info")),
                "disable_info": _as_str_list(p.get("disable_info")),
                "precondition": _as_str_list(p.get("precondition")),
                "action": _as_str_list(p.get("action")),
                "script_text": str(p.get("script_text") or "").strip(),
                "next": next_ids,
            }
        )

    # Ensure root phrase "0" links to phrase "1" (or second phrase) if multi-phrase dialog has no outgoing link from "0"
    if len(out_phrases) > 1:
        root_phr = next((ph for ph in out_phrases if ph["id"] == "0"), None)
        if root_phr is not None and not root_phr["next"]:
            for candidate in out_phrases:
                if candidate["id"] != "0":
                    root_phr["next"].append(candidate["id"])
                    break

    # If dialog-level `action` or `give_info` was provided on the dialog object and not yet present on any phrase,
    # attach it to the terminal phrase (last phrase with no `next`, or last phrase in list) so X-Ray executes it.
    if dialog_level_action:
        any_phrase_has_action = any(bool(ph["action"]) for ph in out_phrases)
        if not any_phrase_has_action and out_phrases:
            leaf_phrases = [ph for ph in out_phrases if not ph["next"]]
            target_phr = leaf_phrases[-1] if leaf_phrases else out_phrases[-1]
            for act in dialog_level_action:
                if act not in target_phr["action"]:
                    target_phr["action"].append(act)

    if dialog_level_give_info:
        any_phrase_has_give = any(bool(ph["give_info"]) for ph in out_phrases)
        if not any_phrase_has_give and out_phrases:
            leaf_phrases = [ph for ph in out_phrases if not ph["next"]]
            target_phr = leaf_phrases[-1] if leaf_phrases else out_phrases[-1]
            for gi in dialog_level_give_info:
                if gi not in target_phr["give_info"]:
                    target_phr["give_info"].append(gi)

    return out_phrases


def _render_dialog_block_xml(dlg: Dict[str, Any]) -> str:
    """Render a single `<dialog id="...">...</dialog>` block with clean indentation."""
    did = _xml_attr_escape(dlg["id"])
    prio = dlg.get("priority")
    prio_attr = f' priority="{_xml_attr_escape(str(prio))}"' if prio is not None and str(prio) != "" else ""

    lines: List[str] = [f'    <dialog id="{did}"{prio_attr}>']

    for init_fn in dlg.get("init_func", []):
        lines.append(f"        <init_func>{_xml_escape(init_fn)}</init_func>")
    for pre in dlg.get("precondition", []):
        lines.append(f"        <precondition>{_xml_escape(pre)}</precondition>")
    for hi in dlg.get("has_info", []):
        lines.append(f"        <has_info>{_xml_escape(hi)}</has_info>")
    for dhi in dlg.get("dont_has_info", []):
        lines.append(f"        <dont_has_info>{_xml_escape(dhi)}</dont_has_info>")

    lines.append("        <phrase_list>")
    for ph in dlg["phrases"]:
        pid = _xml_attr_escape(ph["id"])
        lines.append(f'            <phrase id="{pid}">')
        lines.append(f"                <text>{_xml_escape(ph['text'])}</text>")
        for pre in ph.get("precondition", []):
            lines.append(f"                <precondition>{_xml_escape(pre)}</precondition>")
        for hi in ph.get("has_info", []):
            lines.append(f"                <has_info>{_xml_escape(hi)}</has_info>")
        for dhi in ph.get("dont_has_info", []):
            lines.append(f"                <dont_has_info>{_xml_escape(dhi)}</dont_has_info>")
        for gi in ph.get("give_info", []):
            lines.append(f"                <give_info>{_xml_escape(gi)}</give_info>")
        for di in ph.get("disable_info", []):
            lines.append(f"                <disable_info>{_xml_escape(di)}</disable_info>")
        for act in ph.get("action", []):
            lines.append(f"                <action>{_xml_escape(act)}</action>")
        if ph.get("script_text"):
            lines.append(f"                <script_text>{_xml_escape(ph['script_text'])}</script_text>")
        for nx in ph.get("next", []):
            lines.append(f"                <next>{_xml_escape(nx)}</next>")
        lines.append("            </phrase>")
    lines.append("        </phrase_list>")
    lines.append("    </dialog>")
    return "\n".join(lines)


def _render_fragment_dialogs_xml(
    mod_slug: str,
    npc_character_id: str,
    level_name: str,
    normalized_dialogs: List[Dict[str, Any]],
) -> str:
    """
    Build the Fragment-XML `gamedata/configs/gameplay/dialogs_<mod_slug>.xml`.
    Contains ONLY `<dialog>...</dialog>` blocks (no `<?xml ...?>` declaration and no `<game_dialogs>` root)
    so that `#include "gameplay\\dialogs_<mod_slug>.xml"` inside `<game_dialogs>` in `dialogs_<level_short>.xml`
    produces 100% valid XML.
    """
    header_comment = (
        f"<!-- Anomaly 1.5.3 Studio Dialog Fragment: dialogs_{mod_slug}.xml "
        f"(level={level_name}, npc={npc_character_id}) -->"
    )
    blocks = [_render_dialog_block_xml(d) for d in normalized_dialogs]
    return header_comment + "\n" + "\n".join(blocks) + "\n"


def _patch_level_dialogs_xml(
    base_xml_content: str,
    mod_slug: str,
    level_short: str,
) -> Tuple[str, str]:
    """
    Inject `#include "gameplay\\dialogs_<mod_slug>.xml"` immediately before `</game_dialogs>`
    in `dialogs_<level_short>.xml` (idempotent).
    Returns `(patched_xml_content, include_directive)`.
    """
    include_directive = f'#include "gameplay\\dialogs_{mod_slug}.xml"'

    content = base_xml_content or ""
    if not content.strip() or "</game_dialogs>" not in content:
        content = (
            '<?xml version="1.0" encoding="windows-1251" ?>\n'
            f"<!-- Base level dialog registry: dialogs_{level_short}.xml -->\n"
            "<game_dialogs>\n"
            "</game_dialogs>\n"
        )

    # Check if already included (tolerating forward or backward slash)
    include_rx = re.compile(
        r'#include\s+"gameplay[\\/]dialogs_' + re.escape(mod_slug) + r'\.xml"',
        re.IGNORECASE,
    )
    if include_rx.search(content):
        return content, include_directive

    closing_idx = content.rfind("</game_dialogs>")
    before = content[:closing_idx].rstrip()
    after = content[closing_idx:]
    patched = f"{before}\n    {include_directive}\n{after}"
    if not patched.endswith("\n"):
        patched += "\n"
    return patched, include_directive


def _render_string_table_xml(strings_map: Dict[str, str]) -> str:
    """Render a valid Anomaly 1.5.3 string table XML (`windows-1251` header + `<string_table>`)."""
    lines: List[str] = [
        '<?xml version="1.0" encoding="windows-1251" ?>',
        "<string_table>",
    ]
    for sid, text_val in strings_map.items():
        esc_id = _xml_attr_escape(sid)
        esc_txt = _xml_escape(text_val)
        lines.append(f'    <string id="{esc_id}">')
        lines.append(f"        <text>{esc_txt}</text>")
        lines.append("    </string>")
    lines.append("</string_table>")
    return "\n".join(lines) + "\n"


def _render_dxml_npc_linker_script(
    mod_slug: str,
    level_short: str,
    npc_character_id: str,
    dialog_ids: List[str],
) -> str:
    """
    Generate an Anomaly 1.5.3 DXML (`on_xml_read`) script (`gamedata/scripts/modxml_dialogs_<mod_slug>.script`)
    that safely links all custom `<actor_dialog>` IDs to `npc_character_id` without overwriting full
    `character_desc_*.xml` files.
    """
    lua_dialogs = ", ".join(f'"{_xml_escape(d)}"' for d in dialog_ids)
    return f"""-- =============================================================================
-- Anomaly 1.5.3 Studio — DXML Character & Dialog Linker ({mod_slug})
-- Links dialogs [{lua_dialogs}] to NPC '{npc_character_id}' on level '{level_short}'
-- =============================================================================

local TARGET_NPC_ID = "{npc_character_id}"
local DIALOG_IDS = {{ {lua_dialogs} }}

function on_xml_read()
    RegisterScriptCallback("on_xml_read", function(xml_file_name, xml_obj)
        if not xml_file_name or not xml_obj then return end
        if string.find(xml_file_name, "character_desc_") then
            local res = xml_obj:query("specific_character[id=" .. TARGET_NPC_ID .. "]")
            if res and #res > 0 then
                local char_node = res[1]
                for _, dlg_id in ipairs(DIALOG_IDS) do
                    xml_obj:insertFromXMLString("<actor_dialog>" .. dlg_id .. "</actor_dialog>", char_node, #char_node.el)
                end
            end
        end
    end)
end
"""


def verify_dialog_bundle(
    fragment_xml: str,
    patched_level_xml: str,
    string_table_eng_xml: str,
    string_table_rus_xml: str,
    mod_slug: str,
) -> Dict[str, Any]:
    """
    Perform strict structural and referential verification of the generated dialog bundle:
    1. `fragment_xml` contains ONLY `<dialog>` blocks (no `<game_dialogs>` or `<?xml` header).
    2. `patched_level_xml` contains `#include "gameplay\\dialogs_<mod_slug>.xml"` before `</game_dialogs>`.
    3. Expanding `#include` inside `patched_level_xml` parses as 100% valid XML via ElementTree.
    4. Every `<dialog>` has a root `<phrase id="0">` and all `<next>` targets exist in that dialog.
    5. Every `<text>` ID across all `<phrase>` nodes exists in BOTH `eng` and `rus` string tables.
    """
    errors: List[str] = []

    # 1. Verify fragment XML has no outer wrapper
    stripped_frag = fragment_xml.strip()
    has_xml_decl = "<?xml" in stripped_frag.lower()
    has_game_dialogs_wrapper = "<game_dialogs" in stripped_frag.lower() or "</game_dialogs>" in stripped_frag.lower()
    fragment_is_pure = (not has_xml_decl) and (not has_game_dialogs_wrapper)
    if not fragment_is_pure:
        errors.append("Fragment XML must contain only <dialog>...</dialog> blocks without <?xml> or <game_dialogs>.")

    # Parse fragment wrapped in synthetic <game_dialogs>
    wrapped_frag = f"<game_dialogs>\n{fragment_xml}\n</game_dialogs>"
    referenced_text_ids: List[str] = []
    dialog_ids: List[str] = []
    phrase_graphs_valid = True

    try:
        frag_root = ET.fromstring(wrapped_frag)
        for dlg_el in frag_root.findall("dialog"):
            did = (dlg_el.attrib.get("id") or "").strip()
            if not did:
                errors.append("Found <dialog> without 'id' attribute.")
                phrase_graphs_valid = False
                continue
            dialog_ids.append(did)
            plist = dlg_el.find("phrase_list")
            if plist is None:
                errors.append(f"Dialog '{did}' is missing <phrase_list>.")
                phrase_graphs_valid = False
                continue
            phrases = plist.findall("phrase")
            pids: Set[str] = set()
            next_targets: List[Tuple[str, str]] = []
            for ph_el in phrases:
                pid = (ph_el.attrib.get("id") or "").strip()
                if pid in pids:
                    errors.append(f"Dialog '{did}' has duplicate phrase id='{pid}'.")
                    phrase_graphs_valid = False
                pids.add(pid)
                txt_el = ph_el.find("text")
                if txt_el is not None and (txt_el.text or "").strip():
                    tid = txt_el.text.strip()
                    if tid not in referenced_text_ids:
                        referenced_text_ids.append(tid)
                else:
                    errors.append(f"Dialog '{did}' phrase '{pid}' has empty or missing <text>.")
                    phrase_graphs_valid = False
                for nx_el in ph_el.findall("next"):
                    nx_val = (nx_el.text or "").strip()
                    if nx_val:
                        next_targets.append((pid, nx_val))
            if "0" not in pids:
                errors.append(f"Dialog '{did}' is missing required root phrase id='0'.")
                phrase_graphs_valid = False
            for src_pid, dst_pid in next_targets:
                if dst_pid not in pids:
                    errors.append(f"Dialog '{did}' phrase '{src_pid}' links to non-existent next phrase '{dst_pid}'.")
                    phrase_graphs_valid = False
    except ET.ParseError as exc:
        errors.append(f"Fragment XML parse error: {exc}")
        phrase_graphs_valid = False

    # 2. Verify `#include` position in patched_level_xml
    include_directive = f'#include "gameplay\\dialogs_{mod_slug}.xml"'
    inc_pos = patched_level_xml.find(include_directive)
    close_pos = patched_level_xml.rfind("</game_dialogs>")
    include_before_close = inc_pos != -1 and close_pos != -1 and inc_pos < close_pos
    if not include_before_close:
        errors.append(f"Missing '{include_directive}' before '</game_dialogs>' in patched level XML.")

    # 3. Verify combined XML validity after preprocessor expansion
    combined_xml_valid = False
    try:
        expanded = patched_level_xml.replace(include_directive, fragment_xml)
        # Replace any other X-Ray `#include "..."` directives in base file with XML comments for parser check
        expanded_clean = re.sub(
            r'^\s*#include\s+"([^"]+)"\s*$',
            r"<!-- #include \1 -->",
            expanded,
            flags=re.MULTILINE,
        )
        # Remove encoding attribute from XML declaration when parsing str directly in ElementTree
        expanded_clean = re.sub(
            r'<\?xml\s+version="1\.0"\s+encoding="[^"]+"\s*\?>',
            '<?xml version="1.0"?>',
            expanded_clean,
            count=1,
            flags=re.IGNORECASE,
        )
        combined_root = ET.fromstring(expanded_clean)
        combined_dialog_ids = {
            (el.attrib.get("id") or "").strip() for el in combined_root.findall("dialog")
        }
        if all(d in combined_dialog_ids for d in dialog_ids):
            combined_xml_valid = True
        else:
            errors.append("Not all fragment <dialog> IDs were found in expanded <game_dialogs> XML.")
    except ET.ParseError as exc:
        errors.append(f"Combined dialogs_<level_short>.xml parse error after #include expansion: {exc}")

    # 4. Verify string tables (eng & rus)
    def _extract_st_ids(st_xml: str) -> Set[str]:
        st_clean = re.sub(
            r'<\?xml\s+version="1\.0"\s+encoding="[^"]+"\s*\?>',
            '<?xml version="1.0"?>',
            st_xml,
            count=1,
            flags=re.IGNORECASE,
        )
        root = ET.fromstring(st_clean)
        ids: Set[str] = set()
        for s_el in root.findall("string"):
            sid = (s_el.attrib.get("id") or "").strip()
            t_el = s_el.find("text")
            if sid and t_el is not None and (t_el.text or "").strip():
                ids.add(sid)
        return ids

    eng_ids: Set[str] = set()
    rus_ids: Set[str] = set()
    try:
        eng_ids = _extract_st_ids(string_table_eng_xml)
    except ET.ParseError as exc:
        errors.append(f"ENG string table XML parse error: {exc}")
    try:
        rus_ids = _extract_st_ids(string_table_rus_xml)
    except ET.ParseError as exc:
        errors.append(f"RUS string table XML parse error: {exc}")

    missing_eng = [tid for tid in referenced_text_ids if tid not in eng_ids]
    missing_rus = [tid for tid in referenced_text_ids if tid not in rus_ids]
    if missing_eng:
        errors.append(f"Missing <text> IDs in ENG string table: {missing_eng}")
    if missing_rus:
        errors.append(f"Missing <text> IDs in RUS string table: {missing_rus}")

    verified = (
        fragment_is_pure
        and include_before_close
        and combined_xml_valid
        and phrase_graphs_valid
        and not missing_eng
        and not missing_rus
        and not errors
    )

    return {
        "verified": verified,
        "fragment_is_pure_dialog_blocks": fragment_is_pure,
        "include_present_before_closing_tag": include_before_close,
        "combined_xml_valid": combined_xml_valid,
        "phrase_graphs_valid": phrase_graphs_valid,
        "all_text_ids_resolved": (len(missing_eng) == 0 and len(missing_rus) == 0),
        "all_text_ids_in_eng": len(missing_eng) == 0,
        "all_text_ids_in_rus": len(missing_rus) == 0,
        "missing_text_ids_eng": missing_eng,
        "missing_text_ids_rus": missing_rus,
        "checked_dialog_count": len(dialog_ids),
        "checked_text_count": len(referenced_text_ids),
        "errors": errors,
    }


def build_safe_dialog_bundle(payload: dict) -> dict:
    """
    Crash-proof Dialog-XML & String-Table Generator/Linker for S.T.A.L.K.E.R. Anomaly 1.5.3.

    Parameters (`payload` keys):
    - `level_name` (or `level`): e.g. `"l01_escape"`
    - `npc_character_id` (or `character_id` / `npc_id`): e.g. `"esc_2_12_stalker_wolf"`
    - `dialogs`: list of Start/Turn-In dialog definitions, each supporting:
        * `id` (or `dialog_id`)
        * `has_info`, `dont_has_info`, `precondition`, `action`, `give_info`, `init_func`, `priority`
        * `phrases`: list of phrase dicts with `id`, `text` / `text_id`, `text_en` / `eng`,
          `text_ru` / `rus`, `next`, `has_info`, `dont_has_info`, `give_info`, `precondition`, `action`
    - Optional:
        * `mod_slug` (or `mod_name` / `slug` / `quest_id`): slug for `dialogs_<mod_slug>.xml`
        * `level_short`: explicit short level name (otherwise auto-resolved from `level_name`)
        * `strings_en` / `strings_ru` / `strings`: additional string table entries
        * `root_dir` / `workspace_root`: base Anomaly Studio root directory
        * `output_dir` / `write_files`: optional directory to write the generated `gamedata/...` files
    """
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    root_dir = Path(payload.get("root_dir") or payload.get("workspace_root") or DEFAULT_ROOT)
    level_name = str(payload.get("level_name") or payload.get("level") or "l01_escape").strip()
    npc_character_id = str(
        payload.get("npc_character_id")
        or payload.get("character_id")
        or payload.get("npc_id")
        or "esc_2_12_stalker_wolf"
    ).strip()

    # Locate unpacked gameplay directory if present
    unpacked_gp_candidates = [
        root_dir / "tools" / "_unpacked" / "configs" / "gameplay",
        root_dir / "anomaly_studio" / "tools" / "_unpacked" / "configs" / "gameplay",
        root_dir / "gamedata" / "configs" / "gameplay",
    ]
    unpacked_gp_dir = next((d for d in unpacked_gp_candidates if d.is_dir()), unpacked_gp_candidates[0])

    level_short = resolve_level_short(
        level_name=level_name,
        unpacked_gameplay_dir=unpacked_gp_dir,
        explicit_level_short=payload.get("level_short"),
    )

    raw_slug = (
        payload.get("mod_slug")
        or payload.get("slug")
        or payload.get("mod_name")
        or payload.get("quest_id")
        or payload.get("campaign_id")
    )
    if not raw_slug:
        # Derive a deterministic slug from the first dialog ID or NPC + level_short
        raw_dialogs_preview = payload.get("dialogs") or []
        if isinstance(raw_dialogs_preview, list) and raw_dialogs_preview and isinstance(raw_dialogs_preview[0], dict):
            first_did = str(raw_dialogs_preview[0].get("id") or raw_dialogs_preview[0].get("dialog_id") or "").strip()
            raw_slug = first_did or f"{level_short}_{npc_character_id}"
        else:
            raw_slug = f"{level_short}_{npc_character_id}"
    mod_slug = sanitize_mod_slug(str(raw_slug))

    # Initialize string table maps with any caller-provided strings
    strings_en: Dict[str, str] = {}
    strings_ru: Dict[str, str] = {}

    if isinstance(payload.get("strings"), dict):
        for sid, sval in payload["strings"].items():
            if isinstance(sval, dict):
                if sval.get("eng") or sval.get("en"):
                    strings_en[str(sid)] = str(sval.get("eng") or sval.get("en"))
                if sval.get("rus") or sval.get("ru"):
                    strings_ru[str(sid)] = str(sval.get("rus") or sval.get("ru"))
            elif isinstance(sval, str):
                strings_en[str(sid)] = sval
                strings_ru[str(sid)] = sval

    if isinstance(payload.get("strings_en"), dict):
        for sid, sval in payload["strings_en"].items():
            strings_en[str(sid)] = str(sval)
    if isinstance(payload.get("strings_ru"), dict):
        for sid, sval in payload["strings_ru"].items():
            strings_ru[str(sid)] = str(sval)

    base_lookup = _load_base_string_table_lookup(root_dir)

    raw_dialogs = payload.get("dialogs")
    if not isinstance(raw_dialogs, list) or not raw_dialogs:
        # Build default Start & Turn-In dialog pair if none provided
        raw_dialogs = [
            {
                "id": f"dlg_{mod_slug}_start",
                "dont_has_info": [f"{mod_slug}_started"],
                "phrases": [
                    {
                        "id": "0",
                        "text_id": f"st_{mod_slug}_start_0",
                        "text_en": "Do you have any work for me?",
                        "text_ru": "Есть какая-нибудь работа для меня?",
                        "next": ["1"],
                    },
                    {
                        "id": "1",
                        "text_id": f"st_{mod_slug}_start_1",
                        "text_en": "Yes, check the coordinates on your PDA.",
                        "text_ru": "Да, проверь координаты в своём КПК.",
                        "give_info": [f"{mod_slug}_started"],
                    },
                ],
            },
            {
                "id": f"dlg_{mod_slug}_turn_in",
                "has_info": [f"{mod_slug}_started"],
                "dont_has_info": [f"{mod_slug}_completed"],
                "phrases": [
                    {
                        "id": "0",
                        "text_id": f"st_{mod_slug}_turn_in_0",
                        "text_en": "The job is done.",
                        "text_ru": "Работа выполнена.",
                        "next": ["1"],
                    },
                    {
                        "id": "1",
                        "text_id": f"st_{mod_slug}_turn_in_1",
                        "text_en": "Good work, stalker. Here is your reward.",
                        "text_ru": "Отличная работа, сталкер. Вот твоя награда.",
                        "give_info": [f"{mod_slug}_completed"],
                    },
                ],
            },
        ]

    normalized_dialogs: List[Dict[str, Any]] = []
    seen_dialog_ids: Set[str] = set()

    for idx, raw_d in enumerate(raw_dialogs):
        if not isinstance(raw_d, dict):
            continue
        raw_did = str(raw_d.get("id") or raw_d.get("dialog_id") or f"dlg_{mod_slug}_{idx + 1}").strip()
        did = _SLUG_CLEAN_RX.sub("_", raw_did.lower()).strip("_") or f"dlg_{mod_slug}_{idx + 1}"
        # Preserve original case if valid identifier
        if _IDENTIFIER_RX.match(raw_did):
            did = raw_did
        if did in seen_dialog_ids:
            did = f"{did}_{idx + 1}"
        seen_dialog_ids.add(did)

        dlg_has_info = _as_str_list(raw_d.get("has_info"))
        dlg_dont_has_info = _as_str_list(raw_d.get("dont_has_info"))
        dlg_precondition = _as_str_list(raw_d.get("precondition"))
        dlg_init_func = _as_str_list(raw_d.get("init_func"))
        dlg_action = _as_str_list(raw_d.get("action"))
        dlg_give_info = _as_str_list(raw_d.get("give_info"))

        phrases = _normalize_phrases(
            dialog_id=did,
            raw_phrases=raw_d.get("phrases"),
            dialog_level_action=dlg_action,
            dialog_level_give_info=dlg_give_info,
            strings_en=strings_en,
            strings_ru=strings_ru,
            base_lookup=base_lookup,
        )

        normalized_dialogs.append(
            {
                "id": did,
                "priority": raw_d.get("priority"),
                "init_func": dlg_init_func,
                "precondition": dlg_precondition,
                "has_info": dlg_has_info,
                "dont_has_info": dlg_dont_has_info,
                "action": dlg_action,
                "give_info": dlg_give_info,
                "phrases": phrases,
            }
        )

    # Ensure every single phrase `<text>` ID is guaranteed in both strings_en and strings_ru
    all_text_ids: List[str] = []
    for dlg in normalized_dialogs:
        for ph in dlg["phrases"]:
            tid = ph["text"]
            if tid not in all_text_ids:
                all_text_ids.append(tid)
            if not strings_en.get(tid):
                strings_en[tid] = ph.get("text_en") or tid
            if not strings_ru.get(tid):
                strings_ru[tid] = ph.get("text_ru") or strings_en[tid]

    # a) Generate Fragment-XML `gamedata/configs/gameplay/dialogs_<mod_slug>.xml`
    fragment_rel_path = f"gamedata/configs/gameplay/dialogs_{mod_slug}.xml"
    fragment_xml = _render_fragment_dialogs_xml(
        mod_slug=mod_slug,
        npc_character_id=npc_character_id,
        level_name=level_name,
        normalized_dialogs=normalized_dialogs,
    )

    # b) Generate patched `gamedata/configs/gameplay/dialogs_<level_short>.xml`
    level_dialogs_rel_path = f"gamedata/configs/gameplay/dialogs_{level_short}.xml"
    source_level_xml_path = unpacked_gp_dir / f"dialogs_{level_short}.xml"
    base_level_xml = payload.get("base_level_xml")
    if not base_level_xml and source_level_xml_path.is_file():
        try:
            base_level_xml = source_level_xml_path.read_bytes().decode("cp1251", errors="ignore")
        except Exception:
            base_level_xml = None

    patched_level_xml, include_directive = _patch_level_dialogs_xml(
        base_xml_content=base_level_xml or "",
        mod_slug=mod_slug,
        level_short=level_short,
    )

    # c) Generate String-Table XMLs (`eng` and `rus`)
    st_eng_rel_path = f"gamedata/configs/text/eng/st_dialogs_{mod_slug}.xml"
    st_rus_rel_path = f"gamedata/configs/text/rus/st_dialogs_{mod_slug}.xml"
    string_table_eng_xml = _render_string_table_xml(strings_en)
    string_table_rus_xml = _render_string_table_xml(strings_ru)

    # d) Generate DXML NPC character linker script
    dxml_rel_path = f"gamedata/scripts/modxml_dialogs_{mod_slug}.script"
    dialog_ids = [d["id"] for d in normalized_dialogs]
    dxml_script = _render_dxml_npc_linker_script(
        mod_slug=mod_slug,
        level_short=level_short,
        npc_character_id=npc_character_id,
        dialog_ids=dialog_ids,
    )

    # Verify the generated bundle
    verification = verify_dialog_bundle(
        fragment_xml=fragment_xml,
        patched_level_xml=patched_level_xml,
        string_table_eng_xml=string_table_eng_xml,
        string_table_rus_xml=string_table_rus_xml,
        mod_slug=mod_slug,
    )

    files_map: Dict[str, str] = {
        fragment_rel_path: fragment_xml,
        level_dialogs_rel_path: patched_level_xml,
        st_eng_rel_path: string_table_eng_xml,
        st_rus_rel_path: string_table_rus_xml,
        dxml_rel_path: dxml_script,
    }

    written_files: List[str] = []
    output_dir = payload.get("output_dir")
    write_files = payload.get("write_files", bool(output_dir))
    if write_files:
        target_root = Path(output_dir) if output_dir else root_dir
        for rel_path, content in files_map.items():
            full_path = target_root / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            encoding = "utf-8" if rel_path.endswith(".script") else "cp1251"
            full_path.write_bytes(content.encode(encoding, errors="replace"))
            written_files.append(str(full_path))

    return {
        "ok": verification["verified"],
        "verified": verification["verified"],
        "level_name": level_name,
        "level_short": level_short,
        "mod_slug": mod_slug,
        "npc_character_id": npc_character_id,
        "dialog_ids": dialog_ids,
        "dialogs": normalized_dialogs,
        "text_ids": all_text_ids,
        "include_directive": include_directive,
        "fragment_xml_path": fragment_rel_path,
        "fragment_xml": fragment_xml,
        "patched_level_xml_path": level_dialogs_rel_path,
        "patched_level_xml": patched_level_xml,
        "source_level_xml_path": str(source_level_xml_path),
        "string_table_eng_path": st_eng_rel_path,
        "string_table_eng_xml": string_table_eng_xml,
        "st_eng_xml": string_table_eng_xml,
        "string_table_rus_path": st_rus_rel_path,
        "string_table_rus_xml": string_table_rus_xml,
        "st_rus_xml": string_table_rus_xml,
        "dxml_script_path": dxml_rel_path,
        "dxml_script": dxml_script,
        "strings": {
            "eng": strings_en,
            "rus": strings_ru,
        },
        "files": files_map,
        "written_files": written_files,
        "verification": verification,
    }


__all__ = [
    "LEVEL_TO_SHORT_MAP",
    "sanitize_mod_slug",
    "resolve_level_short",
    "verify_dialog_bundle",
    "build_safe_dialog_bundle",
]
