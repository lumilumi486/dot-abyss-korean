"""Extract Japanese strings from the game's MessagePack master-data cache and
report which ones have no Korean translation in the translation repo.

Port of the location rules in upstream scripts/extract-game-cache.mjs
(same table exclusions, same row naming, same Japanese test, same 2000-char cap).
Read-only: writes only the report files given on the command line.

usage: python3 -I extract_missing.py <cache.dat> <repo_dir> <out_dir>
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import msgpack

JAPANESE = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")
EXCLUDED = [
    re.compile(r"^m_ng_words$"),
    re.compile(r"^m_payment_(googleplay|appstore)_products$"),
    re.compile(r"(?:^|_)text_colors?$"),
]


def record_name(row, index, occurrences):
    cand = row[0] if isinstance(row, list) and row else None
    if not isinstance(cand, (str, int)) or isinstance(cand, bool) or len(str(cand)) > 120:
        return f"row:{index}"
    base = f"id:{cand}"
    n = occurrences[base]
    occurrences[base] += 1
    return base if n == 0 else f"{base}#{n}"


def collect(value, location, out):
    if isinstance(value, str):
        if len(value) <= 2000 and JAPANESE.search(value):
            out["/".join(location)] = value
    elif isinstance(value, list):
        for i, v in enumerate(value):
            collect(v, location + [str(i)], out)
    elif isinstance(value, dict):
        for k in sorted(value, key=str):
            collect(value[k], location + [str(k)], out)


def extract(root):
    entries = {}
    for table, value in root.items():
        if any(p.search(table) for p in EXCLUDED):
            continue
        if isinstance(value, list):
            occ = Counter()
            for i, row in enumerate(value):
                collect(row, [table, record_name(row, i, occ)], entries)
        else:
            collect(value, [table], entries)
    return entries


def flatten_keys(obj, sink):
    """Collect every translated source key (key whose value is a different string)."""
    for k, v in obj.items():
        if isinstance(v, dict):
            flatten_keys(v, sink)
        elif isinstance(v, str) and v != k:
            sink.add(k)


def main():
    cache, repo, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    root = msgpack.unpackb(cache.read_bytes(), raw=False, strict_map_key=False)
    entries = extract(root)

    known = set()
    tr = repo / "translations"
    for f in tr.rglob("ko_KR.json"):
        if "manifest" in f.parts:
            continue
        flatten_keys(json.loads(f.read_text(encoding="utf-8")), known)

    snap = json.loads((repo / "snapshots" / "game-cache-ja_JP.json").read_text(encoding="utf-8"))
    prev = snap.get("entries", {})

    missing = defaultdict(dict)  # table -> {location: source}
    for loc, src in entries.items():
        if src not in known:
            missing[loc.split("/")[0]][loc] = src
    added = {loc: src for loc, src in entries.items() if loc not in prev}
    changed = {loc: {"before": prev[loc], "after": src}
               for loc, src in entries.items() if loc in prev and prev[loc] != src}

    summary = {
        "locations": len(entries),
        "uniqueStrings": len(set(entries.values())),
        "snapshotGeneratedAt": snap.get("generatedAt"),
        "addedSinceSnapshot": len(added),
        "changedSinceSnapshot": len(changed),
        "missingLocations": sum(len(v) for v in missing.values()),
        "missingUniqueStrings": len({s for v in missing.values() for s in v.values()}),
        "missingByTable": dict(sorted(((t, len(v)) for t, v in missing.items()),
                                      key=lambda x: -x[1])),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "missing.json").write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "added.json").write_text(json.dumps(added, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "changed.json").write_text(json.dumps(changed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
