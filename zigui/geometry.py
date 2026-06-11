"""基础几何工具：向量运算、曲线采样、骨架→轮廓（ribbon）展开。

坐标系为字体单位坐标（y 轴向上，em = 1000）。
所有轮廓最终统一为顺时针方向，配合非零环绕填充规则，
重叠的笔画轮廓在渲染时自然合并，无需做多边形布尔运算。
"""

import math


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, k):
    return (a[0] * k, a[1] * k)


def length(a):
    return math.hypot(a[0], a[1])


def normalize(a):
    l = length(a) or 1.0
    return (a[0] / l, a[1] / l)


def left_normal(d):
    return (-d[1], d[0])


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def cubic_point(p0, p1, p2, p3, t):
    mt = 1.0 - t
    a = mt * mt * mt
    b = 3 * mt * mt * t
    c = 3 * mt * t * t
    d = t * t * t
    return (
        a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
        a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
    )


def sample_cubic(p0, p1, p2, p3, n=32):
    return [cubic_point(p0, p1, p2, p3, i / n) for i in range(n + 1)]


def sample_line(p0, p1, n=8):
    return [lerp(p0, p1, i / n) for i in range(n + 1)]


def ribbon(points, width_at):
    """沿骨架采样点向两侧偏移生成闭合轮廓。

    width_at(t) 返回 (左侧半宽, 右侧半宽)，t ∈ [0,1]，
    左/右以骨架前进方向为参照。两侧可不对称（如捺的上缘收锋）。
    """
    n = len(points) - 1
    left = []
    right = []
    for i, p in enumerate(points):
        if i == 0:
            d = normalize(sub(points[1], points[0]))
        elif i == n:
            d = normalize(sub(points[n], points[n - 1]))
        else:
            d = normalize(
                add(
                    normalize(sub(points[i], points[i - 1])),
                    normalize(sub(points[i + 1], points[i])),
                )
            )
        nm = left_normal(d)
        wl, wr = width_at(i / n)
        left.append(add(p, mul(nm, wl)))
        right.append(sub(p, mul(nm, wr)))
    return left + right[::-1]


def signed_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def ensure_cw(pts):
    """y 轴向上坐标系中，顺时针即有向面积为负。"""
    return pts if signed_area(pts) < 0 else list(reversed(pts))
