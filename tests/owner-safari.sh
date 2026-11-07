#!/bin/bash
# The owner's Safari steps, for the owner to run at the Mac (tests/README.md, Owner's Safari steps).
# It switches macOS to Light, then to Dark, and puts back the appearance it found, even when stopped
# with Ctrl-C. Quit Safari first, keep the screen unlocked and leave the Mac alone until it prints
# "done": /docs/css-variables, the styles mode's state replays, the behavior suite and the spike need
# the automation window in front.
#
# Phase 6's steps (PLAN.md Workflow, 6 Final review). Each refuses to start when a result folder it
# would write already exists, so no rerun overwrites a pass's evidence; N (default 1) numbers the run
# ids, as in `tests/owner-safari.sh final 2`.
#
#   tests/owner-safari.sh final [N]    criteria 1, 7 and 15 at this commit, in Light, then in Dark:
#                                      builds dist/, then the behavior suite against it
#                                      (p6-behavior-safari-<scheme>-N), self --full over every kept
#                                      route (p6-self-safari-<scheme>-N) and the run-time loads, pages
#                                      --a dist --b dist --full (p6-loads-safari-<scheme>-N). Reduce
#                                      Motion must be off. About 1 h 25 min.
#   tests/owner-safari.sh reduced [N]  owner decision 4 (2026-11-06): the behavior suite against dist/
#                                      in Light only, with macOS's Reduce Motion on, so Safari runs the
#                                      prefers-reduced-motion checks the final passes skip
#                                      (p6-behavior-safari-reduced-light-N). Every one of them is a light
#                                      check (demo-reduced-motion, spy-nav-click-reduced and
#                                      progress-reduced-motion), so a Dark pass would run none. Turn
#                                      Reduce Motion on first, in System Settings > Accessibility >
#                                      Display > Reduce motion; the script stops if the harness reports
#                                      another OS motion, and reminds you to turn it off. About 2 minutes.
#   tests/owner-safari.sh parity [N]   owner decision 3 (2026-11-06), criterion 2's Safari legs, rerun
#                                      on the current harness between the commits the gates compared,
#                                      in Light, then in Dark: Phase 2's styles --full, static-multipage
#                                      against static-femto (p6-styles-safari-<scheme>-N), and Phase 3's
#                                      sections --full (p6-sections-safari-<scheme>-N) and pages --full
#                                      over /, /examples, /demo and /does-not-exist
#                                      (p6-pages-safari-<scheme>-N), static-femto against
#                                      static-one-page. The harness builds the tags, and its Safari
#                                      session refuses to compare under Reduce Motion: the script stops
#                                      after the first styles run unless it reports OS motion
#                                      no-preference. About 2 h 40 min.
#   tests/owner-safari.sh spike [N]    only the spike, into results/p6-spike-safari-N.txt, on whichever
#                                      appearance is set. About 1 minute.
#
# The durations come from the earlier Safari passes (tests/README.md, Owner's Safari steps and Harness
# proof): the behavior suite took 411 s in Light and 12 s in Dark (p4-behavior-safari-*-2); a dark
# self --full pass 1,548 s (p0-self-safari-dark-masked); a light one 1,072 s without
# /docs/css-variables (owner-self-safari-light) and 1,178 s for that route's six light cells
# (p0-self-safari-light-cssvars); a styles --full pass 1,910 to 1,936 s (p2-styles-safari-*-2). The
# section comparison has never run in Safari: Phase 3 estimated about 45 minutes for a sections pass
# (384 cells, six of them /docs/css-variables at about 190 s each). A pages pass of 36 cells (parity)
# or 54 (final's loads, /docs among them) is estimated at a few minutes.
#
# Historical modes, kept for the record; each now refuses to run and says what it ran:
#   tests/owner-safari.sh, tests/owner-safari.sh dark   Phase 0's steps, under Phase 0's run ids
#   tests/owner-safari.sh styles | one-page | content   Phases 2, 3 and 4's Safari gates, which compared
#                                                       HEAD's dist/ with the tags or wrote Phase 4's ids
set -u
cd "$(dirname "$0")/.." || exit 1

only=${1:-}
n=${2:-1}

historical() {
  echo "tests/owner-safari.sh ${only:-(no argument)} is historical, kept for the record: $1" >&2
  echo "Run tests/owner-safari.sh final, reduced or parity instead (tests/README.md, Owner's Safari steps)." >&2
  exit 2
}

case "$only" in
  final|reduced|parity|spike) ;;
  ""|dark) historical "Phase 0's steps. With no argument it ran the spike (results/p0-spike-safari.txt), \
rig with its input checks (p0-rig-safari-unlocked), the six light /docs/css-variables cells \
(p0-self-safari-light-cssvars), the dark self pass (p0-self-safari-dark) and the selftest controls \
that compare on a dark OS (p0-selftest-safari-dark); dark ran only the dark self pass, as \
p0-self-safari-dark-masked. A rerun would overwrite that evidence. final reruns criterion 1's self \
--full pass on the current harness, in Light and in Dark, under Phase 6's run ids." ;;
  styles) historical "Phase 2's gate: npm run build, then styles --full --browsers safari (dist against \
static-multipage) in Light and in Dark, as p2-styles-safari-light-3 and -dark-3. From Phase 4 HEAD's \
dist/ describes femto 3 (PLAN.md Decision 6), so it cannot match static-multipage. parity compares \
static-multipage with static-femto, the Phase 2 site." ;;
  one-page) historical "Phase 3's gate: npm run build, then in each appearance behavior --target dist \
(p3-behavior-safari-<scheme>-1), sections --full (dist against static-femto, p3-sections-safari-<scheme>-1) \
and pages --a static-femto --b dist --full --routes /,/examples,/demo,/does-not-exist \
(p3-pages-safari-<scheme>-1). From Phase 4 HEAD's dist/ cannot match static-femto, and /demo is not \
built. parity compares static-femto with static-one-page, the Phase 3 commit, and final runs the \
behavior suite at this commit." ;;
  content) historical "Phase 4's Safari pass of criterion 7: npm run build, then behavior --target dist \
--browsers safari in Light and in Dark, as p4-behavior-safari-light-2 and -dark-2, Phase 4's record, \
which a rerun would overwrite. final runs the behavior suite under Phase 6's run ids." ;;
  *) echo "usage: $0 final|reduced|parity|spike [N]   (historical, refused: no argument, dark, styles, one-page, content)"
     exit 2 ;;
esac
case "$n" in
  ""|0*|*[!0-9]*) echo "usage: $0 $only [N]: N numbers the run ids, 1 or more"; exit 2 ;;
esac

# The run ids a mode writes in one appearance.
ids_for() {
  case "$only" in
    final) echo "p6-behavior-safari-$1-$n p6-self-safari-$1-$n p6-loads-safari-$1-$n" ;;
    reduced) [ "$1" = light ] && echo "p6-behavior-safari-reduced-$1-$n" ;;
    parity) echo "p6-styles-safari-$1-$n p6-sections-safari-$1-$n p6-pages-safari-$1-$n" ;;
  esac
}
if [ "$only" = spike ]; then
  planned="p6-spike-safari-$n.txt"
else
  planned="$(ids_for light) $(ids_for dark)"
fi
for id in $planned; do
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

srv=
if [ "$only" = spike ]; then
  trap '[ -n "$srv" ] && kill "$srv" 2>/dev/null' EXIT
  python3 -I docs/research/spike/serve.py 8794 >/dev/null 2>&1 &
  srv=$!
  sleep 1
  run uv run docs/research/spike/test_spike.py 8794 safari --probes 2>&1 | tee "tests/results/$planned"
  kill "$srv" 2>/dev/null
  wait "$srv" 2>/dev/null
  srv=
  echo "$(date +%T) done"
  exit
fi

ids=
# Each session should say "OS scheme light" in the light runs and "OS scheme dark" in the dark ones
# (an error's "the OS scheme is ..." is not counted), and "OS motion no-preference" in the final and
# parity runs and "OS motion reduce" in the reduced one. The behavior and comparison modes both log
# Safari's OS motion; a comparison session refuses to start under reduce.
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
  [ -n "$srv" ] && kill "$srv" 2>/dev/null
  appearance "$was_dark"
  if [ "$only" = reduced ]; then
    echo "Turn Reduce Motion off again: System Settings > Accessibility > Display > Reduce motion."
  fi
}
trap cleanup EXIT

# The harness serves dist/ as it finds it, so the site is built first; parity serves only the tags,
# which the harness builds into tests/builds/.
if [ "$only" != parity ]; then
  run npm run build || exit 1
fi

# reduced runs in Light only: every prefers-reduced-motion check is a light one.
schemes="light dark"
[ "$only" = reduced ] && schemes=light
for scheme in $schemes; do
  if [ $scheme = light ]; then appearance false; else appearance true; fi
  ids="$ids $(ids_for $scheme)"
  case "$only" in
    final)
      # Criterion 7, then 1 (the oracle against itself over the full matrix: the OS scheme's leg and
      # both theme legs here, the other scheme's leg in the other pass), then 15's run-time loads.
      run uv run tests/run.py behavior --target dist --browsers safari --expect-os-motion no-preference \
        --run-id "p6-behavior-safari-$scheme-$n"
      motion_is "p6-behavior-safari-$scheme-$n" no-preference
      run uv run tests/run.py self --full --browsers safari --run-id "p6-self-safari-$scheme-$n"
      run uv run tests/run.py pages --a dist --b dist --full --routes '/,/docs,/docs?theme=jade,/examples,/does-not-exist' \
        --browsers safari --run-id "p6-loads-safari-$scheme-$n"
      ;;
    reduced)
      # Only the checks whose motion is reduce run, all three light ones; every other check is skipped
      # as motion:no-preference (it ran in the final passes) or, the dark ones, as media:dark.
      run uv run tests/run.py behavior --target dist --browsers safari --expect-os-motion reduce \
        --run-id "p6-behavior-safari-reduced-$scheme-$n"
      motion_is "p6-behavior-safari-reduced-$scheme-$n" reduce
      ;;
    parity)
      # Phase 2's gate: the Phase 1 commit against the Phase 2 site. Phase 3's: each old docs route of
      # the Phase 2 site against its section of the Phase 3 one page, then the whole pages whose links
      # into the docs changed. Each pass runs the OS scheme's leg and both theme legs; the other
      # scheme's leg is the skipped check media:<scheme>, which the other pass runs.
      run uv run tests/run.py styles --full --a static-multipage --b static-femto --browsers safari \
        --run-id "p6-styles-safari-$scheme-$n"
      motion_is "p6-styles-safari-$scheme-$n" no-preference
      run uv run tests/run.py sections --full --a static-femto --b static-one-page --browsers safari \
        --run-id "p6-sections-safari-$scheme-$n"
      run uv run tests/run.py pages --full --a static-femto --b static-one-page --routes /,/examples,/demo,/does-not-exist \
        --browsers safari --run-id "p6-pages-safari-$scheme-$n"
      ;;
  esac
done

report
echo "$(date +%T) done"
