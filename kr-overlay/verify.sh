#!/usr/bin/env bash
# Pre-commit gate. Fails (non-zero) unless ALL hold:
#  1. every additions/novels file passes check_pairs (tags, placeholders, line breaks,
#     no Japanese left, Hangul inside the story font's KS X 1001 set)
#  2. upstream's own validator finds no more problems than it finds in clean upstream
#     (upstream's own issues pass through untouched; the overlay must add none)
#  3. applying the overlay to a clean upstream checkout, then running upstream's own
#     manifest script, reproduces translations/ (manifest included) byte for byte
#     (skipped with --no-repro: sync-upstream.sh builds from clean upstream already)
set -euo pipefail
repro=1; [ "${1:-}" = "--no-repro" ] && repro=0
cd "$(dirname "$0")/.."
for f in kr-overlay/additions/*.json kr-overlay/novels/*.json; do
  [ -e "$f" ] || continue
  python3 -I kr-overlay/tools/check_pairs.py "$f" | tail -1 | grep -q "problems 0" || { echo "FAIL check_pairs $f"; exit 1; }
done

tmp=$(mktemp -d)
trap 'git worktree remove --force "$tmp/wt" >/dev/null 2>&1 || true; rm -rf "$tmp"' EXIT
git worktree add -q "$tmp/wt" upstream/main

counts() { grep -E '^[A-Za-z]+(Errors|Values|Shape)=[0-9]+$' | sort; }
(cd "$tmp/wt" && node scripts/validate-translations.mjs || true) | counts > "$tmp/base.txt"
node scripts/validate-translations.mjs > "$tmp/ours.out" || true
counts < "$tmp/ours.out" > "$tmp/ours.txt"
[ -s "$tmp/ours.txt" ] || { cat "$tmp/ours.out"; echo "FAIL validate-translations did not run"; exit 1; }
python3 -I - "$tmp/base.txt" "$tmp/ours.txt" <<'EOF' || { sed -n '/^Samples:/,$p' "$tmp/ours.out" | head -20; exit 1; }
import sys
read = lambda p: dict(l.strip().split("=") for l in open(p) if "=" in l)
base, ours = read(sys.argv[1]), read(sys.argv[2])
worse = [f"{k}: upstream {base.get(k, '0')} -> ours {v}" for k, v in ours.items() if int(v) > int(base.get(k, 0))]
for k, v in base.items():
    if v != "0":
        print(f"note: upstream itself has {k}={v} (left as upstream has it)")
if worse:
    print("FAIL validate-translations: overlay added problems: " + "; ".join(worse))
    sys.exit(1)
EOF

[ $repro = 1 ] || { echo "VERIFY OK"; exit 0; }
cp -r kr-overlay "$tmp/wt/"
(cd "$tmp/wt" && python3 -I kr-overlay/tools/apply_overlay.py >/dev/null && node scripts/update-manifest.mjs >/dev/null)
diff -rq "$tmp/wt/translations" translations || { echo "FAIL clean-upstream reproduction"; exit 1; }
echo "VERIFY OK"
