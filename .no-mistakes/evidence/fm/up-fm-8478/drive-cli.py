import os, pathlib, subprocess, tempfile, json, re, shutil, sys
root=pathlib.Path.cwd()
ev=pathlib.Path('~/.no-mistakes/evidence/01M7EFPKVWB34HQDAX5PBSK5QB')
lab=pathlib.Path(tempfile.mkdtemp(prefix='.nm8478-', dir=root))
env=os.environ.copy()
for k in ['FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE','FM_HOME','FM_BACKEND','FM_SUPERVISION_ACTOR','FM_BRANCH_REPORT_TURN']:
    env.pop(k,None)
env['FM_HOME']=str(lab)
log=open(ev/'cli-product.log','w')
def run(args,expected=0,extra=None,input=None):
    e=env| (extra or {})
    p=subprocess.run(args,cwd=root,env=e,input=input,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    log.write('$ '+ ' '.join(str(x) for x in args)+'\n'+p.stdout+f'EXIT {p.returncode}\n');log.flush()
    assert p.returncode==expected,(args,p.stdout,p.returncode)
    return p.stdout
state=lab/'state'
try:
    run(['bin/fm-lab-home.sh','create',str(lab)])
    (lab/'config/supervision-host').touch()
    run(['bin/fm-afk-contract.sh','enter','--words','watch this disposable fleet'])
    # Independent oracle: Firstmate decisions must be delivered during away, captain acts held.
    (state/'.supervision-host-turn').write_text('turn=live1\nrows=1\ntasks=design release cap\nunscoped=0\nposture=away\nwake=signal: design.status\n')
    branch={'FM_SUPERVISION_ACTOR':'branch','FM_BRANCH_REPORT_TURN':'live1'}
    run(['bin/fm-branch-report.sh','--task','cap','--verdict','captain','--summary','Red merge requires captain decision'],extra=branch)
    for task,summary in [('design','In-scope design choice needs MAIN'),('release','Worker paused waiting for MAIN to release approved local run')]:
        run(['bin/fm-branch-report.sh','--task',task,'--verdict','firstmate','--summary',summary],extra=branch)
    q=(state/'.wake-queue').read_text();log.write('DURABLE WAKE QUEUE\n'+q)
    assert 'firstmate-outcome:2' in q and 'firstmate-outcome:3' in q and 'Red merge' not in q
    run(['bin/fm-branch-report.sh','--task','design','--verdict','firstmate','--summary','hidden decision','--silent','true'],expected=2,extra=branch)
    run(['bin/fm-branch-report.sh','--task','other','--verdict','firstmate','--summary','wrong task'],expected=3,extra=branch)
    scope=run(['node','bin/fm-branch-dispatch.mjs','scope','--afk','--heartbeat'])
    assert re.search(r'^rows=$',scope,re.M),scope
    offer=run(['node','bin/fm-branch-dispatch.mjs','offer','--afk'],input='heartbeat\n')
    assert 'eligible=0' in offer
    drain=run(['bin/fm-wake-drain.sh'])
    assert 'In-scope design choice needs MAIN' in drain and 'Worker paused' in drain and 'Red merge' not in drain
    ack=re.search(r'WAKE_ACK_REQUIRED: after handling completes run bin/fm-wake-drain.sh (.+)',drain)
    assert ack,drain
    import shlex
    run(['bin/fm-wake-drain.sh']+shlex.split(ack.group(1)))
    assert not (state/'.wake-queue').read_text().strip()
    # Store-first crash reproduction: append completed but reporter died before handoff.
    run(['bin/fm-branch-outcome.sh','append','--task','design','--verdict','firstmate','--summary','Saved decision after interrupted reporter'])
    assert 'firstmate-outcome:4' not in (state/'.wake-queue').read_text()
    drain=run(['bin/fm-wake-drain.sh'])
    assert 'Saved decision after interrupted reporter' in drain and 'Red merge' not in drain
    ack=re.search(r'WAKE_ACK_REQUIRED: after handling completes run bin/fm-wake-drain.sh (.+)',drain)
    assert ack
    run(['bin/fm-wake-drain.sh']+shlex.split(ack.group(1)))
    run(['bin/fm-afk-contract.sh','archive'])
    drain=run(['bin/fm-wake-drain.sh'])
    assert 'Red merge requires captain decision' in drain
    assert 'In-scope design choice' not in drain and 'Worker paused' not in drain and 'Saved decision' not in drain
    assert not (state/'.branch-outcomes-processed').exists()
    log.write('OBSERVED: MAIN checks delivered and acknowledged while away. Saved handoff recovered. Captain control held until return. Settled MAIN decisions absent on return.\n')
    run(['bin/fm-branch-outcome.sh','list'])
finally:
    log.close()
    shutil.rmtree(lab)
    print('Disposable CLI home removed:',lab)
