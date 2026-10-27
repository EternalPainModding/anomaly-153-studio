/**
 * Anomaly 1.5.3 Studio — Play in Editor (PIE) & 1-Click Native X-Ray Engine Launch
 * Mode A: Instant First-Person S.T.A.L.K.E.R. Play-Test Mode inside the 3D Viewport (F5)
 * - PointerLock mouselook + WASD walk, Shift sprint, Space jump, C crouch, F flashlight SpotLight
 * - Real CFORM gravity (9.81 m/s²), 1.70 m eye height, stair/slope climbing & horizontal wall collision
 * - Authentic S.T.A.L.K.E.R. HUD overlay (crosshair, compass/coords, live AI-node, flashlight status,
 * procedural WebAudio Geiger counter / anomaly proximity warning, [F] Use / Inspect prompt)
 * Mode B: 1-Click Launch in Native X-Ray / Anomaly Engine at current camera position (POST /api/play_in_engine)
 * Multilingual: DE / EN / RU
 */
(function () {
 'use strict';

 const PIE_I18N = {
 
 en: {
 btn_play_here: '▶ Play Here (F5)',
 btn_stop_play: '⏹ Stop Play Mode (F5/ESC)',
 btn_play_engine: 'Launch in Anomaly 1.5.3',
 hud_title: ' S.T.A.L.K.E.R. PLAY-IN-EDITOR (PIE)',
 hud_stop_hint: '[ESC / F5] Stop Play Mode',
 hud_controls_hint: 'WASD / Arrows: Walk | Shift: Sprint | Space: Jump | C: Crouch | F: Flashlight / Interact | LMB: Mouselook',
 hud_flashlight_on: ' Flashlight [F]: ON',
 hud_flashlight_off: ' Flashlight [F]: OFF',
 hud_stance_stand: 'STANDING (1.70m)',
 hud_stance_crouch: 'CROUCHED (1.05m)',
 hud_stance_sprint: 'SPRINTING (1.70m)',
 hud_ai_node: 'AI-Node (LVID)',
 hud_geiger_safe: ' GEIGER COUNTER: NOMINAL (0.12 µSv/h)',
 hud_geiger_warn: ' WARNING — ANOMALY DETECTED NEARBY!',
 hud_geiger_danger: ' DANGER — CRITICAL ANOMALY PROXIMITY!',
 hud_interact_prefix: '[F] Use / Inspect:',
 hud_inspected_badge: ' PDA INSPECTION LOCKED',
 modal_title: 'Launch in Anomaly 1.5.3 (64-bit Monolith Engine)',
 modal_sub: 'Launches S.T.A.L.K.E.R. Anomaly 1.5.3 (64-bit Monolith Engine) in the active level at your current 3D camera coordinates.',
 modal_cmd_lbl: 'Copy-ready Launch Command (CLI):',
 modal_ltx_lbl: 'Generated Auto-Teleport & Debug Script (configs/scripts/studio_play_here.ltx):',
 modal_copy_btn: ' Copy Command',
 modal_copied: ' Copied!',
 modal_launch_now: ' Launch Engine Process Now',
 modal_close: 'Close'
 },
 ru: {
 btn_play_here: '▶ Играть здесь (F5)',
 btn_stop_play: '⏹ Остановить игру (F5/ESC)',
 btn_play_engine: 'Запустить в Anomaly 1.5.3',
 hud_title: ' S.T.A.L.K.E.R. ИГРА В РЕДАКТОРЕ (PIE)',
 hud_stop_hint: '[ESC / F5] Выйти из режима игры',
 hud_controls_hint: 'WASD / Стрелки: Шаг | Shift: Бег | Space: Прыжок | C: Присесть | F: Фонарик / Осмотр | LMB: Обзор мыши',
 hud_flashlight_on: ' Фонарик [F]: ВКЛ',
 hud_flashlight_off: ' Фонарик [F]: ВЫКЛ',
 hud_stance_stand: 'СТОЯ (1.70м)',
 hud_stance_crouch: 'ПРИСЕВ (1.05м)',
 hud_stance_sprint: 'БЕГ (1.70м)',
 hud_ai_node: 'AI-узел (LVID)',
 hud_geiger_safe: ' ДОЗИМЕТР: НОРМА (0.12 мкЗв/ч)',
 hud_geiger_warn: ' ВНИМАНИЕ — РЯДОМ АНОМАЛИЯ!',
 hud_geiger_danger: ' ОПАСНОСТЬ — КРИТИЧЕСКАЯ ЗОНА АНОМАЛИИ!',
 hud_interact_prefix: '[F] Использовать / Осмотреть:',
 hud_inspected_badge: ' КПК: ОБЪЕКТ ОСМОТРЕН',
 modal_title: 'Запуск в Anomaly 1.5.3 (64-bit Monolith Engine)',
 modal_sub: 'Запускает S.T.A.L.K.E.R. Anomaly 1.5.3 / OpenXRay на текущей локации в позиции камеры.',
 modal_cmd_lbl: 'Готовая команда запуска (CLI):',
 modal_ltx_lbl: 'Сгенерированный скрипт телепорта (configs/scripts/studio_play_here.ltx):',
 modal_copy_btn: ' Скопировать команду',
 modal_copied: ' Скопировано!',
 modal_launch_now: ' Запустить процесс движка',
 modal_close: 'Закрыть'
 }
 };

 function getLang() {
 if (typeof currentLang !== 'undefined' && PIE_I18N[currentLang]) return currentLang;
 return 'de';
 }

 function t(key) {
 const dict = PIE_I18N[getLang()] || PIE_I18N.de;
 return dict[key] || PIE_I18N.en[key] || key;
 }

 // Expose cformLayerMeshes alias to match both cformMeshes and cformLayerMeshes[0]/[1]
 function syncCformLayerMeshesAlias() {
 if (typeof cformMeshes !== 'undefined' && Array.isArray(cformMeshes)) {
 window.cformLayerMeshes = cformMeshes;
 } else if (!Array.isArray(window.cformLayerMeshes)) {
 window.cformLayerMeshes = [null, null, null, null, null, null];
 }
 return window.cformLayerMeshes;
 }

 // State
 const pieState = {
 active: false,
 keys: {},
 yaw: 0,
 pitch: 0,
 footPos: new THREE.Vector3(0, 0, 0),
 vel: new THREE.Vector3(0, 0, 0),
 eyeHeight: 1.70,
 targetEyeHeight: 1.70,
 standingEyeHeight: 1.70,
 crouchEyeHeight: 1.05,
 gravity: 9.81,
 walkSpeed: 5.2,
 sprintSpeed: 9.0,
 crouchSpeed: 2.6,
 jumpSpeed: 5.8,
 stepHeight: 0.62,
 playerRadius: 0.45,
 grounded: false,
 crouched: false,
 flashlightOn: false,
 flashlight: null,
 flashlightTarget: null,
 headBobTimer: 0,
 lastFrameTime: performance.now(),
 savedCamPos: null,
 savedTargetPos: null,
 savedFogDensity: null,
 currentAiNodeId: '—',
 currentAiNodeDist: 0,
 lastAiFetchTime: 0,
 lastAiQueryPos: new THREE.Vector3(99999, 99999, 99999),
 nearestAnomaly: null,
 nearestAnomalyDist: Infinity,
 focusedSpawnIndex: -1,
 focusedSpawnDist: Infinity,
 inspectedSpawnToastTimer: 0,
 inspectedSpawnText: '',
 audioCtx: null,
 nextGeigerBeepTime: 0,
 geigerMuted: false,
 draggingLook: false
 };

 window.studioPlayMode = pieState;

 // Raycasters reused for 0-alloc physics & interaction
 const downRaycaster = new THREE.Raycaster();
 const wallRaycaster = new THREE.Raycaster();
 const centerRaycaster = new THREE.Raycaster();
 const DOWN_VEC = new THREE.Vector3(0, -1, 0);
 const tempOrigin = new THREE.Vector3();
 const tempDir = new THREE.Vector3();
 const forwardHoriz = new THREE.Vector3();
 const rightHoriz = new THREE.Vector3();
 const wishMove = new THREE.Vector3();
 const camEuler = new THREE.Euler(0, 0, 0, 'YXZ');

 function getCollisionMeshes() {
 const layers = syncCformLayerMeshesAlias();
 const targets = [];
 // Primary collision: cformLayerMeshes[0] (Terrain) and cformLayerMeshes[1] (Buildings, Walls, Roofs & Props)
 if (layers[0]) targets.push(layers[0]);
 if (layers[1]) targets.push(layers[1]);
 return targets;
 }

 // O(1) 2D Spatial Hash Grid over CFORM Terrain & Building triangles (4m x 4m cells)
 // Eliminates 4.5M triangle raycasts per frame in JS -> instant <0.05ms floor & wall physics!
 let _spatialGrid = null;
 let _spatialGridLevel = null;
 let _spatialGridVertRef = null;

 function ensureSpatialGrid() {
 const layers = syncCformLayerMeshesAlias();
 const m0 = layers[0];
 if (!m0 || !m0.geometry) return null;
 const posAttr = m0.geometry.getAttribute('position');
 if (!posAttr) return null;
 const lvl = typeof currentLevel !== 'undefined' ? currentLevel : 'l01_escape';
 if (_spatialGrid && _spatialGridLevel === lvl && _spatialGridVertRef === posAttr.array) {
 return _spatialGrid;
 }

 const pos = posAttr.array;
 const normAttr = m0.geometry.getAttribute('normal');
 const norm = normAttr ? normAttr.array : null;
 const cellSize = 4.0;
 const buckets = new Map();

 function indexMeshTriangles(mesh, isBuilding) {
 if (!mesh || !mesh.geometry || !mesh.geometry.index) return;
 const idx = mesh.geometry.index.array;
 const nIdx = idx.length;
 for (let i = 0; i < nIdx; i += 3) {
 const a = idx[i] * 3, b = idx[i + 1] * 3, c = idx[i + 2] * 3;
 const ax = pos[a], ay = pos[a + 1], az = pos[a + 2];
 const bx = pos[b], by = pos[b + 1], bz = pos[b + 2];
 const cx = pos[c], cy = pos[c + 1], cz = pos[c + 2];
 const minX = Math.min(ax, bx, cx), maxX = Math.max(ax, bx, cx);
 const minZ = Math.min(az, bz, cz), maxZ = Math.max(az, bz, cz);
 // Skip oversized bounding triangles if any
 if (maxX - minX > 64 || maxZ - minZ > 64) continue;
 const gx0 = Math.floor(minX / cellSize), gx1 = Math.floor(maxX / cellSize);
 const gz0 = Math.floor(minZ / cellSize), gz1 = Math.floor(maxZ / cellSize);
 const triTag = isBuilding ? (i | 0x40000000) : i;
 for (let gx = gx0; gx <= gx1; gx++) {
 for (let gz = gz0; gz <= gz1; gz++) {
 const key = (gx * 73856093) ^ (gz * 19349663);
 let arr = buckets.get(key);
 if (!arr) {
 arr = [];
 buckets.set(key, arr);
 }
 arr.push(triTag);
 }
 }
 }
 }

 indexMeshTriangles(layers[0], false);
 indexMeshTriangles(layers[1], true);

 _spatialGrid = {
 cellSize,
 buckets,
 pos,
 norm,
 idx0: layers[0]?.geometry?.index?.array || null,
 idx1: layers[1]?.geometry?.index?.array || null
 };
 _spatialGridLevel = lvl;
 _spatialGridVertRef = pos;
 return _spatialGrid;
 }

 // Query floor Y at (x, z) strictly below maxY (so indoor ceilings/roof rafters above the player's waist are ignored!)
 function queryFloorHeightAt(x, z, maxY, minY) {
 const grid = ensureSpatialGrid();
 if (!grid) return null;
 const gx = Math.floor(x / grid.cellSize);
 const gz = Math.floor(z / grid.cellSize);
 const key = (gx * 73856093) ^ (gz * 19349663);
 const cell = grid.buckets.get(key);
 if (!cell || cell.length === 0) return null;

 const pos = grid.pos;
 let bestY = -Infinity;

 for (let k = 0; k < cell.length; k++) {
 const tag = cell[k];
 const isBld = (tag & 0x40000000) !== 0;
 const i = tag & 0x3fffffff;
 const idxArr = isBld ? grid.idx1 : grid.idx0;
 if (!idxArr) continue;

 const a = idxArr[i] * 3, b = idxArr[i + 1] * 3, c = idxArr[i + 2] * 3;
 const ay = pos[a + 1], by = pos[b + 1], cy = pos[c + 1];
 const triMinY = Math.min(ay, by, cy);
 if (triMinY > maxY) continue;
 const triMaxY = Math.max(ay, by, cy);
 if (triMaxY < minY || triMaxY <= bestY) continue;

 const ax = pos[a], az = pos[a + 2];
 const bx = pos[b], bz = pos[b + 2];
 const cx = pos[c], cz = pos[c + 2];

 // 2D barycentric test in XZ plane
 const v0x = cx - ax, v0z = cz - az;
 const v1x = bx - ax, v1z = bz - az;
 const v2x = x - ax, v2z = z - az;

 const denom = v0x * v1z - v1x * v0z;
 if (Math.abs(denom) < 1e-6) continue;
 const invDenom = 1.0 / denom;
 const u = (v2x * v1z - v1x * v2z) * invDenom;
 if (u < -0.02 || u > 1.02) continue;
 const v = (v0x * v2z - v2x * v0z) * invDenom;
 if (v < -0.02 || u + v > 1.02) continue;

 // Check triangle normal Y (must be walkable surface, not a vertical wall)
 const e1x = bx - ax, e1y = by - ay, e1z = bz - az;
 const e2x = cx - ax, e2y = cy - ay, e2z = cz - az;
 const nx = e1y * e2z - e1z * e2y;
 const ny = e1z * e2x - e1x * e2z;
 const nz = e1x * e2y - e1y * e2x;
 const nLen = Math.hypot(nx, ny, nz);
 if (nLen < 1e-6 || Math.abs(ny / nLen) < 0.48) continue;

 const hitY = ay + u * (cy - ay) + v * (by - ay);
 if (hitY <= maxY && hitY >= minY && hitY > bestY) {
 bestY = hitY;
 }
 }

 return bestY > -Infinity ? bestY : null;
 }

 // Fast 2D horizontal wall push/slide against nearby building/steep triangles in the 3x3 cells around player
 function resolveHorizontalWallCollision(footX, footY, footZ, nextX, nextZ, radius) {
 const grid = ensureSpatialGrid();
 if (!grid) return { x: nextX, z: nextZ, blocked: false };
 const gxCenter = Math.floor(nextX / grid.cellSize);
 const gzCenter = Math.floor(nextZ / grid.cellSize);
 const pos = grid.pos;
 const minCheckY = footY + 0.55;
 const maxCheckY = footY + pieState.eyeHeight - 0.15;
 const rSq = radius * radius;
 let outX = nextX, outZ = nextZ, blocked = false;

 for (let dx = -1; dx <= 1; dx++) {
 for (let dz = -1; dz <= 1; dz++) {
 const key = ((gxCenter + dx) * 73856093) ^ ((gzCenter + dz) * 19349663);
 const cell = grid.buckets.get(key);
 if (!cell) continue;
 for (let k = 0; k < cell.length; k++) {
 const tag = cell[k];
 const isBld = (tag & 0x40000000) !== 0;
 if (!isBld) continue; // Only collide walls on buildings/props layer
 const i = tag & 0x3fffffff;
 const idxArr = grid.idx1;
 if (!idxArr) continue;
 const a = idxArr[i] * 3, b = idxArr[i + 1] * 3, c = idxArr[i + 2] * 3;
 const ay = pos[a + 1], by = pos[b + 1], cy = pos[c + 1];
 if (Math.max(ay, by, cy) < minCheckY || Math.min(ay, by, cy) > maxCheckY) continue;

 const ax = pos[a], az = pos[a + 2];
 const bx = pos[b], bz = pos[b + 2];
 const cx = pos[c], cz = pos[c + 2];

 // Check if steep wall triangle
 const e1x = bx - ax, e1y = by - ay, e1z = bz - az;
 const e2x = cx - ax, e2y = cy - ay, e2z = cz - az;
 const nx = e1y * e2z - e1z * e2y;
 const ny = e1z * e2x - e1x * e2z;
 const nz = e1x * e2y - e1y * e2x;
 const nLen = Math.hypot(nx, ny, nz);
 if (nLen < 1e-6 || Math.abs(ny / nLen) > 0.55) continue;

 // Closest point on 2D segment projection of triangle in XZ
 const edges = [[ax, az, bx, bz], [bx, bz, cx, cz], [cx, cz, ax, az]];
 for (let e = 0; e < 3; e++) {
 const x1 = edges[e][0], z1 = edges[e][1], x2 = edges[e][2], z2 = edges[e][3];
 const vx = x2 - x1, vz = z2 - z1;
 const lenSq = vx * vx + vz * vz;
 const tProj = lenSq > 1e-6 ? Math.max(0, Math.min(1, ((outX - x1) * vx + (outZ - z1) * vz) / lenSq)) : 0;
 const px = x1 + tProj * vx, pz = z1 + tProj * vz;
 const distX = outX - px, distZ = outZ - pz;
 const dSq = distX * distX + distZ * distZ;
 if (dSq < rSq && dSq > 1e-8) {
 const d = Math.sqrt(dSq);
 const push = radius - d;
 outX += (distX / d) * push;
 outZ += (distZ / d) * push;
 blocked = true;
 }
 }
 }
 }
 }
 return { x: outX, z: outZ, blocked };
 }

 function ensureAudioContext() {
 if (pieState.geigerMuted) return null;
 if (!pieState.audioCtx) {
 const AudioCtx = window.AudioContext || window.webkitAudioContext;
 if (AudioCtx) {
 try {
 pieState.audioCtx = new AudioCtx();
 } catch (e) {
 pieState.audioCtx = null;
 }
 }
 }
 if (pieState.audioCtx && pieState.audioCtx.state === 'suspended') {
 pieState.audioCtx.resume().catch(() => {});
 }
 return pieState.audioCtx;
 }

 function playGeigerBeep(intensity) {
 const ctx = ensureAudioContext();
 if (!ctx) return;
 try {
 const now = ctx.currentTime;
 const osc = ctx.createOscillator();
 const gain = ctx.createGain();
 osc.type = intensity > 0.65 ? 'square' : 'sawtooth';
 osc.frequency.setValueAtTime(1350 + Math.random() * 550 + intensity * 600, now);
 gain.gain.setValueAtTime(0.001, now);
 gain.gain.linearRampToValueAtTime(Math.min(0.12, 0.03 + intensity * 0.07), now + 0.003);
 gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.022 + intensity * 0.015);
 osc.connect(gain);
 gain.connect(ctx.destination);
 osc.start(now);
 osc.stop(now + 0.04);
 } catch (e) {}
 }

 function playFlashlightClick(on) {
 const ctx = ensureAudioContext();
 if (!ctx) return;
 try {
 const now = ctx.currentTime;
 const osc = ctx.createOscillator();
 const gain = ctx.createGain();
 osc.type = 'triangle';
 osc.frequency.setValueAtTime(on ? 920 : 640, now);
 gain.gain.setValueAtTime(0.06, now);
 gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.035);
 osc.connect(gain);
 gain.connect(ctx.destination);
 osc.start(now);
 osc.stop(now + 0.04);
 } catch (e) {}
 }

 function ensureFlashlight() {
 if (!mapScene || !mapCamera) return;
 if (!pieState.flashlight) {
 const spot = new THREE.SpotLight(0xfff5dc, 0.0, 75, Math.PI / 5.2, 0.42, 1.35);
 const target = new THREE.Object3D();
 mapScene.add(spot);
 mapScene.add(target);
 spot.target = target;
 pieState.flashlight = spot;
 pieState.flashlightTarget = target;
 }
 }

 function setFlashlight(enabled) {
 ensureFlashlight();
 pieState.flashlightOn = !!enabled;
 if (pieState.flashlight) {
 pieState.flashlight.intensity = pieState.flashlightOn ? 2.85 : 0.0;
 pieState.flashlight.visible = pieState.flashlightOn;
 }
 playFlashlightClick(pieState.flashlightOn);
 updateHudDom();
 }

 function updateFlashlightTransform() {
 if (!pieState.flashlight || !mapCamera) return;
 pieState.flashlight.position.copy(mapCamera.position);
 mapCamera.getWorldDirection(tempDir);
 pieState.flashlightTarget.position.copy(mapCamera.position).addScaledVector(tempDir, 25.0);
 }

 // Inject CSS, Toolbar Buttons, Topbar Buttons, S.T.A.L.K.E.R. HUD, and Engine Launch Modal
 function injectPlayModeUI() {
 if (document.getElementById('studioPlayModeStyles')) return;

 const style = document.createElement('style');
 style.id = 'studioPlayModeStyles';
 style.textContent = `
 .btn-pie-play {
 background: linear-gradient(180deg, #2ea043 0%, #238636 100%) !important;
 color: #ffffff !important;
 border: 1px solid #3fb950 !important;
 font-weight: 700 !important;
 padding: 5px 12px !important;
 border-radius: 5px !important;
 cursor: pointer !important;
 box-shadow: 0 0 10px rgba(66, 200, 122, 0.35);
 transition: all 0.15s ease;
 }
 .btn-pie-play:hover {
 filter: brightness(1.12);
 box-shadow: 0 0 14px rgba(66, 200, 122, 0.6);
 }
 .btn-pie-play.active-play {
 background: linear-gradient(180deg, #e5534b 0%, #b93831 100%) !important;
 border-color: #ff7b72 !important;
 box-shadow: 0 0 12px rgba(229, 83, 75, 0.65);
 }
 .btn-pie-engine {
 background: linear-gradient(180deg, #273445 0%, #1b2430 100%) !important;
 color: #79c0ff !important;
 border: 1px solid #388bfd !important;
 font-weight: 700 !important;
 padding: 5px 11px !important;
 border-radius: 5px !important;
 cursor: pointer !important;
 transition: all 0.15s ease;
 }
 .btn-pie-engine:hover {
 background: #388bfd !important;
 color: #0d1117 !important;
 }
 #stalkerPlayHud {
 position: absolute;
 inset: 0;
 pointer-events: none;
 z-index: 45;
 display: none;
 font-family: 'JetBrains Mono', 'Consolas', monospace;
 user-select: none;
 }
 #stalkerPlayHud.visible {
 display: block;
 }
 .stalker-crosshair {
 position: absolute;
 top: 50%;
 left: 50%;
 transform: translate(-50%, -50%);
 width: 34px;
 height: 34px;
 }
 .stalker-crosshair .ch-dot {
 position: absolute;
 top: 15px;
 left: 15px;
 width: 4px;
 height: 4px;
 border-radius: 50%;
 background: #42c87a;
 box-shadow: 0 0 6px #42c87a;
 }
 .stalker-crosshair .ch-line {
 position: absolute;
 background: rgba(229, 154, 46, 0.88);
 box-shadow: 0 0 4px rgba(0, 0, 0, 0.9);
 }
 .stalker-crosshair .ch-top { top: 2px; left: 16px; width: 2px; height: 8px; }
 .stalker-crosshair .ch-bottom { bottom: 2px; left: 16px; width: 2px; height: 8px; }
 .stalker-crosshair .ch-left { left: 2px; top: 16px; width: 8px; height: 2px; }
 .stalker-crosshair .ch-right { right: 2px; top: 16px; width: 8px; height: 2px; }
 .stalker-range {
 position: absolute;
 top: calc(50% + 22px);
 left: 50%;
 transform: translateX(-50%);
 font-size: 11px;
 color: #e59a2e;
 text-shadow: 0 1px 3px #000;
 }
 .stalker-interact-prompt {
 position: absolute;
 top: calc(50% + 44px);
 left: 50%;
 transform: translateX(-50%);
 background: rgba(12, 16, 20, 0.92);
 border: 1px solid #e59a2e;
 color: #f3f6fa;
 padding: 6px 14px;
 border-radius: 4px;
 font-size: 12px;
 font-weight: 700;
 box-shadow: 0 4px 16px rgba(0,0,0,0.75);
 display: none;
 white-space: nowrap;
 }
 .stalker-top-compass {
 position: absolute;
 top: 56px;
 left: 50%;
 transform: translateX(-50%);
 background: rgba(13, 18, 24, 0.88);
 border: 1px solid #354354;
 border-top: 2px solid #e59a2e;
 padding: 6px 16px;
 border-radius: 5px;
 display: flex;
 align-items: center;
 gap: 16px;
 font-size: 12px;
 color: #dce3ec;
 box-shadow: 0 4px 14px rgba(0,0,0,0.6);
 }
 .stalker-hud-left {
 position: absolute;
 bottom: 48px;
 left: 14px;
 background: rgba(12, 16, 21, 0.90);
 border: 1px solid #303d4d;
 border-left: 3px solid #42c87a;
 padding: 10px 14px;
 border-radius: 5px;
 min-width: 295px;
 color: #dce3ec;
 font-size: 11px;
 line-height: 1.55;
 box-shadow: 0 6px 18px rgba(0,0,0,0.65);
 }
 .stalker-hud-right {
 position: absolute;
 bottom: 48px;
 right: 14px;
 background: rgba(12, 16, 21, 0.90);
 border: 1px solid #303d4d;
 border-right: 3px solid #e59a2e;
 padding: 10px 14px;
 border-radius: 5px;
 min-width: 300px;
 color: #dce3ec;
 font-size: 11px;
 line-height: 1.55;
 box-shadow: 0 6px 18px rgba(0,0,0,0.65);
 }
 .stalker-hud-right.anomaly-danger {
 border-color: #e5534b;
 background: rgba(36, 12, 14, 0.92);
 box-shadow: 0 0 18px rgba(229, 83, 75, 0.55);
 }
 .stalker-bar-track {
 width: 100%;
 height: 6px;
 background: #1a222d;
 border-radius: 3px;
 overflow: hidden;
 margin-top: 3px;
 }
 .stalker-bar-fill {
 height: 100%;
 transition: width 0.1s linear;
 }
 #pieEngineModal {
 position: fixed;
 inset: 0;
 background: rgba(5, 8, 12, 0.78);
 backdrop-filter: blur(4px);
 z-index: 2000;
 display: none;
 align-items: center;
 justify-content: center;
 }
 #pieEngineModal.open {
 display: flex;
 }
 .pie-modal-card {
 background: #151b22;
 border: 1px solid #354354;
 border-top: 3px solid #e59a2e;
 border-radius: 7px;
 width: 680px;
 max-width: 94vw;
 padding: 18px 20px;
 color: #dce3ec;
 box-shadow: 0 14px 40px rgba(0,0,0,0.8);
 }
 .pie-code-box {
 background: #0b0e12;
 border: 1px solid #2a3441;
 border-radius: 4px;
 padding: 9px 11px;
 font-family: 'JetBrains Mono', monospace;
 font-size: 11.5px;
 color: #79c0ff;
 overflow-x: auto;
 white-space: pre-wrap;
 word-break: break-all;
 margin-top: 5px;
 }
 `;
 document.head.appendChild(style);

 // Topbar duplicate buttons removed — kept cleanly in #tab-map .viewport-toolbar (#btnPlayHere & #btnPlayInEngine)

 // 2. Add buttons to 3D Viewport Toolbar (#tab-map .viewport-toolbar)
 const mapToolbar = document.querySelector('#tab-map .viewport-toolbar');
 if (mapToolbar && !document.getElementById('btnPlayHere')) {
 const sep = document.createElement('span');
 sep.style.color = 'var(--border)';
 sep.textContent = '|';

 const btnPlay = document.createElement('button');
 btnPlay.id = 'btnPlayHere';
 btnPlay.className = 'btn btn-pie-play';
 btnPlay.textContent = t('btn_play_here');
 btnPlay.title = 'Shortcut: F5 — First-Person S.T.A.L.K.E.R. Play Mode with CFORM gravity & collision';
 btnPlay.onclick = () => togglePlayHereMode();

 const btnEngine = document.createElement('button');
 btnEngine.id = 'btnPlayInEngine';
 btnEngine.className = 'btn btn-pie-engine';
 btnEngine.textContent = t('btn_play_engine');
 btnEngine.title = 'POST /api/play_in_engine — Generate teleport script & launch native engine here';
 btnEngine.onclick = () => triggerPlayInEngine(false);

 mapToolbar.appendChild(sep);
 mapToolbar.appendChild(btnPlay);
 mapToolbar.appendChild(btnEngine);
 }

 // 3. Inject S.T.A.L.K.E.R. In-Game HUD Overlay inside #tab-map .viewport-container
 const viewportContainer = document.querySelector('#tab-map .viewport-container');
 if (viewportContainer && !document.getElementById('stalkerPlayHud')) {
 const hud = document.createElement('div');
 hud.id = 'stalkerPlayHud';
 hud.innerHTML = `
 <div class="stalker-top-compass">
 <strong style="color:#42c87a;" id="pieHudTitle">${t('hud_title')}</strong>
 <span id="pieCompassReadout" style="color:#e59a2e;font-weight:700;">N 000°</span>
 <span id="pieLevelReadout" style="color:#8b97a8;">l01_escape</span>
 <span id="pieStopHint" style="background:#2a1517;color:#ff7b72;border:1px solid #e5534b;padding:2px 8px;border-radius:4px;font-weight:700;">${t('hud_stop_hint')}</span>
 </div>

 <div class="stalker-crosshair">
 <div class="ch-line ch-top"></div>
 <div class="ch-line ch-bottom"></div>
 <div class="ch-line ch-left"></div>
 <div class="ch-line ch-right"></div>
 <div class="ch-dot" id="pieCrosshairDot"></div>
 </div>
 <div class="stalker-range" id="pieRangeReadout">— m</div>
 <div class="stalker-interact-prompt" id="pieInteractPrompt"></div>

 <div class="stalker-hud-left">
 <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
 <strong style="color:#42c87a;" id="pieStanceReadout">STANDING (1.70m)</strong>
 <span id="pieFlashlightReadout" style="color:#8b97a8;font-weight:700;"> [F]: OFF</span>
 </div>
 <div id="pieCoordsReadout" style="color:#dce3ec;">POS: X 0.00 | Y 0.00 | Z 0.00</div>
 <div id="pieAiNodeReadout" style="color:#79c0ff;">AI-Node (LVID): #—</div>
 <div style="margin-top:6px;">
 <div style="display:flex;justify-content:space-between;font-size:10px;color:#8b97a8;">
 <span>HP 100%</span><span id="pieSpeedReadout">0.0 m/s</span>
 </div>
 <div class="stalker-bar-track">
 <div class="stalker-bar-fill" id="pieStaminaBar" style="width:100%;background:#42c87a;"></div>
 </div>
 </div>
 <div id="pieControlsHint" style="margin-top:6px;font-size:10px;color:#8b97a8;">${t('hud_controls_hint')}</div>
 </div>

 <div class="stalker-hud-right" id="pieAnomalyPanel">
 <div style="font-weight:700;color:#e59a2e;" id="pieGeigerHeader">${t('hud_geiger_safe')}</div>
 <div id="pieAnomalyNearest" style="color:#8b97a8;margin-top:2px;">Nearest Zone: —</div>
 <div class="stalker-bar-track" style="margin-top:5px;">
 <div class="stalker-bar-fill" id="pieAnomalyBar" style="width:4%;background:#e59a2e;"></div>
 </div>
 <div id="pieInspectedToast" style="margin-top:6px;color:#42c87a;font-weight:700;display:none;"></div>
 </div>
 `;
 viewportContainer.appendChild(hud);
 }

 // 4. Inject Engine Launch Modal (Supports Mod Organizer 2 USVFS & Direct Vanilla Binary)
 if (!document.getElementById('pieEngineModal')) {
 const modal = document.createElement('div');
 modal.id = 'pieEngineModal';
 const savedMode = localStorage.getItem('studio_pie_launch_mode') || 'mo2';
 const savedProf = localStorage.getItem('studio_pie_mo2_profile') || 'Default';
 const savedPath = localStorage.getItem('studio_pie_mo2_path') || '';
 modal.innerHTML = `
 <div class="pie-modal-card" style="width:740px;">
 <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
 <h3 style="color:#e59a2e;font-size:15px;" id="pieModalTitle">${t('modal_title')}</h3>
 <button class="btn" id="pieModalCloseTop" style="padding:3px 9px;"></button>
 </div>
 <p style="font-size:12px;color:#8b97a8;margin-bottom:10px;" id="pieModalSub">${t('modal_sub')}</p>
 <div id="pieModalMeta" style="font-size:12px;margin-bottom:10px;color:#42c87a;font-weight:600;"></div>

 <div style="display:grid;grid-template-columns:1.25fr 0.75fr;gap:10px;background:#0e1318;border:1px solid #2a3441;border-radius:6px;padding:10px 12px;margin-bottom:10px;">
 <div>
 <label style="display:block;font-size:11px;color:#8b97a8;font-weight:700;margin-bottom:4px;">Launch Mode:</label>
 <select id="pieLaunchModeSelect" style="width:100%;background:#151c24;border:1px solid #354354;color:#dce3ec;border-radius:4px;padding:5px 8px;font-size:12px;">
 <option value="mo2" ${savedMode === 'mo2' ? 'selected' : ''}>Launch via Mod Organizer 2 (MO2)</option>
 <option value="direct" ${savedMode === 'direct' ? 'selected' : ''}>Direct Launch (Anomaly DX11 Binary)</option>
 </select>
 </div>
 <div>
 <label style="display:block;font-size:11px;color:#8b97a8;font-weight:700;margin-bottom:4px;">MO2 Profile (<span id="pieMo2StatusBadge" style="color:#42c87a;">Detected</span>):</label>
 <select id="pieMo2ProfileSelect" style="width:100%;background:#151c24;border:1px solid #354354;color:#dce3ec;border-radius:4px;padding:5px 8px;font-size:12px;">
 <option value="${savedProf}">${savedProf}</option>
 </select>
 </div>
 <div style="grid-column:1 / -1;">
 <label style="display:block;font-size:11px;color:#8b97a8;font-weight:700;margin-bottom:4px;">Mod Organizer 2 Directory (Live Teleport Mod: <code>+ZZZ_Anomaly_Studio_Live_PIE</code>):</label>
 <input id="pieMo2PathInput" type="text" value="${savedPath}" style="width:100%;box-sizing:border-box;background:#151c24;border:1px solid #354354;color:#a8c5e6;border-radius:4px;padding:5px 8px;font-size:11.5px;font-family:'JetBrains Mono',monospace;" />
 </div>
 </div>

 <div style="margin-bottom:10px;">
 <div style="font-size:11px;color:#8b97a8;font-weight:600;" id="pieModalCmdLbl">${t('modal_cmd_lbl')}</div>
 <div class="pie-code-box" id="pieModalCmdBox"></div>
 </div>
 <div style="margin-bottom:14px;">
 <div style="font-size:11px;color:#8b97a8;font-weight:600;" id="pieModalLtxLbl">${t('modal_ltx_lbl')}</div>
 <div class="pie-code-box" id="pieModalLtxBox" style="max-height:140px;overflow-y:auto;color:#dce3ec;"></div>
 </div>
 <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
 <div style="display:flex;gap:8px;flex-wrap:wrap;">
 <button class="btn btn-pie-play" id="pieModalLaunchBtn">${t('modal_launch_now')}</button>
 <button class="btn btn-pie-engine" id="pieModalLaunchMo2Btn" title="Launches ModOrganizer.exe with USVFS and active +ZZZ_Anomaly_Studio_Live_PIE teleport hook">Launch via MO2</button>
 <button class="btn" id="pieModalLaunchDirectBtn" title="Launch Vanilla AnomalyDX11AVX.exe directly without MO2">Direct Launch (Vanilla)</button>
 <button class="btn" id="pieModalCopyBtn">${t('modal_copy_btn')}</button>
 </div>
 <button class="btn" id="pieModalCloseBtn">${t('modal_close')}</button>
 </div>
 </div>
 `;
 document.body.appendChild(modal);

 const closeModal = () => modal.classList.remove('open');
 document.getElementById('pieModalCloseTop').onclick = closeModal;
 document.getElementById('pieModalCloseBtn').onclick = closeModal;
 modal.addEventListener('click', (e) => {
 if (e.target === modal) closeModal();
 });

 const refreshPreviewFromSelectors = () => {
 const modeEl = document.getElementById('pieLaunchModeSelect');
 const profEl = document.getElementById('pieMo2ProfileSelect');
 const pathEl = document.getElementById('pieMo2PathInput');
 if (modeEl) localStorage.setItem('studio_pie_launch_mode', modeEl.value);
 if (profEl) localStorage.setItem('studio_pie_mo2_profile', profEl.value);
 if (pathEl) localStorage.setItem('studio_pie_mo2_path', pathEl.value);
 triggerPlayInEngine(false, modeEl ? modeEl.value : 'mo2');
 };
 document.getElementById('pieLaunchModeSelect').onchange = refreshPreviewFromSelectors;
 document.getElementById('pieMo2ProfileSelect').onchange = refreshPreviewFromSelectors;
 document.getElementById('pieMo2PathInput').onchange = refreshPreviewFromSelectors;

 document.getElementById('pieModalCopyBtn').onclick = () => {
 const cmdText = document.getElementById('pieModalCmdBox').textContent || '';
 if (navigator.clipboard) {
 navigator.clipboard.writeText(cmdText).catch(() => {});
 }
 const btn = document.getElementById('pieModalCopyBtn');
 btn.textContent = t('modal_copied');
 setTimeout(() => { btn.textContent = t('modal_copy_btn'); }, 2000);
 };
 document.getElementById('pieModalLaunchBtn').onclick = () => {
 const modeEl = document.getElementById('pieLaunchModeSelect');
 triggerPlayInEngine(true, modeEl ? modeEl.value : 'mo2');
 };
 document.getElementById('pieModalLaunchMo2Btn').onclick = () => {
 const modeEl = document.getElementById('pieLaunchModeSelect');
 if (modeEl) modeEl.value = 'mo2';
 localStorage.setItem('studio_pie_launch_mode', 'mo2');
 triggerPlayInEngine(true, 'mo2');
 };
 document.getElementById('pieModalLaunchDirectBtn').onclick = () => {
 const modeEl = document.getElementById('pieLaunchModeSelect');
 if (modeEl) modeEl.value = 'direct';
 localStorage.setItem('studio_pie_launch_mode', 'direct');
 triggerPlayInEngine(true, 'direct');
 };
 }

 // Hook setLanguage so DE/EN/RU buttons also translate PIE UI
 if (typeof window.setLanguage === 'function' && !window.setLanguage._pieHooked) {
 const origSetLang = window.setLanguage;
 const wrapped = function (lang) {
 origSetLang(lang);
 refreshPieTranslations();
 };
 wrapped._pieHooked = true;
 window.setLanguage = wrapped;
 }
 }

 function refreshPieTranslations() {
 const playLabel = pieState.active ? t('btn_stop_play') : t('btn_play_here');
 const b1 = document.getElementById('btnPlayHere');
 const b2 = document.getElementById('btnPlayHereTop');
 if (b1) b1.textContent = playLabel;
 if (b2) b2.textContent = playLabel;

 const e1 = document.getElementById('btnPlayInEngine');
 const e2 = document.getElementById('btnPlayInEngineTop');
 if (e1) e1.textContent = t('btn_play_engine');
 if (e2) e2.textContent = t('btn_play_engine');

 const titleEl = document.getElementById('pieHudTitle');
 if (titleEl) titleEl.textContent = t('hud_title');
 const stopEl = document.getElementById('pieStopHint');
 if (stopEl) stopEl.textContent = t('hud_stop_hint');
 const ctrlEl = document.getElementById('pieControlsHint');
 if (ctrlEl) ctrlEl.textContent = t('hud_controls_hint');

 const mt = document.getElementById('pieModalTitle');
 if (mt) mt.textContent = t('modal_title');
 const ms = document.getElementById('pieModalSub');
 if (ms) ms.textContent = t('modal_sub');
 const mc = document.getElementById('pieModalCmdLbl');
 if (mc) mc.textContent = t('modal_cmd_lbl');
 const ml = document.getElementById('pieModalLtxLbl');
 if (ml) ml.textContent = t('modal_ltx_lbl');
 const mlaunch = document.getElementById('pieModalLaunchBtn');
 if (mlaunch) mlaunch.textContent = t('modal_launch_now');
 const mcopy = document.getElementById('pieModalCopyBtn');
 if (mcopy) mcopy.textContent = t('modal_copy_btn');
 const mclose = document.getElementById('pieModalCloseBtn');
 if (mclose) mclose.textContent = t('modal_close');

 if (pieState.active) updateHudDom();
 }

 // Find initial spawn/drop point on CFORM when entering Play Here (F5)
 function findInitialSpawnFootPosition() {
 const colliders = getCollisionMeshes();
 if (!mapCamera) return new THREE.Vector3(0, 0, 0);

 // 1. Fast spatial grid floor check strictly below camera eye height (never snaps onto roofs above camera!)
 const fastFloorY = queryFloorHeightAt(mapCamera.position.x, mapCamera.position.z, mapCamera.position.y + 0.15, mapCamera.position.y - 60.0);
 if (fastFloorY !== null) {
 return new THREE.Vector3(mapCamera.position.x, fastFloorY, mapCamera.position.z);
 }

 // 2. Fallback raycast directly beneath current camera
 if (colliders.length > 0) {
 tempOrigin.set(mapCamera.position.x, mapCamera.position.y + 0.15, mapCamera.position.z);
 downRaycaster.set(tempOrigin, DOWN_VEC);
 downRaycaster.near = 0.01;
 downRaycaster.far = 45.0;
 const nearHits = downRaycaster.intersectObjects(colliders, false);
 if (nearHits.length > 0) {
 return nearHits[0].point.clone();
 }

 // 2. Raycast along camera view direction toward where user is looking in the editor
 mapCamera.getWorldDirection(tempDir);
 downRaycaster.set(mapCamera.position, tempDir);
 downRaycaster.near = 0.5;
 downRaycaster.far = 2500.0;
 const viewHits = downRaycaster.intersectObjects(colliders, false);
 if (viewHits.length > 0) {
 return viewHits[0].point.clone();
 }

 // 3. Raycast straight down from high above mapControls.target or camera XZ
 const refX = (typeof mapControls !== 'undefined' && mapControls) ? mapControls.target.x : mapCamera.position.x;
 const refZ = (typeof mapControls !== 'undefined' && mapControls) ? mapControls.target.z : mapCamera.position.z;
 tempOrigin.set(refX, 900.0, refZ);
 downRaycaster.set(tempOrigin, DOWN_VEC);
 downRaycaster.near = 0.1;
 downRaycaster.far = 2000.0;
 const skyHits = downRaycaster.intersectObjects(colliders, false);
 if (skyHits.length > 0) {
 return skyHits[0].point.clone();
 }
 }

 // 4. Fallback to selected spawn or camera position
 if (typeof selectedSpawnIndex !== 'undefined' && selectedSpawnIndex >= 0 &&
 typeof currentSpawns !== 'undefined' && currentSpawns[selectedSpawnIndex]) {
 const sp = currentSpawns[selectedSpawnIndex];
 return new THREE.Vector3(sp.position[0], sp.position[1], sp.position[2]);
 }
 return new THREE.Vector3(mapCamera.position.x, mapCamera.position.y - pieState.standingEyeHeight, mapCamera.position.z);
 }

 function startPlayHereMode() {
 if (pieState.active) return;
 if (typeof switchTab === 'function' && !document.getElementById('tab-map')?.classList.contains('active')) {
 switchTab('map');
 }
 if (!mapCamera || !mapRenderer) return;

 syncCformLayerMeshesAlias();
 ensureFlashlight();

 pieState.savedCamPos = mapCamera.position.clone();
 pieState.savedTargetPos = mapControls ? mapControls.target.clone() : new THREE.Vector3();

 // Extract initial camera look yaw & pitch
 mapCamera.getWorldDirection(tempDir);
 pieState.yaw = Math.atan2(-tempDir.x, -tempDir.z);
 pieState.pitch = Math.max(-Math.PI * 0.45, Math.min(Math.PI * 0.45, Math.asin(Math.max(-1, Math.min(1, tempDir.y)))));
 if (pieState.pitch < -0.55) pieState.pitch = -0.12; // Level out steep top-down orbit angle when landing

 const startFoot = findInitialSpawnFootPosition();
 pieState.footPos.copy(startFoot);
 pieState.vel.set(0, 0, 0);
 pieState.crouched = false;
 pieState.eyeHeight = pieState.standingEyeHeight;
 pieState.targetEyeHeight = pieState.standingEyeHeight;
 pieState.grounded = true;
 pieState.keys = {};
 pieState.lastFrameTime = performance.now();

 mapCamera.position.set(
 pieState.footPos.x,
 pieState.footPos.y + pieState.eyeHeight,
 pieState.footPos.z
 );
 camEuler.set(pieState.pitch, pieState.yaw, 0, 'YXZ');
 mapCamera.quaternion.setFromEuler(camEuler);

 if (mapControls) mapControls.enabled = false;
 if (typeof transformControl !== 'undefined' && transformControl) {
 transformControl.detach();
 }

 pieState.active = true;
 setFlashlight(pieState.flashlightOn);

 // Update UI buttons & HUD
 const b1 = document.getElementById('btnPlayHere');
 const b2 = document.getElementById('btnPlayHereTop');
 if (b1) { b1.textContent = t('btn_stop_play'); b1.classList.add('active-play'); }
 if (b2) { b2.textContent = t('btn_stop_play'); b2.classList.add('active-play'); }

 const hud = document.getElementById('stalkerPlayHud');
 if (hud) hud.classList.add('visible');

 // Request PointerLock on the 3D canvas
 const canvas = mapRenderer.domElement;
 if (canvas && canvas.requestPointerLock) {
 try {
 canvas.requestPointerLock();
 } catch (e) {}
 }

 queryNearestAiNode(true);
 updateAnomalyProximity(0);
 updateHudDom();
 }

 function stopPlayHereMode() {
 if (!pieState.active) return;
 pieState.active = false;
 pieState.keys = {};
 pieState.draggingLook = false;

 if (document.pointerLockElement && document.exitPointerLock) {
 try { document.exitPointerLock(); } catch (e) {}
 }

 if (pieState.flashlight) {
 pieState.flashlight.intensity = 0;
 pieState.flashlight.visible = false;
 }

 if (mapControls && mapCamera) {
 mapCamera.getWorldDirection(tempDir);
 mapControls.target.copy(mapCamera.position).addScaledVector(tempDir, 12.0);
 mapControls.enabled = true;
 mapControls.update();
 }

 const b1 = document.getElementById('btnPlayHere');
 const b2 = document.getElementById('btnPlayHereTop');
 if (b1) { b1.textContent = t('btn_play_here'); b1.classList.remove('active-play'); }
 if (b2) { b2.textContent = t('btn_play_here'); b2.classList.remove('active-play'); }

 const hud = document.getElementById('stalkerPlayHud');
 if (hud) hud.classList.remove('visible');
 }

 function togglePlayHereMode() {
 if (pieState.active) stopPlayHereMode();
 else startPlayHereMode();
 }

 window.togglePlayHereMode = togglePlayHereMode;
 window.startPlayHereMode = startPlayHereMode;
 window.stopPlayHereMode = stopPlayHereMode;

 // Query nearest AI node (local fast check + backend C-accelerated /api/nearest_ai_node)
 function queryNearestAiNode(force) {
 if (!pieState.active) return;
 const now = performance.now();
 if (!force && now - pieState.lastAiFetchTime < 280) return;
 if (!force && pieState.lastAiQueryPos.distanceToSquared(pieState.footPos) < 0.20) return;

 pieState.lastAiFetchTime = now;
 pieState.lastAiQueryPos.copy(pieState.footPos);

 const lvl = typeof currentLevel !== 'undefined' ? currentLevel : 'l01_escape';
 const x = pieState.footPos.x.toFixed(2);
 const y = pieState.footPos.y.toFixed(2);
 const z = pieState.footPos.z.toFixed(2);

 fetch(`/api/nearest_ai_node/${encodeURIComponent(lvl)}?x=${x}&y=${y}&z=${z}`)
 .then(r => r.json())
 .then(data => {
 if (data && data.level_vertex_id !== undefined && data.level_vertex_id >= 0) {
 pieState.currentAiNodeId = `${data.level_vertex_id}`;
 pieState.currentAiNodeDist = Number(data.distance || 0);
 }
 })
 .catch(() => {});
 }

 function isAnomalySpawn(sp) {
 if (!sp) return false;
 const s = ((sp.section_name || sp.section || '') + ' ' + (sp.entity_name || sp.name || '')).toLowerCase();
 return (
 s.includes('anomal_zone') ||
 s.includes('zone_mine_') ||
 s.includes('zone_field_') ||
 s.includes('zone_mosquito') ||
 s.includes('zone_witches') ||
 s.includes('zone_buzz') ||
 s.includes('zone_gravi') ||
 s.includes('zone_burning') ||
 s.includes('zone_radioactive') ||
 s.includes('torrid') ||
 s.includes('anom')
 );
 }

 function updateAnomalyProximity(dt) {
 if (typeof currentSpawns === 'undefined' || !Array.isArray(currentSpawns)) return;
 let bestSp = null;
 let bestD2 = Infinity;
 const px = pieState.footPos.x;
 const py = pieState.footPos.y;
 const pz = pieState.footPos.z;

 for (let i = 0; i < currentSpawns.length; i++) {
 const sp = currentSpawns[i];
 if (!isAnomalySpawn(sp) || !Array.isArray(sp.position)) continue;
 const dx = sp.position[0] - px;
 const dy = sp.position[1] - py;
 const dz = sp.position[2] - pz;
 const d2 = dx * dx + dy * dy + dz * dz;
 if (d2 < bestD2) {
 bestD2 = d2;
 bestSp = sp;
 }
 }

 pieState.nearestAnomaly = bestSp;
 pieState.nearestAnomalyDist = Math.sqrt(bestD2);

 // Geiger counter beep logic when within 28m of an anomaly
 if (bestSp && pieState.nearestAnomalyDist < 28.0) {
 const norm = Math.max(0, Math.min(1, (28.0 - pieState.nearestAnomalyDist) / 26.0));
 const intervalMs = Math.max(65, 780 - norm * 710);
 const now = performance.now();
 if (now >= pieState.nextGeigerBeepTime) {
 playGeigerBeep(norm);
 pieState.nextGeigerBeepTime = now + intervalMs;
 }
 }
 }

 // Check if player crosshair is pointing at an NPC / Item / Spawn
 function updateCrosshairInteraction() {
 pieState.focusedSpawnIndex = -1;
 pieState.focusedSpawnDist = Infinity;
 if (!mapCamera || typeof currentSpawns === 'undefined' || !Array.isArray(currentSpawns)) return;

 mapCamera.getWorldDirection(tempDir);
 const camPos = mapCamera.position;

 // 1. Check raycast against spawnGroup and spawnOgfGroup
 const targets = [];
 if (typeof spawnGroup !== 'undefined' && spawnGroup) targets.push(...spawnGroup.children);
 if (typeof spawnOgfGroup !== 'undefined' && spawnOgfGroup) targets.push(...spawnOgfGroup.children);

 centerRaycaster.set(camPos, tempDir);
 centerRaycaster.near = 0.2;
 centerRaycaster.far = 9.0;
 const hits = centerRaycaster.intersectObjects(targets, true);
 if (hits.length > 0) {
 let obj = hits[0].object;
 while (obj && obj.userData?.spawnIndex === undefined) obj = obj.parent;
 if (obj && obj.userData?.spawnIndex !== undefined) {
 pieState.focusedSpawnIndex = obj.userData.spawnIndex;
 pieState.focusedSpawnDist = hits[0].distance;
 return;
 }
 }

 // 2. Cone fallback for spawns within 5.5m
 let bestIdx = -1;
 let bestDist = 5.5;
 for (let i = 0; i < currentSpawns.length; i++) {
 const sp = currentSpawns[i];
 if (!sp || !Array.isArray(sp.position)) continue;
 tempOrigin.set(sp.position[0], sp.position[1] + 0.9, sp.position[2]).sub(camPos);
 const dist = tempOrigin.length();
 if (dist < bestDist && dist > 0.2) {
 const cosAngle = tempOrigin.normalize().dot(tempDir);
 if (cosAngle > 0.94) {
 bestDist = dist;
 bestIdx = i;
 }
 }
 }
 if (bestIdx >= 0) {
 pieState.focusedSpawnIndex = bestIdx;
 pieState.focusedSpawnDist = bestDist;
 }
 }

 function inspectFocusedSpawn() {
 if (pieState.focusedSpawnIndex < 0 || typeof currentSpawns === 'undefined') return false;
 const idx = pieState.focusedSpawnIndex;
 const sp = currentSpawns[idx];
 if (!sp) return false;
 if (typeof selectSpawn === 'function') {
 selectSpawn(idx, false);
 }
 pieState.inspectedSpawnText = `${t('hud_inspected_badge')}: ${sp.entity_name || sp.name} [${sp.section_name || sp.section}]`;
 pieState.inspectedSpawnToastTimer = performance.now() + 3800;
 return true;
 }

 function cardinalFromYaw(yawRad) {
 // Three.js camera looks down -Z at yaw=0
 let deg = ((-yawRad * 180 / Math.PI) % 360 + 360) % 360;
 const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
 const idx = Math.round(deg / 45) % 8;
 return `${dirs[idx]} ${String(Math.round(deg)).padStart(3, '0')}°`;
 }

 function updateHudDom() {
 if (!pieState.active) return;

 const compassEl = document.getElementById('pieCompassReadout');
 if (compassEl) compassEl.textContent = cardinalFromYaw(pieState.yaw);

 const lvlEl = document.getElementById('pieLevelReadout');
 if (lvlEl) lvlEl.textContent = typeof currentLevel !== 'undefined' ? currentLevel : 'l01_escape';

 const sprinting = (pieState.keys['ShiftLeft'] || pieState.keys['ShiftRight']) && !pieState.crouched;
 const stanceEl = document.getElementById('pieStanceReadout');
 if (stanceEl) {
 stanceEl.textContent = pieState.crouched
 ? t('hud_stance_crouch')
 : (sprinting ? t('hud_stance_sprint') : t('hud_stance_stand'));
 stanceEl.style.color = pieState.crouched ? '#79c0ff' : (sprinting ? '#e59a2e' : '#42c87a');
 }

 const flEl = document.getElementById('pieFlashlightReadout');
 if (flEl) {
 flEl.textContent = pieState.flashlightOn ? t('hud_flashlight_on') : t('hud_flashlight_off');
 flEl.style.color = pieState.flashlightOn ? '#f5d76e' : '#8b97a8';
 }

 const coordsEl = document.getElementById('pieCoordsReadout');
 if (coordsEl) {
 coordsEl.textContent = `POS: X ${pieState.footPos.x.toFixed(2)} | Y ${pieState.footPos.y.toFixed(2)} | Z ${pieState.footPos.z.toFixed(2)}`;
 }

 const aiEl = document.getElementById('pieAiNodeReadout');
 if (aiEl) {
 aiEl.textContent = `${t('hud_ai_node')}: #${pieState.currentAiNodeId} (Δ ${pieState.currentAiNodeDist.toFixed(2)}m)`;
 }

 const horizSpeed = Math.hypot(pieState.vel.x, pieState.vel.z);
 const spdEl = document.getElementById('pieSpeedReadout');
 if (spdEl) spdEl.textContent = `${horizSpeed.toFixed(1)} m/s`;

 // Crosshair rangefinder (computed via fast spatial grid along look ray)
 const rangeEl = document.getElementById('pieRangeReadout');
 if (rangeEl && mapCamera) {
 if (pieState.focusedSpawnIndex >= 0 && Number.isFinite(pieState.focusedSpawnDist)) {
 rangeEl.textContent = `${pieState.focusedSpawnDist.toFixed(1)} m`;
 } else {
 mapCamera.getWorldDirection(tempDir);
 if (tempDir.y < -0.05 && pieState.eyeHeight > 0.1) {
 const groundDist = Math.min(250.0, -pieState.eyeHeight / tempDir.y);
 rangeEl.textContent = `${groundDist.toFixed(1)} m`;
 } else {
 rangeEl.textContent = '— m';
 }
 }
 }

 // Interaction prompt [F] Use / Inspect
 const promptEl = document.getElementById('pieInteractPrompt');
 const dotEl = document.getElementById('pieCrosshairDot');
 if (promptEl) {
 if (pieState.focusedSpawnIndex >= 0 && typeof currentSpawns !== 'undefined' && currentSpawns[pieState.focusedSpawnIndex]) {
 const sp = currentSpawns[pieState.focusedSpawnIndex];
 promptEl.style.display = 'block';
 promptEl.textContent = `${t('hud_interact_prefix')} ${sp.entity_name || sp.name} [${sp.section_name || sp.section}] (${pieState.focusedSpawnDist.toFixed(1)}m)`;
 if (dotEl) dotEl.style.background = '#e59a2e';
 } else {
 promptEl.style.display = 'none';
 if (dotEl) dotEl.style.background = '#42c87a';
 }
 }

 // Anomaly Geiger Counter Panel
 const anomPanel = document.getElementById('pieAnomalyPanel');
 const geigerHdr = document.getElementById('pieGeigerHeader');
 const anomNearest = document.getElementById('pieAnomalyNearest');
 const anomBar = document.getElementById('pieAnomalyBar');
 if (anomPanel && geigerHdr && anomNearest && anomBar) {
 const dist = pieState.nearestAnomalyDist;
 const sp = pieState.nearestAnomaly;
 if (sp && dist < 28.0) {
 const pct = Math.min(100, Math.max(8, ((28.0 - dist) / 26.0) * 100));
 const uSv = (0.15 + Math.pow((28.0 - dist) / 6.0, 2.2) * 4.8).toFixed(2);
 anomBar.style.width = `${pct.toFixed(0)}%`;
 if (dist < 10.0) {
 anomPanel.classList.add('anomaly-danger');
 geigerHdr.textContent = `${t('hud_geiger_danger')} (${uSv} µSv/h)`;
 geigerHdr.style.color = '#ff7b72';
 anomBar.style.background = '#e5534b';
 } else {
 anomPanel.classList.remove('anomaly-danger');
 geigerHdr.textContent = `${t('hud_geiger_warn')} (${uSv} µSv/h)`;
 geigerHdr.style.color = '#e59a2e';
 anomBar.style.background = '#e59a2e';
 }
 anomNearest.textContent = `${sp.section_name || sp.section} (${sp.entity_name || sp.name}) — ${dist.toFixed(1)}m`;
 } else {
 anomPanel.classList.remove('anomaly-danger');
 geigerHdr.textContent = t('hud_geiger_safe');
 geigerHdr.style.color = '#42c87a';
 anomBar.style.width = '4%';
 anomBar.style.background = '#42c87a';
 anomNearest.textContent = sp
 ? `Nearest: ${sp.section_name || sp.section} (${dist.toFixed(1)}m)`
 : 'Nearest Zone: —';
 }
 }

 const toastEl = document.getElementById('pieInspectedToast');
 if (toastEl) {
 if (performance.now() < pieState.inspectedSpawnToastTimer && pieState.inspectedSpawnText) {
 toastEl.style.display = 'block';
 toastEl.textContent = pieState.inspectedSpawnText;
 } else {
 toastEl.style.display = 'none';
 }
 }
 }

 // Physics Step: CFORM Raycast Gravity + Stair Step + Wall Collision
 function stepPlayModePhysics(dt) {
 if (!pieState.active || !mapCamera) return;

 const colliders = getCollisionMeshes();

 // Smooth crouch interpolation
 pieState.targetEyeHeight = pieState.crouched ? pieState.crouchEyeHeight : pieState.standingEyeHeight;
 pieState.eyeHeight += (pieState.targetEyeHeight - pieState.eyeHeight) * Math.min(1, dt * 12.0);

 // Compute horizontal wish direction from yaw
 forwardHoriz.set(-Math.sin(pieState.yaw), 0, -Math.cos(pieState.yaw)).normalize();
 rightHoriz.set(Math.cos(pieState.yaw), 0, -Math.sin(pieState.yaw)).normalize();

 const moveFwd = ((pieState.keys['KeyW'] || pieState.keys['ArrowUp']) ? 1 : 0) - ((pieState.keys['KeyS'] || pieState.keys['ArrowDown']) ? 1 : 0);
 const moveStr = ((pieState.keys['KeyD'] || pieState.keys['ArrowRight']) ? 1 : 0) - ((pieState.keys['KeyA'] || pieState.keys['ArrowLeft']) ? 1 : 0);

 wishMove.set(0, 0, 0);
 if (moveFwd !== 0) wishMove.addScaledVector(forwardHoriz, moveFwd);
 if (moveStr !== 0) wishMove.addScaledVector(rightHoriz, moveStr);
 if (wishMove.lengthSq() > 0) wishMove.normalize();

 const sprinting = (pieState.keys['ShiftLeft'] || pieState.keys['ShiftRight']) && !pieState.crouched && moveFwd > 0;
 const speed = pieState.crouched ? pieState.crouchSpeed : (sprinting ? pieState.sprintSpeed : pieState.walkSpeed);

 pieState.vel.x = wishMove.x * speed;
 pieState.vel.z = wishMove.z * speed;

 // Fast O(1) horizontal wall collision + sliding against 2D spatial grid
 const candX = pieState.footPos.x + pieState.vel.x * dt;
 const candZ = pieState.footPos.z + pieState.vel.z * dt;
 const wallRes = resolveHorizontalWallCollision(pieState.footPos.x, pieState.footPos.y, pieState.footPos.z, candX, candZ, pieState.playerRadius);
 pieState.footPos.x = wallRes.x;
 pieState.footPos.z = wallRes.z;

 // Apply gravity (9.81 m/s²)
 pieState.vel.y -= pieState.gravity * dt;
 const nextFootY = pieState.footPos.y + pieState.vel.y * dt;

 // Fast O(1) floor height check strictly below waist/step height (so ceilings/roof rafters above waist are NEVER hit!)
 let foundGround = false;
 let groundY = nextFootY;
 const maxStepY = pieState.footPos.y + pieState.stepHeight;
 const minSearchY = Math.min(nextFootY - 4.0, pieState.footPos.y - 6.0);
 const hitY = queryFloorHeightAt(pieState.footPos.x, pieState.footPos.z, maxStepY, minSearchY);
 if (hitY !== null) {
 const deltaY = hitY - pieState.footPos.y;
 if (deltaY <= pieState.stepHeight && (nextFootY <= hitY + 0.16 || (pieState.grounded && deltaY >= -0.75 && pieState.vel.y <= 0))) {
 groundY = hitY;
 foundGround = true;
 }
 }

 if (foundGround) {
 pieState.footPos.y = groundY;
 pieState.vel.y = 0;
 pieState.grounded = true;
 } else {
 pieState.footPos.y = nextFootY;
 pieState.grounded = false;
 // Safety catch if falling below level bounds
 if (pieState.footPos.y < -300 && colliders.length > 0) {
 const safePt = findInitialSpawnFootPosition();
 pieState.footPos.copy(safePt);
 pieState.vel.set(0, 0, 0);
 pieState.grounded = true;
 }
 }

 // Subtle S.T.A.L.K.E.R. head-bob when moving on ground
 let bobY = 0;
 const horizSpd = Math.hypot(pieState.vel.x, pieState.vel.z);
 if (pieState.grounded && horizSpd > 0.4) {
 pieState.headBobTimer += dt * (sprinting ? 13.5 : 9.0);
 bobY = Math.sin(pieState.headBobTimer) * (sprinting ? 0.055 : 0.028);
 } else {
 pieState.headBobTimer = 0;
 }

 // Sync camera position & orientation
 mapCamera.position.set(
 pieState.footPos.x,
 pieState.footPos.y + pieState.eyeHeight + bobY,
 pieState.footPos.z
 );
 camEuler.set(pieState.pitch, pieState.yaw, 0, 'YXZ');
 mapCamera.quaternion.setFromEuler(camEuler);

 updateFlashlightTransform();
 updateCrosshairInteraction();
 updateAnomalyProximity(dt);
 queryNearestAiNode(false);
 updateHudDom();
 }

 // Mode B: Trigger POST /api/play_in_engine (Supports MO2 USVFS & Direct Vanilla launch)
 async function triggerPlayInEngine(launchNow = false, explicitMode = null) {
 if (!mapCamera) return;
 const lvl = typeof currentLevel !== 'undefined' ? currentLevel : 'l01_escape';
 const addonSel = document.getElementById('addonSelector');
 const addon = addonSel ? addonSel.value : 'anomaly153';

 // Convert Three.js camera/foot coordinates (Z inverted) back to X-Ray world coordinates (X, Y, -Z)
 const rawPos = pieState.active ? pieState.footPos : mapCamera.position;
 const pos = [
 Number(rawPos.x.toFixed(3)),
 Number(rawPos.y.toFixed(3)),
 Number((-rawPos.z).toFixed(3))
 ];

 mapCamera.getWorldDirection(tempDir);
 const dir = [Number(tempDir.x.toFixed(3)), Number(tempDir.y.toFixed(3)), Number((-tempDir.z).toFixed(3))];

 const modeEl = document.getElementById('pieLaunchModeSelect');
 const profEl = document.getElementById('pieMo2ProfileSelect');
 const pathEl = document.getElementById('pieMo2PathInput');
 const launchMode = explicitMode || (modeEl ? modeEl.value : (localStorage.getItem('studio_pie_launch_mode') || 'mo2'));
 const mo2Profile = profEl ? profEl.value : (localStorage.getItem('studio_pie_mo2_profile') || 'Default');
 const mo2Path = pathEl ? pathEl.value : (localStorage.getItem('studio_pie_mo2_path') || '');

 try {
 const res = await fetch('/api/play_in_engine', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 level: lvl,
 position: pos,
 direction: dir,
 addon: addon,
 launch_mode: launchMode,
 mo2_profile: mo2Profile,
 mo2_path: mo2Path,
 launch: !!launchNow
 })
 });
 const data = await res.json();

 const modal = document.getElementById('pieEngineModal');
 if (modal) {
 if (modeEl && data.launch_mode) modeEl.value = data.launch_mode;
 if (pathEl && data.mo2_dir && !pathEl.value) pathEl.value = data.mo2_dir;
 if (profEl && Array.isArray(data.mo2_profiles) && data.mo2_profiles.length) {
 const curP = data.mo2_profile || 'Default';
 profEl.innerHTML = data.mo2_profiles.map(p => `<option value="${p}" ${p === curP ? 'selected' : ''}>${p}</option>`).join('');
 }
 const badgeEl = document.getElementById('pieMo2StatusBadge');
 if (badgeEl) {
 badgeEl.textContent = data.mo2_available ? 'MO2 detected ' : 'Check path';
 badgeEl.style.color = data.mo2_available ? '#42c87a' : '#e59a2e';
 }
 document.getElementById('pieModalCmdBox').textContent = data.command || '';
 document.getElementById('pieModalLtxBox').textContent = data.script_content || '';
 const metaEl = document.getElementById('pieModalMeta');
 if (metaEl) {
 const modeLabel = data.launch_mode === 'mo2'
 ? `Mod Organizer 2 (Profile: ${data.mo2_profile || 'Default'}, +ZZZ_Anomaly_Studio_Live_PIE)`
 : `Direct Launch (Vanilla gamedata/)`;
 metaEl.textContent = data.launched
 ? `Launched via ${modeLabel} (PID ${data.pid}) — Level: ${data.level} | Pos: [${pos.join(', ')}] | AI-Node: #${data.level_vertex_id ?? '—'}`
 : ` Teleport hook synchronized for ${modeLabel} — Level: ${data.level} | Pos: [${pos.join(', ')}] | AI-Node: #${data.level_vertex_id ?? '—'}`;
 }
 modal.classList.add('open');
 }
 return data;
 } catch (err) {
 console.error('Error calling /api/play_in_engine:', err);
 return null;
 }
 }

 window.triggerPlayInEngine = triggerPlayInEngine;

 // Event Listeners (Capture phase to cleanly intercept keys while in Play Mode)
 window.addEventListener('keydown', (e) => {
 if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;

 if (e.code === 'F5') {
 e.preventDefault();
 e.stopPropagation();
 togglePlayHereMode();
 return;
 }

 if (!pieState.active) return;

 if (e.code === 'Escape') {
 e.preventDefault();
 e.stopPropagation();
 stopPlayHereMode();
 return;
 }

 pieState.keys[e.code] = true;

 if (e.code === 'Space') {
 e.preventDefault();
 e.stopPropagation();
 if (pieState.grounded) {
 pieState.vel.y = pieState.jumpSpeed;
 pieState.grounded = false;
 }
 return;
 }

 if (e.code === 'KeyC' || e.code === 'ControlLeft') {
 e.preventDefault();
 e.stopPropagation();
 pieState.crouched = !pieState.crouched;
 updateHudDom();
 return;
 }

 if (e.code === 'KeyF') {
 e.preventDefault();
 e.stopPropagation();
 // If looking directly at an entity within range, inspect it AND toggle flashlight if none or hold
 const inspected = inspectFocusedSpawn();
 if (!inspected) {
 setFlashlight(!pieState.flashlightOn);
 } else {
 updateHudDom();
 }
 return;
 }

 if (e.code === 'KeyL') {
 e.preventDefault();
 e.stopPropagation();
 setFlashlight(!pieState.flashlightOn);
 return;
 }

 // Prevent editor hotkeys (1, 2, 3, G, Delete, WASD fly) from firing while in Play Mode
 if (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyQ', 'KeyE', 'KeyG', 'Digit1', 'Digit2', 'Digit3', 'Delete', 'Backspace'].includes(e.code)) {
 e.preventDefault();
 e.stopPropagation();
 }
 }, true);

 window.addEventListener('keyup', (e) => {
 pieState.keys[e.code] = false;
 if (pieState.active && ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyQ', 'KeyE', 'ShiftLeft', 'ShiftRight'].includes(e.code)) {
 e.stopPropagation();
 }
 }, true);

 window.addEventListener('mousemove', (e) => {
 if (!pieState.active) return;
 const canvas = mapRenderer?.domElement;
 const isLocked = document.pointerLockElement === canvas;
 if (!isLocked && !pieState.draggingLook) return;

 const sens = 0.0022;
 pieState.yaw -= (e.movementX || 0) * sens;
 pieState.pitch = Math.max(
 -Math.PI * 0.47,
 Math.min(Math.PI * 0.47, pieState.pitch - (e.movementY || 0) * sens)
 );
 });

 window.addEventListener('mousedown', (e) => {
 if (!pieState.active) return;
 const canvas = mapRenderer?.domElement;
 if (e.target === canvas) {
 if (document.pointerLockElement !== canvas && canvas.requestPointerLock) {
 try { canvas.requestPointerLock(); } catch (err) {}
 }
 if (e.button === 0) {
 pieState.draggingLook = true;
 if (pieState.focusedSpawnIndex >= 0) {
 inspectFocusedSpawn();
 }
 }
 }
 });

 window.addEventListener('mouseup', () => {
 pieState.draggingLook = false;
 });

 // Main animation loop for Play Mode physics
 function pieLoop(now) {
 if (document.hidden) {
 setTimeout(() => requestAnimationFrame(pieLoop), 500);
 return;
 }
 if (!pieState.active) {
 setTimeout(() => requestAnimationFrame(pieLoop), 200);
 return;
 }
 requestAnimationFrame(pieLoop);
 const dt = Math.min(0.05, Math.max(0.001, (now - pieState.lastFrameTime) / 1000));
 pieState.lastFrameTime = now;
 stepPlayModePhysics(dt);
 }

 function initPieExtension() {
 injectPlayModeUI();
 syncCformLayerMeshesAlias();
 requestAnimationFrame(pieLoop);
 try {
 const qs = new URLSearchParams(window.location.search);
 if (qs.get('modal') === 'pie') {
 setTimeout(() => triggerPlayInEngine(false), 3500);
 }
 if (qs.get('cam') === 'rookie') {
 setTimeout(() => {
 if (typeof mapCamera !== 'undefined' && typeof mapControls !== 'undefined') {
 mapCamera.position.set(-178, -5.0, -108);
 mapControls.target.set(-196, -19.5, -132);
 mapControls.update();
 }
 if (qs.get('tex') === 'detail' && typeof setTerrainTextureMode === 'function') {
 setTerrainTextureMode('detail');
 }
 if (qs.get('play') === '1' && typeof togglePlayHereMode === 'function') {
 setTimeout(() => togglePlayHereMode(), 1200);
 }
 }, 5500);
 }
 if (qs.get('ogf_demo') === '1') {
 setTimeout(() => {
 if (typeof switchTab === 'function') switchTab('ogf');
 if (typeof loadOgfModel === 'function') {
 loadOgfModel('actors/stalker_neutral/stalker_neutral_2.ogf');
 }
 }, 2500);
 }
 } catch (e) {}

 }

 if (document.readyState === 'loading') {
 document.addEventListener('DOMContentLoaded', initPieExtension);
 } else {
 initPieExtension();
 }
})();
