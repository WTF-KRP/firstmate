import os, subprocess, pathlib, json, re
root=pathlib.Path.cwd(); ev=pathlib.Path('~/.no-mistakes/evidence/01M7EB8N33JGRNN31XGPFQ318P')
env=os.environ.copy()
for k in ('FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE','FM_GATE_REFUSE_BYPASS','FM_TEST_SEAM','FM_TEST_HARNESS','FM_SUPERVISION_ACTOR','FM_BRANCH_REPORT_TURN'):
    env.pop(k,None)
home=root/'.l'; env['FM_HOME']=str(home)
def run(*args,ok=True):
    p=subprocess.run([str(root/args[0]),*args[1:]],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=100)
    print('$ '+' '.join(args)+'\n'+p.stdout+'exit='+str(p.returncode),flush=True)
    if ok: assert p.returncode==0
    return p

def append(task,verdict,summary):
    return run('bin/fm-branch-outcome.sh','append','--task',task,'--verdict',verdict,'--summary',summary)

def contents(name):
    p=home/'state'/name
    return p.read_text() if p.exists() else '<absent>'
print('candidate='+subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),flush=True)
run('bin/fm-afk-contract.sh','enter','--words','Observe synthetic lab decisions. No external operations authorized.')
append('red-control','captain','RED_CONTROL: red merge requires captain')
append('design','firstmate','DESIGN: select an in-scope design under approved authority')
append('qualification','firstmate','PAUSED_MAIN: release an already approved local qualification run')
assert not (home/'state'/'.wake-queue').exists()
print('STORE-FIRST INTERRUPTED STATE: persisted outcomes, no handoff queue',flush=True)
print(contents('branch-outcomes.jsonl'),flush=True)
away=run('bin/fm-wake-drain.sh').stdout
assert 'DESIGN:' in away and 'PAUSED_MAIN:' in away and 'MAIN owns this decision' in away
assert 'RED_CONTROL:' not in away
assert not (home/'state'/'.branch-outcomes-cursor').exists()
assert not (home/'state'/'.branch-outcomes-processed').exists()
print('DURABLE QUEUE BEFORE READ ADVANCEMENT:\n'+contents('.wake-queue'),flush=True)
m=re.search(r'WAKE_ACK_REQUIRED: after handling completes run bin/fm-wake-drain.sh --ack-through (\d+) --recovery-generation (\S+)',away)
assert m
run('bin/fm-wake-drain.sh','--ack-through',m[1],'--recovery-generation',m[2])
assert contents('.wake-queue') in ('','<absent>')
run('bin/fm-branch-outcome.sh','recover-handoffs')
run('bin/fm-branch-outcome.sh','recover-handoffs')
assert contents('.wake-queue') in ('','<absent>')
print('RESTART RECOVERY: acked Firstmate checks stayed absent despite unread captain row; checkpoint='+contents('.branch-handoffs-recovered'),flush=True)
run('bin/fm-afk-contract.sh','archive')
returned=run('bin/fm-wake-drain.sh').stdout
assert 'RED_CONTROL:' in returned and 'DESIGN:' not in returned and 'PAUSED_MAIN:' not in returned
assert not (home/'state'/'.branch-outcomes-processed').exists()
print('RETURN: only red control presented; captain processed marker absent',flush=True)
# Independent attended store-first recovery path.
home=root/'.l'/'attended'; env['FM_HOME']=str(home)
run('bin/fm-lab-home.sh','create',str(home)); (home/'config'/'supervision-host').touch()
append('saved','firstmate','ATTENDED_RECOVERY: saved MAIN decision before handoff')
out=run('bin/fm-wake-drain.sh').stdout
assert 'ATTENDED_RECOVERY:' in out and 'MAIN owns this decision' in out
assert 'firstmate-outcome:1' in contents('.wake-queue') and contents('.branch-outcomes-cursor').strip()=='1'
print('ATTENDED: durable wake exists before read cursor 1',flush=True)
# Failed delivery may not advance state. Bad checkpoint must fail closed.
home=root/'.l'/'failure'; env['FM_HOME']=str(home)
run('bin/fm-lab-home.sh','create',str(home)); (home/'config'/'supervision-host').touch()
append('blocked','firstmate','FAILURE_RETRY: delivery must remain retryable')
(home/'state'/'.wake-queue').mkdir()
p=run('bin/fm-branch-outcome.sh','recover-handoffs',ok=False); assert p.returncode!=0
assert not (home/'state'/'.branch-handoffs-recovered').exists() and not (home/'state'/'.branch-outcomes-cursor').exists()
(home/'state'/'.wake-queue').rmdir()
run('bin/fm-branch-outcome.sh','recover-handoffs')
assert 'FAILURE_RETRY:' in contents('.wake-queue')
(home/'state'/'.branch-handoffs-recovered').write_text('malformed\n')
p=run('bin/fm-branch-outcome.sh','recover-handoffs',ok=False); assert p.returncode!=0
assert not (home/'state'/'.branch-outcomes-cursor').exists()
print('RECOVERY FAILURE: delivery retried successfully; malformed checkpoint refused without read advancement',flush=True)
print('ALL DIRECT CLI ASSERTIONS PASSED',flush=True)
