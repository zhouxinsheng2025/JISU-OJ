#!/bin/bash
# Memory monitor — poll RSS periodically, output max seen
# Usage: mem_monitor.sh <interval_sec> <pid>
# Outputs max RSS in KB, one line per sample
INTERVAL=${1:-0.1}
PID=${2:-1}

max_rss=0
while kill -0 $PID 2>/dev/null; do
    rss=$(awk '/VmRSS/{print $2}' /proc/$PID/status 2>/dev/null)
    if [ -n "$rss" ] && [ "$rss" -gt "$max_rss" ]; then
        max_rss=$rss
    fi
    sleep "$INTERVAL"
done
echo "$max_rss"
