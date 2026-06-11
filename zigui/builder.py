"""字体构建：把字形轮廓写入标准 OTF（CFF 轮廓）字体文件。"""

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen

from .glyphs import GLYPHS
from .strokes import Strokes, build_glyph_contours

UPM = 1000
ASCENT = 880
DESCENT = -120


def _contours_to_charstring(contours, width=UPM):
    pen = T2CharStringPen(width, None)
    for contour in contours:
        pen.moveTo(contour[0])
        for pt in contour[1:]:
            pen.lineTo(pt)
        pen.closePath()
    return pen.getCharString()


def _notdef_charstring():
    outer = [(80, 0), (80, 760), (920, 760), (920, 0)]
    inner = [(140, 60), (860, 60), (860, 700), (140, 700)]
    return _contours_to_charstring([outer, inner])


def build_font(style, out_path):
    """根据风格参数生成 OTF，返回 {字符: 轮廓列表} 供预览渲染复用。"""
    strokes = Strokes(style)
    family = style["name"]
    ps_name = style["ps_name"]

    glyph_contours = {ch: build_glyph_contours(strokes, specs) for ch, specs in GLYPHS.items()}

    glyph_order = [".notdef", "space"]
    cmap = {0x20: "space"}
    charstrings = {
        ".notdef": _notdef_charstring(),
        "space": _contours_to_charstring([], width=500),
    }
    for ch, contours in glyph_contours.items():
        name = "uni%04X" % ord(ch)
        glyph_order.append(name)
        cmap[ord(ch)] = name
        charstrings[name] = _contours_to_charstring(contours)

    fb = FontBuilder(UPM, isTTF=False)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupCFF(ps_name, {"FullName": family, "FamilyName": family}, charstrings, {})
    metrics = {name: (500 if name == "space" else UPM, 0) for name in glyph_order}
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT)
    fb.setupNameTable({
        "familyName": family,
        "styleName": "Regular",
        "psName": ps_name,
        "fullName": family,
    })
    fb.setupOS2(
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        usWinAscent=ASCENT,
        usWinDescent=-DESCENT,
    )
    fb.setupPost()
    fb.save(out_path)
    return glyph_contours
