# Live task-job validation

Candidate: d2a5d87166b70167b204aca343edc750d2eadb5f.
Source worktree: /Users/daddy/.no-mistakes-upstream-codex/worktrees/b215f934cec2/01M5ZWWWRRKX9F0YGJFT6JHPKR.

Only real product commands and processes count as live below. The four targeted behavior test files use test doubles and do not establish live worker delivery.

## S6: decimal timeout, whole-group timeout cleanup and timezone identity

Created the disposable marked home with:

```text
bin/fm-lab-home.sh create /Users/daddy/.no-mistakes-upstream-codex/evidence/01M5ZWWWRRKX9F0YGJFT6JHPKR/cli-lab
```

Created disposable metadata for timeout and timezone tasks, each with its own spawn generation. Launched the real CLI with FM_HOME pointing at this home, FM_TASK_INBOX pointing at the appropriate task inbox, and inherited path overrides unset.

```text
FM_TASK_JOB_KILL_GRACE_SECS=01 bin/fm-task-job.sh start --timeout 010 -- perl -e '$|=1; $SIG{TERM}="IGNORE"; print "TERM-ignoring child $$\n"; sleep 60'
job: 20261030T121745Z-91934
until: 2026-10-30T12:18Z
```

The public persisted job/exit/output contracts reported:

```text
task=timeout
gen=live-timeout-generation
timeout=10
started=1793362665
deadline=1793362675
outcome=timed-out
status=137
ended=1793362677
runner pid=92246
child pid=92378
TERM-ignoring child 92378
```

The requested ten-second bound remained decimal. The TERM-ignoring child was killed after the bound and grace. This direct CLI case did not exercise watcher delivery of the timeout result.

```text
TZ=UTC FM_TASK_JOB_KILL_GRACE_SECS=01 bin/fm-task-job.sh start --timeout 060 -- sleep 60
job: 20261030T121755Z-10045
until: 2026-10-30T12:19Z
bin/fm-task-job.sh stop-all <cli-lab>/state timezone
stop_all_exit=0
host_timezone=EDT
```

Persisted records:

```text
task=timezone
gen=live-timezone-generation
timeout=60
started=1793362675
deadline=1793362735
stopped=1
runner pid=10551
runner start=Fri Oct 30 12:17:55 2026
child pid=10793
child start=Fri Oct 30 12:17:55 2026
```

Verification against the actual process table:

```text
ps -p 10551,10793,92246,92378 -o pid=,pgid=,stat=,comm=
ps_exit=1
ps -axo pid=,pgid=,stat= | awk '$2 == 10551 || $2 == 92246 {print; found=1} END {if (!found) print "both_job_groups_empty"}'
both_job_groups_empty
```

## S10: invalid and retired launches

Ran the real `bin/fm-task-job.sh start` command with missing FM_TASK_INBOX, metadata lacking spawn_gen, an absent retired task's metadata, and timeout zero.

```text
fm-task-job: FM_TASK_INBOX is not set; run this from a Firstmate task worker, whose launch exports it
missing_identity_exit=1
fm-task-job: the metadata for invalid records no spawn_gen, so its completion cannot be keyed
missing_generation_exit=1
fm-task-job: no task metadata for retired at <cli-lab>/state/retired.meta; the task may have been retired
retired_task_exit=1
fm-task-job: --timeout must be from 1 to 604800 seconds
invalid_timeout_exit=2
inbox_absent=invalid
inbox_absent=retired
```

## Live primary attempts and blocked scenarios

Minted /var/folders/gn/m0fr4_4962q75gpmcl14_z0w0000gn/T//fm-lab.26p3Sb with bin/fm-lab-home.sh. Started the normal Codex CLI as the session command on that home's private tmux socket, at a nonzero 120 by 40 grid, in the candidate worktree. Used the runbook's env-unset list and explicit FM_HOME.

Codex displayed an update offer. Escape skipped that offer without installing anything. The next captured screen was:

```text
Hooks need review
4 hooks are new or changed.
Hooks can run outside the sandbox after you trust them.
1. Review hooks
2. Trust all and continue
3. Continue without trusting (hooks won't run)
```

No hook-consent choice was answered. Stopped only this private tmux server. Started the normal Claude CLI through the same isolated launch recipe, without changing login or trust configuration. Its captured screen was:

```text
Accessing workspace:
/Users/daddy/.no-mistakes-upstream-codex/worktrees/b215f934cec2/01M5ZWWWRRKX9F0YGJFT6JHPKR
Quick safety check: Is this a project you created or one you trust?
Claude Code'll be able to read, edit, and execute files here.
No, exit
Yes, I trust this folder
```

No workspace-consent choice was answered. These modal gates prevented creating and driving real disposable workers for S1-S4 and S7-S9. No worker completion, ring, acknowledgement, hold release, retry, escalation, recursive retirement or concurrent retirement was claimed from these attempts. No Herdr session was provisioned or touched. Another terminal backend would not resolve these CLI consent gates.

The operator must review the Codex hooks or Claude workspace trust in this exact worktree before the normal primary/worker path can proceed. This test phase was explicitly forbidden to answer those dialogs or edit trust stores.

## S5: startup-failure probe refused

Created disposable startup task metadata, then attempted this exact command:

```sh
env -u FM_ROOT_OVERRIDE -u FM_STATE_OVERRIDE -u FM_DATA_OVERRIDE -u FM_CONFIG_OVERRIDE -u FM_PROJECTS_OVERRIDE FM_HOME=/Users/daddy/.no-mistakes-upstream-codex/evidence/01M5ZWWWRRKX9F0YGJFT6JHPKR/cli-lab FM_TASK_INBOX=/Users/daddy/.no-mistakes-upstream-codex/evidence/01M5ZWWWRRKX9F0YGJFT6JHPKR/cli-lab/state/startup.inbox bin/fm-task-job.sh start --timeout 5 -- sh -c 'kill -KILL "$PPID"; sleep 1'
printf 'startup_exit=%s\n' "$?"
```

PreToolUse rejected it before execution:

```text
BLOCKED: Indirect command execution not allowed.
```

Stopped this probe without changing its form or switching tools. Guard-owner authorization of an allowed fault-injection command is required to drive this case live.

## Retained labs and cleanup

Stopped the lab's private tmux server after both primary attempts. Final `tmux -L fm-lab kill-server`, with TMUX_TMPDIR set to the lab's own tmux directory, returned 0. Both task-job process groups were independently confirmed empty. No real fleet data, shared session, trust store, credential, package, global configuration or source file was intentionally changed.

Lab directories remain as explicitly requested:

- /var/folders/gn/m0fr4_4962q75gpmcl14_z0w0000gn/T//fm-lab.26p3Sb
- /Users/daddy/.no-mistakes-upstream-codex/evidence/01M5ZWWWRRKX9F0YGJFT6JHPKR/cli-lab

The CLI lab contains the actual job records, argv, output, exit, runner and child records. `git status --short` was empty after these checks. No screenshots were taken because the change alters CLI completion behavior rather than visual layout. The captured terminal text and persisted product records are the evidence.

## Targeted behavior checks

Ran each affected test file as its own plain top-level command against the exact candidate. All four completed with exit status 0:

```text
bash tests/fm-task-job.test.sh
bash tests/fm-task-inbox.test.sh
bash tests/fm-teardown.test.sh
bash tests/fm-teardown-endpoint-safety.test.sh
```

These checks include the existing startup-record retention and failed-hold-lookup regressions, independent completion retry and escalation, hold preservation, runner identity safety, and recursive teardown. They use test doubles and are supplemental behavioral evidence, not live model-driven proof. The teardown file reported platform-specific skipped branches for Darwin stat behavior. No baseline revision was executed. No complete repository suite, linter, formatter, static analysis, publishing or pipeline-control command was run by this phase.

Overall: S6 and S10 passed live through the product CLI. S1-S5 and S7-S9 remain untested end to end. The live-validation verdict is inconclusive.
