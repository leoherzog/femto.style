#!/bin/bash
# The owner's Safari steps, for the owner to run at the Mac (tests/README.md, Owner's Safari steps).
# Safari runs the behavior suite in the OS's appearance and motion only, since WebDriver cannot
# emulate either there, so this script switches macOS to Light, then to Dark, and puts back the
# appearance it found, even when stopped with Ctrl-C. Quit Safari first, keep the screen unlocked and
# leave the Mac alone until it prints "done": the behavior suite drives Safari with real input, which
# needs the automation window in front.
#
# Each mode refuses to start when a result folder it would write already exists, so no rerun
# overwrites a pass's evidence; N (default 1) numbers the run ids, as in `tests/owner-safari.sh final 2`.
#
#   tests/owner-safari.sh final [N]    criteria 7 and 15 at this commit: builds dist/, then runs the
#                                      behavior suite against it in Light (behavior-safari-light-N),
#                                      then in Dark (behavior-safari-dark-N). The suite's loads group is
#                                      criterion 15's run-time half: in Safari it reads the pages' own
#                                      performance entries (Safari has no WebDriver BiDi, so no request
#                                      log). Reduce Motion must be off. About 10 minutes.
#   tests/owner-safari.sh reduced [N]  the owner's decision of 2026-11-06: the behavior suite against
#                                      dist/ in Light only, with macOS's Reduce Motion on, so Safari runs
#                                      the prefers-reduced-motion checks the final passes skip
#                                      (behavior-safari-reduced-light-N). Both of them are light checks
#                                      (demo-reduced-motion and spy-nav-click-reduced), so a Dark pass
#                                      would run none. Turn Reduce Motion on first, in System Settings >
#                                      Accessibility > Display > Reduce motion; the script stops if the
#                                      harness reports another OS motion, and reminds you to turn it
#                                      off. About 2 minutes.
#
# The durations come from the earlier Safari passes (tests/README.md, Owner's Safari steps): the
# behavior suite took 411 s in Light and 12 s in Dark (p4-behavior-safari-*-2), before the loads
# group was added.
set -u
cd "$(dirname "$0")/.." || exit 1

only=${1:-}
n=${2:-1}

case "$only" in
  final|reduced) ;;
  *) echo "usage: $0 final|reduced [N]"
     exit 2 ;;
esac
case "$n" in
  ""|0*|*[!0-9]*) echo "usage: $0 $only [N]: N numbers the run ids, 1 or more"; exit 2 ;;
esac

# The run id a mode writes in one appearance.
id_for() {
  case "$only" in
    final) echo "behavior-safari-$1-$n" ;;
    reduced) [ "$1" = light ] && echo "behavior-safari-reduced-$1-$n" ;;
  esac
}
schemes="light dark"
[ "$only" = reduced ] && schemes=light
for scheme in $schemes; do
  id=$(id_for $scheme)
  if [ -e "tests/results/$id" ]; then
    echo "tests/results/$id exists, an earlier pass's evidence: run tests/owner-safari.sh $only $((n + 1))"
    exit 1
  fi
done

if pgrep -xq Safari; then echo "Quit Safari (Cmd-Q) first."; exit 1; fi

appearance() {
  osascript -e "tell application \"System Events\" to tell appearance preferences to set dark mode to $1"
  sleep 5
}
run() {
  echo "$(date +%T) $*"
  caffeinate -d -i "$@"
  local status=$?
  echo "$(date +%T) exit $status"
  return $status
}

ids=
# Each session should say "OS scheme light" in the light runs and "OS scheme dark" in the dark one
# (an error's "the OS scheme is ..." is not counted), and "OS motion no-preference" in the final runs
# and "OS motion reduce" in the reduced one.
report() {
  for id in $ids; do
    log="tests/results/$id/log.txt"
    line=$(grep -oE 'OS scheme (light|dark)' "$log" 2>/dev/null | sort | uniq -c | xargs)
    line="$line; $(grep -oE 'OS motion (reduce|no-preference)' "$log" 2>/dev/null | sort | uniq -c | xargs)"
    echo "$id: $line"
  done
}
# Stops the script when the run $1 did not report Safari's OS motion as $2. A run whose log has no
# OS motion at all started no Safari session (its HARNESS ERRORS say why), so the motion is unknown.
motion_is() {
  log="tests/results/$1/log.txt"
  if ! grep -q "OS motion" "$log" 2>/dev/null; then
    echo "$(date +%T) stopped: $1 started no Safari session, so it ran no check (its HARNESS ERRORS" \
      "above say why; Reduce Motion is not the cause). Fix that, then run tests/owner-safari.sh $only $((n + 1))."
    report
    exit 1
  fi
  if ! grep -q "OS motion $2" "$log"; then
    echo "$(date +%T) stopped: $1 did not report Safari's OS motion as $2. Turn Reduce Motion" \
      "$([ "$2" = reduce ] && echo on || echo off) (System Settings > Accessibility > Display > Reduce motion)," \
      "then run tests/owner-safari.sh $only $((n + 1))."
    report
    exit 1
  fi
}

was_dark=$(osascript -e 'tell application "System Events" to tell appearance preferences to get dark mode')
cleanup() {
  appearance "$was_dark"
  if [ "$only" = reduced ]; then
    echo "Turn Reduce Motion off again: System Settings > Accessibility > Display > Reduce motion."
  fi
}
trap cleanup EXIT

# The harness serves dist/ as it finds it, so the site is built first.
run npm run build || exit 1

motion=no-preference
[ "$only" = reduced ] && motion=reduce
for scheme in $schemes; do
  if [ $scheme = light ]; then appearance false; else appearance true; fi
  id=$(id_for $scheme)
  ids="$ids $id"
  # final: criteria 7 and 15, every check of this appearance and of no-preference motion. reduced:
  # only the checks whose motion is reduce run, both light ones; every other check is skipped as
  # motion:no-preference (it ran in the final passes) or, the dark ones, as media:dark.
  run uv run tests/run.py behavior --target dist --browsers safari --expect-os-motion $motion --run-id "$id"
  motion_is "$id" $motion
done

report
echo "$(date +%T) done"
