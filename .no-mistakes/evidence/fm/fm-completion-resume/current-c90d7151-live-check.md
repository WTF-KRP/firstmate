# Product validation at c90d715152962e81d26fe07ebb81b2345750be26

Worktree: /Users/daddy/.no-mistakes-upstream-codex/worktrees/b215f934cec2/01M5ZWWWRRKX9F0YGJFT6JHPKR

## Live CLI input rejection

These commands ran the real product directly, without test doubles or a fleet home. Each refused before resolving task state.

```text
$ env -u FM_TASK_INBOX bin/fm-task-job.sh start --timeout 5 -- true
fm-task-job: FM_TASK_INBOX is not set; run this from a Firstmate task worker, whose launch exports it
exit: 1

$ env -u FM_TASK_INBOX bin/fm-task-job.sh start --timeout 0 -- true
fm-task-job: --timeout must be from 1 to 604800 seconds
usage: fm-task-job.sh start --timeout <seconds> -- <command> [args...] | stop-all <state-dir> <task-id>
exit: 2

$ env -u FM_TASK_INBOX bin/fm-task-job.sh start --timeout 08z -- true
fm-task-job: --timeout needs a whole number of seconds
usage: fm-task-job.sh start --timeout <seconds> -- <command> [args...] | stop-all <state-dir> <task-id>
exit: 2
```

## Lab setup refused

The attempted disposable lab location was the authorized evidence directory. PreToolUse rejected the entire following command before execution:

```sh
TMPDIR=/Users/daddy/.no-mistakes-upstream-codex/evidence/01M5ZWWWRRKX9F0YGJFT6JHPKR LAB_LABEL=completion-current bash -c 'LAB=$(mktemp -d "${TMPDIR:-/tmp}/fm-lab.XXXXXX") && bin/fm-lab-home.sh create "$LAB"'
```

```text
Command blocked by PreToolUse hook: BLOCKED: Indirect command execution not allowed.
```

The denied operation and dependent lab work stopped. No alternate command form, existing lab, backend, runtime, or guard setting was used to route around this refusal. The current attempt created no lab directory, primary, worker, watcher, or terminal server. Live checks requiring those resources remain untested. A guard-owner-approved lab setup route is required before they can run. The earlier evidence files concern earlier attempts and are not current live proof.

The live scenarios still required are completion and acknowledgement, independent completion retries and steer delivery, status and backlog holds with cleared launcher overrides, failed hold lookup and recovery, startup-failure record retention, bounded job cleanup including a moved command group, identity-safe repeated cleanup, recursive secondmate retirement, concurrent retirement bookkeeping, and invalid/retired task metadata refusal. Supplemental fixture-based tests do not establish these live outcomes.

## Supplemental regression checks

Each file ran as a separate plain top-level command against the exact candidate. All completed with exit status 0:

```text
bash tests/fm-task-job.test.sh
bash tests/fm-task-inbox.test.sh
bash tests/fm-teardown.test.sh
bash tests/fm-teardown-endpoint-safety.test.sh
```

The task-job file exercised the moved-command-group timeout, startup-record retention, hold lookup errors, preserved declarations, keyed completion and acknowledgement, independent retries, process identity, and retirement races. The related files exercised inbox and teardown behavior. They use terminal and service doubles and are supplemental checks, not live worker-resumption evidence. The teardown file reported Darwin-specific skipped ownership-shim and mtime-injection branches. No failing case was reported.

Overall verdict: inconclusive. The real CLI input-rejection checks passed, but lab-dependent live acceptance remains untested. No new source finding or fix was introduced.

## Isolation and evidence limits

The current attempt changed no source files, trust stores, credentials, operator fleet state, global configuration, or packages. Existing lab directories and earlier evidence were left untouched as instructed. No screenshot was produced because no rendered product UI was started in this attempt. The input-rejection commands above expose a text CLI. No baseline checkout was executed, no complete repository suite ran, and no linter, formatter, static analysis, publishing, or pipeline-control command ran.
