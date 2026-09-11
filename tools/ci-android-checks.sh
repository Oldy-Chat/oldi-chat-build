#!/usr/bin/env bash
set -uo pipefail
# Collect both independent results; either failed suite still fails the job.
bash tools/ci-android-ui.sh
ui_result=$?
timeout 100s adb shell am instrument -w chat.oldy.tests/chat.oldy.ConversationFeaturesInstrumentation | tee build/ui-report/conversation.txt
grep -q OLDI_CONVERSATION_PASS build/ui-report/conversation.txt
conversation_result=$?
adb logcat -d -b crash > build/ui-report/conversation-errors.txt
timeout 100s adb shell am instrument -w chat.oldy.tests/chat.oldy.MessageEditsInstrumentation | tee build/ui-report/edits.txt
grep -q OLDI_EDITS_PASS build/ui-report/edits.txt
edits_result=$?
timeout 900s adb shell am instrument -w chat.oldy.tests/chat.oldy.SpeechInstrumentation | tee build/ui-report/speech.txt
grep -q OLDI_SPEECH_PASS build/ui-report/speech.txt
speech_result=$?
python3 tools/ci-video-conference.py
conference_result=$?
python3 tools/aeza/verify_android_route.py
media_result=$?
printf 'Android checks: menus=%s media=%s\n' "$ui_result" "$media_result"
test "$edits_result" -eq 0 && test "$conference_result" -eq 0 && test "$ui_result" -eq 0 && test "$conversation_result" -eq 0 && test "$speech_result" -eq 0 && test "$media_result" -eq 0
