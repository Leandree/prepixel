#!/usr/bin/env python3
"""distill-osworld v2 — adapter from OSWorld's AT-SPI accessibility-tree XML to
the prepixel line grammar (spec: src/distill-hardened.mjs §3.1 + driver v2 per
manager_orders/DRIVER-V2-SPEC.md §2.1/2.3/2.6).

Condition B of OSWORLD-PROTOCOL.md §2: the agent's observation is this view
instead of a screenshot. One line per node; the DRIVER prefixes each line with
an element id (e1, e2, …) valid for the current step:

    text x,y,w,h "content"                   readable static text
    <role> x,y,w,h "name" [value="…"]        interactive element
           [state=checked:false,focused,…]   (v2: states emitted, §2.3)
    [offscreen] <role> x,y,w,h "name" …      exists on the page, outside the
                                             viewport (v2 §2.6; scroll_to)
    [pixels] <kind> x,y,w,h [alt=…]          DECLARED pictorial/opaque blind
                                             spot (croppable)

v2 API — distill() returns STRUCTURED RECORDS, not a joined string, so the
driver can assign ids, resolve action targets and scope the act-guard:

    records, suspects, inconsistents = distill(xml_string, vw, vh)
    record = {kind: element|text|pixels|offscreen|note, role, rect,
              label, value, states (dict), line (str, WITHOUT id prefix)}

`suspects` — coverage-guard candidates (mute subtrees >=150k px², the
OBS/qBittorrent shape) for the runner's judgeCrop spot-check, unchanged v1.
`inconsistents` — declared-count-vs-zero-rows candidates (the Chrome
"1 result" / rekordbox shape, spec §2.5): nodes whose name/text declares
N>0 results while the surrounding subtree exposes zero item-role nodes.
The DRIVER re-probes once and, if the contradiction persists, emits
`[pixels] group x,y,w,h [self-inconsistent: declares N …, exposes 0 rows]`.

States emission (v2 §2.3), honest deviation from the spec's
`state=enabled,focusable` example, documented in the returns file: the
OSWorld server writes state attributes ONLY when the state is set (measured:
st:enabled="true" on 378/1665 nodes of the smoke tree, never "false"), so
absence is not evidence of disabled, and emitting enabled/focusable on every
line is token bloat with no information. We emit POSITIVE states
(checked/pressed/selected/expanded/focused) plus an explicit `checked:false`
for checkable roles where absence IS the answer.

Other honest differences vs the web distiller (unchanged from v1): no
hit-testing through AT-SPI so no [occluded] tags; nameless opaque nodes are
DECLARED [pixels], not dropped.

CLI (debug):
    python3 distill-osworld.py tree.xml [--viewport 1920x1080]
                                        [--suspects-out suspects.json]
"""
import argparse
import json
import re
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
# Roles whose checked-ness is the point: absence of st:checked = checked:false.
CHECKABLE = {"toggle-button", "check-box", "radio-button", "check-menu-item",
             "radio-menu-item"}
# Item roles counted when validating a declared result count (§2.5 re-probe).
ITEM_ROLES = {"list-item", "tree-item", "table-cell", "table-row", "row",
              "cell", "menu-item"}
COUNT_RE = re.compile(
    r"\b(\d+)\s+(results?|items?|rows?|matches?|entries|entry)\b", re.I)

SUSPECT_MIN_AREA = 150_000  # px², the qBittorrent-cell trigger size
OFFSCREEN_CAP = 60          # max [offscreen] lines; overflow declared, §2.6


def _get(node, ns, key, default=""):
    return node.get("{{{}}}{}".format(ns, key), default)


def _coords(node):
    try:
        x, y = eval(_get(node, NS_COMP, "screencoord", "(-1, -1)"))
        w, h = eval(_get(node, NS_COMP, "size", "(-1, -1)"))
        return int(x), int(y), int(w), int(h)
    except Exception:
        return -1, -1, -1, -1


def _position(node, vw, vh):
    """None = not renderable (state or extents); "on" = intersects viewport;
    "off" = renderable page content outside the viewport (v2 §2.6)."""
    if _get(node, NS_STATE, "showing", "false") != "true":
        return None
    if _get(node, NS_STATE, "visible", "false") != "true":
        return None
    x, y, w, h = _coords(node)
    if w <= 0 or h <= 0 or (x, y) == (-1, -1):
        return None
    if x >= vw or y >= vh or x + w <= 0 or y + h <= 0:
        return "off"
    return "on"


def _q(s):
    return '"' + s.replace('"', '""') + '"'


def _states(node, role):
    st = {}
    for k in ("checked", "pressed", "selected", "expanded", "focused"):
        if _get(node, NS_STATE, k, "") == "true":
            st[k] = True
    if role in CHECKABLE and "checked" not in st:
        st["checked"] = False
    return st


def _state_str(st):
    parts = []
    if "checked" in st:
        parts.append("checked:" + ("true" if st["checked"] else "false"))
    for k in ("pressed", "selected", "expanded", "focused"):
        if st.get(k):
            parts.append(k)
    return ",".join(parts)


def _readable(node):
    """Does this node itself carry text an agent could read?"""
    name = node.get("name", "") or ""
    text = (node.text or "").strip()
    value = _get(node, NS_VALUE, "value", "") or _get(node, NS_VALUE, "current", "")
    return bool(name.strip() or text or str(value).strip())


def distill(xml_string, vw=1920, vh=1080):
    root = ET.fromstring(xml_string)
    records, suspects, inconsistents = [], [], []
    seen_lines = set()          # exact-duplicate suppression
    seen_suspect_rects = set()
    seen_inconsistent = set()
    consumed = set()            # text nodes promoted into a parent's label
    offscreen_skipped = [0]
    BIG = 0.6 * vw * vh         # background layers: no text emission, no
                                # suspects (guard KNOWN LIMIT 2: area dilution)

    parent_of = {id(root): None}
    for p in root.iter():
        for c in p:
            parent_of[id(c)] = p

    # Pass 1: does each subtree expose ANY readable content? (for suspects)
    subtree_readable = {}

    def mark(node):
        r = _readable(node)
        for child in node:
            r = mark(child) or r
        subtree_readable[id(node)] = r
        return r

    mark(root)

    def emit(rec):
        if rec["line"] not in seen_lines:
            seen_lines.add(rec["line"])
            records.append(rec)

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

    def check_declared_count(node, name, text):
        m = COUNT_RE.search(name) or COUNT_RE.search(text)
        if not m or int(m.group(1)) == 0:
            return
        # Scope = the container the count is ABOUT, not the label's immediate
        # parent (often a wrapper holding only the label and its twin): walk
        # up until the ancestor is clearly bigger than the label itself.
        nx, ny, nw, nh = _coords(node)
        label_area = max(1, nw * nh)
        scope = node
        while True:
            parent = parent_of.get(id(scope))
            if parent is None:
                break
            scope = parent
            px, py, pw, ph = _coords(scope)
            if pw * ph >= 4 * label_area:
                break
        decl = m.group(0).strip().lower()
        exposed = 0
        for n in scope.iter():
            if n is node:
                continue
            if n.tag in ITEM_ROLES:
                exposed += 1
                continue
            t = ((n.get("name", "") or "").strip()
                 or (n.text or "").strip()).lower()
            if t and t != decl:          # the twin label is not a result row
                exposed += 1
        if exposed == 0:
            x, y, w, h = _coords(scope)
            if w <= 0 or h <= 0:
                x, y, w, h = _coords(node)
            key = (x, y, w, h, decl)
            if key in seen_inconsistent:
                return              # label/static twins declare it twice
            seen_inconsistent.add(key)
            inconsistents.append({
                "declared": int(m.group(1)), "unit": m.group(2).lower(),
                "declaring_text": m.group(0), "rect": [x, y, w, h]})

    def build(node, pos):
        """Build the record for one renderable node, or None."""
        role = node.tag
        x, y, w, h = _coords(node)
        big = w * h >= BIG
        box = f"{x},{y},{w},{h}"
        name = (node.get("name", "") or "").strip()
        text = (node.text or "").strip()
        value = str(_get(node, NS_VALUE, "value", "")
                    or _get(node, NS_VALUE, "current", "")).strip()
        off = " [offscreen]" if pos == "off" else ""
        pre = "[offscreen] " if pos == "off" else ""

        if pos == "on":
            check_declared_count(node, name, text)

        if role in OPAQUE:
            if pos == "off":
                return None      # not croppable from the viewport screenshot
            alt = name or _get(node, NS_ATTR, "description", "")
            return {"kind": "pixels", "role": role, "rect": [x, y, w, h],
                    "label": alt, "value": "", "states": {},
                    "line": f"[pixels] {role} {box}"
                            + (f" alt={alt}" if alt else "")}
        if role in INTERACTIVE and id(node) not in consumed:
            label = name or text or promote_label(node)
            if label:
                for child in node.iter():
                    if child is not node and (
                        (child.get("name", "") or "").strip() == label
                        or (child.text or "").strip() == label):
                        consumed.add(id(child))
            val = f' value={_q(value)}' if value else ""
            st = _states(node, role)
            sts = _state_str(st)
            stf = f" state={sts}" if sts else ""
            if not label and not val and (w < 4 or h < 4):
                return None      # 1px nameless slivers: separators
            if pos == "on" and not label and not val and not list(node) \
                    and not big and w * h >= SUSPECT_MIN_AREA:
                rect = (x, y, w, h)
                if rect not in seen_suspect_rects:
                    seen_suspect_rects.add(rect)
                    suspects.append({"label": f"nameless {role}",
                                     "rect": [x, y, w, h],
                                     "hasReadableContent": False})
            return {"kind": "offscreen" if pos == "off" else "element",
                    "role": role, "rect": [x, y, w, h], "label": label,
                    "value": value, "states": st,
                    "line": f"{pre}{role} {box}"
                            + (f" {_q(label)}" if label else "") + val + stf}
        if (role in TEXTUAL or text or name) and not big:
            t = text or name
            if t and id(node) not in consumed:
                return {"kind": "offscreen" if pos == "off" else "text",
                        "role": role, "rect": [x, y, w, h], "label": t,
                        "value": "", "states": {},
                        "line": f"{pre}text {box} {_q(t)}"}
            return None
        # nameless structural node: candidate silent blind spot when its
        # WHOLE subtree is mute and it is big enough to hide content
        if pos == "on" and not subtree_readable[id(node)] and not list(node) \
                and not big and w * h >= SUSPECT_MIN_AREA:
            rect = (x, y, w, h)
            if rect not in seen_suspect_rects:
                seen_suspect_rects.add(rect)
                suspects.append({"label": f"mute {role} (kids=0)",
                                 "rect": [x, y, w, h],
                                 "hasReadableContent": False})
        return None

    def walk(node):
        pos = _position(node, vw, vh)
        if pos is not None:
            if pos == "off" and node.tag not in INTERACTIVE \
                    and node.tag not in TEXTUAL and not (node.text or "").strip():
                pass             # offscreen structural noise: skip silently-
                                 # eligible roles only; content roles kept
            else:
                rec = build(node, pos)
                if rec is not None:
                    if rec["kind"] == "offscreen":
                        n_off = sum(1 for r in records
                                    if r["kind"] == "offscreen")
                        if n_off >= OFFSCREEN_CAP:
                            offscreen_skipped[0] += 1
                            rec = None
                    if rec is not None:
                        emit(rec)
        for child in node:
            walk(child)

    walk(root)
    if offscreen_skipped[0]:
        # no silent caps: overflow is declared in the view itself
        records.append({"kind": "note", "role": "note", "rect": [0, 0, 0, 0],
                        "label": "", "value": "", "states": {},
                        "line": f"[offscreen] +{offscreen_skipped[0]} more "
                                "lines truncated (scroll to reveal)"})
    return records, suspects, inconsistents


def render(records):
    """Debug/CLI rendering without ids (the driver assigns ids)."""
    return "\n".join(r["line"] for r in records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree_xml")
    ap.add_argument("--viewport", default="1920x1080")
    ap.add_argument("--suspects-out")
    args = ap.parse_args()
    vw, vh = (int(v) for v in args.viewport.split("x"))
    xml_string = open(args.tree_xml, encoding="utf-8").read()
    records, suspects, inconsistents = distill(xml_string, vw, vh)
    if args.suspects_out:
        json.dump(suspects, open(args.suspects_out, "w"), indent=1)
    sys.stdout.write(render(records) + "\n")
    if inconsistents:
        sys.stderr.write("self-inconsistent candidates: "
                         + json.dumps(inconsistents) + "\n")


if __name__ == "__main__":
    main()
