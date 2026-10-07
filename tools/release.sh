#!/bin/sh
# tools/release.sh TAG [--dry-run] : builds the two roms and publishes them as
# a GitHub release (notes = the section of docs/CHANGELOG.md for TAG).
# Needs the `gh` CLI (logged in) or a token in $GH_TOKEN (scope: repo).
set -e
TAG=${1:?usage: tools/release.sh TAG [--dry-run]}
DRY=$2
cd "$(dirname "$0")/.."
REPO=${REPO:-luginf/writhdeck-uxn}
make rom rom-cli >/dev/null
rm -rf dist && mkdir dist
cp bin/writhdeck-cli.rom bin/writhdeck.rom dist/
(cd dist && sha256sum writhdeck-cli.rom writhdeck.rom > SHA256SUMS)
awk -v t="## $TAG" '$0==t{f=1;next} /^## /{f=0} f' docs/CHANGELOG.md > dist/NOTES.md
[ -s dist/NOTES.md ] || { echo "no section '## $TAG' in docs/CHANGELOG.md" >&2; exit 1; }
ls -la dist
[ "$DRY" = "--dry-run" ] && { echo "dry run: nothing published"; exit 0; }
if command -v gh >/dev/null 2>&1; then
    if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
        # the release exists: drop assets that no longer exist, replace the others, refresh the notes
        for old in $(gh release view "$TAG" --repo "$REPO" --json assets --jq '.assets[].name'); do
            [ -e "dist/$old" ] || gh release delete-asset "$TAG" "$old" --repo "$REPO" --yes
        done
        gh release upload "$TAG" dist/writhdeck.rom dist/writhdeck-cli.rom dist/SHA256SUMS --repo "$REPO" --clobber
        gh release edit "$TAG" --repo "$REPO" --notes-file dist/NOTES.md
        exit 0
    fi
    gh release create "$TAG" dist/writhdeck-cli.rom dist/writhdeck.rom dist/SHA256SUMS \
        --repo "$REPO" --title "writhdeck-uxn $TAG" --notes-file dist/NOTES.md
    exit 0
fi
: "${GH_TOKEN:?install gh and run 'gh auth login', or export GH_TOKEN}"
API=https://api.github.com/repos/$REPO
BODY=$(python3 -c 'import json,sys;print(json.dumps({"tag_name":sys.argv[1],"name":"writhdeck-uxn "+sys.argv[1],"body":open("dist/NOTES.md").read()}))' "$TAG")
RESP=$(curl -fsS -X POST -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" "$API/releases" -d "$BODY")
UPLOAD=$(printf '%s' "$RESP" | python3 -c 'import json,sys;print(json.load(sys.stdin)["upload_url"].split("{")[0])')
for f in writhdeck-cli.rom writhdeck.rom SHA256SUMS; do
    curl -fsS -X POST -H "Authorization: Bearer $GH_TOKEN" -H "Content-Type: application/octet-stream" \
        --data-binary @"dist/$f" "$UPLOAD?name=$f" >/dev/null && echo "uploaded $f"
done
echo "release $TAG published"
