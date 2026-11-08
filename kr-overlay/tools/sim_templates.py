"""Simulate AbyssMod's on-screen lookup to test translations without the game.

Mirrors OutGameTranslation as read from the DLL: exact match (outgame, names,
titles, descriptions) first; otherwise templates bucketed by the key's first
character ('\\0' when the key starts with a token), tried in file order, first
match wins; colour tags are ignored for matching; each captured value is itself
looked up exactly.

usage:
  python3 -I sim_templates.py <repo> "text1" "text2" ...
  python3 -I sim_templates.py <repo> --regress <old outgame.json>
      for every template, build a sample text and report where the chosen
      template differs between the old file and the repo's current file
"""
import json
import re
import sys
from pathlib import Path

TOKEN = re.compile(r"\{\[[^\]]+\][^}]*\}|\{[^\[{}][^{}]*\}")
COLOR = re.compile(r"</?color(?:=[^>]+)?>")


class Sim:
    def __init__(self, og, extra):
        self.og = og
        self.exact = [og] + extra
        self.buckets = {}
        for k, v in og.items():
            if not isinstance(v, str) or v == k:
                continue
            kk = COLOR.sub("", k)
            ms = list(TOKEN.finditer(kk))
            if not ms:
                continue
            parts, pos = [], 0
            for m in ms:
                parts.append(re.escape(kk[pos:m.start()]))
                parts.append("(.+?)")
                pos = m.end()
            parts.append(re.escape(kk[pos:]))
            first = "\0" if ms[0].start() == 0 else kk[0]
            self.buckets.setdefault(first, []).append(
                (re.compile("^" + "".join(parts) + "$", re.S), [m.group() for m in ms], v, k))

    def lookup(self, text):
        for d in self.exact:
            if text in d and isinstance(d[text], str) and d[text] != text:
                return d[text], "exact"
        t = COLOR.sub("", text)
        for b in ([t[0]] if t else []) + ["\0"]:
            for rx, names, v, k in self.buckets.get(b, []):
                m = rx.match(t)
                if m:
                    out = v
                    for n, val in zip(names, m.groups()):
                        rep = val
                        for d in self.exact:
                            if val in d and isinstance(d[val], str):
                                rep = d[val]
                                break
                        out = out.replace(n, rep, 1)
                    return out, k
        return None, None


def load_repo(repo):
    tr = Path(repo) / "translations"
    og = json.loads((tr / "outgame" / "ko_KR.json").read_text(encoding="utf-8"))
    extra = [json.loads((tr / n / "ko_KR.json").read_text(encoding="utf-8")) for n in ("names", "titles", "descriptions")]
    return og, extra


def main():
    og, extra = load_repo(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "--regress":
        old = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        a, b = Sim(old, extra), Sim(og, extra)
        changed = 0
        for k, v in old.items():
            if not isinstance(v, str) or v == k or not TOKEN.search(COLOR.sub("", k)):
                continue
            sample = TOKEN.sub("7", COLOR.sub("", k))
            ra, ka = a.lookup(sample)
            rb, kb = b.lookup(sample)
            if ka != kb:
                changed += 1
                la = len(TOKEN.sub("", COLOR.sub("", ka or "")))
                lb = len(TOKEN.sub("", COLOR.sub("", kb or "")))
                flag = "OK more specific" if lb >= la else "CHECK"
                print(f"{flag}: {sample[:40]!r}\n   old {ka!r} -> {ra!r}\n   new {kb!r} -> {rb!r}")
        print("templates whose sample now resolves differently:", changed)
        return
    sim = Sim(og, extra)
    for t in sys.argv[2:]:
        r, k = sim.lookup(t)
        print(f"{t!r}\n   => {r!r}   [{k if k else 'NO MATCH'}]")


if __name__ == "__main__":
    main()
