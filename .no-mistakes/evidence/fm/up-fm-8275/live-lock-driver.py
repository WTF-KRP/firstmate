import os, sys, time, json, subprocess, pathlib, signal
R=pathlib.Path.cwd(); E=pathlib.Path('~/.no-mistakes/evidence/01M776M2AX928VHMD0MWKZ2GNT'); T=R/'.test-8275/live'; T.mkdir(parents=True,exist_ok=True)
LIB=R/'bin/fm-wake-lib.sh'; BASH=subprocess.check_output(['which','bash'],text=True).strip(); dead='999999'
assert subprocess.run(['kill','-0',dead],capture_output=True).returncode != 0
baseenv={k:v for k,v in os.environ.items() if k not in ['FM_HOME','FM_ROOT','FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE','FM_WAKE_QUEUE','FM_WAKE_QUEUE_LOCK','STATE']}
results=[]
def record(name,**data):
    row=dict(name=name,**data); results.append(row); print(json.dumps(row),flush=True)
def home(name):
    h=T/name; p=subprocess.run(['bash','bin/fm-lab-home.sh','create',str(h)],capture_output=True,text=True); assert p.returncode==0,p.stderr; return h
def env(h): return dict(baseenv,FM_HOME=str(h))
def shape(h,name='.lock.acquire',kind='nested',live_suffix=None):
    lock=h/'state'/name
    for suffix in ('','.steal'):
        p=pathlib.Path(str(lock)+suffix); p.mkdir()
        o=p/(p.name+'.owner.fixture') if kind=='nested' else p; o.mkdir(exist_ok=True)
        (o/'pid').write_text((str(os.getpid()) if suffix==live_suffix else dead)+'\n')
        if suffix!=live_suffix: (o/'pid-start').write_text('dead holder\n')
        os.utime(o,(1,1)); os.utime(p,(1,1))
    return lock
def tree(h):
    return {str(p.relative_to(h)): ('link:'+os.readlink(p) if p.is_symlink() else 'directory' if p.is_dir() else p.read_text()) for p in sorted((h/'state').rglob('*'))}
def cli(h,script=None):
    t=time.monotonic(); p=subprocess.run([BASH,str(R/'bin/fm-lock.sh')] if script is None else [BASH,'-c',script,'_',str(LIB),str(h/'state'/'.lock.acquire')],env=env(h),capture_output=True,text=True,timeout=15)
    return p,round(time.monotonic()-t,3)
def lib(h,script,*args,timeout=15):
    return subprocess.run([BASH,'-c','. "$1"; '+script,'_',str(LIB),*map(str,args)],env=env(h),capture_output=True,text=True,timeout=timeout)
# CLI recovery and both named refusal branches, including same-session confirmation.
for mode in ('recover-nested','recover-top-level','refuse-primary','refuse-steal','own-refuse'):
    h=home(mode); lock=shape(h,kind='top-level' if mode=='recover-top-level' else 'nested')
    unknown=None
    if 'refuse' in mode:
        unknown=pathlib.Path(str(lock)+('.steal' if mode=='refuse-steal' else ''))/'unrecognized-record'; unknown.write_text('preserve me\n'); os.utime(unknown.parent,(1,1))
    if mode=='own-refuse':
        prior=subprocess.run([BASH,str(R/'bin/fm-session-lock-lib.sh')],env=env(h),capture_output=True,text=True)
        anchor=subprocess.check_output([BASH,'-c','. "$1"; fm_session_lock_anchor_pid','_',str(R/'bin/fm-session-lock-lib.sh')],env=env(h),text=True).strip(); (h/'state'/'.lock').write_text(anchor+'\n')
    before=tree(h); p,elapsed=cli(h)
    record(mode,command='FM_HOME=<marked disposable home> bash bin/fm-lock.sh',exit=p.returncode,seconds=elapsed,stdout=p.stdout,stderr=p.stderr,before=before,after=tree(h))
    if unknown:
        assert p.returncode==1 and 'cannot reclaim lock directory '+str(unknown.parent) in p.stderr
        assert unknown.read_text()=='preserve me\n' and 'lock acquired:' not in p.stdout
    else:
        assert p.returncode==0 and 'lock acquired:' in p.stdout
        assert not lock.exists() and not pathlib.Path(str(lock)+'.steal').exists()
    assert not list((h/'state').glob('*.owner.*'))
# Actual shared primitive used by the Claude Stop hook, no fake CLI or library.
h=home('stop-hook-lock'); lock=shape(h,'.turnend-claude-blocks.lock',kind='top-level')
p=lib(h,'fm_lock_acquire_wait "$2" || exit 10; printf "held pid=%s symlink=%s\n" "$(cat "$2/pid")" "$(readlink "$2")"; fm_lock_release "$2"; ls -A "$STATE"',lock)
record('stop-hook-lock-recovery',exit=p.returncode,stdout=p.stdout,stderr=p.stderr,after=tree(h)); assert p.returncode==0 and list((h/'state').iterdir())==[]
# Live nested holder is protected even with ancient mtimes at either lock level.
for suffix in ('','.steal'):
    h=home('live-nested'+('steal' if suffix else 'primary')); lock=shape(h,live_suffix=suffix)
    live=pathlib.Path(str(lock)+suffix)/(lock.name+suffix+'.owner.fixture')/'pid'
    p=lib(h,'if fm_lock_try_acquire "$2"; then echo unexpected-acquisition; exit 10; else printf "acquisition refused; live nested owner=%s\n" "$(cat "$3")"; fi',lock,live)
    record('live-nested'+suffix,exit=p.returncode,stdout=p.stdout,after=tree(h)); assert p.returncode==0 and live.read_text().strip()==str(os.getpid())
# Real repeated publication failure must not leave staging directories or stray links.
h=home('create-failure'); lock=h/'state'/'.contend.lock'; lock.mkdir(); (lock/'sentinel').write_text('keep')
p=lib(h,'i=0; while [ "$i" -lt 25 ]; do if fm_lock_try_create "$2"; then exit 10; fi; i=$((i+1)); done; printf "failed create attempts=%s\n" "$i"; ls -la "$STATE" "$2"',lock)
record('failed-create-cleanup',exit=p.returncode,stdout=p.stdout,stderr=p.stderr,after=tree(h)); assert p.returncode==0 and list(lock.iterdir())==[lock/'sentinel'] and list((h/'state').iterdir())==[lock]
# Ordinary caller continues waiting until residue becomes safely reclaimable.
h=home('ordinary-wait'); lock=h/'state'/'.contend.lock'; lock.mkdir(); (lock/'pid').write_text(dead+'\n'); recordfile=lock/'unknown'; recordfile.write_text('preserve me'); os.utime(lock,(1,1))
p=subprocess.Popen([BASH,'-c','. "$1"; fm_lock_acquire_wait "$2" || exit 10; echo acquired-after-residue-removed; fm_lock_release "$2"','_',str(LIB),str(lock)],env=env(h),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    limit=time.monotonic()+10
    while (lock/'pid').exists() and time.monotonic()<limit: time.sleep(.05)
    assert not (lock/'pid').exists() and p.poll() is None and recordfile.read_text()=='preserve me'
    record('ordinary-wait-before-release',process_running=True,unknown_record=recordfile.read_text())
    recordfile.unlink(); os.utime(lock,(1,1)); out,err=p.communicate(timeout=15)
    record('ordinary-wait-after-release',exit=p.returncode,stdout=out,stderr=err,after=tree(h)); assert p.returncode==0
finally:
    if p.poll() is None: p.kill()
    p.wait()
# Symlinked home still applies watcher identity contract without signalling holder.
h=home('identity-physical'); logical=T/'identity-logical'; logical.symlink_to(h,target_is_directory=True)
for mode in ('mismatched','matching','unrecorded'):
    lock=h/'state'/'.watch.lock'; lock.mkdir(); (lock/'pid').write_text(str(os.getpid())+'\n')
    if mode!='unrecorded':
        ident=lib(logical,'fm_pid_identity "$2"',os.getpid()); assert ident.returncode==0
        (lock/'pid-identity').write_text('not the current process identity\n' if mode=='mismatched' else ident.stdout)
    p=lib(logical,'if fm_lock_try_acquire "$2"; then echo acquired; fm_lock_release "$2"; else echo held; fi',logical/'state'/'.watch.lock')
    record('logical-home-identity-'+mode,exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
    assert p.returncode==0 and p.stdout.strip()==('acquired' if mode=='mismatched' else 'held'); os.kill(os.getpid(),0)
    if lock.exists():
        for child in lock.iterdir(): child.unlink()
        lock.rmdir()
# Natural concurrent real reapers. Winners hold until every one-shot attempt returns.
for turn in range(3):
    h=home('race-'+str(turn)); lock=shape(h); gate=h/'start'; release=h/'release'; children=[]
    code='. "$1"; while [ ! -e "$3" ]; do sleep .01; done; if fm_lock_try_acquire "$2"; then printf "%s\n" "${BASHPID:-$$}" > "$4/winner.$5"; : > "$4/done.$5"; while [ ! -e "$6" ]; do sleep .02; done; fm_lock_release "$2"; else : > "$4/done.$5"; fi'
    try:
        for i in range(8): children.append(subprocess.Popen([BASH,'-c',code,'_',str(LIB),str(lock),str(gate),str(h),str(i),str(release)],env=env(h),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
        gate.touch(); limit=time.monotonic()+20
        while len(list(h.glob('done.*')))<8 and time.monotonic()<limit: time.sleep(.05)
        assert len(list(h.glob('done.*')))==8
        winners=[p.read_text().strip() for p in h.glob('winner.*')]; observed=(lock/'pid').read_text().strip() if (lock/'pid').exists() else None
        record('concurrent-reapers-'+str(turn),contenders=8,winners=winners,persisted_pid=observed,lock_target=os.readlink(lock) if lock.is_symlink() else None)
        assert len(winners)<=1 and (not winners or observed==winners[0])
        release.touch()
        for c in children:
            out,err=c.communicate(timeout=15); assert c.returncode==0,(out,err)
    finally:
        release.touch(exist_ok=True)
        for c in children:
            if c.poll() is None: c.kill()
            c.wait()
record('completed',revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),bash=BASH,scenarios='all assertions satisfied')
(E/'live-lock-results.json').write_text(json.dumps(results,indent=2)+'\n')
