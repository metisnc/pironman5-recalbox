#!/bin/bash
# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
# Pironman 5 installer for Recalbox (Raspberry Pi 5).
#
# Everything is installed under /recalbox/share/pironman5 (persistent). The
# only other file touched is /recalbox/share/system/custom.sh, where a marked
# autostart block is added. /boot and the rootfs are never modified.
#
# Usage (on the Recalbox, as root):
#   bash install.sh                      # from a copy of the repository
#   bash install.sh --offline <bundle>   # no Internet, see build-offline-bundle.sh
#   bash install.sh --variant max        # case model without asking: base or max
#   wget -qO- https://raw.githubusercontent.com/metisnc/pironman5-recalbox/main-pr5-rc/recalbox/install.sh | bash

set -euo pipefail

PM5_HOME="${PM5_HOME:-/recalbox/share/pironman5}"
BACKUP_ROOT="/recalbox/share/pironman5-backups"
CUSTOM_SH="/recalbox/share/system/custom.sh"
MARK_BEGIN="# >>> pironman5-recalbox >>>"
MARK_END="# <<< pironman5-recalbox <<<"

# Source of this port, used when the script is not run from a repository copy
PM5_REPO="${PM5_REPO:-metisnc/pironman5-recalbox}"
PM5_REF="${PM5_REF:-main-pr5-rc}"

# Upstream SunFounder dependencies, pinned to tested commits
PM_AUTO_COMMIT="117f66567c6b5b74e588a02fa5c192fc69624b1f"        # pm_auto v2
SF_RPI_STATUS_COMMIT="06990abf5e72589257c74fe450012e02c253f59f"  # sf_rpi_status main

OFFLINE_DIR=""
VARIANT=""
while [ $# -gt 0 ]; do
    case "$1" in
        --offline) shift; OFFLINE_DIR="${1:-}" ;;
        --variant) shift; VARIANT="${1:-}" ;;
        --variant=*) VARIANT="${1#*=}" ;;
        -h|--help) sed -n '/^# Pironman 5 installer/,/^$/p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

log() { echo "[pironman5] $*"; }
die() { echo "[pironman5] ERROR: $*" >&2; exit 1; }

# ------------------------------------------------------------------ checks
[ "$(id -u)" = 0 ] || die "run as root"
[ -f /recalbox/recalbox.version ] || die "this installer is for Recalbox only"
grep -qa "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null || die "Raspberry Pi 5 required"
python3 -c 'import sys; sys.exit(sys.version_info[:2] != (3, 11))' \
    || die "Python 3.11 required (wheels are built for cp311), found $(python3 --version 2>&1)"
for module in PIL psutil pyudev venv; do
    python3 -c "import $module" 2>/dev/null || die "Python module '$module' missing from Recalbox"
done
if ! grep -qa "Pironman 5" /proc/device-tree/hat/product 2>/dev/null; then
    log "WARNING: Pironman 5 HAT EEPROM not detected, I2C/SPI may be disabled"
fi
if [ -n "$OFFLINE_DIR" ]; then
    [ -d "$OFFLINE_DIR/wheels" ] || die "offline bundle: $OFFLINE_DIR/wheels not found"
fi
log "Recalbox $(cat /recalbox/recalbox.version), $(python3 --version)"

# ------------------------------------------------------------------ case model
# The HAT EEPROM reads "Pironman 5" on both models: ask which one this is.
variant_name() { case "$1" in max) echo "Pironman 5 Max" ;; *) echo "Pironman 5" ;; esac; }
LANG_FR=false
grep -q '^system.language=fr' /recalbox/share/system/recalbox.conf 2>/dev/null && LANG_FR=true
say() { if [ "$LANG_FR" = true ]; then echo "$1"; else echo "$2"; fi; }

DEFAULT_VARIANT=$(cat "$PM5_HOME/variant" 2>/dev/null || true)
case "$DEFAULT_VARIANT" in base|max) ;; *) DEFAULT_VARIANT=base ;; esac

if [ -n "$VARIANT" ]; then
    case "$VARIANT" in base|max) ;; *) die "--variant must be base or max" ;; esac
elif { exec 3</dev/tty; } 2>/dev/null; then
    # Interactive, also through "wget ... | bash": read the keyboard, not stdin
    default_choice=1; [ "$DEFAULT_VARIANT" = max ] && default_choice=2
    while [ -z "$VARIANT" ]; do
        echo
        say "Quel modèle de boîtier ?" "Which case model?"
        echo "  1) Pironman 5"
        say "  2) Pironman 5 Max (LEDs sur les ventilateurs)" "  2) Pironman 5 Max (LEDs on the case fans)"
        printf '%s' "$(say "Choix" "Choice") [$default_choice] : "
        read -r choice <&3 || choice=""
        case "${choice:-$default_choice}" in
            1) candidate=base ;;
            2) candidate=max ;;
            *) say "Choix invalide, tapez 1 ou 2." "Invalid choice, type 1 or 2."; continue ;;
        esac
        printf '%s' "$(say "Installer pour le $(variant_name "$candidate") ? [O/n] " \
                           "Install for the $(variant_name "$candidate")? [Y/n] ")"
        read -r confirm <&3 || confirm=""
        case "$confirm" in
            ""|[oOyY]*) VARIANT=$candidate ;;
            *) ;;  # ask again
        esac
    done
    exec 3<&-
else
    VARIANT=$DEFAULT_VARIANT
    log "No terminal: using $(variant_name "$VARIANT") (use --variant base|max to choose)"
fi
log "Case model: $(variant_name "$VARIANT")"

WORK=$(mktemp -d /tmp/pironman5-install.XXXXXX)
cleanup() {
    case "$WORK" in /tmp/pironman5-install.*) rm -rf "$WORK" ;; esac
}
trap cleanup EXIT
STAGE="$WORK/stage"
mkdir -p "$STAGE/app" "$STAGE/lib"

# ------------------------------------------------------------------ backup
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$STAMP"
mkdir -p "$BACKUP_DIR"
log "Backup to $BACKUP_DIR"
for f in /boot/config.txt /boot/recalbox-user-config.txt "$CUSTOM_SH" "$PM5_HOME/config.json"; do
    [ -f "$f" ] && cp "$f" "$BACKUP_DIR/"
done
[ -f "$CUSTOM_SH" ] || touch "$BACKUP_DIR/.custom_sh_absent"

# ------------------------------------------------------------------ fetch
download() {  # url dest
    wget -q -O "$2" "$1" || curl -fsSL -o "$2" "$1" || die "download failed: $1"
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd) || SCRIPT_DIR=""
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../pironman5/pironman5.py" ]; then
    SRC=$(cd "$SCRIPT_DIR/.." && pwd)
    log "Using local source $SRC"
elif [ -n "$OFFLINE_DIR" ] && [ -f "$OFFLINE_DIR/pironman5-recalbox.tar.gz" ]; then
    tar -xzf "$OFFLINE_DIR/pironman5-recalbox.tar.gz" -C "$WORK"
    SRC=$(find "$WORK" -maxdepth 1 -type d -name 'pironman5-recalbox*' | head -1)
else
    log "Downloading $PM5_REPO@$PM5_REF"
    download "https://codeload.github.com/$PM5_REPO/tar.gz/$PM5_REF" "$WORK/src.tar.gz"
    tar -xzf "$WORK/src.tar.gz" -C "$WORK"
    SRC=$(find "$WORK" -maxdepth 1 -type d -name 'pironman5-recalbox*' | head -1)
fi
[ -f "$SRC/pironman5/pironman5.py" ] || die "pironman5 source not found"

extract_package() {  # repo commit package
    local archive="$WORK/$1.tar.gz"
    if [ -n "$OFFLINE_DIR" ]; then
        cp "$OFFLINE_DIR/$1-$2.tar.gz" "$archive" || die "offline bundle: $1-$2.tar.gz missing"
    else
        download "https://codeload.github.com/sunfounder/$1/tar.gz/$2" "$archive"
    fi
    tar -xzf "$archive" -C "$WORK"
    [ -d "$WORK/$1-$2/$3" ] || die "$3 not found in $1 archive"
    cp -r "$WORK/$1-$2/$3" "$STAGE/lib/"
}
log "Fetching pm_auto ${PM_AUTO_COMMIT:0:7} and sf_rpi_status ${SF_RPI_STATUS_COMMIT:0:7}"
extract_package pm_auto "$PM_AUTO_COMMIT" pm_auto
extract_package sf_rpi_status "$SF_RPI_STATUS_COMMIT" sf_rpi_status

# ------------------------------------------------------------------ wheels
# pip is not part of Recalbox: use a throwaway venv in /tmp (tmpfs) only to
# run pip, then copy the result to the share partition. Installing straight
# to exFAT would fail on chmod/symlinks.
log "Installing Python dependencies (prebuilt wheels only)"
python3 -m venv "$WORK/venv"
PIP_ARGS=(--disable-pip-version-check --no-cache-dir --no-deps --only-binary=:all:
          --require-hashes --target "$STAGE/lib" -r "$SRC/recalbox/requirements-recalbox.txt")
if [ -n "$OFFLINE_DIR" ]; then
    PIP_ARGS+=(--no-index --find-links "$OFFLINE_DIR/wheels")
fi
"$WORK/venv/bin/python" -m pip install -q "${PIP_ARGS[@]}"
rm -rf "$STAGE/lib/bin"

cp -r "$SRC/pironman5" "$STAGE/app/"
mkdir -p "$STAGE/app/recalbox"
cp "$SRC/recalbox/"*.py "$SRC/recalbox/"*.sh "$SRC/recalbox/"*.txt "$SRC/recalbox/README.md" "$STAGE/app/recalbox/"
cp -r "$SRC/recalbox/pm5r" "$STAGE/app/recalbox/"
find "$STAGE" -name '__pycache__' -prune -exec rm -rf {} +
echo "$(cd "$SRC" && (git rev-parse --short HEAD 2>/dev/null || echo "$PM5_REF")) $STAMP" > "$STAGE/app/.installed"

# ------------------------------------------------------------------ install
if [ -f "$PM5_HOME/app/recalbox/pironman5-service.sh" ]; then
    log "Stopping running service"
    bash "$PM5_HOME/app/recalbox/pironman5-service.sh" stop || true
fi
if [ -d "$PM5_HOME" ] && [ ! -f "$PM5_HOME/app/.installed" ]; then
    # Folder from another (manual) port: keep it aside, reuse its settings
    log "Moving existing $PM5_HOME (not created by this installer) to $BACKUP_DIR/previous-pironman5"
    mv "$PM5_HOME" "$BACKUP_DIR/previous-pironman5"
    mkdir -p "$PM5_HOME"
    if [ -f "$BACKUP_DIR/previous-pironman5/config.json" ]; then
        cp "$BACKUP_DIR/previous-pironman5/config.json" "$PM5_HOME/config.json"
        log "Reusing its config.json"
    fi
fi
mkdir -p "$PM5_HOME"
for d in app lib; do
    if [ -d "$PM5_HOME/$d" ]; then
        mv "$PM5_HOME/$d" "$BACKUP_DIR/$d"   # previous version, kept for rollback
    fi
    cp -r "$STAGE/$d" "$PM5_HOME/$d"
done
mkdir -p "$PM5_HOME/logs"
echo "$VARIANT" > "$PM5_HOME/variant"   # read by the launcher and the menu

# ------------------------------------------------------------------ autostart
if ! grep -qF "$MARK_BEGIN" "$CUSTOM_SH" 2>/dev/null; then
    log "Adding autostart block to $CUSTOM_SH"
    if [ ! -f "$CUSTOM_SH" ]; then
        printf '#!/bin/bash\n' > "$CUSTOM_SH"
    elif [ -n "$(tail -c 1 "$CUSTOM_SH")" ]; then
        echo >> "$CUSTOM_SH"
    fi
    cat >> "$CUSTOM_SH" <<EOF
$MARK_BEGIN
bash "$PM5_HOME/app/recalbox/pironman5-service.sh" "\$1"
$MARK_END
EOF
fi

# ------------------------------------------------------------------ menu
# Entries in Recalbox menu > User scripts (named in the Recalbox language)
log "Adding the Pironman entries to the Recalbox user scripts menu"
python3 "$PM5_HOME/app/recalbox/pironman5ctl.py" install-scripts

bash "$PM5_HOME/app/recalbox/pironman5-service.sh" start
log "Installed in $PM5_HOME (backup: $BACKUP_DIR)"
log "Status:    bash $PM5_HOME/app/recalbox/pironman5-service.sh status"
log "Uninstall: bash $PM5_HOME/app/recalbox/uninstall.sh"
