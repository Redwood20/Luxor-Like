import random
import math

# Ensure your _ctx has this key somewhere in initialization:
# _ctx["current_point"] = None


def move(p) -> None:
    """Luxor-like move(currentpoint). Stores current point for subsequent ops."""
    _require_ctx()
    _ctx["current_point"] = p


def randomhue() -> None:
    """Set a random RGB hue."""
    _require_ctx()
    sethue((random.random(), random.random(), random.random()))


def label_angle(text: str, angle: float, pos, offset: float = 15, fontsize: int = 16) -> None:
    """
    Luxor-ish: label(text, angle, pos; offset=?)
    We place text at `pos + offset * (cos(angle), sin(angle))`.
    (No text rotation; just position offset like many Luxor examples.)
    """
    _require_ctx()
    dx = offset * math.cos(angle)
    dy = offset * math.sin(angle)
    label(text, "C", (pos[0] + dx, pos[1] + dy), fontsize=fontsize)


def arc2r(center, p_from, p_to, stroke: bool = True) -> None:
    """
    Draw an arc centered at `center` (typically O) that goes from p_from to p_to at radius |p_from-center|.
    Uses the minor CCW arc by default (good match for many Luxor uses).

    center: O or (x,y) in Luxor-like coordinates (origin at canvas center, y up via negatives)
    p_from/p_to: (x,y) relative to center O
    """
    _require_ctx()

    if center == "O":
        cx0, cy0 = 0.0, 0.0
        cx, cy = _ctx["width"] / 2, _ctx["height"] / 2
    else:
        cx0, cy0 = center
        cx, cy = _ctx["width"] / 2 + cx0, _ctx["height"] / 2 + cy0

    fx, fy = p_from[0] - cx0, p_from[1] - cy0
    tx, ty = p_to[0] - cx0, p_to[1] - cy0

    r = math.hypot(fx, fy)
    a1 = math.atan2(fy, fx)
    a2 = math.atan2(ty, tx)

    # Normalize to CCW minor-ish arc (ensure a2 is ahead of a1)
    da = a2 - a1
    while da <= 0:
        da += 2 * math.pi
    # If it's the long way around, flip direction by drawing the other CCW segment
    if da > math.pi:
        a1, a2 = a2, a1
        da = a2 - a1
        while da <= 0:
            da += 2 * math.pi

    if _ctx["backend"] == "cairo":
        ctx = _ctx["ctx"]
        ctx.save()
        ctx.new_path()
        ctx.arc(cx, cy, r, a1, a2)
        ctx.set_dash(_ctx["dash"] or [])
        if stroke:
            ctx.set_line_width(2)
            ctx.stroke()
        ctx.restore()
    else:
        # PIL: draw.arc uses degrees; bbox is in image coords
        draw = _ctx["ctx"]
        col = tuple(int(255 * c) for c in _ctx["current_color"])
        box = [cx - r, cy - r, cx + r, cy + r]
        start = math.degrees(a1)
        end = math.degrees(a2)
        draw.arc(box, start=start, end=end, fill=col, width=2)
