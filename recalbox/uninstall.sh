#!/bin/bash
# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
# Pironman 5 uninstaller / rollback for Recalbox.
#
# Stops the service, removes the autostart block from custom.sh and moves
# /recalbox/share/pironman5 to /recalbox/share/pironman5-backups/ (nothing is
# deleted: remove the backup folder by hand once you no longer need it).
#
# Usage: bash /recalbox/share/pironman5/app/recalbox/uninstall.sh

set -euo pipefail

PM5_HOME="${PM5_HOME:-/recalbox/share/pironman5}"
BACKUP_ROOT="/recalbox/share/pironman5-backups"
CUSTOM_SH="/recalbox/share/system/custom.sh"
MARK_BEGIN="# >>> pironman5-recalbox >>>"
MARK_END="# <<< pironman5-recalbox <<<"

log() { echo "[pironman5] $*"; }

[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 1; }

# This script lives inside PM5_HOME, which is moved below: run from a copy.
if [ -z "${PM5_UNINSTALL_COPY:-}" ]; then
    copy=$(mktemp /tmp/pironman5-uninstall.XXXXXX)
    cp "$0" "$copy"
    PM5_UNINSTALL_COPY="$copy" exec bash "$copy" "$@"
fi
trap 'rm -f "$PM5_UNINSTALL_COPY"' EXIT

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/uninstall-$STAMP"
mkdir -p "$BACKUP_DIR"

# 1. Stop the service (switches off OLED, RGB LEDs and case fans)
if [ -f "$PM5_HOME/app/recalbox/pironman5-service.sh" ]; then
    bash "$PM5_HOME/app/recalbox/pironman5-service.sh" stop || true
elif [ -f /var/run/pironman5.pid ]; then
    kill -TERM "$(cat /var/run/pironman5.pid)" 2>/dev/null || true
fi

# 2. Remove the autostart block from custom.sh
if grep -qF "$MARK_BEGIN" "$CUSTOM_SH" 2>/dev/null; then
    cp "$CUSTOM_SH" "$BACKUP_DIR/custom.sh"
    sed "/^$MARK_BEGIN\$/,/^$MARK_END\$/d" "$BACKUP_DIR/custom.sh" > "$CUSTOM_SH"
    # custom.sh created by the installer and now empty: put it aside
    if ! grep -qv '^#!/bin/bash$' "$CUSTOM_SH" \
            && ls "$BACKUP_ROOT"/*/.custom_sh_absent >/dev/null 2>&1; then
        mv "$CUSTOM_SH" "$BACKUP_DIR/custom.sh.empty"
        log "Removed $CUSTOM_SH (created by the installer)"
    else
        log "Removed autostart block from $CUSTOM_SH"
    fi
fi

# 3. Move the installation aside
if [ -d "$PM5_HOME" ]; then
    mv "$PM5_HOME" "$BACKUP_DIR/pironman5"
    log "Moved $PM5_HOME to $BACKUP_DIR/pironman5"
fi

log "Uninstalled. /boot and the rootfs were never modified."
log "Backups kept in $BACKUP_ROOT (delete them by hand when no longer needed)."
