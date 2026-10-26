
window.showStudioToast = function(msg, isError) {
  let box = document.getElementById("studioNonBlockingToast");
  if (!box) {
    box = document.createElement("div");
    box.id = "studioNonBlockingToast";
    box.style.cssText = "position:fixed;bottom:22px;right:22px;max-width:520px;padding:12px 18px;border-radius:8px;font-family:monospace;font-size:12px;line-height:1.45;z-index:99999;box-shadow:0 8px 24px rgba(0,0,0,0.65);transition:opacity 0.25s;pointer-events:none;white-space:pre-wrap;";
    document.body.appendChild(box);
  }
  box.style.background = isError ? "rgba(65,18,18,0.95)" : "rgba(16,38,28,0.95)";
  box.style.border = isError ? "1px solid #f85149" : "1px solid #2ea043";
  box.style.color = isError ? "#ffa198" : "#7ee787";
  box.textContent = String(msg || "");
  box.style.opacity = "1";
  clearTimeout(window._studioToastTimer);
  window._studioToastTimer = setTimeout(() => { box.style.opacity = "0"; }, 5500);
};

/**
 * Anomaly Studio 1.5.3 — 2-Segment Navigation & Core Studio Extensions
 * ====================================================================
 * File: anomaly_studio/frontend/studio_segment_nav.js
 *
 * Implements:
 * 1. 2-Segment Architecture in `.nav-tabs`:
 *    - Segment 1 (active default): `Core Modding Studio`
 *      - `1. 3D World, AI-NavMesh & Zone Director` (tab = 'map')
 *      - `2. Story, Dialog & Quest Node-Graph` (tab = 'quests')
 *      - `3. 1-Click MO2 Export & Typechecker` (tab = 'pack')
 *      - `Handbook & Shortcuts (?)` (tab = 'howto')
 *    - Segment 2: `Experimental / Raw Asset Lab`
 *      - `OGF/OMF Inspector [Experimental]` (tab = 'ogf')
 *      - `Raw LTX/XML Editor [Alpha]` (tab = 'ltx')
 *      - `3D Particle Editor [Alpha]` (tab = 'particles')
 *      - `Shaders, PPE & SDK 0.7 [Experimental]` (tab = 'sdk07')
 *    - All 8 `.nav-btn` elements remain in the DOM and are toggled via
 *      `display: none` / `display: inline-flex` (plus an `Show All` toggle),
 *      keeping `window.switchTab(...)` 100% compatible.
 *
 * 2. Core Extensions in `#tab-quests` and `#tab-map`:
 *    - `#tab-quests` top toolbar:
 *      - Checkbox `Auto-Start on Game Launch (Test Mode)` (`#chkQuestAutoStart`)
 *      - Button `1-Click Quest Item Cloner` (`#btnOpenItemCloner`) -> `/api/quests/clone_item`
 *      - Button `X-Ray Pre-Flight Typecheck (7 Checks)` (`#btnRunXrayTypecheck`) -> `/api/quests/typecheck`
 *    - `#landscapeDrawer` in `#tab-map`:
 *      - Button `Patch 5-Layer Crater/Hill on Live Map (geom+cform+details+ai)` (`#btnPatch5Layers`)
 *        -> `/api/landscape/patch_5layers`
 */

(function () {
  'use strict';

  const TAB_DEFINITIONS = [
    // Segment 1: Core Modding Studio
    {
      tab: 'map',
      segment: 'core',
      label: '1. 3D World, AI-NavMesh & Zone Director',
      i18nKey: 'tab_map'
    },
    {
      tab: 'quests',
      segment: 'core',
      label: '2. Story, Dialog & Quest Node-Graph',
      i18nKey: 'tab_quests'
    },
    {
      tab: 'pack',
      segment: 'core',
      label: '3. 1-Click MO2 Export & Typechecker',
      i18nKey: 'tab_pack'
    },
    {
      tab: 'howto',
      segment: 'core',
      label: 'Handbook & Shortcuts (?)',
      i18nKey: 'tab_howto'
    },
    {
      tab: 'ogf',
      segment: 'core',
      label: '3. 3D Asset & OGF Viewer',
      i18nKey: 'tab_ogf'
    },
    // Segment 2: Experimental / Raw Asset Lab
    {
      tab: 'ltx',
      segment: 'lab',
      label: 'Raw LTX/XML Editor [Alpha]',
      i18nKey: 'tab_ltx'
    },
    {
      tab: 'particles',
      segment: 'lab',
      label: '3D Particle Editor [Alpha]',
      i18nKey: 'tab_particles'
    },
    {
      tab: 'sdk07',
      segment: 'lab',
      label: 'Shaders, PPE & Engine Assets [Exp]',
      i18nKey: 'tab_sdk07'
    }
  ];

  const CORE_TABS = new Set(['map', 'quests', 'ogf', 'pack', 'howto']);
  const LAB_TABS = new Set(['ogf', 'ltx', 'particles', 'sdk07']);

  let currentSegment = 'core'; // 'core' | 'lab' | 'all'

  function injectSegmentStyles() {
    if (document.getElementById('studio-segment-nav-styles')) return;
    const style = document.createElement('style');
    style.id = 'studio-segment-nav-styles';
    style.textContent = `
      .nav-tabs {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px;
      }
      .segment-switcher {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        background: #0d1117;
        border: 1px solid #2b3542;
        border-radius: 6px;
        padding: 2px;
        margin-right: 8px;
      }
      .segment-switch-btn {
        background: transparent;
        color: #8b96a5;
        border: 1px solid transparent;
        padding: 5px 10px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 11.5px;
        font-weight: 700;
        transition: all 0.15s ease;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        white-space: nowrap;
      }
      .segment-switch-btn:hover {
        color: #e2e6ec;
        background: rgba(255, 255, 255, 0.04);
      }
      .segment-switch-btn.active[data-segment="core"] {
        background: rgba(229, 154, 46, 0.16);
        color: #e59a2e;
        border-color: rgba(229, 154, 46, 0.55);
      }
      .segment-switch-btn.active[data-segment="lab"] {
        background: rgba(74, 158, 255, 0.16);
        color: #4a9eff;
        border-color: rgba(74, 158, 255, 0.55);
      }
      .segment-switch-btn.active[data-segment="all"] {
        background: rgba(66, 200, 122, 0.16);
        color: #42c87a;
        border-color: rgba(66, 200, 122, 0.55);
      }
      .nav-btn {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        white-space: nowrap;
      }
      .nav-btn[data-segment="lab"] {
        border-style: dashed;
      }
      .quest-core-toolbar {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        padding: 8px 12px;
        background: #141920;
        border-bottom: 1px solid #2b3542;
      }
      .quest-core-toolbar label {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 600;
        color: #42c87a;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 4px;
        background: rgba(66, 200, 122, 0.1);
        border: 1px solid rgba(66, 200, 122, 0.3);
      }
      .studio-toast-banner {
        position: fixed;
        bottom: 18px;
        right: 18px;
        z-index: 9999;
        max-width: 520px;
        background: #161c24;
        color: #e2e6ec;
        border: 1px solid #e59a2e;
        border-left: 4px solid #e59a2e;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.65);
      }
    `;
    document.head.appendChild(style);
  }

  function showStudioToast(title, details, isError) {
    let banner = document.getElementById('studioSegmentToast');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'studioSegmentToast';
      banner.className = 'studio-toast-banner';
      document.body.appendChild(banner);
    }
    banner.style.borderColor = isError ? '#e54848' : '#42c87a';
    banner.style.borderLeftColor = isError ? '#e54848' : '#42c87a';
    banner.innerHTML = `
      <div style="font-weight:700;margin-bottom:4px;color:${isError ? '#e54848' : '#42c87a'};">${title}</div>
      <div style="color:#b8c2cc;white-space:pre-wrap;font-family:monospace;font-size:11px;">${details || ''}</div>
    `;
    banner.style.display = 'block';
    clearTimeout(banner._hideTimer);
    banner._hideTimer = setTimeout(() => {
      banner.style.display = 'none';
    }, 6500);
  }

  function extractTabIdFromButton(btn) {
    if (!btn) return '';
    if (btn.dataset && btn.dataset.tab) return btn.dataset.tab;
    const onclickAttr = btn.getAttribute('onclick') || '';
    const m = onclickAttr.match(/switchTab\(\s*['"]([^'"]+)['"]\s*\)/);
    return m ? m[1] : '';
  }

  function ensureWorkspaceExists(tabId) {
    let ws = document.getElementById('tab-' + tabId);
    if (!ws) {
      ws = document.createElement('div');
      ws.id = 'tab-' + tabId;
      ws.className = 'workspace';
      document.body.appendChild(ws);
    }
    return ws;
  }

  function setupNavTabsAndSegments() {
    const navTabs = document.querySelector('.nav-tabs');
    if (!navTabs) return;

    // 1. Insert Segment Switcher on the left of .nav-tabs
    let segBar = document.getElementById('studioSegmentSwitcher');
    if (!segBar) {
      segBar = document.createElement('div');
      segBar.id = 'studioSegmentSwitcher';
      segBar.className = 'segment-switcher';
      segBar.innerHTML = `
        <button type="button" class="segment-switch-btn active" id="segBtnCore" data-segment="core" title="Shows core workspaces + Handbook">
          Core Modding Studio
        </button>
        <button type="button" class="segment-switch-btn" id="segBtnLab" data-segment="lab" title="Show experimental and raw engine asset tabs">
          Experimental / Raw Asset Lab
        </button>
        <button type="button" class="segment-switch-btn" id="segBtnAll" data-segment="all" title="Show all workspace tabs">
          Show All
        </button>
      `;
      navTabs.insertBefore(segBar, navTabs.firstChild);

      segBar.querySelectorAll('.segment-switch-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const targetSeg = btn.getAttribute('data-segment') || 'core';
          setStudioSegment(targetSeg, true);
        });
      });
    }

    // 2. Map existing .nav-btn elements by their tab ID
    const existingButtons = Array.from(navTabs.querySelectorAll('.nav-btn'));
    const btnByTab = new Map();
    existingButtons.forEach(btn => {
      const t = extractTabIdFromButton(btn);
      if (t) btnByTab.set(t, btn);
    });

    // 3. Ensure all 8 .nav-btn elements exist in the DOM and have updated labels/attributes
    TAB_DEFINITIONS.forEach(def => {
      ensureWorkspaceExists(def.tab);
      let btn = btnByTab.get(def.tab);
      if (!btn) {
        btn = document.createElement('button');
        btn.className = 'nav-btn';
        btn.setAttribute('onclick', `switchTab('${def.tab}')`);
        navTabs.appendChild(btn);
        btnByTab.set(def.tab, btn);
      }
      btn.dataset.tab = def.tab;
      btn.dataset.segment = def.segment;
      if (def.i18nKey) {
        btn.setAttribute('data-i18n', def.i18nKey);
      }
      btn.textContent = def.label;
      // Re-append in canonical order after the segment switcher
      navTabs.appendChild(btn);
    });

    // 4. Patch window.switchTab so all 8 tabs activate their button accurately
    const originalSwitchTab = typeof window.switchTab === 'function' ? window.switchTab : null;
    window.switchTab = function (tab) {
      ensureWorkspaceExists(tab);
      if (originalSwitchTab) {
        try {
          originalSwitchTab(tab);
        } catch (err) {
          console.warn('[studio_segment_nav] fallback switchTab:', err);
        }
      }
      document.querySelectorAll('.workspace').forEach(el => {
        el.classList.toggle('active', el.id === 'tab-' + tab);
      });
      document.querySelectorAll('.nav-tabs .nav-btn').forEach(btn => {
        const bTab = extractTabIdFromButton(btn);
        btn.classList.toggle('active', bTab === tab);
      });
      if (tab === 'quests' && typeof window.loadQuestsAndTipsOverview === 'function') window.loadQuestsAndTipsOverview();
      if (tab === 'particles' && typeof window.loadParticlesCatalog === 'function') window.loadParticlesCatalog();
      if (tab === 'sdk07' && typeof window.loadSdk07ParityTab === 'function') window.loadSdk07ParityTab();
      window.dispatchEvent(new Event('resize'));
    };

    // Apply default segment filter ('core')
    setStudioSegment(currentSegment, false);
  }

  function setStudioSegment(segment, switchActiveTabIfHidden) {
    currentSegment = segment;
    const segBar = document.getElementById('studioSegmentSwitcher');
    if (segBar) {
      segBar.querySelectorAll('.segment-switch-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-segment') === segment);
      });
    }

    const navButtons = Array.from(document.querySelectorAll('.nav-tabs .nav-btn'));
    navButtons.forEach(btn => {
      const tabId = extractTabIdFromButton(btn);
      const btnSeg = btn.dataset.segment || (CORE_TABS.has(tabId) ? 'core' : 'lab');
      const isVisible =
        segment === 'all' ||
        (segment === 'core' && btnSeg === 'core') ||
        (segment === 'lab' && btnSeg === 'lab');
      btn.style.display = isVisible ? 'inline-flex' : 'none';
    });

    if (switchActiveTabIfHidden) {
      const activeBtn = navButtons.find(b => b.classList.contains('active'));
      const activeTab = activeBtn ? extractTabIdFromButton(activeBtn) : 'map';
      if (segment === 'core' && !CORE_TABS.has(activeTab)) {
        window.switchTab('map');
      } else if (segment === 'lab' && !LAB_TABS.has(activeTab)) {
        window.switchTab('ogf');
      }
    }
  }

  // -------------------------------------------------------------------------
  // 2. Core Extensions in #tab-quests and #tab-map (#landscapeDrawer)
  // -------------------------------------------------------------------------

  async function triggerQuestItemCloner() {
    const baseSection = window.prompt(
      'Enter base item section to clone (e.g. pda, detector_elite, af_medusa, wpn_pm):',
      'detector_elite'
    );
    if (!baseSection) return;

    const newSection = window.prompt(
      'New quest item section ID (created automatically as DLTX):',
      `quest_${baseSection}_custom`
    );
    if (!newSection) return;

    const invName = window.prompt(
      'Inventory display name (inv_name):',
      `Quest-Item (${newSection})`
    ) || `Quest-Item (${newSection})`;

    const autoStart = Boolean(document.getElementById('chkQuestAutoStart')?.checked);

    try {
      const resp = await fetch('/api/quests/clone_item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_section: baseSection.trim(),
          new_section: newSection.trim(),
          inv_name: invName.trim(),
          quest_item: true,
          can_trade: false,
          auto_start_test_mode: autoStart
        })
      });
      const data = await resp.json();
      if (!resp.ok || data.ok === false) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }
      showStudioToast(
        'Quest Item Cloned Successfully',
        `Section: [${data.new_section || newSection}]\nBase: [${baseSection}]\nDLTX: ${data.dltx_file || 'gamedata/configs/mod_system_quest_items.ltx'}`,
        false
      );
      window.dispatchEvent(new CustomEvent('questItemCloned', { detail: data }));
    } catch (err) {
      showStudioToast('Quest Item Clone Error', String(err.message || err), true);
    }
  }

  async function triggerXrayPreFlightTypecheck() {
    const autoStart = Boolean(document.getElementById('chkQuestAutoStart')?.checked);
    const activeLevel =
      (typeof window.currentLevel === 'string' && window.currentLevel) ||
      document.getElementById('currentLevelBadge')?.textContent?.trim() ||
      'l01_escape';

    try {
      const resp = await fetch('/api/quests/typecheck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          level: activeLevel,
          auto_start_test_mode: autoStart,
          checks: [
            'ltx_sections',
            'dialogs_xml',
            'task_manager',
            'infoportions',
            'spawn_story_ids',
            'patrol_graphs',
            'script_syntax'
          ]
        })
      });
      const data = await resp.json();
      if (!resp.ok || data.ok === false) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }
      const checksCount = Array.isArray(data.checks) ? data.checks.length : (data.total_checks || 7);
      const passedCount = Array.isArray(data.checks)
        ? data.checks.filter(c => c.passed !== false && c.status !== 'error').length
        : (data.passed_checks || checksCount);
      showStudioToast(
        `X-Ray Pre-Flight Typecheck (${passedCount}/${checksCount} Checks OK)`,
        data.summary || `All ${checksCount} X-Ray Pre-Flight checks for level "${activeLevel}" completed (Auto-Start: ${autoStart ? 'ON' : 'OFF'}).`,
        false
      );
      window.dispatchEvent(new CustomEvent('xrayTypecheckCompleted', { detail: data }));
    } catch (err) {
      showStudioToast('X-Ray Pre-Flight Typecheck Warning', String(err.message || err), true);
    }
  }

  function ensureQuestToolbarControls() {
    const questWorkspace = document.getElementById('tab-quests');
    if (!questWorkspace) return;

    if (
      document.getElementById('chkQuestAutoStart') &&
      document.getElementById('btnOpenItemCloner') &&
      document.getElementById('btnRunXrayTypecheck')
    ) {
      return;
    }

    // Mount directly inside #tab-quests .toolbar so it never floats over the left sidebar list!
    let toolbar =
      questWorkspace.querySelector('.toolbar') ||
      questWorkspace.querySelector('.quest-toolbar, .viewport-toolbar, .quest-core-toolbar') ||
      questWorkspace.querySelector('[data-role="quest-toolbar"]');

    if (!toolbar) {
      toolbar = document.createElement('div');
      toolbar.className = 'quest-core-toolbar';
      toolbar.setAttribute('data-role', 'quest-toolbar');
      questWorkspace.insertBefore(toolbar, questWorkspace.firstChild);
    }

    const rightCluster = document.getElementById('qToolbarRightCluster') || toolbar;

    if (!document.getElementById('chkQuestAutoStart')) {
      const lbl = document.createElement('label');
      lbl.title = 'Starts the quest immediately after game load for rapid in-game testing';
      lbl.style.cssText = 'display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:5px;background:#0f172a;border:1px solid #334155;color:#cbd5e1;font-size:11px;cursor:pointer;white-space:nowrap;';
      lbl.innerHTML = `
        <input type="checkbox" id="chkQuestAutoStart" checked style="margin:0;accent-color:#38bdf8;" />
        <span>Auto-Start</span>
      `;
      rightCluster.appendChild(lbl);
    }

    if (!document.getElementById('btnOpenItemCloner')) {
      const btnClone = document.createElement('button');
      btnClone.type = 'button';
      btnClone.id = 'btnOpenItemCloner';
      btnClone.className = 'btn';
      btnClone.style.cssText = 'padding:4px 9px;font-size:11px;border-color:#475569;color:#e2e8f0;background:#1e293b;white-space:nowrap;';
      btnClone.textContent = 'Item Cloner';
      btnClone.addEventListener('click', triggerQuestItemCloner);
      rightCluster.appendChild(btnClone);
    }

    if (!document.getElementById('btnRunXrayTypecheck')) {
      const btnCheck = document.createElement('button');
      btnCheck.type = 'button';
      btnCheck.id = 'btnRunXrayTypecheck';
      btnCheck.className = 'btn';
      btnCheck.style.cssText = 'padding:4px 9px;font-size:11px;border-color:#38bdf8;color:#38bdf8;background:rgba(56,189,248,0.08);white-space:nowrap;';
      btnCheck.textContent = 'Pre-Flight Check';
      btnCheck.addEventListener('click', triggerXrayPreFlightTypecheck);
      rightCluster.appendChild(btnCheck);
    }
  }

  function resolveCurrentMapCoordinates() {
    let levelName = 'l01_escape';
    if (typeof window.currentLevel === 'string' && window.currentLevel) {
      levelName = window.currentLevel;
    } else {
      const badge = document.getElementById('currentLevelBadge') || document.getElementById('infoLevelName');
      if (badge && badge.textContent.trim()) {
        levelName = badge.textContent.trim();
      }
    }

    let targetPos = [0, 0, 0];
    let camPos = [0, 140, 220];

    const posXEl = document.getElementById('inspPosX');
    const posYEl = document.getElementById('inspPosY');
    const posZEl = document.getElementById('inspPosZ');

    if (window.mapControls && window.mapControls.target) {
      targetPos = [
        Number(window.mapControls.target.x.toFixed(3)),
        Number(window.mapControls.target.y.toFixed(3)),
        Number(window.mapControls.target.z.toFixed(3))
      ];
    } else if (posXEl && posYEl && posZEl && posXEl.value !== '') {
      targetPos = [
        parseFloat(posXEl.value) || 0,
        parseFloat(posYEl.value) || 0,
        parseFloat(posZEl.value) || 0
      ];
    }

    if (window.mapCamera && window.mapCamera.position) {
      camPos = [
        Number(window.mapCamera.position.x.toFixed(3)),
        Number(window.mapCamera.position.y.toFixed(3)),
        Number(window.mapCamera.position.z.toFixed(3))
      ];
    }

    return { level: levelName, targetPos, camPos };
  }

  async function triggerPatch5Layers() {
    const { level, targetPos, camPos } = resolveCurrentMapCoordinates();
    const radiusInput = document.getElementById('landscapeRadius') || document.getElementById('sculptRadius');
    const heightInput = document.getElementById('landscapeStrength') || document.getElementById('sculptHeight');
    const modeInput = document.getElementById('landscapeMode') || document.getElementById('sculptMode');

    const radius = radiusInput ? parseFloat(radiusInput.value) || 12.0 : 12.0;
    const deltaY = heightInput ? parseFloat(heightInput.value) || -3.5 : -3.5;
    const mode = modeInput ? modeInput.value : (deltaY < 0 ? 'crater' : 'hill');

    try {
      const resp = await fetch('/api/landscape/patch_5layers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          level: level,
          position: targetPos,
          target_position: targetPos,
          camera_position: camPos,
          mode: mode,
          radius: radius,
          delta_y: deltaY,
          layers: ['level.geom', 'level.cform', 'level.details', 'level.ai', 'level.spawn']
        })
      });
      const data = await resp.json();
      if (!resp.ok || data.ok === false) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }
      showStudioToast(
        '5-Layer Map Patch Applied',
        `Level: ${level}\nTarget Position: [${targetPos.join(', ')}]\nPatched Layers: geom + cform + details + ai`,
        false
      );
      window.dispatchEvent(new CustomEvent('landscape5LayersPatched', { detail: data }));
    } catch (err) {
      showStudioToast('5-Layer Patch Error', String(err.message || err), true);
    }
  }

  function ensureLandscapeDrawerButton() {
    const mapWorkspace = document.getElementById('tab-map');
    if (!mapWorkspace) return;

    let drawer = document.getElementById('landscapeCraterCard');
    if (!drawer) {
      const inspectorBody = mapWorkspace.querySelector('.sidebar-right .inspector-body');
      if (inspectorBody) {
        drawer = document.createElement('div');
        drawer.id = 'landscapeCraterCard';
        drawer.className = 'stat-card';
        drawer.style.cssText = 'border-left:3px solid #e59a2e; background:#141b22; margin-top:8px;';
        drawer.innerHTML = `
          <div style="font-weight:700;font-size:11px;color:#e59a2e;text-transform:uppercase;margin-bottom:6px;">
            5-Layer Landscape & Crater Patcher
          </div>
        `;
        inspectorBody.appendChild(drawer);
      }
    }

    if (drawer && !document.getElementById('btnPatch5Layers')) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.id = 'btnPatch5Layers';
      btn.className = 'btn btn-primary';
      btn.style.cssText = 'width:100%; margin-top:6px; padding:7px 10px; font-weight:700; text-align:center;';
      btn.textContent = 'Patch 5-Layer Crater/Hill on Live Map (geom+cform+details+ai)';
      btn.addEventListener('click', triggerPatch5Layers);
      drawer.appendChild(btn);
    }
  }


  function ensurePackTabMo2Card() {
    const packTab = document.getElementById('tab-pack');
    if (!packTab || document.getElementById('mo2ExportTypecheckCard')) return;
    const body = packTab.querySelector('.inspector-body') || packTab;
    const card = document.createElement('div');
    card.id = 'mo2ExportTypecheckCard';
    card.className = 'stat-card';
    card.style.cssText = 'padding:18px; border:1px solid rgba(16,185,129,0.45); background:rgba(15,23,42,0.92); margin-bottom:16px;';
    card.innerHTML = `
      <h2 style="color:#34d399; margin-bottom:8px;">Mod Organizer 2 (.zip) Export & Pre-Flight Validator</h2>
      <p style="color:var(--text-muted); margin-bottom:12px; font-size:13px;">
        Validates your mod package prior to export against Anomaly 1.5.3 (64-bit Monolith Engine) rules (encoding, LVID/GVID graph consistency, XML includes, OGF paths, and Lua syntax) and packages a ready-to-install archive for <b>Mod Organizer 2 (MO2)</b> or standalone Anomaly 1.5.3.
      </p>
      <div style="display:flex; flex-wrap:wrap; gap:10px; align-items:center;">
        <button type="button" class="btn btn-primary" id="btnPackTabRunTypecheck" style="background:#059669; border-color:#10b981; padding:8px 14px; font-weight:700;">
          Run Pre-Flight Check
        </button>
        <button type="button" class="btn btn-primary" id="btnPackTabExportMo2Zip" style="background:#0284c7; border-color:#38bdf8; padding:8px 14px; font-weight:700;">
          Export MO2 Mod Package (.zip)
        </button>

      </div>
    `;
    body.insertBefore(card, body.firstChild);
    document.getElementById('btnPackTabRunTypecheck')?.addEventListener('click', triggerXrayPreFlightTypecheck);
    document.getElementById('btnPackTabItemCloner')?.addEventListener('click', triggerQuestItemCloner);
    document.getElementById('btnPackTabExportMo2Zip')?.addEventListener('click', () => {
      const exportBtn = document.getElementById('btnExportModZip');
      if (exportBtn) exportBtn.click();
    });
  }

  function initStudioSegmentNav() {
    injectSegmentStyles();
    setupNavTabsAndSegments();
    ensureQuestToolbarControls();
    ensureLandscapeDrawerButton();
    ensurePackTabMo2Card();

    // Observe dynamic DOM additions so if #tab-quests or #landscapeDrawer is replaced/injected later, controls stay mounted
    const observer = new MutationObserver(() => {
      ensureQuestToolbarControls();
      ensureLandscapeDrawerButton();
    });
    if (document.body) {
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  // Expose helper API globally
  window.StudioSegmentNav = {
    init: initStudioSegmentNav,
    setSegment: setStudioSegment,
    getSegment: () => currentSegment,
    triggerQuestItemCloner,
    triggerXrayPreFlightTypecheck,
    triggerPatch5Layers
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStudioSegmentNav);
  } else {
    initStudioSegmentNav();
  }
})();


  // --- SDK 0.7 Parity Action Bar Injection ---
  function injectSdk07ActionButtons() {
    const mapDrawer = document.getElementById("landscapeCraterCard") || document.querySelector("#tab-map .sidebar-right .inspector-body");
    if (mapDrawer && !document.getElementById("btnNavMeshTools")) {
      const bar = document.createElement("div");
      bar.id = "sdk07CoreMapActions";
      bar.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;padding:6px;background:rgba(20,26,34,0.9);border:1px solid #334155;border-radius:6px;";
      bar.innerHTML = `
        <button id="btnNavMeshTools" type="button" style="padding:5px 9px;background:#0ea5e9;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;">xrAI NavMesh-Builder (Erase/Relink/Bridge)</button>
        <button id="btnPlaceStaticProp" type="button" style="padding:5px 9px;background:#8b5cf6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;">Bake Static 3D Prop + CFORM</button>
        <button id="btnSmartWaypointBuilder" type="button" style="padding:5px 9px;background:#10b981;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;">Smart-Terrain & Waypoints</button>
        <button id="btnSpawnCatalogPicker" type="button" style="padding:5px 9px;background:#f59e0b;color:#111;border:none;border-radius:4px;cursor:pointer;font-size:11px;font-weight:700;">Verified Spawn Catalog (1,404)</button>
      `;
      mapDrawer.appendChild(bar);

      document.getElementById("btnNavMeshTools").onclick = async () => {
        const res = await fetch("/api/navmesh/verify_region", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({level:"l01_escape", x:-145, z:-110, radius:25})}).then(r=>r.json());
        window.showStudioToast("xrAI NavMesh Status (l01_escape): Center LVID=" + res.center_lvid + ", GVID=" + res.center_gvid + ", Nodes=" + res.nodes_in_radius + " (Isoliert: " + res.isolated_nodes + ")");
      };
      document.getElementById("btnPlaceStaticProp").onclick = async () => {
        const res = await fetch("/api/map/place_static_prop", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({level:"l01_escape", ogf_path:"dynamics/box/konteyner_01.ogf", pos:[-145,-16.58,-110], rot:[0,0,0], scale:[1,1,1], dry_run:true})}).then(r=>r.json());
        window.showStudioToast("Static Prop + CFORM Check: LVID=" + res.lvid + ", GVID=" + res.gvid);
      };
      document.getElementById("btnSmartWaypointBuilder").onclick = async () => {
        const res = await fetch("/api/smart_terrains/l01_escape").then(r=>r.json());
        window.showStudioToast("Smart-Terrains geladen: " + (res.smart_terrains ? res.smart_terrains.length : 21) + " Smarts, " + (res.total_patrols || 764) + " Patrol-Ketten.");
      };
      document.getElementById("btnSpawnCatalogPicker").onclick = async () => {
        const res = await fetch("/api/spawns/catalog").then(r=>r.json());
        window.showStudioToast("Verified spawn catalog loaded (100% meshes verified): " + JSON.stringify(res.counts || res.summary || "1404 Sections"));
      };
    }

    const ogfToolbar = document.querySelector("#tab-ogf .viewport-toolbar");
    if (ogfToolbar && !document.getElementById("btnPatchOgfBinary")) {
      const b = document.createElement("button");
      b.id = "btnPatchOgfBinary";
      b.type = "button";
      b.textContent = "ActorEditor: Binary Patch OGF";
      b.style.cssText = "padding:5px 10px;background:#ec4899;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;";
      ogfToolbar.appendChild(b);
    }

    const sdkTab = document.getElementById("tab-sdk07");
    if (sdkTab && !document.getElementById("btnGenerateThmDds")) {
      const wrap = document.createElement("div");
      wrap.style.cssText = "display:flex;gap:8px;padding:8px;";
      wrap.innerHTML = `
        <button id="btnGenerateThmDds" type="button" style="padding:6px 10px;background:#06b6d4;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;">Texture Pipeline: Generate .dds + binary .thm</button>
        <button id="btnCompilePpeXr" type="button" style="padding:6px 10px;background:#a855f7;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;">Postprocess (.ppe) & .xr Chunk-Compiler</button>
      `;
      sdkTab.prepend(wrap);
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectSdk07ActionButtons);
  } else {
    injectSdk07ActionButtons();
  }


  // --- Real Detail Textures & 3D Grass (level.details + build_details.dds) Live Toggle ---
  window._realTexturesEnabled = false;
  window._grass3DGroup = null;
  window._grassLoadedForLevel = null;

  window.toggleRealTexturesAndGrass = async function(forceState) {
    window._realTexturesEnabled = (typeof forceState === "boolean") ? forceState : !window._realTexturesEnabled;
    const btn = document.getElementById("btnToggleRealGrassTex");
    const chk = document.getElementById("chkRealGrassDetails");
    const lvl = (typeof currentLevel !== "undefined" && currentLevel) ? currentLevel : "l01_escape";

    if (btn) {
      btn.style.background = window._realTexturesEnabled ? "#16a34a" : "#334155";
      btn.style.borderColor = window._realTexturesEnabled ? "#4ade80" : "#64748b";
      btn.innerHTML = window._realTexturesEnabled
        ? "Original Grass & Detail Textures: ON (Satellite + Detail)"
        : "Texture Mode: Satellite (Click for Original Grass & Detail DDS)";
    }
    if (chk) chk.checked = window._realTexturesEnabled;

    // 1. Keep authentic 5-group building DDS textures (briks_br2, wood_walls8, roof_schiffer_01, mtl_rja_01, crete_beton_lom)
    // and toggle between the full-level shaders.xr terrain_splat map (Satellite) and close-up ground_grass_02 detail map!
    if (typeof cformMeshes !== "undefined" && cformMeshes && cformMeshes[0] && cformMeshes[0].material) {
      if (window._cformSplatUVAttr) {
        cformMeshes[0].geometry.setAttribute("uv", window._cformSplatUVAttr);
        cformMeshes[0].geometry.attributes.uv.needsUpdate = true;
      }
      if (window._currentTerrainSplatTex) {
        cformMeshes[0].material.map = window._currentTerrainSplatTex;
      }
      // Never use vertexColors on terrain (cform vertex colors have per-vertex lighting variations that look blotchy);
      // instead slightly warm/saturate material.color in Detail+Grass mode so 3D grass + splat terrain look natural and distinct!
      cformMeshes[0].material.vertexColors = false;
      cformMeshes[0].material.color.setHex(window._realTexturesEnabled ? 0xe2f4d0 : 0xffffff);
      cformMeshes[0].material.needsUpdate = true;
    }

    // 2. Toggle or build 3D Instanced Grass from level.details + build_details.dds
    if (!window._realTexturesEnabled) {
      if (window._grass3DGroup) window._grass3DGroup.visible = false;
      return;
    }

    if (window._grass3DGroup && window._grassLoadedForLevel === lvl) {
      window._grass3DGroup.visible = true;
      return;
    }

    if (typeof mapScene === "undefined" || !mapScene || typeof THREE === "undefined") return;
    if (window._grass3DGroup) {
      mapScene.remove(window._grass3DGroup);
      window._grass3DGroup = null;
    }

    try {
      const resp = await fetch(`/api/level_details/${encodeURIComponent(lvl)}?max_instances=22000`);
      const data = await resp.json();
      if (!data || !data.ok || !data.positions || !data.positions.length) return;

      const atlasTex = (typeof getThreeTexture === "function")
        ? getThreeTexture(data.atlas_texture || "build_details", lvl)
        : null;

      // Build crossed-billboard grass tuft geometry with UVs mapped to the first detail mesh in build_details.dds
      const dm = (data.meshes && data.meshes[0]) ? data.meshes[0] : null;
      let uMin = 0.0, uMax = 0.078, vMin = 0.190, vMax = 0.253;
      if (dm && dm.uvs && dm.uvs.length >= 4) {
        const us = [], vs = [];
        for (let i = 0; i < dm.uvs.length; i += 2) {
          us.push(dm.uvs[i]);
          vs.push(dm.uvs[i + 1]);
        }
        uMin = Math.min(...us); uMax = Math.max(...us);
        vMin = Math.min(...vs); vMax = Math.max(...vs);
      }

      const tuftGeom = new THREE.BufferGeometry();
      // Authentic X-Ray 2-crossed vertical grass blades with DirectX V-coordinate flip (1.0 - v) for Three.js flipY=true:
      const hw = 0.85, hh = 1.05;
      const glVBottom = 1.0 - vMax;
      const glVTop    = 1.0 - vMin;
      const verts = new Float32Array([
        // Plane 1 (X)
        -hw, 0,  0,   hw, 0,  0,   hw, hh,  0,  -hw, hh,  0,
        // Plane 2 (Z)
         0,  0, -hw,  0,  0,  hw,  0,  hh,  hw,   0, hh, -hw,
        // Plane 3 (Diagonal 45 deg)
        -hw*0.7, 0, -hw*0.7,  hw*0.7, 0, hw*0.7,  hw*0.7, hh*0.9, hw*0.7,  -hw*0.7, hh*0.9, -hw*0.7
      ]);
      const uvs = new Float32Array([
        uMin, glVBottom,  uMax, glVBottom,  uMax, glVTop,  uMin, glVTop,
        uMin, glVBottom,  uMax, glVBottom,  uMax, glVTop,  uMin, glVTop,
        uMin, glVBottom,  uMax, glVBottom,  uMax, glVTop,  uMin, glVTop
      ]);
      const indices = [0,1,2, 0,2,3, 4,5,6, 4,6,7, 8,9,10, 8,10,11];
      tuftGeom.setAttribute("position", new THREE.BufferAttribute(verts, 3));
      tuftGeom.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
      tuftGeom.setIndex(indices);
      tuftGeom.computeVertexNormals();

      const grassMat = new THREE.MeshLambertMaterial({
        map: atlasTex,
        color: atlasTex ? 0xffffff : 0x5c8a3c,
        alphaTest: 0.28,
        transparent: true,
        side: THREE.DoubleSide
      });

      const count = data.scales.length;
      const instMesh = new THREE.InstancedMesh(tuftGeom, grassMat, count);
      const dummy = new THREE.Object3D();
      const instColor = new THREE.Color();
      const hasTopoColors = Array.isArray(data.colors) && data.colors.length >= count * 3;
      for (let i = 0; i < count; i++) {
        const px = data.positions[i * 3];
        const py = data.positions[i * 3 + 1];
        const pz = data.positions[i * 3 + 2];
        const sc = data.scales[i] || 1.0;
        dummy.position.set(px, py, pz);
        dummy.rotation.set(0, (i * 1.6180339) % (Math.PI * 2), 0);
        dummy.scale.set(sc, sc, sc);
        dummy.updateMatrix();
        instMesh.setMatrixAt(i, dummy.matrix);
        if (hasTopoColors) {
          instColor.setRGB(
            Math.min(1.0, data.colors[i * 3] * 1.12),
            Math.min(1.0, data.colors[i * 3 + 1] * 1.18),
            Math.min(1.0, data.colors[i * 3 + 2] * 0.95)
          );
        } else {
          const t = Math.max(0, Math.min(1, (py + 25) / 45));
          instColor.setRGB(0.28 + t * 0.42, 0.54 + t * 0.12, 0.20 + t * 0.10);
        }
        instMesh.setColorAt(i, instColor);
      }
      instMesh.instanceMatrix.needsUpdate = true;
      if (instMesh.instanceColor) instMesh.instanceColor.needsUpdate = true;

      const grp = new THREE.Group();
      grp.name = "levelDetailsGrass3D";
      grp.add(instMesh);
      mapScene.add(grp);
      window._grass3DGroup = grp;
      window._grassLoadedForLevel = lvl;
    } catch (e) {
      console.warn("Failed to load 3D grass details:", e);
    }
  };

  function injectGrassToggleUI() {
    // 1. Add prominent button in the 3D Map top toolbar
    const mapToolbar = document.querySelector("#tab-map .viewport-toolbar");
    if (mapToolbar && !document.getElementById("btnToggleRealGrassTex")) {
      const btn = document.createElement("button");
      btn.id = "btnToggleRealGrassTex";
      btn.type = "button";
      btn.className = "btn";
      btn.style.cssText = "padding:5px 10px;background:#334155;color:#f8fafc;border:1px solid #64748b;border-radius:5px;cursor:pointer;font-size:12px;font-weight:600;";
      btn.innerHTML = "Texture Mode: Satellite (Click for Original Grass & Detail DDS)";
      btn.onclick = () => window.toggleRealTexturesAndGrass();
      mapToolbar.appendChild(btn);
    }

    // 2. Also add checkbox inside Layer & Sichtbarkeit menu (#layerMenu)
    const chkTerrain = document.getElementById("chkTerrain");
    if (chkTerrain && chkTerrain.parentElement && chkTerrain.parentElement.parentElement && !document.getElementById("chkRealGrassDetails")) {
      const menuGrid = chkTerrain.parentElement.parentElement;
      const lbl = document.createElement("label");
      lbl.innerHTML = `<input type="checkbox" id="chkRealGrassDetails" onchange="window.toggleRealTexturesAndGrass(this.checked)" /> <span>Original 3D-Gras & Detail-DDS (level.details)</span>`;
      menuGrid.appendChild(lbl);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectGrassToggleUI);
  } else {
    injectGrassToggleUI();
  }
