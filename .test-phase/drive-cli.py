import os, pathlib, subprocess, time, signal, json
root=pathlib.Path.cwd()
home=root/'.test-phase/home'
state=home/'state'
evidence=pathlib.Path('/Users/daddy/.no-mistakes/evidence/01M5Z1F8G71N131RF7P55AE4CV')
log=open(evidence/'live-task-job-transcript.txt','w',buffering=1)
base=os.environ.copy()
for key in ('FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE'):
    base.pop(key,None)
base['FM_HOME']=str(home)
base['TMPDIR']=str(root/'.test-phase/tmp')
def emit(s):
    print(s,flush=True); log.write(s+'\n')
def run(args,env=None,check=True):
    result=subprocess.run(args,env=env or base,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    emit('$ '+' '.join(map(str,args))+'\n'+result.stdout+f'exit={result.returncode}')
    if check and result.returncode: raise RuntimeError(result.stdout)
    return result

def setup(task,gen='live-gen-A',window=''):
    inbox=state/(task+'.inbox'); (inbox/'handled').mkdir(parents=True)
    (state/(task+'.meta')).write_text(f'kind=scout\nharness=claude\nbackend=herdr\nwindow={window}\nspawn_gen={gen}\n')
    (state/(task+'.status')).write_text(f'paused [at={int(time.time())}]: own task job pending\n')
    env=base.copy(); env['FM_TASK_INBOX']=str(inbox)
    return inbox,env

def waitfor(predicate,seconds=25):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.2)
    raise AssertionError('condition not reached')

def start(task,command,timeout=20,gen='live-gen-A'):
    inbox,env=setup(task,gen)
    out=run([str(root/'bin/fm-task-job.sh'),'start','--timeout',str(timeout),'--']+command,env).stdout
    job=inbox/'jobs'/next(line[5:] for line in out.splitlines() if line.startswith('job: '))
    return inbox,env,job

def pids(job):
    return [int((job/f).read_text().splitlines()[0].split('=')[1]) for f in ('runner','child')]
def active(pid):
    p=subprocess.run(['ps','-p',str(pid),'-o','stat='],text=True,stdout=subprocess.PIPE)
    return p.returncode==0 and bool(p.stdout.strip()) and not p.stdout.strip().startswith('Z')
def record(inbox):
    waitfor(lambda:len(list(inbox.glob('*.msg')))==1)
    rec=next(inbox.glob('*.msg'));emit('Persisted completion:\n'+rec.read_text());return rec

def stop(task):
    run([str(root/'bin/fm-task-job.sh'),'stop-all',str(state),task])

# Public CLI safety boundary, without a worker identity or a valid timeout.
result=run([str(root/'bin/fm-task-job.sh'),'start','--timeout','2','--','true'],check=False)
assert result.returncode==1 and 'FM_TASK_INBOX is not set' in result.stdout
inbox,env=setup('invalid')
result=run([str(root/'bin/fm-task-job.sh'),'start','--timeout','0','--','true'],env,False)
assert result.returncode==2 and not (inbox/'jobs').exists()
emit('S1 PASS: invalid identity and timeout refused without a job')

# Start returns before a real command completes; metadata changes before exit.
inbox,env,job=start('generation',['sh','-c','sleep 3; printf "generation-command-output\\n"; exit 7'])
assert not (job/'exit').exists()
meta=state/'generation.meta';meta.write_text(meta.read_text().replace('live-gen-A','live-gen-B'))
rec=record(inbox)
assert 'worker generation live-gen-A' in rec.read_text() and 'status 7' in rec.read_text()
assert (job/'output').read_text()=='generation-command-output\n'
emit('Command output:\n'+(job/'output').read_text())
emit('S3 PASS: detached completion retains original generation after metadata replacement')

# Timeout stops the command process group, including its own child.
pidfile=root/'.test-phase/grandchild.pid'
inbox,env,job=start('timeout',['sh','-c','sleep 30 & echo $! > "$1"; wait','_',str(pidfile)],2)
waitfor(pidfile.exists)
pid=int(pidfile.read_text());rec=record(inbox)
assert 'outcome=timed-out' in (job/'exit').read_text()
waitfor(lambda:not active(pid))
emit('Timeout exit record:\n'+(job/'exit').read_text()+f'grandchild {pid} active={active(pid)}')
emit('S7 PASS: timeout stops command group and records timeout result')

# Retirement's public stop-all owns both live processes before deleting inbox.
inbox,env,job=start('retirement',['sleep','30'],5)
owned=pids(job);stop('retirement')
waitfor(lambda:not any(active(pid) for pid in owned))
assert not list(inbox.glob('*.msg'))
import shutil
shutil.rmtree(inbox)
time.sleep(6)
assert not inbox.exists()
emit(f'S9 PASS: stop-all stopped {owned}; inbox absent after original deadline')

# The task can disappear before the runner publishes its result.
inbox,env,job=start('removed',['sleep','2'],10)
owned=pids(job);shutil.rmtree(inbox)
waitfor(lambda:not any(active(pid) for pid in owned))
assert not inbox.exists()
emit('S10 PASS: completion after inbox removal does not recreate inbox')

# Real watcher recovery with real Herdr endpoint and declared hold. It must
# recover and persist the lost result without typing into the consent screen.
for task in ('proof','claudeproof'):
    (state/(task+'.meta')).unlink(missing_ok=True)
inbox,env,job=start('recover',['sleep','60'],90)
(state/'recover.meta').write_text('kind=scout\nharness=claude\nbackend=herdr\nwindow=fm-lab-completion-36870-31069:w2:p1\nherdr_session=fm-lab-completion-36870-31069\nherdr_pane_id=w2:p1\nspawn_gen=live-gen-A\n')
(state/'recover.status').write_text(f'needs-decision [key=live-recovery] [at={int(time.time())}]: retain recovered result during decision\n')
runner,child=pids(job);os.kill(runner,signal.SIGKILL);waitfor(lambda:not active(runner))
watchenv=base.copy();watchenv.update(FM_BACKEND='herdr',FM_POLL='1',FM_SIGNAL_GRACE='1',FM_CHECK_INTERVAL='999999',FM_HEARTBEAT='999999')
watchlog=open(evidence/'live-watcher-output.txt','w')
watch=subprocess.Popen([str(root/'bin/fm-watch.sh')],env=watchenv,stdout=watchlog,stderr=subprocess.STDOUT)
try:
    rec=record(inbox)
    assert 'outcome=lost' in (job/'exit').read_text()
    waitfor(lambda:not active(child))
    handled=inbox/'handled'/rec.name;rec.rename(handled)
    (job/'delivered').unlink()
    time.sleep(5)
    assert not list(inbox.glob('*.msg')) and (job/'delivered').exists()
    emit('Lost exit record:\n'+(job/'exit').read_text())
    emit(f'S8 PASS: real watcher recovered killed runner {runner}, stopped child {child}, persisted one lost notice and kept acknowledgement')
finally:
    watch.terminate()
    try:watch.wait(timeout=10)
    except subprocess.TimeoutExpired:watch.kill();watch.wait()
    watchlog.close()
    stop('recover')
log.close()
