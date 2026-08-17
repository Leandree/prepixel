#!/usr/bin/env python3
"""distill-osworld — adapter from OSWorld's AT-SPI accessibility-tree XML to the
prepixel line grammar (spec: src/distill-hardened.mjs and §3.1 of the paper).

Condition B of OSWORLD-PROTOCOL.md §2: the agent's observation is this view
instead of a screenshot. One line per visible node, same shapes as the web
distiller:

    text x,y,w,h "content"              readable static text
    <role> x,y,w,h "name" [value="…"]   interactive element (role token kept,
                                        like the desktop AT-SPI cells)
    [pixels] <kind> x,y,w,h [alt=…]     DECLARED pictorial/opaque blind spot
                                        (image, canvas, icon, drawing-area,
                                        unknown-with-no-text)

plus a side-channel (--suspects-out) listing coverage-guard suspects: named or
sized containers whose whole subtree exposes no readable content — the
OBS/qBittorrent silent-divergence shape. The RUNNER spot-checks those rects on
the window pixels (judgeCrop: energy>=0.01 OR edge>=0.01) and, when the guard
fires, appends `[pixels] group x,y,w,h "label" [unverified: pixels show
content]` to the view before the agent sees it.

Differences vs the web distiller, stated honestly:
 - no hit-testing through AT-SPI, so no [occluded] tags — occlusion hardening
   is web-only; the desktop channel's known limits apply (see coverage-guard
   header). The guard covers the structure-empty class, not substitution.
 - visibility = AT-SPI states showing+visible + positive extents + viewport
   clip, i.e. the same filter OSWorld's own linearizer uses (judge_node in
   mm_agents/accessibility_tree_wrap/heuristic_retrieve.py), but WITHOUT its
   "has a name or text" requirement for opaque roles: a nameless canvas is
   exactly what must be DECLARED, not dropped.

CLI:
    python3 distill-osworld.py tree.xml [--viewport 1920x1080]
                                        [--suspects-out suspects.json]
Importable:
    view, suspects = distill(xml_string, vw, vh)
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET

NS_STATE = "https://accessibility.ubuntu.example.org/ns/state"
NS_COMP = "https://accessibility.ubuntu.example.org/ns/component"
NS_VALUE = "https://accessibility.ubuntu.example.org/ns/value"
NS_ATTR = "https://accessibility.ubuntu.example.org/ns/attributes"

# Roles the agent can act on -> emitted as `<role> x,y,w,h "name"`.
INTERACTIVE = {
    "push-button", "button", "toggle-button", "check-box", "radio-button",
    "combo-box", "entry", "password-text", "text", "spin-button", "slider",
    "menu", "menu-item", "check-menu-item", "radio-menu-item", "page-tab",
    "link", "list-item", "tree-item", "table-cell", "scroll-bar", "searchbox",
    "textbox", "textfield", "textarea", "terminal", "document-text",
    "document-web", "document-frame",
}
# Text-bearing, non-interactive -> `text x,y,w,h "…"`.
TEXTUAL = {"label", "static", "heading", "paragraph", "caption", "tooltip"}
# Pictorial / structure-cannot-read-inside -> `[pixels] …` (DECLARED).
OPAQUE = {"image", "icon", "canvas", "drawing-area", "animation", "video",
          "chart", "unknown"}
# Containers eligible as coverage-guard suspects when their subtree is mute.
SUSPECT_MIN_AREA = 150_000  # px², the qBittorrent-cell trigger size


def _get(node, ns, key, default=""):
    return node.get("{{{}}}{}".format(ns, key), default)


def _coords(node):
    try:
        x, y = eval(_get(node, NS_COMP, "screencoord", "(-1, -1)"))
        w, h = eval(_get(node, NS_COMP, "size", "(-1, -1)"))
        return int(x), int(y), int(w), int(h)
    except Exception:
        return -1, -1, -1, -1


def _visible(node, vw, vh):
    if _get(node, NS_STATE, "showing", "false") != "true":
        return False
    if _get(node, NS_STATE, "visible", "false") != "true":
        return False
    x, y, w, h = _coords(node)
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return False
    if x + w < 0 or y + h < 0 or x > vw or y > vh:
        return False
    return True


def _q(s):
    return '"' + s.replace('"', '""') + '"'


def _readable(node):
    """Does this node itself carry text an agent could read?"""
    name = node.get("name", "") or ""
    text = (node.text or "").strip()
    value = _get(node, NS_VALUE, "value", "") or _get(node, NS_VALUE, "current", "")
    return bool(name.strip() or text or str(value).strip())


def distill(xml_string, vw=1920, vh=1080):
    root = ET.fromstring(xml_string)
    lines, suspects = [], []
    seen_lines = set()          # exact-duplicate suppression (label child echoing parent)
    seen_suspect_rects = set()
    consumed = set()            # text nodes promoted into a parent's label
    BIG = 0.6 * vw * vh         # background layers: no text emission, no suspects
                                # (guard KNOWN LIMIT 2: area-relative metrics dilute
                                # on huge rects, so a full-screen suspect is useless)

    # Pass 1: does each subtree expose ANY readable content? (for suspects)
    subtree_readable = {}

    def mark(node):
        r = _readable(node)
        for child in node:
            r = mark(child) or r
        subtree_readable[id(node)] = r
        return r

    mark(root)

    def emit(line):
        if line not in seen_lines:
            seen_lines.add(line)
            lines.append(line)

    def promote_label(node):
        """First readable text among descendants -> label for a nameless
        interactive parent; every descendant carrying that same text is
        consumed (widgets often expose label+static twins)."""
        label = ""
        for child in node.iter():
            if child is node:
                continue
            t = (child.get("name", "") or "").strip() or (child.text or "").strip()
            if t and not label:
                label = t
            if t and t == label:
                consumed.add(id(child))
        return label

    def walk(node):
        role = node.tag
        if _visible(node, vw, vh):
            x, y, w, h = _coords(node)
            big = w * h >= BIG
            box = f"{x},{y},{w},{h}"
            name = (node.get("name", "") or "").strip()
            text = (node.text or "").strip()
            value = str(_get(node, NS_VALUE, "value", "")
                        or _get(node, NS_VALUE, "current", "")).strip()

            if role in OPAQUE:
                alt = name or _get(node, NS_ATTR, "description", "")
                emit(f"[pixels] {role} {box}" + (f" alt={alt}" if alt else ""))
            elif role in INTERACTIVE and id(node) not in consumed:
                label = name or text or promote_label(node)
                if label:
                    # a named widget's descendants often re-expose the same
                    # string as label/static twins — consume them
                    for child in node.iter():
                        if child is not node and (
                            (child.get("name", "") or "").strip() == label
                            or (child.text or "").strip() == label):
                            consumed.add(id(child))
                val = f' value={_q(value)}' if value else ""
                if not label and not val and (w < 4 or h < 4):
                    pass        # 1px nameless slivers: separators, not widgets
                else:
                    emit(f"{role} {box}" + (f" {_q(label)}" if label else "") + val)
                if not label and not val and not list(node) and not big \
                        and w * h >= SUSPECT_MIN_AREA:
                    rect = (x, y, w, h)
                    if rect not in seen_suspect_rects:
                        seen_suspect_rects.add(rect)
                        suspects.append({"label": f"nameless {role}",
                                         "rect": [x, y, w, h],
                                         "hasReadableContent": False})
            elif (role in TEXTUAL or text or name) and not big:
                t = text or name
                if t and id(node) not in consumed:
                    emit(f"text {box} {_q(t)}")
            else:
                # nameless structural node: candidate silent blind spot when its
                # WHOLE subtree is mute and it is big enough to hide content
                # (the SpeedPlotView shape: filler "" kids=0). Background-sized
                # panes are excluded (see BIG above).
                if not subtree_readable[id(node)] and not list(node) and not big \
                        and w * h >= SUSPECT_MIN_AREA:
                    rect = (x, y, w, h)
                    if rect not in seen_suspect_rects:
                        seen_suspect_rects.add(rect)
                        suspects.append({"label": f"mute {role} (kids=0)",
                                         "rect": [x, y, w, h],
                                         "hasReadableContent": False})
        for child in node:
            walk(child)

    walk(root)
    return "\n".join(lines), suspects


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree_xml")
    ap.add_argument("--viewport", default="1920x1080")
    ap.add_argument("--suspects-out")
    args = ap.parse_args()
    vw, vh = (int(v) for v in args.viewport.split("x"))
    xml_string = open(args.tree_xml, encoding="utf-8").read()
    view, suspects = distill(xml_string, vw, vh)
    if args.suspects_out:
        json.dump(suspects, open(args.suspects_out, "w"), indent=1)
    sys.stdout.write(view + "\n")


if __name__ == "__main__":
    main()
