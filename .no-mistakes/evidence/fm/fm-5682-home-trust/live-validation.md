# Trust boundary live validation

Candidate: c068fd93350acb2a03ea8845d3e2b450a2a57e23
Baseline: e9a6675ed188f3d77639cfe753451e07d68ab6a6

The executable trust helper ran against real Git repositories and linked worktrees with isolated HOME and Claude stores. No executable was mocked. The spawn checks used real Treehouse and tmux on a disposable lab socket with a 120 by 40 terminal. They intentionally stopped before Claude launched.

## Trust registration

### home equals primary

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project' is the home directory, not a project root
```

### home below primary

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project' contains the home directory '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project/users/me', so it is not a project root
```

### config equals primary

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project' is the Claude config directory, not a project root
```

### config below primary

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project' contains the Claude config directory '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project/config', so it is not a project root
```

### symlink HOME resolves to primary

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project' is the home directory, not a project root
```

### symlink project resolves to HOME

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project' is the home directory, not a project root
```

### linked project argument canonicalizes to protected primary

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project' is the home directory, not a project root
```

### target contains HOME

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker' contains the home directory '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker/user', so it is not a task worktree
```

### target contains config

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker' contains the Claude config directory '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker/config', so it is not a task worktree
```

### filesystem root target

Exit: 1. Store unchanged: True. Observed result matched the scenario: True.

```text
error: refusing to pre-register Claude trust: '/' is the filesystem root, not a task worktree
```

### safe sibling with shared text prefix

Exit: 0. Store unchanged: False. Observed result matched the scenario: True.

```text
trusted: /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker
trusted (project root): /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project
```

### ordinary project outside HOME

Exit: 0. Store unchanged: False. Observed result matched the scenario: True.

```text
trusted: /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker
trusted (project root): /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project
```

### baseline reproduces HOME equality trust

Exit: 0. Store unchanged: False. Observed result matched the scenario: True.

```text
trusted: /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker
trusted (project root): /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project
```

### baseline reproduces HOME ancestor trust

Exit: 0. Store unchanged: False. Observed result matched the scenario: True.

```text
trusted: /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/worker
trusted (project root): /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.trust-live-z25fy0lb/project
```

## Spawn refusal

### HOME equals primary

Exit: 1. Store unchanged: True. Task metadata, busy state and busy generation absent.

```text
fm-gate-refuse: gate agent lifecycle permitted only against lab home /tmp/fm-lab.b60pbuj4
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-n7jsw2un/project' is the home directory, not a project root
error: could not pre-register Claude workspace trust for /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-n7jsw2un/pool/.treehouse/project-58d099/1/project; refusing to launch a claude worker that would wedge on the trust dialog; inspect window primary:fm-trustrefused
primary:bash bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068
primary:fm-trustrefused bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-n7jsw2un/pool/.treehouse/project-58d099/1/project
```

### HOME below primary

Exit: 1. Store unchanged: True. Task metadata, busy state and busy generation absent.

```text
fm-gate-refuse: gate agent lifecycle permitted only against lab home /tmp/fm-lab.3nc9qg5o
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-se2c16d9/project' contains the home directory '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-se2c16d9/project/users/me', so it is not a project root
error: could not pre-register Claude workspace trust for /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-se2c16d9/pool/.treehouse/project-d2c266/1/project; refusing to launch a claude worker that would wedge on the trust dialog; inspect window primary:fm-trustrefused
primary:bash bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068
primary:fm-trustrefused bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-se2c16d9/pool/.treehouse/project-d2c266/1/project
```

### Config equals primary

Exit: 1. Store unchanged: True. Task metadata, busy state and busy generation absent.

```text
fm-gate-refuse: gate agent lifecycle permitted only against lab home /tmp/fm-lab.xoynld8w
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-1lttqqag/project' is the Claude config directory, not a project root
error: could not pre-register Claude workspace trust for /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-1lttqqag/pool/.treehouse/project-b12ef2/1/project; refusing to launch a claude worker that would wedge on the trust dialog; inspect window primary:fm-trustrefused
primary:bash bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068
primary:fm-trustrefused bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-1lttqqag/pool/.treehouse/project-b12ef2/1/project
```

### Config below primary

Exit: 1. Store unchanged: True. Task metadata, busy state and busy generation absent.

```text
fm-gate-refuse: gate agent lifecycle permitted only against lab home /tmp/fm-lab.jt7epc7s
error: refusing to pre-register Claude trust: '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-wycxusbi/project' contains the Claude config directory '/Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-wycxusbi/project/claude-config', so it is not a project root
error: could not pre-register Claude workspace trust for /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-wycxusbi/pool/.treehouse/project-03402b/1/project; refusing to launch a claude worker that would wedge on the trust dialog; inspect window primary:fm-trustrefused
primary:bash bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068
primary:fm-trustrefused bash /Users/daddy/.no-mistakes/worktrees/9e8480867796/01M3F3ECWQZ7XRPK1V9F37K068/.spawn-live-wycxusbi/pool/.treehouse/project-03402b/1/project
```

All private tmux servers and temporary labs were removed. The working tree is clean.

The focused `bash tests/fm-claude-trust.test.sh` run exited 0. Its stubbed spawn tests supplement the live results and are not counted as live evidence. No full suite, linter, formatter or static analysis ran.
