import json, os, pathlib, shutil, subprocess, sys, time
root = pathlib.Path.cwd()
lab = root / (root / '.local-test/active-lab').read_text().strip()
state = lab / 'state'
cli = root / 'bin/fm-task-job.sh'
env = os.environ.copy()
for k in list(env):
    if k.startswith('FM_') or k in ('TASKS_AXI_FILE', 'TASKS_AXI_BACKEND'):
        env.pop(k)
env['FM_HOME'] = str(lab)
tasks = []

def run(args, task=None, expected=0):
    e = env.copy()
    if task:
        e['FM_TASK_INBOX'] = str(state / (task + '.inbox'))
    p = subprocess.run([str(cli)] + args, env=e, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print('$ bin/fm-task-job.sh ' + ' '.join(args), flush=True)
    print(p.stdout, end='', flush=True)
    assert p.returncode == expected, (p.returncode, expected)
    return p.stdout

def setup(task, gen='live-A'):
    tasks.append(task)
    inbox = state / (task + '.inbox')
    (inbox / 'handled').mkdir(parents=True)
    meta(task, gen)
    return inbox

def meta(task, gen):
    (state / (task + '.meta')).write_text('kind=ship\nharness=codex\nspawn_gen=' + gen + '\nwindow=\n')

def start(task, command, timeout=30):
    out = run(['start', '--timeout', str(timeout), '--'] + command, task)
    jid = next(l[5:] for l in out.splitlines() if l.startswith('job: '))
    return state / (task + '.inbox/jobs') / jid

def wait(pred, seconds=25):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if pred():
            return
        time.sleep(.1)
    raise AssertionError('deadline expired')

def alive(pid):
    p = subprocess.run(['ps','-p', str(pid), '-o','stat='], text=True, stdout=subprocess.PIPE)
    return p.returncode == 0 and p.stdout.strip() and not p.stdout.strip().startswith('Z')

def pid(path):
    return int(next(l[4:] for l in path.read_text().splitlines() if l.startswith('pid=')))

def capture(inbox, job):
    wait(lambda: (job / 'delivered').exists())
    wait(lambda: not alive(pid(job / 'runner')))
    records = list(inbox.glob('*.msg'))
    assert len(records) == 1, records
    print('Persisted completion:\n' + records[0].read_text(), flush=True)
    print('Command output:\n' + (job / 'output').read_text(), flush=True)
    return records[0].read_text()

try:
    print('Candidate: ' + subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip())
    print('Real CLI and detached command processes. No worker endpoint, terminal stub, or fake executable.\n')
    inbox = setup('cli-complete')
    job = start('cli-complete', ['sh','-c','sleep 1; echo actual-monitor-result; exit 3'])
    body = capture(inbox, job)
    assert 'command exited with status 3' in body
    assert 'Task: cli-complete; started by worker generation live-A.' in body
    assert 'actual-monitor-result' in (job/'output').read_text()
    print('PASS: one durable completion with exit status, task, generation and output.\n')

    inbox = setup('cli-generation')
    job = start('cli-generation', ['sh','-c','sleep 2; echo generation-result'])
    meta('cli-generation', 'live-B')
    body = capture(inbox, job)
    assert 'started by worker generation live-A.' in body
    assert 'spawn_gen=live-B' in (state/'cli-generation.meta').read_text()
    print('PASS: completion preserves live-A while current metadata is live-B.\n')

    inbox = setup('cli-timeout')
    childpid = lab/'timeout-child.pid'
    job = start('cli-timeout', ['sh','-c','sleep 60 & echo $! > "$1"; wait','job-command',str(childpid)], timeout=1)
    body = capture(inbox, job)
    assert 'passed its 1-second timeout and was stopped' in body
    assert childpid.exists()
    wait(lambda: not alive(int(childpid.read_text())))
    wait(lambda: not alive(pid(job/'child')))
    print('PASS: timeout stops command and grandchild and delivers timed-out result.\n')

    inbox = setup('cli-stop')
    childpid = lab/'stop-child.pid'
    job = start('cli-stop', ['sh','-c','sleep 60 & echo $! > "$1"; wait','job-command',str(childpid)], timeout=8)
    wait(childpid.exists)
    runner, child, grandchild = pid(job/'runner'), pid(job/'child'), int(childpid.read_text())
    run(['stop-all',str(state),'cli-stop'])
    for p in (runner, child, grandchild):
        wait(lambda p=p: not alive(p))
    assert not list(inbox.glob('*.msg'))
    assert not (job/'exit').exists()
    shutil.rmtree(inbox)
    time.sleep(9)
    assert not inbox.exists()
    print('PASS: stop-all stops runner, command and grandchild without delivery. Removed inbox stays absent beyond deadline.\n')

    run(['start','--timeout','5','--','true'], expected=1)
    inbox = setup('cli-refuse')
    run(['start','--','true'], 'cli-refuse', expected=2)
    run(['start','--timeout','9999999','--','true'], 'cli-refuse', expected=2)
    (state/'cli-refuse.meta').write_text('kind=ship\nharness=codex\nwindow=\n')
    run(['start','--timeout','5','--','true'], 'cli-refuse', expected=1)
    assert not (inbox/'jobs').exists()
    print('PASS: missing identity, timeout and generation are refused without creating jobs.\n')
finally:
    for task in tasks:
        subprocess.run([str(cli),'stop-all',str(state),task], env=env, check=True)
    print('Cleanup: stop-all completed for each disposable task.', flush=True)
