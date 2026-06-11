"""字体查重：图像级字形比对。

把任意字体文件（OTF/TTF）的字形压平、归一化栅格化到统一网格，
逐字计算 IoU（交并比）作为字形相似度的快速代理指标。

平台内生成的字体自带骨架与参数，后续可升级为笔画级精确比对
（骨架对齐 + 参数距离），比图像级灵敏得多——外部查重工具拿不到
骨架数据，这正是平台的数据优势。

栅格化采用"主方向轮廓为实体、反方向轮廓为镂空"的近似填充，
覆盖常见字体（外轮廓与内孔方向相反）及本引擎的同向交叠轮廓。
"""

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw

from .geometry import signed_area

GRID = 96      # 归一化网格边长（像素）
_STEPS = 14    # 曲线压平采样步数


class _FlattenPen(BasePen):
    """把字形轮廓（含二次/三次曲线、组件引用）压平为多边形点列。"""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.contours = []
        self._cur = None

    def _moveTo(self, pt):
        self._cur = [pt]

    def _lineTo(self, pt):
        self._cur.append(pt)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur[-1]
        for i in range(1, _STEPS + 1):
            t = i / _STEPS
            mt = 1 - t
            self._cur.append((
                mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
                mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1],
            ))

    def _qCurveToOne(self, p1, p2):
        p0 = self._cur[-1]
        for i in range(1, _STEPS + 1):
            t = i / _STEPS
            mt = 1 - t
            self._cur.append((
                mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
            ))

    def _closePath(self):
        if self._cur and len(self._cur) >= 3:
            self.contours.append(self._cur)
        self._cur = None

    def _endPath(self):
        self._closePath()


class FontShape:
    """任意字体文件的字形栅格化读取器。"""

    def __init__(self, path):
        self.path = str(path)
        self.font = TTFont(path)
        self.upm = self.font["head"].unitsPerEm
        if "OS/2" in self.font:
            self.top = self.font["OS/2"].sTypoAscender
            self.bottom = self.font["OS/2"].sTypoDescender
        else:
            self.top = self.font["hhea"].ascent
            self.bottom = self.font["hhea"].descent
        self.cmap = self.font.getBestCmap()
        self.glyph_set = self.font.getGlyphSet()

    def chars(self):
        return {c for c in self.cmap if c > 0x20}

    def bitmap(self, code):
        pen = _FlattenPen(self.glyph_set)
        self.glyph_set[self.cmap[code]].draw(pen)
        total = sum(signed_area(c) for c in pen.contours)
        img = Image.new("L", (GRID, GRID), 0)
        draw = ImageDraw.Draw(img)
        sx = GRID / self.upm
        sy = GRID / (self.top - self.bottom)
        passes = ([c for c in pen.contours if signed_area(c) * total >= 0],
                  [c for c in pen.contours if signed_area(c) * total < 0])
        for fill, contours in zip((255, 0), passes):
            for c in contours:
                draw.polygon([(x * sx, (self.top - y) * sy) for x, y in c], fill=fill)
        return img


def _count(img):
    return img.histogram()[255]


def glyph_iou(bitmap_a, bitmap_b):
    union = _count(ImageChops.lighter(bitmap_a, bitmap_b))
    if union == 0:
        return 0.0
    inter = _count(ImageChops.multiply(bitmap_a, bitmap_b))
    return inter / union


def verdict(mean_iou):
    if mean_iou >= 0.80:
        return "高风险：整体字形高度重合，建议人工复核并调整参数"
    if mean_iou >= 0.55:
        return "中风险：风格距离较近，建议抽样人工比对"
    return "低风险：字形差异显著"


def compare_fonts(path_a, path_b, chars=None):
    """比对两个字体文件的共同字符，返回查重报告 dict。"""
    a, b = FontShape(path_a), FontShape(path_b)
    common = sorted(a.chars() & b.chars())
    if chars:
        wanted = {ord(ch) for ch in chars}
        common = [c for c in common if c in wanted]
    per_char = {chr(c): round(glyph_iou(a.bitmap(c), b.bitmap(c)), 3) for c in common}
    mean = sum(per_char.values()) / len(per_char) if per_char else 0.0
    return {
        "font_a": a.path,
        "font_b": b.path,
        "glyphs_compared": len(per_char),
        "mean_iou": round(mean, 3),
        "max_iou": max(per_char.values(), default=0.0),
        "verdict": verdict(mean),
        "per_char": per_char,
    }
