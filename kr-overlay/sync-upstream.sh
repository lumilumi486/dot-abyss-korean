#!/usr/bin/env bash
# Bring in the latest upstream (ddojuki-creator/dot-abyss-korean) and re-apply
# this fork's overlay on top. History stays linear-compatible (merge commit),
# no force-push, and upstream files are taken exactly as upstream has them.
set -euo pipefail
cd "$(dirname "$0")/.."

git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/ddojuki-creator/dot-abyss-korean.git
git fetch upstream main
if git merge-base --is-ancestor upstream/main HEAD; then
  echo "already up to date with upstream"; exit 0
fi

git merge -s ours --no-commit upstream/main      # record upstream as merged
git read-tree --reset -u upstream/main            # take upstream's tree exactly
git checkout HEAD -- kr-overlay                   # keep our overlay
python3 -I kr-overlay/tools/apply_overlay.py
python3 -I kr-overlay/tools/manifest.py write .
node scripts/validate-translations.mjs
git add -A
git commit -m "Sync upstream $(git rev-parse --short upstream/main) and re-apply KR overlay"
