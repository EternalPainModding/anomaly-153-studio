import time as _boot_time
SERVER_BOOT_ID = str(int(_boot_time.time() * 1000))
#!/usr/bin/env python3
"""
Anomaly 1.5.3 Studio — Fast Local Backend API & Web Server
Serves:
- Static Web Editor UI (Three.js 3D Map Viewport, 3D OGF Model Viewer, AI Graph Inspector, LTX/Spawn Editor, Addon Manager, Builder)
- REST API for all 34 unpacked S.T.A.L.K.E.R. Anomaly 1.5.3 levels, 4,093 spawns with resolved .ogf visuals, patrol paths, 1,148 LTX configs, 12,186 OGF 3D models, and real .dds textures
"""
import ctypes
import io
import json
import os
import struct
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

try:
    from PIL import Image
except ImportError:
    Image = None

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import quest_logic_service
try:
    import landscape_service
except Exception:
    landscape_service = None
try:
    import sdk07_parity_service
except Exception:
    sdk07_parity_service = None
import settings_service
import db0_vfs
import v010_core_service
import project_service
try:
    import level_details_grass_service
except Exception:
    level_details_grass_service = None
try:
    import xrai_navmesh_service
except Exception:
    xrai_navmesh_service = None
try:
    import static_prop_placer_service
except Exception:
    static_prop_placer_service = None
try:
    import hom_snd_env_service
except Exception:
    hom_snd_env_service = None
try:
    import smart_terrain_waypoint_service
except Exception:
    smart_terrain_waypoint_service = None
try:
    import ogf_actor_editor_service
except Exception:
    ogf_actor_editor_service = None
try:
    import dds_thm_pipeline_service
except Exception:
    dds_thm_pipeline_service = None
try:
    import all_spawn_compiler_service
except Exception:
    all_spawn_compiler_service = None
try:
    import xr_binary_compiler_service
except Exception:
    xr_binary_compiler_service = None

try:
    import xray_typechecker_service
except Exception:
    xray_typechecker_service = None
try:
    import quest_item_cloner_service
except Exception:
    quest_item_cloner_service = None
try:
    import level_5layer_patcher_service
except Exception:
    level_5layer_patcher_service = None
try:
    import alao_lua_optimizer_service
except Exception:
    alao_lua_optimizer_service = None
try:
    import navmesh_cform_sync_service
except Exception:
    navmesh_cform_sync_service = None
try:
    import dialog_dxml_linker_service
except Exception:
    dialog_dxml_linker_service = None
try:
    import story_campaign_presets_service
except Exception:
    story_campaign_presets_service = None
try:
    import spawn_catalog_service
except Exception:
    spawn_catalog_service = None

ROOT = Path(os.environ["ANOMALY_STUDIO_ROOT"]).resolve() if os.environ.get("ANOMALY_STUDIO_ROOT") else (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent)
INDEX_DIR = ROOT / "index"
UNPACKED_DIR = ROOT / ".studio_cache" / "vfs_mount"
ADDONS_DIR = ROOT / "addons"
STUDIO_DIR = ROOT
FRONTEND_DIR = STUDIO_DIR / "frontend"
TEXTURE_CACHE_DIR = STUDIO_DIR / "_tex_cache"
TEXTURE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

FAST_CFORM_LIB = None
_CFORM_NAME = "fast_cform.dll" if os.name == "nt" else "libfast_cform.so"
FAST_CFORM_SO = (ROOT / "backend" / _CFORM_NAME) if (ROOT / "backend" / _CFORM_NAME).is_file() else (Path(__file__).resolve().parent / _CFORM_NAME)
if FAST_CFORM_SO.is_file():
    try:
        FAST_CFORM_LIB = ctypes.CDLL(str(FAST_CFORM_SO))
        FAST_CFORM_LIB.build_cform_multilayer.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint16),
            ctypes.POINTER(ctypes.c_uint16),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        FAST_CFORM_LIB.build_cform_multilayer.restype = ctypes.c_uint32
        FAST_CFORM_LIB.find_nearest_ai_node.argtypes = [
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        ]
        FAST_CFORM_LIB.find_nearest_ai_node.restype = ctypes.c_uint32

        class _GeomDrawSpec(ctypes.Structure):
            _fields_ = [
                ("vb_id", ctypes.c_uint32),
                ("vb_off", ctypes.c_uint32),
                ("vb_cnt", ctypes.c_uint32),
                ("ib_id", ctypes.c_uint32),
                ("ib_off", ctypes.c_uint32),
                ("ib_cnt", ctypes.c_uint32),
                ("tile_idx", ctypes.c_uint32),
                ("has_xform", ctypes.c_uint32),
                ("xform", ctypes.c_float * 16),
            ]

        FAST_CFORM_LIB.extract_level_geom_draws.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p,
            ctypes.POINTER(_GeomDrawSpec),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        FAST_CFORM_LIB.extract_level_geom_draws.restype = ctypes.c_uint32
    except Exception as e:
        print("Warning: Could not load libfast_cform.so:", e)
        FAST_CFORM_LIB = None

# Load pre-built master index (S.T.A.L.K.E.R. Anomaly 1.5.3)
LEVELS_BY_ADDON = {
    "anomaly153": json.loads((INDEX_DIR / "levels_index_anomaly153.json").read_text()) if (INDEX_DIR / "levels_index_anomaly153.json").is_file() else json.loads((INDEX_DIR / "levels_index.json").read_text()),
}
LEVELS_SUMMARY = LEVELS_BY_ADDON["anomaly153"]
SPAWNS_PARSED_DIR = STUDIO_DIR / ".studio_cache" / "spawns_parsed"
SPAWNS_SUMMARY = json.loads((SPAWNS_PARSED_DIR / "_summary.json").read_text()) if (SPAWNS_PARSED_DIR / "_summary.json").is_file() else {}


def resolve_level_dir(level_name: str, addon_id: str = None) -> Path:
    """Resolve a level directory from S.T.A.L.K.E.R. Anomaly 1.5.3 (on-demand mounted from packed .db0)."""
    if ":" in level_name:
        _, level_name = level_name.split(":", 1)
    try:
        db0_vfs.ensure_vfs_level(level_name)
    except Exception:
        pass
    return UNPACKED_DIR / "levels" / level_name

# Build fast OGF & LTX file lists directly from packed .db0 VFS TOC index
_BOOT_VFS = db0_vfs.get_global_vfs()
OGF_FILES = sorted(
    k[len("meshes/"):]
    for k in _BOOT_VFS.entries.keys()
    if k.startswith("meshes/") and k.endswith(".ogf")
)
LTX_FILES = sorted(
    k[len("configs/"):]
    for k in _BOOT_VFS.entries.keys()
    if k.startswith("configs/") and k.endswith(".ltx")
)

MEM_TEX_CACHE = {}


def get_addons_status():
    """Return S.T.A.L.K.E.R. Anomaly 1.5.3 installation status."""
    return [
        {
            "id": "anomaly153",
            "name": "S.T.A.L.K.E.R. Anomaly 1.5.3",
            "type": "base",
            "path": str(UNPACKED_DIR),
            "ready": UNPACKED_DIR.is_dir(),
            "levels_count": len(LEVELS_SUMMARY),
            "ogf_count": len(OGF_FILES),
            "ltx_count": len(LTX_FILES),
        }
    ]


def resolve_dds_path(tex_rel: str, level_name: str = None) -> Path | None:
    """Locate a .dds texture in unpacked textures, level terrain/textures, or modular addons."""
    clean = tex_rel.replace("\\", "/").strip("/")
    if clean.lower().endswith(".dds"):
        clean = clean[:-4]
    try:
        db0_vfs.ensure_vfs_file(f"textures/{clean}.dds")
        if level_name:
            db0_vfs.ensure_vfs_file(f"levels/{level_name}/{clean}.dds")
            db0_vfs.ensure_vfs_file(f"levels/{level_name}/terrain/{Path(clean).name}.dds")
    except Exception:
        pass
    candidates = [
        UNPACKED_DIR / "textures" / f"{clean}.dds",
    ]
    if level_name:
        candidates.insert(0, UNPACKED_DIR / "levels" / level_name / f"{clean}.dds")
        candidates.insert(1, UNPACKED_DIR / "levels" / level_name / "terrain" / f"{Path(clean).name}.dds")
    if ADDONS_DIR.is_dir():
        for addon_dir in ADDONS_DIR.iterdir():
            if addon_dir.is_dir():
                candidates.append(addon_dir / "textures" / f"{clean}.dds")
    for c in candidates:
        if c.is_file():
            return c
    # Fast O(1) fallback search in .db0 VFS TOC index by suffix
    fname_lower = f"/{Path(clean).name.lower()}.dds"
    try:
        vfs = db0_vfs.get_global_vfs()
        for k in vfs.entries.keys():
            if k.startswith("textures/") and k.endswith(fname_lower):
                return db0_vfs.ensure_vfs_file(k, vfs)
    except Exception:
        pass
    return None


def load_texture_bytes(tex_rel: str, level_name: str = None) -> tuple[bytes, str] | None:
    """Convert .dds texture to cached PNG/JPEG for fast WebGL loading."""
    cache_key = f"{level_name or ''}:{tex_rel}"
    if cache_key in MEM_TEX_CACHE:
        return MEM_TEX_CACHE[cache_key]

    dds_path = resolve_dds_path(tex_rel, level_name)
    if not dds_path or Image is None:
        return None

    is_detail_tex = ("detail_" in tex_rel.lower()) or ("ground_" in tex_rel.lower()) or ("build_details" in tex_rel.lower())
    safe_name = tex_rel.replace("\\", "_").replace("/", "_").replace(".", "_")
    if is_detail_tex:
        safe_name = f"{level_name or 'base'}_{safe_name}_norm_v4"
    disk_cache = TEXTURE_CACHE_DIR / f"{safe_name}_v6.png"
    if disk_cache.is_file():
        data = disk_cache.read_bytes()
        res = (data, "image/png")
        if len(MEM_TEX_CACHE) < 256:
            MEM_TEX_CACHE[cache_key] = res
        return res

    try:
        im = Image.open(dds_path)
        # Split bands BEFORE resizing so Pillow never premultiplies RGB by DDS Alpha=0!
        bands = im.split()
        if max(im.size) > 1024:
            bands = [b.resize((1024, 1024), Image.Resampling.BILINEAR) for b in bands]
        if ("detail_" in tex_rel.lower()) or ("ground_" in tex_rel.lower()):
            # Preserve real RGB color of ground_grass_02 / detail_grnd_grass / detail_beton_det4
            # and expand contrast (0.5 -> ~0.92 center with strong 0.35..1.0 micro-blade detail)
            # so toggling Detail-Textures ON produces crisp, unmistakable grass blades & concrete grain!
            if len(bands) >= 3:
                r_b, g_b, b_b = bands[0], bands[1], bands[2]
            else:
                r_b = g_b = b_b = bands[0]
            lut_r = [max(55, min(255, int(175 + (v - 118) * 2.25))) for v in range(256)]
            lut_g = [max(65, min(255, int(192 + (v - 112) * 2.35))) for v in range(256)]
            lut_b = [max(45, min(255, int(155 + (v - 95) * 2.15))) for v in range(256)]
            im = Image.merge("RGB", (r_b.point(lut_r), g_b.point(lut_g), b_b.point(lut_b)))
        elif "build_details" in tex_rel.lower():
            # Keep crisp alpha cutout & bright foliage luminance for 3D instanced grass
            if len(bands) >= 4:
                r_b, g_b, b_b, a_b = bands[0], bands[1], bands[2], bands[3]
            else:
                r_b = g_b = b_b = bands[0]
                a_b = Image.new("L", r_b.size, 255)
            lut_rgb = [min(255, int(110 + v * 2.8)) for v in range(256)]
            im = Image.merge("RGBA", (r_b.point(lut_rgb), g_b.point(lut_rgb), b_b.point(lut_rgb), a_b))
        elif any(k in tex_rel.lower() for k in ("trees", "bush", "glas", "barbwire", "setka", "vetk", "list", "kamish", "weed")):
            if len(bands) >= 4:
                im = Image.merge("RGBA", bands[:4])
            elif len(bands) == 3:
                im = Image.merge("RGB", bands[:3])
        else:
            # In X-Ray R2, all structural/prop DDS textures store specular/gloss in Alpha (often 0), NOT transparency!
            # Drop alpha and apply a clean daylight curve so every brick, wood, roof, concrete, vehicle, and prop texture renders opaque and vibrant in WebGL
            lut_bldg = [min(255, int(24 + v * 1.58)) for v in range(256)]
            if len(bands) >= 3:
                im = Image.merge("RGB", (bands[0].point(lut_bldg), bands[1].point(lut_bldg), bands[2].point(lut_bldg)))
            else:
                im = bands[0].point(lut_bldg).convert("RGB")
        buf = io.BytesIO()
        im.save(buf, format="PNG", compress_level=3)
        data = buf.getvalue()
        try:
            disk_cache.write_bytes(data)
        except Exception:
            pass
        res = (data, "image/png")
        if len(MEM_TEX_CACHE) < 256:
            MEM_TEX_CACHE[cache_key] = res
        return res
    except Exception:
        return None


def parse_Vertex_buffer(ss: bytes, vfmt: int, vcnt: int):
    """Extract positions, normals, and UVs from an X-Ray OGF_VERTICES chunk."""
    stride = (len(ss) - 8) // max(1, vcnt)
    positions = []
    normals = []
    uvs = []

    # Determine offsets inside each vertex according to X-Ray bone.h / FVF structs:
    # - 0x112 (FVF_OGF, stride 32): P(0..12), N(12..24), UV(24..32)
    # - 0x212 (stride 36): P(0..12), N(12..24), T/B/UV -> UV at 28..36
    # - 1W (vfmt in (1, 0x12071980)):
    #     stride 60: P(0..12), N(12..24), T(24..36), B(36..48), UV(48..56), matrix(56..60)
    #     stride 36: P(0..12), N(12..24), UV(24..32), matrix(32..36)
    # - 2W (vfmt in (2, 0x240e3300)):
    #     stride 64: m0,m1(0..4), P(4..16), N(16..28), T(28..40), B(40..52), w(52..56), UV(56..64)
    #     stride 44: m0,m1(0..4), P(4..16), N(16..28), w(28..32), UV(32..40)
    # - 3W (vfmt in (3, 0x36154c80), stride 70):
    #     m[3](0..6), P(6..18), N(18..30), T(30..42), B(42..54), w[2](54..62), UV(62..70)
    # - 4W (vfmt in (4, 0x481c6600), stride 76):
    #     m[4](0..8), P(8..20), N(20..32), T(32..44), B(44..56), w[3](56..68), UV(68..76)
    if vfmt in (2, 0x240E3300) and stride >= 40:
        p_off, n_off, uv_off = 4, 16, (56 if stride == 64 else stride - 8)
    elif vfmt in (3, 0x36154C80) and stride == 70:
        p_off, n_off, uv_off = 6, 18, 62
    elif vfmt in (4, 0x481C6600) and stride == 76:
        p_off, n_off, uv_off = 8, 20, 68
    elif vfmt in (1, 0x12071980) or stride == 60:
        p_off, n_off, uv_off = 0, 12, (48 if stride == 60 else stride - 12)
    elif stride == 32:
        p_off, n_off, uv_off = 0, 12, 24
    else:
        p_off, n_off, uv_off = 0, 12, max(24, stride - 8)

    for v in range(vcnt):
        vo = 8 + v * stride
        if vo + p_off + 12 <= len(ss):
            px, py, pz = struct.unpack_from("<fff", ss, vo + p_off)
            if abs(px) > 10000 or abs(py) > 10000 or abs(pz) > 10000 or px != px:
                px = py = pz = 0.0
            positions.extend([round(px, 4), round(py, 4), round(pz, 4)])
        else:
            positions.extend([0.0, 0.0, 0.0])

        if vo + n_off + 12 <= len(ss):
            nx, ny, nz = struct.unpack_from("<fff", ss, vo + n_off)
            if nx != nx or abs(nx) > 10:
                nx, ny, nz = 0.0, 1.0, 0.0
            normals.extend([round(nx, 3), round(ny, 3), round(nz, 3)])
        else:
            normals.extend([0.0, 1.0, 0.0])

        if vo + uv_off + 8 <= len(ss):
            u, v_coord = struct.unpack_from("<ff", ss, vo + uv_off)
            if u != u or v_coord != v_coord or abs(u) > 100 or abs(v_coord) > 100:
                u = v_coord = 0.0
            uvs.extend([round(u, 4), round(v_coord, 4)])
        else:
            uvs.extend([0.0, 0.0])

    return positions, normals, uvs


def parse_single_mesh_chunks(csub: bytes, idx: int = 0) -> dict | None:
    """Parse one OGF mesh / child chunk into {name, texture, shader, positions, normals, uvs, indices}."""
    so = 0
    tex = ""
    shader = ""
    positions, normals, uvs, indices = [], [], [], []
    while so + 8 <= len(csub):
        scid, scsz = struct.unpack_from("<II", csub, so)
        scid &= 0x7FFFFFFF
        ss = csub[so + 8 : so + 8 + scsz]
        so += 8 + scsz
        if scid == 2:
            parts = ss.split(b"\x00")
            tex = parts[0].decode("cp1251", "ignore") if parts else ""
            shader = parts[1].decode("cp1251", "ignore") if len(parts) > 1 else ""
        elif scid == 3 and len(ss) >= 8:
            vfmt, vcnt = struct.unpack_from("<II", ss, 0)
            positions, normals, uvs = parse_Vertex_buffer(ss, vfmt, vcnt)
        elif scid == 4 and len(ss) >= 4:
            icnt = struct.unpack_from("<I", ss, 0)[0]
            if 4 + icnt * 2 <= len(ss):
                indices = list(struct.unpack_from(f"<{icnt}H", ss, 4))
    if not positions or not indices:
        return None
    return {
        "id": idx,
        "texture": tex.replace("\\", "/"),
        "shader": shader,
        "vertex_count": len(positions) // 3,
        "face_count": len(indices) // 3,
        "positions": positions,
        "normals": normals,
        "uvs": uvs,
        "indices": indices,
    }


def load_ogf_mesh(rel_path: str, level_name: str = None) -> dict:
    """Parse an X-Ray v4 .ogf 3D model into per-submesh positions, normals, UVs, indices, textures & bones."""
    clean = rel_path.replace("\\", "/").strip("/")
    if not clean.lower().endswith(".ogf"):
        clean += ".ogf"
    try:
        db0_vfs.ensure_vfs_file(f"meshes/{clean}")
    except Exception:
        pass

    candidates = [
        ROOT / "meshes" / clean,
        STUDIO_DIR / "exports" / "custom_meshes" / clean,
        UNPACKED_DIR / "meshes" / clean,

    ]
    if level_name:
        lvl_dir = resolve_level_dir(level_name)
        candidates.insert(0, lvl_dir / clean)
        candidates.insert(1, lvl_dir / "meshes" / Path(clean).name)

    path = None
    for c in candidates:
        if c.is_file():
            path = c
            break
    if not path:
        return {"error": f"OGF not found: {rel_path}"}

    data = path.read_bytes()
    off = 0
    children = []
    bones = []
    top_chunks_data = {}

    while off + 8 <= len(data):
        cid, csz = struct.unpack_from("<II", data, off)
        cid &= 0x7FFFFFFF
        sub = data[off + 8 : off + 8 + csz]
        off += 8 + csz
        top_chunks_data[cid] = sub

        if cid == 9:  # OGF_CHILDREN
            coff = 0
            cidx = 0
            while coff + 8 <= len(sub):
                ccid, ccsz = struct.unpack_from("<II", sub, coff)
                csub = sub[coff + 8 : coff + 8 + ccsz]
                coff += 8 + ccsz
                child = parse_single_mesh_chunks(csub, cidx)
                if child:
                    children.append(child)
                    cidx += 1
        elif cid == 13:  # OGF_S_BONE_NAMES
            if len(sub) >= 4:
                bcnt = struct.unpack_from("<I", sub, 0)[0]
                boff = 4
                for _ in range(min(bcnt, 128)):
                    end = sub.find(b"\x00", boff)
                    if end == -1:
                        break
                    bname = sub[boff:end].decode("cp1251", "ignore")
                    boff = end + 1
                    end2 = sub.find(b"\x00", boff)
                    if end2 == -1:
                        break
                    bparent = sub[boff:end2].decode("cp1251", "ignore")
                    boff = end2 + 1 + 60  # skip Fobb (60 bytes)
                    bones.append({"name": bname, "parent": bparent})

    # If simple single-mesh OGF (top-level chunks 2, 3, 4)
    if not children and 3 in top_chunks_data and 4 in top_chunks_data:
        single = parse_single_mesh_chunks(data, 0)
        if single:
            children.append(single)

    # Also build legacy merged arrays for backward compatibility while keeping `children` with full UVs & textures
    all_positions = []
    all_normals = []
    all_uvs = []
    all_indices = []
    textures = []
    for ch in children:
        if ch["texture"]:
            textures.append({"texture": ch["texture"], "shader": ch["shader"]})
        v_offset = len(all_positions) // 3
        all_positions.extend(ch["positions"])
        all_normals.extend(ch["normals"])
        all_uvs.extend(ch["uvs"])
        all_indices.extend([i + v_offset for i in ch["indices"]])

    return {
        "path": rel_path,
        "vertex_count": len(all_positions) // 3,
        "face_count": len(all_indices) // 3,
        "textures": textures[:30],
        "bones": bones,
        "children": children,
        "positions": all_positions,
        "normals": all_normals,
        "uvs": all_uvs,
        "indices": all_indices,
    }


MEM_TERRAIN_RGBA_CACHE = {}


def load_level_terrain_dds(level_name: str):
    """Minimal fallback lookup for CFORM vertex colors (terrain UV splat is served via build_level_terrain_splat_png)."""
    return None


def open_dds_fast(dds_path: Path) -> Image.Image:
    """Fast C-buffer reader for uncompressed 32-bit BGRA/RGBA DDS textures (4096x4096 67.1MB loads in 12ms instead of 35s in Pillow's Python loop)."""
    with open(dds_path, "rb") as f:
        hdr = f.read(128)
        if len(hdr) == 128 and hdr[:4] == b"DDS ":
            _, _, _, h, w, _, _, _ = struct.unpack_from("<4s7I", hdr, 0)
            _, pf_flags, fourcc, bit_cnt, r_mask, g_mask, b_mask, a_mask = struct.unpack_from("<2I4s5I", hdr, 76)
            if fourcc == b"\x00\x00\x00\x00" and bit_cnt == 32 and w > 0 and h > 0:
                raw_px = f.read(w * h * 4)
                if len(raw_px) == w * h * 4:
                    raw_mode = "BGRA" if b_mask == 0xFF else "RGBA"
                    return Image.frombuffer("RGBA", (w, h), raw_px, "raw", raw_mode, 0, 1)
            elif fourcc == b"\x00\x00\x00\x00" and bit_cnt == 24 and w > 0 and h > 0:
                raw_px = f.read(w * h * 3)
                if len(raw_px) == w * h * 3:
                    raw_mode = "BGR" if b_mask == 0xFF else "RGB"
                    return Image.frombuffer("RGB", (w, h), raw_px, "raw", raw_mode, 0, 1)
    return Image.open(dds_path)

def build_level_terrain_splat_png(level_name: str) -> tuple[bytes, str] | None:
    """
    Authentic X-Ray Engine Terrain Base + Mask Baker (`shaders/r3/deffer_impl_flat.ps`):
      Splits `textures/terrain/terrain_*_mask.dds` BEFORE resizing (preventing Pillow RGBA alpha=0 premultiplication),
      inpaints only exact DXT5 alpha=0 zero holes (p <= 2) in `levels/<level>/terrain/terrain_*.dds` while preserving
      all authentic dark building footprints, ditches, road wear, and topographic shading at 2048x2048 resolution.
    """
    cache_dir = Path("/tmp/anomaly_studio_dds_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"terrain_splat_{level_name}.png"
    if cache_file.is_file() and cache_file.stat().st_size > 1024:
        return (cache_file.read_bytes(), "image/png")

    terrain_dir = resolve_level_dir(level_name) / "terrain"
    dds_candidates = [
        f for f in sorted(terrain_dir.glob("terrain_*.dds"))
        if not f.name.endswith("_lm.dds") and "mask" not in f.name and "ghost" not in f.name
    ] if terrain_dir.is_dir() else []

    if not dds_candidates:
        # [ISSUE-03] Clean concrete/bunker fallback texture for the 10 underground/indoor levels (e.g. l04u_labx18, labx8)
        from PIL import Image
        import io
        ug_cache = cache_dir / "terrain_splat__underground_fallback.png"
        if ug_cache.is_file() and ug_cache.stat().st_size > 512:
            data = ug_cache.read_bytes()
            cache_file.write_bytes(data)
            return (data, "image/png")
        im_ug = Image.new("RGB", (512, 512), (82, 84, 80))
        buf = io.BytesIO()
        im_ug.save(buf, format="PNG", optimize=False)
        data = buf.getvalue()
        ug_cache.write_bytes(data)
        cache_file.write_bytes(data)
        return (data, "image/png")

    dds_file = dds_candidates[0]
    try:
        from PIL import Image, ImageChops, ImageEnhance, ImageFilter
        import io
        im_base = open_dds_fast(dds_file)
        # [ISSUE-02] Downsample immediately if 4096x4096 (67.1 MB zaton/pripyat) BEFORE splitting/filtering
        if im_base.size != (2048, 2048):
            im_base = im_base.resize((2048, 2048), Image.Resampling.BILINEAR)
        b_bands = im_base.split()
        raw_r = b_bands[0]
        # Inpaint ONLY exact DXT5 alpha=0 zero holes (p <= 3) using local neighborhood blur,
        # preserving authentic dark footprints under farmhouses/trees (p ~ 18..42) and bright paths (p ~ 55..85)!
        bg_fill = raw_r.point(lambda p: 52 if p <= 3 else p).filter(ImageFilter.GaussianBlur(5.0))
        valid_mask = raw_r.point(lambda p: 255 if p > 3 else 0).filter(ImageFilter.GaussianBlur(1.2))
        clean_r = Image.composite(raw_r, bg_fill, valid_mask).filter(ImageFilter.GaussianBlur(0.8))
        # Map X-Ray base intensity (mean ~52, dark footprints ~22, bright paths ~75) to [95..235]
        macro_l = clean_r.point(lambda p: max(92, min(238, int(172 + (p - 52) * 2.15))))
        # Dark footprints (where clean_r < 44, e.g. under buildings, trees, and yards) also get an earthy soil tint weight:
        footprint_w = clean_r.point(lambda p: max(0, min(255, int((46 - p) * 9.5))))

        stem = dds_file.stem
        try:
            from db0_vfs import ensure_vfs_file
            ensure_vfs_file(f"textures/terrain/{stem}_mask.dds")
        except Exception:
            pass
        mask_cands = [
            UNPACKED_DIR / "textures" / "terrain" / f"{stem}_mask.dds",
            terrain_dir / f"{stem}_mask.dds",
        ]
        mask_file = next((c for c in mask_cands if c.is_file()), None)

        def _make_tiled_detail(tex_rel: str, target_rgb=(110, 128, 88), tile_px=128) -> Image.Image:
            p = resolve_dds_path(tex_rel, level_name)
            if p and p.is_file():
                im = open_dds_fast(p)
                ib = im.split()
                rgb = Image.merge("RGB", (ib[0], ib[1] if len(ib) > 1 else ib[0], ib[2] if len(ib) > 2 else ib[0])).resize((tile_px, tile_px), Image.Resampling.BILINEAR)
                sr = sum(rgb.getdata(0)) / float(tile_px * tile_px)
                sg = sum(rgb.getdata(1)) / float(tile_px * tile_px)
                sb = sum(rgb.getdata(2)) / float(tile_px * tile_px)
                lr = [max(40, min(230, int((i - sr) * 0.55 + target_rgb[0]))) for i in range(256)]
                lg = [max(40, min(230, int((i - sg) * 0.55 + target_rgb[1]))) for i in range(256)]
                lb = [max(40, min(230, int((i - sb) * 0.55 + target_rgb[2]))) for i in range(256)]
                rc, gc, bc = rgb.split()
                rgb = Image.merge("RGB", (rc.point(lr), gc.point(lg), bc.point(lb)))
            else:
                rgb = Image.new("RGB", (tile_px, tile_px), target_rgb)
            tiled = Image.new("RGB", (2048, 2048))
            for y in range(0, 2048, tile_px):
                for x in range(0, 2048, tile_px):
                    tiled.paste(rgb, (x, y))
            return tiled

        # Authentic CoP / Anomaly 1.5.3 Zone palette (`detail_grnd_grass`, `ground_asphalt_01`, `ground_earth_01`, `ground_mud_01`)
        det_r = _make_tiled_detail("detail/detail_grnd_grass", (112, 118, 78), 128)
        det_g = _make_tiled_detail("detail/ground_asphalt_01", (118, 116, 112), 128)
        det_b = _make_tiled_detail("detail/ground_earth_01", (128, 108, 82), 128)
        det_a = _make_tiled_detail("detail/ground_mud_01", (92, 78, 62), 128)

        if mask_file:
            im_mask = open_dds_fast(mask_file)
            if im_mask.size != (2048, 2048):
                im_mask = im_mask.resize((2048, 2048), Image.Resampling.BILINEAR)
            mb = im_mask.split()
            mr = mb[0].filter(ImageFilter.GaussianBlur(1.5))
            mg = (mb[1] if len(mb) > 1 else Image.new("L", (2048, 2048), 0)).filter(ImageFilter.GaussianBlur(1.5))
            mbl = (mb[2] if len(mb) > 2 else Image.new("L", (2048, 2048), 0)).filter(ImageFilter.GaussianBlur(1.5))
            ma = (mb[3] if len(mb) > 3 else Image.new("L", (2048, 2048), 0)).filter(ImageFilter.GaussianBlur(1.5))

            blend = det_r
            w_earth = mbl.point(lambda p: min(255, int(p * 1.45)))
            blend = Image.composite(det_b, blend, w_earth)
            # Combine mask alpha (mud) + building/tree dark footprints so areas around houses are earthy/muddy like CoP SDK!
            w_mud = ImageChops.lighter(ma.point(lambda p: min(255, int(p * 1.45))), footprint_w)
            blend = Image.composite(det_a, blend, w_mud)
            w_asph = mg.point(lambda p: min(255, int(p * 1.55)))
            blend = Image.composite(det_g, blend, w_asph)
        else:
            blend = Image.composite(det_a, det_r, footprint_w)

        macro_rgb = Image.merge("RGB", (macro_l, macro_l, macro_l))
        out_im = ImageChops.multiply(macro_rgb, blend)
        out_im = ImageEnhance.Brightness(out_im).enhance(1.22)
        out_im = ImageEnhance.Contrast(out_im).enhance(1.12)

        buf = io.BytesIO()
        out_im.save(buf, format="PNG", optimize=False)
        png_bytes = buf.getvalue()
        cache_file.write_bytes(png_bytes)
        return (png_bytes, "image/png")
    except Exception as e:
        print(f"[terrain_splat] error for {level_name}: {e}")
        return None

MEM_LEVEL_GEOM_CACHE = {}
MEM_LEVEL_GEOM_TEX_LIST = {}

def load_level_geom_binary_payload(level_name: str) -> bytes | None:
    """Extract all static building/structure/prop visuals from level + level.geom with their exact UVs and textures."""
    if level_name in MEM_LEVEL_GEOM_CACHE:
        return MEM_LEVEL_GEOM_CACHE[level_name]
    lvl_dir = resolve_level_dir(level_name)
    lvl_path = lvl_dir / "level"
    geom_path = lvl_dir / "level.geom"
    if not lvl_path.is_file() or not geom_path.is_file() or FAST_CFORM_LIB is None:
        return None
    try:
        data = lvl_path.read_bytes()
        gdata = geom_path.read_bytes()

        off = 0
        shaders = []
        visuals_raw = b""
        while off + 8 <= len(data):
            cid, csz = struct.unpack_from("<II", data, off)
            cid &= 0x7FFFFFFF
            if cid == 2:
                shaders = [s.decode("cp1251", "ignore") for s in data[off + 12 : off + 8 + csz].split(b"\x00")]
            elif cid == 3:
                visuals_raw = data[off + 8 : off + 8 + csz]
            off += 8 + csz

        goff = 0
        vb_slices = []
        vb_uv_offs = []
        ib_slices = []
        sz_map = {0: 4, 1: 8, 2: 12, 3: 16, 4: 4, 5: 4, 6: 4, 7: 8, 8: 4}
        while goff + 8 <= len(gdata):
            gcid, gcsz = struct.unpack_from("<II", gdata, goff)
            gcid &= 0x7FFFFFFF
            sub = gdata[goff + 8 : goff + 8 + gcsz]
            goff += 8 + gcsz
            if gcid == 9:
                cnt = struct.unpack_from("<I", sub, 0)[0]
                pos = 4
                for _ in range(cnt):
                    elems = []
                    while True:
                        stream, offset, vtype, method, usage, u_idx = struct.unpack_from("<HHBBBB", sub, pos)
                        pos += 8
                        if stream == 0xFF:
                            break
                        elems.append((offset, vtype, usage, u_idx))
                    v_cnt = struct.unpack_from("<I", sub, pos)[0]
                    pos += 4
                    stride = sum(sz_map.get(e[1], 4) for e in elems)
                    uv_off = 24
                    for (e_off, e_type, e_usage, e_uidx) in elems:
                        if e_usage == 5 and e_uidx == 0:
                            uv_off = e_off
                            break
                    if stride == 32:
                        vb_slices.append((ctypes.c_uint8 * (v_cnt * 32)).from_buffer_copy(sub, pos))
                    else:
                        vb_slices.append(None)
                    vb_uv_offs.append(uv_off)
                    pos += v_cnt * stride
            elif gcid == 10:
                cnt = struct.unpack_from("<I", sub, 0)[0]
                pos = 4
                for _ in range(cnt):
                    i_cnt = struct.unpack_from("<I", sub, pos)[0]
                    pos += 4
                    ib_slices.append((ctypes.c_uint16 * i_cnt).from_buffer_copy(sub, pos))
                    pos += i_cnt * 2

        voff = 0
        buckets: dict[str, list[tuple[int, int, int, int, int, int, tuple[float, ...] | None]]] = {}
        seen_gcont = set()
        tree_count = 0
        while voff + 8 <= len(visuals_raw):
            vcid, vcsz = struct.unpack_from("<II", visuals_raw, voff)
            vsub = visuals_raw[voff + 8 : voff + 8 + vcsz]
            voff += 8 + vcsz
            soff = 0
            sh_id = 0
            mtype = 0
            gcont = None
            swi_s0 = None
            xform_16 = None
            bbox_6 = None
            while soff + 8 <= len(vsub):
                scid, scsz = struct.unpack_from("<II", vsub, soff)
                scid &= 0x7FFFFFFF
                ssub = vsub[soff + 8 : soff + 8 + scsz]
                soff += 8 + scsz
                if scid == 1 and len(ssub) >= 28:
                    ver, mtype, sh_id = struct.unpack_from("<BBH", ssub, 0)
                    bbox_6 = struct.unpack_from("<6f", ssub, 4)
                elif scid == 6 and len(ssub) >= 28:
                    # OGF_SWIDATA: 4 reserved uint32 + count uint32 + slide_window[0] (offset:uint32, num_tris:uint16, num_verts:uint16)
                    s0_off, s0_nt, s0_nv = struct.unpack_from("<IHH", ssub, 20)
                    if s0_nt > 0:
                        swi_s0 = (s0_off, s0_nt * 3)
                elif scid == 12 and len(ssub) >= 64:
                    xform_16 = struct.unpack_from("<16f", ssub, 0)
                elif scid == 21 and len(ssub) == 24:
                    gcont = struct.unpack_from("<6I", ssub, 0)
            if not gcont or mtype not in (0, 2, 7, 11):
                continue
            if mtype in (2, 11) and swi_s0 is not None and gcont[4] + swi_s0[0] + swi_s0[1] <= len(ib_slices[gcont[3]]):
                gcont = (gcont[0], gcont[1], gcont[2], gcont[3], gcont[4] + swi_s0[0], swi_s0[1])
            if mtype in (7, 11):
                if xform_16 is None:
                    continue
                tx, ty, tz = xform_16[12], xform_16[13], xform_16[14]
                tree_pos_key = (round(tx, 1), round(ty, 1), round(tz, 1))
                in_key_area = (
                    (-265.0 <= tx <= -125.0 and -210.0 <= tz <= -75.0) or
                    (-85.0 <= tx <= 60.0 and 220.0 <= tz <= 360.0) or
                    (-130.0 <= tx <= -20.0 and 100.0 <= tz <= 210.0)
                )
                if not in_key_area:
                    h_val = ((int(round(tx)) * 73856093) ^ (int(round(tz)) * 19349663)) & 0xFFFFFFFF
                    if (h_val % 6) != 0:
                        continue
                dedup_key = (gcont, tree_pos_key)
                if dedup_key in seen_gcont:
                    continue
                seen_gcont.add(dedup_key)
                if bbox_6 is not None:
                    # Transform local bbox center/extents by xform_16 translation + approximate scale
                    sx = (xform_16[0]**2 + xform_16[1]**2 + xform_16[2]**2) ** 0.5
                    sy = (xform_16[4]**2 + xform_16[5]**2 + xform_16[6]**2) ** 0.5
                    sz = (xform_16[8]**2 + xform_16[9]**2 + xform_16[10]**2) ** 0.5
                    bbox_6 = (
                        tx + bbox_6[0] * sx, ty + bbox_6[1] * sy, tz + bbox_6[2] * sz,
                        tx + bbox_6[3] * sx, ty + bbox_6[4] * sy, tz + bbox_6[5] * sz,
                    )
            else:
                if gcont in seen_gcont:
                    continue
                seen_gcont.add(gcont)
            if gcont[0] >= len(vb_slices) or vb_slices[gcont[0]] is None or (gcont[1] + gcont[2]) * 32 > len(vb_slices[gcont[0]]) or gcont[3] >= len(ib_slices) or (gcont[4] + gcont[5]) > len(ib_slices[gcont[3]]):
                continue
            sh_str = shaders[sh_id] if sh_id < len(shaders) else ""
            if "/" not in sh_str:
                continue
            base_tex = sh_str.split("/", 1)[1].split(",")[0].replace("\\", "/").strip()
            low = base_tex.lower()
            if any(k in low for k in ("terrain", "fake", "glow", "fx_", "sky", "water", "forrestwall", "antennatrees")):
                continue
            buckets.setdefault(base_tex, []).append((gcont[0], gcont[1], gcont[2], gcont[3], gcont[4], gcont[5], xform_16 if mtype in (7, 11) else None, bbox_6))

        ordered_tex = sorted(buckets.keys(), key=lambda t: -sum(g[5] for g in buckets[t]))
        all_draws = []
        groups_meta = []
        cur_idx = 0
        total_v = 0
        total_i = 0
        zero_xform = (ctypes.c_float * 16)(*([0.0] * 16))
        for t_idx, tex in enumerate(ordered_tex[:256]):
            glist = buckets[tex]
            grp_i = sum(g[5] for g in glist)
            grp_v = sum(g[2] for g in glist)
            draws_meta = []
            grp_start_idx = cur_idx
            for g in glist:
                d_start = cur_idx
                d_cnt = g[5]
                cur_idx += d_cnt
                total_v += g[2]
                total_i += d_cnt
                bb = [round(float(x), 2) for x in g[7]] if g[7] else None
                draws_meta.append([d_start, d_cnt, g[1], g[2]] + (bb if bb else [0,0,0,0,0,0]))
                xf = g[6]
                if xf is not None:
                    xf_arr = (ctypes.c_float * 16)(*xf)
                    all_draws.append(_GeomDrawSpec(g[0], g[1], g[2], g[3], g[4], g[5], t_idx, 1, xf_arr))
                else:
                    all_draws.append(_GeomDrawSpec(g[0], g[1], g[2], g[3], g[4], g[5], t_idx, 0, zero_xform))
            t_low = tex.lower()
            is_alpha = any(k in t_low for k in ("bushes", "frond", "spruce", "pine", "birch", "poplar", "oak", "fuflo", "vetka", "setka", "rabica", "kamish", "ivy", "leaf")) and not any(k in t_low for k in ("bark", "spil", "cap"))
            groups_meta.append({"tex": tex, "start": grp_start_idx, "count": grp_i, "tile_idx": t_idx, "alpha": is_alpha, "draws": draws_meta})
        MEM_LEVEL_GEOM_TEX_LIST[level_name] = ordered_tex[:256]

        n_vb = len(vb_slices)
        n_ib = len(ib_slices)
        vb_ptr_arr = (ctypes.c_void_p * n_vb)(*[ctypes.cast(b, ctypes.c_void_p) if b is not None else 0 for b in vb_slices])
        uv_off_arr = (ctypes.c_uint32 * n_vb)(*vb_uv_offs)
        ib_ptr_arr = (ctypes.c_void_p * n_ib)(*[ctypes.cast(b, ctypes.c_void_p) for b in ib_slices])
        draws_arr = (_GeomDrawSpec * len(all_draws))(*all_draws)

        out_pos = (ctypes.c_float * (total_v * 3))()
        out_norm = (ctypes.c_float * (total_v * 3))()
        out_uv = (ctypes.c_float * (total_v * 2))()
        out_tile = (ctypes.c_float * (total_v * 2))()
        out_idx = (ctypes.c_uint32 * total_i)()
        v_tot = ctypes.c_uint32()
        i_tot = ctypes.c_uint32()

        FAST_CFORM_LIB.extract_level_geom_draws(
            vb_ptr_arr, uv_off_arr, ib_ptr_arr,
            draws_arr, len(all_draws),
            out_pos, out_norm, out_uv, out_tile, out_idx,
            ctypes.byref(v_tot), ctypes.byref(i_tot)
        )

        json_bytes = json.dumps(groups_meta).encode("utf-8")
        pad = (4 - (len(json_bytes) & 3)) & 3
        if pad:
            json_bytes += b" " * pad
        hdr = struct.pack("<IIII", 0x324F4547, v_tot.value, i_tot.value, len(json_bytes))
        payload = (
            hdr
            + json_bytes
            + bytes(out_pos)[: v_tot.value * 12]
            + bytes(out_norm)[: v_tot.value * 12]
            + bytes(out_uv)[: v_tot.value * 8]
            + bytes(out_tile)[: v_tot.value * 8]
            + bytes(out_idx)[: i_tot.value * 4]
        )
        if len(MEM_LEVEL_GEOM_CACHE) >= 4:
            MEM_LEVEL_GEOM_CACHE.clear()
        MEM_LEVEL_GEOM_CACHE[level_name] = payload
        return payload
    except Exception as exc:
        print("load_level_geom_binary_payload error:", exc)
        return None



def build_level_geom_atlas_png(level_name: str) -> tuple[bytes, str] | None:
    """Build a 2048x2048 16x16 texture atlas containing up to 256 exact DDS building/prop textures for this level."""
    cache_key = f"level_geom_atlas_v8:{level_name}"
    if cache_key in MEM_TEX_CACHE:
        return MEM_TEX_CACHE[cache_key]
    disk_cache = TEXTURE_CACHE_DIR / f"level_geom_atlas_v8_{level_name.replace(':', '_')}.png"
    if disk_cache.is_file():
        data = disk_cache.read_bytes()
        res = (data, "image/png")
        MEM_TEX_CACHE[cache_key] = res
        return res
    if Image is None:
        return None
    try:
        if level_name not in MEM_LEVEL_GEOM_TEX_LIST:
            load_level_geom_binary_payload(level_name)
        tex_list = MEM_LEVEL_GEOM_TEX_LIST.get(level_name, [])
        if not tex_list:
            return None
        TILE = 128
        GRID = 16
        atlas = Image.new("RGBA", (TILE * GRID, TILE * GRID), (150, 146, 138, 255))
        lut_bright = [min(255, int(v * 1.38 + 10)) for v in range(256)]
        lut_ident = list(range(256))
        for idx, tex_rel in enumerate(tex_list[:256]):
            col = idx & 15
            row = idx >> 4
            clean = tex_rel.replace("\\", "/").strip("/")
            if clean.lower().endswith(".dds"):
                clean = clean[:-4]
            t_low = clean.lower()
            is_alpha = any(k in t_low for k in ("bushes", "frond", "spruce", "pine", "birch", "poplar", "oak", "fuflo", "vetka", "setka", "rabica", "kamish", "ivy", "leaf")) and not any(k in t_low for k in ("bark", "spil", "cap"))
            p = resolve_dds_path(clean, level_name) or (UNPACKED_DIR / "textures" / f"{clean}.dds")
            tile_im = None
            if p.is_file():
                try:
                    raw = p.read_bytes()
                    dh, dw, dpitch, ddepth, dmips = struct.unpack_from("<IIIII", raw, 12)
                    fourcc = raw[84:88]
                    if fourcc in (b"DXT1", b"DXT3", b"DXT5") and dmips > 1 and dw > TILE and dh > TILE:
                        bsz = 8 if fourcc == b"DXT1" else 16
                        off = 128
                        cw, ch = dw, dh
                        m = 0
                        while cw > TILE and ch > TILE and m < dmips - 1:
                            off += max(1, cw // 4) * max(1, ch // 4) * bsz
                            cw //= 2
                            ch //= 2
                            m += 1
                        mlen = max(1, cw // 4) * max(1, ch // 4) * bsz
                        if off + mlen <= len(raw):
                            hdr = bytearray(raw[:128])
                            struct.pack_into("<IIIII", hdr, 12, ch, cw, mlen, 0, 1)
                            tile_im = Image.open(io.BytesIO(bytes(hdr) + raw[off : off + mlen])).convert("RGBA" if is_alpha else "RGB")
                    if tile_im is None:
                        tile_im = open_dds_fast(p).convert("RGBA" if is_alpha else "RGB")
                except Exception:
                    tile_im = None
            if tile_im is not None:
                if tile_im.size != (TILE, TILE):
                    tile_im = tile_im.resize((TILE, TILE), Image.Resampling.BILINEAR)
                if is_alpha:
                    tile_im = tile_im.convert("RGBA").point(lut_bright * 3 + lut_ident)
                else:
                    tile_im = tile_im.convert("RGB").point(lut_bright * 3).convert("RGBA")
                atlas.paste(tile_im, (col * TILE, row * TILE))
        buf = io.BytesIO()
        atlas.save(buf, format="PNG", compress_level=2)
        png_bytes = buf.getvalue()
        try:
            disk_cache.write_bytes(png_bytes)
        except Exception:
            pass
        res = (png_bytes, "image/png")
        MEM_TEX_CACHE[cache_key] = res
        return res
    except Exception as exc:
        print("build_level_geom_atlas_png warning:", exc)
        return None


def load_cform_binary_payload(level_name: str) -> bytes | None:
    cform_path = resolve_level_dir(level_name) / "level.cform"
    if not cform_path.is_file() or FAST_CFORM_LIB is None:
        return None
    raw_cform = cform_path.read_bytes()
    if len(raw_cform) < 36:
        return None
    version, vertcount, facecount = struct.unpack_from("<III", raw_cform, 0)
    min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack_from("<ffffff", raw_cform, 12)
    bbox = (min_x, min_y, min_z, max_x, max_y, max_z)

    verts_bytes_len = vertcount * 12
    faces_bytes_len = facecount * 16
    if 36 + verts_bytes_len + faces_bytes_len > len(raw_cform):
        return None

    in_verts = (ctypes.c_float * (vertcount * 3)).from_buffer_copy(raw_cform, 36)
    in_faces = (ctypes.c_uint8 * faces_bytes_len).from_buffer_copy(raw_cform, 36 + verts_bytes_len)

    out_verts = (ctypes.c_float * (vertcount * 3))()
    out_colors = (ctypes.c_float * (vertcount * 3))()
    out_indices = (ctypes.c_uint32 * (facecount * 3))()
    out_tri_mats = (ctypes.c_uint16 * facecount)()
    out_tri_sectors = (ctypes.c_uint16 * facecount)()
    out_cat_counts = (ctypes.c_uint32 * 6)()

    dds_info = load_level_terrain_dds(level_name)
    if dds_info:
        dds_bytes, dds_w, dds_h, dds_fourcc = dds_info
        dds_buf = (ctypes.c_uint8 * len(dds_bytes)).from_buffer_copy(dds_bytes)
        dds_len = len(dds_bytes)
    else:
        dds_buf = None
        dds_len = dds_w = dds_h = dds_fourcc = 0

    rc = FAST_CFORM_LIB.build_cform_multilayer(
        in_verts,
        vertcount,
        in_faces,
        facecount,
        dds_buf,
        dds_len,
        dds_w,
        dds_h,
        dds_fourcc,
        min_x, min_y, min_z,
        max_x, max_y, max_z,
        out_verts,
        out_colors,
        out_indices,
        out_tri_mats,
        out_tri_sectors,
        out_cat_counts,
    )

    out_hdr = struct.pack(
        "<IIIffffffIIIIII",
        0x4D524643,
        vertcount,
        rc,
        *bbox,
        out_cat_counts[0],
        out_cat_counts[1],
        out_cat_counts[2],
        out_cat_counts[3],
        out_cat_counts[4],
        out_cat_counts[5],
    )
    return (
        out_hdr
        + bytes(out_verts)
        + bytes(out_colors)
        + bytes(out_indices)[: rc * 12]
        + bytes(out_tri_mats)[: rc * 2]
        + bytes(out_tri_sectors)[: rc * 2]
    )


MEM_AI_RAW_CACHE = {}


def _get_level_ai_raw(level_name: str, addon_id: str = None):
    ai_path = resolve_level_dir(level_name, addon_id) / "level.ai"
    if not ai_path.is_file():
        return None
    key = str(ai_path)
    if key in MEM_AI_RAW_CACHE:
        return MEM_AI_RAW_CACHE[key]
    data = ai_path.read_bytes()
    if len(data) < 56:
        return None
    if len(MEM_AI_RAW_CACHE) >= 8:
        MEM_AI_RAW_CACHE.clear()
    MEM_AI_RAW_CACHE[key] = data
    return data


def load_ai_point_cloud(level_name: str, max_nodes: int = 25000, addon_id: str = None) -> dict:
    """Sample 3D positions from level.ai to render the AI Navigation Mesh in 3D."""
    data = _get_level_ai_raw(level_name, addon_id)
    if data is None:
        return {"error": f"level.ai not found for {level_name}"}

    version, vertex_count, cell_size, factor_y, min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack_from(
        "<IIffffffff", data, 0
    )
    if vertex_count == 0:
        return {"error": "Empty level.ai"}

    rec_size = (len(data) - 56) // vertex_count
    if rec_size not in (21, 23, 25):
        rec_size = 25 if version == 13 else (21 if version <= 8 else 23)
    pxz_off = 19 if rec_size == 25 else (rec_size - 5)
    row_length = int((max_z - min_z) / cell_size + 1.5001)

    step = max(1, vertex_count // max_nodes)
    positions = []
    covers = []
    raw = memoryview(data)[56:]

    for idx in range(0, vertex_count, step):
        off = idx * rec_size
        if off + rec_size > len(raw):
            break
        if rec_size == 25:
            packed_xz = struct.unpack_from("<I", raw, off + 19)[0]
            packed_y = struct.unpack_from("<H", raw, off + 23)[0]
        else:
            b0, b1, b2, b3, b4 = raw[off + pxz_off : off + pxz_off + 5]
            packed_xz = b0 | (b1 << 8) | (b2 << 16)
            packed_y = b3 | (b4 << 8)
        row = packed_xz // row_length
        col = packed_xz % row_length
        x = min_x + row * cell_size
        z = min_z + col * cell_size
        y = min_y + (packed_y / 65535.0) * factor_y
        cov_off = 12 if rec_size >= 23 else 10
        cov_raw = struct.unpack_from("<H", raw, off + cov_off)[0]
        c_avg = ((cov_raw & 0xF) + ((cov_raw >> 4) & 0xF) + ((cov_raw >> 8) & 0xF) + ((cov_raw >> 12) & 0xF)) / 60.0
        positions.extend([round(x, 2), round(y, 2), round(z, 2)])
        covers.append(round(c_avg, 2))

    return {
        "level": level_name,
        "version": version,
        "total_nodes": vertex_count,
        "sampled_nodes": len(positions) // 3,
        "cell_size": round(cell_size, 4),
        "aabb_min": [round(min_x, 2), round(min_y, 2), round(min_z, 2)],
        "aabb_max": [round(max_x, 2), round(max_y, 2), round(max_z, 2)],
        "positions": positions,
        "covers": covers,
    }



_GAME_GRAPH_GVID_CACHE = None

def lookup_exact_game_vertex_id(level_name: str, qx: float, qy: float, qz: float) -> dict:
    global _GAME_GRAPH_GVID_CACHE
    if _GAME_GRAPH_GVID_CACHE is None:
        gg_path = (STUDIO_DIR / "index" / "game_graph_gvids.json") if (STUDIO_DIR / "index" / "game_graph_gvids.json").is_file() else (INDEX_DIR / "game_graph_gvids.json")
        if gg_path.is_file():
            try:
                _GAME_GRAPH_GVID_CACHE = json.loads(gg_path.read_text()).get("by_level", {})
            except Exception:
                _GAME_GRAPH_GVID_CACHE = {}
        else:
            _GAME_GRAPH_GVID_CACHE = {}
    verts = _GAME_GRAPH_GVID_CACHE.get(level_name, [])
    if not verts:
        return {"game_vertex_id": 0, "gvid_min": 0, "gvid_max": 0}
    best_v = min(verts, key=lambda v: (v["local_pos"][0] - qx)**2 + (v["local_pos"][1] - qy)**2 + (v["local_pos"][2] - qz)**2)
    return {
        "game_vertex_id": int(best_v["gvid"]),
        "gvid_min": int(verts[0]["gvid"]),
        "gvid_max": int(verts[-1]["gvid"]),
        "gvid_pos": best_v["local_pos"],
    }

def find_nearest_ai_node(level_name: str, qx: float, qy: float, qz: float, addon_id: str = None) -> dict:
    """Find the closest level_vertex_id in level.ai (v8/v9/v10/v13) to world position (qx, qy, qz)."""
    data = _get_level_ai_raw(level_name, addon_id)
    if data is None:
        return {"error": f"level.ai not found for {level_name}", "level": level_name}

    version, vertex_count, cell_size, factor_y, min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack_from(
        "<IIffffffff", data, 0
    )
    if vertex_count == 0:
        return {"error": f"Empty level.ai for {level_name}", "level": level_name}

    rec_size = (len(data) - 56) // vertex_count
    if rec_size not in (21, 23, 25):
        rec_size = 25 if version == 13 else (21 if version <= 8 else 23)
    row_length = int((max_z - min_z) / cell_size + 1.5001)
    nodes_bytes = data[56:]

    if FAST_CFORM_LIB is not None and hasattr(FAST_CFORM_LIB, "find_nearest_ai_node"):
        out_pos = (ctypes.c_float * 3)()
        out_dist = ctypes.c_float()
        best_id = int(
            FAST_CFORM_LIB.find_nearest_ai_node(
                nodes_bytes,
                vertex_count,
                rec_size,
                row_length,
                cell_size,
                factor_y,
                min_x,
                min_y,
                min_z,
                float(qx),
                float(qy),
                float(qz),
                out_pos,
                ctypes.byref(out_dist),
            )
        )
        return {
            "level_vertex_id": best_id,
            "distance": round(float(out_dist.value), 4),
            "node_pos": [round(float(out_pos[0]), 4), round(float(out_pos[1]), 4), round(float(out_pos[2]), 4)],
            "level": level_name,
            **lookup_exact_game_vertex_id(level_name, qx, qy, qz),
        }

    # Python binary search + neighborhood fallback (since NodeCompressed array is sorted by packed_xz)
    pxz_off = 19 if rec_size == 25 else (rec_size - 5)
    inv_65535 = factor_y / 65535.0
    best_id = 0
    best_d2 = 1e30
    best_pos = [0.0, 0.0, 0.0]

    for i in range(vertex_count):
        off = i * rec_size + pxz_off
        b0, b1, b2, b3, b4 = nodes_bytes[off : off + 5]
        packed_xz = b0 | (b1 << 8) | (b2 << 16)
        packed_y = b3 | (b4 << 8)
        row = packed_xz // row_length
        col = packed_xz % row_length
        nx = min_x + row * cell_size
        nz = min_z + col * cell_size
        dx = nx - qx
        dz = nz - qz
        d2_xz = dx * dx + dz * dz
        if d2_xz >= best_d2:
            continue
        ny = min_y + packed_y * inv_65535
        dy = ny - qy
        d2 = d2_xz + dy * dy
        if d2 < best_d2:
            best_d2 = d2
            best_id = i
            best_pos = [round(nx, 4), round(ny, 4), round(nz, 4)]

    return {
        "level_vertex_id": best_id,
        "distance": round(best_d2 ** 0.5, 4),
        "node_pos": best_pos,
        "level": level_name,
    }




def handle_play_in_engine(body: dict) -> dict:
    """Generate auto-teleport/debug startup script and optionally launch S.T.A.L.K.E.R. Anomaly directly or via Mod Organizer 2 (MO2 USVFS)."""
    import re, shutil
    raw_level = str(body.get("level") or "l01_escape")
    addon = str(body.get("addon") or "anomaly153")
    if ":" in raw_level:
        addon_prefix, clean_level = raw_level.split(":", 1)
        if addon in ("", "all", "anomaly153"):
            addon = addon_prefix
    else:
        clean_level = raw_level

    pos = body.get("position") or [0.0, 0.0, 0.0]
    px = float(pos[0]) if len(pos) > 0 else 0.0
    py = float(pos[1]) if len(pos) > 1 else 0.0
    pz = float(pos[2]) if len(pos) > 2 else 0.0

    direction = body.get("direction") or [0.0, 0.0, 1.0]
    dx = float(direction[0]) if len(direction) > 0 else 0.0
    dy = float(direction[1]) if len(direction) > 1 else 0.0
    dz = float(direction[2]) if len(direction) > 2 else 1.0

    launch_mode = str(body.get("launch_mode") or "mo2").strip().lower()
    if launch_mode not in ("mo2", "direct"):
        launch_mode = "mo2"

    # Discover Mod Organizer 2 installation directory
    custom_mo2 = str(body.get("mo2_path") or "").strip()
    mo2_candidates = []
    if custom_mo2:
        p_custom = Path(custom_mo2)
        if p_custom.is_file():
            mo2_candidates.append(p_custom.parent)
        elif p_custom.is_dir():
            mo2_candidates.append(p_custom)
    mo2_candidates.extend([
        ROOT.parent / "Mod.Organizer-2.5.2",
        ROOT / "MO2",
        ROOT.parent / "MO2",
        Path.home() / "Downloads" / "Mod.Organizer-2.5.2",
    ])
    mo2_dir = next((d for d in mo2_candidates if (d / "ModOrganizer.exe").is_file()), mo2_candidates[0])
    mo2_exe = mo2_dir / "ModOrganizer.exe"
    mo2_available = mo2_exe.is_file()

    # Discover available MO2 profiles
    mo2_profiles = ["Default"]
    selected_profile = str(body.get("mo2_profile") or "").strip()
    profiles_root = mo2_dir / "profiles"
    if profiles_root.is_dir():
        found_profs = sorted([p.name for p in profiles_root.iterdir() if p.is_dir()])
        if found_profs:
            mo2_profiles = found_profs
    if not selected_profile:
        ini_path = mo2_dir / "ModOrganizer.ini"
        if ini_path.is_file():
            m_prof = re.search(r"selected_profile=@ByteArray\(([^)]+)\)", ini_path.read_text(encoding="utf-8", errors="ignore"))
            if m_prof:
                selected_profile = m_prof.group(1).strip()
        if not selected_profile or selected_profile not in mo2_profiles:
            selected_profile = mo2_profiles[0]

    mo2_exec_title = str(body.get("mo2_executable") or "Anomaly (DX11-AVX)").strip()

    ai_info = find_nearest_ai_node(clean_level, px, py, pz, addon_id=addon if addon != "all" else None)
    lvid = ai_info.get("level_vertex_id", 0) if isinstance(ai_info, dict) else 0

    ltx_content = "\n".join([
        "; Auto-generated by Anomaly 1.5.3 Studio — Play in Engine (PIE)",
        "[studio_play_here]",
        f"level = {clean_level}",
        f"addon = {addon}",
        f"position = {px:.3f}, {py:.3f}, {pz:.3f}",
        f"direction = {dx:.3f}, {dy:.3f}, {dz:.3f}",
        f"level_vertex_id = {lvid}",
        f"startup_args = -dbg -start server({clean_level}/single/alife/new) client(localhost)",
        "",
        "[logic]",
        "active = sr_idle@teleport",
        "",
        "[sr_idle@teleport]",
        f"on_info = {{=actor_on_level({clean_level})}} %=teleport_actor({px:.3f}:{py:.3f}:{pz:.3f})% nil",
        "",
    ])

    rel_script_path = "configs/scripts/studio_play_here.ltx"
    unpacked_script = UNPACKED_DIR / "configs" / "scripts" / "studio_play_here.ltx"
    unpacked_script.parent.mkdir(parents=True, exist_ok=True)
    unpacked_script.write_text(ltx_content, encoding="utf-8")

    gamedata_script = ROOT / "gamedata" / "configs" / "scripts" / "studio_play_here.ltx"
    gamedata_script.parent.mkdir(parents=True, exist_ok=True)
    gamedata_script.write_text(ltx_content, encoding="utf-8")

    lua_content = "\n".join([
        "-- Auto-generated by Anomaly 1.5.3 Studio (Play Here Teleport Hook)",
        f'local TARGET_LEVEL = "{clean_level}"',
        f"local TARGET_POS = vector():set({px:.3f}, {py:.3f}, {pz:.3f})",
        "local teleported = false",
        "local function actor_on_first_update()",
        "    if teleported or not db or not db.actor then return end",
        "    if level and level.name() == TARGET_LEVEL then",
        "        teleported = true",
        "        db.actor:set_actor_position(TARGET_POS)",
        "    end",
        "end",
        "function on_game_start()",
        "    if RegisterScriptCallback then",
        '        RegisterScriptCallback("actor_on_first_update", actor_on_first_update)',
        "    end",
        "end",
        "",
    ])
    lua_path = ROOT / "gamedata" / "scripts" / "studio_play_here.script"
    lua_path.parent.mkdir(parents=True, exist_ok=True)
    lua_path.write_text(lua_content, encoding="utf-8")

    mo2_live_mod_name = "ZZZ_Anomaly_Studio_Live_PIE"
    mo2_live_mod_dir = mo2_dir / "mods" / mo2_live_mod_name
    if mo2_dir.is_dir():
        try:
            mo2_ltx = mo2_live_mod_dir / "gamedata" / "configs" / "scripts" / "studio_play_here.ltx"
            mo2_lua = mo2_live_mod_dir / "gamedata" / "scripts" / "studio_play_here.script"
            mo2_meta = mo2_live_mod_dir / "meta.ini"
            mo2_ltx.parent.mkdir(parents=True, exist_ok=True)
            mo2_lua.parent.mkdir(parents=True, exist_ok=True)
            mo2_ltx.write_text(ltx_content, encoding="utf-8")
            mo2_lua.write_text(lua_content, encoding="utf-8")
            mo2_meta.write_text(
                "\n".join([
                    "[General]",
                    "gameName=STALKER Anomaly",
                    "modid=0",
                    "version=1.5.3.0",
                    "newestVersion=1.5.3.0",
                    'category="-1,"',
                    "installationFile=",
                    "notes=Auto-generated Live Play-in-Engine Teleport Hook from Anomaly 1.5.3 Studio",
                    "",
                ]),
                encoding="utf-8",
            )
            modlist_file = mo2_dir / "profiles" / selected_profile / "modlist.txt"
            if modlist_file.is_file():
                lines = modlist_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                entry = f"+{mo2_live_mod_name}"
                if not any(ln.strip().lstrip("+-") == mo2_live_mod_name for ln in lines):
                    insert_idx = 0
                    while insert_idx < len(lines) and lines[insert_idx].startswith("#"):
                        insert_idx += 1
                    lines.insert(insert_idx, entry)
                    modlist_file.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        except Exception:
            pass

    bin_candidates = [
        ROOT / "bin" / "AnomalyDX11AVX.exe",
        ROOT / "bin" / "AnomalyDX11.exe",
        ROOT / "bin" / "VerifiedDX11.exe",
        ROOT / "bin" / "AnomalyDX10AVX.exe",
        ROOT / "bin" / "AnomalyDX9AVX.exe",
        ROOT / "bin" / "AnomalyDX9.exe",
        ROOT / "bin" / "xr_3da",
    ]
    chosen_bin = next((b for b in bin_candidates if b.is_file()), bin_candidates[0])
    wine_bin = shutil.which("wine") or shutil.which("wine64")
    native_xr = shutil.which("xr_3da")

    start_args = ["-dbg", "-start", f"server({clean_level}/single/alife/new)", "client(localhost)"]

    flatpak_bin = shutil.which("flatpak")
    use_portproton = bool(flatpak_bin and Path.home() / ".var" / "app" / "ru.linux_gaming.PortProton".is_dir())
    if launch_mode == "mo2" and mo2_available:
        if use_portproton:
            runner = "flatpak"
            cmd_list = ["flatpak", "run", "ru.linux_gaming.PortProton", str(mo2_exe)]
            cli_command = (
                f'flatpak run ru.linux_gaming.PortProton "{mo2_exe}" '
                f'# MO2 Live-Mod: +{mo2_live_mod_name} -> [{px:.2f}, {py:.2f}, {pz:.2f}] (LVID {lvid})'
            )
        else:
            runner = wine_bin or "wine"
            cmd_list = [runner, str(mo2_exe), "-p", selected_profile, f"moshortcut://:{mo2_exec_title}"]
            cli_command = (
                f'cd "{mo2_dir}" && {runner} "{mo2_exe}" -p "{selected_profile}" '
                f'"moshortcut://:{mo2_exec_title}" '
                f'# MO2 Live-Mod: +{mo2_live_mod_name} -> [{px:.2f}, {py:.2f}, {pz:.2f}] (LVID {lvid})'
            )
        work_cwd = str(mo2_dir)
        target_exists = mo2_exe.is_file()
    else:
        if chosen_bin.name == "xr_3da" or (native_xr and not chosen_bin.is_file()):
            exe_str = str(chosen_bin if chosen_bin.is_file() else native_xr)
            cmd_list = [exe_str] + start_args
            runner = "native"
        else:
            runner = wine_bin or "wine"
            cmd_list = [runner, str(chosen_bin)] + start_args
        cli_command = (
            f'cd "{ROOT}" && {runner} "{chosen_bin}" '
            f'-dbg -start "server({clean_level}/single/alife/new)" "client(localhost)" '
            f'# Teleport -> [{px:.2f}, {py:.2f}, {pz:.2f}] (LVID {lvid})'
        )
        work_cwd = str(ROOT)
        target_exists = chosen_bin.is_file()

    launched = False
    pid = None
    launch_error = None
    if bool(body.get("launch", False)):
        try:
            if (runner in ("native", "flatpak") or wine_bin) and target_exists:
                env_launch = os.environ.copy()
                env_launch.setdefault("DISPLAY", ":0")
                proc = subprocess.Popen(
                    cmd_list,
                    cwd=work_cwd,
                    env=env_launch,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                launched = True
                pid = proc.pid
            else:
                launch_error = "Wine or target binary not found; command & teleport script generated."
        except Exception as e:
            launch_error = str(e)

    return {
        "ok": True,
        "level": clean_level,
        "addon": addon,
        "launch_mode": launch_mode,
        "mo2_available": mo2_available,
        "mo2_dir": str(mo2_dir),
        "mo2_exe": str(mo2_exe),
        "mo2_profiles": mo2_profiles,
        "mo2_profile": selected_profile,
        "mo2_executable": mo2_exec_title,
        "mo2_live_mod": str(mo2_live_mod_dir),
        "position": [round(px, 3), round(py, 3), round(pz, 3)],
        "direction": [round(dx, 3), round(dy, 3), round(dz, 3)],
        "level_vertex_id": lvid,
        "script_path": rel_script_path,
        "gamedata_script_path": str(gamedata_script),
        "lua_script_path": str(lua_path),
        "script_content": ltx_content,
        "binary_path": str(mo2_exe if (launch_mode == "mo2" and mo2_available) else chosen_bin),
        "runner": runner,
        "command": cli_command,
        "launched": launched,
        "pid": pid,
        "launch_error": launch_error,
    }


class StudioRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        try:
            # Strip conditional cache headers so browser reload (F5) always gets 200 OK with latest JS/HTML
            if hasattr(self, "headers") and self.headers is not None:
                for h in ("If-Modified-Since", "If-None-Match", "if-modified-since", "if-none-match"):
                    try:
                        del self.headers[h]
                    except Exception:
                        pass
            self._do_GET_inner()
        except Exception as exc:
            err = v010_core_service.make_error_response(
                "BACKEND_GET_ERROR",
                f"Failed to process GET {self.path}",
                f"Ошибка обработки GET {self.path}",
                hint_en="Check Anomaly/MO2 paths in Settings and see Console Panel for details.",
                hint_ru="Проверьте пути Anomaly/MO2 в настройках и подробности в панели консоли.",
                exc=exc,
            )
            self.send_json(err, 500)

    def _do_GET_inner(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/sdk/manifest":
            self.send_json(v010_core_service.get_sdk_manifest(has_fast_cform=(FAST_CFORM_LIB is not None or FAST_CFORM_SO.is_file())))
            return

        if path == "/api/undo_state":
            self.send_json(v010_core_service.get_undo_history_state())
            return

        if path == "/api/projects":
            return self.send_json(project_service.list_projects())

        if path == "/api/settings/importable_mods":
            return self.send_json(settings_service.list_importable_mods())

        if path == "/api/settings":
            st = settings_service.load_settings()
            val = settings_service.validate_paths(
                st.get("anomaly_path", ""),
                st.get("mo2_path", ""),
                st.get("addons_input_path", ""),
                st.get("mods_output_path", ""),
            )
            vfs = db0_vfs.get_global_vfs()
            self.send_json({
                "ok": True,
                "settings": st,
                "validation": val,
                "vfs": {
                    "archives": vfs.total_archives,
                    "files": len(vfs.entries),
                    "scan_ms": vfs.scan_ms,
                },
            })
            return

        if path == "/api/qa_hold_until_done":
            t0 = _boot_time.time()
            init_logs = v010_core_service.get_logs(since_id=0).get("logs", [])
            max_init_id = max((int(it.get("id", 0)) for it in init_logs), default=0)
            wait_sec = float(qs.get("wait", ["35.0"])[0])
            only_timer = qs.get("timer_only", ["0"])[0] == "1"
            while _boot_time.time() - t0 < wait_sec:
                if not only_timer:
                    logs = v010_core_service.get_logs(since_id=max_init_id).get("logs", [])
                    if any("QA_AUTO_" in (it.get("msg_en") or "") for it in logs):
                        _boot_time.sleep(0.5)
                        break
                _boot_time.sleep(0.15)
            gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(gif)))
            self.end_headers()
            try:
                self.wfile.write(gif)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if path == "/api/console_logs":
            since_id = int(qs.get("since_id", ["0"])[0])
            level_filter = qs.get("level", ["ALL"])[0]
            logs_payload = v010_core_service.get_logs(since_id=since_id, level_filter=level_filter)
            logs_payload['boot_id'] = SERVER_BOOT_ID
            self.send_json(logs_payload)
            return

        if path == "/api/autosave":
            proj = qs.get("project", ["default"])[0]
            st_data = v010_core_service.load_autosave_state(proj)
            self.send_json({
                "ok": True,
                "state": st_data,
                "undo_count": len(v010_core_service.UNDO_STACK),
                "redo_count": len(v010_core_service.REDO_STACK),
            })
            return

        if path == "/api/qa_hold":
            import time
            time.sleep(25)
            self.send_response(204)
            self.end_headers()
            return

        if path == "/api/sdk07/overview":
            idx_p = ROOT / "index" / "sdk07_parity_index.json"
            if idx_p.is_file():
                self.send_json(json.loads(idx_p.read_text(encoding="utf-8")))
            else:
                self.send_json(sdk07_parity_service.build_shaders_and_env_index())
            return

        if path == "/api/sdk07/inspect":
            rel = (qs.get("path") or [""])[0]
            self.send_json(sdk07_parity_service.inspect_shader_or_ppe_file(rel))
            return

        if path == "/api/sdk07/validate":
            self.send_json(sdk07_parity_service.validate_lua_and_ltx_scripts(400))
            return

        if path == "/api/particles":
            p_idx = INDEX_DIR / "particles_index.json"
            data = json.loads(p_idx.read_text()) if p_idx.is_file() else {"total": 0, "categories": [], "particles": []}
            custom_p = INDEX_DIR / "particles_custom.json"
            if custom_p.is_file():
                try:
                    ov = json.loads(custom_p.read_text())
                    for p in data.get("particles", []):
                        if p["name"] in ov:
                            p.update(ov[p["name"]])
                except Exception:
                    pass
            self.send_json(data)
            return

        if path.startswith("/api/hom_snd/"):
            lvl = unquote(path.split("/api/hom_snd/")[1]) or "l01_escape"
            if hom_snd_env_service:
                self.send_json(hom_snd_env_service.inspect_level_hom_and_snd(lvl))
            else:
                self.send_json({"ok": False, "error": "hom_snd_env_service not loaded"}, 500)
            return

        if path.startswith("/api/smart_terrains/"):
            lvl = unquote(path.split("/api/smart_terrains/")[1]) or "l01_escape"
            if smart_terrain_waypoint_service:
                self.send_json(smart_terrain_waypoint_service.list_level_smart_terrains(lvl))
            else:
                self.send_json({"ok": False, "error": "smart_terrain_waypoint_service not loaded"}, 500)
            return

        if path == "/api/all_spawn/inspect":
            if all_spawn_compiler_service:
                self.send_json(all_spawn_compiler_service.inspect_all_spawn_structure())
            else:
                self.send_json({"ok": False, "error": "all_spawn_compiler_service not loaded"}, 500)
            return

        if path == "/api/quests/item_templates":
            if quest_item_cloner_service:
                self.send_json(quest_item_cloner_service.get_vanilla_quest_item_templates())
            else:
                self.send_json({"ok": False, "error": "quest_item_cloner_service not loaded"}, 500)
            return

        if path == "/api/quests/custom_items":
            if quest_item_cloner_service and hasattr(quest_item_cloner_service, "list_custom_quest_items"):
                self.send_json(quest_item_cloner_service.list_custom_quest_items())
            else:
                self.send_json({"ok": True, "items": []})
            return

        if path == "/api/quests/campaign_templates":
            if story_campaign_presets_service and hasattr(story_campaign_presets_service, "get_quest_campaign_templates"):
                self.send_json(story_campaign_presets_service.get_quest_campaign_templates())
            else:
                self.send_json({"ok": True, "templates": []})
            return

        if path == "/api/spawns/catalog":
            if spawn_catalog_service and hasattr(spawn_catalog_service, "get_verified_spawn_catalog"):
                cat = qs.get("category", [None])[0]
                q = qs.get("q", [""])[0]
                self.send_json(spawn_catalog_service.get_verified_spawn_catalog(category=cat, query=q))
            else:
                self.send_json({"ok": True, "catalog": {}})
            return

        if path == "/api/quests/overview":
            t_data = quest_logic_service.parse_all_tm_tasks()
            dlgs = quest_logic_service.list_all_dialogs()
            tips = quest_logic_service.get_loadscreen_tips()
            camps = [{"file": k, "label": v["label"], "count": v["count"]} for k, v in t_data["campaigns"].items()]
            self.send_json({
                "campaigns": camps,
                "total_tasks": len(t_data["tasks"]),
                "dialogs": dlgs[:250],
                "total_dialogs": len(dlgs),
                "loadscreen_tips": tips,
            })
            return

        if path.startswith("/api/quests/campaign/"):
            fname = unquote(path.split("/api/quests/campaign/")[1])
            self.send_json(quest_logic_service.build_campaign_graph(fname))
            return

        if path.startswith("/api/quests/dialog/"):
            did = unquote(path.split("/api/quests/dialog/")[1])
            self.send_json(quest_logic_service.get_dialog_graph(did))
            return

        if path.startswith("/api/quests/download_mod/"):
            zname = Path(unquote(path.split("/api/quests/download_mod/")[1])).name
            zpath = ROOT / "exports" / zname
            if zpath.is_file():
                raw = zpath.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{zname}"')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            self.send_json({"ok": False, "error": "Archive not found"}, 404)
            return

        if path.startswith("/api/eden/"):
            lvl = unquote(path.split("/api/eden/")[1])
            self.send_json(quest_logic_service.get_eden_campaign(lvl))
            return

        if path == "/api/loadscreen_tips":
            self.send_json({"tips": quest_logic_service.get_loadscreen_tips()})
            return

        if path == "/api/overview":
            gm_file = INDEX_DIR / "gamemtl_materials.json"
            gamemtl = json.loads(gm_file.read_text(encoding="utf-8")) if gm_file.is_file() else {}
            self.send_json({
                "levels": LEVELS_SUMMARY,
                "levels_by_addon": LEVELS_BY_ADDON,
                "spawns_summary": SPAWNS_SUMMARY,
                "ogf_count": len(OGF_FILES),
                "ltx_count": len(LTX_FILES),
                "addons": get_addons_status(),
                "materials": gamemtl,
            })
            return

        if path == "/api/addons":
            self.send_json({"addons": get_addons_status()})
            return

        if path.startswith("/api/texture/"):
            tex_rel = unquote(path[len("/api/texture/"):])
            level_name = qs.get("level", [None])[0]
            if tex_rel == "terrain_splat":
                res = build_level_terrain_splat_png(level_name or "l01_escape")
            elif tex_rel == "level_geom_atlas":
                res = build_level_geom_atlas_png(level_name or "l01_escape")
            else:
                res = load_texture_bytes(tex_rel, level_name)
            if not res:
                self.send_json({"error": f"Texture not found: {tex_rel}"}, 404)
                return
            data, mime = res
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return

        if path.startswith("/api/level_geom/"):
            lvl = unquote(path[len("/api/level_geom/"):])
            payload = load_level_geom_binary_payload(lvl)
            if not payload:
                self.send_json({"error": f"level.geom not found for {lvl}"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if path.startswith("/api/level_spawns/"):
            lvl = unquote(path.split("/api/level_spawns/")[1])
            file_key = lvl.replace(":", "_")
            sp_file = SPAWNS_PARSED_DIR / f"{file_key}_spawns.json"
            pt_file = SPAWNS_PARSED_DIR / f"{file_key}_patrols.json"
            spawns = json.loads(sp_file.read_text()) if sp_file.is_file() else []
            patrols = json.loads(pt_file.read_text()) if pt_file.is_file() else {}
            self.send_json({"level": lvl, "spawns": spawns, "patrols": patrols})
            return

        if path.startswith("/api/level_details/"):
            lvl = unquote(path.split("/api/level_details/")[1])
            max_inst = int(qs.get("max_instances", ["22000"])[0])
            if level_details_grass_service:
                self.send_json(level_details_grass_service.load_level_details_grass(lvl, max_instances=max_inst))
            else:
                self.send_json({"ok": False, "error": "level_details_grass_service not loaded"}, 500)
            return

        if path.startswith("/api/level_ai/"):
            lvl = unquote(path.split("/api/level_ai/")[1])
            addon_id = qs.get("addon", [None])[0]
            max_nodes = int(qs.get("max_nodes", ["25000"])[0])
            self.send_json(load_ai_point_cloud(lvl, max_nodes=max_nodes, addon_id=addon_id))
            return

        if path.startswith("/api/nearest_ai_node/"):
            lvl = unquote(path.split("/api/nearest_ai_node/")[1])
            addon_id = qs.get("addon", [None])[0]
            qx = float(qs.get("x", ["0.0"])[0])
            qy = float(qs.get("y", ["0.0"])[0])
            qz = float(qs.get("z", ["0.0"])[0])
            res = find_nearest_ai_node(lvl, qx, qy, qz, addon_id=addon_id)
            self.send_json(res, status=404 if "error" in res else 200)
            return

        if path.startswith("/api/level_cform_bin/"):
            lvl = unquote(path.split("/api/level_cform_bin/")[1])
            payload = load_cform_binary_payload(lvl)
            if payload is None:
                self.send_json({"error": f"Failed to load binary cform for {lvl}"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(payload)
            return

        if path == "/api/ogf_list":
            q = qs.get("q", [""])[0].lower()
            limit = int(qs.get("limit", ["300"])[0])
            matches = [f for f in OGF_FILES if q in f.lower()][:limit]
            self.send_json({"total": len(OGF_FILES), "matches": matches})
            return

        if path.startswith("/api/ogf/"):
            rel = unquote(path[len("/api/ogf/"):])
            lvl = qs.get("level", [None])[0]
            self.send_json(load_ogf_mesh(rel, level_name=lvl))
            return

        if path == "/api/ltx_list":
            q = qs.get("q", [""])[0].lower()
            limit = int(qs.get("limit", ["300"])[0])
            matches = [f for f in LTX_FILES if q in f.lower()][:limit]
            self.send_json({"total": len(LTX_FILES), "matches": matches})
            return

        if path.startswith("/api/ltx/"):
            rel = unquote(path[len("/api/ltx/"):])
            ltx_path = (UNPACKED_DIR / "configs" / rel).resolve()
            if not str(ltx_path).startswith(str((UNPACKED_DIR / "configs").resolve())) or not ltx_path.is_file():
                self.send_json({"error": "Invalid LTX path"}, 404)
                return
            content = ltx_path.read_bytes().decode("cp1251", "replace")
            self.send_json({"path": rel, "content": content})
            return

        if path.startswith("/api/"):
            self.send_json(v010_core_service.make_error_response(
                "UNKNOWN_API_GET",
                f"Unknown GET endpoint: {path}",
                f"Неизвестный GET эндпоинт: {path}",
            ), 404)
            return
        return super().do_GET()

    def do_POST(self):
        try:
            self._do_POST_inner()
        except Exception as exc:
            err = v010_core_service.make_error_response(
                "BACKEND_POST_ERROR",
                f"Failed to process POST {self.path}",
                f"Ошибка обработки POST {self.path}",
                hint_en="Verify input parameters or Anomaly/MO2 paths in Settings.",
                hint_ru="Проверьте входные параметры или пути Anomaly/MO2 в настройках.",
                exc=exc,
            )
            self.send_json(err, 500)

    def _do_POST_inner(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if path == "/api/sdk/hot_reload":
            self.send_json(v010_core_service.perform_hot_reload())
            return

        if path == "/api/quests/validate_graph":
            self.send_json(v010_core_service.validate_quest_or_dialog_graph(body))
            return

        if path == "/api/qa_browser_report":
            Path("/tmp/studio_qa_browser_report.json").write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
            return self.send_json({"ok": True})
        if path == "/api/console_logs/exec":
            res = v010_core_service.execute_debug_console_command(body.get("command", ""))
            self.send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/settings/list_dirs":
            return self.send_json(settings_service.list_filesystem_dirs(body.get("path", "")))

        if path == "/api/settings/browse_dir":
            return self.send_json(settings_service.browse_directory_dialog(body.get("title", "Select Directory"), body.get("initial_dir", "")))

        if path == "/api/settings/import_mod":
            return self.send_json(settings_service.import_mod_into_project(body))

        if path == "/api/settings":
            res_save = settings_service.save_settings(body)
            saved = res_save.get("settings", {})
            val = res_save.get("validation", {})
            vfs = db0_vfs.reload_global_vfs(saved.get("anomaly_path", ""))
            v010_core_service.append_log(
                "INFO",
                f"Updated Studio paths: anomaly={saved.get('anomaly_path')} ({vfs.total_archives} .db0 archives), mo2={saved.get('mo2_path')}",
                f"Обновлены пути Studio: anomaly={saved.get('anomaly_path')} ({vfs.total_archives} архивов .db0), mo2={saved.get('mo2_path')}",
                category="settings",
            )
            self.send_json({
                "ok": True,
                "settings": saved,
                "validation": val,
                "vfs": {
                    "archives": vfs.total_archives,
                    "files": len(vfs.entries),
                    "scan_ms": vfs.scan_ms,
                },
            })
            return

        if path == "/api/console_logs/clear":
            self.send_json(v010_core_service.clear_logs())
            return

        if path in ("/api/console_logs/append", "/api/console/log"):
            entry = v010_core_service.append_log(
                body.get("level", "INFO"),
                body.get("msg_en", ""),
                body.get("msg_ru", ""),
                category=body.get("category") or body.get("source", "ui"),
                details=body.get("details"),
            )
            self.send_json({"ok": True, "entry": entry})
            return

        if path == "/api/autosave":
            res = v010_core_service.save_autosave_payload(body)
            self.send_json(res)
            return

        if path == "/api/undo":
            res = v010_core_service.perform_undo()
            self.send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/redo":
            res = v010_core_service.perform_redo()
            self.send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/placement/action":
            res = v010_core_service.handle_placement_action(body, find_nearest_ai_fn=find_nearest_ai_node)
            self.send_json(res, 200 if res.get("ok") else 404 if res.get("code") == "OBJ_NOT_FOUND" else 400)
            return

        if path == "/api/spawn_load_check":
            res = v010_core_service.run_spawn_and_load_check(body, quest_logic_mod=quest_logic_service)
            self.send_json(res)
            return

        if path == "/api/projects/create":
            return self.send_json(project_service.create_project(body))

        if path == "/api/projects/switch":
            return self.send_json(project_service.switch_project(body))

        if path == "/api/projects/save":
            return self.send_json(project_service.save_project_and_snapshot(body))

        if path == "/api/projects/generate_lua_spawns":
            return self.send_json(project_service.generate_lua_spawn_script(body.get("project_id"), write_to_disk=True))

        if path == "/api/projects/simulate_lua_spawns":
            return self.send_json(project_service.simulate_lua_spawn_script(body.get("project_id")))

        if path == "/api/export_db0":
            res = v010_core_service.export_project_to_db0(body)
            self.send_json(res, 200 if res.get("ok") else 400)
            return

        if path == "/api/save_particle":
            custom_p = INDEX_DIR / "particles_custom.json"
            ov = json.loads(custom_p.read_text()) if custom_p.is_file() else {}
            pname = body.get("name", "")
            if pname:
                ov[pname] = body
                custom_p.write_text(json.dumps(ov, indent=2, ensure_ascii=False))
            self.send_json({"ok": True, "name": pname})
            return

        if path == "/api/navmesh/edit":
            if xrai_navmesh_service:
                self.send_json(xrai_navmesh_service.edit_navmesh_nodes(body))
            else:
                self.send_json({"ok": False, "error": "xrai_navmesh_service not loaded"}, 500)
            return

        if path == "/api/map/place_static_prop":
            if static_prop_placer_service:
                self.send_json(static_prop_placer_service.place_static_prop_with_cform_collision(body))
            else:
                self.send_json({"ok": False, "error": "static_prop_placer_service not loaded"}, 500)
            return

        if path == "/api/map/generate_smart_terrain":
            if smart_terrain_waypoint_service:
                self.send_json(smart_terrain_waypoint_service.generate_smart_terrain_and_waypoints(body))
            else:
                self.send_json({"ok": False, "error": "smart_terrain_waypoint_service not loaded"}, 500)
            return

        if path == "/api/map/patch_hom":
            if hom_snd_env_service:
                self.send_json(hom_snd_env_service.build_or_patch_level_hom(body))
            else:
                self.send_json({"ok": False, "error": "hom_snd_env_service not loaded"}, 500)
            return

        if path == "/api/ogf/import_custom":
            import base64
            rel_name = (body.get("rel_path") or body.get("filename") or "dynamics/equipments/quest/custom_item.ogf").replace("\\", "/").strip("/")
            if not rel_name.lower().endswith(".ogf"):
                rel_name += ".ogf"
            b64_data = body.get("base64_data", "")
            raw_bytes = base64.b64decode(b64_data) if b64_data else b""
            if len(raw_bytes) < 24:
                self.send_json({"ok": False, "error": "Invalid or empty .ogf file payload"}, 400)
                return
            dst_vfs = UNPACKED_DIR / "meshes" / rel_name
            dst_vfs.parent.mkdir(parents=True, exist_ok=True)
            dst_vfs.write_bytes(raw_bytes)
            dst_cust = STUDIO_DIR / "exports" / "custom_meshes" / rel_name
            dst_cust.parent.mkdir(parents=True, exist_ok=True)
            dst_cust.write_bytes(raw_bytes)
            if rel_name not in OGF_FILES:
                OGF_FILES.insert(0, rel_name)
            mesh_info = load_ogf_mesh(rel_name)
            self.send_json({
                "ok": "error" not in mesh_info,
                "rel_path": rel_name,
                "size_bytes": len(raw_bytes),
                "vertex_count": mesh_info.get("vertex_count", 0),
                "face_count": mesh_info.get("face_count", 0),
                "textures": mesh_info.get("textures", []),
            })
            return

        if path == "/api/ogf/patch_binary":
            if ogf_actor_editor_service:
                self.send_json(ogf_actor_editor_service.patch_ogf_binary(body))
            else:
                self.send_json({"ok": False, "error": "ogf_actor_editor_service not loaded"}, 500)
            return

        if path == "/api/textures/generate_thm":
            if dds_thm_pipeline_service:
                self.send_json(dds_thm_pipeline_service.generate_thm_and_dds(body))
            else:
                self.send_json({"ok": False, "error": "dds_thm_pipeline_service not loaded"}, 500)
            return

        if path == "/api/sdk07/compile_ppe":
            if xr_binary_compiler_service:
                self.send_json(xr_binary_compiler_service.compile_ppe_binary(body))
            else:
                self.send_json({"ok": False, "error": "xr_binary_compiler_service not loaded"}, 500)
            return

        if path == "/api/quests/typecheck":
            if xray_typechecker_service:
                lvl = body.get("level") or body.get("level_name") or "l01_escape"
                gdir = body.get("gamedata_dir")
                if not gdir:
                    exp_root = STUDIO_DIR / "exports"
                    cand_dirs = sorted([d / "gamedata" for d in exp_root.iterdir() if d.is_dir() and (d / "gamedata").is_dir()], key=lambda p: p.stat().st_mtime, reverse=True) if exp_root.is_dir() else []
                    lvl_match = [p for p in cand_dirs if lvl in p.parent.name]
                    gdir = str(lvl_match[0] if lvl_match else (cand_dirs[0] if cand_dirs else (exp_root / "gamedata")))
                self.send_json(xray_typechecker_service.run_xray_mod_typechecker(gdir, lvl))
            else:
                self.send_json({"ok": False, "error": "xray_typechecker_service not loaded"}, 500)
            return

        if path == "/api/quests/clone_item":
            if quest_item_cloner_service:
                if "new_section" in body and "section_id" not in body:
                    body["section_id"] = body["new_section"]
                bsec = body.get("base_section") or body.get("template_id") or "device_pda_1"
                if "template_id" not in body:
                    body["template_id"] = bsec
                if "inv_name" in body and "name_en" not in body:
                    body["name_en"] = body["inv_name"]
                    body["name_de"] = body["inv_name"]
                if "description" in body and "descr_en" not in body:
                    body["descr_en"] = body["description"]
                    body["descr_de"] = body["description"]
                res = quest_item_cloner_service.clone_quest_item_to_ltx(body)
                self.send_json(res)
            else:
                self.send_json({"ok": False, "error": "quest_item_cloner_service not loaded"}, 500)
            return

        if path == "/api/landscape/patch_5layers":
            if level_5layer_patcher_service:
                if "x" in body and "center_x" not in body:
                    body["center_x"] = body["x"]
                if "z" in body and "center_z" not in body:
                    body["center_z"] = body["z"]
                if "level" in body and "level_name" not in body:
                    body["level_name"] = body["level"]
                res = level_5layer_patcher_service.apply_5layer_terrain_brush(body)
                self.send_json(res)
            else:
                self.send_json({"ok": False, "error": "level_5layer_patcher_service not loaded"}, 500)
            return

        if path == "/api/lua/optimize":
            if alao_lua_optimizer_service:
                code_txt = body.get("code", "")
                apply_fixes = bool(body.get("apply_fixes", True))
                self.send_json(alao_lua_optimizer_service.analyze_and_optimize_lua(code_txt, apply_fixes=apply_fixes))
            else:
                self.send_json({"ok": False, "error": "alao_lua_optimizer_service not loaded"}, 500)
            return

        if path == "/api/navmesh/verify_region":
            if navmesh_cform_sync_service:
                lvl = body.get("level", "l01_escape")
                cx = float(body.get("x", -145.0))
                cz = float(body.get("z", -110.0))
                rad = float(body.get("radius", 25.0))
                self.send_json(navmesh_cform_sync_service.verify_navmesh_region(lvl, cx, cz, rad))
            else:
                self.send_json({"ok": False, "error": "navmesh_cform_sync_service not loaded"}, 500)
            return

        if path == "/api/quests/instantiate_template":
            if story_campaign_presets_service and hasattr(story_campaign_presets_service, "instantiate_quest_template"):
                self.send_json(story_campaign_presets_service.instantiate_quest_template(body))
            else:
                self.send_json({"ok": False, "error": "story_campaign_presets_service not loaded"}, 500)
            return

        if path in ("/api/quests/save_template", "/api/quest_templates/save_custom"):
            if story_campaign_presets_service and hasattr(story_campaign_presets_service, "save_custom_template"):
                self.send_json(story_campaign_presets_service.save_custom_template(body))
            else:
                self.send_json({"ok": False, "error": "story_campaign_presets_service not loaded"}, 500)
            return

        if path == "/api/quests/save_node":
            self.send_json(quest_logic_service.save_quest_and_text(body))
            return

        if path == "/api/quests/export_mod":
            self.send_json(quest_logic_service.build_moddb_addon_zip(body))
            return

        if path == "/api/landscape/fetch_opentopomap":
            self.send_json(landscape_service.fetch_realworld_opentopomap_dem(body))
            return

        if path == "/api/landscape/import_heightmap":
            self.send_json(landscape_service.parse_heightmap_upload(body))
            return

        if path == "/api/landscape/preset":
            self.send_json(landscape_service.generate_procedural_preset(body))
            return

        if path == "/api/landscape/compile_cform":
            self.send_json(landscape_service.save_and_compile_landscape_cform(body))
            return

        if path == "/api/eden/save":
            self.send_json(quest_logic_service.save_eden_campaign(body))
            return

        if path == "/api/save_loadscreen_tip":
            self.send_json(quest_logic_service.save_loadscreen_tip(body))
            return

        if path == "/api/save_ltx":
            rel = body.get("path", "")
            content = body.get("content", "")
            ltx_path = (UNPACKED_DIR / "configs" / rel).resolve()
            if not str(ltx_path).startswith(str((UNPACKED_DIR / "configs").resolve())):
                self.send_json({"error": "Invalid path"}, 400)
                return
            ltx_path.write_bytes(content.encode("cp1251", "replace"))
            self.send_json({"ok": True, "path": rel, "bytes": ltx_path.stat().st_size})
            return

        if path == "/api/save_spawns":
            lvl = body.get("level", "")
            file_key = lvl.replace(":", "_")
            spawns = body.get("spawns", [])
            sp_file = SPAWNS_PARSED_DIR / f"{file_key}_spawns.json"
            if sp_file.is_file():
                sp_file.write_text(json.dumps(spawns, indent=2, ensure_ascii=False))
            self.send_json({"ok": True, "level": lvl, "count": len(spawns)})
            return

        if path in ("/api/play_in_engine", "/api/studio/play-in-engine"):
            self.send_json(handle_play_in_engine(body))
            return

        if path == "/api/pack_db":
            src_folder = body.get("source_folder", "configs")
            out_name = body.get("output_name", "zzz_anomaly_studio_patch.db0")
            src_dir = (UNPACKED_DIR / src_folder).resolve()
            out_path = (ROOT / "mods" / Path(out_name).name).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "python3",
                str(STUDIO_DIR / "cli" / "anomaly_db_tool.py"),
                "pack",
                str(src_dir),
                str(out_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            self.send_json({
                "ok": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "output_path": str(out_path),
            })
            return

        self.send_json(v010_core_service.make_error_response("UNKNOWN_ENDPOINT", f"Unknown API endpoint: {path}", f"Неизвестный API эндпоинт: {path}", hint_en="Query GET /api/sdk/manifest for all supported SDK endpoints.", hint_ru="Запросите GET /api/sdk/manifest для списка поддерживаемых эндпоинтов SDK."), 404)




class _InProcessRequestAdapter(StudioRequestHandler):
    """
    Executes any StudioRequestHandler GET or POST route 100% in-memory (zero TCP/IP sockets, zero 127.0.0.1 ports)
    for the Native Desktop Edition (anomaly://studio/ custom URI scheme & IPC bridge).
    """
    def __init__(self, method: str, raw_path: str, body_bytes: bytes = b""):
        self.command = (method or "GET").upper()
        self.path = raw_path or "/"
        self.request_version = "HTTP/1.1"
        self.client_address = ("inprocess", 0)
        self.directory = str(FRONTEND_DIR)
        self.headers = {"Content-Length": str(len(body_bytes or b""))}
        self.rfile = io.BytesIO(body_bytes or b"")
        self.wfile = io.BytesIO()
        self._status_code = 200
        self._resp_headers = {}

    def send_response(self, code, message=None):
        self._status_code = int(code)

    def send_header(self, keyword, value):
        self._resp_headers[str(keyword).lower()] = str(value)

    def end_headers(self):
        pass


def dispatch_inprocess_request(method: str, raw_path: str, body_bytes: bytes = b"") -> tuple[int, str, bytes]:
    """
    Dispatches a request directly in-process without opening any network port.
    Returns (status_code, content_type, payload_bytes).
    """
    m = (method or "GET").upper()
    parsed = urlparse(raw_path or "/")
    clean_path = parsed.path or "/"

    # Static frontend files (when not /api/*)
    if m == "GET" and not clean_path.startswith("/api/"):
        rel = clean_path.lstrip("/") or "index.html"
        fpath = (FRONTEND_DIR / rel).resolve()
        if str(fpath).startswith(str(FRONTEND_DIR.resolve())) and fpath.is_file():
            ext = fpath.suffix.lower()
            mime_map = {
                ".html": "text/html; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon",
            }
            return 200, mime_map.get(ext, "application/octet-stream"), fpath.read_bytes()
        return 404, "text/plain; charset=utf-8", b"Not Found"

    adapter = _InProcessRequestAdapter(m, raw_path, body_bytes)
    if m == "POST":
        adapter.do_POST()
    elif m == "OPTIONS":
        adapter.do_OPTIONS()
    else:
        adapter.do_GET()
    ctype = adapter._resp_headers.get("content-type", "application/json; charset=utf-8")
    return adapter._status_code, ctype, adapter.wfile.getvalue()


if __name__ == "__main__":
    port = int(os.environ.get("ANOMALY_STUDIO_PORT", "8780"))
    server = ThreadingHTTPServer(("127.0.0.1", port), StudioRequestHandler)
    print(f"[Anomaly 1.5.3 Studio] Listening on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
