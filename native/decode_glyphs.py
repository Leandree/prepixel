#!/usr/bin/env python3
"""Decode GSK text-node glyph IDs back to strings using the font's cmap.

GTK4 serializes text nodes post-shaping: `glyphs: 70 7, 82 8, ...` is
(glyph_id, advance) pairs. For simple (non-ligature, LTR) runs the reverse
cmap recovers the exact string — a one-time table per font.

Usage: decode_glyphs.py <font.ttf> "70 7, 82 8, 80 13"
"""
import sys
from fontTools.ttLib import TTFont

def reverse_cmap(font_path):
    f = TTFont(font_path)
    order = f.getGlyphOrder()
    rev = {}
    for cp, gname in f.getBestCmap().items():
        rev.setdefault(gname, cp)
    return order, rev

def decode(glyphs_field, order, rev):
    ids = [int(pair.strip().split()[0]) for pair in glyphs_field.split(',') if pair.strip()]
    out = []
    for gid in ids:
        gname = order[gid]
        out.append(chr(rev[gname]) if gname in rev else f'\\g{gid}')
    return ''.join(out)

if __name__ == '__main__':
    order, rev = reverse_cmap(sys.argv[1])
    print(decode(sys.argv[2], order, rev))
