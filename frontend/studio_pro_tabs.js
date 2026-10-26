/* =========================================================================
   ANOMALY STUDIO 1.5.3 — CORE & EXPERIMENTAL WORKSPACES
   ========================================================================= */
(function () {
  "use strict";

  let questsOverview = null;
  let currentGraph = { nodes: [], edges: [], campaign: "" };
  let selectedQuestNode = null;
  let loadscreenTips = [];
  let selectedTip = null;
  let particlesData = { total: 0, categories: [], particles: [] };
  let selectedParticle = null;

  let rulerActive = false;
  let rulerPoints = [];
  let rulerGroup = null;
  let cameraBookmarks = JSON.parse(localStorage.getItem("anomaly_cam_bookmarks_v1") || "[]");

  function get3DScene() { return window.mapScene || (typeof mapScene !== "undefined" ? mapScene : null); }
  function get3DCamera() { return window.mapCamera || (typeof mapCamera !== "undefined" ? mapCamera : null); }
  function get3DControls() { return window.mapControls || (typeof mapControls !== "undefined" ? mapControls : null); }
  function getCurrentLevel() { return window.currentLevelName || (typeof currentLevel !== "undefined" ? currentLevel : "l01_escape"); }

  function initProStudioExtensions() {
    injectStylesheet();
    injectHeaderTabs();
    injectWorkspacePanels();
    inject3DProToolbar();
    injectArmaEdenToolbar();
    injectLandscapeToolbarAndDrawer();
    setupShiftDragBoxSelection();
    handleUrlParamsAndQA();
  }

  function injectStylesheet() {
    if (!document.querySelector('link[href*="studio_responsive.css"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/studio_responsive.css";
      document.head.appendChild(link);
    }
  }

  function injectHeaderTabs() {
    const tabsBar = document.querySelector(".nav-tabs");
    if (!tabsBar || document.getElementById("tabBtnQuests")) return;

    const newTabs = [
      { id: "quests", btnId: "tabBtnQuests", label: "5. Quests & Dialogs" },
      { id: "particles", btnId: "tabBtnParticles", label: "6. Particle Editor" },
      { id: "sdk07", btnId: "tabBtnSdk07", label: "7. Shaders, PPE & Engine Assets" },
      { id: "howto", btnId: "tabBtnHowto", label: "8. Handbook & Shortcuts" },
    ];

    newTabs.forEach((t) => {
      const btn = document.createElement("button");
      btn.className = "nav-btn";
      btn.id = t.btnId;
      btn.dataset.tab = t.id;
      btn.textContent = t.label;
      btn.addEventListener("click", () => {
        if (typeof window.switchTab === "function") window.switchTab(t.id);
        else activateProTab(t.id);
      });
      tabsBar.appendChild(btn);
    });

    // Extend global switchTab so clicking tabs 1..7 switches .workspace.active cleanly
    const origSwitch = window.switchTab;
    window.switchTab = function (tabId) {
      if (typeof origSwitch === "function") {
        try { origSwitch(tabId); } catch (_e) {}
      }
      document.querySelectorAll(".workspace").forEach((el) => el.classList.remove("active"));
      document.querySelectorAll(".nav-btn").forEach((el) => el.classList.remove("active"));
      const target = document.getElementById("tab-" + tabId);
      if (target) target.classList.add("active");
      const allIds = ["map", "ogf", "ltx", "pack", "quests", "particles", "sdk07", "howto"];
      const idx = allIds.indexOf(tabId);
      const btns = document.querySelectorAll(".nav-btn");
      if (idx >= 0 && btns[idx]) btns[idx].classList.add("active");
      if (tabId === "map" && window.mapRenderer && window.mapCamera) {
        const mc = document.getElementById("mapCanvas");
        if (mc) {
          const mw = mc.clientWidth || 960, mh = mc.clientHeight || 640;
          window.mapCamera.aspect = mw / mh;
          window.mapCamera.updateProjectionMatrix();
          window.mapRenderer.setSize(mw, mh, false);
          if (window.mapControls) window.mapControls.update();
          if (window.mapScene) window.mapRenderer.render(window.mapScene, window.mapCamera);
        }
      }
      if (tabId === "quests" && !questsOverview) loadQuestsAndTipsOverview();
      if (tabId === "particles" && (!particlesData.particles || !particlesData.particles.length)) loadParticlesCatalog();
      if (tabId === "sdk07" && typeof window.loadSdk07ParityTab === "function") window.loadSdk07ParityTab();
      window.dispatchEvent(new Event("resize"));
    };
  }

  function activateProTab(tabId) {
    if (typeof window.switchTab === "function") window.switchTab(tabId);
  }

  function injectWorkspacePanels() {
    if (document.getElementById("tab-quests")) return;
    const bodyEl = document.body;
    // =====================================================================
    // TAB 5: QUEST, STORYLINE, DIALOG, STRING-TABLE & LOADSCREEN TIPS EDITOR
    // =====================================================================
    const pQuests = document.createElement("div");
    pQuests.id = "tab-quests";
    pQuests.className = "workspace";
    pQuests.innerHTML = `
      <div class="sidebar" style="width:320px;">
        <div class="search-box">
          <div style="display:flex;gap:4px;margin-bottom:8px;">
            <button class="btn primary" id="qSubTabStory" style="flex:1;padding:6px;font-size:11px;">Quests & Story</button>
            <button class="btn" id="qSubTabDialogs" style="flex:1;padding:6px;font-size:11px;">Dialogs</button>
            <button class="btn" id="qSubTabTips" style="flex:1;padding:6px;font-size:11px;">Loadscreen Tips</button>
          </div>
          <div id="qCampaignBox">
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px;">Campaign / Storyline (Anomaly 1.5.3):</label>
            <select id="qCampaignSelect" class="search-box" style="margin-bottom:6px;"></select>
          </div>
          <input type="text" id="qSearchInput" class="search-box" placeholder="Search quest, title, dialog ID, or tip...">
        </div>
        <div class="list-scroll" id="qItemList"></div>
      </div>

      <div class="viewport-container" style="position:relative;overflow:hidden;background:#090d14;">
        <div class="toolbar" style="justify-content:space-between;flex-wrap:wrap;gap:6px;padding:6px 12px;background:#0b111e;border-bottom:1px solid #1e293b;">
          <div id="qToolbarLeftCluster" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
            <span class="badge" id="qGraphBadge" style="background:#0f172a;border:1px solid #1e3a5f;color:#38bdf8;padding:4px 8px;border-radius:5px;font-size:11px;font-weight:600;">611 Quests | 1,016 Dialogs | 103 Tips</span>
            <button class="btn" id="btnAddQuestNode" style="padding:4px 9px;font-size:11px;border-color:#334155;">+ New Node</button>
            <button class="btn" id="btnAutoLayoutGraph" title="Toggle between Compact S-Curve Flow and Left-to-Right Tree Layout (Undoable with Ctrl+Z)" style="padding:4px 9px;font-size:11px;border-color:#38bdf8;color:#38bdf8;background:rgba(56,189,248,0.1);">Auto-Layout (Tree / Flow)</button>
            <label title="Snap node bubbles to the 24px canvas grid while dragging" style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;border-radius:5px;background:#0f172a;border:1px solid #334155;color:#cbd5e1;font-size:11px;cursor:pointer;white-space:nowrap;">
              <input type="checkbox" id="chkSnapGraphGrid" checked style="margin:0;accent-color:#38bdf8;" />
              <span>Grid Snap (24px)</span>
            </label>
            <button class="btn" id="btnSnapAllNodesToGrid" title="Align all current node bubbles to the 24px grid" style="padding:4px 8px;font-size:11px;border-color:#334155;color:#cbd5e1;">Align to Grid</button>
            <button class="btn" id="btnGraphUndo" title="Undo Graph / Layout Change (Ctrl+Z)" style="padding:4px 8px;font-size:11px;border-color:#334155;color:#cbd5e1;">Undo (0)</button>
            <button class="btn" id="btnGraphRedo" title="Redo Graph / Layout Change (Ctrl+Y)" style="padding:4px 8px;font-size:11px;border-color:#334155;color:#cbd5e1;">Redo (0)</button>
          </div>
          <div id="qToolbarRightCluster" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
            <button class="btn" id="btnOpenQuestLogicGuide" title="Open searchable X-Ray & Anomaly 1.5.3 Quest Logic, Section Fields & Condlist Command Reference" style="padding:4px 9px;font-size:11px;border-color:#a855f7;color:#c084fc;background:rgba(168,85,247,0.12);font-weight:700;">? Quest Logic & Command Guide</button>
            <button class="btn primary" id="btnExportSingleQuestMo2Zip" title="Package ONLY the currently selected quest (+ strings + 3D spawns + MO2 meta.ini) into a ready-to-share Mod Organizer 2 / ModDB .zip file" style="background:#0ea5e9;border-color:#0284c7;color:#082f49;font-weight:700;padding:4px 10px;font-size:11px;">Export Selected Quest (.zip)</button>
            <button class="btn primary" id="btnExportModZip" title="Package all custom quests, dialogs, strings, and 3D spawns into a Mod Organizer 2 / ModDB ready .zip file" style="background:#10b981;border-color:#059669;color:#052e16;font-weight:700;padding:4px 10px;font-size:11px;">Export All Custom (.zip)</button>
          </div>
        </div>

        <!-- UE5-Style Node Canvas with SVG Arrows -->
        <div id="bpViewport" style="flex:1;position:relative;overflow:auto;background-image:radial-gradient(#1e293b 1px, transparent 1px);background-size:24px 24px;">
          <svg id="bpSvgEdges" style="position:absolute;top:0;left:0;width:3600px;height:2800px;pointer-events:none;z-index:2;"></svg>
          <div id="bpNodesContainer" style="position:relative;width:3600px;height:2800px;z-index:5;pointer-events:none;"></div>
        </div>

        <!-- Loadscreen Tips Full Table Overlay (shown when Loadscreen Tips subtab active) -->
        <div id="loadscreenTipsPanel" style="display:none;flex:1;overflow-y:auto;padding:18px;background:#0b0f17;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <div>
              <h3 style="font-size:16px;color:#38bdf8;margin:0;">Ladebildschirm-Texte & Tipps Editor (ui_st_loadscreen.xml)</h3>
              <p style="font-size:12px;color:#94a3b8;margin:4px 0 0;">Search, edit, or add all 103 loadscreen tips (<code>ls_header</code>, <code>ls_tip_1</code> .. <code>ls_tip_100+</code>) directly.</p>
            </div>
            <button class="btn primary" id="btnNewLoadscreenTip">+ New Loadscreen Tip</button>
          </div>
          <div id="loadscreenTipsGrid" style="display:flex;flex-direction:column;gap:8px;"></div>
        </div>
      </div>

      <div class="sidebar-right" style="width:360px;">
        <div class="panel-header" id="qInspectorTitle">Quest, Logic & String Inspector</div>
        <div class="inspector-body" id="qInspectorBody" style="padding:12px;display:flex;flex-direction:column;gap:10px;">
          <div style="color:var(--muted);font-size:12px;">Select a storyline/quest, dialog, or loadscreen tip on the left to edit nodes, transitions, and strings (EN / RU).</div>
        </div>
      </div>
    `;
    bodyEl.appendChild(pQuests);

    // =====================================================================
    // TAB 6: 3D PARTICLE EDITOR (particles.xr — 2,370 Effects)
    // =====================================================================
    const pParticles = document.createElement("div");
    pParticles.id = "tab-particles";
    pParticles.className = "workspace";
    pParticles.innerHTML = `
      <div class="sidebar" style="width:300px;">
        <div class="search-box">
          <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px;">Particle Category (particles.xr):</label>
          <select id="ptCategorySelect" class="search-box" style="margin-bottom:6px;">
            <option value="">All 37 Categories (2,370 Effects)</option>
          </select>
          <input type="text" id="ptSearchInput" class="search-box" placeholder="Search particles (e.g. anomaly2, fire, electro)...">
        </div>
        <div class="list-scroll" id="ptItemList"></div>
      </div>
      <div class="viewport-container" style="position:relative;background:#06090e;">
        <div class="toolbar" style="justify-content:space-between;">
          <span id="ptActiveTitle" style="font-weight:700;color:#38bdf8;font-size:13px;">3D Particle Preview (Live WebGL Emitter)</span>
          <div style="display:flex;gap:6px;">
            <button class="btn" id="btnPtBurst">Test Impulse / Burst</button>
            <button class="btn primary" id="btnPtSave">Save Particle Preset</button>
          </div>
        </div>
        <div id="ptCanvasWrap" style="flex:1;position:relative;display:flex;align-items:center;justify-content:center;">
          <canvas id="ptPreviewCanvas" width="760" height="520" style="width:100%;height:100%;display:block;background:radial-gradient(circle at center, #111927 0%, #06080d 100%);"></canvas>
        </div>
      </div>
      <div class="sidebar-right" style="width:330px;">
        <div class="panel-header">Particle Emitter Parameters</div>
        <div class="inspector-body" style="padding:12px;display:flex;flex-direction:column;gap:10px;">
          <label style="font-size:12px;">Effect Path:<input type="text" id="ptNameField" class="search-box" readonly style="margin-top:4px;"></label>
          <div style="font-size:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;"><span>Max Particles:</span><input type="number" id="ptMaxInput" min="1" max="5000" step="1" value="220" style="width:72px;background:#0b0f17;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:2px 5px;font-size:11px;font-weight:700;text-align:right;"></div>
            <input type="range" id="ptMaxSlider" min="1" max="1000" value="220" style="width:100%;">
          </div>
          <div style="font-size:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;"><span>Emission Rate / sec:</span><input type="number" id="ptRateInput" min="1" max="2000" step="1" value="65" style="width:72px;background:#0b0f17;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:2px 5px;font-size:11px;font-weight:700;text-align:right;"></div>
            <input type="range" id="ptRateSlider" min="1" max="300" value="65" style="width:100%;">
          </div>
          <div style="font-size:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;"><span>Velocity (m/s):</span><input type="number" id="ptSpeedInput" min="0.1" max="100" step="0.1" value="2.4" style="width:72px;background:#0b0f17;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:2px 5px;font-size:11px;font-weight:700;text-align:right;"></div>
            <input type="range" id="ptSpeedSlider" min="0.1" max="20" step="0.1" value="2.4" style="width:100%;">
          </div>
          <div style="font-size:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;"><span>Particle Size:</span><input type="number" id="ptSizeInput" min="0.1" max="100" step="0.1" value="4.5" style="width:72px;background:#0b0f17;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:2px 5px;font-size:11px;font-weight:700;text-align:right;"></div>
            <input type="range" id="ptSizeSlider" min="0.5" max="25" step="0.5" value="4.5" style="width:100%;">
          </div>
          <label style="font-size:12px;">Color / Glow:<input type="color" id="ptColorPicker" value="#38bdf8" style="width:100%;height:34px;margin-top:4px;border:none;background:none;"></label>
          <div id="ptSaveStatus" style="font-size:12px;color:#4ade80;"></div>
        </div>
      </div>
    `;
    bodyEl.appendChild(pParticles);

    // =====================================================================
    // TAB 7: STEP-BY-STEP HOW-TO GUIDE & NEXT STEPS ROADMAP (DE / EN / RU)
    // =====================================================================
    const pHowto = document.createElement("div");
    pHowto.id = "tab-howto";
    pHowto.className = "workspace";
    pHowto.innerHTML = `
      <div style="flex:1;overflow-y:auto;padding:24px 36px;background:#0b0f17;color:#e2e8f0;line-height:1.65;">
        <div style="max-width:1040px;margin:0 auto;">
          <h1 style="color:#38bdf8;font-size:24px;margin-bottom:6px;">S.T.A.L.K.E.R. Anomaly 1.5.3 Studio — Complete Handbook & Workflow Guide (EN / RU)</h1>
          <p style="color:#94a3b8;font-size:13px;margin-bottom:20px;"><b>Open Source (MIT License) · Early Alpha / Tech Demo (<code>v0.1.1-alpha</code>)</b> · Built for <b>S.T.A.L.K.E.R. Anomaly 1.5.3 (64-bit Monolith Engine)</b> · Local execution with direct <code>.db0</code> and Mod Organizer 2 (<code>.zip</code>) export.</p>

          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:24px;">
            <div style="background:#111826;border:1px solid #1f2a3c;border-radius:8px;padding:16px;">
              <h3 style="color:#4ade80;font-size:15px;margin-top:0;">1. 3D Map & Spawn Editor (120 Maps)</h3>
              <ul style="font-size:13px;padding-left:18px;margin:8px 0;">
                <li><b>Camera Controls:</b> Left-click orbit, right-click pan, scroll wheel zoom, or <code>Arrow Keys + PgUp/PgDn</code> for free flight.</li>
                <li><b>Place Object:</b> Pick a <b>Quick-Spawn Preset</b> at the top, click <b>Place Object</b>, and click directly on the 3D terrain (automatic C-level AI node lookup in &lt; 2 ms!).</li>
                <li><b>Multi-Select & Ruler:</b> <code>Shift + Left-Drag</code> draws a marquee selection box; <code>3D Ruler</code> measures distances in meters; <code>Ctrl+Z / Ctrl+Y</code> provides <b>200-step Undo/Redo</b>.</li>
                <li><b>In-Editor Play Mode:</b> Click <b>Play Here (F5)</b> for first-person walkthrough with flashlight (<code>F</code>), Geiger counter & compass.</li>
              </ul>
            </div>

            <div style="background:#111826;border:1px solid #1f2a3c;border-radius:8px;padding:16px;">
              <h3 style="color:#38bdf8;font-size:15px;margin-top:0;">2. Quests, Storylines, Dialogs & Loadscreen Tips</h3>
              <ul style="font-size:13px;padding-left:18px;margin:8px 0;">
                <li>Open Tab <b>1. Story, Dialog & Quest Builder</b>.</li>
                <li>Select a campaign at the top left (e.g. <i>Living Legend</i>, <i>Mortal Sin</i>, <i>Operation Afterglow</i>, or regional quests like <i>Cordon / Sidorovich</i>).</li>
                <li>Click any node in the <b>visual node graph</b>: The right inspector shows the live <b>Quest Title & Description (EN / RU)</b>, preconditions (<code>condlist</code>), rewards (<code>on_complete</code>), and linked dialogs.</li>
                <li>Under <b>Loadscreen Tips</b> you can edit all 103 loadscreen strings (<code>ls_tip_1</code> to <code>ls_tip_100</code>) or add custom tips.</li>
              </ul>
            </div>

            <div style="background:#111826;border:1px solid #1f2a3c;border-radius:8px;padding:16px;">
              <h3 style="color:#f59e0b;font-size:15px;margin-top:0;">3. Direct .db0 Mod Archive Export & Pre-Flight Check</h3>
              <ul style="font-size:13px;padding-left:18px;margin:8px 0;">
                <li>Click <b>Export .db0</b> in the top bar or open Tab <b>4. .db0 Export & Spawn Check</b>.</li>
                <li>The Studio packs all your modified quests, string tables, loadscreen tips, and configs <b>strictly locally</b> into a ready-to-use <code>.db0</code> or <code>.zip</code> archive under <code>exports/</code>.</li>
                <li>The archive contains a valid Anomaly 1.5.3 <code>.db0</code> / <code>gamedata/</code> structure and <code>meta.ini</code> for <b>Mod Organizer 2 (MO2)</b>.</li>
              </ul>
            </div>
          </div>

          <div style="background:#111826;border:1px solid #2b3a55;border-radius:8px;padding:18px;margin-top:16px;">
            <h3 style="color:#facc15;font-size:16px;margin-top:0;">4. Credits & Attribution (CREDITS.md)</h3>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;font-size:13px;">
              <div>
                <b style="color:#38bdf8;">Project & Engineering:</b><br>
                • <b>EternalPain</b> (Project Lead & Architecture for S.T.A.L.K.E.R. Anomaly 1.5.3 Studio)<br>
                • Native C acceleration (<code>libfast_cform</code>), direct <code>.db0</code> VFS reader/packer, 3D level editor, and visual Quest/Dialog builder.
              </div>
              <div>
                <b style="color:#4ade80;">Engine & Game Teams:</b><br>
                • <b>S.T.A.L.K.E.R. Anomaly Team</b> (Anomaly 1.5.3 & 64-bit Monolith Engine)<br>
                • <b>GSC Game World</b> (Original S.T.A.L.K.E.R. Series)<br>
              </div>
            </div>
          </div>

        </div>
      </div>
    `;
    bodyEl.appendChild(pHowto);

    // =====================================================================
    // TAB 7: X-RAY SDK 0.7 SHADERS, POSTPROCESS (.PPE), ACTOR MOTIONS & COMPILERS
    // =====================================================================
    const pSdk07 = document.createElement("div");
    pSdk07.id = "tab-sdk07";
    pSdk07.className = "workspace";
    pSdk07.innerHTML = `
      <div class="sidebar" style="width:350px;">
        <div class="panel-header" style="display:flex;justify-content:space-between;align-items:center;">
          <span>Shaders, PPE & Engine Assets</span>
          <span class="badge" style="background:#f5c400;color:#111315;">Monolith Engine</span>
        </div>
        <div class="search-box" style="display:grid;grid-template-columns:1fr 1fr;gap:5px;border-bottom:1px solid var(--border);padding-bottom:10px;">
          <button class="btn primary" id="sdkSubShaders" onclick="window.switchSdk07Sub('shaders')" style="font-size:11px;padding:6px;">ShaderEditor (397)</button>
          <button class="btn" id="sdkSubPpe" onclick="window.switchSdk07Sub('ppe')" style="font-size:11px;padding:6px;">Postprocess & Env (325)</button>
          <button class="btn" id="sdkSubOmf" onclick="window.switchSdk07Sub('omf')" style="font-size:11px;padding:6px;">Actor Motions (.omf)</button>
          <button class="btn" id="sdkSubDiag" onclick="window.switchSdk07Sub('diag')" style="font-size:11px;padding:6px;">ScriptDebugger & xrLC</button>
        </div>
        <div class="search-box">
          <input type="text" id="sdk07SearchInput" placeholder="Search shader, .ppe, lanim, .omf, material..." oninput="window.renderSdk07List()" />
        </div>
        <div class="item-list" id="sdk07ItemList" style="flex:1;overflow-y:auto;"></div>
      </div>

      <div class="center-view" style="padding:18px;overflow-y:auto;background:#090d14;flex:1;">
        <div id="sdk07MainContent" style="max-width:1180px;margin:0 auto;color:#e2e8f0;">
          <div style="color:#94a3b8;">Loading Engine Asset Index (shaders.xr, shaders_xrlc.xr, gamemtl.xr, lanims.xr, senvironment.xr, .ppe, .omf)...</div>
        </div>
      </div>
    `;
    bodyEl.appendChild(pSdk07);

    // Global Keyboard Shortcuts Modal (Shortcut: H or ?)
    const sModal = document.createElement("div");
    sModal.id = "shortcutsModal";
    sModal.style.cssText = "display:none;position:fixed;inset:0;background:rgba(5,8,15,0.82);z-index:9999;align-items:center;justify-content:center;padding:20px;";
    sModal.innerHTML = `
      <div style="background:#0f172a;border:1.5px solid #38bdf8;border-radius:10px;max-width:760px;width:100%;padding:20px 24px;color:#e2e8f0;box-shadow:0 20px 50px rgba(0,0,0,0.85);">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b;padding-bottom:10px;margin-bottom:14px;">
          <h3 style="margin:0;color:#38bdf8;font-size:16px;">Anomaly 1.5.3 Studio — Keyboard Shortcuts</h3>
          <button class="btn" onclick="window.toggleShortcutsModal()" style="padding:3px 9px;">Close (Esc)</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px 24px;font-size:12px;line-height:1.6;">
          <div>
            <h4 style="margin:0 0 6px 0;color:#f59e0b;">3D Camera & Navigation</h4>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">↑</kbd> <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">↓</kbd> <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">←</kbd> <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">→</kbd> Move camera forward / backward / sideways</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">PgUp</kbd> / <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">PgDn</kbd> Raise / lower camera vertically</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Shift</kbd> + Arrow Keys — Fast camera movement (3x speed)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">F</kbd> Focus camera on selected 3D object</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Home</kbd> Reset camera to full level overview</div>
          </div>
          <div>
            <h4 style="margin:0 0 6px 0;color:#10b981;">3D Object Editing & Direct Terrain Drag</h4>
            <div><b>Hold Left Mouse Button on object + drag:</b> Move directly across the terrain!</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">W</kbd> or <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">1</kbd> Move Mode (3D Gizmo + Direct Terrain Drag)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">E</kbd> or <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">2</kbd> Rotate Mode (3D Rotation Gizmo)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">R</kbd> or <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">3</kbd> Click-Spawn (Click terrain to place new spawn)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">G</kbd> Snap selected object onto terrain ground</div>
          </div>
          <div>
            <h4 style="margin:0 0 6px 0;color:#a855f7;">Editor Actions</h4>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Ctrl + D</kbd> Clone selected spawn (+1.5m offset)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Del / Backspace</kbd> Delete selected spawn</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Ctrl + Z</kbd> / <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Ctrl + Y</kbd> Undo / Redo (up to 200 steps)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Ctrl + S</kbd> Save spawns</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">F5</kbd> Play in Engine (Launch Anomaly 1.5.3 at camera position)</div>
          </div>
          <div>
            <h4 style="margin:0 0 6px 0;color:#38bdf8;">Tools & Viewport</h4>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Q</kbd> Toggle Zone 3D Director (Waypoints, Triggers, Quests)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">L</kbd> Toggle 3D Landscape & Heightmap panel</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">M</kbd> Toggle 3D ruler (distance & elevation measurement)</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">V</kbd> Toggle layer menu | <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Z</kbd> AI-NavMesh | <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">Alt+W</kbd> Wireframe</div>
            <div><kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">H</kbd> or <kbd style="background:#1e293b;padding:2px 6px;border-radius:4px;border:1px solid #475569;">?</kbd> Open/close this shortcut window</div>
          </div>
        </div>
      </div>
    `;
    bodyEl.appendChild(sModal);

    window.toggleShortcutsModal = function () {
      const m = document.getElementById("shortcutsModal");
      if (m) m.style.display = m.style.display === "flex" ? "none" : "flex";
    };


    wireQuestTabEvents();
    wireParticleTabEvents();
  }

  // =========================================================================
  // QUESTS, STORYLINES, DIALOGS & LOADSCREEN TIPS LOGIC
  // =========================================================================
  let activeSubTab = "story"; // "story" | "dialogs" | "tips"

  window.loadQuestsAndTipsOverview = loadQuestsAndTipsOverview;
  let _questsOverviewPromise = null;
  async function loadQuestsAndTipsOverview() {
    if (_questsOverviewPromise) return _questsOverviewPromise;
    _questsOverviewPromise = (async () => {
      try {
        const res = await fetch("/api/quests/overview");
        questsOverview = await res.json();
        loadscreenTips = questsOverview.loadscreen_tips || [];

        const sel = document.getElementById("qCampaignSelect");
        if (sel && questsOverview.campaigns) {
          sel.innerHTML = questsOverview.campaigns
            .map((c) => `<option value="${c.file}">${c.label} (${c.count})</option>`)
            .join("");
          if (questsOverview.campaigns.length && (!currentGraph || !currentGraph.nodes || !currentGraph.nodes.length)) {
            await loadCampaignGraph(questsOverview.campaigns[0].file);
          }
        }
        renderLoadscreenTipsList();
      } catch (e) {
        console.error("Failed to load quests overview:", e);
      }
    })();
    return _questsOverviewPromise;
  }

  async function loadCampaignGraph(fileName) {
    try {
      const res = await fetch("/api/quests/campaign/" + encodeURIComponent(fileName));
      graphUndoStack = [];
      graphRedoStack = [];
      currentLayoutMode = "serpentine";
      currentGraph = await res.json();
      (currentGraph.nodes || []).forEach((n) => {
        n.title_en = n.title_en || n.title_text || n.title || n.id;
        n.descr_en = n.descr_en || n.descr_text || n.subtitle || "";
        n.target_functor = n.target_functor || n.target || "";
      });
      computeHierarchicalGraphLayout(currentGraph.nodes || [], currentGraph.edges || [], currentLayoutMode);
      renderQuestSidebarList();
      renderBlueprintGraph();
      if (
        currentGraph.nodes &&
        currentGraph.nodes.length &&
        (!selectedQuestNode || !currentGraph.nodes.some((n) => n.id === selectedQuestNode.id))
      ) {
        await selectBlueprintNode(currentGraph.nodes[0]);
      }
    } catch (e) {
      console.error("Failed to load campaign graph:", e);
    }
  }

  function renderQuestSidebarList() {
    const listEl = document.getElementById("qItemList");
    const q = (document.getElementById("qSearchInput")?.value || "").toLowerCase();
    if (!listEl) return;

    if (activeSubTab === "story") {
      const nodes = (currentGraph.nodes || []).filter(
        (n) =>
          !q ||
          n.id.toLowerCase().includes(q) ||
          (n.title_en || "").toLowerCase().includes(q) ||
          (n.descr_en || "").toLowerCase().includes(q)
      );
      listEl.innerHTML = nodes
        .map(
          (n) => `
        <div class="list-item" data-nid="${n.id}" style="padding:8px 10px;border-bottom:1px solid var(--border);cursor:pointer;">
          <div style="font-weight:700;font-size:12px;color:#e2e8f0;">${escapeHtml(n.title_en || n.id)}</div>
          <div style="font-size:11px;color:#38bdf8;">[${escapeHtml(n.id)}] · ${escapeHtml(n.giver || "task")}</div>
          <div style="font-size:11px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(n.descr_en || "")}</div>
        </div>`
        )
        .join("");

      listEl.querySelectorAll(".list-item").forEach((el) => {
        el.addEventListener("click", () => {
          const node = (currentGraph.nodes || []).find((x) => x.id === el.dataset.nid);
          if (node) selectBlueprintNode(node);
        });
      });
    } else if (activeSubTab === "dialogs") {
      const dlgs = (questsOverview?.dialogs || []).filter(
        (d) => !q || d.id.toLowerCase().includes(q) || (d.sample_en || "").toLowerCase().includes(q)
      );
      listEl.innerHTML = dlgs
        .map(
          (d) => `
        <div class="list-item" data-did="${d.id}" style="padding:8px 10px;border-bottom:1px solid var(--border);cursor:pointer;">
          <div style="font-weight:700;font-size:12px;color:#c084fc;">${escapeHtml(d.id)} (${d.phrase_count} phrases)</div>
          <div style="font-size:11px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(d.sample_en || d.file)}</div>
        </div>`
        )
        .join("");
      listEl.querySelectorAll(".list-item").forEach((el) => {
        el.addEventListener("click", async () => {
          const res = await fetch("/api/quests/dialog/" + encodeURIComponent(el.dataset.did));
          graphUndoStack = [];
          graphRedoStack = [];
          currentLayoutMode = "serpentine";
          currentGraph = await res.json();
          computeHierarchicalGraphLayout(currentGraph.nodes || [], currentGraph.edges || [], currentLayoutMode);
          selectedQuestNode = (currentGraph.nodes && currentGraph.nodes[0]) || null;
          renderBlueprintGraph();
          if (currentGraph.nodes && currentGraph.nodes[0]) selectBlueprintNode(currentGraph.nodes[0]);
        });
      });
    } else if (activeSubTab === "tips") {
      const tips = loadscreenTips.filter(
        (t) =>
          !q ||
          t.id.toLowerCase().includes(q) ||
          (t.eng || "").toLowerCase().includes(q) ||
          (t.rus || "").toLowerCase().includes(q)
      );
      listEl.innerHTML = tips
        .map(
          (t) => `
        <div class="list-item" data-tid="${t.id}" style="padding:8px 10px;border-bottom:1px solid var(--border);cursor:pointer;">
          <div style="font-weight:700;font-size:12px;color:#4ade80;">${escapeHtml(t.id)}</div>
          <div style="font-size:11px;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(t.eng)}</div>
        </div>`
        )
        .join("");
      listEl.querySelectorAll(".list-item").forEach((el) => {
        el.addEventListener("click", () => {
          const tip = loadscreenTips.find((x) => x.id === el.dataset.tid);
          if (tip) inspectLoadscreenTip(tip);
        });
      });
    }
  }


  let graphUndoStack = [];
  let graphRedoStack = [];
  let currentLayoutMode = "serpentine"; // "serpentine" (screen-fit S-curve) | "tree" (full L->R tree)
  const GRAPH_GRID_SIZE = 24;

  function snapCoordToGrid(val) {
    const snapOn = document.getElementById("chkSnapGraphGrid")?.checked !== false;
    if (!snapOn) return Math.round(val);
    return Math.max(GRAPH_GRID_SIZE, Math.round(val / GRAPH_GRID_SIZE) * GRAPH_GRID_SIZE);
  }

  function syncGraphUndoButtons() {
    const uBtn = document.getElementById("btnGraphUndo");
    const rBtn = document.getElementById("btnGraphRedo");
    if (uBtn) {
      uBtn.textContent = `Undo (${graphUndoStack.length})`;
      uBtn.style.borderColor = graphUndoStack.length ? "#38bdf8" : "#334155";
      uBtn.style.color = graphUndoStack.length ? "#38bdf8" : "#94a3b8";
    }
    if (rBtn) {
      rBtn.textContent = `Redo (${graphRedoStack.length})`;
      rBtn.style.borderColor = graphRedoStack.length ? "#38bdf8" : "#334155";
      rBtn.style.color = graphRedoStack.length ? "#38bdf8" : "#94a3b8";
    }
    const topU = document.getElementById("btnV010Undo");
    const topR = document.getElementById("btnV010Redo");
    if (topU && document.getElementById("tab-quests")?.classList.contains("active")) {
      topU.textContent = graphUndoStack.length ? `Undo (${graphUndoStack.length})` : "Undo (Ctrl+Z)";
    }
    if (topR && document.getElementById("tab-quests")?.classList.contains("active")) {
      topR.textContent = graphRedoStack.length ? `Redo (${graphRedoStack.length})` : "Redo (Ctrl+Y)";
    }
  }

  function snapshotCurrentGraph(actionLabel) {
    return JSON.stringify({
      action: actionLabel || "Graph edit",
      layoutMode: currentLayoutMode,
      nodes: (currentGraph.nodes || []).map((n) => ({ ...n })),
      edges: (currentGraph.edges || []).map((e) => ({ ...e })),
      selectedId: selectedQuestNode ? selectedQuestNode.id : null,
    });
  }

  function pushGraphUndoState(actionLabel = "Graph edit") {
    try {
      const snap = snapshotCurrentGraph(actionLabel);
      if (graphUndoStack.length > 0) {
        const prevObj = JSON.parse(graphUndoStack[graphUndoStack.length - 1]);
        const curObj = JSON.parse(snap);
        if (JSON.stringify(prevObj.nodes) === JSON.stringify(curObj.nodes) && JSON.stringify(prevObj.edges) === JSON.stringify(curObj.edges)) {
          return;
        }
      }
      graphUndoStack.push(snap);
      if (graphUndoStack.length > 100) graphUndoStack.shift();
      graphRedoStack = [];
      syncGraphUndoButtons();
    } catch (e) {}
  }


  window.validateCurrentStudioGraph = async function () {
    const res = await fetch("/api/quests/validate_graph", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: (currentGraph && (currentGraph.id || currentGraph.campaign)) || "active_graph",
        nodes: (currentGraph && currentGraph.nodes) || [],
        edges: (currentGraph && currentGraph.edges) || [],
      }),
    });
    return await res.json();
  };

  window.undoQuestOrDialogGraph = function () {
    if (!graphUndoStack.length) return false;
    try {
      graphRedoStack.push(snapshotCurrentGraph("Redo step"));
      const prev = JSON.parse(graphUndoStack.pop());
      currentLayoutMode = prev.layoutMode || currentLayoutMode;
      currentGraph.nodes = prev.nodes || [];
      currentGraph.edges = prev.edges || [];
      selectedQuestNode = (currentGraph.nodes || []).find((x) => x.id === prev.selectedId) || currentGraph.nodes[0] || null;
      renderBlueprintGraph();
      if (selectedQuestNode) selectBlueprintNode(selectedQuestNode);
      syncGraphUndoButtons();
      (window.showStudioToast || console.log)(`Undo: ${prev.action || "Graph step"} (${graphUndoStack.length} left)`, false);
      fetch("/api/console/log", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ level: "info", category: "graph", message_en: `Undo Graph: ${prev.action || "step"} (${graphUndoStack.length} remaining)`, message_ru: `Отмена (Граф): ${prev.action || "шаг"}` }) }).catch(() => {});
      return true;
    } catch (e) {
      return false;
    }
  };

  window.redoQuestOrDialogGraph = function () {
    if (!graphRedoStack.length) return false;
    try {
      graphUndoStack.push(snapshotCurrentGraph("Undo step"));
      const nxt = JSON.parse(graphRedoStack.pop());
      currentLayoutMode = nxt.layoutMode || currentLayoutMode;
      currentGraph.nodes = nxt.nodes || [];
      currentGraph.edges = nxt.edges || [];
      selectedQuestNode = (currentGraph.nodes || []).find((x) => x.id === nxt.selectedId) || currentGraph.nodes[0] || null;
      renderBlueprintGraph();
      if (selectedQuestNode) selectBlueprintNode(selectedQuestNode);
      syncGraphUndoButtons();
      (window.showStudioToast || console.log)(`Redo: ${nxt.action || "Graph step"}`, false);
      return true;
    } catch (e) {
      return false;
    }
  };

  function computeHierarchicalGraphLayout(nodes, edges, mode = "serpentine") {
    if (!nodes || !nodes.length) return;
    const xStart = 48;
    const yStart = 48;
    const xStep = 312; // 13 * 24px grid (card width is 264px -> 48px horizontal gap)
    const yStep = 168; // 7 * 24px grid (generous vertical spacing so cards never crowd)

    const nodeById = {};
    const outAdj = {};
    const inAdj = {};
    const undirAdj = {};
    nodes.forEach((n) => {
      nodeById[n.id] = n;
      outAdj[n.id] = [];
      inAdj[n.id] = [];
      undirAdj[n.id] = new Set();
    });

    const validEdges = [];
    (edges || []).forEach((e) => {
      if (nodeById[e.from] && nodeById[e.to] && e.from !== e.to) {
        if (!outAdj[e.from].includes(e.to)) outAdj[e.from].push(e.to);
        if (!inAdj[e.to].includes(e.from)) inAdj[e.to].push(e.from);
        undirAdj[e.from].add(e.to);
        undirAdj[e.to].add(e.from);
        validEdges.push(e);
      }
    });

    // Separate nodes into:
    //  (A) Connected multi-node components (Quest Chains / Dialog Trees)
    //  (B) Standalone single nodes (unconnected side tasks)
    const visited = new Set();
    const chainComponents = [];
    const standaloneNodes = [];

    nodes.forEach((n) => {
      if (visited.has(n.id)) return;
      const comp = [];
      const q = [n.id];
      visited.add(n.id);
      while (q.length) {
        const cur = q.shift();
        comp.push(nodeById[cur]);
        undirAdj[cur].forEach((nb) => {
          if (!visited.has(nb)) {
            visited.add(nb);
            q.push(nb);
          }
        });
      }
      if (comp.length > 1) {
        chainComponents.push(comp);
      } else {
        standaloneNodes.push(comp[0]);
      }
    });

    // Sort chain components so largest / main storyline chains appear at the top
    chainComponents.sort((a, b) => b.length - a.length);

    let currentTopY = yStart;
    const maxColsPerRow = mode === "tree" ? 6 : 4;

    // Layout each connected Quest Chain / Dialog Tree cleanly from Left (Root) -> Right (Steps)
    chainComponents.forEach((comp) => {
      const compSet = new Set(comp.map((x) => x.id));
      let roots = comp.filter(
        (x) => x.id === "phr_0" || x.id === "0" || inAdj[x.id].filter((p) => compSet.has(p)).length === 0
      );
      if (!roots.length) roots = [comp[0]];

      const depth = {};
      const bfs = [];
      roots.forEach((r) => {
        depth[r.id] = 0;
        bfs.push(r.id);
      });
      let head = 0;
      while (head < bfs.length) {
        const u = bfs[head++];
        const d = depth[u];
        (outAdj[u] || []).forEach((v) => {
          if (!compSet.has(v)) return;
          if (depth[v] === undefined) {
            depth[v] = d + 1;
            bfs.push(v);
          }
        });
      }
      // Any remaining cycle nodes in this component
      comp.forEach((x) => {
        if (depth[x.id] === undefined) depth[x.id] = 0;
      });

      const cols = {};
      comp.forEach((x) => {
        const d = depth[x.id];
        x.depth_col = d;
        if (!cols[d]) cols[d] = [];
        cols[d].push(x);
      });

      const colKeys = Object.keys(cols).map(Number).sort((a, b) => a - b);
      for (let bandStart = 0; bandStart < colKeys.length; bandStart += maxColsPerRow) {
        const bandCols = colKeys.slice(bandStart, bandStart + maxColsPerRow);
        const maxRows = Math.max(1, ...bandCols.map((d) => cols[d].length));
        const bandH = maxRows * yStep;
        bandCols.forEach((d, cIdx) => {
          const colNodes = cols[d];
          const colH = colNodes.length * yStep;
          const topOff = currentTopY + Math.round((bandH - colH) / 2);
          colNodes.forEach((nodeObj, rIdx) => {
            nodeObj.x = snapCoordToGrid(xStart + cIdx * xStep);
            nodeObj.y = snapCoordToGrid(topOff + rIdx * yStep);
          });
        });
        currentTopY = snapCoordToGrid(currentTopY + bandH + 48);
      }
      currentTopY = snapCoordToGrid(currentTopY + 24);
    });

    // Layout standalone (unconnected) tasks in a clean grid below connected chains
    if (standaloneNodes.length > 0) {
      const gridCols = mode === "tree" ? 4 : 3;
      standaloneNodes.forEach((n, idx) => {
        n.depth_col = idx % gridCols;
        n.x = snapCoordToGrid(xStart + (idx % gridCols) * xStep);
        n.y = snapCoordToGrid(currentTopY + Math.floor(idx / gridCols) * yStep);
      });
    }
  }
  window.computeHierarchicalGraphLayout = computeHierarchicalGraphLayout;

  let pendingWireFromId = null;
  let wireDragState = null; // { nodeId, dir: 'out'|'in', startClientX, startClientY, curX, curY, moved, hoveredTargetId, twoClick }
  let lastConnectedEdge = null; // { from, to }
  let activeNodeMap = {};

  function getCanvasCoordsFromClient(clientX, clientY) {
    const svg = document.getElementById("bpSvgEdges");
    const vp = document.getElementById("bpViewport");
    if (svg) {
      const r = svg.getBoundingClientRect();
      return {
        x: Math.max(0, Math.round(clientX - r.left)),
        y: Math.max(0, Math.round(clientY - r.top)),
      };
    }
    if (vp) {
      const r = vp.getBoundingClientRect();
      return {
        x: Math.max(0, Math.round(clientX - r.left + vp.scrollLeft)),
        y: Math.max(0, Math.round(clientY - r.top + vp.scrollTop)),
      };
    }
    return { x: clientX, y: clientY };
  }

  function findTargetNodeForWire(clientX, clientY, canvasX, canvasY, sourceNodeId, sourceDir) {
    // 1. Check DOM element directly under cursor first
    const elUnder = document.elementFromPoint(clientX, clientY);
    if (elUnder) {
      const pinIn = elUnder.closest(".bp-pin-hit-in");
      const pinOut = elUnder.closest(".bp-pin-hit-out");
      const nodeCard = elUnder.closest(".bp-node");
      if (pinIn && pinIn.dataset.nid && pinIn.dataset.nid !== sourceNodeId) {
        return pinIn.dataset.nid;
      }
      if (pinOut && pinOut.dataset.nid && pinOut.dataset.nid !== sourceNodeId) {
        return pinOut.dataset.nid;
      }
      if (nodeCard && nodeCard.dataset.nid && nodeCard.dataset.nid !== sourceNodeId) {
        return nodeCard.dataset.nid;
      }
    }
    // 2. Magnetic proximity check (within 32px of target pin or inside target node bounding box)
    const nodes = currentGraph.nodes || [];
    let bestId = null;
    let bestDist = 36;
    for (const n of nodes) {
      if (!n || n.id === sourceNodeId) continue;
      const nx = typeof n.x === "number" ? n.x : 48;
      const ny = typeof n.y === "number" ? n.y : 48;
      // Target pin coordinates: IN pin is at (nx + 18, ny + 84), OUT pin is at (nx + 246, ny + 84)
      const targetPinX = sourceDir === "out" ? nx + 18 : nx + 246;
      const targetPinY = ny + 84;
      const dPin = Math.hypot(canvasX - targetPinX, canvasY - targetPinY);
      if (dPin < bestDist) {
        bestDist = dPin;
        bestId = n.id;
      } else if (canvasX >= nx - 8 && canvasX <= nx + 272 && canvasY >= ny - 8 && canvasY <= ny + 114) {
        if (!bestId) bestId = n.id;
      }
    }
    return bestId;
  }

  function updateWireVisualHighlights() {
    const activeSrcId = wireDragState ? wireDragState.nodeId : null;
    const activeDir = wireDragState ? wireDragState.dir : "out";
    const hoveredId = wireDragState ? wireDragState.hoveredTargetId : null;

    document.querySelectorAll("#bpNodesContainer .bp-node").forEach((nodeEl) => {
      const nid = nodeEl.dataset.nid;
      const isSelected = selectedQuestNode && selectedQuestNode.id === nid;
      const isHoveredTarget = Boolean(activeSrcId && hoveredId === nid && nid !== activeSrcId);
      const isSource = activeSrcId === nid;

      if (isHoveredTarget) {
        nodeEl.style.borderColor = "#10b981";
        nodeEl.style.boxShadow = "0 0 0 3px rgba(16,185,129,0.42), 0 8px 20px rgba(0,0,0,0.65)";
      } else if (isSource) {
        nodeEl.style.borderColor = "#38bdf8";
        nodeEl.style.boxShadow = "0 0 0 2px rgba(56,189,248,0.45), 0 8px 20px rgba(0,0,0,0.6)";
      } else {
        nodeEl.style.borderColor = isSelected ? "#38bdf8" : "#1e293b";
        nodeEl.style.boxShadow = isSelected
          ? "0 0 0 2px rgba(56,189,248,0.28), 0 8px 20px rgba(0,0,0,0.6)"
          : "0 4px 12px rgba(0,0,0,0.45)";
      }

      const inPin = nodeEl.querySelector(".bp-pin-hit-in");
      const outPin = nodeEl.querySelector(".bp-pin-hit-out");

      if (inPin) {
        const highlightIn = (activeSrcId && activeDir === "out" && nid !== activeSrcId) || (isSource && activeDir === "in");
        const snapIn = isHoveredTarget && activeDir === "out";
        inPin.style.borderColor = snapIn ? "#10b981" : highlightIn ? "#4ade80" : "#334155";
        inPin.style.background = snapIn ? "rgba(16,185,129,0.35)" : highlightIn ? "rgba(74,222,128,0.18)" : "rgba(255,255,255,0.03)";
        inPin.style.color = highlightIn ? "#4ade80" : "#94a3b8";
      }
      if (outPin) {
        const highlightOut = (isSource && activeDir === "out") || (activeSrcId && activeDir === "in" && nid !== activeSrcId);
        const snapOut = isHoveredTarget && activeDir === "in";
        outPin.style.borderColor = snapOut ? "#10b981" : highlightOut ? "#38bdf8" : "#334155";
        outPin.style.background = snapOut ? "rgba(16,185,129,0.35)" : highlightOut ? "rgba(56,189,248,0.28)" : "rgba(255,255,255,0.03)";
        outPin.style.color = highlightOut ? "#38bdf8" : "#94a3b8";
      }
    });
  }

  function clearActiveWireDrag() {
    if (!wireDragState && !pendingWireFromId) return;
    if (wireDragState && wireDragState._onMove) {
      window.removeEventListener("mousemove", wireDragState._onMove);
    }
    if (wireDragState && wireDragState._onUp) {
      window.removeEventListener("mouseup", wireDragState._onUp);
    }
    wireDragState = null;
    pendingWireFromId = null;
    updateWireVisualHighlights();
    drawSvgEdges(activeNodeMap);
  }

  function startWireConnectionGesture(nodeId, dir, ev) {
    ev.stopPropagation();
    ev.preventDefault();

    // If already in 2-click mode and user clicks a second node/pin:
    if (wireDragState && wireDragState.nodeId) {
      if (wireDragState.nodeId === nodeId) {
        clearActiveWireDrag();
        return;
      }
      const fromId = wireDragState.dir === "out" ? wireDragState.nodeId : nodeId;
      const toId = wireDragState.dir === "out" ? nodeId : wireDragState.nodeId;
      clearActiveWireDrag();
      connectBlueprintNodes(fromId, toId);
      return;
    }

    const pt = getCanvasCoordsFromClient(ev.clientX, ev.clientY);
    pendingWireFromId = dir === "out" ? nodeId : null;
    wireDragState = {
      nodeId,
      dir,
      startClientX: ev.clientX,
      startClientY: ev.clientY,
      curX: pt.x,
      curY: pt.y,
      moved: false,
      hoveredTargetId: null,
      twoClick: false,
      _onMove: null,
      _onUp: null,
    };

    const onMove = (me) => {
      if (!wireDragState) return;
      const dist = Math.hypot(me.clientX - wireDragState.startClientX, me.clientY - wireDragState.startClientY);
      if (dist > 4) wireDragState.moved = true;
      const cur = getCanvasCoordsFromClient(me.clientX, me.clientY);
      wireDragState.curX = cur.x;
      wireDragState.curY = cur.y;
      wireDragState.hoveredTargetId = findTargetNodeForWire(
        me.clientX,
        me.clientY,
        cur.x,
        cur.y,
        wireDragState.nodeId,
        wireDragState.dir
      );
      updateWireVisualHighlights();
      drawSvgEdges(activeNodeMap);
    };

    const onUp = (ue) => {
      if (!wireDragState) return;
      const cur = getCanvasCoordsFromClient(ue.clientX, ue.clientY);
      const targetId =
        findTargetNodeForWire(ue.clientX, ue.clientY, cur.x, cur.y, wireDragState.nodeId, wireDragState.dir) ||
        wireDragState.hoveredTargetId;

      if (targetId && targetId !== wireDragState.nodeId) {
        const fromId = wireDragState.dir === "out" ? wireDragState.nodeId : targetId;
        const toId = wireDragState.dir === "out" ? targetId : wireDragState.nodeId;
        clearActiveWireDrag();
        connectBlueprintNodes(fromId, toId);
        return;
      }

      // If user clicked and released on the starting pin without dragging (>5px), enter 2-Click Mode!
      if (!wireDragState.moved && !wireDragState.twoClick) {
        wireDragState.twoClick = true;
        window.removeEventListener("mouseup", onUp);
        wireDragState._onUp = null;
        updateWireVisualHighlights();
        drawSvgEdges(activeNodeMap);
        return;
      }

      // Otherwise user dragged and dropped onto empty space -> cancel wire cleanly
      clearActiveWireDrag();
    };

    wireDragState._onMove = onMove;
    wireDragState._onUp = onUp;
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    updateWireVisualHighlights();
    drawSvgEdges(activeNodeMap);
  }

  window.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && (wireDragState || pendingWireFromId)) {
      clearActiveWireDrag();
    }
  });

  window.connectBlueprintNodes = connectBlueprintNodes;
  window.disconnectBlueprintEdge = disconnectBlueprintEdge;

  function connectBlueprintNodes(fromId, toId) {
    if (!fromId || !toId || fromId === toId) return false;
    pushGraphUndoState(`Connect ${fromId} -> ${toId}`);
    currentGraph.edges = currentGraph.edges || [];
    const exists = currentGraph.edges.some((e) => e.from === fromId && e.to === toId);
    if (!exists) {
      currentGraph.edges.push({ from: fromId, to: toId });
    }
    lastConnectedEdge = { from: fromId, to: toId };
    const nodes = currentGraph.nodes || [];
    const srcNode = nodes.find((x) => x.id === fromId);
    const dstNode = nodes.find((x) => x.id === toId);
    const isDialog = activeSubTab === "dialogs" || String(fromId).startsWith("phr_");
    if (!isDialog) {
      if (srcNode) {
        const doneToken = `+${fromId}_done`;
        if (!String(srcNode.on_complete || "").includes(doneToken)) {
          srcNode.on_complete = (String(srcNode.on_complete || "").trim() + " " + doneToken).trim();
        }
        srcNode.next_quest_id = toId;
      }
      if (dstNode) {
        const reqToken = `{+${fromId}_done}`;
        if (!String(dstNode.cond_0 || "").includes(`+${fromId}_done`)) {
          dstNode.cond_0 = `${reqToken} ${dstNode.cond_0 || "complete"}`.trim();
        }
        dstNode.prev_quest_id = fromId;
      }
    }
    clearActiveWireDrag();
    renderBlueprintGraph();
    if (selectedQuestNode) selectBlueprintNode(selectedQuestNode);
    const msg = exists
      ? `Link "${fromId}" (OUT) -> "${toId}" (IN) active`
      : `Connected "${fromId}" (OUT) -> "${toId}" (IN)`;
    (window.showStudioToast || console.log)(msg, false);
    fetch("/api/console_logs/append", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        level: "INFO",
        category: "graph",
        msg_en: msg,
        msg_ru: `Связь узлов: "${fromId}" (OUT) -> "${toId}" (IN)`,
      }),
    }).catch(() => {});
    return true;
  }

  function disconnectBlueprintEdge(fromId, toId) {
    if (!fromId || !toId) return false;
    const beforeLen = (currentGraph.edges || []).length;
    if (!currentGraph.edges || !currentGraph.edges.some((e) => e.from === fromId && e.to === toId)) {
      return false;
    }
    pushGraphUndoState(`Disconnect ${fromId} -> ${toId}`);
    currentGraph.edges = (currentGraph.edges || []).filter((e) => !(e.from === fromId && e.to === toId));
    if (lastConnectedEdge && lastConnectedEdge.from === fromId && lastConnectedEdge.to === toId) {
      lastConnectedEdge = null;
    }
    renderBlueprintGraph();
    if (selectedQuestNode) selectBlueprintNode(selectedQuestNode);
    const afterLen = currentGraph.edges.length;
    if (afterLen < beforeLen) {
      (window.showStudioToast || console.log)(`Disconnected "${fromId}" -> "${toId}"`, false);
      fetch("/api/console_logs/append", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          level: "INFO",
          category: "graph",
          msg_en: `Disconnected "${fromId}" -> "${toId}"`,
          msg_ru: `Удалена связь "${fromId}" -> "${toId}"`,
        }),
      }).catch(() => {});
    }
    return true;
  }

  function renderBlueprintGraph() {
    const container = document.getElementById("bpNodesContainer");
    const svg = document.getElementById("bpSvgEdges");
    const vp = document.getElementById("bpViewport");
    if (!container || !svg) return;

    container.style.pointerEvents = "none";
    if (vp && !vp._wireBgBound) {
      vp._wireBgBound = true;
      vp.addEventListener("mousedown", (ev) => {
        if (ev.target === vp || ev.target === svg || ev.target === container) {
          if (wireDragState || pendingWireFromId) {
            clearActiveWireDrag();
          }
        }
      });
    }

    container.innerHTML = "";
    const nodes = currentGraph.nodes || [];
    const nodeMap = {};
    activeNodeMap = nodeMap;

    nodes.forEach((n, idx) => {
      if (typeof n.x !== "number") n.x = 48 + (idx % 3) * 312;
      if (typeof n.y !== "number") n.y = 48 + Math.floor(idx / 3) * 144;
      nodeMap[n.id] = n;

      const isSelected = selectedQuestNode && selectedQuestNode.id === n.id;
      const div = document.createElement("div");
      div.className = "bp-node" + (isSelected ? " selected" : "");
      div.style.cssText = `left:${n.x}px;top:${n.y}px;width:264px;border-radius:6px;background:#0f172a;border:1.5px solid ${isSelected ? "#38bdf8" : "#1e293b"};box-shadow:${isSelected ? "0 0 0 2px rgba(56,189,248,0.28), 0 8px 20px rgba(0,0,0,0.6)" : "0 4px 12px rgba(0,0,0,0.45)"};overflow:hidden;position:absolute;z-index:${isSelected ? 35 : 10};user-select:none;pointer-events:auto;transition:box-shadow 0.12s, border-color 0.12s;`;
      div.dataset.nid = n.id;

      const isDialogNode = activeSubTab === "dialogs" || String(n.id).startsWith("phr_");
      const depthCol = typeof n.depth_col === "number" ? n.depth_col : idx;
      const rawTextEn = (n.descr_text || n.descr_en || n.text_en || n.title_text || "").trim();
      const rawTextRu = (n.descr_ru || n.title_ru || "").trim();
      const displayBody = window.currentLang === "ru" ? (rawTextRu || rawTextEn) : (rawTextEn || rawTextRu);

      let hdrBg = "linear-gradient(90deg,#0f2942,#0f172a)";
      let hdrBorder = "#0284c7";
      let badgeLabel = `Task #${idx + 1}`;
      let headerTitle = (window.currentLang === "ru" ? (n.title_ru || n.title || n.title_text) : (n.title_en || n.title_text || n.title)) || n.id;

      if (isDialogNode) {
        const phrNum = String(n.id).replace(/^phr_/, "");
        const isEntry = phrNum === "0";
        const isActor = isEntry || depthCol % 2 === 1;
        if (isEntry) {
          hdrBg = "linear-gradient(90deg,#115e59,#0f172a)";
          hdrBorder = "#14b8a6";
          badgeLabel = "Entry";
          headerTitle = `Phrase #0 (Start)`;
        } else if (isActor) {
          hdrBg = "linear-gradient(90deg,#064e3b,#0f172a)";
          hdrBorder = "#10b981";
          badgeLabel = "Actor";
          headerTitle = `Phrase #${phrNum}`;
        } else {
          hdrBg = "linear-gradient(90deg,#312e81,#0f172a)";
          hdrBorder = "#6366f1";
          badgeLabel = "NPC";
          headerTitle = `Phrase #${phrNum}`;
        }
      } else if (n.storyline || (n.id && n.id.includes("lttz"))) {
        hdrBg = "linear-gradient(90deg,#3b0764,#0f172a)";
        hdrBorder = "#a855f7";
        badgeLabel = `Story #${idx + 1}`;
      }

      const bodyTextFormatted =
        displayBody && displayBody !== n.title_id
          ? escapeHtml(displayBody.slice(0, 135)) + (displayBody.length > 135 ? "…" : "")
          : `<span style="color:#64748b;font-style:italic;">[Dialog Entry / Condition Gate]</span>`;

      div.innerHTML = `
        <div class="bp-node-header" style="background:${hdrBg};border-left:3px solid ${hdrBorder};padding:6px 10px;display:flex;align-items:center;justify-content:space-between;gap:6px;border-bottom:1px solid rgba(255,255,255,0.08);cursor:grab;">
          <span style="font-size:11.5px;font-weight:700;color:#f8fafc;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(headerTitle)}</span>
          <span style="font-size:10px;font-weight:600;padding:1px 6px;border-radius:4px;background:rgba(0,0,0,0.4);color:#cbd5e1;white-space:nowrap;">${badgeLabel}</span>
        </div>
        <div class="bp-node-body" style="padding:8px 10px;display:flex;flex-direction:column;gap:6px;">
          <div style="font-size:11.5px;line-height:1.38;color:#e2e8f0;min-height:32px;max-height:50px;overflow:hidden;">${bodyTextFormatted}</div>
          <div class="bp-pin-row" style="display:flex;align-items:center;justify-content:space-between;padding-top:4px;border-top:1px solid #1e293b;user-select:none;">
            <span class="bp-pin-hit-in" data-nid="${escapeHtml(n.id)}" title="Drag or click IN to connect incoming link (Right-click to disconnect incoming)" style="cursor:crosshair;font-size:10px;font-weight:700;color:#94a3b8;padding:3px 8px;border-radius:4px;background:rgba(255,255,255,0.03);border:1px solid #334155;display:inline-flex;align-items:center;gap:4px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#4ade80;"></span>IN
            </span>
            <span style="font-size:10px;color:#64748b;font-family:monospace;max-width:116px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(n.id)}">${escapeHtml(n.id)} (${n.x},${n.y})</span>
            <span class="bp-pin-hit-out" data-nid="${escapeHtml(n.id)}" title="Drag or click OUT to another node's IN (Right-click to disconnect outgoing)" style="cursor:crosshair;font-size:10px;font-weight:700;color:#94a3b8;padding:3px 8px;border-radius:4px;background:rgba(255,255,255,0.03);border:1px solid #334155;display:inline-flex;align-items:center;gap:4px;">
              OUT<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#38bdf8;"></span>
            </span>
          </div>
        </div>
      `;

      const outPin = div.querySelector(".bp-pin-hit-out");
      const inPin = div.querySelector(".bp-pin-hit-in");

      // Hold-and-drag OR 2-click starting from OUT pin
      outPin?.addEventListener("mousedown", (ev) => {
        if (ev.button !== 0) return;
        startWireConnectionGesture(n.id, "out", ev);
      });

      // Right-click on OUT pin disconnects all outgoing links from this node
      outPin?.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const outs = (currentGraph.edges || []).filter((e) => e.from === n.id);
        if (outs.length) {
          pushGraphUndoState(`Disconnect outgoing from ${n.id}`);
          currentGraph.edges = (currentGraph.edges || []).filter((e) => e.from !== n.id);
          renderBlueprintGraph();
          if (selectedQuestNode) selectBlueprintNode(selectedQuestNode);
          (window.showStudioToast || console.log)(`Removed ${outs.length} outgoing link(s) from "${n.id}"`, false);
        }
      });

      // Hold-and-drag (reverse) OR 2-click starting/finishing on IN pin
      inPin?.addEventListener("mousedown", (ev) => {
        if (ev.button !== 0) return;
        startWireConnectionGesture(n.id, "in", ev);
      });

      // Right-click on IN pin disconnects all incoming links to this node
      inPin?.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const ins = (currentGraph.edges || []).filter((e) => e.to === n.id);
        if (ins.length) {
          pushGraphUndoState(`Disconnect incoming to ${n.id}`);
          currentGraph.edges = (currentGraph.edges || []).filter((e) => e.to !== n.id);
          renderBlueprintGraph();
          if (selectedQuestNode) selectBlueprintNode(selectedQuestNode);
          (window.showStudioToast || console.log)(`Removed ${ins.length} incoming link(s) to "${n.id}"`, false);
        }
      });

      // Dropping an active wire on IN pin, OUT pin, or anywhere on the node card completes the connection
      div.addEventListener("mouseup", (ev) => {
        if (wireDragState && wireDragState.nodeId && wireDragState.nodeId !== n.id) {
          ev.stopPropagation();
          const fromId = wireDragState.dir === "out" ? wireDragState.nodeId : n.id;
          const toId = wireDragState.dir === "out" ? n.id : wireDragState.nodeId;
          clearActiveWireDrag();
          connectBlueprintNodes(fromId, toId);
        }
      });

      let dragging = false, startX = 0, startY = 0, origX = 0, origY = 0;
      div.addEventListener("click", (ev) => {
        if (ev.target.closest(".bp-pin-hit-out") || ev.target.closest(".bp-pin-hit-in")) return;
        selectBlueprintNode(n);
      });
      div.addEventListener("mousedown", (ev) => {
        if (ev.button !== 0) return;
        if (ev.target.closest(".bp-pin-hit-out") || ev.target.closest(".bp-pin-hit-in")) return;
        ev.stopPropagation();
        // If 2-click wire mode is active, clicking anywhere on another node bubble connects it!
        if (wireDragState && wireDragState.nodeId && wireDragState.nodeId !== n.id) {
          const fromId = wireDragState.dir === "out" ? wireDragState.nodeId : n.id;
          const toId = wireDragState.dir === "out" ? n.id : wireDragState.nodeId;
          clearActiveWireDrag();
          connectBlueprintNodes(fromId, toId);
          return;
        }
        selectBlueprintNode(n);
        dragging = true;
        let _dragUndoPushed = false;
        startX = ev.clientX;
        startY = ev.clientY;
        origX = n.x;
        origY = n.y;
        let _edgeRaf = 0;
        const onMove = (me) => {
          if (!dragging) return;
          if (!_dragUndoPushed && (Math.abs(me.clientX - startX) > 3 || Math.abs(me.clientY - startY) > 3)) {
            const savedX = n.x, savedY = n.y;
            n.x = origX;
            n.y = origY;
            pushGraphUndoState(`Move ${n.id}`);
            n.x = savedX;
            n.y = savedY;
            _dragUndoPushed = true;
          }
          n.x = snapCoordToGrid(Math.max(12, origX + (me.clientX - startX)));
          n.y = snapCoordToGrid(Math.max(12, origY + (me.clientY - startY)));
          div.style.left = n.x + "px";
          div.style.top = n.y + "px";
          const coordLabel = div.querySelector(".bp-pin-row span:nth-child(2)");
          if (coordLabel) coordLabel.textContent = `${n.id} (${n.x},${n.y})`;
          if (!_edgeRaf) {
            _edgeRaf = requestAnimationFrame(() => {
              _edgeRaf = 0;
              drawSvgEdges(nodeMap);
            });
          }
        };
        const onUp = () => {
          dragging = false;
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
        };
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      });

      container.appendChild(div);
    });

    updateWireVisualHighlights();
    drawSvgEdges(nodeMap);
    syncGraphUndoButtons();
    if (nodes.length && !selectedQuestNode) selectBlueprintNode(nodes[0]);
  }

  function computeBezierPathBetweenCoords(x1, y1, x2, y2, srcNode, dstNode) {
    const NODE_W = 264;
    const NODE_H = 104;
    if (srcNode && dstNode) {
      const sameCol = Math.abs(dstNode.x - srcNode.x) < 40;
      const goingRight = dstNode.x >= srcNode.x + 40;
      if (goingRight) {
        const dx = Math.max(45, Math.abs(x2 - x1) * 0.45);
        return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
      } else if (sameCol && dstNode.y > srcNode.y) {
        const sx = srcNode.x + NODE_W * 0.5;
        const sy = srcNode.y + NODE_H;
        const tx = dstNode.x + NODE_W * 0.5;
        const ty = dstNode.y;
        const dy = Math.max(24, (ty - sy) * 0.45);
        return `M ${sx} ${sy} C ${sx} ${sy + dy}, ${tx} ${ty - dy}, ${tx} ${ty}`;
      } else if (!goingRight && Math.abs(dstNode.y - srcNode.y) < 55) {
        const sx = srcNode.x;
        const sy = srcNode.y + 84;
        const tx = dstNode.x + NODE_W;
        const ty = dstNode.y + 84;
        const dx = Math.max(45, Math.abs(sx - tx) * 0.45);
        return `M ${sx} ${sy} C ${sx - dx} ${sy}, ${tx + dx} ${ty}, ${tx} ${ty}`;
      } else {
        const midY = srcNode.y < dstNode.y ? srcNode.y + NODE_H + 28 : srcNode.y - 28;
        return `M ${x1} ${y1} C ${x1 + 36} ${y1}, ${x1 + 36} ${midY}, ${(x1 + x2) * 0.5} ${midY} S ${x2 - 36} ${y2}, ${x2} ${y2}`;
      }
    }
    const dx = Math.max(48, Math.abs(x2 - x1) * 0.45);
    return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
  }

  function drawSvgEdges(nodeMap) {
    const svg = document.getElementById("bpSvgEdges");
    if (!svg) return;
    svg.style.pointerEvents = "none";
    const edges = currentGraph.edges || [];
    const NODE_W = 264;
    const PIN_Y_OFFSET = 84;

    let html = `<defs>
      <marker id="bpArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#38bdf8"/>
      </marker>
      <marker id="bpArrowActive" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#10b981"/>
      </marker>
      <marker id="bpArrowDanger" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#f87171"/>
      </marker>
    </defs>`;

    edges.forEach((e) => {
      const src = nodeMap[e.from];
      const dst = nodeMap[e.to];
      if (!src || !dst) return;

      const x1 = src.x + NODE_W;
      const y1 = src.y + PIN_Y_OFFSET;
      const x2 = dst.x;
      const y2 = dst.y + PIN_Y_OFFSET;
      const path = computeBezierPathBetweenCoords(x1, y1, x2, y2, src, dst);
      const isRecent = lastConnectedEdge && lastConnectedEdge.from === e.from && lastConnectedEdge.to === e.to;
      const strokeColor = isRecent ? "#10b981" : "#38bdf8";
      const markerUrl = isRecent ? "url(#bpArrowActive)" : "url(#bpArrow)";
      const strokeW = isRecent ? "2.8" : "2.2";

      html += `<g class="bp-edge-group" data-from="${escapeHtml(e.from)}" data-to="${escapeHtml(e.to)}">
        <path class="bp-edge-hit" data-from="${escapeHtml(e.from)}" data-to="${escapeHtml(e.to)}" d="${path}" stroke="transparent" stroke-width="14" fill="none" style="pointer-events:stroke;cursor:pointer;"><title>Click to disconnect: ${escapeHtml(e.from)} -> ${escapeHtml(e.to)}</title></path>
        <path class="bp-edge-line" data-from="${escapeHtml(e.from)}" data-to="${escapeHtml(e.to)}" d="${path}" stroke="${strokeColor}" stroke-width="${strokeW}" fill="none" marker-end="${markerUrl}" opacity="0.92" style="pointer-events:none;transition:stroke 0.12s, stroke-width 0.12s;"></path>
      </g>`;
    });

    // Render live rubber-band wire while dragging or in 2-click connection mode
    if (wireDragState && wireDragState.nodeId && nodeMap[wireDragState.nodeId]) {
      const srcNode = nodeMap[wireDragState.nodeId];
      const hoveredNode = wireDragState.hoveredTargetId ? nodeMap[wireDragState.hoveredTargetId] : null;
      let x1, y1, x2, y2;
      if (wireDragState.dir === "out") {
        x1 = srcNode.x + NODE_W;
        y1 = srcNode.y + PIN_Y_OFFSET;
        x2 = hoveredNode ? hoveredNode.x : wireDragState.curX;
        y2 = hoveredNode ? hoveredNode.y + PIN_Y_OFFSET : wireDragState.curY;
      } else {
        x1 = hoveredNode ? hoveredNode.x + NODE_W : wireDragState.curX;
        y1 = hoveredNode ? hoveredNode.y + PIN_Y_OFFSET : wireDragState.curY;
        x2 = srcNode.x;
        y2 = srcNode.y + PIN_Y_OFFSET;
      }
      const livePath = computeBezierPathBetweenCoords(x1, y1, x2, y2, null, null);
      html += `<path id="bpLiveDragWire" d="${livePath}" stroke="#10b981" stroke-width="2.8" stroke-dasharray="6,4" fill="none" marker-end="url(#bpArrowActive)" style="pointer-events:none;opacity:0.98;"/>`;
    }

    svg.innerHTML = html;
    svg.querySelectorAll(".bp-edge-hit").forEach((hitEl) => {
      const grp = hitEl.parentElement;
      const visibleLine = grp?.querySelector(".bp-edge-line");
      hitEl.addEventListener("mouseenter", () => {
        if (visibleLine) {
          visibleLine.setAttribute("stroke", "#f87171");
          visibleLine.setAttribute("stroke-width", "3.2");
          visibleLine.setAttribute("marker-end", "url(#bpArrowDanger)");
        }
      });
      hitEl.addEventListener("mouseleave", () => {
        if (visibleLine) {
          const isRecent =
            lastConnectedEdge &&
            lastConnectedEdge.from === hitEl.dataset.from &&
            lastConnectedEdge.to === hitEl.dataset.to;
          visibleLine.setAttribute("stroke", isRecent ? "#10b981" : "#38bdf8");
          visibleLine.setAttribute("stroke-width", isRecent ? "2.8" : "2.2");
          visibleLine.setAttribute("marker-end", isRecent ? "url(#bpArrowActive)" : "url(#bpArrow)");
        }
      });
      hitEl.addEventListener("click", (ev) => {
        ev.stopPropagation();
        disconnectBlueprintEdge(hitEl.dataset.from, hitEl.dataset.to);
      });
    });
  }

  let cachedQuestPresets = { templates: [], npcs: [], locations: [], items: [] };
  let _questPresetsFetched = false;
  async function ensureQuestPresetsLoaded() {
    if (_questPresetsFetched) return cachedQuestPresets;
    _questPresetsFetched = true;
    fetch("/api/quests/campaign_templates")
      .then((r) => r.json())
      .then((d) => {
        if (d && d.ok) cachedQuestPresets = d;
      })
      .catch(() => {});
    return cachedQuestPresets;
  }

  async function selectBlueprintNode(n) {
    selectedQuestNode = n;
    document.querySelectorAll("#bpNodesContainer .bp-node").forEach((el) => {
      const isSel = el.dataset.nid === n.id;
      el.classList.toggle("selected", isSel);
      el.style.zIndex = isSel ? "35" : "10";
      el.style.borderColor = isSel ? "#38bdf8" : "#1e293b";
      el.style.boxShadow = isSel
        ? "0 0 0 2px rgba(56,189,248,0.28), 0 8px 20px rgba(0,0,0,0.6)"
        : "0 4px 12px rgba(0,0,0,0.45)";
    });
    const body = document.getElementById("qInspectorBody");
    if (!body) return;

    const isDialogNode = activeSubTab === "dialogs" || String(n.id).startsWith("phr_");

    if (isDialogNode) {
      const phrNum = String(n.id).replace(/^phr_/, "");
      const outgoing = (currentGraph.edges || []).filter((e) => e.from === n.id).map((e) => e.to);
      body.innerHTML = `
        <div style="font-size:11px;font-weight:700;color:#818cf8;text-transform:uppercase;letter-spacing:0.05em;">
          Dialog Phrase Inspector (${escapeHtml(n.file || "dialogs.xml")})
        </div>
        <div style="background:#0f172a;border:1px solid #312e81;border-radius:6px;padding:9px;display:flex;flex-direction:column;gap:7px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:11.5px;font-weight:700;color:#e2e8f0;">Phrase ID: <code>${escapeHtml(n.id)}</code> (#${escapeHtml(phrNum)})</span>
            <span style="font-size:10.5px;padding:2px 7px;border-radius:4px;background:#1e1b4b;color:#c084fc;border:1px solid #4338ca;">${phrNum === "0" ? "Entry Phrase" : "Dialog Line"}</span>
          </div>
          <div style="font-size:11px;color:#94a3b8;">String Table ID: <code>${escapeHtml(n.title_id || "(inline)")}</code></div>
        </div>

        <label style="font-size:12px;">Dialog Text (EN):
          <textarea id="qiDescrEn" class="search-box" rows="4" placeholder="Enter English dialogue line..." style="margin-top:4px;font-family:inherit;">${escapeHtml(n.descr_text || n.descr_en || n.title_text || "")}</textarea>
        </label>
        <label style="font-size:12px;">Dialog Text (RU):
          <textarea id="qiDescrRu" class="search-box" rows="4" placeholder="Введите текст реплики на русском..." style="margin-top:4px;font-family:inherit;">${escapeHtml(n.descr_ru || n.title_ru || "")}</textarea>
        </label>

        <div style="background:#0b1322;border:1px solid #1e3a5f;border-radius:6px;padding:9px;display:flex;flex-direction:column;gap:6px;">
          <div style="font-size:11px;font-weight:700;color:#38bdf8;">Next Phrase Links (OUT -> IN)</div>
          <div style="font-size:11px;color:#cbd5e1;">
            Connected Next Phrases: ${outgoing.length ? outgoing.map((t) => `<span class="bp-unlink-pill" data-target="${escapeHtml(t)}" title="Click to disconnect ${escapeHtml(n.id)} -> ${escapeHtml(t)}" style="display:inline-flex;align-items:center;gap:4px;background:#1e293b;border:1px solid #334155;padding:2px 6px;border-radius:4px;margin-right:4px;cursor:pointer;color:#e2e8f0;font-family:monospace;font-size:11px;">${escapeHtml(t)} <b style="color:#f87171;">x</b></span>`).join("") : "<span style='color:#64748b;'>None (End of branch)</span>"}
          </div>
          <div style="display:flex;gap:5px;">
            <select id="qiNextQuestSelect" class="search-box" style="flex:1;font-size:11px;padding:4px;">
              <option value="">-- Connect OUT to Phrase (IN) --</option>
              ${(currentGraph.nodes || []).filter((x) => x.id !== n.id).map((x) => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.id)} — ${escapeHtml((x.descr_text || x.title || "").slice(0, 40))}</option>`).join("")}
            </select>
            <button class="btn" id="btnLinkNextQuest" style="padding:4px 9px;font-size:11px;border-color:#38bdf8;color:#38bdf8;white-space:nowrap;">Link</button>
          </div>
        </div>

        <label style="font-size:11.5px;color:#cbd5e1;">Precondition / Info Check (<code>&lt;has_info&gt;</code> / <code>&lt;precondition&gt;</code>):
          <input type="text" id="qiCond0" class="search-box" value="${escapeHtml(n.cond || n.cond_0 || "")}" placeholder="e.g. dialogs.actor_have_medkit" style="margin-top:3px;font-family:monospace;font-size:11px;">
        </label>
        <label style="font-size:11.5px;color:#cbd5e1;">Script Action / Give Info (<code>&lt;action&gt;</code> / <code>&lt;give_info&gt;</code>):
          <textarea id="qiOnComplete" class="search-box" rows="2" placeholder="e.g. dialogs.relocate_item_section_to_actor" style="margin-top:3px;font-family:monospace;font-size:11px;">${escapeHtml(n.on_complete || n.target || "")}</textarea>
        </label>

        <button class="btn primary" id="btnSaveQuestNode" style="padding:8px;font-weight:700;">Save Dialog Phrase & Strings (XML)</button>
        <div id="qiSaveMsg" style="font-size:12px;color:#4ade80;"></div>
      `;

      body.querySelectorAll(".bp-unlink-pill").forEach((pill) => pill.addEventListener("click", () => disconnectBlueprintEdge(n.id, pill.dataset.target)));
      document.getElementById("btnLinkNextQuest")?.addEventListener("click", () => {
        const targetId = document.getElementById("qiNextQuestSelect")?.value;
        if (!targetId) return;
        connectBlueprintNodes(n.id, targetId);
      });

      document.getElementById("btnSaveQuestNode")?.addEventListener("click", async () => {
        pushGraphUndoState(`Edit ${n.id}`);
        n.descr_text = document.getElementById("qiDescrEn")?.value || "";
        n.descr_en = n.descr_text;
        n.title_text = n.descr_text;
        n.descr_ru = document.getElementById("qiDescrRu")?.value || "";
        n.title_ru = n.descr_ru;
        n.cond = document.getElementById("qiCond0")?.value || "";
        n.on_complete = document.getElementById("qiOnComplete")?.value || "";
        renderBlueprintGraph();
        const res = await fetch("/api/quests/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(n),
        }).then((r) => r.json());
        const msgEl = document.getElementById("qiSaveMsg");
        if (msgEl && res.ok) msgEl.textContent = "Saved dialog phrase & string table.";
      });
      return;
    }

    const presets = await ensureQuestPresetsLoaded();
    const templates = presets.templates || [];
    const npcs = presets.npcs || [];
    const locs = presets.locations || [];
    const items = presets.items || [];

    const curGiver = n.giver_id || n.giver || "esc_2_12_stalker_wolf";
    const curTargetSmart = n.target_smart || "esc_smart_terrain_7_11";
    const curItem = n.item_section || "quest_case_01";
    const curArchetype = n.archetype || (String(n.target_functor || "").includes("actor_has_item") ? "fetch_return" : "fetch_return");
    const curMoney = n.reward_money || "4500:6000";
    const curFaction = n.reward_faction || "stalker";
    const curGoodwill = n.reward_goodwill ?? 50;
    const curStash = n.reward_stash !== false;

    body.innerHTML = `
      <div style="font-size:11px;font-weight:700;color:#38bdf8;text-transform:uppercase;letter-spacing:0.05em;">
        Quest / Campaign Node Inspector
      </div>

      <div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:6px;padding:8px;display:flex;flex-direction:column;gap:6px;">
        <div style="font-size:11px;font-weight:700;color:#38bdf8;">1. Quest Template (Select or Save Own)</div>
        <div style="display:flex;gap:5px;">
          <select id="qiTemplateSelect" class="search-box" style="flex:1;font-size:11px;padding:4px 6px;">
            <option value="">-- Choose a Quest Template --</option>
            ${templates.map((t) => `<option value="${escapeHtml(t.id)}" ${n._appliedTplId === t.id ? "selected" : ""}>${escapeHtml(window.currentLang === "ru" ? (t.name_ru || t.label_ru || t.title_ru || t.name_en || t.label_en || t.id) : (t.name_en || t.label_en || t.title_en || t.id))}</option>`).join("")}
          </select>
          <button class="btn primary" id="btnApplyQuestTpl" style="padding:4px 9px;font-size:11px;white-space:nowrap;">Apply</button>
        </div>
        <div style="display:flex;gap:5px;">
          <input type="text" id="qiCustomTplName" class="search-box" placeholder="New Template Name (e.g. Wolf Carpark Box)..." style="flex:1;font-size:11px;padding:4px 6px;">
          <button class="btn" id="btnSaveCustomTpl" style="padding:4px 8px;font-size:11px;border-color:#38bdf8;color:#38bdf8;white-space:nowrap;">Save as Template</button>
        </div>
      </div>

      <div style="background:#0f172a;border:1px solid #334155;border-radius:6px;padding:8px;display:flex;flex-direction:column;gap:6px;">
        <div style="font-size:11px;font-weight:700;color:#a855f7;">2. Visual Quest Builder (Pick from List OR Type Custom ID)</div>

        <label style="font-size:11px;color:#cbd5e1;">Quest Pattern / Type:
          <select id="qiArchetype" class="search-box" style="margin-top:2px;font-size:11px;padding:4px;">
            <option value="fetch_return" ${curArchetype === "fetch_return" ? "selected" : ""}>Fetch Item at Location & Return to NPC</option>
            <option value="clear_smart" ${curArchetype === "clear_smart" ? "selected" : ""}>Eliminate Squad / Clear Smart Terrain</option>
            <option value="recon_smart" ${curArchetype === "recon_smart" ? "selected" : ""}>Recon / Reach Smart Terrain</option>
            <option value="manual" ${curArchetype === "manual" ? "selected" : ""}>Manual X-Ray Condlist Only</option>
          </select>
        </label>

        <label style="font-size:11px;color:#cbd5e1;">Quest Giver / Return NPC (Select from list or type ID):
          <input type="text" id="qiGiverId" list="dlQuestGivers" class="search-box" value="${escapeHtml(curGiver)}" placeholder="e.g. esc_2_12_stalker_wolf" style="margin-top:2px;font-size:11px;font-family:monospace;">
          <datalist id="dlQuestGivers">
            ${npcs.map((x) => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.label_en)}</option>`).join("")}
          </datalist>
        </label>

        <label style="font-size:11px;color:#cbd5e1;">Target Location / Smart Terrain (Select from list or type ID):
          <input type="text" id="qiTargetSmart" list="dlSmartTerrains" class="search-box" value="${escapeHtml(curTargetSmart)}" placeholder="e.g. esc_smart_terrain_7_11 (Carpark)" style="margin-top:2px;font-size:11px;font-family:monospace;">
          <datalist id="dlSmartTerrains">
            ${locs.map((x) => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.label_en)} [${(x.coords || []).join(", ")}]</option>`).join("")}
          </datalist>
        </label>

        <div id="qiItemRow" style="display:${curArchetype === "fetch_return" ? "block" : "none"};">
          <label style="font-size:11px;color:#cbd5e1;">Quest Item / Box to Recover (Select from list or type ID):
            <div style="display:flex;gap:5px;margin-top:2px;">
              <input type="text" id="qiItemSec" list="dlQuestItems" class="search-box" value="${escapeHtml(curItem)}" placeholder="e.g. quest_case_01 or esc_wolf_carpark_box" style="flex:1;font-size:11px;font-family:monospace;">
              <button class="btn" id="btnPreviewQuestItemOgf" title="Inspect this Quest Item's 3D .ogf mesh in the 3D Asset & OGF Viewer" style="padding:4px 8px;font-size:11px;white-space:nowrap;border-color:#38bdf8;color:#38bdf8;">3D View</button>
            </div>
            <datalist id="dlQuestItems">
              ${items.map((x) => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.label_en)}</option>`).join("")}
            </datalist>
          </label>
        </div>

        <div style="background:#080f1d;border:1px solid #1e3a5f;border-radius:6px;padding:7px;display:flex;flex-direction:column;gap:5px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:10.5px;font-weight:700;color:#fbbf24;">3D World Coordinates (X, Y, Z) & Spawn Placement</span>
            <span id="qiSpawnLvGvBadge" style="font-size:10px;font-family:monospace;color:#38bdf8;">${n.spawn_lvid !== undefined ? `LVID ${n.spawn_lvid} | GVID ${n.spawn_gvid}` : "Auto C-Ray / AI Grid"}</span>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;">
            <label style="font-size:10px;color:#94a3b8;">X
              <input type="number" step="0.1" id="qiSpawnX" class="search-box" value="${escapeHtml(String(n.spawn_x ?? ((locs.find((l) => l.id === curTargetSmart)?.coords || [112.5, -7.2, -16.0])[0])))}" style="margin-top:1px;font-size:11px;padding:3px 5px;font-family:monospace;">
            </label>
            <label style="font-size:10px;color:#94a3b8;">Y (Height)
              <input type="number" step="0.1" id="qiSpawnY" class="search-box" value="${escapeHtml(String(n.spawn_y ?? ((locs.find((l) => l.id === curTargetSmart)?.coords || [112.5, -7.2, -16.0])[1])))}" style="margin-top:1px;font-size:11px;padding:3px 5px;font-family:monospace;">
            </label>
            <label style="font-size:10px;color:#94a3b8;">Z
              <input type="number" step="0.1" id="qiSpawnZ" class="search-box" value="${escapeHtml(String(n.spawn_z ?? ((locs.find((l) => l.id === curTargetSmart)?.coords || [112.5, -7.2, -16.0])[2])))}" style="margin-top:1px;font-size:11px;padding:3px 5px;font-family:monospace;">
            </label>
          </div>
          <div style="display:flex;gap:5px;margin-top:2px;">
            <button class="btn" id="btnSpawnQuestItem3D" title="Spawn this Quest Item at the exact X, Y, Z coordinates above (automatically snaps to CFORM ground & computes LVID/GVID)" style="flex:1;padding:5px 8px;font-size:11px;border-color:#f59e0b;color:#fbbf24;font-weight:700;">Spawn at X,Y,Z in 3D</button>
            <button class="btn" id="btnPickQuestPos3D" title="Switch to the 3D World Editor and click anywhere on the terrain to pick X, Y, Z coordinates and spawn the object right there" style="flex:1;padding:5px 8px;font-size:11px;border-color:#38bdf8;color:#38bdf8;font-weight:700;">Pick Pos in 3D Editor</button>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 70px;gap:5px;">
          <label style="font-size:11px;color:#cbd5e1;">Reward RU (min:max)
            <input type="text" id="qiRewardMoney" class="search-box" value="${escapeHtml(curMoney)}" placeholder="4500:6000" style="margin-top:2px;font-size:11px;font-family:monospace;">
          </label>
          <label style="font-size:11px;color:#cbd5e1;">Faction
            <input type="text" id="qiRewardFaction" list="dlFactions" class="search-box" value="${escapeHtml(curFaction)}" style="margin-top:2px;font-size:11px;font-family:monospace;">
            <datalist id="dlFactions">
              <option value="stalker">Free Stalkers (Loner)</option>
              <option value="dolg">Duty (Dolg)</option>
              <option value="freedom">Freedom</option>
              <option value="ecolog">Ecologists</option>
              <option value="csky">Clear Sky</option>
              <option value="killer">Mercenaries</option>
              <option value="bandit">Bandits</option>
              <option value="army">Military</option>
            </datalist>
          </label>
          <label style="font-size:11px;color:#cbd5e1;">Goodwill
            <input type="number" id="qiRewardGoodwill" class="search-box" value="${escapeHtml(String(curGoodwill))}" style="margin-top:2px;font-size:11px;">
          </label>
        </div>
        <label style="font-size:11px;color:#cbd5e1;display:flex;align-items:center;gap:6px;cursor:pointer;">
          <input type="checkbox" id="qiRewardStash" ${curStash ? "checked" : ""}> Grant random Stash Coordinates on completion (<code>reward_stash</code>)
        </label>
      </div>

      <label style="font-size:12px;">Section / Quest ID:
        <input type="text" id="qiNodeId" class="search-box" value="${escapeHtml(n.id || "")}" style="margin-top:3px;font-family:monospace;">
      </label>
      <label style="font-size:12px;">Title (EN <code>${escapeHtml(n.title_id || "")}</code>):
        <input type="text" id="qiTitleEn" class="search-box" value="${escapeHtml(n.title_text || n.title_en || n.text_en || n.title || "")}" style="margin-top:3px;">
      </label>
      <label style="font-size:12px;">Title (RU):
        <input type="text" id="qiTitleRu" class="search-box" value="${escapeHtml(n.title_ru || n.text_ru || "")}" style="margin-top:3px;">
      </label>
      <label style="font-size:12px;">Description / Briefing (EN):
        <textarea id="qiDescrEn" class="search-box" rows="3" style="margin-top:3px;font-family:inherit;">${escapeHtml(n.descr_text || n.descr_en || n.text_en || "")}</textarea>
      </label>
      <label style="font-size:12px;">Description / Briefing (RU):
        <textarea id="qiDescrRu" class="search-box" rows="3" style="margin-top:3px;font-family:inherit;">${escapeHtml(n.descr_ru || n.text_ru || "")}</textarea>
      </label>
      <label style="font-size:12px;">Target Functor / Condlist (Auto-generated or Manual):
        <input type="text" id="qiTarget" class="search-box" value="${escapeHtml(n.target_functor || "")}" style="margin-top:3px;font-family:monospace;font-size:11px;">
      </label>
      <label style="font-size:12px;">Task Stage / Completion Condlist (<code>cond_0</code>):
        <input type="text" id="qiCond0" class="search-box" value="${escapeHtml(n.cond_0 || "")}" style="margin-top:3px;font-family:monospace;font-size:11px;">
      </label>
      <label style="font-size:12px;">On Complete (Reward / Info Portion — Auto-generated or Manual):
        <textarea id="qiOnComplete" class="search-box" rows="2" style="margin-top:3px;font-family:monospace;font-size:11px;">${escapeHtml(n.on_complete || "")}</textarea>
      </label>
      <div style="background:#0b1322;border:1px solid #1e3a5f;border-radius:6px;padding:8px;display:flex;flex-direction:column;gap:5px;">
        <div style="font-size:11px;font-weight:700;color:#38bdf8;">Connect Quest Chain (OUT -> IN)</div>
        <div style="font-size:10.5px;color:#94a3b8;">Hold & drag from <b>OUT</b> to <b>IN</b> (or click OUT then IN):</div>
        <div style="font-size:11px;color:#cbd5e1;">
          Connected: ${(currentGraph.edges || []).filter((e) => e.from === n.id).map((e) => `<span class="bp-unlink-pill" data-target="${escapeHtml(e.to)}" title="Click to disconnect ${escapeHtml(n.id)} -> ${escapeHtml(e.to)}" style="display:inline-flex;align-items:center;gap:4px;background:#1e293b;border:1px solid #334155;padding:2px 6px;border-radius:4px;margin-right:4px;cursor:pointer;color:#e2e8f0;font-family:monospace;font-size:11px;">${escapeHtml(e.to)} <b style="color:#f87171;">x</b></span>`).join("") || "<span style='color:#64748b;'>None</span>"}
        </div>
        <div style="display:flex;gap:5px;">
          <select id="qiNextQuestSelect" class="search-box" style="flex:1;font-size:11px;padding:4px;">
            <option value="">-- Connect OUT to Quest (IN) --</option>
            ${(currentGraph.nodes || []).filter((x) => x.id !== n.id).map((x) => `<option value="${escapeHtml(x.id)}" ${n.next_quest_id === x.id ? "selected" : ""}>${escapeHtml(x.id)} — ${escapeHtml(x.title_en || x.title || "")}</option>`).join("")}
          </select>
          <button class="btn" id="btnLinkNextQuest" style="padding:4px 9px;font-size:11px;border-color:#38bdf8;color:#38bdf8;white-space:nowrap;">Link OUT->IN</button>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px;">
        <button class="btn primary" id="btnSaveQuestNode" style="padding:8px;font-weight:700;">Save Quest & Strings (LTX + XML)</button>
        <div style="display:flex;gap:5px;">
          <button class="btn" id="btnExportThisQuestZip" title="Export ONLY this quest (+ strings + 3D spawns + MO2 meta.ini) as a ready-to-share Mod Organizer 2 / ModDB .zip file" style="flex:1;padding:6px 8px;font-size:11px;background:#0ea5e9;border-color:#0284c7;color:#082f49;font-weight:700;">Export Quest as MO2 .zip</button>
          <button class="btn" id="btnOpenInspectorQuestGuide" title="Open X-Ray & Anomaly 1.5.3 Quest Logic, Section Fields & Condlist Command Guide" style="padding:6px 9px;font-size:11px;border-color:#a855f7;color:#c084fc;font-weight:700;">? Logic Guide</button>
        </div>
      </div>
      <div id="qiSaveMsg" style="font-size:12px;color:#4ade80;"></div>
    `;

    function rebuildXrayExpressionsFromGuided() {
      const arch = document.getElementById("qiArchetype")?.value || "fetch_return";
      const itemRow = document.getElementById("qiItemRow");
      if (itemRow) itemRow.style.display = arch === "fetch_return" ? "block" : "none";
      if (arch === "manual") return;

      const giver = (document.getElementById("qiGiverId")?.value || "esc_2_12_stalker_wolf").trim();
      const smart = (document.getElementById("qiTargetSmart")?.value || "esc_smart_terrain_7_11").trim();
      const item = (document.getElementById("qiItemSec")?.value || "quest_case_01").trim();
      const money = (document.getElementById("qiRewardMoney")?.value || "4500:6000").trim();
      const fac = (document.getElementById("qiRewardFaction")?.value || "stalker").trim();
      const gw = parseInt(document.getElementById("qiRewardGoodwill")?.value || "50", 10) || 50;
      const stash = Boolean(document.getElementById("qiRewardStash")?.checked);
      const qid = (document.getElementById("qiNodeId")?.value || n.id || "custom_quest").trim();

      n.archetype = arch;
      n.giver_id = giver;
      n.target_smart = smart;
      n.item_section = item;
      n.reward_money = money;
      n.reward_faction = fac;
      n.reward_goodwill = gw;
      n.reward_stash = stash;

      let targetExpr = smart;
      let condExpr = `{=squad_exist(${smart})} nil, complete`;
      const effects = [];
      if (money) effects.push(`reward_random_money(${money})`);
      if (stash) effects.push(`reward_stash(true)`);
      if (fac && gw) effects.push(`inc_faction_goodwill_to_actor(${fac}:${gw})`);

      if (arch === "fetch_return") {
        targetExpr = `{=actor_has_item(${item})} ${giver}, ${smart}`;
        condExpr = `{=actor_has_item(${item}) =talking_to_actor(${giver})} complete`;
        if (item) effects.push(`remove_item(${item})`);
      } else if (arch === "clear_smart") {
        targetExpr = `{!squad_exist(${smart})} ${giver}, ${smart}`;
        condExpr = `{!squad_exist(${smart})} complete`;
      } else if (arch === "recon_smart") {
        targetExpr = `{=actor_on_level(l01_escape)} ${smart}, ${giver}`;
        condExpr = `{=dist_to_smart_terrain_le(${smart}:25)} complete`;
      }

      const onCompExpr = `%=${effects.join(" =")}% +${qid}_done`;
      const tEl = document.getElementById("qiTarget");
      const cEl = document.getElementById("qiCond0");
      const oEl = document.getElementById("qiOnComplete");
      if (tEl) tEl.value = targetExpr;
      if (cEl) cEl.value = condExpr;
      if (oEl) oEl.value = onCompExpr;
    }

    if (!n.cond_0) rebuildXrayExpressionsFromGuided();

    document.getElementById("qiTargetSmart")?.addEventListener("change", (ev) => {
      const smartId = (ev.target?.value || "").trim();
      const locInfo = locs.find((l) => l.id === smartId);
      if (locInfo && Array.isArray(locInfo.coords) && locInfo.coords.length === 3) {
        const xEl = document.getElementById("qiSpawnX");
        const yEl = document.getElementById("qiSpawnY");
        const zEl = document.getElementById("qiSpawnZ");
        if (xEl) xEl.value = String(locInfo.coords[0]);
        if (yEl) yEl.value = String(locInfo.coords[1]);
        if (zEl) zEl.value = String(locInfo.coords[2]);
        n.spawn_x = locInfo.coords[0];
        n.spawn_y = locInfo.coords[1];
        n.spawn_z = locInfo.coords[2];
        n.spawn_level = locInfo.level || "l01_escape";
      }
    });
    ["qiArchetype", "qiGiverId", "qiTargetSmart", "qiItemSec", "qiRewardMoney", "qiRewardFaction", "qiRewardGoodwill", "qiRewardStash"].forEach((id) => {
      document.getElementById(id)?.addEventListener("input", rebuildXrayExpressionsFromGuided);
      document.getElementById(id)?.addEventListener("change", rebuildXrayExpressionsFromGuided);
    });

    function applyQuestTemplateById(selId) {
      if (!selId) return;
      const tpl = templates.find((t) => t.id === selId);
      if (!tpl) return;
      n._appliedTplId = tpl.id;
      n.archetype = tpl.archetype || "fetch_return";
      n.giver_id = tpl.giver_id || "esc_2_12_stalker_wolf";
      n.target_smart = tpl.target_smart || "esc_smart_terrain_7_11";
      n.item_section = tpl.item_section || "quest_case_01";
      n.item_mesh = tpl.item_mesh || n.item_mesh || "";
      n.reward_money = tpl.reward_money || "4500:6000";
      n.reward_faction = tpl.reward_faction || "stalker";
      n.reward_goodwill = tpl.reward_goodwill ?? 50;
      n.reward_stash = tpl.reward_stash !== undefined ? tpl.reward_stash : true;
      n.title_en = tpl.title_en || tpl.name_en || n.title_en;
      n.title_text = n.title_en;
      n.title = n.title_en;
      n.title_ru = tpl.title_ru || tpl.name_ru || n.title_ru;
      n.descr_en = tpl.descr_en || n.descr_en;
      n.descr_text = n.descr_en;
      n.descr_ru = tpl.descr_ru || n.descr_ru;
      n.cond_0 = "";
      renderBlueprintGraph();
      selectBlueprintNode(n);
      const msgEl = document.getElementById("qiSaveMsg");
      if (msgEl) msgEl.textContent = `Applied template: ${tpl.name_en || tpl.label_en || tpl.id}`;
    }

    document.getElementById("btnApplyQuestTpl")?.addEventListener("click", () => {
      const selId = document.getElementById("qiTemplateSelect")?.value;
      if (!selId) {
        const msgEl = document.getElementById("qiSaveMsg");
        if (msgEl) msgEl.textContent = "Please select a template from the dropdown first, then click Apply.";
        return;
      }
      pushGraphUndoState(`Apply Template ${selId}`);
      applyQuestTemplateById(selId);
    });

    document.getElementById("btnSaveCustomTpl")?.addEventListener("click", async () => {
      const customName = (document.getElementById("qiCustomTplName")?.value || document.getElementById("qiTitleEn")?.value || "Custom Template").trim();
      const payload = {
        name_en: customName,
        name_ru: document.getElementById("qiTitleRu")?.value || customName,
        archetype: document.getElementById("qiArchetype")?.value || "fetch_return",
        giver_id: document.getElementById("qiGiverId")?.value || "",
        target_smart: document.getElementById("qiTargetSmart")?.value || "",
        item_section: document.getElementById("qiItemSec")?.value || "",
        reward_money: document.getElementById("qiRewardMoney")?.value || "4500:6000",
        reward_faction: document.getElementById("qiRewardFaction")?.value || "stalker",
        reward_goodwill: parseInt(document.getElementById("qiRewardGoodwill")?.value || "50", 10) || 50,
        reward_stash: Boolean(document.getElementById("qiRewardStash")?.checked),
        title_en: document.getElementById("qiTitleEn")?.value || "",
        title_ru: document.getElementById("qiTitleRu")?.value || "",
        descr_en: document.getElementById("qiDescrEn")?.value || "",
        descr_ru: document.getElementById("qiDescrRu")?.value || "",
        target_functor: document.getElementById("qiTarget")?.value || "",
        cond: document.getElementById("qiCond0")?.value || "",
        on_complete: document.getElementById("qiOnComplete")?.value || "",
      };
      const r = await fetch("/api/quests/save_template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (d && d.ok) {
        cachedQuestPresets = null;
        await selectBlueprintNode(n);
        const msgEl = document.getElementById("qiSaveMsg");
        if (msgEl) msgEl.textContent = `Saved reusable template: "${customName}"!`;
      }
    });

    document.getElementById("btnPreviewQuestItemOgf")?.addEventListener("click", async () => {
      const itemSec = (document.getElementById("qiItemSec")?.value || "quest_case_01").trim();
      const itemInfo = items.find((i) => i.id === itemSec);
      const ogfPath = (itemInfo?.mesh || n.item_mesh || "dynamics/equipments/quest/box_black.ogf").replace(/\\/g, "/");
      if (typeof window.switchTab === "function") window.switchTab("ogf");
      setTimeout(() => {
        if (typeof window.loadOgfModel === "function") window.loadOgfModel(ogfPath);
      }, 120);
    });

    document.getElementById("btnSpawnQuestItem3D")?.addEventListener("click", async () => {
      const smartId = (document.getElementById("qiTargetSmart")?.value || "esc_smart_terrain_7_11").trim();
      const itemSec = (document.getElementById("qiItemSec")?.value || "quest_case_01").trim();
      const locInfo = locs.find((l) => l.id === smartId) || { level: window.currentLevel || "l01_escape", coords: [112.5, -7.2, -16.0] };
      const itemInfo = items.find((i) => i.id === itemSec) || { mesh: n.item_mesh || "dynamics\\equipments\\quest\\box_black.ogf" };
      const sx = parseFloat(document.getElementById("qiSpawnX")?.value ?? String(locInfo.coords[0]));
      const sy = parseFloat(document.getElementById("qiSpawnY")?.value ?? String(locInfo.coords[1]));
      const sz = parseFloat(document.getElementById("qiSpawnZ")?.value ?? String(locInfo.coords[2]));
      const targetLevel = n.spawn_level || locInfo.level || window.currentLevel || "l01_escape";

      const r = await fetch("/api/placement/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          op: "place",
          level: targetLevel,
          section: itemSec,
          name: `${n.id || "quest"}_${itemSec}`,
          category: "item",
          x: Number.isFinite(sx) ? sx : 112.5,
          y: Number.isFinite(sy) ? sy : -7.2,
          z: Number.isFinite(sz) ? sz : -16.0,
          snap_to_ai_y: true,
          mesh: itemInfo.mesh,
        }),
      });
      const d = await r.json();
      const msgEl = document.getElementById("qiSaveMsg");
      if (d && d.ok && d.object) {
        n.spawn_x = d.object.x;
        n.spawn_y = d.object.y;
        n.spawn_z = d.object.z;
        n.spawn_lvid = d.object.lvid;
        n.spawn_gvid = d.object.gvid;
        n.spawn_level = d.object.level;
        const xEl = document.getElementById("qiSpawnX");
        const yEl = document.getElementById("qiSpawnY");
        const zEl = document.getElementById("qiSpawnZ");
        const bEl = document.getElementById("qiSpawnLvGvBadge");
        if (xEl) xEl.value = String(d.object.x);
        if (yEl) yEl.value = String(d.object.y);
        if (zEl) zEl.value = String(d.object.z);
        if (bEl) bEl.textContent = `LVID ${d.object.lvid} | GVID ${d.object.gvid}`;
        window.placedStudioObjects = d.objects || [];
        window.selectedStudioObjectId = d.object.id;
        if (typeof window.renderPlaced3DObjectsOnMap === "function") window.renderPlaced3DObjectsOnMap();
        const notice = `Spawned "${itemSec}" on ${d.object.level} at (${d.object.x}, ${d.object.y}, ${d.object.z}) [LVID ${d.object.lvid}, GVID ${d.object.gvid}]!`;
        if (msgEl) msgEl.textContent = notice;
        (window.showStudioToast || console.log)(notice, false);
      }
    });

    document.getElementById("btnPickQuestPos3D")?.addEventListener("click", () => {
      const itemSec = (document.getElementById("qiItemSec")?.value || "quest_case_01").trim();
      const itemInfo = items.find((i) => i.id === itemSec) || { mesh: n.item_mesh || "dynamics\\equipments\\quest\\box_black.ogf" };
      window.startQuest3DPickMode?.(n, itemSec, itemInfo.mesh);
    });

    document.getElementById("btnExportThisQuestZip")?.addEventListener("click", () => {
      window.exportSingleQuestMo2Zip?.(n);
    });

    document.getElementById("btnOpenInspectorQuestGuide")?.addEventListener("click", () => {
      window.toggleQuestLogicGuideModal?.();
    });

    body.querySelectorAll(".bp-unlink-pill").forEach((pill) => pill.addEventListener("click", () => disconnectBlueprintEdge(n.id, pill.dataset.target)));
    document.getElementById("btnLinkNextQuest")?.addEventListener("click", () => {
      const targetId = document.getElementById("qiNextQuestSelect")?.value;
      if (targetId) connectBlueprintNodes(n.id, targetId);
    });

    document.getElementById("btnSaveQuestNode")?.addEventListener("click", async () => {
      n.id = document.getElementById("qiNodeId").value.trim();
      n.title_en = document.getElementById("qiTitleEn").value;
      n.title_ru = document.getElementById("qiTitleRu").value;
      n.descr_en = document.getElementById("qiDescrEn").value;
      n.descr_ru = document.getElementById("qiDescrRu").value;
      n.target_functor = document.getElementById("qiTarget").value;
      n.cond_0 = document.getElementById("qiCond0")?.value || "";
      n.on_complete = document.getElementById("qiOnComplete").value;

      const ltxBlock = `[${n.id}]\nicon = ${n.icon || "ui_inGame2_Put_v_pripyat"}\nstoryline = ${n.storyline ? "true" : "false"}\nprior = ${n.prior || 20}\ntitle = ${n.title_id || "st_" + n.id + "_title"}\ndescr = ${n.descr_id || "st_" + n.id + "_descr"}\ntarget = ${n.target_functor || "esc_smart_terrain_7_11"}\ncondlist_0 = ${n.cond_0 || "complete"}\non_complete = ${n.on_complete || "%=inc_faction_goodwill_to_actor(stalker:50)%"}\n`;

      const res = await fetch("/api/quests/save_node", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quest_id: n.id,
          compiled_ltx: ltxBlock,
          strings_en: {
            [n.title_id || "st_" + n.id + "_title"]: n.title_en,
            [n.descr_id || "st_" + n.id + "_descr"]: n.descr_en,
          },
          strings_ru: {
            [n.title_id || "st_" + n.id + "_title"]: n.title_ru,
            [n.descr_id || "st_" + n.id + "_descr"]: n.descr_ru,
          },
        }),
      });
      const out = await res.json();
      const msgEl = document.getElementById("qiSaveMsg");
      if (msgEl) msgEl.textContent = out.ok ? "Saved to LTX & String-Table XML!" : "Error";
      renderBlueprintGraph();
      renderQuestSidebarList();
    });
  }

  function renderLoadscreenTipsList() {
    const grid = document.getElementById("loadscreenTipsGrid");
    if (!grid) return;
    const q = (document.getElementById("qSearchInput")?.value || "").toLowerCase();
    const filtered = loadscreenTips.filter(
      (t) =>
        !q ||
        t.id.toLowerCase().includes(q) ||
        (t.eng || "").toLowerCase().includes(q) ||
        (t.rus || "").toLowerCase().includes(q)
    );
    grid.innerHTML = filtered
      .map(
        (t) => `
      <div class="tip-card" data-tid="${t.id}" style="background:#111826;border:1px solid #1f2a3c;border-radius:6px;padding:10px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:12px;">
        <div style="flex:1;">
          <div style="font-weight:700;font-size:12px;color:#4ade80;margin-bottom:3px;">${escapeHtml(t.id)}</div>
          <div style="font-size:13px;color:#e2e8f0;">${escapeHtml(t.eng)}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px;">RU: ${escapeHtml(t.rus)}</div>
        </div>
        <button class="btn" style="font-size:11px;padding:5px 10px;">Edit</button>
      </div>`
      )
      .join("");

    grid.querySelectorAll(".tip-card").forEach((el) => {
      el.addEventListener("click", () => {
        const tip = loadscreenTips.find((x) => x.id === el.dataset.tid);
        if (tip) inspectLoadscreenTip(tip);
      });
    });
  }

  function inspectLoadscreenTip(tip) {
    selectedTip = tip;
    const body = document.getElementById("qInspectorBody");
    if (!body) return;
    body.innerHTML = `
      <div style="font-size:11px;color:#4ade80;font-weight:700;">EDIT LOADSCREEN TIP (ui_st_loadscreen.xml)</div>
      <label style="font-size:12px;">String-ID (in <code>ui_st_loadscreen.xml</code>):
        <input type="text" id="lsTipId" class="search-box" value="${escapeHtml(tip.id)}" style="margin-top:4px;font-family:monospace;">
      </label>
      <label style="font-size:12px;">Loadscreen Text (ENG):
        <textarea id="lsTipEng" class="search-box" rows="5" style="margin-top:4px;font-family:inherit;">${escapeHtml(tip.eng)}</textarea>
      </label>
      <label style="font-size:12px;">Loadscreen Text (RUS):
        <textarea id="lsTipRus" class="search-box" rows="5" style="margin-top:4px;font-family:inherit;">${escapeHtml(tip.rus)}</textarea>
      </label>
      <button class="btn primary" id="btnSaveLsTip" style="padding:8px;font-weight:700;">Save Loadscreen Tip</button>
      <div id="lsSaveStatus" style="font-size:12px;color:#4ade80;"></div>
    `;

    document.getElementById("btnSaveLsTip")?.addEventListener("click", async () => {
      const idVal = document.getElementById("lsTipId").value.trim();
      const engVal = document.getElementById("lsTipEng").value.trim();
      const rusVal = document.getElementById("lsTipRus").value.trim();
      const res = await fetch("/api/save_loadscreen_tip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: idVal, eng: engVal, rus: rusVal }),
      });
      const out = await res.json();
      if (out.ok) {
        tip.id = idVal;
        tip.eng = engVal;
        tip.rus = rusVal;
        if (!loadscreenTips.find((x) => x.id === idVal)) loadscreenTips.push(tip);
        renderLoadscreenTipsList();
        renderQuestSidebarList();
        const st = document.getElementById("lsSaveStatus");
        if (st) st.textContent = `Saved directly to ui_st_loadscreen.xml (${idVal})!`;
      }
    });
  }

  function wireQuestTabEvents() {
    const subStory = document.getElementById("qSubTabStory");
    const subDlgs = document.getElementById("qSubTabDialogs");
    const subTips = document.getElementById("qSubTabTips");
    const bpView = document.getElementById("bpViewport");
    const lsPanel = document.getElementById("loadscreenTipsPanel");
    const campBox = document.getElementById("qCampaignBox");

    function setSubMode(mode) {
      activeSubTab = mode;
      [subStory, subDlgs, subTips].forEach((b) => b?.classList.remove("primary"));
      if (mode === "story") subStory?.classList.add("primary");
      if (mode === "dialogs") subDlgs?.classList.add("primary");
      if (mode === "tips") subTips?.classList.add("primary");

      if (bpView) bpView.style.display = mode === "tips" ? "none" : "block";
      if (lsPanel) lsPanel.style.display = mode === "tips" ? "block" : "none";
      if (campBox) campBox.style.display = mode === "story" ? "block" : "none";
      renderQuestSidebarList();
      if (mode === "tips") renderLoadscreenTipsList();
      if (mode === "story") {
        if (currentGraph && currentGraph.is_dialog) {
          const cVal = document.getElementById("qCampaignSelect")?.value || "tm_escape.ltx";
          loadCampaignGraph(cVal);
        } else if (selectedQuestNode) {
          selectBlueprintNode(selectedQuestNode);
        } else if (currentGraph && Array.isArray(currentGraph.nodes) && currentGraph.nodes.length) {
          selectBlueprintNode(currentGraph.nodes[0]);
        }
      }
    }

    subStory?.addEventListener("click", () => setSubMode("story"));
    subDlgs?.addEventListener("click", () => setSubMode("dialogs"));
    subTips?.addEventListener("click", () => setSubMode("tips"));

    document.getElementById("qCampaignSelect")?.addEventListener("change", (e) => {
      loadCampaignGraph(e.target.value);
    });

    document.getElementById("qSearchInput")?.addEventListener("input", () => {
      renderQuestSidebarList();
      if (activeSubTab === "tips") renderLoadscreenTipsList();
    });

    document.getElementById("btnNewLoadscreenTip")?.addEventListener("click", () => {
      const nextNum = loadscreenTips.filter((t) => t.id.startsWith("ls_tip_")).length + 1;
      inspectLoadscreenTip({
        id: `ls_tip_${nextNum}`,
        eng: "New Stalker survival tip for Anomaly 1.5.3...",
        rus: "Новый совет для выживания в Зоне...",
      });
    });

    document.getElementById("btnAddQuestNode")?.addEventListener("click", async () => {
      if (activeSubTab !== "story") {
        activeSubTab = "story";
        document.getElementById("qSubTabStory")?.click();
      }
      pushGraphUndoState("Add Quest Node");
      currentGraph.nodes = currentGraph.nodes || [];
      let suffix = currentGraph.nodes.length + 1;
      while (currentGraph.nodes.some((x) => x.id === "custom_quest_" + suffix)) suffix++;
      const newId = "custom_quest_" + suffix;

      // Find guaranteed collision-free (x, y) on the 24px grid near current viewport or selected node
      const vp = document.getElementById("bpViewport");
      let baseX = snapCoordToGrid((vp ? vp.scrollLeft : 0) + 48);
      let baseY = snapCoordToGrid((vp ? vp.scrollTop : 0) + 48);
      if (selectedQuestNode && typeof selectedQuestNode.x === "number" && typeof selectedQuestNode.y === "number") {
        baseX = snapCoordToGrid(selectedQuestNode.x + 312);
        baseY = snapCoordToGrid(selectedQuestNode.y);
      }
      const overlapsExisting = (tx, ty) =>
        (currentGraph.nodes || []).some(
          (existing) => Math.abs((existing.x || 0) - tx) < 276 && Math.abs((existing.y || 0) - ty) < 126
        );
      let candX = baseX;
      let candY = baseY;
      let step = 0;
      while (overlapsExisting(candX, candY) && step < 400) {
        step++;
        const col = step % 4;
        const row = Math.floor(step / 4);
        candX = snapCoordToGrid(48 + col * 312);
        candY = snapCoordToGrid(baseY + row * 144);
      }
      if (overlapsExisting(candX, candY)) {
        const maxY = Math.max(0, ...(currentGraph.nodes || []).map((n) => n.y || 0));
        candX = 48;
        candY = snapCoordToGrid(maxY + 144);
      }

      const newNode = {
        id: newId,
        title_id: "st_" + newId + "_title",
        descr_id: "st_" + newId + "_descr",
        title_en: "New Custom Anomaly Task (" + newId + ")",
        descr_en: "Retrieve the target item or complete the objective in the Zone.",
        title_ru: "Новое задание в Зоне (" + newId + ")",
        descr_ru: "Выполните поручение в Зоне.",
        storyline: false,
        prior: 25,
        target_functor: "general_fetch_task",
        on_complete: "%=inc_faction_goodwill_to_actor(stalker:50)%",
        x: candX,
        y: candY,
      };
      currentGraph.nodes.push(newNode);
      renderBlueprintGraph();
      await selectBlueprintNode(newNode);
      const createdEl = document.querySelector(`#bpNodesContainer .bp-node[data-nid="${newId}"]`);
      if (createdEl && typeof createdEl.scrollIntoView === "function") {
        createdEl.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
      }
      (window.showStudioToast || console.log)(`Created new Quest Node "${newId}" at (${candX}, ${candY})`, false);
    });

    document.getElementById("btnAutoLayoutGraph")?.addEventListener("click", () => {
      const nextMode = currentLayoutMode === "serpentine" ? "tree" : "serpentine";
      pushGraphUndoState(`Auto-Layout (${currentLayoutMode === "serpentine" ? "S-Curve Flow" : "Left->Right Tree"})`);
      currentLayoutMode = nextMode;
      computeHierarchicalGraphLayout(currentGraph.nodes || [], currentGraph.edges || [], currentLayoutMode);
      renderBlueprintGraph();
      syncGraphUndoButtons();
      (window.showStudioToast || console.log)(
        currentLayoutMode === "tree"
          ? "Applied Left->Right Tree Layout (Ctrl+Z or Undo to revert)"
          : "Applied Compact S-Curve Flow Layout (Ctrl+Z or Undo to revert)"
      );
    });

    document.getElementById("btnSnapAllNodesToGrid")?.addEventListener("click", () => {
      pushGraphUndoState("Align Nodes to 24px Grid");
      (currentGraph.nodes || []).forEach((n) => {
        n.x = Math.max(24, Math.round((n.x || 48) / GRAPH_GRID_SIZE) * GRAPH_GRID_SIZE);
        n.y = Math.max(24, Math.round((n.y || 48) / GRAPH_GRID_SIZE) * GRAPH_GRID_SIZE);
      });
      renderBlueprintGraph();
      syncGraphUndoButtons();
      (window.showStudioToast || console.log)("All node bubbles aligned to 24px grid (Ctrl+Z to undo)");
    });

    document.getElementById("btnGraphUndo")?.addEventListener("click", () => {
      if (!window.undoQuestOrDialogGraph()) {
        window.triggerStudioUndo?.();
      }
    });
    document.getElementById("btnGraphRedo")?.addEventListener("click", () => {
      if (!window.redoQuestOrDialogGraph()) {
        window.triggerStudioRedo?.();
      }
    });

    window.exportSingleQuestMo2Zip = async function (questNode) {
      const qn = questNode || selectedQuestNode || (currentGraph.nodes && currentGraph.nodes[0]);
      if (!qn) {
        (window.showStudioToast || console.log)("Please select a quest node first.", true);
        return null;
      }
      // Read live Inspector inputs if currently open for this node
      const liveId = (document.getElementById("qiNodeId")?.value || qn.id || "custom_quest").trim();
      const liveTitleEn = document.getElementById("qiTitleEn")?.value ?? (qn.title_en || qn.title_text || qn.title || liveId);
      const liveTitleRu = document.getElementById("qiTitleRu")?.value ?? (qn.title_ru || liveTitleEn);
      const liveDescrEn = document.getElementById("qiDescrEn")?.value ?? (qn.descr_en || qn.descr_text || "");
      const liveDescrRu = document.getElementById("qiDescrRu")?.value ?? (qn.descr_ru || liveDescrEn);
      const liveTarget = document.getElementById("qiTarget")?.value ?? (qn.target_functor || "esc_smart_terrain_7_11");
      const liveCond0 = document.getElementById("qiCond0")?.value ?? (qn.cond_0 || "complete");
      const liveOnComp = document.getElementById("qiOnComplete")?.value ?? (qn.on_complete || "%=reward_random_money(4500:6000)%");

      const safeModName = `MO2_Quest_${liveId.replace(/[^A-Za-z0-9_\-]+/g, "_")}`;
      const res = await fetch("/api/quests/export_mod", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mod_name: safeModName,
          version: "1.0.0",
          author: "EternalPain",
          description: `Standalone S.T.A.L.K.E.R. Anomaly 1.5.3 Quest Addon: ${liveTitleEn} (${liveId})`,
          single_quest_id: liveId,
          single_quest_node: {
            id: liveId,
            title: qn.title_id || `st_${liveId}_title`,
            title_text: liveTitleEn,
            title_ru: liveTitleRu,
            descr: qn.descr_id || `st_${liveId}_descr`,
            descr_text: liveDescrEn,
            descr_ru: liveDescrRu,
            icon: qn.icon || "ui_inGame2_Put_v_pripyat",
            prior: qn.prior || 25,
            storyline: Boolean(qn.storyline),
            target_functor: liveTarget,
            status_functor: qn.status_functor || "fetch_task_Need_return",
            condlist_0: liveCond0,
            on_init: qn.on_init || "",
            on_complete: liveOnComp,
            on_fail: qn.on_fail || "",
          },
        }),
      });
      const out = await res.json();
      if (out && out.ok && out.download_url) {
        if (!new URLSearchParams(window.location.search).get("qa_auto")) {
          const a = document.createElement("a");
          a.href = out.download_url;
          a.download = out.zip_filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
        }
        const msg = `Exported MO2/ModDB .zip: ${out.zip_filename} (${out.size_bytes} bytes, saved in exports/${out.zip_filename})`;
        const msgEl = document.getElementById("qiSaveMsg");
        if (msgEl) msgEl.textContent = msg;
        (window.showStudioToast || console.log)(msg, false);
      }
      return out;
    };

    window.startQuest3DPickMode = function (questNode, itemSection, itemMesh) {
      const qn = questNode || selectedQuestNode;
      if (!qn) return;
      window.quest3DPickState = {
        active: true,
        questNode: qn,
        questId: qn.id || "custom_quest",
        itemSection: itemSection || qn.item_section || "quest_case_01",
        itemMesh: itemMesh || qn.item_mesh || "dynamics\\equipments\\quest\\box_black.ogf",
      };
      if (typeof window.switchTab === "function") window.switchTab("map");

      let banner = document.getElementById("quest3DPickBanner");
      if (!banner) {
        banner = document.createElement("div");
        banner.id = "quest3DPickBanner";
        banner.style.cssText =
          "position:fixed;top:52px;left:50%;transform:translateX(-50%);z-index:9500;background:#0f172a;border:2px solid #fbbf24;border-radius:8px;padding:8px 16px;color:#fef08a;font-size:12px;font-weight:700;display:flex;align-items:center;gap:12px;box-shadow:0 10px 30px rgba(0,0,0,0.85);";
        document.body.appendChild(banner);
      }
      banner.style.display = "flex";
      banner.innerHTML = `
        <span>QUEST TARGET PICK MODE: Click anywhere on the 3D Terrain to spawn <code>${escapeHtml(window.quest3DPickState.itemSection)}</code> &amp; capture X, Y, Z, LVID, GVID for Quest <code>${escapeHtml(window.quest3DPickState.questId)}</code></span>
        <button class="btn" id="btnCancelQuest3DPick" style="padding:3px 9px;font-size:11px;border-color:#f87171;color:#f87171;">Cancel (Esc)</button>
      `;
      document.getElementById("btnCancelQuest3DPick")?.addEventListener("click", () => {
        window.quest3DPickState = null;
        banner.style.display = "none";
      });
    };

    window.completeQuest3DPickAtPoint = async function (pt) {
      const st = window.quest3DPickState;
      if (!st || !st.active || !pt) return false;
      const lvl = window.currentLevel || "l01_escape";
      const r = await fetch("/api/placement/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          op: "place",
          level: lvl,
          section: st.itemSection,
          name: `${st.questId}_${st.itemSection}`,
          category: "item",
          x: Number(pt.x.toFixed(2)),
          y: Number(pt.y.toFixed(2)),
          z: Number(pt.z.toFixed(2)),
          snap_to_ai_y: true,
          mesh: st.itemMesh,
        }),
      });
      const d = await r.json();
      if (d && d.ok && d.object) {
        st.questNode.spawn_x = d.object.x;
        st.questNode.spawn_y = d.object.y;
        st.questNode.spawn_z = d.object.z;
        st.questNode.spawn_lvid = d.object.lvid;
        st.questNode.spawn_gvid = d.object.gvid;
        st.questNode.spawn_level = d.object.level;
        window.placedStudioObjects = d.objects || [];
        window.selectedStudioObjectId = d.object.id;
        if (typeof window.renderPlaced3DObjectsOnMap === "function") window.renderPlaced3DObjectsOnMap();
      }
      const banner = document.getElementById("quest3DPickBanner");
      if (banner) {
        banner.innerHTML = `
          <span style="color:#4ade80;">Picked 3D Position (${d?.object?.x ?? pt.x.toFixed(2)}, ${d?.object?.y ?? pt.y.toFixed(2)}, ${d?.object?.z ?? pt.z.toFixed(2)}) [LVID ${d?.object?.lvid ?? 0} | GVID ${d?.object?.gvid ?? 0}] for <code>${escapeHtml(st.questId)}</code>!</span>
          <button class="btn primary" id="btnReturnToQuestFrom3D" style="padding:4px 10px;font-size:11px;">Return to Quest Builder</button>
        `;
        document.getElementById("btnReturnToQuestFrom3D")?.addEventListener("click", () => {
          banner.style.display = "none";
          window.quest3DPickState = null;
          if (typeof window.switchTab === "function") window.switchTab("quests");
          if (st.questNode) selectBlueprintNode(st.questNode);
        });
      }
      if (st.questNode && selectedQuestNode && selectedQuestNode.id === st.questNode.id) {
        const xEl = document.getElementById("qiSpawnX");
        const yEl = document.getElementById("qiSpawnY");
        const zEl = document.getElementById("qiSpawnZ");
        const bEl = document.getElementById("qiSpawnLvGvBadge");
        if (xEl && d?.object) xEl.value = String(d.object.x);
        if (yEl && d?.object) yEl.value = String(d.object.y);
        if (zEl && d?.object) zEl.value = String(d.object.z);
        if (bEl && d?.object) bEl.textContent = `LVID ${d.object.lvid} | GVID ${d.object.gvid}`;
      }
      window.quest3DPickState = null;
      if (typeof window.hideStudio3DGhostPreview === 'function') window.hideStudio3DGhostPreview();
      return true;
    };

    window.toggleQuestLogicGuideModal = function () {
      let gm = document.getElementById("questLogicGuideModal");
      if (!gm) {
        gm = document.createElement("div");
        gm.id = "questLogicGuideModal";
        gm.style.cssText =
          "display:none;position:fixed;inset:0;z-index:9800;background:rgba(4,8,16,0.86);align-items:center;justify-content:center;padding:24px;";
        gm.innerHTML = `
          <div style="background:#0f172a;border:1.5px solid #a855f7;border-radius:10px;max-width:960px;width:100%;max-height:88vh;display:flex;flex-direction:column;color:#e2e8f0;box-shadow:0 24px 60px rgba(0,0,0,0.9);">
            <div style="display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid #1e293b;background:#090d16;border-radius:10px 10px 0 0;">
              <div>
                <h3 style="margin:0;color:#c084fc;font-size:16px;">S.T.A.L.K.E.R. Anomaly 1.5.3 — Quest Logic, Section Fields &amp; Condlist Command Guide</h3>
                <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Complete reference for Task Sections (tm_*.ltx), Condlist Syntax, Preconditions (=func), Effects (%=func%), and Console Commands</div>
              </div>
              <div style="display:flex;gap:8px;align-items:center;">
                <input type="text" id="inpQuestGuideFilter" class="search-box" placeholder="Filter commands (e.g. reward, item, squad, smart, condlist)..." style="width:260px;font-size:11.5px;padding:5px 9px;">
                <button class="btn" id="btnCloseQuestLogicGuide" style="padding:5px 12px;font-weight:700;">Close (Esc)</button>
              </div>
            </div>
            <div id="questGuideContentBody" style="padding:18px 22px;overflow-y:auto;display:flex;flex-direction:column;gap:16px;font-size:12px;line-height:1.55;">
              <div class="qguide-sec" style="background:#0b111e;border:1px solid #1e293b;border-radius:8px;padding:12px 14px;">
                <h4 style="margin:0 0 8px 0;color:#38bdf8;font-size:13.5px;">1. Anatomy of an Anomaly 1.5.3 Task Section (<code>gamedata/configs/misc/task/tm_*.ltx</code>)</h4>
                <pre style="background:#050811;border:1px solid #1e293b;padding:10px;border-radius:6px;color:#a5f3fc;font-size:11px;overflow-x:auto;margin:0 0 8px 0;">[esc_wolf_carpark_box_task]
icon                  = ui_inGame2_Put_v_pripyat       ; PDA task icon from ui_ingame2_common.xml
storyline             = false                          ; true = Golden Main Storyline Quest, false = Side / Task Quest
prior                 = 25                             ; PDA sorting priority (higher priority appears first)
title                 = st_esc_wolf_carpark_box_title  ; String ID in configs/text/eng/*.xml (or functor)
descr                 = st_esc_wolf_carpark_box_descr  ; Briefing description String ID in configs/text/eng/*.xml
target                = {=actor_has_item(quest_case_01)} esc_2_12_stalker_wolf, esc_smart_terrain_7_11
condlist_0            = {=actor_has_item(quest_case_01) =talking_to_actor(esc_2_12_stalker_wolf)} complete
on_init               = %=create_squad(esc_bandit_carpark_squad:esc_smart_terrain_7_11)%
on_complete           = %=remove_item(quest_case_01) =reward_random_money(4500:6000) =reward_stash(true) =inc_faction_goodwill_to_actor(stalker:50)% +esc_wolf_carpark_box_task_done
on_fail               = %-esc_wolf_carpark_box_task_active%</pre>
                <div style="color:#cbd5e1;font-size:11.5px;">
                  <b>How <code>target</code> works:</b> Dynamic condlist evaluated every frame for the yellow PDA map marker. In the example above, while the player does <i>not</i> yet have <code>quest_case_01</code>, the PDA marker points to <code>esc_smart_terrain_7_11</code> (Carpark). As soon as the player picks up <code>quest_case_01</code>, <code>{=actor_has_item(quest_case_01)}</code> becomes true and the PDA marker automatically switches to Wolf (<code>esc_2_12_stalker_wolf</code>)!
                </div>
              </div>

              <div class="qguide-sec" style="background:#0b111e;border:1px solid #1e293b;border-radius:8px;padding:12px 14px;">
                <h4 style="margin:0 0 8px 0;color:#f59e0b;font-size:13.5px;">2. X-Ray Condlist Syntax Rules (Conditions vs. Effects)</h4>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                  <div style="background:#070b14;border:1px solid #1e293b;border-radius:6px;padding:9px;">
                    <div style="font-weight:700;color:#4ade80;margin-bottom:4px;">Curly Braces <code>{ ... }</code> = Preconditions (Checks)</div>
                    <div>• <code>{+info_id}</code> : True if Info Portion <code>info_id</code> is active</div>
                    <div>• <code>{-info_id}</code> : True if Info Portion <code>info_id</code> is NOT active</div>
                    <div>• <code>{=func(arg1:arg2)}</code> : True if Lua function in <code>xr_conditions.script</code> returns <code>true</code></div>
                    <div>• <code>{!func(arg1:arg2)}</code> : True if Lua function returns <code>false</code> (negated)</div>
                  </div>
                  <div style="background:#070b14;border:1px solid #1e293b;border-radius:6px;padding:9px;">
                    <div style="font-weight:700;color:#38bdf8;margin-bottom:4px;">Percent Signs <code>% ... %</code> = Effects (Actions)</div>
                    <div>• <code>%+info_id%</code> or <code>+info_id</code> : Grants Info Portion <code>info_id</code> (unlocks next quests/dialogs)</div>
                    <div>• <code>%-info_id%</code> : Removes / disables Info Portion <code>info_id</code></div>
                    <div>• <code>%=func(arg1:arg2)%</code> : Executes Lua action in <code>xr_effects.script</code></div>
                    <div>• Outcomes in <code>condlist_0</code>: <code>complete</code>, <code>fail</code>, <code>reversed</code>, or <code>nil</code></div>
                  </div>
                </div>
              </div>

              <div class="qguide-sec" style="background:#0b111e;border:1px solid #1e293b;border-radius:8px;padding:12px 14px;">
                <h4 style="margin:0 0 8px 0;color:#4ade80;font-size:13.5px;">3. Essential Preconditions (<code>xr_conditions.script</code> — use inside <code>{ ... }</code>) — Click any Snippet to Copy</h4>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                  <div class="qguide-cmd" data-snippet="{=actor_has_item(quest_case_01)}" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#4ade80;font-weight:700;">=actor_has_item(section)</code>
                    <div style="font-size:11px;color:#94a3b8;">True when the player carries the specified item section in their inventory.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="{=talking_to_actor(esc_2_12_stalker_wolf)}" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#4ade80;font-weight:700;">=talking_to_actor(story_id)</code>
                    <div style="font-size:11px;color:#94a3b8;">True while the player is in dialogue with the NPC matching <code>story_id</code>.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="{!squad_exist(esc_smart_terrain_7_11)}" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#4ade80;font-weight:700;">!squad_exist(smart_or_squad_id)</code>
                    <div style="font-size:11px;color:#94a3b8;">True when the target squad or smart terrain population has been eliminated.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="{=dist_to_smart_terrain_le(esc_smart_terrain_7_11:25)}" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#4ade80;font-weight:700;">=dist_to_smart_terrain_le(smart:meters)</code>
                    <div style="font-size:11px;color:#94a3b8;">True when the player is within <code>meters</code> of the Smart Terrain center (Recon tasks).</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="{=actor_on_level(l01_escape)}" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#4ade80;font-weight:700;">=actor_on_level(level_name)</code>
                    <div style="font-size:11px;color:#94a3b8;">True when the player is currently on the specified level (e.g. <code>l01_escape</code>).</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="{+my_previous_quest_done}" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#4ade80;font-weight:700;">+info_portion_id</code>
                    <div style="font-size:11px;color:#94a3b8;">True when the specified Info Portion has been granted (used for OUT-&gt;IN quest chains).</div>
                  </div>
                </div>
              </div>

              <div class="qguide-sec" style="background:#0b111e;border:1px solid #1e293b;border-radius:8px;padding:12px 14px;">
                <h4 style="margin:0 0 8px 0;color:#c084fc;font-size:13.5px;">4. Essential Effects &amp; Rewards (<code>xr_effects.script</code> — use inside <code>%= ... %</code> in <code>on_init</code> / <code>on_complete</code>)</h4>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                  <div class="qguide-cmd" data-snippet="%=reward_random_money(4500:6000)%" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#c084fc;font-weight:700;">=reward_random_money(min:max)</code>
                    <div style="font-size:11px;color:#94a3b8;">Transfers a random Ruble reward between <code>min</code> and <code>max</code> to the player with PDA notification.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="%=reward_item(medkit_army)%" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#c084fc;font-weight:700;">=reward_item(section)</code>
                    <div style="font-size:11px;color:#94a3b8;">Spawns the given item section directly into the player's inventory as a reward.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="%=remove_item(quest_case_01)%" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#c084fc;font-weight:700;">=remove_item(section)</code>
                    <div style="font-size:11px;color:#94a3b8;">Removes the quest item from the player's inventory when handing it over to the Quest Giver.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="%=reward_stash(true)%" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#c084fc;font-weight:700;">=reward_stash(true)</code>
                    <div style="font-size:11px;color:#94a3b8;">Reveals a random loot stash on the player's PDA map via <code>treasure_manager</code>.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="%=inc_faction_goodwill_to_actor(stalker:50)%" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#c084fc;font-weight:700;">=inc_faction_goodwill_to_actor(faction:delta)</code>
                    <div style="font-size:11px;color:#94a3b8;">Increases reputation with <code>stalker</code>, <code>dolg</code>, <code>freedom</code>, <code>ecolog</code>, <code>csky</code>, <code>killer</code>, <code>army</code>, or <code>bandit</code>.</div>
                  </div>
                  <div class="qguide-cmd" data-snippet="%=create_squad(esc_bandit_carpark_squad:esc_smart_terrain_7_11)%" style="cursor:pointer;background:#070b14;border:1px solid #334155;border-radius:5px;padding:7px;">
                    <code style="color:#c084fc;font-weight:700;">=create_squad(squad_sec:smart_terrain)</code>
                    <div style="font-size:11px;color:#94a3b8;">Spawns an A-Life NPC/mutant squad at the target Smart Terrain (ideal in <code>on_init</code>).</div>
                  </div>
                </div>
              </div>

              <div class="qguide-sec" style="background:#0b111e;border:1px solid #1e293b;border-radius:8px;padding:12px 14px;">
                <h4 style="margin:0 0 8px 0;color:#38bdf8;font-size:13.5px;">5. Studio <code>SDK&gt;</code> Bottom Console Commands &amp; Sharing as MO2 / ModDB <code>.zip</code></h4>
                <div style="font-size:11.5px;color:#cbd5e1;display:flex;flex-direction:column;gap:4px;">
                  <div>• <code>quest.validate</code> — Runs full DAG cycle &amp; softlock verification across the active campaign graph.</div>
                  <div>• <code>quest.complete &lt;quest_id&gt;</code> / <code>quest.abandon &lt;quest_id&gt;</code> / <code>quest.reset &lt;quest_id&gt;</code> — Simulates quest state transitions in the Studio runtime.</div>
                  <div>• <code>vfs.reload</code> — Hot-reloads all modified LTX/XML/OGF assets and clears the VFS cache without restarting.</div>
                  <div>• <b>Sharing a Single Quest or Campaign (Mod Organizer 2 / ModDB):</b> Click <b>Export Selected Quest (.zip)</b> in the top toolbar (or <b>Export Quest as MO2 .zip</b> at the bottom of the Quest Inspector). It packages <code>gamedata/configs/misc/task/...</code>, English &amp; Russian string tables, 3D spawns, <code>meta.ini</code>, and <code>README_ModDB.txt</code> into a ready-to-install <code>.zip</code> in <code>exports/</code> and downloads it immediately.</div>
                </div>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(gm);

        document.getElementById("btnCloseQuestLogicGuide")?.addEventListener("click", () => {
          gm.style.display = "none";
        });
        gm.addEventListener("click", (ev) => {
          if (ev.target === gm) gm.style.display = "none";
        });
        document.getElementById("inpQuestGuideFilter")?.addEventListener("input", (ev) => {
          const q = (ev.target.value || "").toLowerCase().trim();
          gm.querySelectorAll(".qguide-cmd, .qguide-sec").forEach((el) => {
            if (el.classList.contains("qguide-cmd")) {
              el.style.display = !q || el.textContent.toLowerCase().includes(q) ? "block" : "none";
            }
          });
        });
        gm.querySelectorAll(".qguide-cmd").forEach((card) => {
          card.addEventListener("click", () => {
            const snip = card.getAttribute("data-snippet") || "";
            if (navigator.clipboard && snip) navigator.clipboard.writeText(snip).catch(() => {});
            (window.showStudioToast || console.log)(`Copied snippet to clipboard: ${snip}`, false);
          });
        });
      }
      gm.style.display = gm.style.display === "flex" ? "none" : "flex";
    };

    document.getElementById("btnOpenQuestLogicGuide")?.addEventListener("click", () => {
      window.toggleQuestLogicGuideModal();
    });

    document.getElementById("btnExportSingleQuestMo2Zip")?.addEventListener("click", () => {
      window.exportSingleQuestMo2Zip();
    });

    // 1-Click Local Mod Archive (.zip) Output (NO upload, strictly local disk + browser download)
    document.getElementById("btnExportModZip")?.addEventListener("click", async () => {
      const modName = prompt("Local Mod Archive Name (saved under exports/):", "Anomaly_153_Custom_Quest_Mod");
      if (!modName) return;
      const res = await fetch("/api/quests/export_mod", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mod_name: modName,
          version: "1.0.0",
          author: "EternalPain",
          include_loadscreen: true,
        }),
      });
      const out = await res.json();
      if (out.ok && out.download_url) {
        const a = document.createElement("a");
        a.href = out.download_url;
        a.download = out.zip_filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        (window.showStudioToast || alert)(`Local mod archive created!\n\nFile: ${out.zip_path}\nSize: ${out.size_bytes} bytes\nIncluded files:\n- ${out.included_files.join("\n- ")}`);
      }
    });
  }

  // =========================================================================
  // TAB 6: 3D PARTICLE EDITOR LOGIC (2,370 Effects)
  // =========================================================================
  let ptAnimId = null;
  let ptParticles = [];
  let ptConfig = { max: 220, rate: 65, speed: 2.4, size: 4.5, color: "#38bdf8" };

  window.loadParticlesCatalog = loadParticlesCatalog;
  async function loadParticlesCatalog() {
    try {
      const res = await fetch("/api/particles");
      particlesData = await res.json();
      const catSel = document.getElementById("ptCategorySelect");
      if (catSel && particlesData.categories) {
        catSel.innerHTML =
          `<option value="">All ${particlesData.categories.length} Categories (${particlesData.total} Effects)</option>` +
          particlesData.categories
            .map((c) => `<option value="${c.name}">${c.name} (${c.count})</option>`)
            .join("");
      }
      renderParticlesSidebar();
      if (particlesData.particles && particlesData.particles[0]) {
        selectParticleEffect(particlesData.particles[0]);
      }
      startParticleCanvasLoop();
    } catch (e) {
      console.error("Failed to load particles:", e);
    }
  }

  function renderParticlesSidebar() {
    const listEl = document.getElementById("ptItemList");
    if (!listEl) return;
    const cat = document.getElementById("ptCategorySelect")?.value || "";
    const q = (document.getElementById("ptSearchInput")?.value || "").toLowerCase();

    const filtered = (particlesData.particles || [])
      .filter((p) => (!cat || p.category === cat) && (!q || p.name.toLowerCase().includes(q)))
      .slice(0, 300);

    listEl.innerHTML = filtered
      .map(
        (p) => `
      <div class="list-item" data-pname="${escapeHtml(p.name)}" style="padding:7px 10px;border-bottom:1px solid var(--border);cursor:pointer;">
        <div style="font-weight:600;font-size:12px;color:#e2e8f0;">${escapeHtml(p.name)}</div>
        <div style="font-size:10px;color:#38bdf8;">Category: ${escapeHtml(p.category)}</div>
      </div>`
      )
      .join("");

    listEl.querySelectorAll(".list-item").forEach((el) => {
      el.addEventListener("click", () => {
        const p = (particlesData.particles || []).find((x) => x.name === el.dataset.pname);
        if (p) selectParticleEffect(p);
      });
    });
  }

  function selectParticleEffect(p) {
    selectedParticle = p;
    const nameField = document.getElementById("ptNameField");
    const titleEl = document.getElementById("ptActiveTitle");
    if (nameField) nameField.value = p.name;
    if (titleEl) titleEl.textContent = `3D Particle Emitter: ${p.name}`;

    // Derive deterministic visual preset from effect name
    const n = p.name.toLowerCase();
    if (n.includes("fire") || n.includes("burner") || n.includes("campfire")) {
      ptConfig = { max: 280, rate: 95, speed: 3.1, size: 5.5, color: "#f97316" };
    } else if (n.includes("electr") || n.includes("el_") || n.includes("spark")) {
      ptConfig = { max: 180, rate: 80, speed: 5.8, size: 3.5, color: "#38bdf8" };
    } else if (n.includes("acid") || n.includes("chem") || n.includes("gas")) {
      ptConfig = { max: 240, rate: 50, speed: 1.4, size: 6.5, color: "#4ade80" };
    } else if (n.includes("blood") || n.includes("hit_flesh")) {
      ptConfig = { max: 160, rate: 90, speed: 4.0, size: 4.0, color: "#ef4444" };
    } else {
      ptConfig = { max: p.max_particles || 220, rate: p.rate || 65, speed: p.speed || 2.4, size: p.size || 4.5, color: p.color || "#a855f7" };
    }

    syncParticleSliders();
    ptParticles = [];
  }

  function syncParticleSliders() {
    const setV = (id, v) => { const el = document.getElementById(id); if (el && document.activeElement !== el) el.value = v; };
    setV("ptMaxSlider", ptConfig.max); setV("ptMaxInput", ptConfig.max);
    setV("ptRateSlider", ptConfig.rate); setV("ptRateInput", ptConfig.rate);
    setV("ptSpeedSlider", ptConfig.speed); setV("ptSpeedInput", ptConfig.speed);
    setV("ptSizeSlider", ptConfig.size); setV("ptSizeInput", ptConfig.size);
    setV("ptColorPicker", ptConfig.color);
  }

  function startParticleCanvasLoop() {
    if (ptAnimId) cancelAnimationFrame(ptAnimId);
    const canvas = document.getElementById("ptPreviewCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    function step() {
      ptAnimId = requestAnimationFrame(step);
      if (!document.getElementById("tab-particles")?.classList.contains("active")) return;

      const w = canvas.width;
      const h = canvas.height;
      ctx.fillStyle = "rgba(9, 13, 20, 0.22)";
      ctx.fillRect(0, 0, w, h);

      // Draw 3D grid floor
      ctx.strokeStyle = "rgba(56, 189, 248, 0.12)";
      ctx.lineWidth = 1;
      for (let i = -5; i <= 5; i++) {
        ctx.beginPath();
        ctx.moveTo(w / 2 + i * 55, h * 0.72);
        ctx.lineTo(w / 2 + i * 95, h * 0.92);
        ctx.stroke();
      }

      // Spawn new particles
      const toSpawn = Math.max(1, Math.round(ptConfig.rate / 30));
      for (let i = 0; i < toSpawn && ptParticles.length < ptConfig.max; i++) {
        const angle = Math.random() * Math.PI * 2;
        const spread = (Math.random() - 0.5) * ptConfig.speed * 1.6;
        ptParticles.push({
          x: w / 2 + (Math.random() - 0.5) * 18,
          y: h * 0.72,
          vx: Math.cos(angle) * spread,
          vy: -Math.random() * ptConfig.speed * 1.8 - 0.8,
          life: 1.0,
          decay: 0.008 + Math.random() * 0.014,
          size: ptConfig.size * (0.7 + Math.random() * 0.7),
        });
      }

      for (let i = ptParticles.length - 1; i >= 0; i--) {
        const p = ptParticles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life -= p.decay;
        if (p.life <= 0) {
          ptParticles.splice(i, 1);
          continue;
        }
        ctx.save();
        ctx.globalAlpha = Math.max(0, p.life);
        ctx.fillStyle = ptConfig.color;
        ctx.shadowColor = ptConfig.color;
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }
    step();
  }

  function wireParticleTabEvents() {
    document.getElementById("ptCategorySelect")?.addEventListener("change", renderParticlesSidebar);
    document.getElementById("ptSearchInput")?.addEventListener("input", renderParticlesSidebar);

    [
      ["ptMaxSlider", "ptMaxInput", "max", true],
      ["ptRateSlider", "ptRateInput", "rate", true],
      ["ptSpeedSlider", "ptSpeedInput", "speed", false],
      ["ptSizeSlider", "ptSizeInput", "size", false],
    ].forEach(([slId, inId, key, isInt]) => {
      const handler = (rawVal) => {
        const v = isInt ? parseInt(rawVal, 10) : parseFloat(rawVal);
        if (!isNaN(v) && v > 0) {
          ptConfig[key] = v;
          syncParticleSliders();
        }
      };
      document.getElementById(slId)?.addEventListener("input", (e) => handler(e.target.value));
      document.getElementById(inId)?.addEventListener("input", (e) => handler(e.target.value));
    });
    document.getElementById("ptColorPicker")?.addEventListener("input", (e) => {
      ptConfig.color = e.target.value;
      syncParticleSliders();
    });

    document.getElementById("btnPtBurst")?.addEventListener("click", () => {
      const canvas = document.getElementById("ptPreviewCanvas");
      if (!canvas) return;
      for (let i = 0; i < 120; i++) {
        const a = Math.random() * Math.PI * 2;
        const spd = 1 + Math.random() * ptConfig.speed * 3;
        ptParticles.push({
          x: canvas.width / 2,
          y: canvas.height * 0.65,
          vx: Math.cos(a) * spd,
          vy: Math.sin(a) * spd - 1.5,
          life: 1.0,
          decay: 0.012,
          size: ptConfig.size * 1.3,
        });
      }
    });

    document.getElementById("btnPtSave")?.addEventListener("click", async () => {
      if (!selectedParticle) return;
      const res = await fetch("/api/save_particle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: selectedParticle.name,
          max_particles: ptConfig.max,
          rate: ptConfig.rate,
          speed: ptConfig.speed,
          size: ptConfig.size,
          color: ptConfig.color,
        }),
      });
      const out = await res.json();
      const st = document.getElementById("ptSaveStatus");
      if (st) st.textContent = out.ok ? `Saved (${selectedParticle.name})` : "Error";
    });
  }

  // =========================================================================
  // 3D VIEWPORT PRO TOOLS: 3D RULER, CAMERA BOOKMARKS & MULTI-SELECT
  // =========================================================================
  function inject3DProToolbar() {
    const toolbar = document.querySelector("#tab-map .viewport-toolbar");
    if (!toolbar || document.getElementById("btn3DRuler")) return;

    const wrap = document.createElement("div");
    wrap.style.display = "inline-flex";
    wrap.style.gap = "5px";
    wrap.style.alignItems = "center";
    wrap.innerHTML = `
      <button class="btn" id="btn3DRuler" title="3D Ruler: Click two points on the map to measure distance in meters" style="padding:5px 9px;font-size:12px;">Ruler: <span id="rulerDistText">Off</span></button>
      <select id="camBookmarkSelect" class="search-box" style="width:135px;padding:4px 6px;font-size:11px;margin:0;">
        <option value="">Kamera-Lesezeichen...</option>
      </select>
      <button class="btn" id="btnSaveCamBookmark" title="Bookmark current 3D camera position" style="padding:4px 7px;font-size:11px;"></button>

    `;
    toolbar.appendChild(wrap);

    const rulerBtn = document.getElementById("btn3DRuler");
    rulerBtn?.addEventListener("click", () => {
      rulerActive = !rulerActive;
      rulerPoints = [];
      rulerBtn.classList.toggle("primary", rulerActive);
      document.getElementById("rulerDistText").textContent = rulerActive ? "Click Point 1..." : "Off";
    });

    // Listen to 3D canvas clicks for Ruler measurement
    const vp = document.getElementById("mapCanvas");
    vp?.addEventListener("click", (ev) => {
      if (!rulerActive || !get3DCamera() || !get3DScene() || !window.THREE) return;
      const rect = vp.getBoundingClientRect();
      const mouse = new window.THREE.Vector2(
        ((ev.clientX - rect.left) / rect.width) * 2 - 1,
        -((ev.clientY - rect.top) / rect.height) * 2 + 1
      );
      const raycaster = new window.THREE.Raycaster();
      raycaster.setFromCamera(mouse, get3DCamera());
      const hits = raycaster.intersectObjects(get3DScene().children, true);
      if (hits.length > 0) {
        rulerPoints.push(hits[0].point.clone());
        if (rulerPoints.length === 1) {
          document.getElementById("rulerDistText").textContent = "Punkt 2 klicken...";
        } else if (rulerPoints.length >= 2) {
          const p1 = rulerPoints[rulerPoints.length - 2];
          const p2 = rulerPoints[rulerPoints.length - 1];
          const dist = p1.distanceTo(p2);
          const dx = Math.abs(p2.x - p1.x).toFixed(1);
          const dy = Math.abs(p2.y - p1.y).toFixed(1);
          const dz = Math.abs(p2.z - p1.z).toFixed(1);
          document.getElementById("rulerDistText").textContent = `${dist.toFixed(2)} m (ΔY:${dy}m)`;
          draw3DRulerLine(p1, p2);
        }
      }
    });

    function refreshBookmarkDropdown() {
      const sel = document.getElementById("camBookmarkSelect");
      if (!sel) return;
      sel.innerHTML =
        `<option value="">Kamera-Pos (${cameraBookmarks.length})...</option>` +
        cameraBookmarks.map((b, i) => `<option value="${i}">${escapeHtml(b.name)}</option>`).join("");
    }
    refreshBookmarkDropdown();

    document.getElementById("btnSaveCamBookmark")?.addEventListener("click", () => {
      if (!get3DCamera() || !get3DControls()) return;
      const name = prompt("Camera bookmark name:", `View ${cameraBookmarks.length + 1}`);
      if (!name) return;
      cameraBookmarks.push({
        name,
        pos: [get3DCamera().position.x, get3DCamera().position.y, get3DCamera().position.z],
        target: [get3DControls().target.x, get3DControls().target.y, get3DControls().target.z],
      });
      localStorage.setItem("anomaly_cam_bookmarks_v1", JSON.stringify(cameraBookmarks));
      refreshBookmarkDropdown();
    });

    document.getElementById("camBookmarkSelect")?.addEventListener("change", (e) => {
      const idx = parseInt(e.target.value, 10);
      if (isNaN(idx) || !cameraBookmarks[idx] || !get3DCamera() || !get3DControls()) return;
      const b = cameraBookmarks[idx];
      get3DCamera().position.set(b.pos[0], b.pos[1], b.pos[2]);
      get3DControls().target.set(b.target[0], b.target[1], b.target[2]);
      get3DControls().update();
    });
  }

  function draw3DRulerLine(p1, p2) {
    if (!get3DScene() || !window.THREE) return;
    if (rulerGroup) get3DScene().remove(rulerGroup);
    rulerGroup = new window.THREE.Group();
    const geom = new window.THREE.BufferGeometry().setFromPoints([p1, p2]);
    const mat = new window.THREE.LineBasicMaterial({ color: 0xf59e0b, linewidth: 3 });
    rulerGroup.add(new window.THREE.Line(geom, mat));
    get3DScene().add(rulerGroup);
  }

  function setupShiftDragBoxSelection() {
    const vp = document.getElementById("mapCanvas");
    if (!vp) return;
    const overlay = document.createElement("div");
    overlay.id = "boxSelectOverlay";
    vp.style.position = "relative";
    vp.appendChild(overlay);

    let boxSelecting = false, sx = 0, sy = 0;
    vp.addEventListener("mousedown", (e) => {
      if (!e.shiftKey || e.button !== 0) return;
      boxSelecting = true;
      const r = vp.getBoundingClientRect();
      sx = e.clientX - r.left;
      sy = e.clientY - r.top;
      overlay.style.left = sx + "px";
      overlay.style.top = sy + "px";
      overlay.style.width = "0px";
      overlay.style.height = "0px";
      overlay.style.display = "block";
    });

    window.addEventListener("mousemove", (e) => {
      if (!boxSelecting) return;
      const r = vp.getBoundingClientRect();
      const cx = e.clientX - r.left;
      const cy = e.clientY - r.top;
      overlay.style.left = Math.min(sx, cx) + "px";
      overlay.style.top = Math.min(sy, cy) + "px";
      overlay.style.width = Math.abs(cx - sx) + "px";
      overlay.style.height = Math.abs(cy - sy) + "px";
    });

    window.addEventListener("mouseup", () => {
      if (!boxSelecting) return;
      boxSelecting = false;
      overlay.style.display = "none";
    });
  }


  // =========================================================================
  // ARMA 3 EDEN-STYLE 3D MISSION & CAMPAIGN BUILDER (DIRECT IN 3D VIEWPORT)
  // =========================================================================
  let edenMode = ""; // "" | "waypoint" | "trigger" | "task" | "link"
  let edenCampaign = { level: "l01_escape", mission_name: "Operation_Escape", entities: [], links: [] };
  let edenGroup3D = null;
  let edenLinkStartId = null;
  let selectedEdenEntity = null;

  function injectArmaEdenToolbar() {
    const toolbar = document.querySelector("#tab-map .viewport-toolbar");
    if (!toolbar || document.getElementById("edenToolbarBar")) return;

    const toggleBtn = document.createElement("button");
    toggleBtn.className = "btn";
    toggleBtn.id = "btnToggleDirector";
    toggleBtn.style.cssText = "padding:4px 9px;font-size:11px;background:rgba(16,185,129,0.14);border:1px solid #059669;color:#34d399;font-weight:700;";
    toggleBtn.title = "Shortcut: Q — Open Zone 3D Director for waypoints, trigger zones & quest targets";
    toggleBtn.innerHTML = `Zone 3D Director (Q) <span id="edenCountBadge" style="background:#065f46;padding:1px 5px;border-radius:4px;margin-left:3px;">0</span>`;
    toolbar.appendChild(toggleBtn);

    const vpEl = document.getElementById("mapCanvas");
    const bar = document.createElement("div");
    bar.id = "edenToolbarBar";
    bar.style.cssText = "display:none;position:absolute;top:12px;right:12px;width:310px;background:rgba(15,23,42,0.96);border:1.5px solid #059669;border-radius:8px;padding:12px;z-index:40;color:#e2e8f0;font-size:12px;box-shadow:0 12px 30px rgba(0,0,0,0.8);";
    bar.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;border-bottom:1px solid #1e293b;padding-bottom:6px;">
        <span style="font-size:12px;font-weight:700;color:#34d399;">Zone 3D Director (Quest & AI)</span>
        <button class="btn" id="btnCloseDirector" style="padding:2px 7px;font-size:11px;"></button>
      </div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;line-height:1.4;">
        Place waypoints, trigger zones, and quest targets directly on the 3D terrain or drag existing markers with the <b>left mouse button</b>.
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;">
        <button class="btn" id="btnEdenWaypoint" title="Place a 3D AI waypoint (MOVE / PATROL / ASSAULT / GUARD) directly on the terrain" style="padding:5px 8px;font-size:11px;">+Waypoint</button>
        <button class="btn" id="btnEdenTrigger" title="Place a 3D spherical trigger zone (on_actor_inside) on the map" style="padding:5px 8px;font-size:11px;">+Trigger Zone</button>
        <button class="btn" id="btnEdenTask" title="Pin a 3D quest target marker directly to a location on the 3D map" style="padding:5px 8px;font-size:11px;">+Quest Target</button>
        <button class="btn" id="btnEdenLink" title="Connect two 3D objects (Waypoint -> Waypoint or Trigger -> Quest) with a 3D link" style="padding:5px 8px;font-size:11px;">Link Nodes</button>
      </div>
      <button class="btn primary" id="btnEdenSaveCompile" title="Compile all 3D waypoints, triggers, and quests into Anomaly 1.5.3 LTX + String-Table XML" style="width:100%;padding:6px 9px;font-size:11px;background:#059669;border-color:#10b981;">Compile & Save Campaign</button>
    `;
    vpEl?.appendChild(bar);
    toggleBtn.addEventListener("click", () => {
      const opening = bar.style.display === "none";
      bar.style.display = opening ? "block" : "none";
      if (edenGroup3D) edenGroup3D.visible = opening;
      toggleBtn.classList.toggle("primary", opening);
    });
    document.getElementById("btnCloseDirector")?.addEventListener("click", () => {
      bar.style.display = "none";
      edenMode = "";
      if (edenGroup3D) edenGroup3D.visible = false;
      toggleBtn.classList.remove("primary");
    });

    const modes = [
      { id: "btnEdenWaypoint", m: "waypoint" },
      { id: "btnEdenTrigger", m: "trigger" },
      { id: "btnEdenTask", m: "task" },
      { id: "btnEdenLink", m: "link" },
    ];
    modes.forEach(({ id, m }) => {
      document.getElementById(id)?.addEventListener("click", () => {
        edenMode = edenMode === m ? "" : m;
        edenLinkStartId = null;
        modes.forEach((x) => document.getElementById(x.id)?.classList.toggle("primary", edenMode === x.m));
      });
    });

    document.getElementById("btnEdenSaveCompile")?.addEventListener("click", async () => {
      const lvl = getCurrentLevel() || "l01_escape";
      edenCampaign.level = lvl;
      const res = await fetch("/api/eden/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(edenCampaign),
      });
      const out = await res.json();
      if (out.ok) {
        (window.showStudioToast || alert)(`Zone 3D Director campaign for '${lvl}' compiled & saved!\n\n• 3D Objects: ${out.entities_count}\n• Sync Links: ${out.links_count}\n\nYou can now export it with 1 click as a .db0 / .zip mod archive!`);
      }
    });

    // Direct LMB Dragging for Zone 3D Director objects + Click handler for placing/linking
    const vp = document.getElementById("mapCanvas");
    let draggingEdenEnt = null;
    let draggingEdenMoved = false;
    let edenDownPt = { x: 0, y: 0 };

    vp?.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0 || edenMode || !edenGroup3D || !get3DCamera() || !window.THREE) return;
      edenDownPt = { x: ev.clientX, y: ev.clientY };
      const rect = vp.getBoundingClientRect();
      const mouse = new window.THREE.Vector2(
        ((ev.clientX - rect.left) / rect.width) * 2 - 1,
        -((ev.clientY - rect.top) / rect.height) * 2 + 1
      );
      const raycaster = new window.THREE.Raycaster();
      raycaster.setFromCamera(mouse, get3DCamera());
      const hits = raycaster.intersectObjects(edenGroup3D.children, true);
      const hitObj = hits.find((h) => h.object?.userData?.edenId || h.object?.parent?.userData?.edenId);
      const eid = hitObj?.object?.userData?.edenId || hitObj?.object?.parent?.userData?.edenId;
      if (eid) {
        const ent = (edenCampaign.entities || []).find((x) => x.id === eid);
        if (ent) {
          draggingEdenEnt = ent;
          draggingEdenMoved = false;
          selectedEdenEntity = ent;
          showEdenEntityInspector(ent);
          const ctrl = get3DControls();
          if (ctrl) ctrl.enabled = false;
        }
      }
    });

    window.addEventListener("pointermove", (ev) => {
      if (!draggingEdenEnt || !get3DScene() || !get3DCamera() || !window.THREE) return;
      if (Math.hypot(ev.clientX - edenDownPt.x, ev.clientY - edenDownPt.y) > 3) {
        draggingEdenMoved = true;
      }
      if (draggingEdenMoved) {
        const rect = vp.getBoundingClientRect();
        const mouse = new window.THREE.Vector2(
          ((ev.clientX - rect.left) / rect.width) * 2 - 1,
          -((ev.clientY - rect.top) / rect.height) * 2 + 1
        );
        const raycaster = new window.THREE.Raycaster();
        raycaster.setFromCamera(mouse, get3DCamera());
        const terrainMeshes = get3DScene().children.filter((c) => c !== edenGroup3D);
        const hits = raycaster.intersectObjects(terrainMeshes, true);
        if (hits.length > 0) {
          const pt = hits[0].point;
          draggingEdenEnt.pos = [Number(pt.x.toFixed(2)), Number(pt.y.toFixed(2)), Number(pt.z.toFixed(2))];
          rebuildEden3DObjects();
          showEdenEntityInspector(draggingEdenEnt);
        }
      }
    });

    window.addEventListener("pointerup", () => {
      if (draggingEdenEnt) {
        draggingEdenEnt = null;
        const ctrl = get3DControls();
        if (ctrl) ctrl.enabled = true;
      }
    });

    vp?.addEventListener("click", async (ev) => {
      if (draggingEdenMoved) { draggingEdenMoved = false; return; }
      if (!edenMode || !get3DCamera() || !get3DScene() || !window.THREE) return;
      const rect = vp.getBoundingClientRect();
      const mouse = new window.THREE.Vector2(
        ((ev.clientX - rect.left) / rect.width) * 2 - 1,
        -((ev.clientY - rect.top) / rect.height) * 2 + 1
      );
      const raycaster = new window.THREE.Raycaster();
      raycaster.setFromCamera(mouse, get3DCamera());

      if (edenMode === "link" && edenGroup3D) {
        const hits = raycaster.intersectObjects(edenGroup3D.children, true);
        const hitEnt = hits.find((h) => h.object?.userData?.edenId || h.object?.parent?.userData?.edenId);
        const eid = hitEnt?.object?.userData?.edenId || hitEnt?.object?.parent?.userData?.edenId;
        if (eid) {
          if (!edenLinkStartId) {
            edenLinkStartId = eid;
          } else if (edenLinkStartId !== eid) {
            edenCampaign.links.push({ from: edenLinkStartId, to: eid });
            edenLinkStartId = null;
            rebuildEden3DObjects();
          }
        }
        return;
      }

      const hits = raycaster.intersectObjects(get3DScene().children, true);
      if (!hits.length) return;
      const pt = hits[0].point;
      const lvl = getCurrentLevel() || "l01_escape";

      // Query nearest AI node (< 2 ms C accelerator)
      let lvid = 1, gvid = 1;
      try {
        const nr = await fetch(`/api/nearest_ai_node/${encodeURIComponent(lvl)}?x=${pt.x.toFixed(2)}&y=${pt.y.toFixed(2)}&z=${pt.z.toFixed(2)}`);
        const nd = await nr.json();
        if (nd && typeof nd.level_vertex_id === "number") {
          lvid = nd.level_vertex_id;
          gvid = nd.game_vertex_id || 1;
        }
      } catch (e) {}

      const idx = (edenCampaign.entities?.length || 0) + 1;
      const newEnt = {
        id: `${edenMode}_${idx}`,
        type: edenMode,
        name: edenMode === "waypoint" ? `WP #${idx} (PATROL)` : edenMode === "trigger" ? `Trigger Zone #${idx}` : `Mission Task #${idx}`,
        pos: [Number(pt.x.toFixed(2)), Number(pt.y.toFixed(2)), Number(pt.z.toFixed(2))],
        lvid,
        gvid,
        radius: edenMode === "trigger" ? 12.0 : 2.5,
        wp_behavior: "MOVE",
        move_state: "patrol",
        trigger_cond: "on_actor_inside",
        title_en: `Objective #${idx} on ${lvl}`,
        descr_en: `Reach sector (${pt.x.toFixed(0)}, ${pt.z.toFixed(0)}) and secure the area.`,
        title_ru: `Цель #${idx} (${lvl})`,
        descr_ru: `Достигните сектора (${pt.x.toFixed(0)}, ${pt.z.toFixed(0)}) и зачистите периметр.`,
      };

      // Auto-chain consecutive waypoints like Zone 3D Director!
      if (edenMode === "waypoint") {
        const prevWps = edenCampaign.entities.filter((x) => x.type === "waypoint");
        if (prevWps.length > 0) {
          edenCampaign.links.push({ from: prevWps[prevWps.length - 1].id, to: newEnt.id });
        }
      }

      edenCampaign.entities.push(newEnt);
      selectedEdenEntity = newEnt;
      rebuildEden3DObjects();
      showEdenEntityInspector(newEnt);
    });

    // Load saved Eden campaign whenever level changes (event-driven, zero interval polling)
    let lastCheckedLevel = "";
    window.syncEdenCampaignForLevel = async function (lvlName) {
      const lvl = lvlName || getCurrentLevel() || "";
      if (lvl && lvl !== lastCheckedLevel) {
        lastCheckedLevel = lvl;
        try {
          const r = await fetch(`/api/eden/${encodeURIComponent(lvl)}`);
          edenCampaign = await r.json();
          rebuildEden3DObjects();
        } catch (e) {}
      }
    };
  }

  function rebuildEden3DObjects() {
    const badge = document.getElementById("edenCountBadge");
    if (badge) badge.textContent = String((edenCampaign.entities || []).length);
    if (!get3DScene() || !window.THREE) return;
    const THREE = window.THREE;
    if (edenGroup3D) get3DScene().remove(edenGroup3D);
    edenGroup3D = new THREE.Group();
    edenGroup3D.name = "ArmaEden3DGroup";

    const entMap = {};
    (edenCampaign.entities || []).forEach((e) => {
      entMap[e.id] = e;
      const [x, y, z] = e.pos || [0, 0, 0];

      if (e.type === "waypoint") {
        // Golden Arma-style diamond beacon + vertical pole
        const g = new THREE.Group();
        g.position.set(x, y, z);
        g.userData = { edenId: e.id };
        const pole = new THREE.Mesh(
          new THREE.CylinderGeometry(0.12, 0.12, 3.2, 8),
          new THREE.MeshBasicMaterial({ color: 0xfacc15 })
        );
        pole.position.y = 1.6;
        const diamond = new THREE.Mesh(
          new THREE.OctahedronGeometry(1.1, 0),
          new THREE.MeshBasicMaterial({ color: 0xf59e0b, wireframe: false })
        );
        diamond.position.y = 3.4;
        g.add(pole, diamond);
        edenGroup3D.add(g);
      } else if (e.type === "trigger") {
        // Translucent Cyan/Green Trigger Hemisphere + Ring
        const rad = Math.max(2, Number(e.radius || 12));
        const g = new THREE.Group();
        g.position.set(x, y, z);
        g.userData = { edenId: e.id };
        const dome = new THREE.Mesh(
          new THREE.SphereGeometry(rad, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2),
          new THREE.MeshBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.22, side: THREE.DoubleSide })
        );
        const wire = new THREE.Mesh(
          new THREE.CylinderGeometry(rad, rad, 0.4, 28, 1, true),
          new THREE.MeshBasicMaterial({ color: 0x34d399, wireframe: true })
        );
        g.add(dome, wire);
        edenGroup3D.add(g);
      } else if (e.type === "task") {
        // Purple/Blue Task Objective Pillar
        const g = new THREE.Group();
        g.position.set(x, y, z);
        g.userData = { edenId: e.id };
        const box = new THREE.Mesh(
          new THREE.BoxGeometry(1.8, 1.8, 1.8),
          new THREE.MeshBasicMaterial({ color: 0x38bdf8 })
        );
        box.position.y = 2.6;
        g.add(box);
        edenGroup3D.add(g);
      }
    });

    // Draw 3D Sync / Waypoint Lines
    (edenCampaign.links || []).forEach((lk) => {
      const a = entMap[lk.from];
      const b = entMap[lk.to];
      if (!a || !b) return;
      const p1 = new THREE.Vector3(a.pos[0], a.pos[1] + 2.5, a.pos[2]);
      const p2 = new THREE.Vector3(b.pos[0], b.pos[1] + 2.5, b.pos[2]);
      const geom = new THREE.BufferGeometry().setFromPoints([p1, p2]);
      const color = a.type === "waypoint" && b.type === "waypoint" ? 0xfacc15 : 0x38bdf8;
      const line = new THREE.Line(geom, new THREE.LineBasicMaterial({ color, linewidth: 3 }));
      edenGroup3D.add(line);
    });

    const dirBar = document.getElementById("edenToolbarBar");
    edenGroup3D.visible = Boolean(dirBar && dirBar.style.display !== "none");
    window.edenGroup3D = edenGroup3D;
    get3DScene().add(edenGroup3D);
  }

  function showEdenEntityInspector(ent) {
    const insp = document.getElementById("spawnInspector");
    if (!insp) return;
    insp.innerHTML = `
      <div style="background:#064e3b;padding:8px 10px;border-radius:6px;margin-bottom:10px;color:#ecfdf5;font-weight:700;font-size:12px;">
        Zone 3D Director Object: ${escapeHtml(ent.type.toUpperCase())} (${escapeHtml(ent.id)})
      </div>
      <div style="display:flex;flex-direction:column;gap:8px;font-size:12px;">
        <label>Label / Name:
          <input type="text" id="edName" class="search-box" value="${escapeHtml(ent.name || "")}">
        </label>
        <div style="font-size:11px;color:#94a3b8;">3D-Pos: (${ent.pos.join(", ")}) · AI-Node LVID: <b>${ent.lvid}</b> · GVID: <b>${ent.gvid}</b></div>
        ${
          ent.type === "trigger"
            ? `<label>Trigger Radius (m):
                 <input type="number" id="edRadius" class="search-box" value="${ent.radius || 12}" step="1">
               </label>
               <label>Trigger Condition (sr_idle):
                 <select id="edTrigCond" class="search-box">
                   <option value="on_actor_inside" ${ent.trigger_cond === "on_actor_inside" ? "selected" : ""}>on_actor_inside (Player enters zone)</option>
                   <option value="on_actor_outside" ${ent.trigger_cond === "on_actor_outside" ? "selected" : ""}>on_actor_outside (Actor leaves zone)</option>
                   <option value="on_npc_in_zone" ${ent.trigger_cond === "on_npc_in_zone" ? "selected" : ""}>on_npc_in_zone (NPC enters zone)</option>
                 </select>
               </label>`
            : ""
        }
        ${
          ent.type === "waypoint"
            ? `<label>AI Waypoint Behavior (State):
                 <select id="edMoveState" class="search-box">
                   <option value="patrol" ${ent.move_state === "patrol" ? "selected" : ""}>PATROL (Standard patrol)</option>
                   <option value="assault" ${ent.move_state === "assault" ? "selected" : ""}>ASSAULT (Seek & destroy)</option>
                   <option value="sneak" ${ent.move_state === "sneak" ? "selected" : ""}>STEALTH (Sneak)</option>
                   <option value="guard" ${ent.move_state === "guard" ? "selected" : ""}>GUARD (Hold position)</option>
                 </select>
               </label>`
            : ""
        }
        ${
          ent.type === "task"
            ? `<label>Quest Title (EN):
                 <input type="text" id="edTitleEn" class="search-box" value="${escapeHtml(ent.title_en || "")}">
               </label>
               <label>Quest Title (RU):
                 <input type="text" id="edTitleRu" class="search-box" value="${escapeHtml(ent.title_ru || "")}">
               </label>
               <label>Quest Description (EN):
                 <textarea id="edDescrEn" class="search-box" rows="3">${escapeHtml(ent.descr_en || "")}</textarea>
               </label>`
            : ""
        }
        <div style="display:flex;gap:6px;margin-top:6px;">
          <button class="btn primary" id="btnApplyEdenEnt" style="flex:1;">Apply</button>
          <button class="btn" id="btnDeleteEdenEnt" style="background:#7f1d1d;color:#fecaca;">Delete</button>
        </div>
      </div>
    `;

    document.getElementById("btnApplyEdenEnt")?.addEventListener("click", () => {
      ent.name = document.getElementById("edName")?.value || ent.name;
      if (document.getElementById("edRadius")) ent.radius = parseFloat(document.getElementById("edRadius").value) || 12;
      if (document.getElementById("edTrigCond")) ent.trigger_cond = document.getElementById("edTrigCond").value;
      if (document.getElementById("edMoveState")) ent.move_state = document.getElementById("edMoveState").value;
      if (document.getElementById("edTitleEn")) ent.title_en = document.getElementById("edTitleEn").value;
      if (document.getElementById("edTitleRu")) ent.title_ru = document.getElementById("edTitleRu").value;
      if (document.getElementById("edDescrEn")) ent.descr_en = document.getElementById("edDescrEn").value;
      rebuildEden3DObjects();
    });

    document.getElementById("btnDeleteEdenEnt")?.addEventListener("click", () => {
      edenCampaign.entities = (edenCampaign.entities || []).filter((x) => x.id !== ent.id);
      edenCampaign.links = (edenCampaign.links || []).filter((l) => l.from !== ent.id && l.to !== ent.id);
      rebuildEden3DObjects();
      insp.innerHTML = `<div style="color:var(--muted);padding:12px;">3D object deleted.</div>`;
    });
  }


  // =========================================================================
  // 3D LANDSCAPE SCULPTING, OPENTOPOMAP DEM & HEIGHTMAP IMPORT/EXPORT
  // =========================================================================
  let lsOpen = false;
  let lsBrush = ""; // "" | "raise" | "lower" | "flatten" | "smooth"
  let lsBrushRadius = 22.0;
  let lsBrushStrength = 2.0;
  let lsGridRes = 96;
  let lsWorldSize = 400.0;
  let lsHeights = [];
  let lsMesh3D = null;
  let lsPainting = false;

  function injectLandscapeToolbarAndDrawer() {
    const toolbar = document.querySelector("#tab-map .viewport-toolbar");
    if (!toolbar || document.getElementById("btnToggleLandscape")) return;

    const btn = document.createElement("button");
    btn.className = "btn";
    btn.id = "btnToggleLandscape";
    btn.style.cssText = "padding:5px 10px;font-size:11px;background:rgba(56,189,248,0.14);border-color:#0284c7;color:#7dd3fc;font-weight:700;";
    btn.textContent = "Landscape (L)"; btn.title = "Shortcut: L — 3D Terrain Sculpting, Heightmap & OpenTopoMap";
    toolbar.appendChild(btn);

    const vp = document.getElementById("mapCanvas");
    if (!vp) return;

    const drawer = document.createElement("div");
    drawer.id = "landscapeDrawer";
    drawer.style.cssText = "display:none;position:absolute;top:12px;left:12px;width:340px;max-height:calc(100% - 24px);overflow-y:auto;background:rgba(15,23,42,0.95);border:1.5px solid #0284c7;border-radius:8px;padding:12px;z-index:35;color:#e2e8f0;font-size:12px;box-shadow:0 12px 30px rgba(0,0,0,0.75);";
    drawer.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-weight:700;color:#38bdf8;font-size:13px;">3D Landscape & Heightmap Tools</span>
        <button class="btn" id="btnCloseLandscape" style="padding:2px 7px;font-size:11px;"></button>
      </div>

      <!-- 1. OpenTopoMap & Real-World DEM GPS Import -->
      <div style="background:#0b1120;border:1px solid #1e293b;border-radius:6px;padding:9px;margin-bottom:9px;">
        <div style="font-weight:700;color:#4ade80;font-size:11px;margin-bottom:5px;">1. Real-World OpenTopoMap + DEM Import</div>
        <select id="lsGpsPreset" class="search-box" style="margin-bottom:5px;font-size:11px;">
          <option value="pripyat_center">Pripyat City Center & Ferris Wheel (51.406°N, 30.057°E)</option>
          <option value="cnpp_reactor4">CNPP Reactor 4 & Sarcophagus (51.389°N, 30.099°E)</option>
          <option value="duga_radar">Duga-1 Radar / Brain Scorcher (51.305°N, 30.066°E)</option>
          <option value="red_forest">Red Forest (51.382°N, 30.045°E)</option>
          <option value="yanov_station">Yanov Station (51.392°N, 30.017°E)</option>
          <option value="cooling_pond">CNPP Cooling Pond (51.365°N, 30.145°E)</option>
          <option value="custom">Custom GPS Coordinates (Lat / Lon)...</option>
        </select>
        <div id="lsCustomGpsRow" style="display:none;gap:4px;margin-bottom:5px;">
          <input type="number" id="lsLat" class="search-box" placeholder="Lat (51.389)" value="51.3894" step="0.001" style="flex:1;font-size:11px;">
          <input type="number" id="lsLon" class="search-box" placeholder="Lon (30.099)" value="30.0991" step="0.001" style="flex:1;font-size:11px;">
        </div>
        <button class="btn primary" id="btnFetchOpenTopo" style="width:100%;padding:6px;font-size:11px;font-weight:700;">Load OpenTopoMap + Real DEM Elevation</button>
      </div>

      <!-- 2. File Heightmap Import (.png, 16-bit .raw/.r16, NASA SRTM .hgt, GeoTIFF .tif) -->
      <div style="background:#0b1120;border:1px solid #1e293b;border-radius:6px;padding:9px;margin-bottom:9px;">
        <div style="font-weight:700;color:#38bdf8;font-size:11px;margin-bottom:5px;">2. Import Heightmap File</div>
        <div style="font-size:10px;color:#94a3b8;margin-bottom:5px;">Supported: <code>.png</code> (8/16-Bit), <code>.raw/.r16</code> (World Machine / Gaea / UE5), <code>.hgt</code> (NASA SRTM), <code>.tif/.tiff</code> (GeoTIFF)</div>
        <input type="file" id="lsHeightmapFile" accept=".png,.raw,.r16,.hgt,.tif,.tiff,.jpg,.webp" style="font-size:11px;width:100%;margin-bottom:5px;">
        <div style="display:flex;gap:4px;">
          <button class="btn" id="btnLsPresetValley" style="flex:1;font-size:10px;padding:4px;">Valley</button>
          <button class="btn" id="btnLsPresetCrater" style="flex:1;font-size:10px;padding:4px;">Crater</button>
          <button class="btn" id="btnLsPresetHills" style="flex:1;font-size:10px;padding:4px;">Hills</button>
        </div>
      </div>

      <!-- 3. 3D Sculpting Brushes -->
      <div style="background:#0b1120;border:1px solid #1e293b;border-radius:6px;padding:9px;margin-bottom:9px;">
        <div style="font-weight:700;color:#f59e0b;font-size:11px;margin-bottom:5px;">3. 3D Sculpting Brushes (Paint in Viewport)</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:6px;">
          <button class="btn" id="btnBrushRaise" style="font-size:11px;padding:5px;">Raise</button>
          <button class="btn" id="btnBrushLower" style="font-size:11px;padding:5px;">Lower</button>
          <button class="btn" id="btnBrushFlatten" style="font-size:11px;padding:5px;">Flatten</button>
          <button class="btn" id="btnBrushSmooth" style="font-size:11px;padding:5px;">Smooth</button>
        </div>
        <div style="font-size:11px;margin-bottom:6px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
            <span>Brush Radius (m):</span>
            <input type="number" id="lsRadInput" min="0.5" max="500" step="0.5" value="22" style="width:68px;background:#0b0f17;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:2px 5px;font-size:11px;font-weight:700;text-align:right;">
          </div>
          <input type="range" id="lsRadSlider" min="1" max="120" step="0.5" value="22" style="width:100%;">
        </div>
        <div style="font-size:11px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
            <span>Strength (m):</span>
            <input type="number" id="lsStrInput" min="0.1" max="100" step="0.1" value="2.0" style="width:68px;background:#0b0f17;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:2px 5px;font-size:11px;font-weight:700;text-align:right;">
          </div>
          <input type="range" id="lsStrSlider" min="0.1" max="20.0" step="0.1" value="2.0" style="width:100%;">
        </div>
      </div>

      <!-- 4. Compile to X-Ray level.cform & Export 16-bit Heightmap -->
      <button class="btn primary" id="btnCompileLandscapeCform" style="width:100%;padding:7px;font-weight:700;background:#10b981;border-color:#059669;color:#052e16;">Export level.cform + 16-bit Heightmap PNG</button>
      <div id="lsStatusMsg" style="font-size:11px;color:#4ade80;margin-top:6px;"></div>
    `;
    vp.appendChild(drawer);

    btn.addEventListener("click", () => {
      lsOpen = !lsOpen;
      drawer.style.display = lsOpen ? "block" : "none";
      btn.classList.toggle("primary", lsOpen);
    });
    document.getElementById("btnCloseLandscape")?.addEventListener("click", () => {
      lsOpen = false;
      drawer.style.display = "none";
      btn.classList.remove("primary");
      lsBrush = "";
    });

    document.getElementById("lsGpsPreset")?.addEventListener("change", (e) => {
      const customRow = document.getElementById("lsCustomGpsRow");
      if (customRow) customRow.style.display = e.target.value === "custom" ? "flex" : "none";
    });

    // Fetch live OpenTopoMap + AWS Terrarium DEM
    document.getElementById("btnFetchOpenTopo")?.addEventListener("click", async () => {
      const st = document.getElementById("lsStatusMsg");
      if (st) st.textContent = "Loading DEM elevation data & OpenTopoMap...";
      const preset = document.getElementById("lsGpsPreset").value;
      const body = {
        gps_preset: preset === "custom" ? "" : preset,
        lat: parseFloat(document.getElementById("lsLat")?.value || "51.3894"),
        lon: parseFloat(document.getElementById("lsLon")?.value || "30.0991"),
        grid_res: 96,
        world_size: 400.0,
        exaggeration: 2.5,
      };
      const res = await fetch("/api/landscape/fetch_opentopomap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const out = await res.json();
      if (out.ok) {
        lsGridRes = out.grid_res;
        lsWorldSize = out.world_size;
        lsHeights = out.heights;
        buildOrUpdateLandscapeMesh3D(out.opentopomap_texture_b64);
        if (st) st.textContent = `${out.label} loaded (${out.real_elevation_range_m[0]}m..${out.real_elevation_range_m[1]}m ASL)!`;
      }
    });

    // Upload local Heightmap file (.png, .raw, .r16, .hgt, .tif)
    document.getElementById("lsHeightmapFile")?.addEventListener("change", (e) => {
      const f = e.target.files?.[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = async () => {
        const res = await fetch("/api/landscape/import_heightmap", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: f.name,
            data_b64: reader.result,
            grid_res: 96,
            world_size: 400.0,
            min_height: 0.0,
            max_height: 45.0,
          }),
        });
        const out = await res.json();
        if (out.ok) {
          lsGridRes = out.grid_res;
          lsWorldSize = out.world_size;
          lsHeights = out.heights;
          buildOrUpdateLandscapeMesh3D("");
          const st = document.getElementById("lsStatusMsg");
          if (st) st.textContent = `Heightmap '${f.name}' importiert (${out.vertex_count} Vertices)!`;
        }
      };
      reader.readAsDataURL(f);
    });

    // Procedural presets
    [
      { id: "btnLsPresetValley", p: "valley" },
      { id: "btnLsPresetCrater", p: "crater" },
      { id: "btnLsPresetHills", p: "hills" },
    ].forEach(({ id, p }) => {
      document.getElementById(id)?.addEventListener("click", async () => {
        const res = await fetch("/api/landscape/preset", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ preset: p, grid_res: 96, world_size: 400.0 }),
        });
        const out = await res.json();
        if (out.ok) {
          lsGridRes = out.grid_res;
          lsWorldSize = out.world_size;
          lsHeights = out.heights;
          buildOrUpdateLandscapeMesh3D("");
        }
      });
    });

    // Brush selection
    const brushBtns = [
      { id: "btnBrushRaise", b: "raise" },
      { id: "btnBrushLower", b: "lower" },
      { id: "btnBrushFlatten", b: "flatten" },
      { id: "btnBrushSmooth", b: "smooth" },
    ];
    brushBtns.forEach(({ id, b }) => {
      document.getElementById(id)?.addEventListener("click", () => {
        lsBrush = lsBrush === b ? "" : b;
        brushBtns.forEach((x) => document.getElementById(x.id)?.classList.toggle("primary", lsBrush === x.b));
      });
    });

    const syncLsRad = (val) => {
      const v = parseFloat(val);
      if (isNaN(v) || v <= 0) return;
      lsBrushRadius = v;
      const sl = document.getElementById("lsRadSlider");
      const inp = document.getElementById("lsRadInput");
      if (sl) { if (v > parseFloat(sl.max)) sl.max = String(v); sl.value = String(v); }
      if (inp && document.activeElement !== inp) inp.value = String(v);
    };
    const syncLsStr = (val) => {
      const v = parseFloat(val);
      if (isNaN(v) || v <= 0) return;
      lsBrushStrength = v;
      const sl = document.getElementById("lsStrSlider");
      const inp = document.getElementById("lsStrInput");
      if (sl) { if (v > parseFloat(sl.max)) sl.max = String(v); sl.value = String(v); }
      if (inp && document.activeElement !== inp) inp.value = String(v);
    };
    document.getElementById("lsRadSlider")?.addEventListener("input", (e) => syncLsRad(e.target.value));
    document.getElementById("lsRadInput")?.addEventListener("input", (e) => syncLsRad(e.target.value));
    document.getElementById("lsStrSlider")?.addEventListener("input", (e) => syncLsStr(e.target.value));
    document.getElementById("lsStrInput")?.addEventListener("input", (e) => syncLsStr(e.target.value));

    // Sculpting on 3D Landscape Mesh
    vp.addEventListener("mousedown", (e) => {
      if (lsOpen && lsBrush && e.button === 0 && lsMesh3D) {
        lsPainting = true;
        if (get3DControls()) get3DControls().enabled = false;
        applySculptBrushAtMouse(e);
      }
    });
    window.addEventListener("mousemove", (e) => {
      if (lsPainting && lsOpen && lsBrush) applySculptBrushAtMouse(e);
    });
    window.addEventListener("mouseup", () => {
      if (lsPainting) {
        lsPainting = false;
        if (get3DControls()) get3DControls().enabled = true;
      }
    });

    document.getElementById("btnCompileLandscapeCform")?.addEventListener("click", async () => {
      if (!lsHeights.length) return;
      const lvlName = (getCurrentLevel() || "l99_custom_terrain").replace(":", "_");
      const res = await fetch("/api/landscape/compile_cform", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          level_name: lvlName,
          grid_res: lsGridRes,
          world_size: lsWorldSize,
          heights: lsHeights,
        }),
      });
      const out = await res.json();
      const st = document.getElementById("lsStatusMsg");
      if (out.ok && st) {
        st.innerHTML = `Compiled!<br>• <code>${out.cform_path}</code> (${(out.cform_bytes / 1024).toFixed(1)} KB)<br>• 16-Bit PNG: <code>${out.heightmap_png}</code>`;
      }
    });
  }

  function buildOrUpdateLandscapeMesh3D(topoDataUrl) {
    if (!get3DScene() || !window.THREE || !lsHeights.length) return;
    const THREE = window.THREE;
    if (lsMesh3D) get3DScene().remove(lsMesh3D);

    const geom = new THREE.PlaneGeometry(lsWorldSize, lsWorldSize, lsGridRes - 1, lsGridRes - 1);
    geom.rotateX(-Math.PI / 2);
    const posAttr = geom.attributes.position;
    const colors = new Float32Array(posAttr.count * 3);

    for (let i = 0; i < posAttr.count; i++) {
      const h = lsHeights[i] || 0;
      posAttr.setY(i, h);
      // Natural Zone elevation biome coloring (valley grass -> olive slope -> rocky peak)
      if (h < 4.0) {
        colors[i * 3] = 0.22; colors[i * 3 + 1] = 0.34; colors[i * 3 + 2] = 0.18;
      } else if (h < 18.0) {
        colors[i * 3] = 0.28; colors[i * 3 + 1] = 0.38; colors[i * 3 + 2] = 0.21;
      } else {
        colors[i * 3] = 0.42; colors[i * 3 + 1] = 0.41; colors[i * 3 + 2] = 0.37;
      }
    }
    geom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geom.computeVertexNormals();

    let mat;
    if (topoDataUrl) {
      const tex = new THREE.TextureLoader().load(topoDataUrl);
      mat = new THREE.MeshLambertMaterial({ map: tex, side: THREE.DoubleSide });
    } else {
      mat = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide });
    }

    lsMesh3D = new THREE.Mesh(geom, mat);
    lsMesh3D.name = "SculptableLandscape3D";
    get3DScene().add(lsMesh3D);
  }

  function applySculptBrushAtMouse(ev) {
    const vp = document.getElementById("mapCanvas");
    if (!vp || !lsMesh3D || !get3DCamera() || !window.THREE) return;
    const THREE = window.THREE;
    const rect = vp.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((ev.clientX - rect.left) / rect.width) * 2 - 1,
      -((ev.clientY - rect.top) / rect.height) * 2 + 1
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, get3DCamera());
    const hits = raycaster.intersectObject(lsMesh3D);
    if (!hits.length) return;

    const pt = hits[0].point;
    const posAttr = lsMesh3D.geometry.attributes.position;
    const r2 = lsBrushRadius * lsBrushRadius;

    for (let i = 0; i < posAttr.count; i++) {
      const vx = posAttr.getX(i);
      const vy = posAttr.getY(i);
      const vz = posAttr.getZ(i);
      const d2 = (vx - pt.x) * (vx - pt.x) + (vz - pt.z) * (vz - pt.z);
      if (d2 <= r2) {
        const falloff = 1.0 - Math.sqrt(d2) / lsBrushRadius;
        let nh = vy;
        if (lsBrush === "raise") nh += lsBrushStrength * falloff * 0.35;
        else if (lsBrush === "lower") nh -= lsBrushStrength * falloff * 0.35;
        else if (lsBrush === "flatten") nh = vy + (pt.y - vy) * falloff * 0.4;
        else if (lsBrush === "smooth") nh = vy * 0.85 + pt.y * 0.15;
        lsHeights[i] = Number(nh.toFixed(3));
        posAttr.setY(i, lsHeights[i]);
      }
    }
    posAttr.needsUpdate = true;
    lsMesh3D.geometry.computeVertexNormals();
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initProStudioExtensions);
  } else {
    initProStudioExtensions();
  }

  
  // =========================================================================
  // X-RAY SDK 0.7 FULL PARITY MODULE (SHADERS, PPE, LANIMS, SENV, OMF, VALIDATOR)
  // =========================================================================
  let sdk07Data = null;
  let sdk07SubMode = "shaders";

  window.loadSdk07ParityTab = async function () {
    if (!sdk07Data) {
      try {
        const r = await fetch("/api/sdk07/overview");
        sdk07Data = await r.json();
      } catch (e) {
        console.error("Failed to load SDK 0.7 index:", e);
      }
    }
    window.renderSdk07List();
    window.renderSdk07OverviewDashboard();
  };

  window.switchSdk07Sub = function (mode) {
    sdk07SubMode = mode;
    ["shaders", "ppe", "omf", "diag"].forEach((m) => {
      const btnId = m === "shaders" ? "sdkSubShaders" : m === "ppe" ? "sdkSubPpe" : m === "omf" ? "sdkSubOmf" : "sdkSubDiag";
      document.getElementById(btnId)?.classList.toggle("primary", m === mode);
    });
    window.renderSdk07List();
    if (mode === "diag") {
      window.runSdk07ScriptValidator();
    } else {
      window.renderSdk07OverviewDashboard();
    }
  };

  window.renderSdk07List = function () {
    const listEl = document.getElementById("sdk07ItemList");
    if (!listEl || !sdk07Data) return;
    const q = (document.getElementById("sdk07SearchInput")?.value || "").toLowerCase().trim();

    let items = [];
    if (sdk07SubMode === "shaders") {
      (sdk07Data.shaders_xrlc?.entries || []).forEach((e) => {
        items.push({ title: `[xrLC] ${e.name}`, sub: `Light/Compile Shader · Translucency: ${e.vert_translucency}`, type: "xrlc", data: e });
      });
      ((sdk07Data.shader_files_hlsl?.sample || []) || []).forEach((f) => {
        items.push({ title: `[${f.renderer.toUpperCase()}] ${f.name}`, sub: `${f.rel_path} (${f.size} B)`, type: "file", path: f.rel_path });
      });
    } else if (sdk07SubMode === "ppe") {
      ((sdk07Data.postprocess_ppe?.files || []) || []).forEach((f) => {
        items.push({ title: `${f.name}`, sub: `${f.rel_path} (${f.size} B)`, type: "file", path: f.rel_path });
      });
      (sdk07Data.lanims_xr?.entries || []).forEach((l) => {
        items.push({ title: `[lanim] ${l.name}`, sub: `FPS: ${l.fps} · Frames: ${l.frame_count} · Keys: ${l.keys?.length || 0}`, type: "lanim", data: l });
      });
      ((sdk07Data.senvironment_xr?.environments || []) || []).forEach((z) => {
        items.push({ title: `[SoundEnv] ${z}`, sub: `senvironment.xr EAX/OpenAL Preset`, type: "senv", name: z });
      });
    } else if (sdk07SubMode === "omf") {
      ((sdk07Data.actor_motions_omf?.sample || []) || []).forEach((f) => {
        items.push({ title: `${f.name}`, sub: `${f.rel_path} (${Math.round(f.size / 1024)} KB)`, type: "omf", data: f });
      });
    } else if (sdk07SubMode === "diag") {
      items = [
        { title: "Lua & LTX Bulk Validator", sub: "Validates syntax, brackets & sections in gamedata/", type: "diag_run" },
        { title: "xrLC / CFORM / Spawn Compiler", sub: "Direct bridge to DB0/CFORM/Spawn Repacker", type: "goto_pack" },
      ];
    }

    if (q) {
      items = items.filter((it) => it.title.toLowerCase().includes(q) || it.sub.toLowerCase().includes(q));
    }

    listEl.innerHTML = items.slice(0, 250).map((it, idx) => `
      <div class="list-item" onclick="window.inspectSdk07Item(${idx})" data-sdk-idx="${idx}">
        <div class="title">${escapeHtml(it.title)}</div>
        <div class="meta">${escapeHtml(it.sub)}</div>
      </div>
    `).join("");
    window._currentSdk07Items = items.slice(0, 250);
  };

  window.inspectSdk07Item = async function (idx) {
    const it = (window._currentSdk07Items || [])[idx];
    const mainEl = document.getElementById("sdk07MainContent");
    if (!it || !mainEl) return;

    if (it.type === "file") {
      const r = await fetch(`/api/sdk07/inspect?path=${encodeURIComponent(it.path)}`);
      const d = await r.json();
      if (d.type === "ppe") {
        mainEl.innerHTML = `
          <h3 style="margin-top:0;color:#38bdf8;">Postprocess Effector (.PPE): ${escapeHtml(d.path)}</h3>
          <div style="display:flex;gap:16px;margin-bottom:14px;font-size:12px;color:#94a3b8;">
            <span>File Size: <b>${d.size} Bytes</b></span>
            <span>Version: <b>0x${(d.version || 0).toString(16)}</b></span>
            <span>Float Channels (Duality, Noise, Blur, ColorMatrix): <b>${(d.float_preview || []).length} values</b></span>
          </div>
          <div style="background:#111827;border:1px solid #1e293b;border-radius:8px;padding:12px;margin-bottom:14px;">
            <div style="font-weight:700;color:#f59e0b;margin-bottom:6px;">Channel Curve Values (Float32 Preview):</div>
            <div style="font-family:monospace;font-size:12px;color:#a7f3d0;line-height:1.6;">${(d.float_preview || []).join("  |  ")}</div>
          </div>
          <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;">
            <div style="font-weight:700;color:#93c5fd;margin-bottom:6px;">Binary Hex Dump (First 256 Bytes):</div>
            <pre style="font-family:monospace;font-size:11px;color:#cbd5e1;white-space:pre-wrap;word-break:break-all;margin:0;">${escapeHtml(d.hex_head || "")}</pre>
          </div>
        `;
      } else {
        mainEl.innerHTML = `
          <h3 style="margin-top:0;color:#38bdf8;">Shader Source / Blender Table: ${escapeHtml(d.path)}</h3>
          <textarea style="width:100%;height:72vh;background:#0b1120;color:#e2e8f0;border:1px solid #334155;border-radius:8px;padding:14px;font-family:monospace;font-size:12px;line-height:1.5;" spellcheck="false">${escapeHtml(d.content || "")}</textarea>
        `;
      }
    } else if (it.type === "lanim") {
      const l = it.data;
      const swatchHtml = (l.keys || []).map((k) => {
        const [r, g, b] = k.rgba || [255, 255, 255];
        return `<div style="padding:8px 12px;border-radius:6px;background:rgb(${r},${g},${b});color:${r + g + b > 380 ? '#000' : '#fff'};font-family:monospace;font-size:11px;font-weight:700;">Frame ${k.frame}: rgb(${r},${g},${b})</div>`;
      }).join("");
      mainEl.innerHTML = `
        <h3 style="margin-top:0;color:#facc15;">Light Animation (lanims.xr): ${escapeHtml(l.name)}</h3>
        <p style="font-size:13px;color:#94a3b8;">Speed: <b>${l.fps} FPS</b> · Duration: <b>${l.frame_count} Frames</b> · Keyframes: <b>${(l.keys || []).length}</b></p>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">${swatchHtml}</div>
      `;
    } else if (it.type === "xrlc") {
      const e = it.data;
      mainEl.innerHTML = `
        <h3 style="margin-top:0;color:#38bdf8;">Compiler Shader (shaders_xrlc.xr): ${escapeHtml(e.name)}</h3>
        <div style="background:#111827;border:1px solid #1e293b;border-radius:8px;padding:16px;font-size:13px;line-height:1.8;">
          <div>• <b>Shader Name:</b> <code>${escapeHtml(e.name)}</code></div>
          <div>• <b>Flags (Bitmask):</b> <code>0x${(e.flags || 0).toString(16)}</code></div>
          <div>• <b>Vertex Translucency:</b> <code>${e.vert_translucency}</code></div>
          <div>• <b>Vertex Ambient:</b> <code>${e.vert_ambient}</code></div>
          <div>• <b>Lightmap Density (lm_density):</b> <code>${e.lm_density}</code></div>
        </div>
      `;
    } else if (it.type === "omf") {
      const f = it.data;
      mainEl.innerHTML = `
        <h3 style="margin-top:0;color:#a855f7;">ActorEditor Skeletal Motion (.OMF): ${escapeHtml(f.name)}</h3>
        <p style="font-size:13px;color:#cbd5e1;">Path: <code>${escapeHtml(f.rel_path)}</code> (${f.size.toLocaleString()} Bytes)</p>
        <p style="font-size:12px;color:#94a3b8;">Tip: In the <b>3D OGF, Animations & Textures</b> tab you can preview any 3D model alongside its linked <code>.omf</code> skeletal animations and physics parameters.</p>
        <button class="btn primary" onclick="window.switchTab('ogf')">Open in 3D OGF Viewer (Tab 3)</button>
      `;
    } else if (it.type === "goto_pack") {
      window.switchTab("pack");
    } else if (it.type === "diag_run") {
      window.runSdk07ScriptValidator();
    }
  };

  window.renderSdk07OverviewDashboard = function () {
    const mainEl = document.getElementById("sdk07MainContent");
    if (!mainEl || !sdk07Data) return;
    const m = sdk07Data.sdk07_parity_matrix || {};
    const cardsHtml = Object.entries(m).map(([k, v]) => `
      <div style="background:#111827;border:1px solid #1e293b;border-radius:8px;padding:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <b style="color:#38bdf8;font-size:14px;">${escapeHtml(k)}</b>
          <span style="background:#065f46;color:#a7f3d0;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:700;">AVAILABLE</span>
        </div>
        <div style="font-size:11px;color:#94a3b8;margin-bottom:4px;">Legacy SDK Tool: <code>${escapeHtml(v.sdk_exe)}</code></div>
        <div style="font-size:12px;color:#e2e8f0;">Studio Workspace: <b>${escapeHtml(v.studio_tab)}</b></div>
      </div>
    `).join("");

    mainEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div>
          <h2 style="margin:0;color:#f8fafc;font-size:18px;">Monolith Engine Assets — Shaders, Postprocess (.PPE), Motions & Validator</h2>
          <div style="font-size:12px;color:#94a3b8;margin-top:4px;">Inspect Anomaly 1.5.3 shaders, postprocess effectors (.ppe), light animations (lanims.xr), sound environments, and skeletal motions (.omf)</div>
        </div>
        <button class="btn primary" onclick="window.runSdk07ScriptValidator()">Run Lua & LTX Batch Validator</button>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:10px;margin-bottom:18px;">
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;">
          <div style="font-size:11px;color:#94a3b8;">HLSL / Render Shaders</div>
          <div style="font-size:22px;font-weight:800;color:#38bdf8;">${sdk07Data.shader_files_hlsl?.count || 397}</div>
          <div style="font-size:11px;color:#64748b;">r1 / r2 / r3 (DX10/DX11)</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;">
          <div style="font-size:11px;color:#94a3b8;">Postprocess (.PPE) & Lanims</div>
          <div style="font-size:22px;font-weight:800;color:#f59e0b;">${(sdk07Data.postprocess_ppe?.count || 115) + (sdk07Data.lanims_xr?.count || 192)}</div>
          <div style="font-size:11px;color:#64748b;">${sdk07Data.postprocess_ppe?.count || 115} .ppe + ${sdk07Data.lanims_xr?.count || 192} lanims.xr</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;">
          <div style="font-size:11px;color:#94a3b8;">xrLC Shaders & Sound-Env</div>
          <div style="font-size:22px;font-weight:800;color:#10b981;">${(sdk07Data.shaders_xrlc?.count || 39) + (sdk07Data.senvironment_xr?.count || 18)}</div>
          <div style="font-size:11px;color:#64748b;">39 shaders_xrlc.xr + 18 EAX Zonen</div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;">
          <div style="font-size:11px;color:#94a3b8;">Actor Motions (.OMF)</div>
          <div style="font-size:22px;font-weight:800;color:#a855f7;">${sdk07Data.actor_motions_omf?.count || 200}+</div>
          <div style="font-size:11px;color:#64748b;">Skelett-Animationen</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        ${cardsHtml}
      </div>
    `;
  };

  window.runSdk07ScriptValidator = async function () {
    const mainEl = document.getElementById("sdk07MainContent");
    if (!mainEl) return;
    mainEl.innerHTML = `<div style="color:#38bdf8;font-size:14px;">Validating 400 Lua scripts and 400 LTX configs...</div>`;
    try {
      const r = await fetch("/api/sdk07/validate");
      const d = await r.json();
      mainEl.innerHTML = `
        <h3 style="margin-top:0;color:#10b981;">Lua & LTX Batch Validation Result</h3>
        <div style="display:flex;gap:16px;margin-bottom:14px;">
          <div style="background:#111827;border:1px solid #059669;border-radius:8px;padding:12px;flex:1;">
            <div style="font-size:12px;color:#94a3b8;">Validated Lua Scripts</div>
            <div style="font-size:22px;font-weight:800;color:#34d399;">${d.checked_lua_scripts}</div>
          </div>
          <div style="background:#111827;border:1px solid #0284c7;border-radius:8px;padding:12px;flex:1;">
            <div style="font-size:12px;color:#94a3b8;">Validated LTX Files</div>
            <div style="font-size:22px;font-weight:800;color:#38bdf8;">${d.checked_ltx_configs}</div>
          </div>
          <div style="background:#111827;border:1px solid ${d.issues_count === 0 ? '#059669' : '#e11d48'};border-radius:8px;padding:12px;flex:1;">
            <div style="font-size:12px;color:#94a3b8;">Syntax Errors Found</div>
            <div style="font-size:22px;font-weight:800;color:${d.issues_count === 0 ? '#34d399' : '#f43f5e'};">${d.issues_count}</div>
          </div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:12px;font-size:12px;color:#cbd5e1;">
          ${d.issues_count === 0 ? "All validated Lua scripts and LTX sections are syntactically clean!" : JSON.stringify(d.issues, null, 2)}
        </div>
      `;
    } catch (e) {
      mainEl.innerHTML = `<div style="color:#f43f5e;">Validator Error: ${escapeHtml(String(e))}</div>`;
    }
  };

  // =====================================================================
  // URL PARAMS & AUTOMATED WEB UI QA HARNESS (window.runStudioWebQA)
  // =====================================================================
  function handleUrlParamsAndQA() {
    const params = new URLSearchParams(window.location.search);
    const reqTab = params.get("tab");
    if (reqTab && typeof window.switchTab === "function") {
      window.switchTab(reqTab);
      if (reqTab === "quests" && !questsOverview) loadQuestsAndTipsOverview();
      if (reqTab === "particles" && (!particlesData.particles || !particlesData.particles.length)) loadParticlesCatalog();
      if (reqTab === "sdk07" && typeof window.loadSdk07ParityTab === "function") window.loadSdk07ParityTab();
    }
    if ((params.get("qa_auto") === "1" || params.get("wait_sec")) && !window._qaAutoStarted) {
      window._qaAutoStarted = true;
      const waitParam = params.get("wait_sec");
      const holdImg = document.createElement("img");
      holdImg.src = waitParam
        ? `/api/qa_hold_until_done?timer_only=1&wait=${encodeURIComponent(waitParam)}&t=${Date.now()}`
        : `/api/qa_hold_until_done?t=${Date.now()}`;
      holdImg.style.cssText = "position:fixed;width:1px;height:1px;opacity:0;pointer-events:none;";
      document.body.appendChild(holdImg);
      if (params.get("qa_auto") !== "1") return;
      setTimeout(async () => {
        await loadQuestsAndTipsOverview();
        try {
          // Switch to Dialogs sub-tab and load dm_encrypted_pda (6 phrases)
          document.getElementById("qSubTabDialogs")?.click();
          const res = await fetch("/api/quests/dialog/dm_encrypted_pda");
          graphUndoStack = [];
          graphRedoStack = [];
          currentLayoutMode = "serpentine";
          currentGraph = await res.json();
          computeHierarchicalGraphLayout(currentGraph.nodes || [], currentGraph.edges || [], currentLayoutMode);
          selectedQuestNode = (currentGraph.nodes && currentGraph.nodes[0]) || null;
          renderBlueprintGraph();
          if (selectedQuestNode) await selectBlueprintNode(selectedQuestNode);

          const nEls = Array.from(document.querySelectorAll("#bpNodesContainer .bp-node"));
          const n0 = nEls[0], n1 = nEls[1], n2 = nEls[2], n3 = nEls[3], n4 = nEls[4], n5 = nEls[5];
          const results = {};

          const centerOf = (el) => {
            const r = el.getBoundingClientRect();
            return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
          };
          const hasEdge = (f, t) => (currentGraph.edges || []).some((e) => e.from === f && e.to === t);

          // Test 1: Hold Left Mouse Button & Drag from OUT (phr_0) -> IN (phr_2)
          const p0Out = n0.querySelector(".bp-pin-hit-out");
          const p2In = n2.querySelector(".bp-pin-hit-in");
          const c0Out = centerOf(p0Out), c2In = centerOf(p2In);
          p0Out.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX: c0Out.x, clientY: c0Out.y }));
          window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: Math.round((c0Out.x + c2In.x) / 2), clientY: Math.round((c0Out.y + c2In.y) / 2) }));
          const liveWireDuringDrag1 = Boolean(document.getElementById("bpLiveDragWire"));
          window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: c2In.x, clientY: c2In.y }));
          window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: c2In.x, clientY: c2In.y }));
          results.test1_drag_out_to_in = liveWireDuringDrag1 && hasEdge("phr_0", "phr_2");

          // Test 2: Hold Left Mouse Button & Drag from OUT (phr_1) -> Drop on Target Node Bubble body (phr_4)
          const nEls2 = Array.from(document.querySelectorAll("#bpNodesContainer .bp-node"));
          const p1Out = nEls2[1].querySelector(".bp-pin-hit-out");
          const c1Out = centerOf(p1Out), c4Body = centerOf(nEls2[4].querySelector(".bp-node-header"));
          p1Out.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX: c1Out.x, clientY: c1Out.y }));
          window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: c4Body.x, clientY: c4Body.y }));
          nEls2[4].dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: c4Body.x, clientY: c4Body.y }));
          results.test2_drag_out_to_bubble = hasEdge("phr_1", "phr_4");

          // Test 3: Reverse Hold Left Mouse Button & Drag from IN (phr_5) -> OUT (phr_0)
          const nEls3 = Array.from(document.querySelectorAll("#bpNodesContainer .bp-node"));
          const p5In = nEls3[5].querySelector(".bp-pin-hit-in");
          const p0Out3 = nEls3[0].querySelector(".bp-pin-hit-out");
          const c5In = centerOf(p5In), c0Out3 = centerOf(p0Out3);
          p5In.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX: c5In.x, clientY: c5In.y }));
          window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: c0Out3.x, clientY: c0Out3.y }));
          const liveWireReverse = Boolean(document.getElementById("bpLiveDragWire"));
          window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: c0Out3.x, clientY: c0Out3.y }));
          results.test3_reverse_drag_in_to_out = liveWireReverse && hasEdge("phr_0", "phr_5");

          // Test 4: Two-Click Connection (Click OUT on phr_2, release, move, Click IN on phr_5)
          const nEls4 = Array.from(document.querySelectorAll("#bpNodesContainer .bp-node"));
          const p2Out = nEls4[2].querySelector(".bp-pin-hit-out");
          const p5In4 = nEls4[5].querySelector(".bp-pin-hit-in");
          const c2Out = centerOf(p2Out), c5In4 = centerOf(p5In4);
          p2Out.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX: c2Out.x, clientY: c2Out.y }));
          window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: c2Out.x, clientY: c2Out.y }));
          window.dispatchEvent(new MouseEvent("mousemove", { bubbles: true, clientX: c5In4.x, clientY: c5In4.y }));
          const liveWireTwoClick = Boolean(document.getElementById("bpLiveDragWire"));
          p5In4.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX: c5In4.x, clientY: c5In4.y }));
          results.test4_twoclick_out_to_in = liveWireTwoClick && hasEdge("phr_2", "phr_5");

          // Test 5: Reverse Two-Click Connection (Click IN on phr_3, release, Click Node Bubble on phr_0)
          const nEls5 = Array.from(document.querySelectorAll("#bpNodesContainer .bp-node"));
          const p3In = nEls5[3].querySelector(".bp-pin-hit-in");
          const c3In = centerOf(p3In), c0Bubble = centerOf(nEls5[0].querySelector(".bp-node-header"));
          p3In.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX: c3In.x, clientY: c3In.y }));
          window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, button: 0, clientX: c3In.x, clientY: c3In.y }));
          nEls5[0].dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, clientX: c0Bubble.x, clientY: c0Bubble.y }));
          results.test5_reverse_twoclick_in_to_bubble = hasEdge("phr_0", "phr_3");

          // Test 6: Click SVG Wire Hit-Path to Disconnect (phr_0 -> phr_3)
          const hitEl = document.querySelector('.bp-edge-hit[data-from="phr_0"][data-to="phr_3"]');
          hitEl?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
          results.test6_click_wire_disconnect = Boolean(hitEl) && !hasEdge("phr_0", "phr_3");

          // Test 7: Undo & Redo restores and reapplies the disconnect + 24px Grid Alignment check
          window.undoQuestOrDialogGraph();
          const undoRestored = hasEdge("phr_0", "phr_3");
          window.redoQuestOrDialogGraph();
          const redoRemoved = !hasEdge("phr_0", "phr_3");
          document.getElementById("btnSnapAllNodesToGrid")?.click();
          const allSnapped24 = (currentGraph.nodes || []).every((n) => n.x % 24 === 0 && n.y % 24 === 0);
          results.test7_undo_redo_and_grid24 = undoRestored && redoRemoved && allSnapped24;

          // Test 8: SDK Best Practices UI checks (Resizable textareas, Debug Console Input, Graph Softlock Validator, Zero Emojis in DOM)
          const allTextareasResizable = Array.from(document.querySelectorAll("#tab-quests textarea")).every((ta) => getComputedStyle(ta).resize !== "none");
          const consoleInputExists = Boolean(document.getElementById("v010ConsoleCmdInput"));
          const valRes = await window.validateCurrentStudioGraph();
          const bodyEmojis = (document.body.innerText || "").match(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu) || [];
          // Verify Quest Template dropdown options & Apply button on a task node
          activeSubTab = "tasks";
          const taskNode = { id: "esc_wolf_test_qa", title_en: "Initial Title" };
          let tplTestPassed = false;
          await selectBlueprintNode(taskNode);
          const tplSel = document.getElementById("qiTemplateSelect");
          const optTexts = tplSel ? Array.from(tplSel.options).map((o) => o.textContent.trim()).filter(Boolean) : [];
          if (tplSel && optTexts.length >= 5 && optTexts.some((t) => t.includes("Wolf"))) {
            tplSel.value = "wolf_carpark_box";
            document.getElementById("btnApplyQuestTpl")?.click();
            await new Promise((r) => setTimeout(r, 150));
            const titleVal = document.getElementById("qiTitleEn")?.value || "";
            tplTestPassed = titleVal.includes("Wolf");
          }
          results.test8_sdk_best_practices_ui = Boolean(allTextareasResizable && consoleInputExists && valRes && typeof valRes.error_count === "number" && bodyEmojis.length === 0 && tplTestPassed);

          // Test 9: Tab 2 (3D Map), Tab 3 (3D OGF Viewer), Tab 4 (.db0 Pack), Tab 5 (Handbook) Full Viewport & Zero-German Check
          window.switchTab("map");
          window.dispatchEvent(new Event("resize"));
          await new Promise((r) => setTimeout(r, 350));
          let sdk3dPlaceOk = false;
          if (typeof window.placeStudio3DObject === "function") {
            const pRes = await window.placeStudio3DObject({
              x: -146.5,
              y: -19.8,
              z: -145.2,
              section: "quest_case_01",
              mesh: "dynamics\\equipments\\quest\\box_black.ogf",
              category: "item"
            });
            await new Promise((r) => setTimeout(r, 250));
            const count3D = window.studioPlacementGroup3D ? window.studioPlacementGroup3D.children.length : 0;
            const gizmoOk = Boolean(window.transformControl && window.transformControl.object);
            sdk3dPlaceOk = Boolean(pRes && pRes.ok && count3D >= 1 && gizmoOk);
            if (pRes && pRes.ok && typeof window.deleteSelectedStudio3DObject === "function") {
              await window.deleteSelectedStudio3DObject();
            }
          }
          const mapCanvasEl = document.querySelector("#mapCanvas canvas");
          const mapRect = mapCanvasEl ? mapCanvasEl.getBoundingClientRect() : { width: 0, height: 0 };
          const mapParentRect = document.getElementById("mapCanvas")?.getBoundingClientRect() || { width: 0, height: 0 };
          results.test9_tab2_map_full_viewport = Boolean(
            mapRect.width >= mapParentRect.width - 4 &&
            mapRect.height >= mapParentRect.height - 4 &&
            mapRect.width > 700 &&
            sdk3dPlaceOk
          );

          window.switchTab("ogf");
          if (typeof window.searchOgfList === "function") await window.searchOgfList();
          if (typeof window.loadOgfModel === "function") {
            await window.loadOgfModel("dynamics/weapons/wpn_ak74/wpn_ak74.ogf");
          }
          await new Promise((r) => setTimeout(r, 400));
          const ogfCanvasEl = document.querySelector("#ogfCanvas canvas");
          const ogfRect = ogfCanvasEl ? ogfCanvasEl.getBoundingClientRect() : { width: 0, height: 0 };
          const ogfParentRect = document.getElementById("ogfCanvas")?.getBoundingClientRect() || { width: 0, height: 0 };
          const ogfInspText = document.getElementById("ogfInspector")?.innerText || "";
          const ogfTabText = document.getElementById("tab-ogf")?.innerText || "";
          results.test10_tab3_ogf_full_viewport_and_mesh = Boolean(
            ogfRect.width >= ogfParentRect.width - 4 &&
            ogfRect.height >= ogfParentRect.height - 4 &&
            ogfRect.width > 700 &&
            /19[,.]450/.test(ogfInspText) &&
            !/Modelle|Echte|suchen|Durchsuchen/i.test(ogfTabText)
          );

          window.switchTab("pack");
          await new Promise((r) => setTimeout(r, 150));
          const packText = document.getElementById("tab-pack")?.innerText || "";
          window.switchTab("howto");
          await new Promise((r) => setTimeout(r, 150));
          const howtoText = document.getElementById("tab-howto")?.innerText || "";
          results.test11_tab4_and_tab5_clean_en_ru = Boolean(
            packText.includes("Direct .db0 Mod Archive Builder") &&
            howtoText.includes("Complete Handbook & Workflow Guide") &&
            !/Quell-Ordner|Modulare|Komplettes|Danksagungen/i.test(packText + " " + howtoText)
          );

          // Test 12: Verify all 8 user-reported Quest & 3D fixes in live Gecko DOM
          window.switchTab("quests");
          activeSubTab = "story";
          await loadCampaignGraph("tm_escape.ltx");
          await new Promise((r) => setTimeout(r, 250));
          const campLabels = Array.from(document.getElementById("qCampaignSelect")?.options || []).map((o) => o.textContent.trim());
          const noRawTmNames = campLabels.length >= 25 && campLabels.every((lbl) => !lbl.startsWith("tm_"));

          const beforeTplTitle = document.getElementById("qiTitleEn")?.value || "";
          const tplSel2 = document.getElementById("qiTemplateSelect");
          if (tplSel2 && tplSel2.options.length > 1) {
            tplSel2.selectedIndex = 1;
            tplSel2.dispatchEvent(new Event("change", { bubbles: true }));
          }
          const afterTplChangeOnly = document.getElementById("qiTitleEn")?.value || "";
          const templateWaitForApply = beforeTplTitle === afterTplChangeOnly;

          document.getElementById("btnAddQuestNode")?.click();
          await new Promise((r) => setTimeout(r, 350));
          const selCard = document.querySelector("#bpNodesContainer .bp-node.selected");
          const overlaps = (currentGraph.nodes || []).filter((n) => {
            if (!selectedQuestNode || n.id === selectedQuestNode.id) return false;
            return Math.abs((n.x || 0) - (selectedQuestNode.x || 0)) < 240 && Math.abs((n.y || 0) - (selectedQuestNode.y || 0)) < 95;
          });
          const newNodeNoOverlap = Boolean(selCard && selectedQuestNode && overlaps.length === 0);

          if (typeof window.spawnQuestTargetIn3DWorld === "function") {
            await window.spawnQuestTargetIn3DWorld();
          } else {
            document.getElementById("btnSpawnQuestItem3D")?.click();
            await new Promise((r) => setTimeout(r, 800));
          }
          const spawnBadgeTxt = document.getElementById("qiSpawnLvGvBadge")?.textContent || "";
          const spawnXYZWorked = spawnBadgeTxt.includes("LVID") && spawnBadgeTxt.includes("GVID");

          const zipRes = await window.exportSingleQuestMo2Zip?.();
          const singleMo2ZipWorked = Boolean(zipRes && zipRes.ok && String(zipRes.zip_filename || "").endsWith(".zip"));

          window.toggleQuestLogicGuideModal?.();
          const guideModalOpen = document.getElementById("questLogicGuideModal")?.style?.display === "flex";
          if (params.get("show_guide") !== "1") {
            window.toggleQuestLogicGuideModal?.();
          }

          results.test12_eight_user_fixes_verified = Boolean(
            noRawTmNames &&
            templateWaitForApply &&
            newNodeNoOverlap &&
            spawnXYZWorked &&
            singleMo2ZipWorked &&
            guideModalOpen
          );
          if (!results.test12_eight_user_fixes_verified) {
            results._t12_debug = { noRawTmNames, templateWaitForApply, newNodeNoOverlap, spawnXYZWorked, singleMo2ZipWorked, guideModalOpen };
          }

          // Test 13: Godot-Style Project Manager (project.anomaly) & In-Game Lua Spawn Generator UI Modal Playtest
          const projBtn = document.getElementById("btnV010ProjectMgr");
          projBtn?.click();
          await new Promise((r) => setTimeout(r, 450));
          const projModal = document.getElementById("v010ProjectModal");
          const projModalOpen = Boolean(projModal && projModal.style.display === "flex");
          document.getElementById("btnRegenLuaSpawn")?.click();
          await new Promise((r) => setTimeout(r, 350));
          document.getElementById("btnSaveProjManifest")?.click();
          await new Promise((r) => setTimeout(r, 350));
          const luaTxt = document.getElementById("txtLuaSpawnPreview")?.value || "";
          const luaPreviewValid = luaTxt.includes("alife_create") && luaTxt.includes("spawn_project_entities");
          if (params.get("show_project_modal") !== "1") {
            document.getElementById("btnCloseProjectModal")?.click();
          }
          results.test13_project_manager_and_lua_spawn_ui = Boolean(projBtn && projModalOpen && luaPreviewValid);

          // Test 14: Lua Placer in Tab 2 (Place 3D Object -> Click #btnLuaPlacerSim3D -> Real Lua 5.5 VM ALife Simulation -> Clean up)
          window.switchTab("map");
          await new Promise((r) => setTimeout(r, 350));
          const placedRes = await window.placeStudio3DObject?.({
            x: -145.75,
            y: -19.81,
            z: -144.25,
            rot_y: 135.0,
            section: "stalker_sim_ecolog",
            mesh: "actors\\stalker_ecologist\\stalker_ecolog.ogf",
            category: "npc",
            name: "qa_lua_placer_ecolog",
            story_id: "qa_lua_placer_ecolog_sid"
          });
          await new Promise((r) => setTimeout(r, 250));
          const simBtn3D = document.getElementById("btnLuaPlacerSim3D");
          simBtn3D?.click();
          await new Promise((r) => setTimeout(r, 550));
          const statusBadge3D = document.getElementById("lblLuaPlacerStatus3D")?.textContent || "";
          const luaPlacerPassed = Boolean(
            placedRes?.ok &&
            simBtn3D &&
            statusBadge3D.includes("PASS:") &&
            statusBadge3D.includes("0 reload duplicates")
          );
          if (placedRes?.ok && placedRes?.object?.id && params.get("keep_lua_demo") !== "1") {
            await fetch("/api/placement/action", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ op: "delete", id: placedRes.object.id, level: window.currentLevel || "l01_escape" }),
            });
            window.refreshPlacedObjectsForLevel?.(window.currentLevel || "l01_escape");
          }
          results.test14_lua_placer_3d_to_alife_vm = luaPlacerPassed;

          const endTab = params.get("tab") || "quests";
          window.switchTab(endTab);
          if (endTab === "ogf" && typeof window.loadOgfModel === "function") {
            await window.loadOgfModel("dynamics/weapons/wpn_ak74/wpn_ak74.ogf");
          }
          if (params.get("show_guide") === "1" && document.getElementById("questLogicGuideModal")?.style?.display !== "flex") {
            window.toggleQuestLogicGuideModal?.();
          }
          if (endTab === "map") {
            window.dispatchEvent(new Event("resize"));
            await new Promise((r) => setTimeout(r, 2500));
          } else {
            await new Promise((r) => setTimeout(r, 400));
          }

          await fetch("/api/console_logs/append", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              level: "INFO",
              category: "qa_auto",
              msg_en: "QA_AUTO_RESULT:" + JSON.stringify(results),
              msg_ru: "QA_AUTO_RESULT:" + JSON.stringify(results),
            }),
          });
        } catch (err) {
          await fetch("/api/console_logs/append", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              level: "ERROR",
              category: "qa_auto",
              msg_en: "QA_AUTO_ERROR:" + String(err && err.stack || err),
              msg_ru: "QA_AUTO_ERROR:" + String(err),
            }),
          });
        }
      }, 900);
    }
    const reqDrawer = params.get("drawer");
    if (reqDrawer === "landscape") {
      const d = document.getElementById("landscapeDrawer");
      if (d) d.style.display = "block";
    }
    // Wait until CFORM level 3D geometry is loaded before applying camera/grass/play QA params
    if (params.get("cam") || params.get("grass") === "1" || params.get("play") === "1") {
      let tries = 0;
      const pollTimer = setInterval(() => {
        tries++;
        const ready = typeof cformMeshes !== "undefined" && cformMeshes && cformMeshes[0] && window.mapCamera && window.mapControls;
        if (ready || tries > 35) {
          clearInterval(pollTimer);
          const camStr = params.get("cam");
          if (camStr && window.mapCamera && window.mapControls) {
            const nums = camStr.split(",").map(Number);
            if (nums.length >= 6) {
              window.mapCamera.position.set(nums[0], nums[1], nums[2]);
              window.mapControls.target.set(nums[3], nums[4], nums[5]);
              window.mapControls.update();
            }
          }
          if (params.get("grass") === "1" && typeof window.toggleRealTexturesAndGrass === "function") {
            window.toggleRealTexturesAndGrass(true);
          }
          if (params.get("play") === "1") {
            setTimeout(() => {
              const btn = document.getElementById("btnPlayHere");
              if (btn && (!window.studioPlayMode || !window.studioPlayMode.active)) btn.click();
            }, 350);
          }
        }
      }, 150);
    }
  }

  window.runStudioWebQA = function () {
    const workspaces = Array.from(document.querySelectorAll(".workspace"));
    const visibleWorkspaces = workspaces.filter((w) => getComputedStyle(w).display !== "none");
    const navBtns = Array.from(document.querySelectorAll(".nav-btn"));
    const canvas = document.getElementById("mapCanvas");
    const rect = canvas ? canvas.getBoundingClientRect() : { width: 0, height: 0 };
    return {
      ok: visibleWorkspaces.length === 1 && navBtns.length === 8,
      totalWorkspaces: workspaces.length,
      visibleWorkspaceCount: visibleWorkspaces.length,
      activeWorkspaceId: visibleWorkspaces[0] ? visibleWorkspaces[0].id : null,
      navButtonsCount: navBtns.length,
      navButtonLabels: navBtns.map((b) => b.textContent.trim()),
      mapCanvasSize: { width: Math.round(rect.width), height: Math.round(rect.height) },
      hasEdenToolbar: !!document.getElementById("btnToggleDirector"),
      hasLandscapeToolbar: !!document.getElementById("btnToggleLandscape"),
      hasLandscapeDrawer: !!document.getElementById("landscapeDrawer"),
    };
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(handleUrlParamsAndQA, 200));
  } else {
    setTimeout(handleUrlParamsAndQA, 200);
  }

})();
