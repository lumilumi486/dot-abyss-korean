#!/usr/bin/env bash
# Bring in the latest upstream (ddojuki-creator/dot-abyss-korean) and re-apply
# this fork's overlay on top. Upstream files are taken exactly as upstream has
# them; the overlay only fills gaps (upstream wins on every sentence it has).
# History stays fast-forward (merge commit), no force-push.
# Run by .github/workflows/sync-upstream.yml every hour; also fine to run by hand.
# Exits 0 without committing when upstream has nothing new.
set -euo pipefail
cd "$(dirname "$0")/.."

git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/ddojuki-creator/dot-abyss-korean.git
git fetch upstream main
if git merge-base --is-ancestor upstream/main HEAD; then
  echo "already up to date with upstream $(git rev-parse --short upstream/main)"; exit 0
fi

git merge -s ours --no-commit upstream/main      # record upstream as merged
git read-tree --reset -u upstream/main            # take upstream's tree exactly
git checkout HEAD -- kr-overlay .github           # keep our overlay and the sync workflow
python3 -I kr-overlay/tools/apply_overlay.py
node scripts/update-manifest.mjs                  # upstream's own manifest script
kr-overlay/verify.sh --no-repro                   # any failure stops here: nothing is committed
git add -A
git commit -q -m "Sync upstream $(git rev-parse --short upstream/main) and re-apply KR overlay"
echo "synced to upstream $(git rev-parse --short upstream/main)"
