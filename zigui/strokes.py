"""笔画工厂：根据风格参数把笔画骨架展开为轮廓。

每个方法对应一种笔画（横、竖、撇、捺、点、提、折、钩及复合笔画），
输入为骨架关键坐标，输出为若干闭合轮廓（点列表）。
风格差异（线宽对比、顿笔、拐角顿角、收锋锥度等）全部来自参数文件，
笔画骨架本身与风格无关——这正是"一套骨架、多套字体"的核心。
"""

from .geometry import ensure_cw, lerp, ribbon, sample_cubic, sample_line


class Strokes:
    def __init__(self, style):
        s = style["stroke"]
        self.hw = s["h_width"]          # 横画线宽
        self.vw = s["v_width"]          # 竖画线宽
        self.tilt = s.get("heng_tilt", 0)      # 横画右端抬升量
        self.cap = s.get("cap", "flat")        # 起收笔风格: flat | dun
        self.dun = s.get("dun_size", 1.4)      # 顿角尺寸（相对横宽）
        self.corner = s.get("corner", "miter")  # 折角风格: miter | bump
        self.pie_tip = s.get("pie_tip", 0.3)   # 撇收锋处宽度比
        self.na_peak = s.get("na_peak", 1.5)   # 捺最宽处相对竖宽
        self.hook_len = s.get("hook_len", 105)  # 钩长

    # ---- 基本笔画 ----

    def heng(self, x0, y, x1, end_cap=True, start_cap=True):
        """横。宋体类：左端斜切起笔，右端三角顿角收笔。"""
        p0, p1 = (x0, y), (x1, y + self.tilt)
        pts = sample_line(p0, p1, 8)
        h = self.hw / 2
        contours = [ribbon(pts, lambda t: (h, h))]
        if self.cap == "dun":
            d = self.hw * self.dun
            if start_cap:
                contours.append([
                    (x0 - d * 0.25, y + h + d * 0.45),
                    (x0 + d * 0.9, y + h * 0.4),
                    (x0 + d * 0.9, y - h),
                    (x0 - d * 0.1, y - h),
                ])
            if end_cap:
                ex, ey = p1
                contours.append([
                    (ex - d * 1.2, ey + h),
                    (ex + d * 0.1, ey + d * 0.95),
                    (ex + d * 0.5, ey + h * 0.2),
                    (ex + d * 0.15, ey - h - d * 0.2),
                    (ex - d * 1.2, ey - h),
                ])
        return contours

    def shu(self, x, y0, y1, top_cap=True, bottom="chui"):
        """竖。y0 为上端，y1 为下端。bottom: chui(垂露) | flat。"""
        pts = sample_line((x, y0), (x, y1), 8)
        v = self.vw / 2
        contours = [ribbon(pts, lambda t: (v, v))]
        if self.cap == "dun":
            d = self.vw * 0.8
            if top_cap:
                contours.append([
                    (x - v - d * 0.45, y0 + d * 0.75),
                    (x + v, y0 + d * 0.3),
                    (x + v, y0 - d * 0.2),
                    (x - v, y0 - d * 0.2),
                ])
            if bottom == "chui":
                contours.append([
                    (x - v, y1 + 2),
                    (x + v, y1 + 2),
                    (x + v * 0.1, y1 - self.vw * 0.6),
                ])
        return contours

    def pie(self, p0, p3, bend=1.0):
        """撇：起笔重，先竖后弯，收锋出尖。p0 起点（上），p3 末端（左下）。"""
        w = p0[0] - p3[0]
        hgt = p0[1] - p3[1]
        c1 = (p0[0] - 0.04 * w * bend, p0[1] - 0.42 * hgt)
        c2 = (p0[0] - 0.38 * w * bend, p0[1] - 0.82 * hgt)
        pts = sample_cubic(p0, c1, c2, p3, 36)
        v = self.vw / 2
        tip = self.pie_tip

        def width(t):
            k = v * (tip + (1 - tip) * (1 - t) ** 1.35)
            return (k, k)

        return [ribbon(pts, width)]

    def na(self, p0, p3):
        """捺：入笔轻，渐行渐重，捺脚铺开后收锋。上缘先于下缘收束。"""
        c1 = (lerp(p0, p3, 0.35)[0], lerp(p0, p3, 0.35)[1] - 28)
        c2 = (lerp(p0, p3, 0.72)[0], lerp(p0, p3, 0.72)[1] - 22)
        pts = sample_cubic(p0, c1, c2, p3, 36)
        peak = self.vw * self.na_peak / 2

        def width(t):
            if t < 0.78:
                k = t / 0.78
                upper = peak * (0.16 + 0.84 * k**1.1)
                lower = peak * (0.10 + 0.55 * k)
            else:
                k = (t - 0.78) / 0.22
                upper = peak * (1 - k**0.8)        # 上缘快速收锋
                lower = peak * 0.65 * (1 - k * 0.7)  # 下缘铺出捺脚
            return (max(upper, 1.0), max(lower, 1.0))

        return [ribbon(pts, width)]

    def dian(self, p0, p3):
        """点：短促入笔、腹部饱满、向行笔方向收驻。"""
        c1 = lerp(p0, p3, 0.3)
        c2 = lerp(p0, p3, 0.7)
        pts = sample_cubic(p0, (c1[0] + 8, c1[1]), (c2[0] + 6, c2[1]), p3, 20)
        v = self.vw / 2

        def width(t):
            k = v * (0.2 + 0.75 * t) if t < 0.72 else v * (0.74 - 0.3 * (t - 0.72) / 0.28)
            return (k, k)

        return [ribbon(pts, width)]

    def ti(self, p0, p3):
        """提：起笔重按，向右上挑出收锋。p0 为左下起点。"""
        c1 = lerp(p0, p3, 0.35)
        c2 = lerp(p0, p3, 0.7)
        pts = sample_cubic(p0, (c1[0], c1[1] - 10), (c2[0], c2[1] - 6), p3, 24)
        v = self.vw / 2
        tip = self.pie_tip

        def width(t):
            k = v * (tip + (1 - tip) * (1 - t) ** 1.2)
            return (k, k)

        return [ribbon(pts, width)]

    # ---- 钩与复合笔画 ----

    def _hook(self, bx, by, direction="left"):
        """钩：自竖画末端向左上方（或竖弯末端向正上方）挑出的三角。"""
        v = self.vw / 2
        L = self.hook_len
        if direction == "left":
            tip = (bx - L * 0.95, by + L * 0.45)
            return [[
                (bx + v, by + self.vw * 0.85),
                (bx + v * 0.6, by - v * 0.35),
                tip,
            ]]
        else:  # up，用于竖弯钩
            tip = (bx + L * 0.25, by + L * 0.95)
            return [[
                (bx - self.vw * 0.85, by - v),
                (bx + v * 0.35, by - v * 0.6),
                tip,
            ]]

    def shugou(self, x, y0, y1):
        """竖钩。"""
        return self.shu(x, y0, y1, bottom="flat") + self._hook(x, y1)

    def hengzhe(self, x0, y, x1, y1, gou=False, zhe_tilt=0):
        """横折（可带钩）：横 + 折角 + 竖。zhe_tilt 为竖段底部向左收的量。"""
        contours = self.heng(x0, y, x1, end_cap=False)
        top = y + self.tilt
        v = self.vw / 2
        bx = x1 - zhe_tilt
        pts = sample_line((x1, top + self.hw / 2), (bx, y1), 8)
        contours.append(ribbon(pts, lambda t: (v, v)))
        if self.corner == "bump":
            d = self.vw * 0.85
            contours.append([
                (x1 - self.vw, top + self.hw / 2),
                (x1 + v + d * 0.25, top + d * 0.8),
                (x1 + v + d * 0.35, top - self.hw),
                (x1 - self.vw, top - self.hw),
            ])
        else:
            contours.append([
                (x1 - self.vw, top + self.hw / 2),
                (x1 + v, top + self.hw / 2),
                (x1 + v, top - self.hw),
                (x1 - self.vw, top - self.hw),
            ])
        if gou:
            contours += self._hook(bx, y1)
        return contours

    def hengpie(self, x0, y, x1, p3):
        """横撇：短横接撇。"""
        return self.heng(x0, y, x1, end_cap=False) + self.pie((x1, y), p3, bend=0.7)

    def shuwangou(self, x, y0, y1, x1):
        """竖弯钩：竖 + 圆弯 + 底横 + 上挑钩。"""
        v = self.vw / 2
        bend_r = min(120, (x1 - x) * 0.35)
        pts = sample_line((x, y0), (x, y1 + bend_r), 6)
        pts += sample_cubic(
            (x, y1 + bend_r), (x, y1 + bend_r * 0.3),
            (x + bend_r * 0.7, y1), (x + bend_r, y1), 12,
        )[1:]
        pts += sample_line((x + bend_r, y1), (x1, y1), 6)[1:]

        def width(t):
            k = v if t < 0.6 else v * (1 + 0.12 * (t - 0.6) / 0.4)
            return (k, k)

        return [ribbon(pts, width)] + self._hook(x1, y1, direction="up")


def build_glyph_contours(strokes, specs):
    """按字形定义（笔画规格列表）生成全部轮廓，统一为顺时针方向。"""
    contours = []
    for spec in specs:
        method = getattr(strokes, spec[0])
        contours += method(*spec[1:])
    return [ensure_cw(c) for c in contours]
