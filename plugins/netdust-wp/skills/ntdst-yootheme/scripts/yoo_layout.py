"""
yoo_layout — build YOOtheme layout JSON in Python with the props the builder itself writes.

    import yoo_layout as y
    page = y.wrap([
        y.section("H1 · Hero — tekst", [
            y.row([
                y.column([y.headline("Hallo", element="h1", style="h2"), y.text("<p>Intro</p>"),
                          y.button("Meer", "/meer/")], width_medium="1-2"),
                y.column([y.image("content/uploads/2026/09/x.jpg", 628, 500)], width_medium="1-2"),
            ], layout="1-2,1-2", column_gap="large", alignment="center"),
        ]),
    ], version="5.0.43")
    y.dump(page, "specs/pages/home.json")

Every constructor carries the defaults the builder stamps on a fresh element
(`image_position`, `position_sticky_breakpoint`, `title_breakpoint`, …) so a
hand-built layout round-trips through a builder save without churn, and `**props`
overrides or extends them. Lint the result with scripts/yoo-lint.php before writing.

Reusing sections:
    lib = y.library(".yoo-tools/page64.json")        # {name: section} from a page dump
    lib = y.library("all-templates.json")            # or the `yootheme` option's library
    hero = y.at(lib["H1 · Hero — tekst"], "0/1/0")   # child path: row 0 > column 1 > element 0
"""
from __future__ import annotations

import copy
import json
import pathlib

# --- node constructors -------------------------------------------------------

def node(type_, props=None, children=None, name=None, source=None):
    n = {"type": type_}
    if name:
        n["name"] = name
    if props is not None:
        n["props"] = props
    if children is not None:
        n["children"] = children
    if source is not None:
        n["source"] = source
    return n


def wrap(sections, version):
    """A page / template / widget root. `version` is mandatory — without it every
    element migration runs on save and rewrites props."""
    return {"type": "layout", "version": version, "children": sections}


def section(name, children, **p):
    return node("section", {"image_position": "center-center", "style": "default",
                            "title_breakpoint": "xl", "title_position": "top-left",
                            "title_rotation": "left", "vertical_align": "middle",
                            "width": "default", **p}, children, name=name)


def row(children, **p):
    """Give a multi-column row its `layout` ("1-2,1-2") AND every column its width_*;
    a lone column needs `alignment` or it fills the row."""
    return node("row", {"margin_top": "remove", **p}, children)


def column(children, **p):
    return node("column", {"image_position": "center-center",
                           "position_sticky_breakpoint": "m", **p}, children)


def fragment(children, **p):
    """The Sublayout: the only sanctioned way to nest a row inside a column."""
    return node("fragment", {**p}, children)


def headline(content, element="h2", style="h3", **p):
    return node("headline", {"content": content, "image_align": "left", "image_margin": "xsmall",
                             "margin_bottom": "default", "margin_top": "remove",
                             "title_element": element, "title_style": style, **p})


def text(content, **p):
    return node("text", {"column_breakpoint": "m", "content": content,
                         "margin_bottom": "remove", "margin_top": "remove", **p})


def image(path, width=None, height=None, **p):
    props = {"image": path, "image_svg_color": "emphasis", "margin_bottom": "remove",
             "margin_top": "remove", **p}
    if width:
        props["image_width"] = width
    if height:
        props["image_height"] = height
    return node("image", props)


def button(label, link, style="default", size="small", **p):
    return node("button", {"button_size": size, "grid_column_gap": "small", "grid_row_gap": "small",
                           "margin_bottom": "remove", "margin_top": "small", **p},
                [node("button_item", {"button_style": style, "dialog_layout": "modal",
                                      "dialog_offcanvas_flip": True, "icon_align": "left",
                                      "link": link, "content": label})])


def grid(items, **p):
    """Card grid. For a listing, bind the ITEM (see grid_item) and leave the grid unbound."""
    return node("grid", {"grid_column_gap": "medium", "grid_default": "1", "grid_medium": "3",
                         "grid_row_gap": "large", "image_align": "top", "link_style": "default",
                         "link_text": "", "margin_bottom": "remove", "margin_top": "remove",
                         "meta_align": "above-title", "meta_style": "text-meta",
                         "show_content": True, "show_image": True, "show_link": True,
                         "show_meta": True, "show_title": True, "title_element": "h3",
                         "title_style": "h4", **p}, items)


def grid_item(props=None, source=None, **p):
    return node("grid_item", {**(props or {}), **p}, source=source)


def bound_item(query, arguments=None, **fields):
    """One repeating grid_item bound to a list query: bound_item("verhalen.customVerhalen",
    {"limit": 6}, title="title", link="link", image="featuredImage.url")."""
    q = {"name": query}
    if arguments:
        q["arguments"] = arguments
    return node("grid_item", {}, source={"query": q, "props": {k: {"name": v} for k, v in fields.items()}})


def panel(**p):
    return node("panel", {"image_align": "top", "margin_bottom": "remove", "margin_top": "remove",
                          "show_content": True, "show_image": True, "show_link": True,
                          "show_meta": True, "show_title": True, "title_element": "h3", **p})


def accordion(items, **p):
    """items: [(title, html), …]. The rule-between-items look is the theme's default
    accordion (four variables), never CSS."""
    return node("accordion", {"collapsible": True, "margin_bottom": "remove", "margin_top": "remove",
                              "multiple": False, "show_image": False, "show_link": False, **p},
                [node("accordion_item", {"title": t, "content": c, "item_element": "div"}) for t, c in items])


def panel_slider(items, **p):
    """A marquee / logo wall: slider_width "" (auto) + slider_parallax; a grid cannot bleed."""
    return node("panel-slider", {"nav": "", "panel_match": False, "show_content": False,
                                 "show_image": True, "show_link": False, "show_meta": False,
                                 "show_title": False, "slidenav": "", "slider_finite": False,
                                 "slider_gap": "large", "slider_parallax": True,
                                 "slider_parallax_easing": "0", "slider_parallax_target": "!.uk-section",
                                 "slider_width": "", "margin_bottom": "remove", "margin_top": "remove", **p},
                items)


def slider_item(image_path, width=300, **p):
    return node("panel-slider_item", {"image": image_path, "image_width": width, **p})


# --- reading and addressing --------------------------------------------------

def library(path):
    """{name: section} from a page dump (`page get`), a template export, or the
    `yootheme` option's library. Every section is deep-copied on access via sec()."""
    data = json.loads(pathlib.Path(path).read_text())
    out = {}

    def take(layout):
        for s in layout.get("children", []):
            if s.get("name"):
                out[s["name"]] = s

    if isinstance(data, dict) and data.get("type") == "layout":
        take(data)
    elif isinstance(data, dict):
        for v in data.values():
            lay = v.get("layout") if isinstance(v, dict) else None
            if isinstance(lay, dict):
                take(lay)
            elif isinstance(v, dict) and v.get("type") == "layout":
                take(v)
    return out


def sec(lib, name):
    """A deep copy of a library section — a library insert is always a COPY."""
    return copy.deepcopy(lib[name])


def at(node_, path):
    """Child path: "0/1/0" = children[0].children[1].children[0]."""
    for step in [p for p in str(path).split("/") if p]:
        node_ = node_["children"][int(step.split(":")[0])]
    return node_


def dump(node_, path, indent=2):
    pathlib.Path(path).write_text(json.dumps(node_, ensure_ascii=False, indent=indent) + "\n")
    return path
