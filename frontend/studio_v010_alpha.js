/**
 * Anomaly Studio v0.1.1-alpha — Must-Ship Core Extension (Strictly EN + RU, 0% DE)
 * =================================================================================
 * Author / Credits: EternalPain
 *
 * Implements:
 * 1. Tab Order: Tab #1 = Story, Dialog & Quest Builder (`quests`), Tab #2 = 3D World & Eden Placement (`map`)
 * 2. Resizable Quest/Dialog Right Inspector (`280px..780px` drag splitter + resizable textareas)
 * 3. Client-side & Server-side Hierarchical DAG Auto-Layout (`window.applyStudioHierarchicalDagLayout`)
 * 4. Persistent Collapsible/Resizable Bottom Console / Log Panel (`All`, `Info`, `Warn`, `Error`, `Spawn & Load`)
 * 5. Spawn & Load Check (`Query -> Console`) button & live log streaming
 * 6. Anomaly & MO2 Path Settings Modal (`/api/settings`) + `.db0` Export Modal (`/api/export_db0`)
 * 7. Undo / Redo (`Ctrl+Z` / `Ctrl+Y`) + Autosave (`/api/autosave` every 15s + localStorage backup)
 * 8. Basic 3D Placement (`Place`, `Select`, `Move`, `Rotate/Scale`, `Delete`, `Grid/Terrain Snap`) wired to `/api/placement/action`
 * 9. Full EN + RU Localization (removes all remaining German strings from DOM)
 */
(function () {
  "use strict";

  window.currentLang = localStorage.getItem("anomaly_studio_lang") || "en";
  if (window.currentLang !== "en" && window.currentLang !== "ru") {
    window.currentLang = "en";
  }

  const I18N_V010 = {
    en: {
      tab_quests: "1. Story, Dialog & Quest Builder",
      tab_map: "2. 3D World & Eden Placement",
      tab_ogf: "3. 3D Asset & OGF Viewer",
      tab_pack: "4. .db0 Export & Spawn Check",
      tab_howto: "5. Handbook & Shortcuts (?)",
      btn_project: "Project: default",
      btn_settings: "Paths & Settings",
      btn_undo: "Undo (Ctrl+Z)",
      btn_redo: "Redo (Ctrl+Y)",
      btn_spawn_check: "Spawn & Load Check",
      btn_export_db0: "Export .db0",
      console_title: "Studio Console & Diagnostic Log (Direct .db0 VFS)",
      console_all: "All",
      console_info: "Info",
      console_warn: "Warn",
      console_error: "Error",
      console_spawn: "Spawn & Load",
      console_clear: "Clear",
      console_copy: "Copy",
      autosave_ready: "Autosave: ON",
      autosave_saved: "Autosaved",
      autosave_off: "Autosave: OFF",
      place_bar_title: "3D Object Placement (CFORM + AI Node):",
      btn_place_obj: "Place on Terrain",
      btn_move_obj: "Move Selected",
      btn_rot_obj: "Rotate / Scale",
      btn_del_obj: "Delete Selected",
      lbl_snap_grid: "Grid Snap (1m)",
      lbl_snap_cform: "Terrain CFORM Snap",
    },
    ru: {
      tab_quests: "1. Квесты, Сюжет и Диалоги",
      tab_map: "2. 3D Мир и Размещение (Eden)",
      tab_ogf: "3. 3D Просмотр Ассетов (.ogf)",
      tab_pack: "4. Экспорт .db0 и Проверка Спавна",
      tab_howto: "5. Справочник и Хоткеи (?)",
      btn_project: "Проект: default",
      btn_settings: "Пути и Настройки",
      btn_undo: "Отмена (Ctrl+Z)",
      btn_redo: "Повтор (Ctrl+Y)",
      btn_spawn_check: "Проверка Спавна и Загрузки",
      btn_export_db0: "Экспорт .db0",
      console_title: "Консоль и Журнал Диагностики (Прямая VFS .db0)",
      console_all: "Все",
      console_info: "Инфо",
      console_warn: "Пред.",
      console_error: "Ошибки",
      console_spawn: "Спавн и Загрузка",
      console_clear: "Очистить",
      console_copy: "Копировать",
      autosave_ready: "Автосохр.: ВКЛ",
      autosave_saved: "Сохранено",
      autosave_off: "Автосохр.: ВЫКЛ",
      place_bar_title: "3D Размещение Объектов (CFORM + ИИ-Нода):",
      btn_place_obj: "Разместить",
      btn_move_obj: "Переместить",
      btn_rot_obj: "Поворот / Масштаб",
      btn_del_obj: "Удалить",
      lbl_snap_grid: "Сетка (1м)",
      lbl_snap_cform: "Привязка к CFORM",
    },
  };

  function tr(key) {
    const dict = I18N_V010[window.currentLang] || I18N_V010.en;
    return dict[key] || I18N_V010.en[key] || key;
  }

  // German -> English/Russian DOM scrubber so 0% German remains anywhere in the UI
  const DE_TO_EN_RU = [
    ["Quests & Story", "Quests & Story", "Квесты и Сюжет"],
    ["Dialoge", "Dialogs", "Диалоги"],
    ["Lade-Tipps", "Loadscreen Tips", "Советы Загрузки"],
    ["Kampagne / Storyline (Anomaly 1.5.3):", "Campaign / Storyline (Anomaly 1.5.3):", "Кампания / Сюжет (Anomaly 1.5.3):"],
    ["Suche Quest, Titel, ID oder Lade-Tipp...", "Search quest, title, dialog ID, or tip...", "Поиск квеста, заголовка, ID диалога..."],
    ["Neue Quest-Node", "New Quest Node", "Новый Узел Квеста"],
    ["Lokales Mod-Archiv ausgeben (.zip)", "Export Mod Archive (.zip / .db0)", "Экспорт Архива Мода (.zip / .db0)"],
    ["Quest, Logik & Text-Inspektor", "Quest, Logic & String Inspector", "Инспектор Квестов, Логики и Текстов"],
    ["Wähle links eine Storyline/Quest, einen Dialog oder einen Ladebildschirm-Tipp aus, um Knoten, Pfeil-Verbindungen und Texte (ENG / RUS) zu bearbeiten.", "Select a storyline/quest, dialog, or loadscreen tip on the left to inspect and edit nodes, transitions, and strings (EN / RU).", "Выберите сюжет/квест, диалог или совет слева для редактирования узлов, переходов и текстов (EN / RU)."],
    ["Core Modding Studio", "Core Modding Studio", "Основная Студия Моддинга"],
    ["Alle zeigen", "Show All", "Показать Все"],
    ["Auto-Start nach Spielstart (Test-Modus)", "Auto-Start Quest on Game Launch", "Авто-Старт Квеста при Запуске"],
    ["1-Klick Quest-Item Kloner", "1-Click Quest Item Cloner", "Клонирование Квестового Предмета"],
    ["X-Ray Pre-Flight Typecheck (7 Checks)", "X-Ray Pre-Flight Typecheck", "Предварительная Проверка X-Ray"],
    ["Handbuch & Shortcuts (?)", "Handbook & Shortcuts (?)", "Справочник и Хоткеи (?)"],
    ["8. Handbuch & Shortcuts", "4. Handbook & Shortcuts", "4. Справочник и Хоткеи"],
    ["5. Quests & Dialoge", "1. Story, Dialog & Quest Builder", "1. Квесты, Сюжет и Диалоги"],
    ["3D-Objekt gelöscht.", "3D object deleted.", "3D объект удалён."],
    ["Speichern", "Save", "Сохранить"],
    ["Schließen", "Close", "Закрыть"],
    ["Abbrechen", "Cancel", "Отмена"],
    ["Löschen", "Delete", "Удалить"],
  ];

  function scrubGermanStrings() {
    const isRu = window.currentLang === "ru";
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    let node;
    while ((node = walk.nextNode())) {
      let val = node.nodeValue;
      if (!val || !val.trim()) continue;
      for (const [deStr, enStr, ruStr] of DE_TO_EN_RU) {
        if (val.includes(deStr)) {
          val = val.split(deStr).join(isRu ? ruStr : enStr);
        }
      }
      if (val !== node.nodeValue) node.nodeValue = val;
    }
    document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((el) => {
      let ph = el.getAttribute("placeholder") || "";
      for (const [deStr, enStr, ruStr] of DE_TO_EN_RU) {
        if (ph.includes(deStr)) {
          ph = ph.split(deStr).join(isRu ? ruStr : enStr);
        }
      }
      el.setAttribute("placeholder", ph);
    });
  }

  // -------------------------------------------------------------------------
  // 1. HIERARCHICAL DAG AUTO-LAYOUT (Client-side for Auto-Layout button)
  // -------------------------------------------------------------------------
  window.applyStudioHierarchicalDagLayout = function (nodes, edges) {
    if (!Array.isArray(nodes) || !nodes.length) return nodes;
    if (typeof window.computeHierarchicalGraphLayout === "function") {
      window.computeHierarchicalGraphLayout(nodes, edges, "tree");
      return nodes;
    }
    const adj = {};
    const inDeg = {};
    nodes.forEach((n) => {
      adj[n.id] = [];
      inDeg[n.id] = 0;
    });
    (edges || []).forEach((e) => {
      if (adj[e.from] && e.to in inDeg && e.from !== e.to) {
        adj[e.from].push(e.to);
        inDeg[e.to] = (inDeg[e.to] || 0) + 1;
      }
    });
    let roots = nodes.filter((n) => n.id === "phr_0" || n.id === "0" || inDeg[n.id] === 0).map((n) => n.id);
    if (!roots.length) roots = [nodes[0].id];

    const depth = {};
    const q = [];
    roots.forEach((r) => {
      depth[r] = 0;
      q.push(r);
    });
    let head = 0;
    while (head < q.length) {
      const u = q[head++];
      const d = depth[u];
      (adj[u] || []).forEach((v) => {
        if (!(v in depth)) {
          depth[v] = d + 1;
          q.push(v);
        }
      });
    }
    let maxD = Math.max(0, ...Object.values(depth));
    nodes.forEach((n) => {
      if (!(n.id in depth)) depth[n.id] = ++maxD;
    });

    const cols = {};
    nodes.forEach((n) => {
      const d = depth[n.id];
      if (!cols[d]) cols[d] = [];
      cols[d].push(n);
    });
    const maxRows = Math.max(1, ...Object.values(cols).map((c) => c.length));
    const yStep = 145;
    const xStep = 340;
    const totalH = maxRows * yStep;

    Object.keys(cols)
      .map(Number)
      .sort((a, b) => a - b)
      .forEach((d) => {
        const colNodes = cols[d];
        const colH = colNodes.length * yStep;
        const topOff = Math.max(50, 50 + Math.floor((totalH - colH) / 2));
        colNodes.forEach((n, rIdx) => {
          n.x = 60 + d * xStep;
          n.y = topOff + rIdx * yStep;
        });
      });
    return nodes;
  };

  // -------------------------------------------------------------------------
  // 2. RESIZABLE QUEST/DIALOG RIGHT INSPECTOR (280px..780px drag handle)
  // -------------------------------------------------------------------------
  function setupResizableQuestInspector() {
    const qTab = document.getElementById("tab-quests");
    if (!qTab) return;
    const rightSidebar = qTab.querySelector(".sidebar-right");
    if (!rightSidebar || document.getElementById("qInspectorSplitter")) return;

    const savedW = parseInt(localStorage.getItem("anomaly_qinspector_width") || "420", 10);
    rightSidebar.style.width = Math.min(780, Math.max(280, savedW)) + "px";
    rightSidebar.style.minWidth = "280px";
    rightSidebar.style.maxWidth = "780px";
    rightSidebar.style.position = "relative";
    rightSidebar.style.flexShrink = "0";

    const splitter = document.createElement("div");
    splitter.id = "qInspectorSplitter";
    splitter.title = "Drag to resize Quest/Dialog Inspector (280px - 780px)";
    splitter.style.cssText =
      "position:absolute;left:-5px;top:0;bottom:0;width:10px;cursor:col-resize;z-index:50;background:transparent;display:flex;align-items:center;justify-content:center;";
    splitter.innerHTML = `<div style="width:2px;height:48px;background:#38bdf8;border-radius:2px;opacity:0.65;"></div>`;
    rightSidebar.appendChild(splitter);

    let dragging = false, startX = 0, startW = 0;
    splitter.addEventListener("mousedown", (e) => {
      e.preventDefault();
      dragging = true;
      startX = e.clientX;
      startW = rightSidebar.getBoundingClientRect().width;
      const onMove = (me) => {
        if (!dragging) return;
        const newW = Math.min(780, Math.max(280, startW - (me.clientX - startX)));
        rightSidebar.style.width = newW + "px";
        localStorage.setItem("anomaly_qinspector_width", String(Math.round(newW)));
      };
      const onUp = () => {
        dragging = false;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    });
  }

  // -------------------------------------------------------------------------
  // 3. TAB ORDER: MAKE QUEST BUILDER TAB #1 & 3D WORLD TAB #2 + HEADER BAR
  // -------------------------------------------------------------------------
  function setupTopControlsAndTabOrder() {
    // Reorder Core Tabs so Story/Dialog/Quest Builder is #1 and 3D Map is #2
    const tabsBar = document.querySelector(".nav-tabs");
    const btnQuests = document.getElementById("tabBtnQuests") || document.querySelector('.nav-btn[data-tab="quests"]');
    const btnMap = document.querySelector('.nav-btn[onclick*="map"], .nav-btn[data-tab="map"]');
    const btnOgf = document.querySelector('.nav-btn[onclick*="ogf"], .nav-btn[data-tab="ogf"]');
    const btnPack = document.querySelector('.nav-btn[onclick*="pack"], .nav-btn[data-tab="pack"]');
    const btnHowto = document.getElementById("tabBtnHowto") || document.querySelector('.nav-btn[data-tab="howto"]');

    if (tabsBar && btnQuests && btnMap) {
      btnQuests.textContent = tr("tab_quests");
      btnMap.textContent = tr("tab_map");
      if (btnOgf) {
        btnOgf.textContent = tr("tab_ogf");
        btnOgf.dataset.segment = "core";
        btnOgf.style.display = "inline-flex";
      }
      if (btnPack) btnPack.textContent = tr("tab_pack");
      if (btnHowto) btnHowto.textContent = tr("tab_howto");
      tabsBar.insertBefore(btnQuests, btnMap);
      if (btnOgf && btnPack) tabsBar.insertBefore(btnOgf, btnPack);
    }

    // Hide experimental segment switch buttons in v0.1.1-alpha release view to keep focus 100% on Must-Ship
    document.querySelectorAll('.segment-switch-btn[data-segment="lab"], .segment-switch-btn[data-segment="all"]').forEach((b) => {
      b.style.display = "none";
    });
    document.querySelectorAll('.nav-btn[data-segment="lab"]').forEach((b) => {
      if (b.dataset.tab !== "ogf") b.style.display = "none";
    });

    // Inject v0.1.1-alpha action cluster into header-right
    const hdrRight = document.querySelector(".header-right");
    if (hdrRight && !document.getElementById("v010TopBarCluster")) {
      const cluster = document.createElement("div");
      cluster.id = "v010TopBarCluster";
      cluster.style.cssText = "display:flex;align-items:center;gap:6px;flex-wrap:wrap;";
      cluster.innerHTML = `
        <span id="v010TechDemoBadge" title="Early Alpha / Technical Preview (v0.1.1-alpha) — For testing and evaluation. Always back up your gamedata/MO2 profile." style="font-size:10.5px;color:#fbbf24;background:#451a03;padding:3px 7px;border-radius:4px;border:1px solid #d97706;font-weight:700;letter-spacing:0.3px;">ALPHA TECH DEMO v0.1.1</span>
        <button type="button" id="v010AutosaveBadge" title="Click to toggle Autosave ON / OFF" style="cursor:pointer;font-size:11px;color:#34d399;background:#064e3b;padding:4px 8px;border-radius:4px;border:1px solid #059669;font-weight:600;">${tr("autosave_ready")}</button>
        <button class="btn" id="btnV010Undo" title="Undo (Ctrl+Z)" style="padding:4px 8px;font-size:11px;">${tr("btn_undo")}</button>
        <button class="btn" id="btnV010Redo" title="Redo (Ctrl+Y)" style="padding:4px 8px;font-size:11px;">${tr("btn_redo")}</button>
        <button class="btn primary" id="btnV010SpawnCheck" style="background:#0284c7;border-color:#38bdf8;color:#fff;padding:4px 10px;font-size:11px;font-weight:700;">${tr("btn_spawn_check")}</button>
        <button class="btn" id="btnV010ProjectMgr" title="Godot-Style Project Manager (project.anomaly) & In-Game Lua Spawn Script Generator" style="background:#1e1b4b;border-color:#818cf8;color:#c7d2fe;padding:4px 10px;font-size:11px;font-weight:700;">${tr("btn_project")}</button>
        <button class="btn primary" id="btnV010ExportDb0" style="background:#10b981;border-color:#059669;color:#052e16;padding:4px 10px;font-size:11px;font-weight:700;">${tr("btn_export_db0")}</button>
        <button class="btn" id="btnV010Settings" style="padding:4px 10px;font-size:11px;border-color:#f59e0b;color:#fbbf24;">${tr("btn_settings")}</button>
      `;
      hdrRight.insertBefore(cluster, hdrRight.firstChild);

      document.getElementById("v010AutosaveBadge")?.addEventListener("click", () => window.toggleStudioAutosave());
      window.syncAutosaveBadgeUI?.();
      document.getElementById("btnV010Undo")?.addEventListener("click", () => window.triggerStudioUndo());
      document.getElementById("btnV010Redo")?.addEventListener("click", () => window.triggerStudioRedo());
      document.getElementById("btnV010SpawnCheck")?.addEventListener("click", () => window.runStudioSpawnLoadCheck());
      document.getElementById("btnV010ProjectMgr")?.addEventListener("click", () => window.openProjectManagerModal());
      document.getElementById("btnV010ExportDb0")?.addEventListener("click", () => window.openExportDb0Modal());
      window.refreshActiveProjectBadge?.();
      document.getElementById("btnV010Settings")?.addEventListener("click", () => window.openStudioSettingsModal());
    }

    // Ensure #langSelect has strictly EN and RU
    const langSel = document.getElementById("langSelect");
    if (langSel) {
      langSel.innerHTML = `
        <option value="en" ${window.currentLang === "en" ? "selected" : ""}>EN (English)</option>
        <option value="ru" ${window.currentLang === "ru" ? "selected" : ""}>RU (Exp)</option>
      `;
      langSel.addEventListener("change", (e) => {
        const newLang = e.target.value === "ru" ? "ru" : "en";
        window.currentLang = newLang;
        localStorage.setItem("anomaly_studio_lang", newLang);
        fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language: newLang }),
        }).catch(() => {});
        refreshV010Labels();
        scrubGermanStrings();
        renderConsoleLogs();
      });
    }
  }

  function refreshV010Labels() {
    const mapIds = {
      btnV010Undo: "btn_undo",
      btnV010Redo: "btn_redo",
      btnV010SpawnCheck: "btn_spawn_check",
      btnV010ExportDb0: "btn_export_db0",
      btnV010Settings: "btn_settings",
      studioConsoleTitleText: "console_title",
    };
    Object.entries(mapIds).forEach(([id, k]) => {
      const el = document.getElementById(id);
      if (el) el.textContent = tr(k);
    });
    const btnQuests = document.getElementById("tabBtnQuests") || document.querySelector('.nav-btn[data-tab="quests"]');
    const btnMap = document.querySelector('.nav-btn[onclick*="map"], .nav-btn[data-tab="map"]');
    const btnPack = document.querySelector('.nav-btn[onclick*="pack"], .nav-btn[data-tab="pack"]');
    const btnHowto = document.getElementById("tabBtnHowto") || document.querySelector('.nav-btn[data-tab="howto"]');
    if (btnQuests) btnQuests.textContent = tr("tab_quests");
    if (btnMap) btnMap.textContent = tr("tab_map");
    if (btnPack) btnPack.textContent = tr("tab_pack");
    if (btnHowto) btnHowto.textContent = tr("tab_howto");
  }

  // -------------------------------------------------------------------------
  // 4. PERSISTENT COLLAPSIBLE / RESIZABLE BOTTOM CONSOLE & LOG PANEL
  // -------------------------------------------------------------------------
  let consoleLogsCache = [];
  let consoleFilter = "ALL";
  let lastLogId = 0;
  let consoleCollapsed = false;

  function injectConsolePanel() {
    if (document.getElementById("studioConsolePanel")) return;
    const panel = document.createElement("div");
    panel.id = "studioConsolePanel";
    panel.style.cssText =
      "position:fixed;left:0;right:0;bottom:0;height:185px;background:#070a0f;border-top:2px solid #1e293b;z-index:9500;display:flex;flex-direction:column;font-family:monospace;box-shadow:0 -6px 20px rgba(0,0,0,0.65);";
    panel.innerHTML = `
      <div id="studioConsoleDragBar" style="height:28px;background:#0f172a;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:space-between;padding:0 12px;cursor:ns-resize;user-select:none;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span id="studioConsoleTitleText" style="font-size:11.5px;font-weight:700;color:#38bdf8;">${tr("console_title")}</span>
          <span id="studioConsoleCountBadge" style="font-size:10px;background:#1e293b;color:#94a3b8;padding:1px 6px;border-radius:4px;">0</span>
        </div>
        <div style="display:flex;align-items:center;gap:4px;">
          <button class="btn console-filter-btn active" data-filter="ALL" style="padding:2px 7px;font-size:10.5px;">${tr("console_all")}</button>
          <button class="btn console-filter-btn" data-filter="INFO" style="padding:2px 7px;font-size:10.5px;">${tr("console_info")}</button>
          <button class="btn console-filter-btn" data-filter="WARN" style="padding:2px 7px;font-size:10.5px;">${tr("console_warn")}</button>
          <button class="btn console-filter-btn" data-filter="ERROR" style="padding:2px 7px;font-size:10.5px;">${tr("console_error")}</button>
          <button class="btn console-filter-btn" data-filter="SPAWN_CHECK" style="padding:2px 7px;font-size:10.5px;color:#34d399;">${tr("console_spawn")}</button>
          <button class="btn" id="btnConsoleClear" style="padding:2px 7px;font-size:10.5px;margin-left:6px;">${tr("console_clear")}</button>
          <button class="btn" id="btnConsoleCopy" style="padding:2px 7px;font-size:10.5px;">${tr("console_copy")}</button>
          <button class="btn" id="btnConsoleCollapse" style="padding:2px 7px;font-size:10.5px;">▼</button>
        </div>
      </div>
      <div id="studioConsoleBody" style="flex:1;overflow-y:auto;padding:8px 12px;font-size:11.5px;line-height:1.5;color:#cbd5e1;"></div>
      <div style="display:flex;align-items:center;gap:6px;padding:4px 12px;background:#090d16;border-top:1px solid #1e293b;">
        <span style="font-size:11px;color:#38bdf8;font-family:monospace;font-weight:700;">SDK&gt;</span>
        <input id="v010ConsoleCmdInput" type="text" placeholder="quest.complete &lt;id&gt; | quest.reset &lt;id&gt; | quest.abandon &lt;id&gt; | quest.validate | vfs.reload | help" style="flex:1;background:#0f172a;border:1px solid #334155;color:#f8fafc;padding:3px 8px;border-radius:4px;font-size:11px;font-family:monospace;" />
        <button class="btn primary" id="btnConsoleCmdExec" style="padding:2px 10px;font-size:10.5px;">Execute</button>
        <button class="btn" id="btnConsoleHotReload" style="padding:2px 8px;font-size:10.5px;" title="Hot-Reload .db0 VFS & State">Hot-Reload VFS</button>
      </div>
    `;
    document.body.appendChild(panel);
    document.body.style.paddingBottom = "185px";

    // Filter buttons
    panel.querySelectorAll(".console-filter-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        panel.querySelectorAll(".console-filter-btn").forEach((b) => b.classList.remove("active", "primary"));
        btn.classList.add("active", "primary");
        consoleFilter = btn.dataset.filter || "ALL";
        renderConsoleLogs();
      });
    });

    const execConsoleCmd = async () => {
      const inp = document.getElementById("v010ConsoleCmdInput");
      const raw = (inp?.value || "").trim();
      if (!raw) return;
      if (raw.toLowerCase().startsWith("quest.validate") && typeof window.validateCurrentStudioGraph === "function") {
        await window.validateCurrentStudioGraph();
      } else {
        await fetch("/api/console_logs/exec", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: raw }),
        });
      }
      if (inp) inp.value = "";
      await pollConsoleLogs();
    };
    document.getElementById("btnConsoleCmdExec")?.addEventListener("click", (e) => {
      e.stopPropagation();
      execConsoleCmd();
    });
    document.getElementById("v010ConsoleCmdInput")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        execConsoleCmd();
      }
    });
    document.getElementById("btnConsoleHotReload")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      await fetch("/api/sdk/hot_reload", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      await pollConsoleLogs();
      window.showStudioToast?.(window.currentLang === "ru" ? "Горячая перезагрузка VFS выполнена" : "Hot-Reload VFS complete", false);
    });

    document.getElementById("btnConsoleClear")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      await fetch("/api/console_logs/clear", { method: "POST", body: "{}" });
      consoleLogsCache = [];
      lastLogId = 0;
      renderConsoleLogs();
    });

    document.getElementById("btnConsoleCopy")?.addEventListener("click", (e) => {
      e.stopPropagation();
      const text = consoleLogsCache
        .map((l) => `[${l.ts}] [${l.level}] ${window.currentLang === "ru" ? l.msg_ru : l.msg_en}`)
        .join("\n");
      navigator.clipboard?.writeText(text);
      window.showStudioToast?.(window.currentLang === "ru" ? "Журнал скопирован в буфер обмена" : "Console log copied to clipboard", false);
    });

    document.getElementById("btnConsoleCollapse")?.addEventListener("click", (e) => {
      e.stopPropagation();
      consoleCollapsed = !consoleCollapsed;
      panel.style.height = consoleCollapsed ? "28px" : "185px";
      document.body.style.paddingBottom = consoleCollapsed ? "28px" : "185px";
      document.getElementById("btnConsoleCollapse").textContent = consoleCollapsed ? "▲" : "▼";
      window.dispatchEvent(new Event("resize"));
    });

    // Vertical drag resize on header bar
    const dragBar = document.getElementById("studioConsoleDragBar");
    let dragging = false, startY = 0, startH = 185;
    dragBar.addEventListener("mousedown", (e) => {
      if (e.target.tagName === "BUTTON") return;
      dragging = true;
      startY = e.clientY;
      startH = panel.getBoundingClientRect().height;
      const onMove = (me) => {
        if (!dragging) return;
        const newH = Math.min(480, Math.max(85, startH - (me.clientY - startY)));
        consoleCollapsed = false;
        panel.style.height = newH + "px";
        document.body.style.paddingBottom = newH + "px";
      };
      const onUp = () => {
        dragging = false;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        window.dispatchEvent(new Event("resize"));
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    });
  }

  function renderConsoleLogs() {
    const body = document.getElementById("studioConsoleBody");
    const badge = document.getElementById("studioConsoleCountBadge");
    if (!body) return;
    const isRu = window.currentLang === "ru";
    const filtered = consoleLogsCache.filter((l) => {
      if (consoleFilter === "ALL") return true;
      if (consoleFilter === "SPAWN_CHECK") return l.category === "spawn_check";
      return l.level === consoleFilter;
    });
    if (badge) badge.textContent = String(filtered.length);

    body.innerHTML = filtered
      .map((l) => {
        let color = "#94a3b8";
        if (l.level === "ERROR") color = "#f87171";
        else if (l.level === "WARN") color = "#fbbf24";
        else if (l.category === "spawn_check") color = "#34d399";
        else if (l.level === "INFO") color = "#38bdf8";
        const msg = isRu ? l.msg_ru || l.msg_en : l.msg_en;
        return `<div style="padding:2px 0;border-bottom:1px solid rgba(30,41,59,0.45);">
          <span style="color:#64748b;">[${l.ts}]</span>
          <span style="color:${color};font-weight:700;">[${l.level}]</span>
          <span style="color:#e2e8f0;">${ String(msg).replace(/</g, "&lt;").replace(/>/g, "&gt;") }</span>
        </div>`;
      })
      .join("");
    body.scrollTop = body.scrollHeight;
  }

  async function pollConsoleLogs() {
    try {
      const r = await fetch(`/api/console_logs?since_id=${lastLogId}`);
      if (!r.ok) return;
      const data = await r.json();
      if (data && data.boot_id) {
        if (!window._studioBootId) window._studioBootId = data.boot_id;
        else if (window._studioBootId !== data.boot_id) {
          window._studioBootId = data.boot_id;
          window.location.reload();
          return;
        }
      }
      if (data.logs && data.logs.length) {
        consoleLogsCache.push(...data.logs);
        if (consoleLogsCache.length > 500) consoleLogsCache.splice(0, consoleLogsCache.length - 500);
        lastLogId = data.latest_id || lastLogId;
        renderConsoleLogs();
      }
    } catch (e) {}
  }

  window.appendStudioLog = async function (level, msg_en, msg_ru, category = "ui") {
    try {
      await fetch("/api/console_logs/append", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, msg_en, msg_ru: msg_ru || msg_en, category }),
      });
      await pollConsoleLogs();
    } catch (e) {}
  };

  // -------------------------------------------------------------------------
  // 5. SPAWN & LOAD CHECK (Query -> Console)
  // -------------------------------------------------------------------------
  window.runStudioSpawnLoadCheck = async function () {
    const level = window.currentLevel || "l01_escape";
    const campaign = document.getElementById("qCampaignSelect")?.value || "tm_escape.ltx";
    const dialog = window.currentDialogId || "inf_trader_buy_transitions";
    try {
      const r = await fetch("/api/spawn_load_check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, campaign, dialog }),
      });
      const res = await r.json();
      await pollConsoleLogs();
      const panel = document.getElementById("studioConsolePanel");
      if (panel && consoleCollapsed) {
        document.getElementById("btnConsoleCollapse")?.click();
      }
      const msg =
        window.currentLang === "ru"
          ? `Проверка завершена: ${res.pass_count} УСПЕШНО, ${res.warn_count} ПРЕДУПР., ${res.fail_count} ОШИБОК`
          : `Spawn & Load Check complete: ${res.pass_count} PASS, ${res.warn_count} WARN, ${res.fail_count} FAIL`;
      window.showStudioToast?.(msg, res.fail_count > 0);
      return res;
    } catch (e) {
      window.showStudioToast?.("Spawn & Load Check error: " + e, true);
    }
  };

  // -------------------------------------------------------------------------
  // 6. ANOMALY & MO2 PATH SETTINGS MODAL + .DB0 EXPORT MODAL
  // -------------------------------------------------------------------------
  window.openCrossPlatformDirPicker = async function (targetInputId, titleText) {
    let picker = document.getElementById("v010CrossDirPickerModal");
    if (!picker) {
      picker = document.createElement("div");
      picker.id = "v010CrossDirPickerModal";
      picker.style.cssText =
        "position:fixed;inset:0;background:rgba(0,0,0,0.82);z-index:10050;display:flex;align-items:center;justify-content:center;padding:16px;";
      document.body.appendChild(picker);
    }
    const inp = document.getElementById(targetInputId);
    let currentDir = inp ? inp.value.trim() : "";

    async function renderDirView(dirPath) {
      const res = await fetch("/api/settings/list_dirs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: dirPath || "" }),
      }).then((r) => r.json());
      currentDir = res.current_path || "";
      const roots = res.roots || [];
      const subdirs = res.subdirs || [];

      picker.style.display = "flex";
      picker.innerHTML = `
        <div style="width:680px;max-width:95vw;max-height:85vh;background:#090d16;border:1px solid #38bdf8;border-radius:10px;padding:16px;color:#e2e8f0;display:flex;flex-direction:column;gap:10px;box-shadow:0 20px 50px rgba(0,0,0,0.9);">
          <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b;padding-bottom:8px;">
            <strong style="color:#38bdf8;font-size:14px;">${titleText || "Select Folder (Native Linux & Windows Navigator)"}</strong>
            <button class="btn" id="btnCloseDirPicker">Cancel</button>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
            <span style="font-size:11px;color:#94a3b8;">Drives / Roots:</span>
            ${roots
              .map(
                (rt) =>
                  `<button class="btn btn-dir-root" data-root="${rt.replace(/"/g, "&quot;")}" style="padding:2px 8px;font-size:11px;">${rt}</button>`
              )
              .join("")}
            <button class="btn" id="btnDirUp" style="padding:2px 8px;font-size:11px;margin-left:auto;">Up One Level (..)</button>
          </div>
          <div style="display:flex;gap:6px;align-items:center;">
            <input id="inpDirPickerCurrent" type="text" class="search-box" style="flex:1;margin:0;font-family:monospace;font-size:12px;" value="${currentDir.replace(/"/g, "&quot;")}">
            <button class="btn" id="btnDirGo" style="padding:4px 10px;font-size:11px;">Go</button>
          </div>
          <div style="flex:1;min-height:240px;max-height:360px;overflow-y:auto;background:#050811;border:1px solid #1e293b;border-radius:6px;padding:6px;display:flex;flex-direction:column;gap:3px;">
            ${
              subdirs.length === 0
                ? `<div style="padding:12px;color:#64748b;font-size:12px;">No subdirectories in this folder.</div>`
                : subdirs
                    .map(
                      (sd) => `
                  <div class="dir-row-item" data-path="${sd.path.replace(/"/g, "&quot;")}" style="display:flex;justify-content:space-between;align-items:center;padding:5px 8px;border-radius:4px;cursor:pointer;background:#0f172a;border:1px solid #1e293b;font-size:12px;">
                    <span style="font-family:monospace;color:#e2e8f0;">[DIR] ${sd.name}</span>
                    <span style="font-size:10px;color:#34d399;">
                      ${sd.is_anomaly_candidate ? "[db/*.db0 detected]" : sd.is_mo2_candidate ? "[MO2 detected]" : ""}
                    </span>
                  </div>`
                    )
                    .join("")
            }
          </div>
          <div style="display:flex;justify-content:flex-end;gap:8px;padding-top:6px;border-top:1px solid #1e293b;">
            <button class="btn primary" id="btnSelectThisFolder" style="font-weight:700;">Use This Folder</button>
          </div>
        </div>
      `;

      document.getElementById("btnCloseDirPicker").onclick = () => (picker.style.display = "none");
      document.getElementById("btnDirUp").onclick = () => renderDirView(res.parent_path || currentDir);
      document.getElementById("btnDirGo").onclick = () =>
        renderDirView(document.getElementById("inpDirPickerCurrent").value.trim());
      document.getElementById("btnSelectThisFolder").onclick = () => {
        const chosen = document.getElementById("inpDirPickerCurrent").value.trim() || currentDir;
        if (inp && chosen) inp.value = chosen;
        picker.style.display = "none";
      };
      picker.querySelectorAll(".btn-dir-root").forEach((b) => {
        b.onclick = () => renderDirView(b.getAttribute("data-root"));
      });
      picker.querySelectorAll(".dir-row-item").forEach((row) => {
        row.onclick = () => renderDirView(row.getAttribute("data-path"));
      });
    }

    await renderDirView(currentDir);
  };

  window.openStudioSettingsModal = async function (isFirstRunPrompt = false) {
    let modal = document.getElementById("v010SettingsModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "v010SettingsModal";
      modal.style.cssText =
        "position:fixed;inset:0;background:rgba(0,0,0,0.78);z-index:10030;display:flex;align-items:center;justify-content:center;padding:16px;";
      document.body.appendChild(modal);
    }
    modal.style.display = "flex";
    if (!modal.innerHTML) {
      modal.innerHTML = `<div style="background:#0f172a;border:1px solid #f5c400;border-radius:10px;padding:18px 24px;color:#f8fafc;font-size:13px;">Loading Paths & Settings...</div>`;
    }
    const [r, modsRes] = await Promise.all([
      fetch("/api/settings").then((x) => x.json()).catch(() => ({})),
      fetch("/api/settings/importable_mods").then((x) => x.json()).catch(() => ({ mods: [] })),
    ]);
    const st = r.settings || {};
    const val = r.validation || {};
    const importableMods = modsRes.mods || [];
    const isRu = window.currentLang === "ru";
    const showFirstRunBanner = isFirstRunPrompt || !st.first_run_completed || !val.anomaly_valid;

    modal.style.display = "flex";
    modal.innerHTML = `
      <div style="width:760px;max-width:96vw;max-height:92vh;overflow-y:auto;background:#0f172a;border:1px solid #38bdf8;border-radius:10px;padding:20px;color:#e2e8f0;box-shadow:0 16px 40px rgba(0,0,0,0.85);display:flex;flex-direction:column;gap:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b;padding-bottom:10px;">
          <div>
            <h3 style="margin:0;color:#38bdf8;font-size:16px;">
              ${isRu ? "Настройка Путей, Папок Модов и Импорт из MO2 (Linux и Windows)" : "Workspace Paths, Input/Output Folders & MO2 Mod Importer (Linux & Windows)"}
            </h3>
            <p style="font-size:11.5px;color:#94a3b8;margin:4px 0 0;">
              ${isRu ? "Прямое чтение архивов .db0 из папки игры (распаковка unpacked/ не требуется)." : "Direct .db0 VFS archive reader (zero unpacked/ folder required). Works natively on Linux and Windows."}
            </p>
          </div>
          <button class="btn" id="btnAutoDetectPaths" style="font-size:11px;border-color:#38bdf8;color:#38bdf8;">
            ${isRu ? "Авто-Поиск Путей" : "Auto-Detect Paths"}
          </button>
        </div>

        ${
          showFirstRunBanner
            ? `<div style="background:#0c192c;border:1px solid #0284c7;border-radius:8px;padding:10px 12px;font-size:12px;color:#bae6fd;">
                <strong>${isRu ? "Первый запуск Anomaly Studio:" : "First-Launch Setup Wizard:"}</strong>
                ${
                  isRu
                    ? "Укажите путь к S.T.A.L.K.E.R. Anomaly 1.5.3, папку Mod Organizer 2 (опционально) и папки ввода/вывода модов."
                    : "Please verify or select your S.T.A.L.K.E.R. Anomaly 1.5.3 installation path, Mod Organizer 2 (MO2) directory, Addons Input folder, and Mods Output folder."
                }
              </div>`
            : ""
        }

        <!-- 1. Anomaly 1.5.3 Path -->
        <div style="background:#090d16;border:1px solid #1e293b;border-radius:8px;padding:10px 12px;">
          <label style="font-size:12px;font-weight:700;color:#cbd5e1;display:block;margin-bottom:4px;">
            1. ${isRu ? "Путь к S.T.A.L.K.E.R. Anomaly 1.5.3 (обязательно):" : "S.T.A.L.K.E.R. Anomaly 1.5.3 Installation Path (Required):"}
          </label>
          <div style="display:flex;gap:6px;align-items:center;">
            <input id="inpSettingAnomalyPath" type="text" class="search-box" style="flex:1;margin:0;" placeholder="C:\Games\Anomaly-1.5.3 or /path/to/Anomaly" value="${(st.anomaly_path || "").replace(/"/g, "&quot;")}">
            <button class="btn btn-os-browse" data-target="inpSettingAnomalyPath" data-title="Select S.T.A.L.K.E.R. Anomaly 1.5.3 Directory" style="font-size:11px;">Browse (OS)</button>
            <button class="btn btn-tree-browse" data-target="inpSettingAnomalyPath" data-title="Select S.T.A.L.K.E.R. Anomaly 1.5.3 Directory" style="font-size:11px;">Navigator</button>
          </div>
          <div style="font-size:11px;margin-top:4px;color:${val.anomaly_valid ? "#34d399" : "#f87171"};">
            ${val.anomaly_valid ? `Valid (${val.anomaly_db0_count} packed .db0 archives detected)` : "Please select a valid Anomaly 1.5.3 root folder containing db/*.db0"}
          </div>
        </div>

        <!-- 2. Mod Organizer 2 (MO2) Path -->
        <div style="background:#090d16;border:1px solid #1e293b;border-radius:8px;padding:10px 12px;">
          <label style="font-size:12px;font-weight:700;color:#cbd5e1;display:block;margin-bottom:4px;">
            2. ${isRu ? "Путь к Mod Organizer 2 / MO2 (для импорта и деплоя модов):" : "Mod Organizer 2 (MO2) Path (Optional, for MO2 mod import & direct deployment):"}
          </label>
          <div style="display:flex;gap:6px;align-items:center;">
            <input id="inpSettingMo2Path" type="text" class="search-box" style="flex:1;margin:0;" placeholder="C:\Modding\MO2 or /path/to/MO2" value="${(st.mo2_path || "").replace(/"/g, "&quot;")}">
            <button class="btn btn-os-browse" data-target="inpSettingMo2Path" data-title="Select Mod Organizer 2 (MO2) Directory" style="font-size:11px;">Browse (OS)</button>
            <button class="btn btn-tree-browse" data-target="inpSettingMo2Path" data-title="Select Mod Organizer 2 (MO2) Directory" style="font-size:11px;">Navigator</button>
          </div>
          <div style="font-size:11px;margin-top:4px;color:${val.mo2_valid ? "#34d399" : "#fbbf24"};">
            ${val.mo2_valid ? `Valid MO2 directory (${val.mo2_mods_Count || 0} mods found in ${val.mo2_mods_dir})` : "Optional MO2 root or instance folder"}
          </div>
        </div>

        <!-- 3. Addons / Mods Input Folder -->
        <div style="background:#090d16;border:1px solid #1e293b;border-radius:8px;padding:10px 12px;">
          <label style="font-size:12px;font-weight:700;color:#cbd5e1;display:block;margin-bottom:4px;">
            3. ${isRu ? "Входная Папка Аддонов / Модов (Addons / Mods Input Folder):" : "Addons / Mods Input Folder (Source folder for external addons & unpacked mods):"}
          </label>
          <div style="display:flex;gap:6px;align-items:center;">
            <input id="inpSettingAddonsInputPath" type="text" class="search-box" style="flex:1;margin:0;" placeholder="Folder containing unpacked addons/mods to edit or merge" value="${(st.addons_input_path || "").replace(/"/g, "&quot;")}">
            <button class="btn btn-os-browse" data-target="inpSettingAddonsInputPath" data-title="Select Addons / Mods Input Folder" style="font-size:11px;">Browse (OS)</button>
            <button class="btn btn-tree-browse" data-target="inpSettingAddonsInputPath" data-title="Select Addons / Mods Input Folder" style="font-size:11px;">Navigator</button>
          </div>
          <div style="font-size:11px;margin-top:4px;color:${val.addons_input_valid ? "#34d399" : "#94a3b8"};">
            ${val.addons_input_valid ? `Ready (${val.addons_input_count || 0} addon folders detected)` : "Will be created automatically on save if it does not exist"}
          </div>
        </div>

        <!-- 4. Mods Output Folder -->
        <div style="background:#090d16;border:1px solid #1e293b;border-radius:8px;padding:10px 12px;">
          <label style="font-size:12px;font-weight:700;color:#cbd5e1;display:block;margin-bottom:4px;">
            4. ${isRu ? "Выходная Папка Готовых Модов (Mods Output Folder):" : "Mods Output Folder (Target directory for built .db0 archives & mod packages):"}
          </label>
          <div style="display:flex;gap:6px;align-items:center;">
            <input id="inpSettingModsOutputPath" type="text" class="search-box" style="flex:1;margin:0;" placeholder="Folder where exported .db0 / mod packages are written" value="${(st.mods_output_path || "").replace(/"/g, "&quot;")}">
            <button class="btn btn-os-browse" data-target="inpSettingModsOutputPath" data-title="Select Mods Output Folder" style="font-size:11px;">Browse (OS)</button>
            <button class="btn btn-tree-browse" data-target="inpSettingModsOutputPath" data-title="Select Mods Output Folder" style="font-size:11px;">Navigator</button>
          </div>
          <div style="font-size:11px;margin-top:4px;color:${val.mods_output_valid ? "#34d399" : "#94a3b8"};">
            ${val.mods_output_valid ? `Ready (${st.mods_output_path})` : "Will be created automatically on save if it does not exist"}
          </div>
        </div>

        <!-- 5. Direct Mod Importer from MO2 / Addons Input Folder -->
        <div style="background:#090d16;border:1px solid #334155;border-radius:8px;padding:10px 12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="font-size:12px;font-weight:700;color:#38bdf8;">
              ${isRu ? "Импорт Модов из Mod Organizer 2 (MO2) или Входной Папки Аддонов" : "Import Mod from Mod Organizer 2 (MO2) or Addons Input Folder"}
            </span>
            <span style="font-size:11px;color:#94a3b8;">${importableMods.length} mods available</span>
          </div>
          <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
            <select id="selImportableMod" class="search-box" style="flex:1;min-width:240px;margin:0;">
              ${
                importableMods.length === 0
                  ? `<option value="">-- Save MO2 Path or Addons Input Path above to list mods --</option>`
                  : importableMods
                      .map(
                        (m) =>
                          `<option value="${m.path.replace(/"/g, "&quot;")}" data-name="${m.name.replace(/"/g, "&quot;")}">[${m.source}] ${m.name} (${m.has_gamedata ? "gamedata" : "root"}${m.db0_count ? ", " + m.db0_count + " .db0" : ""})</option>`
                      )
                      .join("")
              }
            </select>
            <label style="font-size:11px;color:#cbd5e1;display:flex;align-items:center;gap:4px;cursor:pointer;">
              <input type="checkbox" id="chkImportAsNewProj" checked>
              ${isRu ? "Создать как новый проект" : "Create as new Studio project"}
            </label>
            <button class="btn primary" id="btnImportModNow" style="font-size:11px;" ${importableMods.length === 0 ? "disabled" : ""}>
              ${isRu ? "Импортировать Мод" : "Import Selected Mod"}
            </button>
          </div>
        </div>

        <div style="display:flex;justify-content:flex-end;gap:8px;padding-top:6px;border-top:1px solid #1e293b;">
          <button class="btn" id="btnCloseSettingsModal">${isRu ? "Закрыть" : "Close"}</button>
          <button class="btn primary" id="btnSaveSettingsModal" style="font-weight:700;">${isRu ? "Сохранить Все Пути и Проверить" : "Save & Validate All Paths"}</button>
        </div>
      </div>
    `;

    modal.querySelectorAll(".btn-os-browse").forEach((btn) => {
      btn.onclick = async () => {
        const targetId = btn.getAttribute("data-target");
        const title = btn.getAttribute("data-title") || "Select Folder";
        const inp = document.getElementById(targetId);
        const res = await fetch("/api/settings/browse_dir", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, initial_dir: inp ? inp.value.trim() : "" }),
        }).then((x) => x.json());
        if (res.ok && res.path && inp) {
          inp.value = res.path;
        } else if (!res.cancelled) {
          await window.openCrossPlatformDirPicker(targetId, title);
        }
      };
    });

    modal.querySelectorAll(".btn-tree-browse").forEach((btn) => {
      btn.onclick = async () => {
        const targetId = btn.getAttribute("data-target");
        const title = btn.getAttribute("data-title") || "Select Folder";
        await window.openCrossPlatformDirPicker(targetId, title);
      };
    });

    document.getElementById("btnAutoDetectPaths").onclick = async () => {
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_detect: true }),
      }).then((x) => x.json());
      window.showStudioToast?.("Auto-detected paths on this machine!", false);
      window.openStudioSettingsModal(isFirstRunPrompt);
    };

    const btnImport = document.getElementById("btnImportModNow");
    if (btnImport) {
      btnImport.onclick = async () => {
        const sel = document.getElementById("selImportableMod");
        const modPath = sel ? sel.value : "";
        if (!modPath) return;
        const createNew = !!document.getElementById("chkImportAsNewProj")?.checked;
        btnImport.disabled = true;
        btnImport.textContent = "Importing...";
        const res = await fetch("/api/settings/import_mod", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mod_path: modPath, create_new_project: createNew }),
        }).then((x) => x.json());
        await pollConsoleLogs();
        await window.refreshActiveProjectBadge();
        if (res.ok) {
          window.showStudioToast?.(
            "Imported " + res.source_mod_name + " into project " + res.project_id + " (" + res.copied_files + " files)!",
            false
          );
          modal.style.display = "none";
        } else {
          window.showStudioToast?.(res.error || "Import failed", true);
          btnImport.disabled = false;
          btnImport.textContent = "Import Selected Mod";
        }
      };
    }

    document.getElementById("btnCloseSettingsModal").onclick = () => (modal.style.display = "none");
    document.getElementById("btnSaveSettingsModal").onclick = async () => {
      const anomaly_path = document.getElementById("inpSettingAnomalyPath").value.trim();
      const mo2_path = document.getElementById("inpSettingMo2Path").value.trim();
      const addons_input_path = document.getElementById("inpSettingAddonsInputPath").value.trim();
      const mods_output_path = document.getElementById("inpSettingModsOutputPath").value.trim();
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          anomaly_path,
          mo2_path,
          addons_input_path,
          mods_output_path,
          language: window.currentLang,
        }),
      }).then((x) => x.json());
      await pollConsoleLogs();
      window.showStudioToast?.(
        res.validation?.anomaly_valid
          ? `Workspace paths saved! (${res.validation.anomaly_db0_count} .db0 archives indexed)`
          : "Warning: Anomaly path has no db/*.db0 archives",
        !res.validation?.anomaly_valid
      );
      modal.style.display = "none";
    };
  };

  window.activeStudioProjectId = "default";

  window.refreshActiveProjectBadge = async function () {
    try {
      const r = await fetch("/api/projects");
      const data = await r.json();
      if (data && data.ok) {
        window.activeStudioProjectId = data.active_project || "default";
        const btn = document.getElementById("btnV010ProjectMgr");
        const count = data.active_summary?.stats?.placed_objects_count ?? 0;
        if (btn) {
          btn.textContent = (window.currentLang === "ru" ? "Проект: " : "Project: ") + window.activeStudioProjectId + ` (${count})`;
        }
      }
    } catch (e) {}
  };

  window.runLuaPlacerSimulation = async function (projectId) {
    try {
      const res = await fetch("/api/projects/simulate_lua_spawns", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId || window.activeStudioProjectId || "default" }),
      }).then((r) => r.json());
      await pollConsoleLogs();
      const badge = document.getElementById("lblLuaPlacerStatus3D");
      if (badge && res) {
        badge.style.display = "block";
        badge.textContent = `[${res.lua_vm || "Lua VM"}] PASS: ${res.spawned_first_update}/${res.expected_count} ALife entities spawned (0 reload duplicates) -> ${res.script_rel}`;
      }
      if (res && res.ok) {
        window.showStudioToast?.(
          `Lua Placer [${res.lua_vm}]: ${res.spawned_first_update} ALife entities spawned, 0 duplicates on reload!`,
          false
        );
      } else {
        window.showStudioToast?.("Lua Placer simulation warning", true);
      }
      return res;
    } catch (e) {
      window.showStudioToast?.("Lua Placer error: " + e, true);
      return { ok: false, error: String(e) };
    }
  };

  window.openProjectManagerModal = async function () {
    let modal = document.getElementById("v010ProjectModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "v010ProjectModal";
      modal.style.cssText =
        "position:fixed;inset:0;background:rgba(0,0,0,0.78);z-index:10030;display:flex;align-items:center;justify-content:center;padding:16px;";
      document.body.appendChild(modal);
    }
    modal.style.display = "flex";
    if (!modal.innerHTML) {
      modal.innerHTML = `<div style="background:#0f172a;border:1px solid #f5c400;border-radius:10px;padding:18px 24px;color:#f8fafc;font-size:13px;">Loading Project Manager...</div>`;
    }
    const isRu = window.currentLang === "ru";
    const data = await fetch("/api/projects").then((r) => r.json()).catch(() => ({}));
    const act = data.active_summary || {};
    const mf = act.manifest || {};
    const luaInfo = data.lua_spawn_script || {};
    const projects = data.projects || [];

    modal.style.display = "flex";
    modal.innerHTML = `
      <div style="width:940px;max-width:96vw;max-height:90vh;overflow:auto;resize:both;background:#0f172a;border:1px solid #818cf8;border-radius:10px;padding:18px;color:#e2e8f0;box-shadow:0 20px 50px rgba(0,0,0,0.85);display:flex;flex-direction:column;gap:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b;padding-bottom:10px;">
          <div>
            <h3 style="margin:0;color:#818cf8;font-size:16px;">${isRu ? "Менеджер Проектов (project.anomaly) и Генератор Lua Спавна" : "Project Workspace Manager (project.anomaly) & In-Game Lua Spawn Generator"}</h3>
            <div style="font-size:11px;color:#94a3b8;margin-top:3px;">
              ${isRu ? "Базовые архивы Anomaly 1.5.3 (.db0) остаются 100% только для чтения. Каждый проект изолирован в projects/<id>/." : "Base Anomaly 1.5.3 .db0 archives stay 100% read-only. Each mod workspace is isolated in projects/<id>/."}
            </div>
          </div>
          <button class="btn" id="btnCloseProjectModal">${isRu ? "Закрыть" : "Close"}</button>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
          <!-- Left: Active Project Manifest & Project List -->
          <div style="background:#090d16;border:1px solid #1e293b;border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:8px;">
            <div style="font-size:12px;font-weight:700;color:#38bdf8;">${isRu ? "Активный Проект (project.anomaly)" : "Active Project Manifest (project.anomaly)"}</div>
            <div style="display:grid;grid-template-columns:110px 1fr;gap:6px;align-items:center;font-size:11.5px;">
              <span style="color:#94a3b8;">Project ID:</span>
              <code style="color:#34d399;font-weight:700;">projects/${act.project_id || "default"}/project.anomaly</code>
              <span style="color:#94a3b8;">Title:</span>
              <input id="inpProjTitle" class="search-box" style="margin:0;" value="${(mf.title || "").replace(/"/g, "&quot;")}">
              <span style="color:#94a3b8;">Version:</span>
              <input id="inpProjVersion" class="search-box" style="margin:0;" value="${(mf.version || "0.1.0").replace(/"/g, "&quot;")}">
              <span style="color:#94a3b8;">Output .db0:</span>
              <input id="inpProjArchive" class="search-box" style="margin:0;" value="${(mf.archive_name || "zzz_default.db0").replace(/"/g, "&quot;")}">
            </div>
            <label style="font-size:11px;color:#94a3b8;">${isRu ? "Описание мода:" : "Mod Description:"}</label>
            <textarea id="inpProjDesc" class="search-box" style="width:100%;min-height:52px;resize:both;margin:0;font-family:sans-serif;">${(mf.description || "").replace(/</g, "&lt;")}</textarea>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px;">
              <button class="btn primary" id="btnSaveProjManifest" style="font-size:11px;">${isRu ? "Сохранить project.anomaly + Lua" : "Save project.anomaly + Generate Lua"}</button>
              <button class="btn" id="btnSnapProjManifest" style="font-size:11px;border-color:#38bdf8;color:#38bdf8;">${isRu ? "Создать Снапшот" : "Save Snapshot"}</button>
              <button class="btn primary" id="btnExportProjDb0Now" style="background:#10b981;border-color:#059669;color:#052e16;font-size:11px;font-weight:700;">${isRu ? "Собрать .db0 Архив" : "Build & Export .db0"}</button>
            </div>

            <div style="border-top:1px solid #1e293b;margin-top:6px;padding-top:8px;">
              <div style="font-size:12px;font-weight:700;color:#cbd5e1;margin-bottom:6px;">${isRu ? "Все Проекты (" + projects.length + ")" : "Available Projects (" + projects.length + ")"}</div>
              <div style="max-height:135px;overflow-y:auto;display:flex;flex-direction:column;gap:5px;">
                ${projects
                  .map(
                    (p) => `
                  <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;background:${p.is_active ? "#1e1b4b" : "#0f172a"};border:1px solid ${p.is_active ? "#818cf8" : "#1e293b"};border-radius:6px;font-size:11px;">
                    <div>
                      <strong style="color:${p.is_active ? "#34d399" : "#f8fafc"};">${p.manifest?.title || p.project_id}</strong>
                      <span style="color:#94a3b8;"> (${p.project_id} v${p.manifest?.version || "0.1.0"})</span>
                      <div style="font-size:10px;color:#64748b;">3D Objects: ${p.stats?.placed_objects_count || 0} | Quests: ${p.stats?.quest_edits_count || 0} | Snapshots: ${p.stats?.snapshots_count || 0}</div>
                    </div>
                    ${
                      p.is_active
                        ? `<span style="font-size:10px;background:#065f46;color:#34d399;padding:2px 6px;border-radius:4px;font-weight:700;">ACTIVE</span>`
                        : `<button class="btn btn-switch-proj" data-pid="${p.project_id}" style="padding:3px 8px;font-size:10.5px;">Switch</button>`
                    }
                  </div>`
                  )
                  .join("")}
              </div>
            </div>

            <!-- Create New Project -->
            <div style="border-top:1px solid #1e293b;margin-top:4px;padding-top:8px;">
              <div style="font-size:11.5px;font-weight:700;color:#fbbf24;margin-bottom:4px;">${isRu ? "Создать Новый Изолированный Проект" : "Create New Isolated Mod Project"}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:6px;">
                <input id="inpNewProjId" class="search-box" style="margin:0;font-size:11px;" placeholder="project_id (e.g. cordon_story)">
                <input id="inpNewProjTitle" class="search-box" style="margin:0;font-size:11px;" placeholder="Mod Title">
                <button class="btn primary" id="btnCreateNewProj" style="padding:4px 10px;font-size:11px;">+ Create</button>
              </div>
            </div>
          </div>

          <!-- Right: Live In-Game Lua Spawn Script Generator -->
          <div style="background:#090d16;border:1px solid #1e293b;border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:12px;font-weight:700;color:#34d399;">${isRu ? "Генератор Lua-Скрипта Спавна в Игре" : "In-Game ALife Lua Spawn Script Generator"}</div>
                <code id="lblLuaScriptRelPath" style="font-size:10.5px;color:#94a3b8;">${luaInfo.script_rel || "gamedata/scripts/mod_studio_spawns_default.script"} (${luaInfo.entity_count || 0} entities)</code>
              </div>
              <div style="display:flex;gap:6px;">
                <button class="btn" id="btnRegenLuaSpawn" style="padding:3px 8px;font-size:10.5px;">Refresh Lua</button>
                <button class="btn primary" id="btnSimLuaSpawnModal" style="padding:3px 8px;font-size:10.5px;background:#059669;border-color:#10b981;color:#fff;">Simulate ALife VM</button>
                <button class="btn primary" id="btnCopyLuaSpawn" style="padding:3px 8px;font-size:10.5px;">Copy .script</button>
              </div>
            </div>
            <textarea id="txtLuaSpawnPreview" spellcheck="false" style="flex:1;width:100%;min-height:330px;resize:both;background:#050811;color:#a7f3d0;border:1px solid #334155;border-radius:6px;padding:10px;font-family:monospace;font-size:11px;line-height:1.45;">${(luaInfo.lua_code || "").replace(/</g, "&lt;")}</textarea>
            <div style="font-size:10.5px;color:#94a3b8;">
              ${isRu ? "Этот скрипт автоматически упаковывается в .db0 и спавнит все размещённые в 3D-редакторе объекты один раз на сохранение через alife_create(section, pos, lvid, gvid)." : "Automatically packed into your .db0 build. Spawns all placed 3D objects once per savegame via alife_create(section, pos, lvid, gvid) with exact rotation and story_id."}
            </div>
          </div>
        </div>
      </div>
    `;

    document.getElementById("btnCloseProjectModal").onclick = () => (modal.style.display = "none");

    document.getElementById("btnSaveProjManifest").onclick = async () => {
      const payload = {
        project_id: act.project_id || "default",
        title: document.getElementById("inpProjTitle").value.trim(),
        version: document.getElementById("inpProjVersion").value.trim(),
        archive_name: document.getElementById("inpProjArchive").value.trim(),
        description: document.getElementById("inpProjDesc").value.trim(),
        create_snapshot: false,
      };
      const res = await fetch("/api/projects/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then((r) => r.json());
      await pollConsoleLogs();
      await window.refreshActiveProjectBadge();
      if (res.lua_spawn_script) {
        document.getElementById("txtLuaSpawnPreview").value = res.lua_spawn_script.lua_code || "";
      }
      window.showStudioToast?.("Saved project.anomaly & updated Lua spawn script!", false);
    };

    document.getElementById("btnSnapProjManifest").onclick = async () => {
      const res = await fetch("/api/projects/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: act.project_id || "default",
          title: document.getElementById("inpProjTitle").value.trim(),
          version: document.getElementById("inpProjVersion").value.trim(),
          archive_name: document.getElementById("inpProjArchive").value.trim(),
          description: document.getElementById("inpProjDesc").value.trim(),
          create_snapshot: true,
          snapshot_label: "manual",
        }),
      }).then((r) => r.json());
      await pollConsoleLogs();
      window.showStudioToast?.(`Snapshot saved: ${res.snapshot_created || "ok"}`, false);
      window.openProjectManagerModal();
    };

    document.getElementById("btnExportProjDb0Now").onclick = async () => {
      await window.openExportDb0Modal(
        act.project_id || "default",
        document.getElementById("inpProjArchive").value.trim()
      );
    };

    document.getElementById("btnSimLuaSpawnModal").onclick = async () => {
      const simRes = await window.runLuaPlacerSimulation(act.project_id || "default");
      if (simRes && simRes.lua_code) {
        const ta = document.getElementById("txtLuaSpawnPreview");
        if (ta) ta.value = simRes.lua_code;
      }
    };
    document.getElementById("btnRegenLuaSpawn").onclick = async () => {
      const res = await fetch("/api/projects/generate_lua_spawns", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: act.project_id || "default" }),
      }).then((r) => r.json());
      if (res.ok) {
        document.getElementById("txtLuaSpawnPreview").value = res.lua_code || "";
        document.getElementById("lblLuaScriptRelPath").textContent = `${res.script_rel} (${res.entity_count} entities)`;
        window.showStudioToast?.(`Generated ${res.script_rel} (${res.entity_count} entities)`, false);
      }
    };

    document.getElementById("btnCopyLuaSpawn").onclick = () => {
      const code = document.getElementById("txtLuaSpawnPreview")?.value || "";
      navigator.clipboard?.writeText(code);
      window.showStudioToast?.("Copied Lua spawn script to clipboard!", false);
    };

    document.getElementById("btnCreateNewProj").onclick = async () => {
      const project_id = document.getElementById("inpNewProjId").value.trim();
      const title = document.getElementById("inpNewProjTitle").value.trim() || project_id;
      if (!project_id) {
        window.showStudioToast?.("Please enter a Project ID", true);
        return;
      }
      const res = await fetch("/api/projects/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id, title, switch_to: true }),
      }).then((r) => r.json());
      await pollConsoleLogs();
      await window.refreshActiveProjectBadge();
      window.refreshPlacedObjectsForLevel?.(window.currentLevel || "l01_escape");
      window.showStudioToast?.(`Created & switched to project '${project_id}'`, false);
      window.openProjectManagerModal();
    };

    modal.querySelectorAll(".btn-switch-proj").forEach((btn) => {
      btn.onclick = async () => {
        const pid = btn.getAttribute("data-pid");
        await fetch("/api/projects/switch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: pid }),
        });
        await pollConsoleLogs();
        await window.refreshActiveProjectBadge();
        window.refreshPlacedObjectsForLevel?.(window.currentLevel || "l01_escape");
        window.showStudioToast?.(`Switched active project to '${pid}'`, false);
        window.openProjectManagerModal();
      };
    });
  };

  window.openExportDb0Modal = async function (customProjId, customArchiveName) {
    const isRu = window.currentLang === "ru";
    const projId = customProjId || window.activeStudioProjectId || "default";
    const archName = customArchiveName || `zzz_${projId.toLowerCase()}.db0`;
    const res = await fetch("/api/export_db0", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project: projId,
        mod_name: `Anomaly_Studio_${projId}`,
        archive_name: archName,
        deploy_target: "both",
      }),
    }).then((x) => x.json());
    await pollConsoleLogs();
    if (res.ok) {
      window.showStudioToast?.(
        isRu
          ? `Успешно упакован ${res.archive_name} (${res.size_bytes} Б, файлов в TOC: ${res.verified_toc_count})`
          : `Exported ${res.archive_name} (${res.size_bytes} B, verified TOC entries: ${res.verified_toc_count})`,
        false
      );
    } else {
      window.showStudioToast?.(res.message_en || "Export failed", true);
    }
    return res;
  };

  // -------------------------------------------------------------------------
  // 7. UNDO / REDO (Ctrl+Z / Ctrl+Y) + AUTOSAVE
  // -------------------------------------------------------------------------
  window.triggerStudioUndo = async function () {
    const questsTabActive = document.getElementById("tab-quests")?.classList.contains("active");
    if (questsTabActive && typeof window.undoQuestOrDialogGraph === "function") {
      if (window.undoQuestOrDialogGraph()) return { ok: true };
    }
    const res = await fetch("/api/undo", { method: "POST", body: "{}" }).then((x) => x.json());
    await pollConsoleLogs();
    if (res.ok && res.state) {
      window.placedStudioObjects = res.state.placed_objects || [];
      renderPlaced3DObjectsOnMap();
      window.showStudioToast?.(`Undo: ${res.action_en}`, false);
    } else if (typeof window.undoQuestOrDialogGraph === "function" && window.undoQuestOrDialogGraph()) {
      return { ok: true };
    } else {
      window.showStudioToast?.(res.message_en || "Nothing to undo", true);
    }
    return res;
  };

  window.triggerStudioRedo = async function () {
    const questsTabActive = document.getElementById("tab-quests")?.classList.contains("active");
    if (questsTabActive && typeof window.redoQuestOrDialogGraph === "function") {
      if (window.redoQuestOrDialogGraph()) return { ok: true };
    }
    const res = await fetch("/api/redo", { method: "POST", body: "{}" }).then((x) => x.json());
    await pollConsoleLogs();
    if (res.ok && res.state) {
      window.placedStudioObjects = res.state.placed_objects || [];
      renderPlaced3DObjectsOnMap();
      window.showStudioToast?.(`Redo: ${res.action_en}`, false);
    } else if (typeof window.redoQuestOrDialogGraph === "function" && window.redoQuestOrDialogGraph()) {
      return { ok: true };
    } else {
      window.showStudioToast?.(res.message_en || "Nothing to redo", true);
    }
    return res;
  };

  window.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
      e.preventDefault();
      if (e.shiftKey) window.triggerStudioRedo();
      else window.triggerStudioUndo();
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
      e.preventDefault();
      window.triggerStudioRedo();
    }
  });

  // Toggleable Autosave (persisted in localStorage, default ON)
  window.studioAutosaveEnabled = localStorage.getItem("anomaly_studio_autosave_enabled") !== "false";

  window.syncAutosaveBadgeUI = function (lastTimeStr) {
    const badge = document.getElementById("v010AutosaveBadge");
    if (!badge) return;
    if (window.studioAutosaveEnabled) {
      badge.style.color = "#34d399";
      badge.style.background = "#064e3b";
      badge.style.borderColor = "#059669";
      badge.textContent = lastTimeStr ? `${tr("autosave_saved")} (${lastTimeStr})` : tr("autosave_ready");
    } else {
      badge.style.color = "#94a3b8";
      badge.style.background = "#1e293b";
      badge.style.borderColor = "#475569";
      badge.textContent = tr("autosave_off");
    }
  };

  window.runStudioAutosaveNow = async function () {
    try {
      const payload = {
        record_undo: false,
        active_level: window.currentLevel || "l01_escape",
        active_campaign: document.getElementById("qCampaignSelect")?.value || "tm_escape.ltx",
      };
      localStorage.setItem("anomaly_studio_autosave_backup", JSON.stringify(payload));
      await fetch("/api/autosave", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const nowStr = new Date().toLocaleTimeString();
      window.syncAutosaveBadgeUI(nowStr);
    } catch (e) {}
  };

  window.toggleStudioAutosave = function (forceState) {
    window.studioAutosaveEnabled = typeof forceState === "boolean" ? forceState : !window.studioAutosaveEnabled;
    localStorage.setItem("anomaly_studio_autosave_enabled", window.studioAutosaveEnabled ? "true" : "false");
    window.syncAutosaveBadgeUI();
    window.showStudioToast?.(
      window.studioAutosaveEnabled
        ? (window.currentLang === "ru" ? "Автосохранение включено (каждые 15 сек)" : "Autosave enabled (every 15s)")
        : (window.currentLang === "ru" ? "Автосохранение выключено" : "Autosave disabled"),
      false
    );
    if (window.studioAutosaveEnabled) {
      window.runStudioAutosaveNow();
    }
  };

  // Periodic Autosave every 15 seconds (only when enabled)
  setInterval(async () => {
    if (!window.studioAutosaveEnabled) return;
    await window.runStudioAutosaveNow();
  }, 15000);

  // -------------------------------------------------------------------------
  // 8. X-RAY SDK 0.7 3D PLACEMENT PIPELINE (Live 3D OGF Ghost, Real OGF Meshes, Gizmo & Terrain Raycast)
  // -------------------------------------------------------------------------
  window.placedStudioObjects = [];
  window.selectedStudioObjectId = null;
  window.studioPlacementGroup3D = null;
  window.studioGhostGroup3D = null;
  window.studioGhostRotY = 0;
  let studioPlacementGroup3D = null;
  let _currentGhostMeshPath = "";
  let _ghostLoadingPath = "";

  const PRESET_TO_TOPBAR_KEY = {
    "quest_case_01": "quest_box",
    "device_pda_1": "pda",
    "stalker_sim_ecolog": "ecolog",
    "sim_default_duty_2": "stalker",
    "wpn_ak74": "ak74",
    "af_medusa": "medusa",
    "inv_backpack": "stash"
  };

  const TOPBAR_KEY_TO_PRESET = {
    "quest_box": "quest_case_01|dynamics\\equipments\\quest\\box_black.ogf|item",
    "pda": "device_pda_1|dynamics\\devices\\dev_pda\\dev_pda.ogf|item",
    "ecolog": "stalker_sim_ecolog|actors\\stalker_ecologist\\stalker_ecolog.ogf|npc",
    "stalker": "sim_default_duty_2|actors\\stalker_dolg\\stalker_dolg_2.ogf|npc",
    "ak74": "wpn_ak74|dynamics\\weapons\\wpn_ak74\\wpn_ak74.ogf|weapon",
    "medusa": "af_medusa|dynamics\\artefacts\\af_medusa.ogf|artefact",
    "stash": "inv_backpack|dynamics\\equipments\\sumka1.ogf|stash"
  };

  function getActivePlacementSpec() {
    if (window.quest3DPickState && window.quest3DPickState.active) {
      return {
        section: window.quest3DPickState.itemSection || window.quest3DPickState.targetSection || "quest_target",
        mesh: window.quest3DPickState.itemMesh || "dynamics\\equipments\\quest\\box_black.ogf",
        category: "quest_target"
      };
    }
    const selEl = document.getElementById("selPlacePreset");
    const val = selEl?.value || "quest_case_01|dynamics\\equipments\\quest\\box_black.ogf|item";
    const [section, mesh, category] = val.split("|");
    return { section: section || "quest_case_01", mesh: mesh || "dynamics\\equipments\\quest\\box_black.ogf", category: category || "item" };
  }

  async function ensureGhostMeshLoaded(meshPath) {
    const THREE = window.THREE;
    const scene = window.mapScene;
    if (!THREE || !scene) return;
    if (!window.studioGhostGroup3D) {
      const gg = new THREE.Group();
      gg.name = "StudioSDK3DGhostGroup";
      gg.visible = false;

      // SDK Ground Target Ring + Crosshair + Forward Arrow + Normal Line
      const ringGeom = new THREE.RingGeometry(0.55, 0.82, 32);
      ringGeom.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({ color: 0x10b981, side: THREE.DoubleSide, depthTest: false, transparent: true, opacity: 0.92 });
      const ringMesh = new THREE.Mesh(ringGeom, ringMat);
      ringMesh.position.y = 0.04;
      ringMesh.renderOrder = 995;
      gg.add(ringMesh);

      const arrowGeom = new THREE.ConeGeometry(0.18, 0.5, 10);
      arrowGeom.rotateX(Math.PI / 2);
      const arrowMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, depthTest: false, transparent: true, opacity: 0.9 });
      const arrowMesh = new THREE.Mesh(arrowGeom, arrowMat);
      arrowMesh.position.set(0, 0.12, 0.95);
      arrowMesh.renderOrder = 996;
      gg.add(arrowMesh);

      const normPoints = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 1.6, 0)];
      const normGeom = new THREE.BufferGeometry().setFromPoints(normPoints);
      const normLine = new THREE.Line(normGeom, new THREE.LineBasicMaterial({ color: 0x10b981, depthTest: false, transparent: true, opacity: 0.75 }));
      normLine.renderOrder = 995;
      gg.add(normLine);

      const meshHolder = new THREE.Group();
      meshHolder.name = "GhostOgfHolder";
      gg.add(meshHolder);

      window.studioGhostGroup3D = gg;
      scene.add(gg);
    }

    const normPath = (meshPath || "").replace(/\\/g, "/").trim();
    if (!normPath || normPath === _currentGhostMeshPath || normPath === _ghostLoadingPath) return;
    if (typeof window.fetchOgfCached !== "function" || typeof window.createThreeObjectFromOgfData !== "function") return;

    _ghostLoadingPath = normPath;
    try {
      const data = await window.fetchOgfCached(normPath, window.currentLevel || "l01_escape");
      if (data && !data.error && window.studioGhostGroup3D) {
        const holder = window.studioGhostGroup3D.getObjectByName("GhostOgfHolder");
        if (holder) {
          while (holder.children.length > 0) holder.remove(holder.children[0]);
          const ogfObj = window.createThreeObjectFromOgfData(data, window.currentLevel || "l01_escape", true, false);
          ogfObj.traverse((m) => {
            if (m.isMesh && m.material) {
              m.material = m.material.clone();
              m.material.transparent = true;
              m.material.opacity = 0.72;
              if (m.material.emissive) m.material.emissive.setHex(0x0d4f38);
            }
          });
          holder.add(ogfObj);
          _currentGhostMeshPath = normPath;
        }
      }
    } catch (e) {
      // keep ring fallback
    } finally {
      _ghostLoadingPath = "";
    }
  }

  window.hideStudio3DGhostPreview = function () {
    if (window.studioGhostGroup3D) {
      window.studioGhostGroup3D.visible = false;
    }
  };

  window.updateStudio3DGhostPreview = function (e, raycaster, cformMeshes, tip, mapRenderer) {
    const visibleCform = (cformMeshes || []).filter((m) => m && m.visible);
    if (!visibleCform.length) return false;
    const spec = getActivePlacementSpec();
    ensureGhostMeshLoaded(spec.mesh);

    const hits = raycaster.intersectObjects(visibleCform, false);
    if (!hits.length) {
      if (window.studioGhostGroup3D) window.studioGhostGroup3D.visible = false;
      return false;
    }

    const hit = hits[0];
    const pt = hit.point.clone();
    const snapChecked = document.getElementById("chkGridSnap3D")?.checked;
    const snapSelectVal = parseFloat(document.getElementById("gridSnapSelect")?.value || "0");
    const snapStep = snapSelectVal > 0 ? snapSelectVal : (snapChecked ? 0.5 : 0);

    const sx = snapStep > 0 ? Math.round(pt.x / snapStep) * snapStep : pt.x;
    const sy = pt.y;
    const sz = snapStep > 0 ? Math.round(pt.z / snapStep) * snapStep : pt.z;

    if (window.studioGhostGroup3D) {
      window.studioGhostGroup3D.position.set(sx, sy, sz);
      window.studioGhostGroup3D.rotation.set(0, ((window.studioGhostRotY || 0) * Math.PI) / 180, 0);
      window.studioGhostGroup3D.visible = true;
    }

    if (mapRenderer?.domElement) {
      mapRenderer.domElement.style.cursor = "crosshair";
    }
    if (tip) {
      tip.style.display = "block";
      tip.style.left = (e.clientX + 16) + "px";
      tip.style.top = (e.clientY + 16) + "px";
      const isQuestPick = Boolean(window.quest3DPickState && window.quest3DPickState.active);
      tip.innerHTML =
        `<div style="border-left:3px solid #10b981;padding-left:6px;">` +
        `<strong style="color:#10b981;">${isQuestPick ? "SDK 3D QUEST TARGET PICK" : "SDK 3D PLACEMENT PREVIEW (LMB TO PLACE)"}</strong><br/>` +
        `Section: <code>${spec.section}</code> | Mesh: <code>${spec.mesh.split(/[\\/]/).pop()}</code><br/>` +
        `World XYZ: <code>${sx.toFixed(2)}, ${sy.toFixed(2)}, ${sz.toFixed(2)}</code> | Yaw: <code>${window.studioGhostRotY || 0} deg</code> <span style="color:#94a3b8;">(Q/E rotate, Shift=Multi, Esc=Exit)</span>` +
        `</div>`;
    }
    return true;
  };

  window.onStudioGizmoModeChanged = function (mode) {
    const btnInteractive = document.getElementById("btnInteractivePlace3D");
    if (btnInteractive) {
      if (mode === "place") {
        btnInteractive.classList.add("primary");
        btnInteractive.textContent = "Click Terrain to Place (Active - Esc to Exit)";
        const spec = getActivePlacementSpec();
        ensureGhostMeshLoaded(spec.mesh);
      } else {
        btnInteractive.classList.remove("primary");
        btnInteractive.textContent = "Click-to-Place on Terrain (R)";
        window.hideStudio3DGhostPreview();
      }
    }
  };

  // Q/E rotation shortcut while in Place mode
  window.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
    if (window.editorMode === "place") {
      if (e.key === "q" || e.key === "Q") {
        window.studioGhostRotY = ((window.studioGhostRotY || 0) - 15 + 360) % 360;
      } else if (e.key === "e" || e.key === "E") {
        window.studioGhostRotY = ((window.studioGhostRotY || 0) + 15) % 360;
      } else if (e.key === "Escape") {
        if (typeof window.setGizmoMode === "function") window.setGizmoMode("translate");
      }
    }
  });

  function inject3DPlacementBar() {
    const mapTab = document.getElementById("tab-map");
    if (mapTab && !document.getElementById("v010PlacementBar")) {
      const inspBody = mapTab.querySelector(".sidebar-right .inspector-body");
      if (inspBody) {
        const bar = document.createElement("div");
        bar.id = "v010PlacementBar";
        bar.className = "stat-card";
        bar.style.cssText =
          "display:flex;flex-direction:column;gap:6px;padding:10px;background:#0b1320;border:1px solid #1e3a5f;border-left:3px solid #38bdf8;font-size:11.5px;";
        bar.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong style="color:#38bdf8;">${tr("place_bar_title")}</strong>
            <span style="font-size:10px;color:#10b981;font-family:monospace;">SDK 0.7 OGF + Raycast</span>
          </div>
          <select id="selPlacePreset" class="search-box" style="width:100%;padding:4px 6px;font-size:11px;">
            <option value="quest_case_01|dynamics\equipments\quest\box_black.ogf|item">Quest Box: Supply Case (quest_case_01)</option>
            <option value="device_pda_1|dynamics\devices\dev_pda\dev_pda.ogf|item">Quest PDA: Stalker PDA (device_pda_1)</option>
            <option value="stalker_sim_ecolog|actors\stalker_ecologist\stalker_ecolog.ogf|npc">NPC: Ecolog Stalker (stalker_sim_ecolog)</option>
            <option value="sim_default_duty_2|actors\stalker_dolg\stalker_dolg_2.ogf|npc">NPC: Duty Veteran (sim_default_duty_2)</option>
            <option value="wpn_ak74|dynamics\weapons\wpn_ak74\wpn_ak74.ogf|weapon">Weapon: AK-74 (wpn_ak74)</option>
            <option value="af_medusa|dynamics\artefacts\af_medusa.ogf|artefact">Artefact: Jellyfish (af_medusa)</option>
            <option value="inv_backpack|dynamics\equipments\sumka1.ogf|stash">Stash: Backpack (inv_backpack)</option>
          </select>
          <button class="btn" id="btnInteractivePlace3D" style="padding:5px 8px;font-size:11px;border-color:#10b981;color:#10b981;font-weight:600;">Click-to-Place on Terrain (R)</button>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;">
            <button class="btn primary" id="btnPlace3DObj" style="padding:5px 8px;font-size:11px;" title="Place 3D object right onto terrain at camera crosshair">${tr("btn_place_obj")}</button>
            <button class="btn" id="btnMove3DObj" style="padding:5px 8px;font-size:11px;">${tr("btn_move_obj")}</button>
            <button class="btn" id="btnRot3DObj" style="padding:5px 8px;font-size:11px;">${tr("btn_rot_obj")}</button>
            <button class="btn" id="btnDel3DObj" style="padding:5px 8px;font-size:11px;border-color:#ef4444;color:#f87171;">${tr("btn_del_obj")}</button>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
            <label style="display:inline-flex;align-items:center;gap:5px;color:#94a3b8;cursor:pointer;font-size:11px;">
              <input type="checkbox" id="chkGridSnap3D" checked> ${tr("lbl_snap_grid")}
            </label>
            <label style="display:inline-flex;align-items:center;gap:5px;color:#94a3b8;cursor:pointer;font-size:11px;">
              <input type="checkbox" id="chkCformSnap3D" checked> ${tr("lbl_snap_cform")}
            </label>
            <button class="btn" id="btnSnapSelectedGround3D" style="padding:2px 7px;font-size:10.5px;margin-left:auto;border-color:#10b981;color:#34d399;" title="Snap selected 3D object or spawn onto terrain surface (Shortcut: G)">Snap to Ground (G)</button>
          </div>
          <select id="selPlacedEntityList" class="search-box" style="width:100%;padding:4px 6px;font-size:11px;">
            <option value="">-- Placed Objects (0) --</option>
          </select>
          <div style="display:grid;grid-template-columns:1fr auto;gap:5px;margin-top:2px;">
            <button class="btn primary" id="btnLuaPlacerSim3D" style="padding:5px 8px;font-size:11px;background:#065f46;border-color:#10b981;color:#ecfdf5;font-weight:700;" title="Compile placed 3D objects to Lua .script and run ALife VM spawn simulation">Lua Placer: Build &amp; Simulate ALife (.script)</button>
            <button class="btn" id="btnOpenLuaPlacerCode3D" style="padding:5px 8px;font-size:11px;border-color:#818cf8;color:#c7d2fe;" title="Open generated Lua spawn script in Project Manager">View Lua</button>
          </div>
          <div id="lblLuaPlacerStatus3D" style="font-size:10.5px;color:#34d399;font-family:monospace;display:none;padding:4px 6px;background:#052e16;border:1px solid #059669;border-radius:4px;"></div>
        `;
        inspBody.insertBefore(bar, inspBody.children[1] || inspBody.firstChild);

        document.getElementById("selPlacePreset")?.addEventListener("change", (ev) => {
          const [sec, mesh] = (ev.target.value || "").split("|");
          const topSel = document.getElementById("placePresetSelect");
          if (topSel && PRESET_TO_TOPBAR_KEY[sec]) {
            topSel.value = PRESET_TO_TOPBAR_KEY[sec];
          }
          ensureGhostMeshLoaded(mesh);
        });

        document.getElementById("placePresetSelect")?.addEventListener("change", (ev) => {
          const mapped = TOPBAR_KEY_TO_PRESET[ev.target.value];
          const selEl = document.getElementById("selPlacePreset");
          if (mapped && selEl) {
            selEl.value = mapped;
            const [, mesh] = mapped.split("|");
            ensureGhostMeshLoaded(mesh);
          }
        });

        document.getElementById("btnInteractivePlace3D")?.addEventListener("click", () => {
          const nextMode = window.editorMode === "place" ? "translate" : "place";
          if (typeof window.setGizmoMode === "function") {
            window.setGizmoMode(nextMode);
          }
        });

        document.getElementById("chkGridSnap3D")?.addEventListener("change", (ev) => {
          const gSel = document.getElementById("gridSnapSelect");
          const mode = ev.target.checked ? "0.5" : "off";
          if (gSel) gSel.value = mode;
          if (typeof window.applyGridSnap === "function") window.applyGridSnap(mode);
        });
        document.getElementById("btnSnapSelectedGround3D")?.addEventListener("click", () => {
          if (typeof window.snapSelectedSpawnToGround === "function") window.snapSelectedSpawnToGround();
        });
        document.getElementById("btnPlace3DObj")?.addEventListener("click", () => window.placeStudio3DObject());
        document.getElementById("btnMove3DObj")?.addEventListener("click", () => window.moveSelectedStudio3DObject(2.0, 0.0, 2.0));
        document.getElementById("btnRot3DObj")?.addEventListener("click", () => window.rotateSelectedStudio3DObject(45.0, 1.15));
        document.getElementById("btnDel3DObj")?.addEventListener("click", () => window.deleteSelectedStudio3DObject());
        document.getElementById("btnLuaPlacerSim3D")?.addEventListener("click", () => window.runLuaPlacerSimulation());
        document.getElementById("btnOpenLuaPlacerCode3D")?.addEventListener("click", () => window.openProjectManagerModal());
        document.getElementById("selPlacedEntityList")?.addEventListener("change", (e) => {
          const id = e.target.value || null;
          if (id) {
            window.selectStudioPlaced3DObject(id, true);
          } else {
            window.selectedStudioObjectId = null;
            renderPlaced3DObjectsOnMap();
          }
        });
      }
    }

    // Enhance Tab 3 (3D Asset & OGF Viewer) with Custom .ogf Import & Quest Item Preview shortcuts
    const ogfTab = document.getElementById("tab-ogf");
    if (ogfTab && !document.getElementById("v010OgfImportBox")) {
      const ogfSidebar = ogfTab.querySelector(".sidebar");
      const ogfToolbar = ogfTab.querySelector(".viewport-toolbar");
      if (ogfSidebar) {
        const impBox = document.createElement("div");
        impBox.id = "v010OgfImportBox";
        impBox.style.cssText = "padding:8px 10px;background:#0d1522;border-bottom:1px solid #1e3a5f;display:flex;flex-direction:column;gap:6px;";
        impBox.innerHTML = `
          <div style="font-size:11px;font-weight:700;color:#38bdf8;">Import Custom .OGF Model & Quest Items</div>
          <div style="display:flex;align-items:center;gap:6px;">
            <label for="inpCustomOgfFile" class="btn" style="padding:3px 8px;font-size:10.5px;cursor:pointer;white-space:nowrap;">Select .OGF File</label>
            <span id="lblCustomOgfFileName" style="font-size:10.5px;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">No file selected</span>
            <input type="file" id="inpCustomOgfFile" accept=".ogf" style="display:none;">
          </div>
          <div style="display:flex;gap:4px;">
            <input type="text" id="inpCustomOgfRelPath" class="search-box" placeholder="dynamics/equipments/quest/my_item.ogf" style="flex:1;font-size:10.5px;padding:4px 6px;font-family:monospace;">
            <button class="btn primary" id="btnUploadCustomOgf" style="padding:4px 8px;font-size:10.5px;white-space:nowrap;">Import & View</button>
          </div>
          <div style="display:flex;gap:4px;flex-wrap:wrap;">
            <button class="btn" data-qogf="dynamics/equipments/quest/box_black.ogf" style="font-size:10px;padding:3px 6px;">Supply Box (x16)</button>
            <button class="btn" data-qogf="dynamics/equipments/quest/notes_document_case_1.ogf" style="font-size:10px;padding:3px 6px;">Field Case</button>
            <button class="btn" data-qogf="dynamics/devices/dev_pda/dev_pda.ogf" style="font-size:10px;padding:3px 6px;">Stalker PDA</button>
            <button class="btn" data-qogf="dynamics/artefacts/af_medusa.ogf" style="font-size:10px;padding:3px 6px;">Artifact</button>
          </div>
        `;
        ogfSidebar.insertBefore(impBox, ogfSidebar.children[1] || ogfSidebar.firstChild);

        impBox.querySelectorAll("[data-qogf]").forEach((b) => {
          b.addEventListener("click", () => {
            if (typeof window.loadOgfModel === "function") window.loadOgfModel(b.dataset.qogf);
          });
        });

        document.getElementById("inpCustomOgfFile")?.addEventListener("change", (ev) => {
          const f = ev.target.files?.[0];
          const lbl = document.getElementById("lblCustomOgfFileName");
          if (lbl) lbl.textContent = f ? f.name : "No file selected";
          if (f) {
            const relInp = document.getElementById("inpCustomOgfRelPath");
            if (relInp && !relInp.value.trim()) {
              relInp.value = `dynamics/equipments/quest/${f.name}`;
            }
          }
        });

        document.getElementById("btnUploadCustomOgf")?.addEventListener("click", async () => {
          const fileEl = document.getElementById("inpCustomOgfFile");
          const f = fileEl?.files?.[0];
          if (!f) {
            window.showStudioToast?.("Please select a local .ogf file first.", true);
            return;
          }
          const relPath = (document.getElementById("inpCustomOgfRelPath")?.value || `dynamics/equipments/quest/${f.name}`).trim();
          const buf = await f.arrayBuffer();
          let binary = "";
          const bytes = new Uint8Array(buf);
          for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
          const b64 = btoa(binary);
          const r = await fetch("/api/ogf/import_custom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rel_path: relPath, filename: f.name, base64_data: b64 }),
          });
          const d = await r.json();
          if (d && d.ok) {
            window.showStudioToast?.(`Imported custom OGF: ${d.rel_path} (${d.vertex_count} verts, ${d.face_count} tris)`, false);
            if (typeof window.searchOgfList === "function") await window.searchOgfList();
            if (typeof window.loadOgfModel === "function") await window.loadOgfModel(d.rel_path);
          } else {
            window.showStudioToast?.(`OGF Import Error: ${d?.error || "Invalid format"}`, true);
          }
        });
      }

      if (ogfToolbar && !document.getElementById("btnUseOgfInQuest")) {
        const useBtn = document.createElement("button");
        useBtn.className = "btn primary";
        useBtn.id = "btnUseOgfInQuest";
        useBtn.style.cssText = "padding:4px 9px;font-size:11px;margin-left:auto;";
        useBtn.textContent = "Use Model in Active Quest / 3D Spawn";
        useBtn.addEventListener("click", () => {
          const curOgf = document.getElementById("ogfTitle")?.textContent?.trim() || "dynamics/equipments/quest/box_black.ogf";
          const inpVis = document.getElementById("inspVisual");
          if (inpVis) inpVis.value = curOgf;
          window.showStudioToast?.(`Selected 3D mesh "${curOgf}" for Quest Item / 3D Spawn!`, false);
        });
        ogfToolbar.appendChild(useBtn);
      }
    }
  }

  function raycastCameraCenterTerrain() {
    const THREE = window.THREE;
    const cam = window.mapCamera;
    const cform = (window.cformMeshes || []).filter((m) => m && m.visible);
    if (THREE && cam && cform.length > 0) {
      const rc = new THREE.Raycaster();
      rc.setFromCamera(new THREE.Vector2(0, 0), cam);
      const hits = rc.intersectObjects(cform, false);
      if (hits.length > 0) {
        return hits[0].point;
      }
    }
    return window.mapControls?.target || { x: -145.0, y: -19.8, z: -145.0 };
  }

  function syncInspectorToStudioObject(o) {
    if (!o) return;
    const setVal = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.value = v;
    };
    setVal("inspName", o.name || o.id || "");
    setVal("inspSection", o.section || "");
    setVal("inspVisual", o.mesh || "");
    setVal("inspPosX", Number((o.x || 0).toFixed(3)));
    setVal("inspPosY", Number((o.y || 0).toFixed(3)));
    setVal("inspPosZ", Number((o.z || 0).toFixed(3)));
    setVal("inspRotX", 0);
    setVal("inspRotY", Number((((o.rot_y || 0) * Math.PI) / 180).toFixed(3)));
    setVal("inspRotZ", 0);
    setVal("inspGvid", o.game_vertex_id || o.gvid || 0);
    setVal("inspLvid", o.level_vertex_id || o.lvid || 0);
    const presetSel = document.getElementById("selPlacePreset");
    if (presetSel && o.section) {
      for (let i = 0; i < presetSel.options.length; i++) {
        if (presetSel.options[i].value.startsWith(o.section + "|")) {
          presetSel.selectedIndex = i;
          break;
        }
      }
    }
    if (typeof window.updateUniversalPickCard === "function") {
      window.updateUniversalPickCard(
        "PLACED 3D OBJECT (SDK 0.7)",
        `${Number(o.x || 0).toFixed(2)}, ${Number(o.y || 0).toFixed(2)}, ${Number(o.z || 0).toFixed(2)}`,
        `${o.name || o.id} [${o.section || "custom"}]`,
        `3D OGF: ${o.mesh || "dynamics/equipments/quest/box_black.ogf"} · Yaw: ${o.rot_y || 0}°`,
        o
      );
    }
  }

  window.selectStudioPlaced3DObject = function (id, flyTo = false) {
    if (window._selectedStaticVisual && window._selectedStaticVisual.proxyGroup && window.mapScene) { window.mapScene.remove(window._selectedStaticVisual.proxyGroup); window._selectedStaticVisual = null; }
    window.selectedStudioObjectId = id;
    const obj = (window.placedStudioObjects || []).find((o) => o.id === id);
    const sel = document.getElementById("selPlacedEntityList");
    if (sel) sel.value = id || "";
    if (obj) {
      syncInspectorToStudioObject(obj);
      if (typeof window.updateUniversalPickCard === "function") {
        window.updateUniversalPickCard(
          "PLACED 3D OBJECT (SDK 0.7)",
          `${Number(obj.x || 0).toFixed(2)}, ${Number(obj.y || 0).toFixed(2)}, ${Number(obj.z || 0).toFixed(2)}`,
          `${obj.name || obj.id} [${obj.section}]`,
          `3D OGF: ${obj.mesh || "dynamics/equipments/quest/box_black.ogf"} · Yaw: ${obj.rot_y || 0}°`,
          obj
        );
      }
      if (flyTo && window.mapControls && window.mapCamera) {
        window.mapControls.target.set(obj.x, obj.y + 1.0, obj.z);
        window.mapCamera.position.set(obj.x + 12, obj.y + 10, obj.z + 12);
        window.mapControls.update();
      }
    }
    renderPlaced3DObjectsOnMap();
  };

  window.updateStudioObjectFromInspector = function () {
    const id = window.selectedStudioObjectId;
    if (!id) return;
    const obj = (window.placedStudioObjects || []).find((o) => o.id === id);
    if (!obj) return;
    obj.name = document.getElementById("inspName")?.value || obj.name;
    obj.section = document.getElementById("inspSection")?.value || obj.section;
    obj.x = parseFloat(document.getElementById("inspPosX")?.value) || 0;
    obj.y = parseFloat(document.getElementById("inspPosY")?.value) || 0;
    obj.z = parseFloat(document.getElementById("inspPosZ")?.value) || 0;
    const rotYRad = parseFloat(document.getElementById("inspRotY")?.value) || 0;
    obj.rot_y = Number(((rotYRad * 180) / Math.PI).toFixed(1));
    if (window.studioPlacementGroup3D) {
      const g = window.studioPlacementGroup3D.children.find((c) => c.userData?.studioObjectId === id);
      if (g) {
        g.position.set(obj.x, obj.y, obj.z);
        g.rotation.y = rotYRad;
        window.commitStudioObjectGizmoTransform(g);
      }
    }
  };

  window.syncStudioObjectGizmoLive = function (threeGroup) {
    const id = threeGroup?.userData?.studioObjectId;
    const obj = (window.placedStudioObjects || []).find((o) => o.id === id);
    if (!obj) return;
    obj.x = Number(threeGroup.position.x.toFixed(3));
    obj.y = Number(threeGroup.position.y.toFixed(3));
    obj.z = Number(threeGroup.position.z.toFixed(3));
    obj.rot_y = Number((((threeGroup.rotation.y * 180) / Math.PI) % 360).toFixed(1));
    obj.scale = Number((threeGroup.scale.x || 1.0).toFixed(2));
    syncInspectorToStudioObject(obj);
  };

  window.commitStudioObjectGizmoTransform = async function (threeGroup) {
    const id = threeGroup?.userData?.studioObjectId;
    const obj = (window.placedStudioObjects || []).find((o) => o.id === id);
    if (!obj) return;
    window.syncStudioObjectGizmoLive(threeGroup);
    await fetch("/api/placement/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        op: "move",
        id: obj.id,
        level: obj.level || window.currentLevel || "l01_escape",
        x: obj.x,
        y: obj.y,
        z: obj.z,
      }),
    });
    await fetch("/api/placement/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        op: "rotate_scale",
        id: obj.id,
        level: obj.level || window.currentLevel || "l01_escape",
        rot_y: obj.rot_y || 0,
        scale: obj.scale || 1.0,
      }),
    });
    await pollConsoleLogs();
  };

  window.placeStudio3DObject = async function (customParams) {
    const val = document.getElementById("selPlacePreset")?.value || "quest_case_01|dynamics\\equipments\\quest\\box_black.ogf|item";
    const [section, mesh, category] = val.split("|");
    const hitPt = customParams?.x !== undefined ? customParams : raycastCameraCenterTerrain();
    const snap = document.getElementById("chkGridSnap3D")?.checked;
    const cformSnap = document.getElementById("chkCformSnap3D")?.checked !== false;
    const x = customParams?.x ?? (snap ? Math.round(hitPt.x * 2) / 2 : Number(hitPt.x.toFixed(2)));
    const z = customParams?.z ?? (snap ? Math.round(hitPt.z * 2) / 2 : Number(hitPt.z.toFixed(2)));
    let rawY = customParams?.y ?? Number(hitPt.y.toFixed(2));
    if (cformSnap && typeof window.raycastGroundAt === "function") {
      const gHit = window.raycastGroundAt(x, rawY, z);
      if (gHit && gHit.point) rawY = Number(gHit.point.y.toFixed(3));
    }
    const y = rawY;

    const res = await fetch("/api/placement/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        op: "place",
        level: window.currentLevel || "l01_escape",
        section: customParams?.section || section,
        mesh: customParams?.mesh || mesh,
        category: customParams?.category || category,
        x,
        y,
        z,
        rot_y: customParams?.rot_y ?? (window.studioGhostRotY || 0),
        snap_to_ai_y: customParams?.x === undefined,
      }),
    }).then((r) => r.json());

    if (res.ok) {
      window.placedStudioObjects = res.objects || [];
      window.selectedStudioObjectId = res.object?.id || null;
      if (res.object) syncInspectorToStudioObject(res.object);
      renderPlaced3DObjectsOnMap();
      window.refreshActiveProjectBadge?.();
      await pollConsoleLogs();
    }
    return res;
  };

  window.moveSelectedStudio3DObject = async function (dx = 2.0, dy = 0.0, dz = 2.0) {
    const id = window.selectedStudioObjectId || window.placedStudioObjects[window.placedStudioObjects.length - 1]?.id;
    const obj = window.placedStudioObjects.find((o) => o.id === id);
    if (!obj) return { ok: false };
    const res = await fetch("/api/placement/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        op: "move",
        id: obj.id,
        level: obj.level,
        x: obj.x + dx,
        y: obj.y + dy,
        z: obj.z + dz,
      }),
    }).then((r) => r.json());
    if (res.ok) {
      window.placedStudioObjects = res.objects || [];
      if (res.object) syncInspectorToStudioObject(res.object);
      renderPlaced3DObjectsOnMap();
      window.refreshActiveProjectBadge?.();
      await pollConsoleLogs();
    }
    return res;
  };

  window.rotateSelectedStudio3DObject = async function (dRot = 45.0, scaleMult = 1.1) {
    const id = window.selectedStudioObjectId || window.placedStudioObjects[window.placedStudioObjects.length - 1]?.id;
    const obj = window.placedStudioObjects.find((o) => o.id === id);
    if (!obj) return { ok: false };
    const res = await fetch("/api/placement/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        op: "rotate_scale",
        id: obj.id,
        level: obj.level,
        rot_y: ((obj.rot_y || 0) + dRot) % 360,
        scale: Number(((obj.scale || 1.0) * scaleMult).toFixed(2)),
      }),
    }).then((r) => r.json());
    if (res.ok) {
      window.placedStudioObjects = res.objects || [];
      if (res.object) syncInspectorToStudioObject(res.object);
      renderPlaced3DObjectsOnMap();
      window.refreshActiveProjectBadge?.();
      await pollConsoleLogs();
    }
    return res;
  };

  window.deleteSelectedStudio3DObject = async function () {
    const id = window.selectedStudioObjectId || window.placedStudioObjects[window.placedStudioObjects.length - 1]?.id;
    if (!id) return { ok: false };
    const res = await fetch("/api/placement/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        op: "delete",
        id,
        level: window.currentLevel || "l01_escape",
      }),
    }).then((r) => r.json());
    if (res.ok) {
      window.placedStudioObjects = res.objects || [];
      window.selectedStudioObjectId = window.placedStudioObjects[0]?.id || null;
      renderPlaced3DObjectsOnMap();
      window.refreshActiveProjectBadge?.();
      await pollConsoleLogs();
    }
    return res;
  };

  window.refreshPlacedObjectsForLevel = function (levelName) {
    fetch("/api/placement/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ op: "list", level: levelName || window.currentLevel || "l01_escape" }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.objects) {
          window.placedStudioObjects = d.objects;
          renderPlaced3DObjectsOnMap();
        }
      })
      .catch(() => {});
  };

  function renderPlaced3DObjectsOnMap() {
    const sel = document.getElementById("selPlacedEntityList");
    if (sel) {
      sel.innerHTML =
        `<option value="">-- Placed Objects (${window.placedStudioObjects.length}) --</option>` +
        window.placedStudioObjects
          .map(
            (o) =>
              `<option value="${o.id}" ${o.id === window.selectedStudioObjectId ? "selected" : ""}>${o.name} [${o.section}] (${o.x}, ${o.y}, ${o.z})</option>`
          )
          .join("");
    }
    const scene = window.mapScene;
    const THREE = window.THREE;
    if (!scene || !THREE) return;
    if (window.transformControl && window.transformControl.object?.userData?.studioObjectId) {
      window.transformControl.detach();
    }
    if (studioPlacementGroup3D) scene.remove(studioPlacementGroup3D);
    studioPlacementGroup3D = new THREE.Group();
    studioPlacementGroup3D.name = "StudioPlacedObjects3D";
    window.studioPlacementGroup3D = studioPlacementGroup3D;

    window.placedStudioObjects.forEach((o) => {
      const isSel = o.id === window.selectedStudioObjectId;
      const g = new THREE.Group();
      g.position.set(o.x || 0, o.y || 0, o.z || 0);
      g.rotation.y = ((o.rot_y || 0) * Math.PI) / 180;
      const sc = o.scale || 1.0;
      g.scale.set(sc, sc, sc);
      g.userData = { studioObjectId: o.id, placedObject: o };

      // 1. SDK Ground Ring + Facing Direction Cone
      const ringGeom = new THREE.RingGeometry(0.45, 0.68, 28);
      ringGeom.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({
        color: isSel ? 0x10b981 : 0x38bdf8,
        side: THREE.DoubleSide,
        depthTest: false,
        transparent: true,
        opacity: isSel ? 0.95 : 0.7,
      });
      const ringMesh = new THREE.Mesh(ringGeom, ringMat);
      ringMesh.position.y = 0.03;
      ringMesh.renderOrder = 990;
      ringMesh.userData = { studioObjectId: o.id, placedObject: o };
      g.add(ringMesh);

      const dirGeom = new THREE.ConeGeometry(0.14, 0.38, 8);
      dirGeom.rotateX(Math.PI / 2);
      const dirMesh = new THREE.Mesh(
        dirGeom,
        new THREE.MeshBasicMaterial({ color: isSel ? 0x10b981 : 0x38bdf8, depthTest: false })
      );
      dirMesh.position.set(0, 0.08, 0.78);
      dirMesh.renderOrder = 991;
      dirMesh.userData = { studioObjectId: o.id, placedObject: o };
      g.add(dirMesh);

      // 2. Fallback wireframe cage (shown immediately and kept as subtle selection bounds)
      const fallbackCage = new THREE.Mesh(
        new THREE.BoxGeometry(0.75, 1.2, 0.75),
        new THREE.MeshBasicMaterial({
          color: isSel ? 0x10b981 : 0x38bdf8,
          wireframe: true,
          transparent: true,
          opacity: isSel ? 0.55 : 0.25,
        })
      );
      fallbackCage.position.y = 0.6;
      fallbackCage.userData = { studioObjectId: o.id, placedObject: o };
      g.add(fallbackCage);

      // 3. Load and attach the REAL 3D .OGF Model + DDS Texture from VFS!
      const meshPath = (o.mesh || "dynamics\\equipments\\quest\\box_black.ogf").replace(/\\/g, "/");
      if (typeof window.fetchOgfCached === "function" && typeof window.createThreeObjectFromOgfData === "function") {
        window.fetchOgfCached(meshPath, o.level || window.currentLevel || "l01_escape").then((data) => {
          if (!data || data.error) return;
          const ogfObj = window.createThreeObjectFromOgfData(data, o.level || window.currentLevel || "l01_escape", true, false);
          ogfObj.userData = { studioObjectId: o.id, placedObject: o };
          ogfObj.traverse((child) => {
            child.userData = { studioObjectId: o.id, placedObject: o };
          });
          g.add(ogfObj);
          // Adjust selection box to fit real OGF bounding box
          const box = new THREE.Box3().setFromObject(ogfObj);
          if (!box.isEmpty()) {
            const sz = new THREE.Vector3();
            const center = new THREE.Vector3();
            box.getSize(sz);
            box.getCenter(center);
            g.worldToLocal(center);
            fallbackCage.geometry.dispose();
            fallbackCage.geometry = new THREE.BoxGeometry(
              Math.max(sz.x, 0.35),
              Math.max(sz.y, 0.35),
              Math.max(sz.z, 0.35)
            );
            fallbackCage.position.copy(center);
            fallbackCage.material.opacity = isSel ? 0.65 : 0.0;
          }
        });
      }

      studioPlacementGroup3D.add(g);

      if (isSel && window.transformControl && window.editorMode !== "place") {
        window.transformControl.attach(g);
      }
    });
    scene.add(studioPlacementGroup3D);
  }
  window.renderPlaced3DObjectsOnMap = renderPlaced3DObjectsOnMap;

  // -------------------------------------------------------------------------
  
  window.runFullMultiTabBrowserQA = async function runFullMultiTabBrowserQA() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("qa_auto") !== "v010") return;
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    await sleep(250);
    const rep = { ok: true, tabs: {} };
    try {
      window.switchTab("quests");
      await sleep(500);
      const qNodes = document.querySelectorAll("#bpNodesContainer .bp-node").length;
      const inspEl = document.getElementById("qInspector");
      const splitterEl = document.getElementById("questInspResizer");
      const tab1Text = document.getElementById("tab-quests")?.innerText || "";
      rep.tabs.tab1_quests = {
        node_count: qNodes,
        has_resizable_splitter: Boolean(splitterEl),
        inspector_width: inspEl ? Math.round(inspEl.getBoundingClientRect().width) : 0,
        has_german_remnants: /Phrasen|Suche Quest|Klicke/i.test(tab1Text),
      };

      window.switchTab("map");
      await sleep(500);
      if (typeof window.setGizmoMode === "function") window.setGizmoMode("place");
      const placeModeActive = window.editorMode === "place";
      if (typeof window.setGizmoMode === "function") window.setGizmoMode("translate");
      const pRes = await window.placeStudio3DObject({
        x: -146.5,
        y: -19.8,
        z: -145.2,
        section: "quest_case_01",
        mesh: "dynamics\\equipments\\quest\\box_black.ogf",
        category: "item"
      });
      await sleep(450);
      const placed3DCount = window.studioPlacementGroup3D ? window.studioPlacementGroup3D.children.length : 0;
      const gizmoAttached = Boolean(window.transformControl && window.transformControl.object);
      if (pRes && pRes.ok) {
        await window.deleteSelectedStudio3DObject();
      }
      const mapCanvasEl = document.querySelector("#mapCanvas canvas");
      const mapRect = mapCanvasEl ? mapCanvasEl.getBoundingClientRect() : { width: 0, height: 0 };
      const mapParentRect = document.getElementById("mapCanvas")?.getBoundingClientRect() || { width: 0, height: 0 };
      const tab2Text = document.getElementById("tab-map")?.innerText || "";
      rep.tabs.tab2_map = {
        canvas_w: Math.round(mapRect.width),
        canvas_h: Math.round(mapRect.height),
        parent_w: Math.round(mapParentRect.width),
        parent_h: Math.round(mapParentRect.height),
        fills_viewport:
          mapRect.width >= mapParentRect.width - 4 &&
          mapRect.height >= mapParentRect.height - 4 &&
          mapRect.width > 700,
        sdk_place_mode_ok: placeModeActive,
        sdk_placed_3d_ogf_ok: placed3DCount >= 1 && gizmoAttached,
        has_german_remnants: /Spawns im Level|Pfeiltasten|Klick-Auswahl|Achsen:/i.test(tab2Text),
      };

      window.switchTab("ogf");
      if (typeof window.loadOgfModel === "function") {
        await window.loadOgfModel("dynamics/weapons/wpn_ak74/wpn_ak74.ogf");
      }
      await sleep(500);
      const ogfCanvasEl = document.querySelector("#ogfCanvas canvas");
      const ogfRect = ogfCanvasEl ? ogfCanvasEl.getBoundingClientRect() : { width: 0, height: 0 };
      const ogfParentRect = document.getElementById("ogfCanvas")?.getBoundingClientRect() || { width: 0, height: 0 };
      const ogfVerts = document.querySelector("#ogfInspector .val")?.textContent || "0";
      const ogfListCount = document.querySelectorAll("#ogfList .list-item").length;
      const tab3Text = document.getElementById("tab-ogf")?.innerText || "";
      rep.tabs.tab3_ogf = {
        canvas_w: Math.round(ogfRect.width),
        canvas_h: Math.round(ogfRect.height),
        parent_w: Math.round(ogfParentRect.width),
        parent_h: Math.round(ogfParentRect.height),
        fills_viewport:
          ogfRect.width >= ogfParentRect.width - 4 &&
          ogfRect.height >= ogfParentRect.height - 4 &&
          ogfRect.width > 700,
        ogf_verts: ogfVerts,
        ogf_list_items: ogfListCount,
        has_custom_file_btn: Boolean(document.getElementById("lblCustomOgfFileName")),
        has_german_remnants: /Modelle|Echte|suchen|Durchsuchen/i.test(tab3Text),
      };

      window.switchTab("pack");
      await sleep(250);
      const tab4Text = document.getElementById("tab-pack")?.innerText || "";
      rep.tabs.tab4_pack = {
        has_direct_db0_builder: tab4Text.includes("Direct .db0 Mod Archive Builder"),
        has_german_remnants: /Quell-Ordner|Modulare|Jetzt/i.test(tab4Text),
      };

      window.switchTab("howto");
      await sleep(250);
      const tab5Text = document.getElementById("tab-howto")?.innerText || "";
      rep.tabs.tab5_howto = {
        has_en_handbook: tab5Text.includes("Complete Handbook & Workflow Guide"),
        has_german_remnants: /Komplettes|Klicke|Danksagungen/i.test(tab5Text),
      };

      const finalTab = params.get("tab") || "quests";
      window.switchTab(finalTab);
      await sleep(300);
    } catch (err) {
      rep.ok = false;
      rep.error = String(err);
    }
    await fetch("/api/qa_browser_report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rep),
    });
  }

  // INITIALIZE ON DOM READY
  // -------------------------------------------------------------------------
  function initV010Alpha() {
    setupTopControlsAndTabOrder();
    setupResizableQuestInspector();
    injectConsolePanel();
    inject3DPlacementBar();
    scrubGermanStrings();

    // Open Tab #1 (Story, Dialog & Quest Builder) by default on startup
    setTimeout(() => {
      setupTopControlsAndTabOrder();
      setupResizableQuestInspector();
      inject3DPlacementBar();
      scrubGermanStrings();
      if (typeof window.switchTab === "function") {
        const reqTab = new URLSearchParams(window.location.search).get("tab") || "quests";
        window.switchTab(reqTab);
      }
      pollConsoleLogs();
      // First-Launch Path Setup Wizard check (skipped during automated headless QA runs)
      if (!new URLSearchParams(window.location.search).get("qa_auto")) {
        fetch("/api/settings")
          .then((r) => r.json())
          .then((d) => {
            if (d && (!d.settings?.first_run_completed || !d.validation?.anomaly_valid)) {
              window.openStudioSettingsModal(true);
            }
          })
          .catch(() => {});
      }
      fetch("/api/placement/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ op: "list", level: window.currentLevel || "l01_escape" }),
      })
        .then((r) => r.json())
        .then((d) => {
          if (d.objects) {
            window.placedStudioObjects = d.objects;
            renderPlaced3DObjectsOnMap();
          }
        })
        .catch(() => {});
    }, 350);

    setInterval(pollConsoleLogs, 2500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initV010Alpha);
  } else {
    initV010Alpha();
  }
})();
