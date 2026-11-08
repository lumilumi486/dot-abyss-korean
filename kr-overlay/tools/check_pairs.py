"""Technical check of {source: korean} pairs before they go into the game files.

Fails on: tag/placeholder mismatch, more line breaks than the source,
Japanese kana/kanji left in the Korean, empty or unchanged values.
Colour tags added around Korean terms are allowed only as balanced pairs.

usage: python3 -I check_pairs.py <additions.json>
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

PROTECTED = re.compile(r"<br>|</?b>|</?i>|<size=[^>]*>|</size>|<sprite=[^>]*>|\{[0-9a-zA-Z_]+\}|%[sd]|<user>|%user%")
JAPANESE = re.compile(r"[ぁ-ゖァ-ヺ一-鿿]")


def check(src, ko):
    problems = []
    if not ko or ko == src:
        problems.append("empty or unchanged")
    if Counter(PROTECTED.findall(src)) != Counter(PROTECTED.findall(ko)):
        problems.append(f"protected tokens differ: {Counter(PROTECTED.findall(src))} vs {Counter(PROTECTED.findall(ko))}")
    if ko.count("\n") > src.count("\n"):
        problems.append("more line breaks than source")
    if ko.count("<color=") != ko.count("</color>"):
        problems.append("unbalanced color tags")
    left = JAPANESE.findall(ko)
    if left:
        problems.append(f"Japanese left: {''.join(left)}")
    return problems


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    bad = 0
    total = 0
    for table, pairs in data.items():
        for src, ko in pairs.items():
            total += 1
            p = check(src, ko)
            if p:
                bad += 1
                print(f"[{table}] {src[:40]!r}: {p}")
    print(f"checked {total}, problems {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
