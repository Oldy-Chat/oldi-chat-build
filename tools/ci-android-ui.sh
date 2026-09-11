#!/usr/bin/env bash
set -euo pipefail
mkdir -p build/ui-report
adb install -r app/build/outputs/apk/release/app-release.apk
adb install -r app/build/outputs/apk/androidTest/release/app-release-androidTest.apk
adb shell pm grant chat.oldy android.permission.POST_NOTIFICATIONS
# The test configures the chat endpoint as loopback before installing its local fixtures.
timeout 150s adb shell am instrument -w chat.oldy.tests/chat.oldy.Release066Instrumentation | tee build/ui-report/result.txt
grep -q OLDI_066_UI_PASS build/ui-report/result.txt
adb pull /sdcard/Android/data/chat.oldy/files/review/. build/ui-report/
