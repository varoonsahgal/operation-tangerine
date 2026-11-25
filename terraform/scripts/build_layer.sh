#!/usr/bin/env bash
# Builds a Lambda layer containing the Anthropic Python SDK (with the Bedrock extra)
# for the python3.13 / x86_64 Lambda runtime. Called by Terraform (lambda.tf).
set -euo pipefail

OUT_DIR="${1:?usage: build_layer.sh <out_dir> <requirements.txt>}"
REQUIREMENTS="${2:?usage: build_layer.sh <out_dir> <requirements.txt>}"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.9+ or set enable_claude_agent = false." >&2
  exit 1
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/python"

echo "🍊 Building Anthropic SDK layer into $OUT_DIR ..."
"$PY" -m pip install \
  --quiet \
  --disable-pip-version-check \
  --target "$OUT_DIR/python" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  --upgrade \
  -r "$REQUIREMENTS"

# boto3/botocore already ship with the Lambda runtime; drop the copies the
# bedrock extra pulled in to keep the layer small.
rm -rf "$OUT_DIR/python/boto3" "$OUT_DIR/python/botocore" "$OUT_DIR/python/s3transfer" \
       "$OUT_DIR"/python/boto3-*.dist-info "$OUT_DIR"/python/botocore-*.dist-info "$OUT_DIR"/python/s3transfer-*.dist-info
find "$OUT_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +

echo "✅ Layer built: $(du -sh "$OUT_DIR" | cut -f1)"
