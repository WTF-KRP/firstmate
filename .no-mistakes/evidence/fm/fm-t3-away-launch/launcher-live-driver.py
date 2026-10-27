import os, pathlib, subprocess, tempfile, shutil, json
root=pathlib.Path.cwd()
evidence=pathlib.Path('/Users/daddy/.no-mistakes-upstream-codex/evidence/01M5ZCDBWWQXYNTDPKGB2WD62X')
lab=pathlib.Path(tempfile.mkdtemp(prefix='fm-lab.',dir=root))
log=[]
def note(text):
    log.append(text)
    print(text,flush=True)
env=os.environ.copy()
for key in ['FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE','FM_GATE_REFUSE_BYPASS','FM_TEST_SEAM','FM_TEST_HARNESS','FM_AFK_LAUNCH_ENTRY','FM_SUPERVISOR_TARGET','FM_SUPERVISOR_BACKEND','TMUX_PANE','HERDR_ENV','HERDR_PANE_ID','REX_SESSION','REX_BLOCK','FM_AFK_MODE']:
    env.pop(key,None)
env.update(FM_HOME=str(lab),FM_BACKEND='t3code')
launcher=str(root/'bin/fm-afk-launch.sh')
def run(args,expected,extra=None):
    e=env.copy(); e.update(extra or {})
    p=subprocess.run([launcher,*args],env=e,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    note('$ fm-afk-launch.sh '+' '.join(args)+'\n'+p.stdout+'exit='+str(p.returncode))
    assert p.returncode==expected,(args,p.returncode,expected)
    return p.stdout
try:
    p=subprocess.run(['bin/fm-lab-home.sh','create',str(lab)],text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    note('Marked disposable home created inside the gate worktree. No test seams or entry overrides enabled.')
    p=subprocess.run(['bin/fm-harness.sh'],env=env,text=True,capture_output=True)
    note('Detected primary harness: '+p.stdout.strip()); assert p.stdout.strip()=='codex'
    run(['run-external'],1)
    state=lab/'state'; record=state/'.afk-daemon-terminal'
    for value in ['none\t-\tnative\n','none\tmcp:lab-primary\tt3code:claude\n','none\tmcp:lab-primary\tt3code:pi\n','none\tbad target\tt3code:codex\n']:
        record.write_text(value)
        note('Serialized lifecycle input: '+repr(value))
        run(['run-external'],1)
    record.unlink()
    run(['enter','--words','Isolated launcher verification.'],0)
    run(['prepare-external'],1,{'FM_SUPERVISOR_BACKEND':'tmux','FM_SUPERVISOR_TARGET':'unrelated-pane'})
    assert not record.exists() and not (state/'.afk').exists()
    (lab/'config/supervision-host').touch()
    target={'FM_SUPERVISOR_BACKEND':'t3code','FM_SUPERVISOR_TARGET':'mcp:lab-primary'}
    run(['prepare-external'],1,target)
    assert not record.exists() and not (state/'.afk').exists()
    (lab/'config/supervision-host').unlink()
    run(['prepare-external'],0,target)
    value=record.read_text(); note('Persisted lifecycle: '+repr(value))
    assert value=='none\tmcp:lab-primary\tt3code:codex\n'
    assert (state/'.afk').exists() and not (state/'.afk-launch.lock').exists()
    (state/'.afk-return-catchup').touch()
    run(['run-external'],1,{'FM_SUPERVISOR_BACKEND':'tmux','FM_SUPERVISOR_TARGET':'unrelated-pane'})
    assert record.read_text()==value
    (state/'.afk-return-catchup').unlink()
    out=run(['run-external'],1,{'FM_SUPERVISOR_BACKEND':'tmux','FM_SUPERVISOR_TARGET':'unrelated-pane'})
    assert "supervisor target 'mcp:lab-primary'" in out and 't3code' in out
    note('Actual daemon reached recorded T3 target validation and exited because this lab has no T3 server credential. Delivery and a running-daemon singleton remain untested live.')
    if (state/'.supervise-daemon.log').exists(): note('Daemon log:\n'+(state/'.supervise-daemon.log').read_text())
    assert not (state/'.afk-launch.lock').exists()
    run(['stop'],0)
    assert not record.exists() and not (state/'.afk').exists() and not (state/'.afk-contract').exists()
    assert not (state/'.supervise-daemon.pid').exists()
    note('Ordinary stop removed lifecycle and away flag, archived the posture, and left no daemon pid or launcher lock.')
finally:
    shutil.rmtree(lab)
    note('Disposable lab removed.')
    (evidence/'launcher-live-cli.log').write_text('\n'.join(log)+'\n')
