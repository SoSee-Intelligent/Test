"""生成即存证：为每次构建产出著作权登记用的证据清单。

字体在中国不适用专利，确权路径为著作权（计算机软件著作权 +
美术作品登记）。登记效率的关键是创作过程证据链的自动化：
参数文件与成品的哈希 + 生成时间戳 + 独创性声明，
后续可叠加可信时间戳（TSA）与登记机构电子申请对接。
"""

import hashlib
import json
from datetime import datetime, timezone

from . import __version__
from .glyphs import CHARS

STATEMENT = (
    "本字体由字规（ZiGui）参数化引擎根据自有笔画骨架数据与本清单所列"
    "风格参数文件生成，生成过程未参照、训练或演绎任何第三方字体。"
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_evidence(font_path, style_path):
    """在成品 OTF 旁写出 <名称>.evidence.json，返回清单路径。"""
    manifest = {
        "engine": f"ZiGui {__version__}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "style_file": {"path": style_path.name, "sha256": sha256_file(style_path)},
        "font_file": {"path": font_path.name, "sha256": sha256_file(font_path)},
        "glyph_coverage": "".join(CHARS),
        "statement": STATEMENT,
    }
    out = font_path.with_suffix(".evidence.json")
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
