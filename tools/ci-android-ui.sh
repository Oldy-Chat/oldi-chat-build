#!/usr/bin/env bash
set -euo pipefail
mkdir -p build/ui-report
collect_report() {
  adb logcat -d -s AndroidRuntime:E Oldi066Fixture:I > build/ui-report/android-errors.txt || true
  adb pull /sdcard/Android/data/chat.oldy/files/review/. build/ui-report/ || true
  adb exec-out screencap -p > build/ui-report/final-screen.png || true
}
trap collect_report EXIT
adb install -r app/build/outputs/apk/release/app-release.apk
adb install -r app/build/outputs/apk/androidTest/release/app-release-androidTest.apk
adb shell pm grant chat.oldy android.permission.POST_NOTIFICATIONS
# The test configures the chat endpoint as loopback before installing its local fixtures.
timeout 150s adb shell am instrument -w chat.oldy.tests/chat.oldy.Release066Instrumentation | tee build/ui-report/result.txt
grep -q OLDI_066_UI_PASS build/ui-report/result.txt
