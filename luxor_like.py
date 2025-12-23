import random
import math


def move(p) -> None:
    _require_ctx()
    _ctx["current_point"] = p


def randomhue() -> None:
    _require_ctx()
    sethue((random.random(), random.random(), random.random()))


def label_angle(text: str, angle: float, pos, offset: float = 15, fontsize: int = 16) -> None:
    _require_ctx()
    dx = offset * math.cos(angle)
    dy = offset * math.sin(angle)
    label(text, "C", (pos[0] + dx, pos[1] + dy), fontsize=fontsize)


def arc2r(center, p_from, p_to, stroke: bool = True) -> None:

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

  
    da = a2 - a1
    while da <= 0:
        da += 2 * math.pi
        
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
        draw = _ctx["ctx"]
        col = tuple(int(255 * c) for c in _ctx["current_color"])
        box = [cx - r, cy - r, cx + r, cy + r]
        start = math.degrees(a1)
        end = math.degrees(a2)
        draw.arc(box, start=start, end=end, fill=col, width=2)

