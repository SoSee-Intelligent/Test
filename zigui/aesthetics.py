"""字面美学度量：把"尺度"变成可计算的统计指标。

灰度（字面墨量）与重心（视觉中心）是排版质感的核心统计量：
整套字灰度均匀、重心稳定，版面才"平"。量化之后可以做两件事：

1. 自检：检查一套字内部的一致性，揪出过重/过轻/重心漂移的字；
2. 校准：统计开源授权字体（如 OFL 字体）的灰度/重心分布作为
   "尺度"参照——学习的是度量分布，不接触、不复制任何字形。
"""

from .fingerprint import GRID, FontShape


def glyph_metrics(bitmap):
    """单字位图 → (墨量占比, 重心x, 重心y)，重心为 0~1 归一化坐标。"""
    px = bitmap.load()
    total = 0
    sx = 0.0
    sy = 0.0
    for y in range(GRID):
        for x in range(GRID):
            if px[x, y]:
                total += 1
                sx += x
                sy += y
    if total == 0:
        return (0.0, 0.5, 0.5)
    return (total / (GRID * GRID), sx / total / GRID, 1.0 - sy / total / GRID)


def font_metrics(path):
    """整套字的美学度量报告。"""
    shape = FontShape(path)
    per_char = {}
    for code in sorted(shape.chars()):
        density, cx, cy = glyph_metrics(shape.bitmap(code))
        per_char[chr(code)] = {
            "ink": round(density, 4),
            "cx": round(cx, 3),
            "cy": round(cy, 3),
        }
    inks = [m["ink"] for m in per_char.values()]
    mean_ink = sum(inks) / len(inks) if inks else 0.0
    outliers = [
        ch for ch, m in per_char.items()
        if mean_ink and abs(m["ink"] - mean_ink) / mean_ink > 0.45
    ]
    return {
        "font": shape.path,
        "mean_ink": round(mean_ink, 4),
        "ink_range": [round(min(inks, default=0), 4), round(max(inks, default=0), 4)],
        "outliers": outliers,
        "per_char": per_char,
    }
