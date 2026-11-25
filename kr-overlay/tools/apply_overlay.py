"""Apply this fork's Korean overlay on top of the upstream translation files.

The overlay never edits upstream data blindly:
- additions/*.json fill only gaps. If upstream already has a real translation
  for a key, upstream wins and the addition is reported as "upstream has it".
    {"<m_table>": {src: ko}}   -> outgame + every field of that static table
    {"_outgame_only": {src: ko}} -> outgame only (strings collected on screen)
- novels/<novel_id>.json {src: ko} fill story lines the same way (gaps only);
  a story upstream has no file for gets translations/novels/<novel_id>/ko_KR.json
- novel_overrides/<novel_id>.json rewrites story lines the same way (quality fixes,
  never sexual scenes), checked against the upstream value like overrides.json
- overrides.json replaces specific upstream values (quality fixes). Each entry
  records the upstream value it was written against; if upstream has since
  changed that value, the override is skipped and reported as a conflict.
    {"<file>": {src: {"from": upstream_ko, "to": new_ko}}}
    <file> is "outgame", "names", "titles", "descriptions", "another_name",
    "ability_descriptions", or "static/<table>/<field>"

- user_r18/: adult-scene translations the user supplied (made elsewhere, not by this
  overlay's authors). They REPLACE upstream values: novels/<novel_id>.json {src: ko}
  and meta.json {"titles"|"descriptions"|"outgame": {src: ko}} (synopses go to
  descriptions and, where upstream keeps a copy there, to outgame too).

usage (from repo root): python3 -I kr-overlay/tools/apply_overlay.py
"""
import json
import re
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


TEMPLATE_TOKEN = re.compile(r"\{\[[^\]]+\][^}]*\}|\{[^\[{}][^{}]*\}")
COLOR_TAG = re.compile(r"</?color(?:=[^>]+)?>")


def order_templates(og):
    """AbyssMod tries outgame templates (keys with {0} / {[name]} tokens) in file
    order and uses the first match, so a generic template listed earlier hides a
    more specific one (e.g. "あと{0}時間" catching "あと3日5時間"). Put templates
    with more fixed text first; ties keep their original order. Exact keys are
    looked up by hash, so their position does not matter. The manifest hash sorts
    keys itself, so reordering does not change it."""
    plain, templates = [], []
    for i, (k, v) in enumerate(og.items()):
        stripped = COLOR_TAG.sub("", k)
        if TEMPLATE_TOKEN.search(stripped):
            templates.append((-len(TEMPLATE_TOKEN.sub("", stripped)), i, k, v))
        else:
            plain.append((k, v))
    templates.sort()
    return dict(plain + [(k, v) for _, _, k, v in templates])


def main():
    files = {}

    def get(name):
        if name not in files:
            files[name] = load(TR / name / "ko_KR.json")
        return files[name]

    og, st = get("outgame"), get("static")
    # upstream values as published, before anything from this overlay
    baseline = [dict(og), dict(get("descriptions")), dict(get("ability_descriptions"))]
    baseline += [dict(d) for fields in st.values() for d in fields.values()]
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
    all_ov = load(ov_path) if ov_path.exists() else {}
    # story rewrites: novel_overrides/<novel_id>.json {src: {"from": upstream_ko, "to": new_ko}}
    for f in sorted((OVERLAY / "novel_overrides").glob("*.json")):
        all_ov["novels/" + f.stem] = load(f)
    for target, entries in all_ov.items():
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

    sys.path.insert(0, str(Path(__file__).parent))
    import rules as rules_mod
    rule_stats = {}
    rules_path = OVERLAY / "rules.json"
    if rules_path.exists():
        targets = [get("outgame"), get("descriptions"), get("ability_descriptions")]
        targets += [d for fields in get("static").values() for d in fields.values()]
        rule_stats = rules_mod.apply_rules(load(rules_path), targets, baseline)

    # user-supplied adult-scene translations: replace upstream
    user_meta = user_lines = 0
    um_path = OVERLAY / "user_r18" / "meta.json"
    if um_path.exists():
        um = load(um_path)
        for src, ko in um.get("titles", {}).items():
            for name in ("titles", "outgame"):
                d = get(name)
                if name == "titles" or src in d:
                    if d.get(src) != ko:
                        d[src] = ko
                        user_meta += 1
        for src, ko in um.get("descriptions", {}).items():
            for name in ("descriptions", "outgame"):
                d = get(name)
                if name == "descriptions" or src in d:
                    if d.get(src) != ko:
                        d[src] = ko
                        user_meta += 1

    files["outgame"] = order_templates(files["outgame"])
    for name, obj in files.items():
        save(TR / name / "ko_KR.json", obj)

    # stories: novels/<novel_id>.json fills only lines upstream has not translated
    novel_filled = novel_files = 0
    for f in sorted((OVERLAY / "novels").glob("*.json")):
        target = TR / "novels" / f.stem / "ko_KR.json"
        cur = load(target) if target.exists() else {}
        n = 0
        for src, ko in load(f).items():
            if not translated(cur, src):
                cur[src] = ko
                n += 1
        if n:
            target.parent.mkdir(parents=True, exist_ok=True)
            save(target, cur)
            novel_filled += n
            novel_files += 1

    for f in sorted((OVERLAY / "user_r18" / "novels").glob("*.json")):
        target = TR / "novels" / f.stem / "ko_KR.json"
        cur = load(target) if target.exists() else {}
        n = 0
        for src, ko in load(f).items():
            if cur.get(src) != ko:
                cur[src] = ko
                n += 1
        if n or not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            save(target, cur)
            user_lines += n

    # user term choices: where the Japanese key has the term, swap the Korean word everywhere
    term_n = 0
    if um_path.exists():
        reps = load(um_path).get("term_replace", [])
        if reps:
            def walk(o):
                nonlocal term_n
                for k, v in list(o.items()):
                    if isinstance(v, dict):
                        walk(v)
                    elif isinstance(v, str):
                        nv = v
                        for ja, old, new in reps:
                            if ja in k and old in nv:
                                nv = nv.replace(old, new)
                        if nv != v:
                            o[k] = nv
                            term_n += 1
            for p in sorted(TR.glob("*/ko_KR.json")) + sorted((TR / "novels").glob("*/ko_KR.json")):
                if p.parent.name == "manifest":
                    continue
                obj = load(p)
                before = term_n
                walk(obj)
                if term_n != before:
                    save(p, obj)

    sys.path.insert(0, str(Path(__file__).parent))
    import font_safe
    fs_files, fs_values = font_safe.apply(ROOT)

    print(f"additions filled {filled} (upstream already translated differently: {upstream_has}); "
          f"story lines filled {novel_filled} in {novel_files} files; "
          f"overrides applied {applied}, conflicts {conflicts}; "
          f"font-safe glyphs fixed in {fs_values} values / {fs_files} files; "
          f"user adult translations: {user_lines} story lines, {user_meta} titles/synopses; user term swaps {term_n}")
    for line in rule_stats.pop("_skipped", []):
        print("  RULE OFF " + line)
    for name, n in rule_stats.items():
        print(f"  rule {name}: {n} values")
    for line in report:
        print("  " + line)


if __name__ == "__main__":
    main()
