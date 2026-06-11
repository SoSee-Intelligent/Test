"""命令行入口：python -m zigui [风格文件...]

不带参数时构建 styles/ 下全部风格，输出 OTF 与对照样张到 dist/。
"""

import json
import sys
from pathlib import Path

from .builder import build_font
from .glyphs import CHARS
from .preview import render_specimen


def main(argv):
    root = Path(__file__).resolve().parent.parent
    style_paths = [Path(p) for p in argv] or sorted((root / "styles").glob("*.json"))
    dist = root / "dist"
    dist.mkdir(exist_ok=True)

    rows = []
    for path in style_paths:
        style = json.loads(path.read_text(encoding="utf-8"))
        out = dist / (path.stem + ".otf")
        contours = build_font(style, out)
        rows.append((style["name"], contours, CHARS))
        print(f"已生成 {out}（{len(CHARS)} 个演示字形）")

    specimen = dist / "specimen.png"
    render_specimen(rows, specimen)
    print(f"样张已输出 {specimen}")


if __name__ == "__main__":
    main(sys.argv[1:])
