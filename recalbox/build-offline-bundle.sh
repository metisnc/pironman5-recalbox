#!/bin/bash
# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
# Build an offline bundle for recalbox/install.sh --offline, on any machine
# with Internet, python3 and pip (macOS or Linux, no compiler needed).
#
# Usage: bash recalbox/build-offline-bundle.sh [output_dir]
# Then copy the output dir and the repository to the Recalbox, e.g.
#   scp -r pironman5-offline root@recalbox:/recalbox/share/
#   bash install.sh --offline /recalbox/share/pironman5-offline

set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
OUT="${1:-pironman5-offline}"
mkdir -p "$OUT/wheels"

# Keep in sync with install.sh
PM_AUTO_COMMIT=$(sed -n 's/^PM_AUTO_COMMIT="\([0-9a-f]*\)".*/\1/p' "$HERE/install.sh")
SF_RPI_STATUS_COMMIT=$(sed -n 's/^SF_RPI_STATUS_COMMIT="\([0-9a-f]*\)".*/\1/p' "$HERE/install.sh")

python3 -m pip download --disable-pip-version-check --no-deps --only-binary=:all: \
    --require-hashes -r "$HERE/requirements-recalbox.txt" -d "$OUT/wheels" \
    --python-version 3.11 --implementation cp --abi cp311 --abi abi3 --abi none \
    --platform manylinux_2_34_aarch64 --platform manylinux2014_aarch64 --platform any

curl -fsSL -o "$OUT/pm_auto-$PM_AUTO_COMMIT.tar.gz" \
    "https://codeload.github.com/sunfounder/pm_auto/tar.gz/$PM_AUTO_COMMIT"
curl -fsSL -o "$OUT/sf_rpi_status-$SF_RPI_STATUS_COMMIT.tar.gz" \
    "https://codeload.github.com/sunfounder/sf_rpi_status/tar.gz/$SF_RPI_STATUS_COMMIT"

echo "Offline bundle ready in $OUT"
