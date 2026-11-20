import math


def _points(points):
    out = [(float(x), float(y)) for x, y in points]
    if len(out) < 2:
        raise ValueError("need at least two points")
    if any(not math.isfinite(v) for point in out for v in point):
        raise ValueError("coordinates must be finite")
    if not math.isfinite(math.hypot(max(x for x, _ in out) - min(x for x, _ in out),
                                    max(y for _, y in out) - min(y for _, y in out))):
        raise ValueError("coordinate range is too large")
    return out


def _cutoff(cutoff):
    if isinstance(cutoff, bool) or not isinstance(cutoff, int) or cutoff < 2:
        raise ValueError("cutoff must be an integer of at least 2")


def closest_pair_dc(points, cutoff=16, on_step=None):
    _cutoff(cutoff)
    px = sorted(_points(points))
    best_pair, best_d, _, _ = _rec(0, len(px), px, cutoff, on_step)
    return best_d, best_pair, px


def _rec(lo, hi, px, cutoff, on_step=None, depth=0):
    def emit(kind, **values):
        if on_step:
            on_step(dict(kind=kind, depth=depth, lo=lo, hi=hi, **values))
    n = hi - lo
    if n <= cutoff:
        emit("base", size=n)
        pair, d = _brute(px[lo:hi], lambda pair, distance, best: emit(
            "compare", pair=pair, distance=distance, best=best))
        emit("return", pair=pair, distance=d if pair else None)
        return pair, d, _by_y(px[lo:hi]), None

    mid = (lo + hi) // 2
    mid_x = px[mid][0]

    emit("split", mid_x=mid_x, left=mid-lo, right=hi-mid)
    lp, ld, ly, _ = _rec(lo, mid, px, cutoff, on_step, depth + 1)
    rp, rd, ry, _ = _rec(mid, hi, px, cutoff, on_step, depth + 1)
    emit("merge", left_distance=ld if lp else None, right_distance=rd if rp else None)

    pair, d = (lp, ld) if ld <= rd else (rp, rd)

    by_y = []
    i = j = 0
    while i < len(ly) and j < len(ry):
        if ly[i][1] <= ry[j][1]:
            by_y.append(ly[i])
            i += 1
        else:
            by_y.append(ry[j])
            j += 1
    by_y.extend(ly[i:])
    by_y.extend(ry[j:])

    dist = d
    strip = [p for p in by_y if abs(p[0] - mid_x) < dist]
    emit("strip", mid_x=mid_x, width=d, size=len(strip), pair=pair, distance=d)
    for k in range(len(strip)):
        m = k + 1
        while m < len(strip) and m <= k + 7:
            dy = strip[m][1] - strip[k][1]
            if dy >= d:
                break
            sq = math.hypot(strip[k][0] - strip[m][0], dy)
            emit("compare", pair=(strip[k], strip[m]), distance=sq, best=min(d, sq))
            if sq < d:
                d = sq
                pair = (strip[k], strip[m])
            m += 1

    emit("combine", pair=pair, distance=d)
    node = {"lo": lo, "hi": hi, "mid_x": mid_x, "pair": pair,
            "dist": d}
    return pair, d, by_y, node


def _brute(points, on_compare=None):
    best = math.inf
    pair = None
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            sq = math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1])
            if on_compare:
                on_compare((points[i], points[j]), sq, min(best, sq))
            if sq < best:
                best = sq
                pair = (points[i], points[j])
    return pair, best


def _by_y(points):
    return sorted(points, key=lambda p: p[1])


def closest_pair_display(points):
    p = _points(points)
    return min(p), p.index(min(p)), p


def closest_pair_brute(points):
    points = _points(points)
    pair, sq = _brute(points)
    return sq, pair


def trace(points, cutoff=16, max_depth=6):
    _cutoff(cutoff)
    px = sorted(_points(points))
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth must be a nonnegative integer")
    nodes = []

    def rec(lo, hi, depth):
        n = hi - lo
        node = {"id": len(nodes), "lo": lo, "hi": hi, "n": n,
                "depth": depth, "mid_x": None, "best": None}
        nodes.append(node)
        xs = [p[0] for p in px[lo:hi]]
        ys = [p[1] for p in px[lo:hi]]
        node["xmin"], node["xmax"] = min(xs), max(xs)
        node["ymin"], node["ymax"] = min(ys), max(ys)
        if n <= cutoff or depth >= max_depth:
            pair, d = _brute(px[lo:hi])
            node["best"] = pair
            node["dist"] = d if pair else None
            return
        mid = (lo + hi) // 2
        node["mid_x"] = px[mid][0]
        rec(lo, mid, depth + 1)
        rec(mid, hi, depth + 1)

    rec(0, len(px), 0)
    return px, nodes
