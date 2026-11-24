"""Compute output->source corner maps for the simulated camera angles.

Each angle is a single projective warp: punch-in scale, offset (re-framing),
rotation and a light keystone ("looking down" perspective). Returns the 4
source-space points that the output corners (TL, TR, BL, BR) sample from,
for ffmpeg's perspective filter (sense=source).
"""
import math

W, H = 1920, 1080


def corners(scale, rot_deg, cx, cy, keystone):
    th = math.radians(rot_deg)
    c, s = math.cos(th), math.sin(th)
    pts = []
    for (u, v) in [(0, 0), (W, 0), (0, H), (W, H)]:
        x = (u - W / 2) / scale
        y = (v - H / 2) / scale
        # keystone: widen the sampled region at the top -> top edge appears
        # smaller in the output = mild high-angle (looking down) perspective.
        k = 1 + keystone * (-(v - H / 2) / (H / 2))
        x *= k
        xr = c * x - s * y
        yr = s * x + c * y
        pts.append((cx + xr, cy + yr))
    return pts


def inside(pts, m=1.0):
    return all(m <= x <= W - m and m <= y <= H - m for x, y in pts)


def best(scale, rot, keystone, side, cy):
    """Push the source centre as far as allowed so the speaker shifts to one side."""
    rng = range(W // 2, W) if side == "left" else range(W // 2, 0, -1)
    good = None
    for cx in rng:
        if inside(corners(scale, rot, cx, cy, keystone)):
            good = cx
        else:
            break
    return good


ANGLES = {
    # angle 1: camera above-right -> speaker in left third, frame tilted
    "a1": dict(scale=1.25, rot=-3.5, keystone=0.02, side="left", cy=500),
    # angle 2: mirror
    "a2": dict(scale=1.25, rot=3.5, keystone=0.02, side="right", cy=500),
}


def spec(name):
    a = ANGLES[name]
    cx = best(a["scale"], a["rot"], a["keystone"], a["side"], a["cy"])
    pts = corners(a["scale"], a["rot"], cx, a["cy"], a["keystone"])
    return cx, pts


def src_to_out(name, sx, sy):
    """Approximate inverse (ignoring keystone) for placing graphics."""
    a = ANGLES[name]
    cx, _ = spec(name)
    th = math.radians(-a["rot"])
    dx, dy = sx - cx, sy - a["cy"]
    xr = math.cos(th) * dx - math.sin(th) * dy
    yr = math.sin(th) * dx + math.cos(th) * dy
    return W / 2 + xr * a["scale"], H / 2 + yr * a["scale"]


if __name__ == "__main__":
    for n in ANGLES:
        cx, pts = spec(n)
        print(n, "cx", cx, "face->", tuple(round(v) for v in src_to_out(n, 1020, 500)))
        print("  ", ":".join(f"{x:.2f}:{y:.2f}" for x, y in pts))
