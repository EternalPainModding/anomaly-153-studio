#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

typedef struct {
    uint32_t i0, i1, i2, flags;
} xrTri;

/*
 * Fast on-the-fly pixel sampler from DDS / Pillow RGBA buffer
 * Supports raw RGBA bytes (fourcc == 0, hdr 0 or 128) as well as DXT1/DXT3/DXT5 blocks.
 */
static inline void sample_dds_pixel(
    const uint8_t* dds_data, uint32_t dds_len, uint32_t w, uint32_t h, uint32_t fourcc,
    float u, float v, float* r_out, float* g_out, float* b_out
) {
    if (u < 0.0f) u = 0.0f; else if (u > 1.0f) u = 1.0f;
    if (v < 0.0f) v = 0.0f; else if (v > 1.0f) v = 1.0f;
    uint32_t ix = (uint32_t)(u * (float)(w - 1));
    uint32_t iy = (uint32_t)(v * (float)(h - 1));

    if (fourcc == 0) {
        size_t hdr = (dds_len >= 128 + (size_t)w * h * 4) ? 128 : 0;
        size_t off = hdr + ((size_t)iy * w + ix) * 4;
        if (off + 4 <= dds_len) {
            *r_out = dds_data[off + 0] / 255.0f;
            *g_out = dds_data[off + 1] / 255.0f;
            *b_out = dds_data[off + 2] / 255.0f;
            return;
        }
    } else {
        uint32_t bx = ix >> 2;
        uint32_t by = iy >> 2;
        uint32_t bw = (w + 3) >> 2;
        uint32_t block_size = (fourcc == 0x31545844U) ? 8 : 16;
        uint32_t color_off = (fourcc == 0x31545844U) ? 0 : 8;
        size_t off = 128 + ((size_t)by * bw + bx) * block_size + color_off;
        if (off + 8 <= dds_len) {
            uint16_t c0 = *(const uint16_t*)(dds_data + off);
            uint16_t c1 = *(const uint16_t*)(dds_data + off + 2);
            uint32_t bits = *(const uint32_t*)(dds_data + off + 4);
            uint32_t px_idx = ((iy & 3) * 4 + (ix & 3)) * 2;
            uint32_t code = (bits >> px_idx) & 3;

            float r0 = ((c0 >> 11) & 31) / 31.0f;
            float g0 = ((c0 >> 5) & 63) / 63.0f;
            float b0 = (c0 & 31) / 31.0f;
            float r1 = ((c1 >> 11) & 31) / 31.0f;
            float g1 = ((c1 >> 5) & 63) / 63.0f;
            float b1 = (c1 & 31) / 31.0f;

            if (code == 0) { *r_out = r0; *g_out = g0; *b_out = b0; return; }
            if (code == 1) { *r_out = r1; *g_out = g1; *b_out = b1; return; }
            if (code == 2) { *r_out = (2.0f*r0 + r1)/3.0f; *g_out = (2.0f*g0 + g1)/3.0f; *b_out = (2.0f*b0 + b1)/3.0f; return; }
            *r_out = (r0 + 2.0f*r1)/3.0f; *g_out = (g0 + 2.0f*g1)/3.0f; *b_out = (b0 + 2.0f*b1)/3.0f;
            return;
        }
    }
    *r_out = 0.35f; *g_out = 0.44f; *b_out = 0.28f;
}

static inline uint8_t classify_material(uint32_t mat_id) {
    switch (mat_id) {
        case 39:
            return 3; /* Trees (trunks & branches) */
        case 37:
        case 95:
            return 4; /* Bush collision cones */
        case 11:
        case 96:
            return 2; /* Water */
        case 0:
        case 80:
        case 82:
        case 88:
        case 97:
        case 98:
        case 99:
            return 5; /* Fake walls / borders / invisible blockers */
        case 4:  /* asphalt */
        case 7:  /* earth */
        case 8:  /* gravel */
        case 10: /* dirt */
        case 15: /* grass */
        case 16: /* sand */
        case 93: /* earth_death */
        case 94: /* earth_slide */
            return 0; /* Terrain & Roads */
        default:
            if (mat_id == 1 || mat_id == 58 || mat_id == 63 || mat_id == 64 ||
                mat_id == 84 || mat_id == 85 || mat_id == 90 || mat_id == 91 || mat_id == 92) {
                return 5;
            }
            return 1; /* Buildings, Walls, Roofs & Props */
    }
}

static inline void get_material_rgb(
    uint32_t mat_id, float vx, float vy, float vz, float slope,
    const uint8_t* sat_dds, uint32_t sat_len, uint32_t sat_w, uint32_t sat_h, uint32_t sat_fourcc,
    float min_x, float max_x, float min_z, float max_z, float t_height,
    float* r_out, float* g_out, float* b_out
) {
    float detail = 1.0f;
    float biome = 0.5f;

    if ((mat_id == 7 || mat_id == 8 || mat_id == 10 || mat_id == 15 || mat_id == 16 || mat_id == 4 || mat_id == 93 || mat_id == 94) &&
        sat_dds != NULL && sat_w > 0 && sat_h > 0) {
        float u = (vx - min_x) / (max_x - min_x);
        float v = (max_z - vz) / (max_z - min_z);
        float sr, sg, sb;
        sample_dds_pixel(sat_dds, sat_len, sat_w, sat_h, sat_fourcc, u, v, &sr, &sg, &sb);

        /* sat_dds is already pre-composited from terrain_*.dds (Hemi/AO) + terrain_*_mask.dds (4-channel splat).
           Only apply smooth, gentle topographic modulation (no harsh brown step on slopes!) */
        if (mat_id == 4) {
            /* Asphalt roads: distinct road surface */
            float lum = 0.299f * sr + 0.587f * sg + 0.114f * sb;
            sr = 0.22f + lum * 0.32f;
            sg = 0.23f + lum * 0.33f;
            sb = 0.25f + lum * 0.35f;
        } else if (mat_id == 8) {
            /* Railway gravel / ballast embankment */
            float lum = 0.299f * sr + 0.587f * sg + 0.114f * sb;
            sr = 0.34f + lum * 0.35f;
            sg = 0.32f + lum * 0.33f;
            sb = 0.28f + lum * 0.30f;
        } else {
            /* Preserve authentic X-Ray shaders.xr splat color from sat_dds with only subtle cliff rock blend */
            float cliff_rock = (slope < 0.48f) ? ((0.48f - slope) * 0.65f) : 0.0f;
            if (cliff_rock > 0.28f) cliff_rock = 0.28f;
            sr = sr * (1.0f - cliff_rock) + 0.44f * cliff_rock;
            sg = sg * (1.0f - cliff_rock) + 0.41f * cliff_rock;
            sb = sb * (1.0f - cliff_rock) + 0.36f * cliff_rock;
        }

        if (sr < 0.06f) sr = 0.06f; else if (sr > 1.0f) sr = 1.0f;
        if (sg < 0.08f) sg = 0.08f; else if (sg > 1.0f) sg = 1.0f;
        if (sb < 0.05f) sb = 0.05f; else if (sb > 1.0f) sb = 1.0f;
        *r_out = sr * detail;
        *g_out = sg * detail;
        *b_out = sb * detail;
        return;
    }

    switch (mat_id) {
        case 4:  *r_out = 0.26f * detail; *g_out = 0.27f * detail; *b_out = 0.29f * detail; break;
        case 7:  *r_out = (0.34f + 0.08f * biome) * detail; *g_out = (0.45f + 0.07f * slope) * detail; *b_out = 0.25f * detail; break;
        case 8:  *r_out = 0.45f * detail; *g_out = 0.43f * detail; *b_out = 0.37f * detail; break;
        case 10:
        case 93:
        case 94: *r_out = 0.46f * detail; *g_out = 0.37f * detail; *b_out = 0.25f * detail; break;
        case 15: *r_out = 0.29f * detail; *g_out = 0.49f * detail; *b_out = 0.23f * detail; break;
        case 16: *r_out = 0.54f * detail; *g_out = 0.47f * detail; *b_out = 0.33f * detail; break;
        case 18: *r_out = 0.94f * detail; *g_out = 0.88f * detail; *b_out = 0.85f * detail; break; /* Bricks (briks_br2) */
        case 2:
        case 19:
        case 76: *r_out = 0.93f * detail; *g_out = 0.90f * detail; *b_out = 0.84f * detail; break; /* Wood walls/planks (wood_walls8) */
        case 3:
        case 53:
        case 12:
        case 78: *r_out = 0.92f * detail; *g_out = 0.91f * detail; *b_out = 0.89f * detail; break; /* Concrete & Stucco (crete_beton_lom) */
        case 49: *r_out = 0.90f * detail; *g_out = 0.91f * detail; *b_out = 0.93f * detail; break; /* Slate Roofs (roof_schiffer_01) */
        case 5:
        case 13:
        case 34:
        case 60:
        case 61:
        case 71:
        case 72: *r_out = 0.90f * detail; *g_out = 0.89f * detail; *b_out = 0.88f * detail; break; /* Metal roofs/plates (mtl_rja_01) */
        case 48: *r_out = 0.88f * detail; *g_out = 0.89f * detail; *b_out = 0.87f * detail; break;
        case 6:
        case 86: *r_out = 0.55f; *g_out = 0.72f; *b_out = 0.78f; break;
        case 11:
        case 96: *r_out = 0.18f; *g_out = 0.44f; *b_out = 0.62f; break;
        case 39:
            /* Trees: forest green canopy & warm bark brown */
            if (slope > 0.35f) {
                *r_out = 0.25f * detail; *g_out = 0.44f * detail; *b_out = 0.22f * detail;
            } else {
                *r_out = 0.38f * detail; *g_out = 0.31f * detail; *b_out = 0.22f * detail;
            }
            break;
        case 37:
        case 95: *r_out = 0.26f * detail; *g_out = 0.46f * detail; *b_out = 0.24f * detail; break;
        case 81: *r_out = 0.49f * detail; *g_out = 0.47f * detail; *b_out = 0.38f * detail; break;
        case 0:
        case 80:
        case 82:
        case 97: *r_out = 0.35f * detail; *g_out = 0.41f * detail; *b_out = 0.45f * detail; break;
        default:
            *r_out = (0.30f + t_height * 0.28f) * detail;
            *g_out = (0.40f + t_height * 0.28f) * detail;
            *b_out = (0.25f + t_height * 0.20f) * detail;
            break;
    }
}

uint32_t build_cform_multilayer(
    const float* verts_in,
    uint32_t vertcount,
    const uint8_t* faces_in,
    uint32_t facecount,
    const uint8_t* sat_dds,
    uint32_t sat_len,
    uint32_t sat_w,
    uint32_t sat_h,
    uint32_t sat_fourcc,
    float min_x, float min_y, float min_z,
    float max_x, float max_y, float max_z,
    float* verts_out,
    float* colors_out,
    uint32_t* tris_out,
    uint16_t* tri_mats_out,
    uint16_t* tri_sectors_out,
    uint32_t* cat_counts_out
) {
    const xrTri* tris = (const xrTri*)faces_in;
    float* nx = (float*)calloc(vertcount, sizeof(float));
    float* ny = (float*)calloc(vertcount, sizeof(float));
    float* nz = (float*)calloc(vertcount, sizeof(float));
    uint16_t* v_mat = (uint16_t*)calloc(vertcount, sizeof(uint16_t));
    uint8_t* v_cat = (uint8_t*)malloc(vertcount);
    memset(v_cat, 255, vertcount);
    uint8_t* f_cat = (uint8_t*)malloc(facecount);

    uint32_t counts[6] = {0, 0, 0, 0, 0, 0};

    for (uint32_t i = 0; i < facecount; ++i) {
        uint32_t i0 = tris[i].i0;
        uint32_t i1 = tris[i].i1;
        uint32_t i2 = tris[i].i2;
        if (i0 >= vertcount || i1 >= vertcount || i2 >= vertcount) {
            f_cat[i] = 255;
            continue;
        }
        uint32_t mat = tris[i].flags & 0x3FFFU;

        float x0 = verts_in[i0 * 3 + 0], y0 = verts_in[i0 * 3 + 1], z0 = verts_in[i0 * 3 + 2];
        float x1 = verts_in[i1 * 3 + 0], y1 = verts_in[i1 * 3 + 1], z1 = verts_in[i1 * 3 + 2];
        float x2 = verts_in[i2 * 3 + 0], y2 = verts_in[i2 * 3 + 1], z2 = verts_in[i2 * 3 + 2];

        float ux = x1 - x0, uy = y1 - y0, uz = z1 - z0;
        float vx = x2 - x0, vy = y2 - y0, vz = z2 - z0;
        float fnx = uy * vz - uz * vy;
        float fny = uz * vx - ux * vz;
        float fnz = ux * vy - uy * vx;

        uint8_t cat = classify_material(mat);
        f_cat[i] = cat;
        counts[cat]++;

        /* Priority assignment: Buildings (cat=1) take priority over Terrain (cat=0) at wall foundations
           so green grass vertex color never bleeds up onto house walls! */
        uint8_t prio = (cat == 1) ? 0 : ((cat == 0) ? 1 : cat);
        if (prio < v_cat[i0] || (prio == 0 && v_cat[i0] == 0 && (mat == 18 || mat == 49 || mat == 19))) { v_cat[i0] = prio; v_mat[i0] = (uint16_t)mat; }
        if (prio < v_cat[i1] || (prio == 0 && v_cat[i1] == 0 && (mat == 18 || mat == 49 || mat == 19))) { v_cat[i1] = prio; v_mat[i1] = (uint16_t)mat; }
        if (prio < v_cat[i2] || (prio == 0 && v_cat[i2] == 0 && (mat == 18 || mat == 49 || mat == 19))) { v_cat[i2] = prio; v_mat[i2] = (uint16_t)mat; }

        if (cat <= 3) {
            nx[i0] += fnx; ny[i0] += fny; nz[i0] += fnz;
            nx[i1] += fnx; ny[i1] += fny; nz[i1] += fnz;
            nx[i2] += fnx; ny[i2] += fny; nz[i2] += fnz;
        }
    }

    uint32_t offsets[6];
    uint32_t tri_idx_offsets[6];
    uint32_t running = 0;
    for (int c = 0; c < 6; ++c) {
        cat_counts_out[c] = counts[c];
        offsets[c] = running * 3;
        tri_idx_offsets[c] = running;
        running += counts[c];
    }

    for (uint32_t i = 0; i < facecount; ++i) {
        uint8_t cat = f_cat[i];
        if (cat >= 6) continue;
        uint32_t pos = offsets[cat];
        uint32_t tpos = tri_idx_offsets[cat];
        tris_out[pos + 0] = tris[i].i0;
        tris_out[pos + 1] = tris[i].i1;
        tris_out[pos + 2] = tris[i].i2;
        if (tri_mats_out) tri_mats_out[tpos] = (uint16_t)(tris[i].flags & 0x3FFFU);
        if (tri_sectors_out) tri_sectors_out[tpos] = (uint16_t)(tris[i].flags >> 16);
        offsets[cat] += 3;
        tri_idx_offsets[cat] += 1;
    }

    float span_y = (max_y - min_y > 1.0f) ? (max_y - min_y) : 1.0f;
    const float lx = 0.42f, ly = 0.82f, lz = 0.38f;

    for (uint32_t v = 0; v < vertcount; ++v) {
        float vx = verts_in[v * 3 + 0];
        float vy = verts_in[v * 3 + 1];
        float vz_orig = verts_in[v * 3 + 2];
        float vz = vz_orig;
        verts_out[v * 3 + 0] = vx;
        verts_out[v * 3 + 1] = vy;
        verts_out[v * 3 + 2] = vz;

        float vnx = nx[v], vny = ny[v], vnz = nz[v];
        float len = sqrtf(vnx * vnx + vny * vny + vnz * vnz);
        float shade = 0.78f;
        float slope = 1.0f;
        if (len > 1e-6f) {
            vnx /= len; vny /= len; vnz /= len;
            float dot = fabsf(vnx * lx + vny * ly + vnz * lz);
            shade = 0.46f + 0.54f * dot;
            slope = fabsf(vny);
        }

        float t = (vy - min_y) / span_y;
        if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;

        float r, g, b;
        get_material_rgb(
            v_mat[v], vx, vy, vz_orig, slope,
            sat_dds, sat_len, sat_w, sat_h, sat_fourcc,
            min_x, max_x, min_z, max_z, t,
            &r, &g, &b
        );

        colors_out[v * 3 + 0] = r * shade;
        colors_out[v * 3 + 1] = g * shade;
        colors_out[v * 3 + 2] = b * shade;
    }

    free(nx);
    free(ny);
    free(nz);
    free(v_mat);
    free(v_cat);
    free(f_cat);
    return running;
}

uint32_t find_nearest_ai_node(
    const uint8_t* nodes_raw,
    uint32_t vertex_count,
    uint32_t rec_size,
    uint32_t row_length,
    float cell_size,
    float factor_y,
    float min_x,
    float min_y,
    float min_z,
    float qx,
    float qy,
    float qz,
    float* out_pos,
    float* out_dist
) {
    if (!nodes_raw || vertex_count == 0 || rec_size < 21 || row_length == 0) {
        if (out_dist) *out_dist = -1.0f;
        return 0;
    }
    uint32_t pxz_off = (rec_size == 25) ? 19 : (rec_size - 5);
    uint32_t best_id = 0;
    float best_d2 = 1e30f;
    float best_x = min_x, best_y = min_y, best_z = min_z;
    const float inv_65535 = factor_y / 65535.0f;

    for (uint32_t i = 0; i < vertex_count; ++i) {
        const uint8_t* p = nodes_raw + (size_t)i * rec_size + pxz_off;
        uint32_t packed_xz;
        uint16_t packed_y;
        if (rec_size == 25) {
            packed_xz = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
            packed_y = (uint16_t)p[4] | ((uint16_t)p[5] << 8);
        } else {
            packed_xz = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16);
            packed_y = (uint16_t)p[3] | ((uint16_t)p[4] << 8);
        }
        uint32_t row = packed_xz / row_length;
        uint32_t col = packed_xz % row_length;
        float nx = min_x + (float)row * cell_size;
        float nz = min_z + (float)col * cell_size;
        float dx = nx - qx;
        float dz = nz - qz;
        float d2_xz = dx * dx + dz * dz;
        if (d2_xz >= best_d2) continue;

        float ny = min_y + (float)packed_y * inv_65535;
        float dy = ny - qy;
        float d2 = d2_xz + dy * dy;
        if (d2 < best_d2) {
            best_d2 = d2;
            best_id = i;
            best_x = nx;
            best_y = ny;
            best_z = nz;
        }
    }

    if (out_pos) {
        out_pos[0] = best_x;
        out_pos[1] = best_y;
        out_pos[2] = best_z;
    }
    if (out_dist) {
        *out_dist = sqrtf(best_d2);
    }
    return best_id;
}

typedef struct {
    uint32_t vb_id;
    uint32_t vb_off;
    uint32_t vb_cnt;
    uint32_t ib_id;
    uint32_t ib_off;
    uint32_t ib_cnt;
    uint32_t tile_idx;
    uint32_t has_xform;
    float xform[16];
} GeomDrawSpec;

uint32_t extract_level_geom_draws(
    const uint8_t** vb_ptrs,
    const uint32_t* vb_uv_offs,
    const uint16_t** ib_ptrs,
    const GeomDrawSpec* draws,
    uint32_t draw_count,
    float* out_pos,
    float* out_norm,
    float* out_uv,
    float* out_tile,
    uint32_t* out_idx,
    uint32_t* out_vert_total,
    uint32_t* out_idx_total
) {
    uint32_t v_cur = 0;
    uint32_t i_cur = 0;
    const float inv_1024 = 1.0f / 1024.0f;
    const float inv_127  = 1.0f / 127.5f;

    for (uint32_t d = 0; d < draw_count; ++d) {
        uint32_t vb_id  = draws[d].vb_id;
        uint32_t vb_off = draws[d].vb_off;
        uint32_t vb_cnt = draws[d].vb_cnt;
        uint32_t ib_id  = draws[d].ib_id;
        uint32_t ib_off = draws[d].ib_off;
        uint32_t ib_cnt = draws[d].ib_cnt;

        const uint8_t* vb = vb_ptrs[vb_id];
        uint32_t uv_off   = vb_uv_offs[vb_id];
        const uint16_t* ib = ib_ptrs[ib_id];
        if (!vb || !ib) continue;

        uint32_t has_xf = draws[d].has_xform;
        const float* xf = draws[d].xform;
        for (uint32_t v = 0; v < vb_cnt; ++v) {
            const uint8_t* vp = vb + (size_t)(vb_off + v) * 32;
            const float* pf = (const float*)vp;
            uint32_t dst_v = v_cur + v;
            float lx = pf[0], ly = pf[1], lz = pf[2];
            if (has_xf) {
                out_pos[dst_v * 3 + 0] = lx * xf[0] + ly * xf[4] + lz * xf[8]  + xf[12];
                out_pos[dst_v * 3 + 1] = lx * xf[1] + ly * xf[5] + lz * xf[9]  + xf[13];
                out_pos[dst_v * 3 + 2] = lx * xf[2] + ly * xf[6] + lz * xf[10] + xf[14];
            } else {
                out_pos[dst_v * 3 + 0] = lx;
                out_pos[dst_v * 3 + 1] = ly;
                out_pos[dst_v * 3 + 2] = lz;
            }

            out_norm[dst_v * 3 + 0] = 0.0f;
            out_norm[dst_v * 3 + 1] = 0.35f;
            out_norm[dst_v * 3 + 2] = 0.0f;

            const int16_t* uvs = (const int16_t*)(vp + uv_off);
            float u, vt;
            if (has_xf) {
                u  = (float)uvs[0] * (1.0f / 2048.0f);
                vt = (float)uvs[1] * (1.0f / 2048.0f);
            } else {
                /* Exact X-Ray unpack_tc_base(I.tc, I.T.w, I.B.w) from shaders/r3/common_functions.h */
                float du = (float)vp[19] / 255.0f;
                float dv = (float)vp[23] / 255.0f;
                u  = ((float)uvs[0] + du) * inv_1024;
                vt = ((float)uvs[1] + dv) * inv_1024;
            }
            uint32_t t_idx = draws[d].tile_idx & 255U;
            uint32_t t_col = t_idx & 15U;
            uint32_t t_row = t_idx >> 4;
            out_uv[dst_v * 2 + 0] = u;
            out_uv[dst_v * 2 + 1] = 1.0f - vt;
            if (out_tile) {
                out_tile[dst_v * 2 + 0] = (float)t_col;
                out_tile[dst_v * 2 + 1] = (float)(15U - t_row);
            }
        }

        const uint16_t* ip = ib + ib_off;
        uint32_t valid_i = 0;
        for (uint32_t k = 0; k + 2 < ib_cnt; k += 3) {
            uint32_t r0 = (uint32_t)ip[k + 0];
            uint32_t r1 = (uint32_t)ip[k + 1];
            uint32_t r2 = (uint32_t)ip[k + 2];
            if (r0 >= vb_cnt || r1 >= vb_cnt || r2 >= vb_cnt) continue;
            uint32_t i0 = v_cur + r0;
            uint32_t i1 = v_cur + r1;
            uint32_t i2 = v_cur + r2;
            out_idx[i_cur + valid_i + 0] = i0;
            out_idx[i_cur + valid_i + 1] = i1;
            out_idx[i_cur + valid_i + 2] = i2;
            valid_i += 3;

            float ux = out_pos[i1 * 3 + 0] - out_pos[i0 * 3 + 0];
            float uy = out_pos[i1 * 3 + 1] - out_pos[i0 * 3 + 1];
            float uz = out_pos[i1 * 3 + 2] - out_pos[i0 * 3 + 2];
            float vx = out_pos[i2 * 3 + 0] - out_pos[i0 * 3 + 0];
            float vy = out_pos[i2 * 3 + 1] - out_pos[i0 * 3 + 1];
            float vz = out_pos[i2 * 3 + 2] - out_pos[i0 * 3 + 2];
            float fnx = uy * vz - uz * vy;
            float fny = uz * vx - ux * vz;
            float fnz = ux * vy - uy * vx;
            /* Keep vertical component gently upward-biased so walls/roofs receive clean sun + sky light */
            if (fny < 0.0f) fny = -fny * 0.65f;
            out_norm[i0 * 3 + 0] += fnx; out_norm[i0 * 3 + 1] += fny; out_norm[i0 * 3 + 2] += fnz;
            out_norm[i1 * 3 + 0] += fnx; out_norm[i1 * 3 + 1] += fny; out_norm[i1 * 3 + 2] += fnz;
            out_norm[i2 * 3 + 0] += fnx; out_norm[i2 * 3 + 1] += fny; out_norm[i2 * 3 + 2] += fnz;
        }
        for (uint32_t v = 0; v < vb_cnt; ++v) {
            uint32_t dst_v = v_cur + v;
            float nx = out_norm[dst_v * 3 + 0];
            float ny = out_norm[dst_v * 3 + 1];
            float nz = out_norm[dst_v * 3 + 2];
            float len = sqrtf(nx * nx + ny * ny + nz * nz);
            if (len > 1e-6f) {
                out_norm[dst_v * 3 + 0] = nx / len;
                out_norm[dst_v * 3 + 1] = ny / len;
                out_norm[dst_v * 3 + 2] = nz / len;
            } else {
                out_norm[dst_v * 3 + 0] = 0.0f;
                out_norm[dst_v * 3 + 1] = 1.0f;
                out_norm[dst_v * 3 + 2] = 0.0f;
            }
        }

        v_cur += vb_cnt;
        i_cur += valid_i;
    }

    if (out_vert_total) *out_vert_total = v_cur;
    if (out_idx_total)  *out_idx_total  = i_cur;
    return i_cur / 3;
}
