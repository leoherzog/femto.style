#!/bin/bash
# The owner's Safari steps, for the owner to run at the Mac (tests/README.md, Owner's Safari steps):
# Phase 0's remaining ones, Phase 2's styles gate and Phase 3's gate. It switches macOS to Light, then to Dark, and
# puts back the appearance it found, even when stopped with Ctrl-C. Quit Safari first, keep the
# screen unlocked and leave the Mac alone until it prints "done": /docs/css-variables, rig's input
# checks, the spike, the styles mode's state replays and the behavior suite need the automation window
# in front.
#
#   tests/owner-safari.sh         Phase 0's steps below (about 70 minutes)
#   tests/owner-safari.sh dark    only Phase 0's dark self pass, under a new run id (about 26 minutes)
#   tests/owner-safari.sh spike   only the spike, on whichever appearance is set (about 1 minute)
#   tests/owner-safari.sh styles  Phase 2's styles gate in Light, then in Dark (about 65 minutes)
#   tests/owner-safari.sh one-page  Phase 3's gate in Light, then in Dark: the behavior suite, the full
#                                   section comparison and the whole-page comparisons (about 1 h 45 min)
set -u
cd "$(dirname "$0")/.." || exit 1

only=${1:-}
case "$only" in
  "") dark_id=p0-self-safari-dark ;;
  dark) dark_id=p0-self-safari-dark-masked ;;
  spike|styles|one-page) ;;
  *) echo "usage: $0 [dark|spike|styles|one-page]"; exit 2 ;;
esac

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

spike() {
  python3 -I docs/research/spike/serve.py 8794 >/dev/null 2>&1 &
  srv=$!
  sleep 1
  run uv run docs/research/spike/test_spike.py 8794 safari --probes 2>&1 | tee "tests/results/$1"
  kill "$srv" 2>/dev/null
  wait "$srv" 2>/dev/null
  srv=
}

srv=
if [ "$only" = spike ]; then
  trap '[ -n "$srv" ] && kill "$srv" 2>/dev/null' EXIT
  spike p0-spike-safari-2.txt
  echo "$(date +%T) done"
  exit
fi

was_dark=$(osascript -e 'tell application "System Events" to tell appearance preferences to get dark mode')
trap '[ -n "$srv" ] && kill "$srv" 2>/dev/null; appearance "$was_dark"' EXIT

if [ "$only" = styles ]; then
  # Phase 2's gate (criterion 2): the tag static-multipage against dist over the full matrix, once
  # per appearance. Each run compares the OS scheme's leg and both theme legs, 420 of Safari's 744
  # cells, and registers the other scheme's leg as the skipped check media:<scheme>. The harness
  # serves dist/ as it finds it, so the site is built first.
  run npm run build || exit 1
  appearance false
  run uv run tests/run.py styles --full --browsers safari --run-id p2-styles-safari-light-3
  appearance true
  run uv run tests/run.py styles --full --browsers safari --run-id p2-styles-safari-dark-3
  ids="p2-styles-safari-light-3 p2-styles-safari-dark-3"
elif [ "$only" = one-page ]; then
  # Phase 3's gate in Safari (PLAN.md Workflow, 3 One page; criteria 2 and 7), once per appearance:
  # the behavior suite against dist (the checks whose media is the other scheme are skipped and run in
  # the other pass), the section comparison of every old docs route of static-femto against its
  # section of the one page over the full matrix (384 of Safari's 684 cells per pass: the OS scheme's
  # leg and both theme legs), and the whole pages whose links into the docs changed. The harness
  # serves dist/ as it finds it, so the site is built first; static-femto is the harness's own build.
  run npm run build || exit 1
  for scheme in light dark; do
    if [ $scheme = light ]; then appearance false; else appearance true; fi
    run uv run tests/run.py behavior --target dist --browsers safari --run-id "p3-behavior-safari-$scheme-1"
    run uv run tests/run.py sections --full --browsers safari --run-id "p3-sections-safari-$scheme-1"
    run uv run tests/run.py pages --a static-femto --b dist --full --browsers safari \
      --routes /,/examples,/demo,/does-not-exist --run-id "p3-pages-safari-$scheme-1"
  done
  ids="p3-sections-safari-light-1 p3-pages-safari-light-1 p3-sections-safari-dark-1 p3-pages-safari-dark-1"
  for id in p3-behavior-safari-light-1 p3-behavior-safari-dark-1; do
    echo "$id: $(grep -o 'OS scheme [a-z]*' "tests/results/$id/log.txt" | sort | uniq -c | xargs)"
  done
else
  # Light: the spike (Safari column of docs/research/05-spike.md), rig's input checks, and the six
  # light /docs/css-variables cells (the other 53 routes passed locked in owner-self-safari-light).
  if [ -z "$only" ]; then
    appearance false
    spike p0-spike-safari.txt
    run uv run tests/run.py rig --browsers safari --run-id p0-rig-safari-unlocked
    run uv run tests/run.py self --full --browsers safari --routes /docs/css-variables --run-id p0-self-safari-light-cssvars
  fi

  # Dark: every kept route on the current harness, then the selftest controls that compare on a dark
  # OS (the others are pinned to the light leg and ran in owner-selftest-safari-light).
  appearance true
  run uv run tests/run.py self --full --browsers safari --run-id "$dark_id"
  [ -z "$only" ] && run uv run tests/run.py selftest --browsers safari --cases self,dark-only,theme-dark-only --run-id p0-selftest-safari-dark

  ids=$dark_id
  [ -z "$only" ] && ids="p0-self-safari-light-cssvars $dark_id"
fi

# Each session should say "OS scheme light" in the light run and "OS scheme dark" in the dark one.
for id in $ids; do
  echo "$id: $(grep -o 'OS scheme [a-z]*' "tests/results/$id/log.txt" | sort | uniq -c | xargs)"
done
echo "$(date +%T) done"
