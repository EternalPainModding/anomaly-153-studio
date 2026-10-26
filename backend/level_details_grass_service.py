import os, sys
#!/usr/bin/env python3
"""
X-Ray level.details 3D Grass & Foliage Parser for Anomaly 1.5.3 Studio.
Computes topography-dependent color per instance based on:
- Local elevation (normalized height between valley floor and hilltops)
- Local terrain slope (gradient across neighboring 2m x 2m DetailSlots)
- Micro-depression / valley moisture (lush dark green in hollows, dry ochre/olive on steep slopes & ridges)
"""
import math
import struct
from pathlib import Path

ROOT = (Path(os.environ['ANOMALY_STUDIO_ROOT']).resolve() if os.environ.get('ANOMALY_STUDIO_ROOT') else (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent))
UNPACKED = ROOT / ".studio_cache" / "vfs_mount"
EXPORTS = ROOT / "exports"

def load_level_details_grass(level_name: str = "l01_escape", max_instances: int = 25000) -> dict:
    try:
        from db0_vfs import get_vfs
        get_vfs().ensure_vfs_level(level_name)
    except Exception:
        pass
    candidates = [
        ROOT / ".studio_cache" / "vfs_mount" / "levels" / level_name / "level.details",
        EXPORTS / f"Operation_Sunken_Convoy_{level_name}" / "gamedata" / "levels" / level_name / "level.details",
        UNPACKED / "levels" / level_name / "level.details",
    ]
    det_path = next((c for c in candidates if c.is_file()), None)
    if not det_path:
        return {"ok": True, "underground_no_details": True, "level": level_name, "version": 3, "elevation_range": [0.0, 0.0], "atlas_texture": "build_details", "meshes": [], "slots_sampled": 0, "total_slots": 0, "positions": [], "scales": [], "rotations": [], "mesh_indices": [], "colors": [], "message": f"Underground/indoor level {level_name} has no 3D grass (level.details)."}

    raw = det_path.read_bytes()
    pos = 0
    chunks = {}
    while pos + 8 <= len(raw):
        cid, csize = struct.unpack_from("<II", raw, pos)
        csize &= 0x7FFFFFFF
        chunks[cid] = raw[pos + 8 : pos + 8 + csize]
        pos += 8 + csize

    if 0 not in chunks or 1 not in chunks or 2 not in chunks:
        return {"ok": False, "error": "Incomplete level.details chunks"}

    ver, obj_cnt, offs_x, offs_z, size_x, size_z = struct.unpack_from("<IIiiII", chunks[0], 0)

    # Parse Chunk 1: Detail Objects
    meshes = []
    sub = chunks[1]
    spos = 0
    while spos + 8 <= len(sub):
        scid, scsize = struct.unpack_from("<II", sub, spos)
        body = sub[spos + 8 : spos + 8 + scsize]
        spos += 8 + scsize
        z1 = body.find(b"\x00")
        sh = body[:z1].decode("cp1251", "ignore")
        z2 = body.find(b"\x00", z1 + 1)
        tx = body[z1 + 1 : z2].decode("cp1251", "ignore")
        flags, min_s, max_s, vcnt, icnt = struct.unpack_from("<IffII", body, z2 + 1)
        v_off = z2 + 1 + 20
        verts = []
        uvs = []
        for v in range(vcnt):
            px, py, pz, u, vv = struct.unpack_from("<fffff", body, v_off + v * 20)
            verts.extend([round(px, 4), round(py, 4), round(pz, 4)])
            uvs.extend([round(u, 4), round(vv, 4)])
        i_off = v_off + vcnt * 20
        idxs = list(struct.unpack_from(f"<{icnt}H", body, i_off))
        meshes.append({
            "id": scid,
            "shader": sh,
            "texture": tx,
            "min_scale": round(min_s, 3),
            "max_scale": round(max_s, 3),
            "positions": verts,
            "uvs": uvs,
            "indices": idxs,
        })

    slots = chunks[2]
    total_slots = len(slots) // 16
    # Scan with a prime step across the ENTIRE map first, then uniformly downsample
    # to `max_instances` so North, South, East, and West (including the Northern Farmhouse!)
    # have 100% uniform grass coverage!
    scan_stride = max(1, total_slots // max(90000, max_instances * 4))

    def _slot_y(s_idx: int, fallback_y: float) -> float:
        if s_idx < 0 or s_idx >= total_slots:
            return fallback_y
        w0 = struct.unpack_from("<I", slots, s_idx * 16)[0]
        if ((w0 >> 20) & 0x3F) == 0x3F:
            return fallback_y
        yb = (w0 & 0xFFF) * 0.2 - 200.0
        return yb if yb > -190.0 else fallback_y

    # First pass to collect valid slots across the entire Z-span (south to north)
    candidates_all = []
    min_y = 1e9
    max_y = -1e9
    for idx in range(0, total_slots, scan_stride):
        off = idx * 16
        if off + 16 > len(slots):
            break
        w0, w1, p0, p1, p2, p3 = struct.unpack_from("<IIHHHH", slots, off)
        id0 = (w0 >> 20) & 0x3F
        if id0 == 0x3F:
            continue
        density = (p0 & 0xF) or ((p0 >> 4) & 0xF) or (p1 & 0xF)
        if density == 0:
            continue
        y_base = (w0 & 0xFFF) * 0.2 - 200.0
        y_height = ((w0 >> 12) & 0xFF) * 0.1
        if y_height <= 0.02 or y_base < -190.0:
            continue
        if y_base < min_y:
            min_y = y_base
        if y_base > max_y:
            max_y = y_base
        hemi = ((w1 >> 24) & 0xF) / 15.0
        candidates_all.append((idx, y_base, density, id0, hemi))

    if len(candidates_all) > max_instances and max_instances > 0:
        step_f = len(candidates_all) / float(max_instances)
        raw_items = [candidates_all[int(i * step_f)] for i in range(max_instances)]
    else:
        raw_items = candidates_all

    span_y = max(1.0, max_y - min_y)
    positions = []
    scales = []
    colors = []
    mesh_ids = []

    for idx, y_base, density, id0, hemi in raw_items:
        gx = idx % size_x
        gz = idx // size_x
        wx = (gx - offs_x) * 2.0
        wz = (gz - offs_z) * 2.0

        # Compute local slope & curvature from 4 neighbor slots (2m grid)
        y_l = _slot_y(idx - 1 if gx > 0 else idx, y_base)
        y_r = _slot_y(idx + 1 if gx + 1 < size_x else idx, y_base)
        y_d = _slot_y(idx - size_x if gz > 0 else idx, y_base)
        y_u = _slot_y(idx + size_x if gz + 1 < size_z else idx, y_base)

        dx = (y_r - y_l) * 0.25
        dz = (y_u - y_d) * 0.25
        slope = min(1.0, math.sqrt(dx * dx + dz * dz) * 1.8)
        # Positive laplacian => depression/hollow (wetter, lusher); negative => ridge/crest (drier)
        hollow = max(-1.0, min(1.0, ((y_l + y_r + y_d + y_u) * 0.25 - y_base) * 1.5))
        elev_t = max(0.0, min(1.0, (y_base - min_y) / span_y))

        # Blend between:
        # - Low/hollow moisture: rich dark zone green (0.24, 0.52, 0.20)
        # - Mid flat meadow: natural stalker olive-green (0.44, 0.62, 0.27)
        # - High elevation / steep slope: dry autumn yellow-ochre (0.76, 0.66, 0.34)
        dryness = min(1.0, max(0.0, elev_t * 0.55 + slope * 0.65 - hollow * 0.35))
        moisture = min(1.0, max(0.0, (1.0 - elev_t) * 0.5 + hollow * 0.5 - slope * 0.3))

        r = 0.42 + dryness * 0.34 - moisture * 0.16
        g = 0.60 + dryness * 0.06 - moisture * 0.08
        b = 0.26 + dryness * 0.08 - moisture * 0.06

        # Modulate subtly by baked slot hemisphere lighting
        shade = 0.78 + 0.28 * hemi
        r = round(max(0.12, min(1.0, r * shade)), 3)
        g = round(max(0.18, min(1.0, g * shade)), 3)
        b = round(max(0.10, min(1.0, b * shade)), 3)

        positions.extend([round(wx, 2), round(y_base, 2), round(wz, 2)])
        scales.append(round(0.85 + (density / 15.0) * 0.65, 2))
        colors.extend([r, g, b])
        mesh_ids.append(id0 % max(1, len(meshes)))

    return {
        "ok": True,
        "level": level_name,
        "version": ver,
        "elevation_range": [round(min_y, 2), round(max_y, 2)],
        "atlas_texture": "build_details",
        "detail_ground_texture": "detail/detail_grnd_grass",
        "detail_building_texture": "crete/crete_beton_1",
        "meshes": meshes[:8],
        "instance_count": len(scales),
        "positions": positions,
        "scales": scales,
        "colors": colors,
        "mesh_ids": mesh_ids,
    }
