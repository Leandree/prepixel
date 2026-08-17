# -*- coding: utf-8 -*-
"""Python port of src/coverage-guard.mjs for the native Windows cells.

Guard A: content-energy on a per-region PrintWindow crop (PIL port of the
sharp implementation: 64x64 resize, modal color via 4-bit/channel histogram,
ink ratio = pixels with L1 distance > 48 from the mode).
Guard B: view self-consistency ("N items claimed, 0 rows exposed").
Plus: structural-coverage accounting of a window's client area.
"""
import re


def content_energy(img):
    """img: PIL Image (any mode). Returns ink ratio 0..1 (same math as mjs)."""
    small = img.convert("RGB").resize((64, 64))
    px = list(small.getdata())
    hist = {}
    for r, g, b in px:
        k = (r >> 4) << 8 | (g >> 4) << 4 | (b >> 4)
        hist[k] = hist.get(k, 0) + 1
    mode_k = max(hist, key=hist.get)
    mr, mg, mb = ((mode_k >> 8) & 15) << 4, ((mode_k >> 4) & 15) << 4, (mode_k & 15) << 4
    ink = sum(1 for r, g, b in px
              if abs(r - mr) + abs(g - mg) + abs(b - mb) > 48)
    return ink / len(px)


COUNT_RE = re.compile(r"(\d+)\s+(tracks?|items?|results?|rows?|files?|messages?|projects?|élément)", re.I)
ROW_RE = re.compile(r"^(row|listitem|cell|treeitem|dataitem)\b", re.I)


def self_consistency(view_text):
    """Flags 'declares N>0 items but 0 rows' (the rekordbox shape)."""
    lines = view_text.split("\n")
    row_lines = sum(1 for l in lines if ROW_RE.match(l))
    flags = []
    for l in lines:
        m = COUNT_RE.search(l)
        if m and int(m.group(1)) > 0 and row_lines == 0:
            flags.append({"claim": f"{m.group(1)} {m.group(2)}", "rowsExposed": 0,
                          "line": l.strip() + "  [inconsistent: count>0 but 0 rows -> unexposed list, crop]"})
    return flags


def spot_check(window_img, wrect, suspects, threshold=0.03):
    """suspects: [{label, rect:[x,y,w,h] screen coords, hasReadableContent}].
    Crops each suspect from the PrintWindow image (window-relative) and flags."""
    wx, wy = wrect[0], wrect[1]
    out = []
    for s in suspects:
        if s.get("hasReadableContent"):
            out.append({**s, "verdict": "ok"})
            continue
        x, y, w, h = s["rect"]
        lx, ly = x - wx, y - wy
        lx2, ly2 = min(lx + w, window_img.width), min(ly + h, window_img.height)
        lx, ly = max(lx, 0), max(ly, 0)
        if lx2 - lx < 8 or ly2 - ly < 8:
            out.append({**s, "verdict": "crop-out-of-bounds"})
            continue
        crop = window_img.crop((lx, ly, lx2, ly2))
        e = content_energy(crop)
        silent = e >= threshold
        out.append({**s, "energy": round(e, 3), "crop": crop,
                    "verdict": "SILENT->declare-opaque" if silent else "genuinely-empty",
                    "line": (f'[pixels] group {x},{y},{w},{h} "{s["label"]}" [unverified: pixels show content]'
                             if silent else
                             f'group {x},{y},{w},{h} "{s["label"]}" (empty, pixel-confirmed)')})
    return out


def structural_coverage(nodes, wrect, min_leaf=16):
    """Fraction of the client area covered by CONTENT-BEARING nodes (name or
    value on a leaf-ish node). nodes: [{t, n, r:[x,y,w,h], d}]. Coarse grid
    accounting (32x32 cells) to avoid double-counting overlaps."""
    wx, wy, ww, wh = wrect
    if ww <= 0 or wh <= 0:
        return 0.0
    GRID = 48
    covered = set()
    for nd in nodes:
        if not nd.get("n"):
            continue
        if nd["t"] in ("WindowControl", "PaneControl", "GroupControl", "CustomControl") and nd.get("d", 9) < 3:
            continue  # big named containers don't count as content
        x, y, w, h = nd["r"]
        if w < min_leaf or h < min_leaf or w * h > 0.5 * ww * wh:
            continue
        for gx in range(max(0, (x - wx) * GRID // ww), min(GRID, ((x - wx + w) * GRID + ww - 1) // ww)):
            for gy in range(max(0, (y - wy) * GRID // wh), min(GRID, ((y - wy + h) * GRID + wh - 1) // wh)):
                covered.add((gx, gy))
    return len(covered) / (GRID * GRID)


def empty_big_regions(nodes, min_area=150000):
    """Regions structure exposes but with NO readable content in their subtree:
    the suspects Guard A must pixel-check. Containment judged geometrically."""
    def contains(outer, inner):
        ox, oy, ow, oh = outer
        ix, iy, iw, ih = inner
        return ix >= ox - 2 and iy >= oy - 2 and ix + iw <= ox + ow + 2 and iy + ih <= oy + oh + 2
    out = []
    content_nodes = [nd for nd in nodes if nd.get("n") and nd["t"] not in
                     ("WindowControl", "PaneControl", "GroupControl", "CustomControl")]
    for nd in nodes:
        x, y, w, h = nd["r"]
        if w * h < min_area:
            continue
        if nd["t"] not in ("PaneControl", "GroupControl", "CustomControl", "TableControl", "ListControl"):
            continue
        inner_content = [c for c in content_nodes if contains(nd["r"], c["r"])]
        if not inner_content:
            out.append({"label": nd.get("n") or nd.get("cls") or nd["t"],
                        "rect": nd["r"], "hasReadableContent": False,
                        "node_type": nd["t"], "depth": nd.get("d")})
    # keep only the INNERMOST suspects (drop any that contain another suspect)
    pruned = [s for s in out
              if not any(o is not s and contains(s["rect"], o["rect"]) for o in out)]
    return pruned


def synthesize_client_suspect(wrect, coverage, caption_h=32, max_coverage=0.15):
    """Frame-only trees (Swing without JAB, Heaven) expose NO container over the
    client area, so empty_big_regions finds nothing to check — the guard's own
    blind spot, found by the Swing cell. When structural coverage of the client
    area is near zero, the router must synthesize the whole client rect as the
    suspect."""
    if coverage >= max_coverage:
        return None
    x, y, w, h = wrect
    return {"label": "client-area (synthesized: frame-only tree)",
            "rect": [x, y + caption_h, w, h - caption_h],
            "hasReadableContent": False, "node_type": "synthesized", "depth": -1}
