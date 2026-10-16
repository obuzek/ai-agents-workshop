#!/usr/bin/env bash
# Build every edition of the docsite into site/<edition>/ and add the root redirect pages.
# Usage: ./build.sh [extra mkdocs build args, e.g. --strict]
set -euo pipefail

cd "$(dirname "$0")"
EDITIONS=(opensource ibm)

rm -rf site
for edition in "${EDITIONS[@]}"; do
  echo "==> Building $edition"
  (cd "$edition" && mkdocs build --site-dir "../site/$edition" "$@")
done
cp root/index.html root/404.html site/
echo "==> Built site/ (${EDITIONS[*]})"
