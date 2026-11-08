"""Apply this fork's Korean overlay on top of the upstream translation files.

The overlay never edits upstream data blindly:
- additions/*.json fill only gaps. If upstream already has a real translation
  for a key, upstream wins and the addition is reported as "upstream has it".
    {"<m_table>": {src: ko}}   -> outgame + every field of that static table
    {"_outgame_only": {src: ko}} -> outgame only (strings collected on screen)
- overrides.json replaces specific upstream values (quality fixes). Each entry
  records the upstream value it was written against; if upstream has since
  changed that value, the override is skipped and reported as a conflict.
    {"<file>": {src: {"from": upstream_ko, "to": new_ko}}}
    <file> is "outgame", "names", "titles", "descriptions", "another_name",
    "ability_descriptions", or "static/<table>/<field>"

usage (from repo root): python3 -I kr-overlay/tools/apply_overlay.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TR = ROOT / "translations"
OVERLAY = ROOT / "kr-overlay"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def translated(d, k):
    return k in d and isinstance(d[k], str) and d[k] != k and d[k] != ""


def main():
    files = {}

    def get(name):
        if name not in files:
            files[name] = load(TR / name / "ko_KR.json")
        return files[name]

    og, st = get("outgame"), get("static")
    filled = upstream_has = 0
    for f in sorted((OVERLAY / "additions").glob("*.json")):
        for table, pairs in load(f).items():
            fields = None
            if table != "_outgame_only":
                fields = st.get(table)
                if not fields:
                    sys.exit(f"{f.name}: table {table} not in static bundle")
            for src, ko in pairs.items():
                if translated(og, src):
                    upstream_has += og[src] != ko
                else:
                    og[src] = ko
                    filled += 1
                for d in (fields or {}).values():
                    if not translated(d, src):
                        d[src] = ko

    applied = conflicts = 0
    ov_path = OVERLAY / "overrides.json"
    report = []
    for target, entries in (load(ov_path) if ov_path.exists() else {}).items():
        if target.startswith("static/"):
            _, table, field = target.split("/", 2)
            d = st.get(table, {}).get(field)
        else:
            d = get(target)
        if d is None:
            report.append(f"missing target {target}")
            continue
        for src, e in entries.items():
            cur = d.get(src)
            if cur == e["to"]:
                continue
            if cur == e["from"]:
                d[src] = e["to"]
                applied += 1
            else:
                conflicts += 1
                report.append(f"CONFLICT {target} {src[:30]!r}: upstream now {str(cur)[:40]!r}")

    for name, obj in files.items():
        save(TR / name / "ko_KR.json", obj)
    print(f"additions filled {filled} (upstream already translated differently: {upstream_has}); "
          f"overrides applied {applied}, conflicts {conflicts}")
    for line in report:
        print("  " + line)


if __name__ == "__main__":
    main()
