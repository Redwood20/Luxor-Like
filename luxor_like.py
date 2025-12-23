"""
Coordinates:
- "O" origin at canvas center.
- Points you pass (x, y) are relative to center, with +y upward (so we map to image y downward internally).

Backends:
- Prefers pycairo (if installed).
- Falls back to Pillow (PIL).
"""

from __future__ import annotations

from contextlib import contextmanager
import math
import random
from typing import Iterable, Optional, Tuple, Union

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
    "backend": None,         # "cairo" | "pil" | None
    "surface": None,         # cairo.ImageSurface | None
    "ctx": None,             # cairo.Context | PIL.ImageDraw.Draw | None
    "width": 0,
    "height": 0,
    "current_color": (0.0, 0.0, 0.0),
    "dash": None,            # None or tuple
    "pil_image": None,       # PIL.Image | None
    "current_point": None,   # for move()
}


def _require_ctx() -> None:
    if _ctx["backend"] is None or _ctx["ctx"] is None:
        raise RuntimeError("Drawing commands must be used inside `with png(...):`")


def _to_canvas_xy(p: Point) -> Point:
    """Convert Luxor-like point (origin at center) to canvas pixel coords (origin at top-left)."""
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
            dash=None,
            pil_image=None,
            current_point=None,
        )
    elif _HAS_PIL:
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        _ctx.update(
            backend="pil",
            surface=None,
            ctx=draw,
            width=width,
            height=height,
            current_color=(0.0, 0.0, 0.0),
            dash=None,
            pil_image=img,
            current_point=None,
        )
    else:
        raise RuntimeError("No supported drawing backend. Install 'pycairo' or 'Pillow'.")

    try:
        yield
        if _ctx["backend"] == "cairo":
            _ctx["surface"].write_to_png(path)
        else:
            _ctx["pil_image"].convert("RGB").save(path, "PNG")
    finally:
        _ctx.update(
            backend=None,
            surface=None,
            ctx=None,
            width=0,
            height=0,
            current_color=(0.0, 0.0, 0.0),
            dash=None,
            pil_image=None,
            current_point=None,
        )


def sethue(color: Color) -> None:
    _require_ctx()
    rgb = _parse_color(color)
    _ctx["current_color"] = rgb
    if _ctx["backend"] == "cairo":
        _ctx["ctx"].set_source_rgb(*rgb)


def background(color: Color) -> None:
    _require_ctx()
    rgb = _parse_color(color)
    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.set_source_rgb(*rgb)
        ctx.paint()
        ctx.restore()
    else:
        col = tuple(int(255 * c) for c in rgb)
        _ctx["ctx"].rectangle([0, 0, _ctx["width"], _ctx["height"]], fill=col)


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
        if fill:
            ctx.fill_preserve()
        if stroke:
            ctx.set_line_width(2.0)
            ctx.stroke()
        ctx.restore()
    else:
        draw = _ctx["ctx"]
        col = tuple(int(255 * c) for c in _ctx["current_color"])
        box = [cx - radius, cy - radius, cx + radius, cy + radius]
        if fill:
            draw.ellipse(box, fill=col)
        if stroke:
            draw.ellipse(box, outline=col, width=2)


def label(text: str, anchor: str, pos: Point, fontsize: int = 16) -> None:
    """
    anchor: "N", "S", "E", "W", "C" (approx)
    pos: Luxor-like (x,y) relative to O.
    """
    _require_ctx()
    x, y = _to_canvas_xy(pos)

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.set_source_rgb(*_ctx["current_color"])
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
        # "W" falls through

        ctx.move_to(x, y)
        ctx.show_text(text)
        ctx.restore()
        return

    # PIL
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

    col = tuple(int(255 * c) for c in _ctx["current_color"])
    draw.text((x, y), text, fill=col, font=font)


def label_angle(text: str, angle: float, pos: Point, offset: float = 15.0, fontsize: int = 16) -> None:
    """
    Luxor-ish: label(text, angle, pos; offset=15)
    Places the label at pos + offset*(cos(angle), sin(angle)).
    (No text rotation; only positional offset.)
    """
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


def arc2r(center: Union[str, Point], p_from: Point, p_to: Point, stroke: bool = True) -> None:
    """
    Draw an arc around `center` (often O) from p_from to p_to.
    - center: "O" or (x,y) Luxor-like.
    - p_from, p_to: Luxor-like points.
    Uses the shorter arc (minor arc) by default.
    """
    _require_ctx()

    if center == "O":
        c = (0.0, 0.0)
    else:
        c = center

    fx, fy = (p_from[0] - c[0], p_from[1] - c[1])
    tx, ty = (p_to[0] - c[0], p_to[1] - c[1])

    r = math.hypot(fx, fy)
    a1 = math.atan2(fy, fx)
    a2 = math.atan2(ty, tx)

    # Normalize CCW delta into (0, 2pi]
    da = a2 - a1
    while da <= 0:
        da += 2 * math.pi

    # Choose minor arc
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
        if stroke:
            ctx.set_line_width(2.0)
            ctx.stroke()
        ctx.restore()
        return

    # PIL: arc uses degrees, bounding box in canvas coords
    draw = _ctx["ctx"]
    col = tuple(int(255 * c_) for c_ in _ctx["current_color"])
    box = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(box, start=math.degrees(a1), end=math.degrees(a2), fill=col, width=2)


O = "O"

__all__ = [
    "png",
    "background",
    "sethue",
    "setdash",
    "circle",
    "label",
    "label_angle",
    "randomhue",
    "move",
    "arc2r",
    "O",
]



