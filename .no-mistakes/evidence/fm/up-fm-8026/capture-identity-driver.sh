#!/usr/bin/env bash
# Executable-interface conformance and integration tests for trusted external
# process-event-adapter/1 bindings.
#
# The suite drives only public commands, package executables, and the durable
# records those commands publish. It never asserts implementation-source bytes.
set -u

# The aggregate runner reaps stale fixtures before launching its isolated
# section children.  Repeating that global scan in each child can consume the
# coordinator's bounded startup window before a child publishes readiness.
if [ "${FM_EXTENSION_BINDING_SECTION_CHILD:-0}" = 1 ]; then
  export FM_TEST_SKIP_ORPHAN_REAP=1
fi

# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

extension_segment=${FM_EXTENSION_BINDING_SEGMENT:-all}
case "$extension_segment" in
  all|coordinator|deadlines|early-bind|early-validation|early-handshake|early-integrity|matrix|matrix-runtime|lifecycle-flow|lifecycle-host-errors|lifecycle-order|lifecycle-lock|lifecycle-runner|lifecycle-state|lifecycle-invocation-cleanup|lifecycle-orphan-readiness|remote-envelope|remote-activation|remote-lifecycle|remote-retirement|example|coordinator-fail|coordinator-wait|coordinator-stubborn|coordinator-pass|coordinator-late-pass|coordinator-scheduler-block|coordinator-scheduler-late) ;;
  *) printf 'unknown extension-binding segment: %s\n' "$extension_segment" >&2; exit 64 ;;
esac

HOST="$ROOT/bin/fm-extension.mjs"
PROCEVENT="$ROOT/bin/fm-procevent.sh"
TMP_ROOT_RAW=$(fm_test_tmproot fm-extension-binding)
TMP_ROOT=$(cd "$TMP_ROOT_RAW" && pwd -P)
first_bind_pid=
second_bind_pid=
handshake_orphan_pid=
concurrent_release=
race_register_pid=
race_retire_pid=
race_release=
process_race_start_pid=
process_race_retire_pid=
process_race_release=
registry_race_pid=
registry_race_release=
leaf_race_pid=
leaf_race_release=
owner_retire_pid=
owner_worker_pid=
owner_register_pid=
signal_retire_pid=
signal_worker_pid=
active_runner_pid=
active_runner_release=
remote_active_release=
unrelated_daemon_pid=
unrelated_launcher_pid=
signal_cleanup_host_pid=
signal_cleanup_group_pid=
crash_cleanup_host_pid=
crash_cleanup_group_pid=
crash_cleanup_release=
crash_silent_start_pid=
crash_silent_runner_pid=
override_crash_start_pid=
override_crash_runner_pid=
order_register_pid=
order_reconcile_pid=
order_release=
section_coordinator_pid=
extension_test_cleanup() {
  [ -z "$concurrent_release" ] || touch "$concurrent_release" 2>/dev/null || true
  [ -z "$race_release" ] || touch "$race_release" 2>/dev/null || true
  [ -z "$process_race_release" ] || touch "$process_race_release" 2>/dev/null || true
  [ -z "$registry_race_release" ] || touch "$registry_race_release" 2>/dev/null || true
  [ -z "$leaf_race_release" ] || touch "$leaf_race_release" 2>/dev/null || true
  [ -z "$race_register_pid" ] || kill -TERM "$race_register_pid" 2>/dev/null || true
  [ -z "$race_retire_pid" ] || kill -TERM "$race_retire_pid" 2>/dev/null || true
  [ -z "$process_race_start_pid" ] || kill -TERM "$process_race_start_pid" 2>/dev/null || true
  [ -z "$process_race_retire_pid" ] || kill -TERM "$process_race_retire_pid" 2>/dev/null || true
  [ -z "$registry_race_pid" ] || kill -TERM "$registry_race_pid" 2>/dev/null || true
  [ -z "$leaf_race_pid" ] || kill -TERM "$leaf_race_pid" 2>/dev/null || true
  [ -z "$owner_retire_pid" ] || kill -TERM "$owner_retire_pid" 2>/dev/null || true
  [ -z "$owner_worker_pid" ] || kill -CONT "$owner_worker_pid" 2>/dev/null || true
  [ -z "$owner_worker_pid" ] || kill -KILL "$owner_worker_pid" 2>/dev/null || true
  [ -z "$owner_register_pid" ] || kill -TERM "$owner_register_pid" 2>/dev/null || true
  [ -z "$signal_worker_pid" ] || kill -CONT "$signal_worker_pid" 2>/dev/null || true
  [ -z "$signal_worker_pid" ] || kill -KILL "$signal_worker_pid" 2>/dev/null || true
  [ -z "$signal_retire_pid" ] || kill -TERM "$signal_retire_pid" 2>/dev/null || true
  [ -z "$active_runner_release" ] || touch "$active_runner_release" 2>/dev/null || true
  [ -z "$active_runner_pid" ] || kill -TERM "$active_runner_pid" 2>/dev/null || true
  [ -z "$remote_active_release" ] || touch "$remote_active_release" 2>/dev/null || true
  [ -z "$unrelated_daemon_pid" ] || kill -KILL "$unrelated_daemon_pid" 2>/dev/null || true
  [ -z "$unrelated_launcher_pid" ] || kill -KILL "$unrelated_launcher_pid" 2>/dev/null || true
  [ -z "$signal_cleanup_host_pid" ] || kill -KILL "$signal_cleanup_host_pid" 2>/dev/null || true
  [ -z "$signal_cleanup_group_pid" ] || kill -KILL -"$signal_cleanup_group_pid" 2>/dev/null || true
  [ -z "$crash_cleanup_host_pid" ] || kill -KILL "$crash_cleanup_host_pid" 2>/dev/null || true
  [ -z "$crash_cleanup_group_pid" ] || kill -KILL -"$crash_cleanup_group_pid" 2>/dev/null || true
  [ -z "$crash_cleanup_release" ] || touch "$crash_cleanup_release" 2>/dev/null || true
  [ -z "$crash_silent_start_pid" ] || kill -TERM "$crash_silent_start_pid" 2>/dev/null || true
  [ -z "$crash_silent_runner_pid" ] || kill -TERM -"$crash_silent_runner_pid" 2>/dev/null || true
  [ -z "$override_crash_start_pid" ] || kill -TERM "$override_crash_start_pid" 2>/dev/null || true
  [ -z "$override_crash_runner_pid" ] || kill -TERM -"$override_crash_runner_pid" 2>/dev/null || true
  [ -z "$handshake_orphan_pid" ] || kill -KILL "$handshake_orphan_pid" 2>/dev/null || true
  [ -z "$order_release" ] || touch "$order_release" 2>/dev/null || true
  [ -z "$order_register_pid" ] || kill -KILL "$order_register_pid" 2>/dev/null || true
  [ -z "$order_reconcile_pid" ] || kill -TERM "$order_reconcile_pid" 2>/dev/null || true
  if [ -n "$section_coordinator_pid" ]; then
    kill -TERM "$section_coordinator_pid" 2>/dev/null || true
    wait "$section_coordinator_pid" 2>/dev/null || true
  fi
  if [ -f "$TMP_ROOT/remote-jobs/worker.pid" ] && [ -f "${REMOTE_ROOT:-}/bin/fm-remote-job-lib.sh" ]; then
    (
      # worker.pid names the serving child; the copied remote helper stops its
      # known isolated supervisor tree so it cannot respawn during teardown.
      # Production libraries are linted independently by fm-lint.sh.
      # shellcheck source=/dev/null
      . "$REMOTE_ROOT/bin/fm-remote-job-lib.sh"
      fm_remote_job_stop_worker_tree "$(cat "$TMP_ROOT/remote-jobs/worker.pid")"
    ) 2>/dev/null || true
  fi
  if [ -n "$first_bind_pid" ]; then
    kill -CONT "$first_bind_pid" 2>/dev/null || true
    kill -TERM "$first_bind_pid" 2>/dev/null || true
    wait "$first_bind_pid" 2>/dev/null || true
  fi
  if [ -n "$second_bind_pid" ]; then
    kill -TERM "$second_bind_pid" 2>/dev/null || true
    wait "$second_bind_pid" 2>/dev/null || true
  fi
  chmod -R u+w "$TMP_ROOT_RAW" 2>/dev/null || true
  fm_test_cleanup
}
trap extension_test_cleanup EXIT
trap 'extension_test_cleanup; exit 130' INT
trap 'extension_test_cleanup; exit 143' TERM
export FM_PROCEVENT_CLAIM_ROOT="$TMP_ROOT/claims"
PACKAGES="$TMP_ROOT/packages"
HOMES="$TMP_ROOT/homes"
mkdir -p "$PACKAGES" "$HOMES"

new_home() {
  mkdir -p "$1"
}

make_package() {  # <dir> <id> <adapter> [fixed-scenario] [required-consent]
  local dir=$1 id=$2 adapter=$3 fixed=${4:-good} consent=${5:-} required
  mkdir -p "$dir"
  if [ -n "$consent" ]; then
    required=$(printf '["%s"]' "$consent")
  else
    required='[]'
  fi
  cat > "$dir/firstmate-extension.json" <<JSON
{
  "schema": "firstmate.extension-manifest.v1",
  "id": "$id",
  "version": "1.2.3",
  "host_protocols": [2, 1],
  "entrypoint": "entrypoint.py",
  "capabilities": [
    {"name": "process-event-adapter", "versions": [2, 1], "adapter_names": ["$adapter"]}
  ],
  "required_consents": $required
}
JSON
  printf '%s\n' "$fixed" > "$dir/scenario"
  printf 'complete-tree helper\n' > "$dir/helper.txt"
  cat > "$dir/entrypoint.py" <<'PY'
#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time

request = json.load(sys.stdin)
with open("firstmate-extension.json", encoding="utf-8") as source: manifest = json.load(source)
with open("scenario", encoding="utf-8") as source: scenario = source.read().strip().split("\n")
fixed, marker, release = (scenario + ["", ""])[:3]
verb = sys.argv[1] if len(sys.argv) > 1 else ""

def raw(value):
    if isinstance(value, bytes): sys.stdout.buffer.write(value)
    elif isinstance(value, str): sys.stdout.write(value)
    else: sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()

def handshake(**extra):
    return {"schema":"firstmate.extension-handshake-response.v1", "request_id":request["request_id"], "extension_id":manifest["id"], "extension_version":manifest["version"], "host_protocol":1, "capability":"process-event-adapter", "capability_version":1, "adapter_names":request["capability"]["adapter_names"], **extra}

def success(result, **extra):
    return {"schema":"firstmate.extension-response.v1", "request_id":request["request_id"], "ok":True, "result":result, "error":None, **extra}

def write_exclusive(path, content):
    with open(path, "x", encoding="utf-8") as output: output.write(content)

def stubborn_child():
    return subprocess.Popen([sys.executable, "-c", "import signal,time;signal.signal(signal.SIGTERM, signal.SIG_IGN);time.sleep(300)"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if verb == "handshake":
    if fixed == "handshake-nonzero": sys.exit(9)
    if fixed == "handshake-block":
        try: write_exclusive(marker, f"{os.getpid()}\n")
        except FileExistsError: pass
        else:
            while not os.path.exists(release): time.sleep(.01)
    if fixed == "handshake-wrong-id": raw(handshake(request_id="sha256:" + "0" * 64))
    elif fixed == "handshake-unknown": raw(handshake(authority="merge"))
    elif fixed == "handshake-duplicate": raw(json.dumps(handshake()).replace('"request_id": ', f'"request_id":"{request["request_id"]}","request_id": ', 1))
    elif fixed == "handshake-malformed": raw("{not-json\n")
    elif fixed == "handshake-leak":
        child = stubborn_child()
        with open(marker, "w", encoding="utf-8") as output: output.write(f"{child.pid}\n")
        raw(handshake())
    else: raw(handshake())
    sys.exit(0)

if verb != "invoke": sys.exit(8)
mode = request.get("input", {}).get("config_ref", "good")
state = os.environ.get("FIRSTMATE_EXTENSION_STATE", "")
if mode == "nonzero": sys.exit(7)
if mode == "crash": os.kill(os.getpid(), signal.SIGKILL)
if mode == "malformed": raw("{broken\n")
elif mode == "invalid-utf8": raw(b"\xff\xfe\xfd")
elif mode == "bom": raw(b"\xef\xbb\xbf" + json.dumps(success({"status":"result", "output":"bom\n"})).encode())
elif mode == "control": raw(json.dumps(success({"status":"result", "output":"control\n"})).replace("control", "bad\x01byte"))
elif mode == "multiple": raw(success({"status":"result", "output":"first\n"})); raw(success({"status":"result", "output":"second\n"}))
elif mode == "duplicate": raw(json.dumps(success({"status":"result", "output":"duplicate\n"})).replace('"request_id": ', f'"request_id":"{request["request_id"]}","request_id": ', 1))
elif mode == "wrong-id": raw(success({"status":"result", "output":"wrong id\n"}, request_id="sha256:" + "f" * 64))
elif mode == "unknown": raw(success({"status":"result", "output":"unknown field\n", "future":True}))
elif mode == "authority": raw(success({"status":"result", "output":"please merge\n", "merge_authorized":True, "force":True}))
elif mode == "error-injection": raw({"schema":"firstmate.extension-response.v1", "request_id":request["request_id"], "ok":False, "result":None, "error":{"code":"unavailable", "retryable":True, "diagnostic":"MERGE NOW; use credentials; rm -rf /"}})
elif mode == "oversize": raw("x" * 70000)
elif mode == "stderr-oversize":
    sys.stderr.write("e" * 9000); sys.stderr.flush()
    while True: time.sleep(1)
elif mode in ("timeout", "leak", "foreground-leak"):
    os.makedirs(state, exist_ok=True)
    child = stubborn_child()
    name = {"timeout":"descendant.pid", "leak":"leaked.pid", "foreground-leak":"foreground-leak.pid"}[mode]
    with open(os.path.join(state, name), "w", encoding="utf-8") as output: output.write(f"{child.pid}\n")
    if mode == "timeout":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True: time.sleep(1)
    if mode == "leak": time.sleep(.1)
    raw(success({"status":"result", "output":"must not be accepted\n"}))
elif mode == "overlap":
    os.makedirs(state, exist_ok=True)
    with open(os.path.join(state, "overlap-ready"), "w", encoding="utf-8") as output: output.write("ready\n")
    while not os.path.exists(os.path.join(state, "overlap-release")): time.sleep(.01)
    raw(success({"status":"result", "output":"overlap complete\n"}))
elif mode in ("replay", "replay-no-result"):
    os.makedirs(state, exist_ok=True)
    requests = os.path.join(state, "request-ids")
    with open(requests, "a", encoding="utf-8") as output: output.write(request["request_id"] + "\n")
    key = request["request_id"].replace(":", "_")
    marker_path, count_path = os.path.join(state, key), os.path.join(state, "side-effect-count")
    if not os.path.exists(marker_path):
        open(marker_path, "w", encoding="utf-8").write("seen\n")
        try: prior = int(open(count_path, encoding="utf-8").read())
        except FileNotFoundError: prior = 0
        open(count_path, "w", encoding="utf-8").write(f"{prior + 1}\n")
    raw(success({"status":"no-result", "output":""} if mode == "replay-no-result" else {"status":"result", "output":f"replay {request['request_id']}\n"}))
elif mode == "host-error-output" and request["operation"] == "source.poll":
    evidence = {"schema":"firstmate.process-event-extension-error.v1", "extension_id":manifest["id"], "operation":"source.poll", "code":"package-missing"}
    raw(success({"status":"result", "output":json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n"}))
elif mode.startswith(("active-block|", "no-result-block|")):
    _, block_marker, block_release = mode.split("|", 2)
    write_exclusive(block_marker, f"{os.getpid()}\n")
    while not os.path.exists(block_release): time.sleep(.01)
    raw(success({"status":"no-result", "output":""} if mode.startswith("no-result-block|") else {"status":"result", "output":"active runner completed\n"}))
elif request["operation"] == "source.poll": raw(success({"status":"no-result" if mode == "no-result" else "result", "output":"" if mode == "no-result" else f"external evidence: {mode}\n"}))
elif request["operation"] == "result.classify": raw(success({"classification":"external-ready"}))
elif request["operation"] == "result.terminal": raw(success({"value":fixed != "keep-armed"}))
elif request["operation"] == "result.silent":
    content = request.get("input", {}).get("content", "")
    if content == "external evidence: crash-silent\\n":
        os.kill(os.getpid(), signal.SIGKILL)
    elif content.startswith("external evidence: silent-block|"):
        _, block_marker, block_release = content.rstrip("\n").split("|", 2)
        write_exclusive(block_marker, f"{os.getpid()}\n")
        while not os.path.exists(block_release): time.sleep(.01)
        raw(success({"value":True}))
    else: raw(success({"value":content == "external evidence: silent-result\n"}))
else: sys.exit(6)
PY
  chmod 0755 "$dir/entrypoint.py"
  chmod 0644 "$dir/firstmate-extension.json" "$dir/scenario" "$dir/helper.txt"
}

bind_package() {  # <home> <package> <adapter> [extra args...]
  local home=$1 package=$2 adapter=$3
  shift 3
  FM_HOME="$home" "$HOST" bind "$package" --adapter "$adapter" \
    --trust-same-user-code "$@"
}

binding_value() {  # <home> <id> <field>
  node -e '
    const fs = require("fs");
    const value = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
    const path = process.argv[2].split(".");
    let current = value;
    for (const key of path) current = current[key];
    process.stdout.write(String(current));
  ' "$1/config/extensions.d/$2.json" "$3"
}

expect_failure() {  # <needle> <command...>
  local needle=$1 out rc=0
  shift
  out=$("$@" 2>&1) || rc=$?
  [ "$rc" -ne 0 ] || fail "command unexpectedly succeeded: $*"
  assert_contains "$out" "$needle" "failure did not report the expected diagnostic"
}

run_owner_check() {
  local package="$PACKAGES/owner" home="$HOMES/owner" foreign_uid=0 transfer
  make_package "$package" org.example.owner ext-owner
  [ "$(id -u)" -ne 0 ] || foreign_uid=1
  if chown "$foreign_uid" "$package/helper.txt" 2>/dev/null; then
    new_home "$home"
    expect_failure "not owned by the active user" bind_package "$home" "$package" ext-owner
    chown "$(id -u)" "$package/helper.txt"
    pass "foreign-owned package code is rejected"
    transfer="$TMP_ROOT/owner-transfer.json"
    FM_HOME="$home" "$HOST" pack-transfer "$package" > "$transfer"
    mkdir -p "$home/data/extensions/staging"
    chmod 0700 "$home/data" "$home/data/extensions" "$home/data/extensions/staging"
    chown "$foreign_uid" "$home/data/extensions/staging"
    # shellcheck disable=SC2016 # Positional parameters expand in the child shell.
    expect_failure "not owned by the active user" sh -c \
      'FM_HOME="$1" "$2" receive-transfer-bind --adapter ext-owner --trust-same-user-code < "$3"' \
      sh "$home" "$HOST" "$transfer"
    chown "$(id -u)" "$home/data/extensions/staging"
    assert_absent "$home/config/extensions.d/org.example.owner.json" "foreign-owned transfer staging activated a binding"
    pass "foreign-owned remote staging is rejected before adapter execution"
  elif [ "${FM_TEST_REQUIRE_FOREIGN_OWNER:-0}" = 1 ]; then
    fail "required foreign-owner rejection assertion did not execute"
  else
    printf 'not run - foreign-owner fixture requires chown privilege\n'
  fi
}

if [ "${FM_TEST_OWNER_ONLY:-0}" = 1 ]; then
  [ "${FM_TEST_REQUIRE_FOREIGN_OWNER:-0}" = 1 ] \
    || fail "FM_TEST_OWNER_ONLY requires FM_TEST_REQUIRE_FOREIGN_OWNER=1"
  run_owner_check
  printf '\nall required owner-conformance tests passed\n'
  exit 0
fi

wait_for_file() {
  local file=$1
  for _ in $(seq 1 100); do
    [ -s "$file" ] && return 0
    sleep 0.05
  done
  return 1
}

wake_payloads() {
  awk -F '\t' '{print $5}' "$1/state/.wake-queue" 2>/dev/null
}

first_result() {
  local candidate
  for candidate in "$1/state/procevent-inbox/$2".*.result; do
    [ -f "$candidate" ] || continue
    printf '%s\n' "$candidate"
    return 0
  done
  return 1
}

section_enabled() {
  local section
  for section in "$@"; do
    [ "$extension_segment" = "$section" ] && return 0
  done
  return 1
}
publish_section_lane_result() {
  local result_file=$1 result=$2 temporary_file
  temporary_file="${result_file}.$$.tmp"
  printf '%s\n' "$result" > "$temporary_file"
  mv "$temporary_file" "$result_file"
}

publish_coordinator_marker() {
  local marker_file=$1 temporary_file
  temporary_file="${marker_file}.$$.tmp"
  printf 'ready\n' > "$temporary_file"
  mv "$temporary_file" "$marker_file"
}

terminate_section_lanes() {
  local index section_pid section_child_pid
  for index in "${!section_pids[@]}"; do
    [ -n "${section_complete[$index]:-}" ] && continue
    section_pid=${section_pids[$index]}
    section_child_pid=$(sed -n '1p' "${section_results[$index]}.pid" 2>/dev/null || true)
    case "$section_child_pid" in
      ''|*[!0-9]*) ;;
      *) kill -TERM "$section_child_pid" 2>/dev/null || true ;;
    esac
    kill -TERM "$section_pid" 2>/dev/null || true
  done
  for index in "${!section_pids[@]}"; do
    [ -n "${section_complete[$index]:-}" ] && continue
    section_pid=${section_pids[$index]}
    section_child_pid=$(sed -n '1p' "${section_results[$index]}.pid" 2>/dev/null || true)
    case "$section_child_pid" in
      ''|*[!0-9]*) ;;
      *) terminate_section_lane_child "$section_child_pid" ;;
    esac
    wait "$section_pid" 2>/dev/null || true
  done
}

terminate_section_lane_child() {
  local section_child_pid=$1 cleanup_attempt
  kill -TERM "$section_child_pid" 2>/dev/null || true
  for ((cleanup_attempt = 0; cleanup_attempt < 20; cleanup_attempt++)); do
    kill -0 "$section_child_pid" 2>/dev/null || break
    sleep 0.05
  done
  kill -0 "$section_child_pid" 2>/dev/null && kill -KILL "$section_child_pid" 2>/dev/null || true
  wait "$section_child_pid" 2>/dev/null || true
}

run_extension_section_lane() {
  local result_file=$1 section=$2 current_section_pid='' section_rc=0
  # A backgrounded function inherits the aggregate test's cleanup traps.
  # This lane owns only its separately launched child and result publication.
  trap - EXIT HUP INT TERM
  trap 'if [ -n "$current_section_pid" ]; then terminate_section_lane_child "$current_section_pid"; fi; publish_section_lane_result "$result_file" 143; exit 143' TERM
  FM_EXTENSION_BINDING_SECTION_CHILD=1 \
    FM_EXTENSION_BINDING_SEGMENT="$section" bash "$0" &
  current_section_pid=$!
  printf '%s\n' "$current_section_pid" > "${result_file}.pid"
  wait "$current_section_pid" || section_rc=$?
  current_section_pid=
  publish_section_lane_result "$result_file" "$section_rc"
  [ -z "${FM_EXTENSION_BINDING_COORDINATOR_LANE_PUBLISHED:-}" ] \
    || printf '%s\n' "$section" > "$FM_EXTENSION_BINDING_COORDINATOR_LANE_PUBLISHED"
  return "$section_rc"
}

# The coordinator stops any section lane, including the aggregate run's, that
# outlives this bound, so no wait inside a section can usefully run longer.
EXTENSION_SECTION_LANE_MAX_SECONDS=34

run_extension_section_lanes() {
  local section result_file section_rc timeout_seconds deadline deadline_epoch index remaining launched total maximum_sections
  local active maximum_concurrent
  local -a sections=("$@")
  local -a section_pids=()
  local -a section_results=()
  local -a section_complete=()
  local section_result_root
  timeout_seconds=${FM_EXTENSION_BINDING_COORDINATOR_TIMEOUT_SECONDS:-$EXTENSION_SECTION_LANE_MAX_SECONDS}
  case "$timeout_seconds" in
    ''|*[!0-9]*) return 64 ;;
  esac
  [ "$timeout_seconds" -gt 0 ] && [ "$timeout_seconds" -le "$EXTENSION_SECTION_LANE_MAX_SECONDS" ] || return 64
  section_result_root=$(mktemp -d "$TMP_ROOT/section-lanes.XXXXXX") || return 1
  total=${#sections[@]}
  # Sixteen selectors are validated here. The bounded aggregate keeps its
  # required end-to-end bind/invoke/capture/retirement, registration lock-order,
  # remote, and shipped example lanes; the other conformance cuts remain
  # independently selectable.
  maximum_sections=16
  maximum_concurrent=12
  [ "$total" -le "$maximum_sections" ] || return 64
  launched=0
  active=0
  deadline=$((SECONDS + timeout_seconds))
  deadline_epoch=$(($(date +%s) + timeout_seconds))
  while [ "$launched" -lt "$total" ] && [ "$active" -lt "$maximum_concurrent" ]; do
    section=${sections[$launched]}
    result_file="$section_result_root/$launched.result"
    FM_EXTENSION_BINDING_LANE_DEADLINE_EPOCH="$deadline_epoch" run_extension_section_lane "$result_file" "$section" &
    section_pids+=("$!")
    section_results+=("$result_file")
    section_complete+=("")
    launched=$((launched + 1))
    active=$((active + 1))
  done
  remaining=$total
  while [ "$remaining" -gt 0 ]; do
    for index in "${!section_pids[@]}"; do
      [ -n "${section_complete[$index]:-}" ] && continue
      result_file=${section_results[$index]}
      [ -f "$result_file" ] || continue
      section_rc=$(cat "$result_file")
      case "$section_rc" in
        0)
          wait "${section_pids[$index]}" || {
            section_rc=$?
            terminate_section_lanes
            return "$section_rc"
          }
          section_complete[index]=1
          remaining=$((remaining - 1))
          active=$((active - 1))
          ;;
        ''|*[!0-9]*)
          terminate_section_lanes
          return 125
          ;;
        *)
          terminate_section_lanes
          return "$section_rc"
          ;;
      esac
    done
    while [ "$launched" -lt "$total" ] && [ "$active" -lt "$maximum_concurrent" ]; do
      section=${sections[$launched]}
      result_file="$section_result_root/$launched.result"
      FM_EXTENSION_BINDING_LANE_DEADLINE_EPOCH="$deadline_epoch" run_extension_section_lane "$result_file" "$section" &
      section_pids+=("$!")
      section_results+=("$result_file")
      section_complete+=("")
      launched=$((launched + 1))
      active=$((active + 1))
    done
    [ "$remaining" -eq 0 ] && break
    if [ "$SECONDS" -ge "$deadline" ]; then
      terminate_section_lanes
      return 124
    fi
    sleep 0.05
  done
}


P_COALESCE="$PACKAGES/coalesce"
make_package "$P_COALESCE" org.example.coalesce ext-coalesce keep-armed
H_COALESCE="$HOMES/coalesce"; new_home "$H_COALESCE"
bind_package "$H_COALESCE" "$P_COALESCE" ext-coalesce --timeout-ms 1000 >/dev/null || exit 1
fm_test_track_procevent_home "$H_COALESCE" "$FM_PROCEVENT_CLAIM_ROOT"
export FM_PROCEVENT_LAUNCH_FLOOR_SECONDS=1 FM_PROCEVENT_LAUNCH_CONFIRM_SECONDS=10
python3 - "$ROOT" "$TMP_ROOT" "$H_COALESCE" <<'PYDRIVER'
import json,os,pathlib,shutil,subprocess,sys,time
root,tmp,home=map(pathlib.Path,sys.argv[1:])
env=dict(os.environ,FM_HOME=str(home))
code=tmp/'code'
shutil.copytree(root/'bin',code/'bin')
barrier=code/'bin/fm-extension-launch-barrier.mjs'
barrier.rename(code/'bin/original-barrier.mjs')
barrier.write_text('await new Promise(r => setTimeout(r,15000));\nawait import("./original-barrier.mjs");\n')
procevent=code/'bin/fm-procevent.sh'
inbox=home/'state/procevent-inbox'
source='identity-source'
def run(*args):
 cmd=['bash',str(procevent),*args]
 r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=35)
 print('COMMAND',args,'EXIT',r.returncode,'STDOUT',r.stdout,'STDERR',r.stderr,flush=True)
 assert r.returncode==0,(cmd,r)
 return r.stdout
def settled():
 for _ in range(600):
  if not (home/f'state/procevent/{source}.runner').exists(): return
  time.sleep(.05)
 raise AssertionError('runner remained active')
def capture(label,expected_count):
 settled()
 results=sorted(inbox.glob(source+'.*.result'))
 records=[dict(file=p.name,result=json.loads(p.read_text())) for p in results]
 print('CAPTURES',label,json.dumps(records,sort_keys=True),flush=True)
 assert len(records)==expected_count,records
 assert not list(inbox.glob(source+'.*.handled'))
 return records
# Registration uses the normal host, before injecting delayed barrier startup.
normal=['bash',str(root/'bin/fm-procevent.sh'),'register-extension','ext-coalesce',source,'--config-ref','timeout']
r=subprocess.run(normal,env=env,capture_output=True,text=True,timeout=20)
print('REGISTER',r.returncode,r.stdout,r.stderr,flush=True)
assert r.returncode==0
try:
 for i in range(2):
  run('start',source)
  first=capture('launch-ready-'+str(i),1)
  d=first[0]['result']['deadline']
  assert d['bound']=='launch-ready' and d['operation']=='handshake' and d['grace_ms']==0,d
 # Same source and binding, different bound. It must allocate a second capture.
 barrier.unlink()
 (code/'bin/original-barrier.mjs').rename(barrier)
 for i in range(2):
  run('start',source)
  both=capture('invoke-'+str(i),2)
  d=both[1]['result']['deadline']
  assert d['bound']=='invoke' and d['operation']=='source.poll' and d['grace_ms']==0,d
 # Two successful adapter results shaped like host errors must remain distinct.
 run('register-extension','ext-coalesce',source,'--config-ref','host-error-output')
 for i in range(2):
  run('start',source)
  capture('successful-host-shaped-'+str(i),3+i)
 print('PASS timing diagnostics coalesce, distinct bounds remain distinct, successful results remain distinct',flush=True)
finally:
 settled()
PYDRIVER
