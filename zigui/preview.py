"""样张渲染：不依赖系统字体栈，直接把轮廓画成 PNG 便于校对。

笔画轮廓全部为实心多边形（无内孔），逐轮廓填充即等价于非零环绕填充。
"""

from PIL import Image, ImageDraw

CELL = 170          # 每个字的像素格
PAD = 20
GLYPH_BOX = 1000.0  # 字面坐标范围
Y_TOP = 870         # 渲染窗口上沿（字体单位）
Y_BOTTOM = -130


def _draw_glyph(draw, contours, ox, oy, scale):
    for contour in contours:
        pts = [(ox + x * scale, oy + (Y_TOP - y) * scale) for x, y in contour]
        draw.polygon(pts, fill=(20, 20, 20))


def render_specimen(rows, out_path):
    """rows: [(标签, {字符: 轮廓列表}, 字符顺序)]，每个风格渲染一行。"""
    n_chars = max(len(r[2]) for r in rows)
    label_w = 150
    width = label_w + n_chars * CELL + PAD * 2
    height = len(rows) * CELL + PAD * 2
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    scale = (CELL - 14) / GLYPH_BOX

    for row, (label, glyph_contours, chars) in enumerate(rows):
        oy = PAD + row * CELL + 7
        draw.text((PAD, oy + CELL // 2 - 8), label, fill=(120, 120, 120))
        for col, ch in enumerate(chars):
            ox = label_w + PAD + col * CELL + 7
            draw.rectangle(
                [ox, oy, ox + CELL - 14, oy + CELL - 14],
                outline=(225, 225, 225),
            )
            _draw_glyph(draw, glyph_contours[ch], ox, oy, scale)
    img.save(out_path)
