"""命令行入口。

python -m zigui [风格文件...]                构建（默认 styles/ 全部）→ OTF + 存证清单 + 样张
python -m zigui compare A.otf B.otf [--json 报告.json]   字形查重
python -m zigui blend A.json B.json 0.5 -o 新风格.json   风格混合
"""

import json
import sys
from pathlib import Path

from .blend import blend_styles
from .builder import build_font
from .evidence import write_evidence
from .fingerprint import compare_fonts
from .glyphs import CHARS
from .preview import render_specimen

ROOT = Path(__file__).resolve().parent.parent


def cmd_build(argv):
    style_paths = [Path(p) for p in argv] or sorted((ROOT / "styles").glob("*.json"))
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)

    rows = []
    for path in style_paths:
        style = json.loads(path.read_text(encoding="utf-8"))
        out = dist / (path.stem + ".otf")
        contours = build_font(style, out)
        evidence = write_evidence(out, path)
        rows.append((style["name"], contours, CHARS))
        print(f"已生成 {out}（{len(CHARS)} 个演示字形），存证 {evidence.name}")

    specimen = dist / "specimen.png"
    render_specimen(rows, specimen)
    print(f"样张已输出 {specimen}")


def cmd_compare(argv):
    json_out = None
    if "--json" in argv:
        i = argv.index("--json")
        json_out = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    report = compare_fonts(argv[0], argv[1])
    print(f"查重：{report['font_a']} ←→ {report['font_b']}")
    print(f"比对字形 {report['glyphs_compared']} 个 | "
          f"平均 IoU {report['mean_iou']} | 最高 {report['max_iou']}")
    print(f"结论：{report['verdict']}")
    top = sorted(report["per_char"].items(), key=lambda kv: -kv[1])[:5]
    print("重合度最高字形：" + "  ".join(f"{ch} {v}" for ch, v in top))
    if json_out:
        json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"报告已存 {json_out}")


def cmd_blend(argv):
    out = None
    if "-o" in argv:
        i = argv.index("-o")
        out = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    a = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    b = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    style = blend_styles(a, b, float(argv[2]))
    text = json.dumps(style, ensure_ascii=False, indent=2) + "\n"
    if out:
        out.write_text(text, encoding="utf-8")
        print(f"混合风格已存 {out}（{style['name']}）")
    else:
        print(text)


def cmd_order(argv):
    from .preview import render_order_sheet
    from .strokes import Strokes, glyph_stroke_contours
    from .glyphs import GLYPHS

    style_path = Path(argv[0]) if argv else ROOT / "styles" / "songti.json"
    style = json.loads(style_path.read_text(encoding="utf-8"))
    strokes = Strokes(style)
    per_char = {ch: glyph_stroke_contours(strokes, specs) for ch, specs in GLYPHS.items()}
    out = ROOT / "dist" / "stroke_order.png"
    out.parent.mkdir(exist_ok=True)
    render_order_sheet(per_char, CHARS, out)
    print(f"笔顺校对图已输出 {out}（{style['name']}）")


def main(argv):
    if argv and argv[0] == "compare":
        cmd_compare(argv[1:])
    elif argv and argv[0] == "blend":
        cmd_blend(argv[1:])
    elif argv and argv[0] == "order":
        cmd_order(argv[1:])
    else:
        cmd_build(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
