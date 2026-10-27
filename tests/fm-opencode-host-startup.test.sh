#!/usr/bin/env bash
# Exercise the OpenCode coordinator's readiness deadlines through its public API.
set -u
# shellcheck source=tests/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
TMP_ROOT=$(fm_test_tmproot fm-opencode-host-startup)
trap fm_test_cleanup EXIT
command -v node >/dev/null 2>&1 || { printf 'skip: node absent\n'; exit 0; }

test_readiness_window() {  # <host-ready|host-expiry|host-explicit|arm>
  local kind=$1 repo home out status
  repo="$TMP_ROOT/$kind/root"
  home="$TMP_ROOT/$kind/home"
  mkdir -p "$repo/bin" "$home/state" "$home/config"
  git init -q "$repo"
  : > "$repo/AGENTS.md"
  : > "$home/state/task.meta"
  cp "$ROOT/bin/fm-supervision-lib.sh" "$ROOT/bin/fm-supervision-engine-lib.sh" "$repo/bin/"
  [ "$kind" = arm ] || : > "$home/config/supervision-host"
  cat > "$repo/bin/fm-watch-arm.sh" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$$" > "$FM_HOME/child-pid"
trap 'exit 0' TERM INT
while [ ! -e "$FM_HOME/ready" ] && [ ! -e "$FM_HOME/stop" ] && [ -e "$0" ]; do sleep 0.02; done
[ ! -e "$FM_HOME/stop" ] || exit 0
printf 'watcher: started pid=%s (beacon fresh)\n' "$$"
while [ ! -e "$FM_HOME/stop" ] && [ -e "$0" ]; do sleep 0.02; done
SH
  cp "$repo/bin/fm-watch-arm.sh" "$repo/bin/fm-supervision-host.sh"
  chmod +x "$repo/bin/fm-watch-arm.sh" "$repo/bin/fm-supervision-host.sh"
  out=$(FM_HOME="$home" WORKTREE="$repo" PLUGIN="$ROOT/.opencode/plugins/fm-primary-watch-arm.js" \
    FM_OPENCODE_ARM_READY_TIMEOUT_MS=12000 FM_SUPERVISION_HOST_READY_TIMEOUT="$([ "$kind" != host-explicit ] || printf 120)" \
    NODE_NO_WARNINGS=1 TEST_KIND="$kind" node --input-type=module 2>&1 <<'JS'
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const sleep = (ms) => new Promise((resolve) => nativeTimeout(resolve, ms));
const nativeTimeout = globalThis.setTimeout;
const nativeClear = globalThis.clearTimeout;
const timers = new Set();
let now = 0;
globalThis.setTimeout = (callback, delay, ...args) => {
  if (delay < 1000) return nativeTimeout(callback, delay, ...args);
  const timer = { at: now + delay, callback: () => callback(...args), unref() { return this; } };
  timers.add(timer);
  return timer;
};
globalThis.clearTimeout = (timer) => { if (!timers.delete(timer)) nativeClear(timer); };
const advance = async (time) => {
  now = time;
  for (const timer of [...timers]) if (timer.at <= now) { timers.delete(timer); timer.callback(); }
  await new Promise(setImmediate);
};
const home = process.env.FM_HOME;
try {
  const mod = await import(pathToFileURL(process.env.PLUGIN).href);
  const client = { session: { promptAsync: async () => {} } };
  await mod.FmPrimaryWatchArm({ client, directory: process.env.WORKTREE, worktree: process.env.WORKTREE });
  writeFileSync(`${home}/state/.lock`, `${process.pid}\n`);
  let status;
  const ready = globalThis.__firstmateOpenCodeWatchArm.ensureArmed("startup-test", client).then((value) => { status = value; });
  for (let i = 0; i < 500 && (!timers.size || !existsSync(`${home}/child-pid`)); i += 1) await sleep(10);
  if (!timers.size || !existsSync(`${home}/child-pid`)) throw new Error("coordinator did not start its readiness wait");
  const deadline = [...timers][0].at;
  if (process.env.TEST_KIND === "arm") {
    await advance(12000);
    await ready;
    if (status !== "timeout") throw new Error(`plain arm lost its configured 12 s bound: ${status}`);
  } else {
    const total = process.env.TEST_KIND === "host-explicit" ? 120000 : 100000;
    await advance(35000);
    if (status !== undefined) throw new Error(`host expired during progressing startup at 35 s: ${status}`);
    await advance(total);
    if (status !== undefined) throw new Error(`host was retired before its ${total} ms total window: ${status}`);
    if (deadline <= total || deadline > total + 10000) throw new Error(`host margin is outside (0, 10 s]: ${deadline - total}`);
    if (process.env.TEST_KIND === "host-expiry") {
      await advance(deadline);
      await ready;
      if (status !== "timeout") throw new Error(`unready host did not expire at its enclosing bound: ${status}`);
    } else {
      writeFileSync(`${home}/ready`, "ready\n");
      for (let i = 0; i < 300 && status === undefined; i += 1) await sleep(10);
      if (status !== "armed") throw new Error(`host did not deliver genuine readiness: ${status}`);
      await ready;
    }
  }
} finally {
  writeFileSync(`${home}/stop`, "stop\n");
  for (let i = 0; i < 200 && existsSync(`${home}/child-pid`); i += 1) {
    try { process.kill(Number(readFileSync(`${home}/child-pid`, "utf8").trim()), 0); } catch { break; }
    await sleep(10);
  }
}
JS
  )
  status=$?
  expect_code 0 "$status" "OpenCode $kind readiness contract: $out"
  pass "OpenCode $kind preserves the enclosing startup bound"
}

for kind in host-ready host-expiry host-explicit arm; do test_readiness_window "$kind"; done
