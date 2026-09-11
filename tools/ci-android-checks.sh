#!/usr/bin/env bash
set -uo pipefail
# Collect both independent results; either failed suite still fails the job.
bash tools/ci-android-ui.sh
ui_result=$?
python3 tools/aeza/verify_android_route.py
media_result=$?
printf 'Android checks: menus=%s media=%s\n' "$ui_result" "$media_result"
test "$ui_result" -eq 0 && test "$media_result" -eq 0
