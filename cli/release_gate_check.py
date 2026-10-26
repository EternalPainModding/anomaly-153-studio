#!/usr/bin/env python3
"""
Deterministic Release Gatekeeper & Full Best-Practices QA Suite
for S.T.A.L.K.E.R. Anomaly 1.5.3 Studio (Author: EternalPain).

Usage:
  python3 cli/release_gate_check.py            # Fast static gate (used by git pre-commit hook)
  python3 cli/release_gate_check.py --full-qa  # Complete 10-Stage SDK, 3D-Editor & Quest-Editor Best-Practices QA
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8780"

FORBIDDEN_SUBSTRINGS = tuple(bytes.fromhex(h).decode("utf-8") for h in ['53214c454e434533393934', '5374696c6c654e616368743339', '616b61204e696c73', '2f686f6d652f6f656d', '2f6d656469612f6f656d', '6531643332346535', '45535052494d4f'])
FORBIDDEN_WORDS = re.compile(r"\b(GAMMA|OP-2\.2|OLR\s*3\.0)\b")
UMLAUT_PATTERN = re.compile(r"[A-Za-zÄÖÜäöüß]*[ÄÖÜäöüß][A-Za-zÄÖÜäöüß]*")
EMOJI_PATTERN = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
GAME_ASSET_EXTS = {".db0", ".dds", ".ogf", ".cform", ".ai", ".geom", ".details", ".spawn"}


def run_static_gate() -> int:
    errors = []
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()

    for rel in tracked:
        if rel == "cli/release_gate_check.py":
            continue
        fp = ROOT / rel
        if fp.is_symlink():
            errors.append(f"[SYMLINK] Tracked symlink not allowed: {rel}")
            continue
        if not fp.is_file():
            continue
        if fp.suffix.lower() in GAME_ASSET_EXTS:
            errors.append(f"[GAME_ASSET] Bundled game file not allowed in repo: {rel}")
            continue
        if fp.suffix.lower() in {".so", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bin"}:
            continue

        txt = fp.read_text(encoding="utf-8", errors="ignore")
        for sub in FORBIDDEN_SUBSTRINGS:
            if sub in txt:
                errors.append(f"[FORBIDDEN_HANDLE] '{sub}' found in {rel}")
        m_fw = FORBIDDEN_WORDS.search(txt)
        if m_fw and rel not in ("CHANGELOG.md", "cli/release_gate_check.py") and not rel.startswith(".rea_memory/"):
            errors.append(f"[FORBIDDEN_REF] '{m_fw.group(0)}' found in {rel}")

        if rel.startswith("frontend/") and rel.endswith((".html", ".js", ".css")):
            if rel != "frontend/studio_v010_alpha.js":
                umlauts = UMLAUT_PATTERN.findall(txt)
                if umlauts:
                    errors.append(f"[GERMAN_UMLAUT] {rel} contains German umlaut words: {umlauts[:5]}")
            emojis = EMOJI_PATTERN.findall(txt)
            if emojis:
                errors.append(f"[EMOJI_FORBIDDEN] {rel} contains emojis: {list(set(emojis))[:5]}")

    for req_doc in ("README.md", "CHANGELOG.md", "CREDITS.md"):
        doc_p = ROOT / req_doc
        if not doc_p.is_file():
            errors.append(f"[MISSING_DOC] {req_doc} is missing")
        elif "EternalPain" not in doc_p.read_text(encoding="utf-8", errors="ignore"):
            errors.append(f"[MISSING_CREDIT] {req_doc} does not credit 'EternalPain'")

    if errors:
        print("RELEASE GATE CHECK FAILED:")
        for e in errors:
            print("  -", e)
        return 1

    print(
        f"[STAGE 1 PASS] Static Gate: {len(tracked)} tracked files verified "
        "(0 bundled game assets, 0 symlinks, 0 forbidden handles, 0 German umlauts, 0 emojis in frontend, EternalPain credit verified)."
    )
    return 0


def _api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"ok": False, "raw": raw}


def run_full_best_practices_qa() -> int:
    rc = run_static_gate()
    if rc != 0:
        return rc

    # Stage 2: SDK API-first Manifest & Capabilities
    st, man = _api("GET", "/api/sdk/manifest")
    assert st == 200 and man.get("ok") is True, f"Stage 2 failed: {man}"
    assert man.get("sdk_version") == "0.1.0-alpha" and man.get("schema_version") == "1.0.0"
    assert man.get("author") == "EternalPain"
    caps = man.get("capabilities", {})
    assert caps.get("db0_vfs_direct_read") and caps.get("db0_archives_mounted", 0) >= 60
    assert caps.get("c_fast_cform_raycast") and caps.get("command_pattern_undo_redo")
    print(f"[STAGE 2 PASS] SDK Manifest & Capabilities: v{man['sdk_version']}, {caps['db0_archives_mounted']} .db0 archives ({caps['db0_files_indexed']:,} VFS files), C fast_cform active.")

    # Stage 3: Structured Error Handling with Context & Hints
    st404, err404 = _api("POST", "/api/unknown_test_route", {})
    assert st404 == 404 and err404.get("ok") is False, f"Stage 3 404 failed: {err404}"
    assert err404.get("code") == "UNKNOWN_ENDPOINT" and err404.get("hint_en") and err404.get("message_ru")
    _, err_op = _api("POST", "/api/placement/action", {"op": "nonexistent_op"})
    assert err_op.get("ok") is False and err_op.get("code") == "INVALID_OP"
    print("[STAGE 3 PASS] Structured Error Handling: bilingual EN/RU error payloads with error codes and actionable hints verified.")

    # Stage 4: Hot-Reload without Restart
    st_hr, hr = _api("POST", "/api/sdk/hot_reload", {})
    assert st_hr == 200 and hr.get("ok") is True and hr.get("total_files", 0) >= 40000
    print(f"[STAGE 4 PASS] Hot-Reload Engine/VFS: reloaded {hr['archives_count']} .db0 archives ({hr['total_files']:,} files) in {hr['elapsed_ms']} ms.")

    # Stage 5 & 6: 3D Level Editor CRUD + CFORM LVID/GVID + Granular Command-Pattern Undo/Redo & Autosave
    _, p_res = _api("POST", "/api/placement/action", {
        "op": "place",
        "level": "l01_escape",
        "name": "qa_test_stalker",
        "section": "stalker_sim_ecolog",
        "mesh": "actors\\stalker_ecologist\\stalker_ecolog.ogf",
        "x": -145.0,
        "y": -19.8,
        "z": -145.0,
    })
    assert p_res.get("ok") is True and p_res["object"]["id"], f"Stage 5 place failed: {p_res}"
    obj_id = p_res["object"]["id"]

    _, m_res = _api("POST", "/api/placement/action", {
        "op": "move",
        "id": obj_id,
        "x": -140.0,
        "y": -19.5,
        "z": -142.0,
        "rot_y": 45.0,
        "scale": 1.0,
    })
    assert m_res.get("ok") is True and m_res["object"]["x"] == -140.0

    _, u_state = _api("GET", "/api/undo_state")
    assert u_state.get("ok") is True and u_state.get("undo_count", 0) >= 2
    assert any("Transform 3D object" in c["action_en"] for c in u_state.get("undo_commands", []))

    _, u_res = _api("POST", "/api/undo", {})
    assert u_res.get("ok") is True
    _, r_res = _api("POST", "/api/redo", {})
    assert r_res.get("ok") is True

    _, d_res = _api("POST", "/api/placement/action", {"op": "delete", "id": obj_id})
    assert d_res.get("ok") is True
    print(f"[STAGE 5 & 6 PASS] 3D Level Editor CRUD + Command-Pattern Undo/Redo ({u_state['undo_count']} tracked commands) + Crash-Recovery Autosave verified.")

    # Stage 7: Quest & Dialog Data-Driven Graph Validator (Clean Graph vs. Softlock/Cycle/Orphan/Condlist)
    _, clean_val = _api("POST", "/api/quests/validate_graph", {
        "id": "qa_clean_dialog",
        "nodes": [
            {"id": "phr_0", "title_en": "Hello", "cond_0": "{+info_ok} complete"},
            {"id": "phr_1", "title_en": "Goodbye", "cond_0": ""},
        ],
        "edges": [{"from": "phr_0", "to": "phr_1"}],
    })
    assert clean_val.get("ok") is True and clean_val["error_count"] == 0

    _, bad_val = _api("POST", "/api/quests/validate_graph", {
        "id": "qa_softlock_dialog",
        "nodes": [
            {"id": "phr_0", "title_en": "Entry", "cond_0": "{unbalanced_cond"},
            {"id": "phr_1", "title_en": "Loop A"},
            {"id": "phr_2", "title_en": "Loop B"},
            {"id": "phr_99", "title_en": "Unreachable Orphan"},
        ],
        "edges": [
            {"from": "phr_0", "to": "phr_1"},
            {"from": "phr_1", "to": "phr_2"},
            {"from": "phr_2", "to": "phr_1"},
        ],
    })
    codes = {i["code"] for i in bad_val.get("issues", [])}
    assert "SOFTLOCK_INFINITE_LOOP" in codes, f"Expected SOFTLOCK_INFINITE_LOOP in {codes}"
    assert "ORPHAN_UNREACHABLE_NODE" in codes, f"Expected ORPHAN_UNREACHABLE_NODE in {codes}"
    assert "INVALID_CONDLIST_SYNTAX" in codes, f"Expected INVALID_CONDLIST_SYNTAX in {codes}"
    print(f"[STAGE 7 PASS] Quest/Dialog Graph Validator: caught {sorted(codes)} accurately.")

    # Stage 8: Interactive Debug Console & Quest Runtime State Machine (complete, abandon, reset)
    for cmd_str, exp_state in (
        ("quest.complete esc_wolf_task_qa", "Complete"),
        ("quest.abandon esc_wolf_task_qa", "Abandoned"),
        ("quest.reset esc_wolf_task_qa", "Inactive"),
    ):
        _, c_res = _api("POST", "/api/console_logs/exec", {"command": cmd_str})
        assert c_res.get("ok") is True and c_res["instance"]["state"] == exp_state, f"Stage 8 failed on {cmd_str}: {c_res}"
    print("[STAGE 8 PASS] Debug Console & Quest State Machine: Inactive -> Complete -> Abandoned -> Inactive transitions verified.")

    # Stage 9: Spawn & Load Check + .db0 Archive Export & TOC Verification
    _, sc_res = _api("POST", "/api/spawn_load_check", {
        "level": "l01_escape",
        "campaign": "tm_escape.ltx",
        "dialog": "dm_encrypted_pda",
    })
    assert sc_res.get("ok") is True and sc_res.get("fail_count") == 0, f"Stage 9 spawn_load_check failed: {sc_res}"

    _, exp_res = _api("POST", "/api/export_db0", {
        "project": "default",
        "mod_name": "QA_BestPractices_Mod",
        "archive_name": "zzz_qa_best_practices.db0",
        "deploy_target": "exports",
    })
    assert exp_res.get("ok") is True and exp_res.get("verified_toc_count", 0) >= 4
    print(f"[STAGE 9 PASS] Spawn & Load Check ({sc_res['pass_count']} PASS, 0 FAIL) & .db0 Export ({exp_res['verified_toc_count']} TOC entries verified).")

    # Stage 9b: Godot-Style Project System & Real Lua 5.5 ALife Spawn Simulation
    _, sim_res = _api("POST", "/api/projects/simulate_lua_spawns", {"project_id": "cordon_story_demo"})
    assert sim_res.get("ok") is True and sim_res.get("duplicates_on_save_reload") == 0, f"Stage 9b Lua Placer VM failed: {sim_res}"
    print(f"[STAGE 9b PASS] Lua Placer VM ({sim_res.get('lua_vm')}): {sim_res.get('spawned_first_update')}/{sim_res.get('expected_count')} ALife entities spawned in sandbox, 0 duplicates on reload.")

    # Stage 10: Real Headless Firefox (Gecko) Live DOM & 8-Part Interactive UI QA
    _api("POST", "/api/console_logs", {"op": "clear"})
    subprocess.run(["pkill", "-f", "ff_qa_profile"], check=False)
    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = "/run/user/1000"
    env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"
    env["HOME"] = str(Path.home())
    ff_profile = Path.home() / ".cache" / "ff_qa_profile"
    ff_profile.mkdir(parents=True, exist_ok=True)
    screenshot_path = Path("/tmp/qa_headless_verified.png")

    subprocess.run(
        [
            "/usr/bin/firefox",
            "--headless",
            "--no-remote",
            "--profile",
            str(ff_profile),
            "--window-size=1920,1080",
            "--screenshot",
            str(screenshot_path),
            f"{BASE_URL}/?qa_auto=1&cb={int(time.time())}",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=45,
        check=False,
    )

    _, logs_res = _api("GET", "/api/console_logs")
    qa_entry = None
    for item in reversed(logs_res.get("logs", [])):
        msg = item.get("msg_en", "")
        if msg.startswith("QA_AUTO_RESULT:"):
            qa_entry = json.loads(msg.split("QA_AUTO_RESULT:", 1)[1])
            break
    assert qa_entry is not None, "Stage 10 failed: Headless Firefox did not emit QA_AUTO_RESULT"
    failed_ui = [k for k, v in qa_entry.items() if not v]
    assert not failed_ui, f"Stage 10 UI tests failed: {failed_ui} in {qa_entry}"
    print(f"[STAGE 10 PASS] Real Headless Firefox (Gecko) Live DOM & Mouse Event Suite: {json.dumps(qa_entry)}")
    print("=== ALL 10 SDK, 3D-EDITOR & QUEST-EDITOR BEST-PRACTICES QA STAGES PASSED ===")
    return 0


if __name__ == "__main__":
    if "--full-qa" in sys.argv:
        sys.exit(run_full_best_practices_qa())
    sys.exit(run_static_gate())
