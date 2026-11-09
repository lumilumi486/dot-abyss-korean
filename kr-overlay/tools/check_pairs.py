"""Technical check of {source: korean} pairs before they go into the game files.

Fails on: tag/placeholder mismatch, more line breaks than the source,
Japanese kana/kanji left in the Korean, empty or unchanged values.
Colour tags added around Korean terms are allowed only as balanced pairs.

usage: python3 -I check_pairs.py <additions.json | novels/<id>.json>
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
    # colour wrappers may be added around Korean terms, but only as complete pairs:
    # the open/close imbalance must equal the source's own (some sources leave one open)
    if ko.count("<color=") - ko.count("</color>") != src.count("<color=") - src.count("</color>"):
        problems.append("color tag balance differs from source")
    left = JAPANESE.findall(ko)
    if left:
        problems.append(f"Japanese left: {''.join(left)}")
    # the story font (MaplestoryKR SDF) is a static atlas; upstream uses only the
    # 2,350 KS X 1001 syllables, so anything outside that set may render as a box
    rare = [c for c in ko if "가" <= c <= "힣" and not _ks(c)]
    if rare:
        problems.append(f"Hangul outside KS X 1001: {''.join(rare)}")
    return problems


def _ks(c):
    try:
        c.encode("euc-kr")
        return True
    except UnicodeEncodeError:
        return False


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if all(isinstance(v, str) for v in data.values()):
        data = {"story": data}  # kr-overlay/novels/<id>.json is a flat {src: ko}
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
