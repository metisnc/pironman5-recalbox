#!/bin/bash
# Copyright (C) 2026 metisnc
# SPDX-License-Identifier: GPL-2.0-only
# Pironman 5 service control for Recalbox.
# Called at boot/shutdown by /recalbox/share/system/custom.sh (via S99custom).
#
# Usage: bash pironman5-service.sh start|stop|restart|status

PM5_HOME="${PM5_HOME:-/recalbox/share/pironman5}"
PIDFILE="/var/run/pironman5.pid"
LOG_DIR="${PM5_HOME}/logs"
LAUNCHER="${PM5_HOME}/app/recalbox/pironman5_recalbox.py"
STOP_TIMEOUT=10

is_running() {
    local pid
    [ -f "$PIDFILE" ] || return 1
    pid=$(cat "$PIDFILE" 2>/dev/null)
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start() {
    if is_running; then
        echo "pironman5 already running (pid $(cat "$PIDFILE"))"
        return 0
    fi
    if [ ! -f "$LAUNCHER" ]; then
        echo "pironman5 not installed: $LAUNCHER missing" >&2
        return 1
    fi
    # /dev/i2c-1 for the OLED; I2C1 and SPI0 are enabled by the overlay the
    # firmware loads from the Pironman 5 HAT EEPROM.
    modprobe i2c-dev 2>/dev/null
    mkdir -p "$LOG_DIR"
    # Run from /tmp: lgpio creates FIFOs in its working directory, which
    # exFAT (/recalbox/share) does not support.
    cd /tmp || return 1
    export PM5_HOME
    PYTHONPATH="${PM5_HOME}/app:${PM5_HOME}/lib" LG_WD=/tmp \
        setsid nice -n 10 python3 -u "$LAUNCHER" \
        > "${LOG_DIR}/console.log" 2>&1 < /dev/null &
    echo $! > "$PIDFILE"
    sleep 1
    if is_running; then
        echo "pironman5 started (pid $(cat "$PIDFILE"))"
    else
        echo "pironman5 failed to start, see ${LOG_DIR}/console.log" >&2
        rm -f "$PIDFILE"
        return 1
    fi
}

stop() {
    local pid _
    if ! is_running; then
        echo "pironman5 not running"
        rm -f "$PIDFILE"
        return 0
    fi
    pid=$(cat "$PIDFILE")
    # SIGTERM lets the service switch off the OLED, LEDs and case fans
    kill -TERM "$pid"
    for _ in $(seq 1 "$STOP_TIMEOUT"); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
        echo "pironman5 did not stop after ${STOP_TIMEOUT}s, killing" >&2
        kill -KILL "$pid"
    fi
    rm -f "$PIDFILE"
    echo "pironman5 stopped"
}

status() {
    if is_running; then
        echo "pironman5 running (pid $(cat "$PIDFILE"))"
    else
        echo "pironman5 not running"
    fi
    # Boot hook sanity checks (useful after a Recalbox upgrade)
    [ -f /etc/init.d/S99custom ] || echo "WARNING: /etc/init.d/S99custom missing, no autostart"
    grep -q "pironman5-recalbox" /recalbox/share/system/custom.sh 2>/dev/null \
        || echo "WARNING: autostart block missing in /recalbox/share/system/custom.sh"
    [ -e /dev/i2c-1 ] || echo "WARNING: /dev/i2c-1 missing (OLED)"
    [ -e /dev/spidev0.0 ] || echo "WARNING: /dev/spidev0.0 missing (RGB LEDs)"
    is_running
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
    status) status ;;
    *) echo "Usage: $0 start|stop|restart|status" >&2; exit 2 ;;
esac
