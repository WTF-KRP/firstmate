#!/usr/bin/env bash
# tests/fm-task-job.test.sh - task jobs (bin/fm-task-job.sh,
# bin/fm-task-job-lib.sh): a worker command that outlives its turn and whose
# exit reaches the task's steering inbox.
#
# The gap this closes: a worker ends its turn while its own monitoring command
# still runs, the command then finishes, and no turn follows, because the
# harness records the exit against the ended turn and nothing rings the worker.
# These tests pin the replacement with real processes and a fake terminal:
#   1. A finished command becomes one durable hold-aware inbox record keyed by
#      task, starting spawn generation, and job id, and its doorbell rings.
#   2. The record names the generation that started the job even after a
#      relaunch replaced it.
#   3. A command past its timeout is stopped with its whole process group.
#   4. A task holding an open decision of its own gets the record without a
#      ring, and the watcher's ladder leaves it unrung until the decision
#      closes, then rings it.
#   5. A doorbell that did not land is re-rung by the watcher until the worker
#      acknowledges the record.
#   6. A running watcher publishes a job whose runner died as lost, stops its
#      orphaned command, delivers it once, and never redelivers an
#      acknowledged completion.
#   7. Teardown's stop-all stops live jobs without delivering anything.
#   8. A job whose task inbox was removed never recreates it.
#   9. Start refuses without a task identity or a valid timeout.
set -u

# shellcheck source=tests/wake-helpers.sh
. "$(dirname "${BASH_SOURCE[0]}")/wake-helpers.sh"

JOB="$ROOT/bin/fm-task-job.sh"
WATCH="$ROOT/bin/fm-watch.sh"
TMP_ROOT=$(fm_test_tmproot fm-task-job)
TMP_ROOT=$(cd "$TMP_ROOT" && pwd)
DOORBELL="Firstmate instruction waiting: list \"\$FM_TASK_INBOX\"/*.msg in your 't1.inbox' steering inbox"

# A fake tmux: every literal send-keys is logged to FM_SEND_LOG so a doorbell
# is observable, FM_FAKE_TMUX_SEND_FAIL=1 makes sends fail, and capture-pane
# shows an idle composer box.
make_stubs() {  # <dir>
  local fb="$1/fakebin"
  mkdir -p "$fb"
  cat > "$fb/tmux" <<'SH'
#!/usr/bin/env bash
set -u
case "${1:-}" in
  send-keys)
    if [ "${FM_FAKE_TMUX_SEND_FAIL:-0}" = 1 ]; then
      printf 'send failed\n' >> "${FM_SEND_LOG:-/dev/null}"
      exit 1
    fi
    shift
    literal=0
    while [ $# -gt 0 ]; do
      case "$1" in
        -t) shift 2 ;;
        -l) literal=1; shift ;;
        *) break ;;
      esac
    done
    [ "$literal" = 0 ] || printf '%s\n' "${1:-}" >> "${FM_SEND_LOG:-/dev/null}"
    exit 0 ;;
  display-message)
    for a in "$@"; do
      case "$a" in *cursor_y*) printf '1\n'; exit 0 ;; esac
    done
    printf 'fakepane\n'; exit 0 ;;
  capture-pane) printf '╭────╮\n│    │\n╰────╯\n'; exit 0 ;;
  list-windows) printf 'fm-t1\n'; exit 0 ;;
esac
exit 0
SH
  chmod +x "$fb/tmux"
  make_fake_crew_state "$fb" >/dev/null
}

setup_case() {  # <name> -> echoes the case dir; task t1 lives in <dir>/state
  local dir="$TMP_ROOT/$1"
  mkdir -p "$dir/state/t1.inbox/handled"
  make_stubs "$dir"
  : > "$dir/send.log"
  fm_write_meta "$dir/state/t1.meta" "window=sess:fm-t1" "kind=ship" "harness=grok" "spawn_gen=gen-A"
  printf 'paused [at=1]: waiting for my own monitor\n' > "$dir/state/t1.status"
  printf '%s\n' "$dir"
}

# Start a task job the way a worker does: from the task's environment.
job_start() {  # <dir> <start args...>
  local dir=$1
  shift
  PATH="$dir/fakebin:$PATH" FM_TASK_INBOX="$dir/state/t1.inbox" FM_SEND_LOG="$dir/send.log" \
    "$JOB" start "$@"
}

start_waiting_job() {
  cat > "$1/wait.sh" <<'SH'
while [ ! -f "$1" ]; do sleep 0.1; done
SH
  job_start "$1" --timeout 60 -- sh "$1/wait.sh" "$1/release"
}

job_lib() {  # <dir> <function> [args...]
  local dir=$1
  shift
  PATH="$dir/fakebin:$PATH" FM_STATE_OVERRIDE="$dir/state" FM_SEND_LOG="$dir/send.log" bash -c '
    . "$1"
    fn=$2
    shift 2
    "$fn" "$@"
  ' _ "$ROOT/bin/fm-task-job-lib.sh" "$@"
}

# One watcher steering-inbox pass, as the poll loop runs it.
steer_check() {  # <dir>
  PATH="$1/fakebin:$PATH" FM_STATE_OVERRIDE="$1/state" FM_SEND_LOG="$1/send.log" \
    FM_TASK_INBOX_GRACE_SECS=1 \
    bash -c '. "$1" && inbox_steer_check sess:fm-t1 t1' _ "$WATCH" >/dev/null 2>&1
}

age_path() {  # <path>  (set mtime well past any grace under test)
  touch -t 202001010000 "$1"
}

records() {  # <dir> -> unhandled record paths, one per line
  local f
  for f in "$1/state/t1.inbox"/*.msg; do
    [ -e "$f" ] && printf '%s\n' "$f"
  done
  return 0
}

record_count() {  # <dir>
  records "$1" | grep -c . || true
}

wait_for_record() {  # <dir>
  local i=0
  while [ "$i" -lt 200 ]; do
    [ "$(record_count "$1")" -ge 1 ] && return 0
    sleep 0.1
    i=$((i + 1))
  done
  return 1
}

wait_gone() {  # <pid>
  local i=0
  while [ "$i" -lt 200 ]; do
    kill -0 "$1" 2>/dev/null || return 0
    sleep 0.1
    i=$((i + 1))
  done
  return 1
}

job_dir_of() {  # <dir> <start-output>
  local id
  id=$(printf '%s\n' "$2" | sed -n 's/^job: //p')
  printf '%s/state/t1.inbox/jobs/%s' "$1" "$id"
}

body_of() {  # <record>
  sed '1,/^--$/d' "$1"
}

test_completion_reaches_inbox_and_rings() {
  local dir out jobdir rec body until_line
  dir=$(setup_case finished)
  out=$(job_start "$dir" --timeout 60 -- \
    sh -c 'echo monitored-outcome; exit 3') || fail "start failed: $out"
  jobdir=$(job_dir_of "$dir" "$out")
  [ -d "$jobdir" ] || fail "start did not report its job directory:"$'\n'"$out"
  assert_contains "$out" "output: $jobdir/output" "start should print the output path"
  until_line=$(printf '%s\n' "$out" | sed -n 's/^until: //p')
  case "$until_line" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]Z) ;;
    *) fail "start should print a UTC minute for the paused declaration, got: $until_line" ;;
  esac
  wait_for_record "$dir" || fail "a finished command produced no inbox record"
  wait_gone "$(sed -n 's/^pid=//p' "$jobdir/runner")" || fail "the runner outlived its delivery"
  [ "$(record_count "$dir")" = 1 ] || fail "expected one completion record, got:"$'\n'"$(records "$dir")"
  rec=$(records "$dir")
  body=$(body_of "$rec")
  assert_contains "$body" "Task job ${jobdir##*/} finished: the command exited with status 3." \
    "the record should name the job and its exit status"
  assert_contains "$body" "Task: t1; started by worker generation gen-A." \
    "the record should key the completion by task and spawn generation"
  assert_contains "$body" "Output: $jobdir/output" "the record should point at the output"
  assert_contains "$body" "not a new instruction" "the record should read as a result, not an order"
  assert_grep 'delivery=hold-aware' "$rec" "a completion record should be hold-aware"
  assert_grep 'monitored-outcome' "$jobdir/output" "the command's output should be captured"
  assert_grep "record=${rec##*/}" "$jobdir/delivered" "the job should record where it was delivered"
  assert_grep "$DOORBELL" "$dir/send.log" "the completion should ring the worker's doorbell"
  pass "task job: a finished command becomes one keyed inbox record and rings the worker"
}

test_completion_names_the_starting_generation() {
  local dir out jobdir
  dir=$(setup_case relaunched)
  out=$(job_start "$dir" --timeout 60 -- sh -c 'sleep 1') || fail "start failed: $out"
  jobdir=$(job_dir_of "$dir" "$out")
  fm_write_meta "$dir/state/t1.meta" "window=sess:fm-t1" "kind=ship" "harness=grok" "spawn_gen=gen-B"
  wait_for_record "$dir" || fail "the job was not delivered to the relaunched task"
  assert_contains "$(body_of "$(records "$dir")")" "started by worker generation gen-A." \
    "a relaunched task should learn which generation started the job"
  assert_grep 'gen=gen-A' "$jobdir/job" "the job record should keep its starting generation"
  pass "task job: a completion names the spawn generation that started it"
}

test_timeout_stops_the_command_group() {
  local dir out jobdir grandchild
  dir=$(setup_case timeout)
  # shellcheck disable=SC2016 # The job's own shell expands $! and $0.
  out=$(job_start "$dir" --timeout 1 -- \
    sh -c 'sleep 30 & echo $! > "$0"; wait' "$dir/grandchild.pid") || fail "start failed: $out"
  jobdir=$(job_dir_of "$dir" "$out")
  wait_for_record "$dir" || fail "a timed-out command produced no inbox record"
  assert_contains "$(body_of "$(records "$dir")")" "passed its 1-second timeout and was stopped" \
    "the record should report the timeout"
  assert_grep 'outcome=timed-out' "$jobdir/exit" "the exit record should say timed-out"
  grandchild=$(cat "$dir/grandchild.pid")
  wait_gone "$grandchild" || fail "the timeout left a process the command started running"
  pass "task job: a command past its timeout is stopped with its whole process group"
}

test_hold_defers_the_ring_until_the_decision_closes() {
  local dir out rec rings
  dir=$(setup_case held)
  printf 'needs-decision [key=pick]: ship alpha or beta?\n' >> "$dir/state/t1.status"
  out=$(job_start "$dir" --timeout 60 -- true) || fail "start failed: $out"
  wait_for_record "$dir" || fail "a held task's job was not delivered"
  wait_gone "$(sed -n 's/^pid=//p' "$(job_dir_of "$dir" "$out")/runner")" || fail "the runner outlived its delivery"
  [ ! -s "$dir/send.log" ] || fail "a completion rang a worker holding its own decision:"$'\n'"$(cat "$dir/send.log")"
  rec=$(records "$dir")
  age_path "$rec"
  steer_check "$dir"
  steer_check "$dir"
  [ ! -s "$dir/send.log" ] || fail "the ladder rang a held completion:"$'\n'"$(cat "$dir/send.log")"
  [ -f "$rec" ] || fail "the held completion record must stay in the inbox"

  printf 'resolved [key=pick]: alpha\n' >> "$dir/state/t1.status"
  steer_check "$dir"
  rings=$(grep -cF "$DOORBELL" "$dir/send.log" || true)
  [ "$rings" = 1 ] || fail "expected one ring once the decision closed, got $rings:"$'\n'"$(cat "$dir/send.log")"
  pass "task job: a hold receives the result unrung, and the ladder rings it once the decision closes"
}

test_captain_hold_defers_completion() {
  local dir out rec
  dir=$(setup_case captain-held)
  out=$(start_waiting_job "$dir") || fail "start failed: $out"
  printf 'needs-decision [key=pick]: ship alpha or beta?\n' >> "$dir/state/t1.status"
  printf 'captain-held [key=pick]: waiting for captain\n' >> "$dir/state/t1.status"
  touch "$dir/release"
  wait_for_record "$dir" || fail "a captain-held task's completion was not recorded"
  wait_gone "$(sed -n 's/^pid=//p' "$(job_dir_of "$dir" "$out")/runner")" || fail "the runner outlived delivery"
  [ ! -s "$dir/send.log" ] || fail "a captain-held completion rang immediately"
  rec=$(records "$dir")
  age_path "$rec"
  steer_check "$dir"
  steer_check "$dir"
  [ ! -s "$dir/send.log" ] || fail "the watcher rang a captain-held completion"
  [ -f "$rec" ] || fail "the captain-held completion disappeared"
  printf 'resolved [key=pick]: alpha\n' >> "$dir/state/t1.status"
  steer_check "$dir"
  assert_grep "$DOORBELL" "$dir/send.log" "the watcher should ring after the captain hold clears"
  pass "task job: captain holds suppress immediate and watcher completion rings"
}

test_runner_rings_a_preexisting_completion() {
  local dir out jobdir rec
  dir=$(setup_case preexisting)
  out=$(start_waiting_job "$dir") || fail "start failed: $out"
  jobdir=$(job_dir_of "$dir" "$out")
  job_lib "$dir" fm_task_job_publish_exit "$jobdir" exited 0 || fail "could not publish exit"
  job_lib "$dir" fm_task_job_deliver "$dir/state" t1 "$jobdir" || fail "watcher delivery failed"
  [ ! -s "$dir/send.log" ] || fail "delivery without ring rang immediately"
  rec=$(records "$dir")
  touch "$dir/release"
  wait_gone "$(sed -n 's/^pid=//p' "$jobdir/runner")" || fail "the runner outlived delivery"
  [ "$(record_count "$dir")" = 1 ] || fail "the runner duplicated the completion"
  assert_grep "$DOORBELL" "$dir/send.log" "the runner should ring an existing unhandled completion"
  mv "$rec" "$dir/state/t1.inbox/handled/"
  : > "$dir/send.log"
  job_lib "$dir" fm_task_job_deliver "$dir/state" t1 "$jobdir" ring || fail "acknowledged redelivery failed"
  [ ! -s "$dir/send.log" ] || fail "an acknowledged completion rang again"
  pass "task job: immediate ringing ignores the record's writer and respects acknowledgement"
}

test_finished_live_runner_is_owned_until_stopped() {
  local dir out jobdir runner child
  dir=$(setup_case exit-before-delivery)
  out=$(start_waiting_job "$dir") || fail "start failed: $out"
  jobdir=$(job_dir_of "$dir" "$out")
  runner=$(sed -n 's/^pid=//p' "$jobdir/runner")
  child=$(sed -n 's/^pid=//p' "$jobdir/child")
  job_lib "$dir" fm_task_job_publish_exit "$jobdir" exited 0 || fail "could not publish exit"
  job_lib "$dir" fm_task_job_reconcile "$dir/state" t1 || fail "reconcile failed"
  [ "$(record_count "$dir")" = 0 ] || fail "reconcile delivered while the runner was alive"
  FM_TASK_JOB_KILL_GRACE_SECS=1 "$JOB" stop-all "$dir/state" t1 || fail "stop-all failed"
  wait_gone "$runner" || fail "stop-all left a runner with an exit record running"
  wait_gone "$child" || fail "stop-all left the command running"
  [ "$(record_count "$dir")" = 0 ] || fail "stop-all delivered the completion"
  rm -rf "$dir/state/t1.inbox"
  [ ! -e "$dir/state/t1.inbox" ] || fail "the stopped runner recreated its inbox"
  pass "task job: reconcile defers to a live runner and teardown stops it after exit publication"
}

test_watcher_rerings_until_acknowledged() {
  local dir out rec
  dir=$(setup_case rering)
  out=$(FM_FAKE_TMUX_SEND_FAIL=1 job_start "$dir" --timeout 60 -- true) || fail "start failed: $out"
  wait_for_record "$dir" || fail "the job was not delivered"
  wait_gone "$(sed -n 's/^pid=//p' "$(job_dir_of "$dir" "$out")/runner")" || fail "the runner outlived its delivery"
  assert_no_grep "$DOORBELL" "$dir/send.log" "the failed first ring should not have landed"
  rec=$(records "$dir")
  age_path "$rec"
  steer_check "$dir"
  assert_grep "$DOORBELL" "$dir/send.log" "the watcher should re-ring an unacknowledged completion"

  mv "$rec" "$dir/state/t1.inbox/handled/"
  : > "$dir/send.log"
  steer_check "$dir"
  [ ! -s "$dir/send.log" ] || fail "the watcher rang after the acknowledgement:"$'\n'"$(cat "$dir/send.log")"
  pass "task job: an unlanded doorbell is re-rung until the worker acknowledges the record"
}

watch_bg() {  # <dir> <out>
  PATH="$1/fakebin:$PATH" FM_STATE_OVERRIDE="$1/state" FM_SEND_LOG="$1/send.log" \
    FM_CREW_STATE_BIN="$1/fakebin/fm-crew-state.sh" \
    FM_FAKE_CREW_STATE='state: working · source: run-step · validating (running)' \
    FM_POLL=1 FM_SIGNAL_GRACE=1 FM_CHECK_INTERVAL=999999 FM_HEARTBEAT=999999 \
    FM_TASK_INBOX_GRACE_SECS=1 FM_TASK_JOB_KILL_GRACE_SECS=1 \
    "$WATCH" > "$2" 2>/dev/null &
}

test_watcher_delivers_a_lost_runner_once() {
  local dir out jobdir runner child wpid rec i
  dir=$(setup_case lost)
  prime_status_seen "$dir/state" "$dir/state/t1.status"
  out=$(job_start "$dir" --timeout 120 -- sleep 60) || fail "start failed: $out"
  jobdir=$(job_dir_of "$dir" "$out")
  runner=$(sed -n 's/^pid=//p' "$jobdir/runner")
  child=$(sed -n 's/^pid=//p' "$jobdir/child")
  [ -n "$child" ] || fail "the runner did not record its command"
  kill -KILL "$runner"
  wait_gone "$runner" || fail "could not stop the runner under test"
  watch_bg "$dir" "$dir/watch.out"
  wpid=$!
  i=0
  while [ "$i" -lt 200 ] && [ "$(record_count "$dir")" -lt 1 ]; do
    sleep 0.1
    i=$((i + 1))
  done
  [ "$(record_count "$dir")" = 1 ] || { kill "$wpid" 2>/dev/null; fail "the watcher did not deliver the lost job"; }
  assert_grep 'outcome=lost' "$jobdir/exit" "the exit record should say lost"
  rec=$(records "$dir")
  assert_contains "$(body_of "$rec")" "its runner stopped before recording an exit" \
    "the record should report the lost runner"
  wait_gone "$child" || { kill "$wpid" 2>/dev/null; fail "the orphaned command was left running"; }

  mv "$rec" "$dir/state/t1.inbox/handled/"
  rm -f "$jobdir/delivered"
  sleep 2.5
  kill "$wpid" 2>/dev/null
  wait "$wpid" 2>/dev/null
  [ "$(record_count "$dir")" = 0 ] || fail "an acknowledged completion was delivered again:"$'\n'"$(records "$dir")"
  assert_grep 'record=' "$dir/state/t1.inbox/jobs/${jobdir##*/}/delivered" \
    "redelivery should land on the acknowledged record"
  pass "watcher: a job whose runner died is delivered once as lost, with its command stopped"
}

test_stop_all_stops_without_delivering() {
  local dir out jobdir runner child
  dir=$(setup_case stop)
  out=$(job_start "$dir" --timeout 120 -- sleep 60) || fail "start failed: $out"
  jobdir=$(job_dir_of "$dir" "$out")
  runner=$(sed -n 's/^pid=//p' "$jobdir/runner")
  child=$(sed -n 's/^pid=//p' "$jobdir/child")
  FM_TASK_JOB_KILL_GRACE_SECS=1 "$JOB" stop-all "$dir/state" t1 || fail "stop-all failed"
  wait_gone "$runner" || fail "stop-all left the runner running"
  wait_gone "$child" || fail "stop-all left the command running"
  [ ! -e "$jobdir/exit" ] || fail "a stopped job must not publish an exit"
  [ "$(record_count "$dir")" = 0 ] || fail "a stopped job must not be delivered"
  pass "task job: teardown's stop-all stops live jobs without delivering them"
}

test_removed_inbox_is_never_recreated() {
  local dir out runner
  dir=$(setup_case retired)
  out=$(job_start "$dir" --timeout 60 -- sleep 1) || fail "start failed: $out"
  runner=$(sed -n 's/^pid=//p' "$(job_dir_of "$dir" "$out")/runner")
  rm -rf "$dir/state/t1.inbox"
  wait_gone "$runner" || fail "the runner did not finish"
  [ ! -e "$dir/state/t1.inbox" ] || fail "a retired task's job recreated its inbox"
  [ ! -s "$dir/send.log" ] || fail "a retired task's job rang its old endpoint"
  pass "task job: a job whose task inbox is gone delivers nothing and recreates nothing"
}

test_start_refuses_without_identity_or_timeout() {
  local dir rc out
  dir=$(setup_case refuse)
  rc=0
  out=$(env -u FM_TASK_INBOX "$JOB" start --timeout 5 -- true 2>&1) || rc=$?
  expect_code 1 "$rc" "start without FM_TASK_INBOX"
  assert_contains "$out" "FM_TASK_INBOX is not set" "the refusal should name the missing identity"
  rc=0
  out=$(job_start "$dir" -- true 2>&1) || rc=$?
  expect_code 2 "$rc" "start without a timeout"
  rc=0
  out=$(job_start "$dir" --timeout 9999999 -- true 2>&1) || rc=$?
  expect_code 2 "$rc" "start with an oversized timeout"
  fm_write_meta "$dir/state/t1.meta" "window=sess:fm-t1" "kind=ship" "harness=grok"
  rc=0
  out=$(job_start "$dir" --timeout 5 -- true 2>&1) || rc=$?
  expect_code 1 "$rc" "start without a spawn generation"
  assert_contains "$out" "no spawn_gen" "the refusal should name the missing generation"
  [ ! -d "$dir/state/t1.inbox/jobs" ] || [ -z "$(ls "$dir/state/t1.inbox/jobs")" ] \
    || fail "a refused start left a job record behind"
  pass "task job: start refuses without a task identity, a spawn generation, or a valid timeout"
}

fm_test_run \
  test_completion_reaches_inbox_and_rings \
  test_completion_names_the_starting_generation \
  test_timeout_stops_the_command_group \
  test_hold_defers_the_ring_until_the_decision_closes \
  test_captain_hold_defers_completion \
  test_runner_rings_a_preexisting_completion \
  test_finished_live_runner_is_owned_until_stopped \
  test_watcher_rerings_until_acknowledged \
  test_watcher_delivers_a_lost_runner_once \
  test_stop_all_stops_without_delivering \
  test_removed_inbox_is_never_recreated \
  test_start_refuses_without_identity_or_timeout
