#!/usr/bin/env bash
set -u
ROOT=$PWD
EVIDENCE=~/.no-mistakes-upstream-codex/evidence/01M7PH8J6P5MQJS1CXZ3MGG21E
BASE=$ROOT/.test-phase
export FM_SUPERVISION_HOST_PRIMARY=claude FM_BACKEND=tmux
export FM_POLL=1 FM_SIGNAL_GRACE=0 FM_CHECK_INTERVAL=999999 FM_HEARTBEAT=999999
unset FM_ROOT_OVERRIDE FM_STATE_OVERRIDE FM_DATA_OVERRIDE FM_CONFIG_OVERRIDE FM_PROJECTS_OVERRIDE
unset FM_TEST_SEAM FM_TEST_STARTUP_CLOCK FM_GATE_REFUSE_BYPASS
host='' holder='' home=''
cleanup_case() {
  local pid
  if [ -n "$home" ]; then : > "$home/release"; : > "$home/recovery-release"; fi
  [ -z "$holder" ] || wait "$holder" 2>/dev/null || true
  holder=''
  if [ -n "$home" ]; then
    pid=$(cut -f1 "$home/state/.supervision-handoff-owner" 2>/dev/null || true)
    [ -z "$pid" ] || kill -TERM "$pid" 2>/dev/null || true
    [ -z "$host" ] || kill -TERM "$host" 2>/dev/null || true
    bash "$ROOT/bin/fm-watch-arm.sh" --stop >> "$home/cleanup.out" 2>&1 || true
    pid=$(cut -f1 "$home/state/.supervision-host-left" 2>/dev/null || true)
    [ -z "$pid" ] || kill -TERM "$pid" 2>/dev/null || true
    [ -z "$host" ] || wait "$host" 2>/dev/null || true
  fi
  host=''
}
trap cleanup_case EXIT
wait_file() {
  local max=$1 path=$2 start=$SECONDS
  while [ ! -s "$path" ]; do
    [ $((SECONDS-start)) -lt "$max" ] || return 1
    sleep .2
  done
}
wait_ready() {
  local start=$SECONDS
  while ! grep -q '^watcher: started pid=' "$home/host.out" 2>/dev/null; do
    [ $((SECONDS-start)) -lt 65 ] || return 1
    [ ! -s "$home/host.rc" ] || return 1
    sleep .2
  done
}
save_case() {
  local name=$1
  { printf 'candidate=%s\ncase=%s\n' "$(git rev-parse HEAD)" "$name"
    for f in lock.out host.out host.rc state/.supervision-host.log state/.supervision-host-left state/.supervision-handoff-owner state/.supervision-handoff.log state/.watch-cycle-exits.log cleanup.out; do
      printf '\n--- %s ---\n' "$f"
      [ ! -f "$home/$f" ] || cat "$home/$f"
    done
  } > "$EVIDENCE/$name.txt"
}
new_case() {
  local name=$1
  cleanup_case
  home=$BASE/$name
  bash "$ROOT/bin/fm-lab-home.sh" create "$home" || return 1
  export FM_HOME=$home
  : > "$home/config/supervision-host"
  printf 'project=lab\nharness=claude\n' > "$home/state/demo.meta"
  bash "$ROOT/bin/fm-lock.sh" > "$home/lock.out" 2>&1 || return 1
}
start_host() {
  (bash "$ROOT/bin/fm-supervision-host.sh" park > "$home/host.out" 2>&1; printf '%s\n' "$?" > "$home/host.rc") &
  host=$!
}
failure() { printf 'FAIL %s: %s\n' "$1" "$2" | tee -a "$EVIDENCE/live-results.txt"; save_case "$1"; exit 1; }
success() { printf 'PASS %s: %s\n' "$1" "$2" | tee -a "$EVIDENCE/live-results.txt"; cleanup_case; save_case "$1"; }

name=initial-progress
new_case "$name" || failure "$name" 'real primary lock unavailable'
cat > "$home/config/watch.env" <<'SH'
case "$0" in */fm-watch-arm.sh)
  if [ ! -e "$FM_HOME/entered" ]; then
    printf '%s\n' "$$" > "$FM_HOME/entered"
    sleep 14
  fi
esac
SH
FM_HOME=$home bash -c '. "$1/bin/fm-wake-lib.sh"; fm_lock_acquire_wait "$STATE/.watcher-down.lock" || exit; echo held > "$FM_HOME/held"; while [ ! -e "$FM_HOME/release" ]; do sleep .1; done; fm_lock_release "$STATE/.watcher-down.lock"' _ "$ROOT" > "$home/holder.out" 2>&1 &
holder=$!
wait_file 10 "$home/held" || failure "$name" 'recovery lock not held'
begin=$SECONDS
start_host
wait_file 15 "$home/entered" || failure "$name" 'arm never entered configuration'
sleep 29
: > "$home/release"
wait "$holder"; holder=''
wait_ready || failure "$name" 'progressing initial startup failed'
elapsed=$((SECONDS-begin))
[ "$elapsed" -gt 25 ] || failure "$name" 'did not exceed old deadline'
success "$name" "genuine initial watcher ready after ${elapsed}s"

for mode in direct ack; do
  for kind in progress stalled explicit dead; do
    name=$mode-$kind
    new_case "$name" || failure "$name" 'real primary lock unavailable'
    [ "$mode" != ack ] || : > "$home/config/supervision-handoff-ack"
    cat > "$home/config/watch.env" <<'SH'
if [ -n "${FM_WATCH_PREDECESSOR_ARM_PID:-}" ]; then
  printf '%s\n' "$$" > "$FM_HOME/entered"
  printf '%s\n' "$FM_STARTUP_PROGRESS_JOURNAL" > "$FM_HOME/journal"
  while [ ! -e "$FM_HOME/release" ]; do sleep .1; done
fi
SH
    unset FM_SUPERVISION_HOST_READY_TIMEOUT
    [ "$kind" != explicit ] || export FM_SUPERVISION_HOST_READY_TIMEOUT=6
    start_host
    wait_ready || failure "$name" 'no initial watcher'
    # A main-only queued decision is a synthetic user event, processed by the real watcher.
    printf 'needs-decision [at=%s]: choose a local export format\n' "$(date +%s)" >> "$home/state/demo.status"
    wait_file 30 "$home/entered" || failure "$name" 'no successor attempt'
    begin=$SECONDS
    case "$kind" in
      progress)
        FM_HOME=$home bash -c '. "$1/bin/fm-wake-lib.sh"; fm_lock_acquire_wait "$STATE/.watcher-down.lock" || exit; echo held > "$FM_HOME/held"; while [ ! -e "$FM_HOME/recovery-release" ]; do sleep .1; done; fm_lock_release "$STATE/.watcher-down.lock"' _ "$ROOT" > "$home/holder.out" 2>&1 &
        holder=$!
        wait_file 10 "$home/held" || failure "$name" 'recovery lock not held'
        sleep 14
        : > "$home/release"
        sleep 15
        : > "$home/recovery-release"
        wait "$holder"; holder=''
        ;;
      stalled)
        journal=$(cat "$home/journal")
        for n in 1 2 3 4; do
          printf 'stage 99 wrong-nonce\n' >> "$journal"
          touch "$journal"
          sleep 5
        done
        ;;
      dead) kill -TERM "$(cat "$home/entered")" ;;
      explicit) : ;;
    esac
    wait_file 45 "$home/host.rc" || failure "$name" 'host did not return control'
    elapsed=$((SECONDS-begin))
    if [ "$kind" = progress ]; then
      [ -s "$home/state/.supervision-host-left" ] || failure "$name" 'no retained verified successor'
      ! grep -q 'could not be verified\|successor-unverified\|watcher: FAILED' "$home/host.out" "$home/state/.supervision-host.log" || failure "$name" 'unexpected readiness fallback'
      [ "$elapsed" -gt 25 ] || failure "$name" 'did not exceed old deadline'
    else
      grep -q 'could not be verified\|successor-unverified' "$home/host.out" "$home/state/.supervision-host.log" || failure "$name" 'missing safe fallback'
      [ ! -s "$home/state/.supervision-host-left" ] || failure "$name" 'unverified successor persisted'
      [ "$elapsed" -le 42 ] || failure "$name" 'bounded fallback too late'
    fi
    success "$name" "real host returned in ${elapsed}s, retained-successor=$([ -s "$home/state/.supervision-host-left" ] && echo yes || echo no)"
  done
done
unset FM_SUPERVISION_HOST_READY_TIMEOUT
printf 'COMPLETED\n' >> "$EVIDENCE/live-results.txt"
