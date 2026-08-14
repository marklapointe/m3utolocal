#!/bin/sh
# Build the PEP 517 sdist and write ports/net/m3utolocal/distinfo.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
VERSION="${1:-1.2.0}"
NAME="m3utolocal-${VERSION}"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
"$PYTHON" -m build --sdist

TARBALL="$ROOT/dist/${NAME}.tar.gz"
if [ ! -f "$TARBALL" ]; then
  echo "error: expected $TARBALL" >&2
  exit 1
fi

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
