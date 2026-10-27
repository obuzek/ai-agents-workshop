#!/usr/bin/env bash
# Build every edition of the docsite into site/<edition>/ and add the root redirect pages.
# Usage: ./build.sh [extra mkdocs build args, e.g. --strict]
#
# IBM_DOCS_DIR (optional): build the IBM edition from another checkout's docs/ibm,
# e.g. the txc-2026-ibm branch, which carries the IBM workshop code students clone.
set -euo pipefail

cd "$(dirname "$0")"
EDITIONS=(oss ibm)
SITE="$PWD/site"

rm -rf site
for edition in "${EDITIONS[@]}"; do
  src="$edition"
  if [[ "$edition" == ibm && -n "${IBM_DOCS_DIR:-}" ]]; then
    src="$IBM_DOCS_DIR"
  fi
  echo "==> Building $edition from $src"
  (cd "$src" && mkdocs build --site-dir "$SITE/$edition" "$@")
done
cp root/index.html root/404.html site/
echo "==> Built site/ (${EDITIONS[*]})"
