#!/usr/bin/env bash
# Pre-commit gate. Fails (non-zero) unless ALL hold:
#  1. every additions file passes check_pairs (tags, placeholders, line breaks, no Japanese left)
#  2. upstream's own validator reports zero errors
#  3. the committed manifest matches the files
#  4. applying the overlay to a clean upstream checkout reproduces translations/ byte for byte
set -euo pipefail
cd "$(dirname "$0")/.."
for f in kr-overlay/additions/*.json; do
  python3 -I kr-overlay/tools/check_pairs.py "$f" | tail -1 | grep -q "problems 0" || { echo "FAIL check_pairs $f"; exit 1; }
done
out=$(node scripts/validate-translations.mjs)
echo "$out" | grep -E "Errors=|Values=" | grep -v "=0$" && { echo "FAIL validate-translations"; exit 1; }
python3 -I kr-overlay/tools/manifest.py verify . >/dev/null || { echo "FAIL manifest"; exit 1; }
tmp=$(mktemp -d)
trap 'git worktree remove --force "$tmp/wt" >/dev/null 2>&1 || true; rm -rf "$tmp"' EXIT
git worktree add -q "$tmp/wt" upstream/main
cp -r kr-overlay "$tmp/wt/"
(cd "$tmp/wt" && python3 -I kr-overlay/tools/apply_overlay.py >/dev/null && python3 -I kr-overlay/tools/manifest.py write . >/dev/null)
diff -rq "$tmp/wt/translations" translations || { echo "FAIL clean-upstream reproduction"; exit 1; }
echo "VERIFY OK"
