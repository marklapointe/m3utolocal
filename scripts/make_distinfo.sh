#!/bin/sh
# Build release tarball + ports/net/m3utolocal/distinfo from the working tree.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VERSION="${1:-1.1.0}"
NAME="m3utolocal-${VERSION}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/$NAME" "$ROOT/dist"
rsync -a \
  --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
  --exclude '.pytest_cache' --exclude '.idea' --exclude '.junie' \
  --exclude 'dist' --exclude 'dist/**' --exclude 'downloads' --exclude '*.pyc' \
  --exclude '*.m3u' --exclude '*.m3u8' --exclude 'chans.m3u' \
  --exclude '*.part' --exclude '*.mp4' --exclude '*.mkv' --exclude '*.avi' \
  --exclude '*.ts' --exclude '*.webm' --exclude '*.m4v' \
  "$ROOT"/ "$STAGE/$NAME/"

TARBALL="$ROOT/dist/${NAME}.tar.gz"
tar -C "$STAGE" -czf "$TARBALL" "$NAME"

if command -v sha256sum >/dev/null 2>&1; then
  SHA="$(sha256sum "$TARBALL" | awk '{print $1}')"
elif command -v sha256 >/dev/null 2>&1; then
  SHA="$(sha256 -q "$TARBALL")"
else
  SHA="$(shasum -a 256 "$TARBALL" | awk '{print $1}')"
fi
SIZE="$(wc -c < "$TARBALL" | tr -d ' ')"
TS="$(date +%s)"

cat > "$ROOT/ports/net/m3utolocal/distinfo" <<EOF
TIMESTAMP = ${TS}
SHA256 (${NAME}.tar.gz) = ${SHA}
SIZE (${NAME}.tar.gz) = ${SIZE}
EOF

echo "Wrote $TARBALL"
echo "Wrote $ROOT/ports/net/m3utolocal/distinfo"
cat "$ROOT/ports/net/m3utolocal/distinfo"
