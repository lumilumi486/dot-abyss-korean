"""Python port of scripts/update-manifest.mjs (the hash AbyssMod checks).

  python3 -I manifest.py verify <repo>   -> rebuild and compare with the committed manifest
  python3 -I manifest.py write  <repo>   -> rewrite translations/manifest/ko_KR.json
"""
import hashlib
import json
import sys
from pathlib import Path

CONTENT_TYPES = ["names", "titles", "descriptions", "another_name", "outgame", "static"]


def js_sorted(keys):
    # JavaScript Array.prototype.sort() compares UTF-16 code units.
    return sorted(keys, key=lambda s: s.encode("utf-16-be"))


def js_string(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, list):
        return ",".join(js_string(x) for x in v)
    return str(v)


def traverse(obj, prefix=""):
    for key in js_sorted(obj.keys()):
        value = obj[key]
        path = f"{prefix}\x01{key}" if prefix else key
        if isinstance(value, dict):
            yield from traverse(value, path)
        else:
            yield path, js_string(value)


def object_hash(obj):
    md5 = hashlib.md5()
    for key, value in traverse(obj):
        md5.update(key.encode("utf-8", "surrogatepass"))
        md5.update(b"\0")
        md5.update(value.encode("utf-8", "surrogatepass"))
        md5.update(b"\0")
    return md5.hexdigest()


def file_hash(path):
    return object_hash(json.loads(path.read_text(encoding="utf-8")))


def build(repo):
    tr = repo / "translations"
    manifest = {}
    for t in CONTENT_TYPES:
        f = tr / t / "ko_KR.json"
        if f.exists():
            manifest[t] = file_hash(f)
    manifest["novels"] = {}
    for d in js_sorted([p.name for p in (tr / "novels").iterdir()]):
        f = tr / "novels" / d / "ko_KR.json"
        if f.exists():
            manifest["novels"][d] = file_hash(f)
    manifest["hash"] = object_hash(manifest)
    return manifest


def main():
    mode, repo = sys.argv[1], Path(sys.argv[2])
    built = build(repo)
    out = repo / "translations" / "manifest" / "ko_KR.json"
    if mode == "verify":
        current = json.loads(out.read_text(encoding="utf-8"))
        diffs = [k for k in CONTENT_TYPES + ["hash"] if current.get(k) != built.get(k)]
        ndiff = [k for k in built["novels"] if current["novels"].get(k) != built["novels"][k]]
        print("top-level diffs:", diffs or "none", "| novel diffs:", len(ndiff), "| hash:", built["hash"])
        sys.exit(1 if diffs or ndiff else 0)
    elif mode == "write":
        out.write_text(json.dumps(built, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
        print("manifest written, hash:", built["hash"])


if __name__ == "__main__":
    main()
