"""Replace characters the Korean story font (MaplestoryKR SDF, static atlas) lacks.

AbyssMod swaps story text to the Korean font, so these glyphs would render as
boxes there. Each is mapped to a visually equivalent glyph the font contains
(checked against the font's character table). Only Korean values change: the
Japanese keys and each file's own formatting stay byte-for-byte as they were.

Config: kr-overlay/font_safe.json
  {"map": {"・": "·", ...}, "names": true, "novel_prefixes": ["mas", "evs", "men"]}
"""
import json
import re
from pathlib import Path

STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def _rewrite_values(raw, mapping):
    """Rewrite only the value strings of a flat {key: value} JSON object."""
    out, pos, is_value, changed = [], 0, False, 0
    for m in STRING.finditer(raw):
        between = raw[pos:m.start()]
        out.append(between)
        token = m.group()
        if is_value:
            new = token
            for a, b in mapping.items():
                new = new.replace(a, b)
            if new != token:
                changed += 1
            token = new
        out.append(token)
        pos = m.end()
        # the next string is a value if this one is followed by a colon
        nxt = raw[pos:pos + 8].lstrip()
        is_value = nxt.startswith(":")
    out.append(raw[pos:])
    return "".join(out), changed


def apply(root):
    cfg_path = root / "kr-overlay" / "font_safe.json"
    if not cfg_path.exists():
        return 0, 0
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    mapping = cfg["map"]
    targets = []
    if cfg.get("names"):
        targets.append(root / "translations" / "names" / "ko_KR.json")
    for d in sorted((root / "translations" / "novels").iterdir()):
        if d.name.split("_")[0] in cfg.get("novel_prefixes", []):
            targets.append(d / "ko_KR.json")
    files = values = 0
    for f in targets:
        if not f.exists():
            continue
        raw = f.read_text(encoding="utf-8")
        new, n = _rewrite_values(raw, mapping)
        if not n:
            continue
        before, after = json.loads(raw), json.loads(new)
        if list(before) != list(after):
            raise SystemExit(f"key changed in {f}")
        for k in before:
            exp = before[k]
            if isinstance(exp, str):
                for a, b in mapping.items():
                    exp = exp.replace(a, b)
            if after[k] != exp:
                raise SystemExit(f"unexpected value change in {f}: {k[:20]!r}")
        f.write_text(new, encoding="utf-8")
        files += 1
        values += n
    return files, values
