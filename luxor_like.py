# luxor_like.py
"""
Luxor-inspired drawing API (PNG) with Cairo preferred and Pillow fallback.

Coordinate system:
- Use "O" as the origin at canvas center.
- Points passed as (x, y) are relative to O.
- +y is upward in your math; we convert internally to screen coords where +y is downward.
"""

from __future__ import annotations

from contextlib import contextmanager
import math
import random
from typing import Iterable, Optional, Tuple, Union, List

try:
    import cairo  # type: ignore
    _HAS_CAIRO = True
except Exception:
    _HAS_CAIRO = False

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

try:
    from matplotlib.colors import to_rgb  # type: ignore
    _HAS_MPL_COLORS = True
except Exception:
    _HAS_MPL_COLORS = False


Point = Tuple[float, float]
Color = Union[str, Tuple[float, float, float], Tuple[int, int, int]]

_SIMPLE_COLORS = {
    "black": (0.0, 0.0, 0.0),
    "white": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 1.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "darkblue": (0.06, 0.06, 0.5),
    "navy": (0.0, 0.0, 0.5),
    "yellow": (1.0, 1.0, 0.0),
    "gray": (0.5, 0.5, 0.5),
}

_ctx = {
    "backend": None,          # "cairo" | "pil" | None
    "surface": None,          # cairo.ImageSurface | None
    "ctx": None,              # cairo.Context | PIL.ImageDraw.Draw | None
    "width": 0,
    "height": 0,
    "current_color": (0.0, 0.0, 0.0),
    "alpha": 1.0,
    "dash": None,             # None | tuple
    "line_width": 2.0,
    "pil_image": None,        # PIL.Image | None
    "current_point": None,    # for move()
}


def _require_ctx() -> None:
    if _ctx["backend"] is None or _ctx["ctx"] is None:
        raise RuntimeError("Drawing commands must be used inside `with png(...):`")


def _to_canvas_xy(p: Point) -> Point:
    x0 = _ctx["width"] / 2
    y0 = _ctx["height"] / 2
    return (x0 + p[0], y0 + p[1])


def _parse_color(col: Optional[Color]) -> Tuple[float, float, float]:
    if col is None:
        return (0.0, 0.0, 0.0)

    if isinstance(col, (tuple, list)):
        vals = tuple(col)[:3]
        if max(vals) > 1:
            return (vals[0] / 255.0, vals[1] / 255.0, vals[2] / 255.0)
        return (float(vals[0]), float(vals[1]), float(vals[2]))

    s = str(col).strip()
    if _HAS_MPL_COLORS:
        try:
            r, g, b = to_rgb(s)
            return (float(r), float(g), float(b))
        except Exception:
            pass

    key = s.lower()
    if key in _SIMPLE_COLORS:
        return _SIMPLE_COLORS[key]

    if key.startswith("#") and len(key) in (4, 7):
        if len(key) == 7:
            r = int(key[1:3], 16) / 255.0
            g = int(key[3:5], 16) / 255.0
            b = int(key[5:7], 16) / 255.0
            return (r, g, b)
        r = int(key[1] * 2, 16) / 255.0
        g = int(key[2] * 2, 16) / 255.0
        b = int(key[3] * 2, 16) / 255.0
        return (r, g, b)

    return (0.0, 0.0, 0.0)


def _pil_rgba(rgb: Tuple[float, float, float], alpha: float) -> Tuple[int, int, int, int]:
    a = max(0, min(255, int(round(alpha * 255))))
    return (
        max(0, min(255, int(round(rgb[0] * 255)))),
        max(0, min(255, int(round(rgb[1] * 255)))),
        max(0, min(255, int(round(rgb[2] * 255)))),
        a,
    )


@contextmanager
def png(path: str, width: int, height: int):
    if _HAS_CAIRO:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        _ctx.update(
            backend="cairo",
            surface=surface,
            ctx=ctx,
            width=width,
            height=height,
            current_color=(0.0, 0.0, 0.0),
            alpha=1.0,
            dash=None,
            line_width=2.0,
            pil_image=None,
            current_point=None,
        )
    elif _HAS_PIL:
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        _ctx.update(
            backend="pil",
            surface=None,
            ctx=draw,
            width=width,
            height=height,
            current_color=(0.0, 0.0, 0.0),
            alpha=1.0,
            dash=None,
            line_width=2.0,
            pil_image=img,
            current_point=None,
        )
    else:
        raise RuntimeError("No supported backend. Install 'pycairo' or 'Pillow'.")

    try:
        yield
        if _ctx["backend"] == "cairo":
            _ctx["surface"].write_to_png(path)
        else:
            _ctx["pil_image"].save(path, "PNG")
    finally:
        _ctx.update(
            backend=None,
            surface=None,
            ctx=None,
            width=0,
            height=0,
            current_color=(0.0, 0.0, 0.0),
            alpha=1.0,
            dash=None,
            line_width=2.0,
            pil_image=None,
            current_point=None,
        )


def sethue(color: Color) -> None:
    _require_ctx()
    _ctx["current_color"] = _parse_color(color)
    if _ctx["backend"] == "cairo":
        r, g, b = _ctx["current_color"]
        _ctx["ctx"].set_source_rgba(r, g, b, _ctx["alpha"])


def setopacity(alpha: float) -> None:
    _require_ctx()
    _ctx["alpha"] = float(max(0.0, min(1.0, alpha)))
    if _ctx["backend"] == "cairo":
        r, g, b = _ctx["current_color"]
        _ctx["ctx"].set_source_rgba(r, g, b, _ctx["alpha"])


def setlinewidth(w: float) -> None:
    _require_ctx()
    _ctx["line_width"] = float(max(0.1, w))
    if _ctx["backend"] == "cairo":
        _ctx["ctx"].set_line_width(_ctx["line_width"])


def setdash(style: Optional[Union[str, Iterable[float]]]) -> None:
    _require_ctx()
    if style in (None, "solid"):
        dash = None
    elif style == "dot":
        dash = (1.5, 3.0)
    elif style == "dash":
        dash = (6.0, 4.0)
    elif isinstance(style, (tuple, list)):
        dash = tuple(float(x) for x in style)
    else:
        raise ValueError(f"Unknown dash style: {style!r}")

    _ctx["dash"] = dash
    if _ctx["backend"] == "cairo":
        _ctx["ctx"].set_dash(dash or [])


def background(color: Color) -> None:
    _require_ctx()
    rgb = _parse_color(color)
    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.set_source_rgb(*rgb)
        ctx.paint()
        ctx.restore()
        return

    fill = _pil_rgba(rgb, 1.0)
    _ctx["ctx"].rectangle([0, 0, _ctx["width"], _ctx["height"]], fill=fill)


def circle(center: Union[str, Point], radius: float, stroke: bool = False, fill: bool = False) -> None:
    _require_ctx()
    if center == "O":
        cx, cy = _ctx["width"] / 2, _ctx["height"] / 2
    else:
        cx, cy = _to_canvas_xy(center)

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.new_path()
        ctx.arc(cx, cy, radius, 0, 2 * math.pi)
        ctx.set_dash(_ctx["dash"] or [])
        ctx.set_line_width(_ctx["line_width"])
        r, g, b = _ctx["current_color"]
        ctx.set_source_rgba(r, g, b, _ctx["alpha"])
        if fill:
            ctx.fill_preserve()
        if stroke:
            ctx.stroke()
        ctx.restore()
        return

    draw = _ctx["ctx"]
    rgb = _ctx["current_color"]
    box = [cx - radius, cy - radius, cx + radius, cy + radius]
    if fill:
        draw.ellipse(box, fill=_pil_rgba(rgb, _ctx["alpha"]))
    if stroke:
        draw.ellipse(box, outline=_pil_rgba(rgb, _ctx["alpha"]), width=int(round(_ctx["line_width"])))


def rect(center: Union[str, Point], w: float, h: float, stroke: bool = False, fill: bool = False) -> None:
    _require_ctx()
    if center == "O":
        cx, cy = _ctx["width"] / 2, _ctx["height"] / 2
    else:
        cx, cy = _to_canvas_xy(center)

    x1, y1 = cx - w / 2, cy - h / 2
    x2, y2 = cx + w / 2, cy + h / 2

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.new_path()
        ctx.rectangle(x1, y1, w, h)
        ctx.set_dash(_ctx["dash"] or [])
        ctx.set_line_width(_ctx["line_width"])
        r, g, b = _ctx["current_color"]
        ctx.set_source_rgba(r, g, b, _ctx["alpha"])
        if fill:
            ctx.fill_preserve()
        if stroke:
            ctx.stroke()
        ctx.restore()
        return

    draw = _ctx["ctx"]
    rgba = _pil_rgba(_ctx["current_color"], _ctx["alpha"])
    if fill:
        draw.rectangle([x1, y1, x2, y2], fill=rgba)
    if stroke:
        draw.rectangle([x1, y1, x2, y2], outline=rgba, width=int(round(_ctx["line_width"])))


def line(p1: Point, p2: Point) -> None:
    _require_ctx()
    x1, y1 = _to_canvas_xy(p1)
    x2, y2 = _to_canvas_xy(p2)

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.new_path()
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.set_dash(_ctx["dash"] or [])
        ctx.set_line_width(_ctx["line_width"])
        r, g, b = _ctx["current_color"]
        ctx.set_source_rgba(r, g, b, _ctx["alpha"])
        ctx.stroke()
        ctx.restore()
        return

    draw = _ctx["ctx"]
    draw.line([(x1, y1), (x2, y2)], fill=_pil_rgba(_ctx["current_color"], _ctx["alpha"]), width=int(round(_ctx["line_width"])))


def bezier(p0: Point, p1: Point, p2: Point, p3: Point) -> None:
    _require_ctx()
    x0, y0 = _to_canvas_xy(p0)
    x1, y1 = _to_canvas_xy(p1)
    x2, y2 = _to_canvas_xy(p2)
    x3, y3 = _to_canvas_xy(p3)

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.new_path()
        ctx.move_to(x0, y0)
        ctx.curve_to(x1, y1, x2, y2, x3, y3)
        ctx.set_dash(_ctx["dash"] or [])
        ctx.set_line_width(_ctx["line_width"])
        r, g, b = _ctx["current_color"]
        ctx.set_source_rgba(r, g, b, _ctx["alpha"])
        ctx.stroke()
        ctx.restore()
        return

    # PIL fallback: polyline approximation
    steps = 60
    pts: List[Tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        bx = (
            mt**3 * x0
            + 3 * mt**2 * t * x1
            + 3 * mt * t**2 * x2
            + t**3 * x3
        )
        by = (
            mt**3 * y0
            + 3 * mt**2 * t * y1
            + 3 * mt * t**2 * y2
            + t**3 * y3
        )
        pts.append((bx, by))

    draw = _ctx["ctx"]
    draw.line(pts, fill=_pil_rgba(_ctx["current_color"], _ctx["alpha"]), width=int(round(_ctx["line_width"])))


def label(text: str, anchor: str, pos: Point, fontsize: int = 16) -> None:
    _require_ctx()
    x, y = _to_canvas_xy(pos)

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        r, g, b = _ctx["current_color"]
        ctx.set_source_rgba(r, g, b, _ctx["alpha"])
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(fontsize)
        xb, yb, w, h, xa, ya = ctx.text_extents(text)

        if anchor == "N":
            x -= w / 2
            y += h
        elif anchor == "S":
            x -= w / 2
        elif anchor == "E":
            x -= w
        elif anchor == "C":
            x -= w / 2
            y += h / 2

        ctx.move_to(x, y)
        ctx.show_text(text)
        ctx.restore()
        return

    draw = _ctx["ctx"]
    font = ImageFont.load_default()
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    if anchor == "N":
        x -= w / 2
        y -= h
    elif anchor == "S":
        x -= w / 2
    elif anchor == "E":
        x -= w
    elif anchor == "C":
        x -= w / 2
        y -= h / 2

    draw.text((x, y), text, fill=_pil_rgba(_ctx["current_color"], _ctx["alpha"]), font=font)


def label_angle( 
    text: str,
    angle: float,
    pos: Point, 
    offset: float = 15.0, 
    fontsize: int = 16, 
 ) -> None: 
    _require_ctx()
    dx = offset * math.cos(angle) 
    dy = offset * math.sin(angle) 
    label(text, "C", (pos[0] + dx, pos[1] + dy), fontsize=fontsize)


def randomhue() -> None:
    _require_ctx()
    sethue((random.random(), random.random(), random.random()))


def move(p: Point) -> None:
    _require_ctx()
    _ctx["current_point"] = p


def arc2r(center: Union[str, Point], p_from: Point, p_to: Point) -> None:
    """
    Circular arc around `center` from p_from to p_to (minor arc).
    """
    _require_ctx()

    c = (0.0, 0.0) if center == "O" else center
    fx, fy = (p_from[0] - c[0], p_from[1] - c[1])
    tx, ty = (p_to[0] - c[0], p_to[1] - c[1])

    r = math.hypot(fx, fy)
    a1 = math.atan2(fy, fx)
    a2 = math.atan2(ty, tx)

    da = a2 - a1
    while da <= 0:
        da += 2 * math.pi
    if da > math.pi:
        a1, a2 = a2, a1
        da = a2 - a1
        while da <= 0:
            da += 2 * math.pi

    cx, cy = _to_canvas_xy(c)

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.new_path()
        ctx.arc(cx, cy, r, a1, a2)
        ctx.set_dash(_ctx["dash"] or [])
        ctx.set_line_width(_ctx["line_width"])
        r0, g0, b0 = _ctx["current_color"]
        ctx.set_source_rgba(r0, g0, b0, _ctx["alpha"])
        ctx.stroke()
        ctx.restore()
        return

    draw = _ctx["ctx"]
    box = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(
        box,
        start=math.degrees(a1),
        end=math.degrees(a2),
        fill=_pil_rgba(_ctx["current_color"], _ctx["alpha"]),
        width=int(round(_ctx["line_width"])),
    )


O = "O"

__all__ = [
    "png",
    "background",
    "sethue",
    "setopacity",
    "setlinewidth",
    "setdash",
    "circle",
    "rect",
    "line",
    "bezier",
    "label",
    "label_angle",
    "randomhue",
    "move",
    "arc2r",
    "O",
]

