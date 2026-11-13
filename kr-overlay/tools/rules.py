"""Apply kr-overlay/rules.json: source-conditioned wording unification.

A rule changes a Korean value only when its Japanese key matches `key` (regex)
and not `key_not`. Rules marked "user_choice" carry a wording the user chose and
are not switched off when upstream prefers the other spelling. Plain `replace` pairs fix the Korean particle that follows the
replaced word when the new word's final consonant differs (매혹을 -> 매료를,
은혜가 -> 혜택이). Placeholders/tags are never part of a replaced term.
"""
import json
import re

PARTICLES = [  # (after consonant, after vowel)
    ("으로", "로"), ("을", "를"), ("은", "는"), ("과", "와"), ("이", "가"),
]


def has_batchim(word):
    ch = word[-1]
    code = ord(ch) - 0xAC00
    return 0 <= code <= 11171 and code % 28 != 0


def ends_in_rieul(word):
    code = ord(word[-1]) - 0xAC00
    return 0 <= code <= 11171 and code % 28 == 8


def _swap(old, new, value):
    if has_batchim(old) == has_batchim(new) and ends_in_rieul(old) == ends_in_rieul(new):
        return value.replace(old, new), value.count(old)
    out, i, n = [], 0, 0
    while True:
        j = value.find(old, i)
        if j < 0:
            out.append(value[i:])
            break
        out.append(value[i:j])
        out.append(new)
        k = j + len(old)
        for cons, vow in PARTICLES:
            src = cons if has_batchim(old) else vow
            dst = cons if has_batchim(new) else vow
            if cons == "으로" and ends_in_rieul(new):
                dst = "로"
            if value.startswith(src, k):
                after = value[k + len(src):k + len(src) + 1]
                # "이"/"가" only as a standalone particle (not 이번, 이상 ...)
                if src in ("이", "가") and after and re.match(r"[가-힣]", after):
                    continue
                out.append(dst)
                k += len(src)
                break
        i = k
        n += 1
    return "".join(out), n


def _matches(k, kre, kno):
    return kre.search(k) and not (kno and kno.search(k))


def upstream_preferred(compiled, baseline):
    """Keep a replace pair only while upstream itself (baseline = upstream values
    before this overlay) uses the target spelling more often than the old one, in
    entries whose key matches the rule. If upstream switches its own wording, the
    pair turns itself off and upstream's choice stands."""
    keep, skipped = {}, []
    for r, kre, kno in compiled:
        if r.get("user_choice"):
            # wording the user decided on: applied even where upstream mostly uses the other spelling
            keep[r["name"]] = [tuple(x) for x in r.get("replace", [])]
            continue
        pairs = []
        for old, new in r.get("replace", []):
            n_old = n_new = 0
            for d in baseline:
                for k, v in d.items():
                    if isinstance(v, str) and v != k and _matches(k, kre, kno):
                        n_old += old in v
                        n_new += new in v
            if n_old and n_new <= n_old:
                skipped.append(f"{r['name']}: {old}->{new} off (upstream uses old {n_old}, new {n_new})")
            else:
                pairs.append((old, new))
        keep[r["name"]] = pairs
    return keep, skipped


def apply_rules(cfg, dicts, baseline=None):
    """dicts: list of {src: ko} dicts (modified in place). Returns {rule: changed values}.
    With baseline, replace pairs upstream no longer prefers are skipped and listed
    under the "_skipped" key."""
    stats = {}
    compiled = [(r, re.compile(r["key"]), re.compile(r["key_not"]) if r.get("key_not") else None)
                for r in cfg["rules"]]
    if baseline is not None:
        keep, skipped = upstream_preferred(compiled, baseline)
        if skipped:
            stats["_skipped"] = skipped
        for r, _, _ in compiled:
            r["replace"] = keep[r["name"]]
    for d in dicts:
        for k, v in list(d.items()):
            if not isinstance(v, str) or v == k:
                continue
            new = v
            for r, kre, kno in compiled:
                if not kre.search(k) or (kno and kno.search(k)):
                    continue
                before = new
                for old, rep in r.get("replace", []):
                    new, _ = _swap(old, rep, new)
                for pat, rep in r.get("regex", []):
                    new = re.sub(pat, rep, new)
                if new != before:
                    stats[r["name"]] = stats.get(r["name"], 0) + 1
            if new != v:
                d[k] = new
    return stats
