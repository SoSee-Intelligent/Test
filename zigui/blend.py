"""风格混合器：两套风格参数插值出第三套——零绘制创作。

数值参数线性插值；离散参数（cap/corner 等）按插值比就近取整。
这是生态市场的最小创作单元：创作者不画一个字，
也能在参数空间里"调"出一套可确权的新字体。
"""


def blend_styles(a, b, t):
    sa, sb = a["stroke"], b["stroke"]
    stroke = {}
    for key in sorted(set(sa) | set(sb)):
        va, vb = sa.get(key), sb.get(key)
        if va is None or vb is None:
            stroke[key] = vb if va is None else va
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            stroke[key] = round(va + (vb - va) * t, 2)
        else:
            stroke[key] = va if t < 0.5 else vb
    pct = int(round(t * 100))
    return {
        "name": f"ZiGui Blend {pct}",
        "ps_name": f"ZiGuiBlend{pct}-Regular",
        "blend_of": [a["name"], b["name"], t],
        "stroke": stroke,
    }
