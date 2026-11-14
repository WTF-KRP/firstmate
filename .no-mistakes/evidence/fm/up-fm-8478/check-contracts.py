from pathlib import Path
import subprocess,os,json
root=Path.cwd(); lab=root/'.tools/fm8478/contracts2'; evidence=Path('~/.no-mistakes/evidence/01M7DX6WEE2RPYFAECVX8QYV31'); log=[]
env=os.environ.copy()
for key in ['FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE','FM_SUPERVISION_ACTOR','FM_BRANCH_REPORT_TURN']:env.pop(key,None)
env['FM_HOME']=str(lab)
def run(args,input=None,ok=0):
 p=subprocess.run(args,cwd=root,env=env,input=input,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log.append('$ '+ ' '.join(map(str,args))+'\n'+p.stdout+f'EXIT={p.returncode}\n')
 (evidence/'contract-checks.txt').write_text('\n'.join(log))
 if ok is not None:assert p.returncode==ok,log[-1]
 return p
run(['bin/fm-lab-home.sh','create',str(lab)])
(lab/'config/backlog-backend').write_text('manual\n')
(lab/'data/backlog.md').write_text('# Backlog\n')
run(['bin/fm-afk-contract.sh','enter','--words','Continue approved work; hold red merges.'])
for verdict,summary in [('captain','red merge remains held'),('firstmate','design choice belongs to MAIN'),('routine','worker continues approved work')]:
 run(['bin/fm-branch-outcome.sh','append','--task','fleet','--verdict',verdict,'--summary',summary])
run(['bin/fm-branch-outcome.sh','handoff','--seq','2'])
run(['bin/fm-branch-outcome.sh','handoff','--seq','2'])
run(['bash','-c','. bin/fm-wake-lib.sh; fm_wake_append heartbeat heartbeat heartbeat'])
queue=(lab/'state/.wake-queue').read_text(); log.append('PERSISTED MIXED QUEUE\n'+queue)
assert queue.count('firstmate-outcome:2\t')>=1
for posture in [[],['--afk']]:
 for reason in ['check: rearm-resurface','heartbeat']:
  p=run(['node','bin/fm-branch-dispatch.mjs','offer']+posture,input=reason+'\n');assert 'eligible=0\n' in p.stdout;assert 'rows=\n' in p.stdout
run(['bin/fm-branch-outcome.sh','handoff','--seq','1'],ok=2)
run(['bin/fm-branch-outcome.sh','append','--task','fleet','--verdict','firstmate','--summary','must remain visible','--silent','true'],ok=2)
run(['bin/fm-branch-outcome.sh','mark-read','--through','3'])
p=run(['bin/fm-branch-outcome.sh','mark-processed','--through','2'],ok=None);assert p.returncode!=0
assert not (lab/'state/.branch-outcomes-processed').exists()
assert (lab/'state/.afk-contract').exists()
log.append('CONFIRMED: mixed handoff always stays MAIN-owned; replay retains the durable handoff; firstmate cannot be silent or acknowledge the held captain row; away posture persists.\n')
p=run(['bin/fm-afk-return.sh','begin'],ok=None)
(evidence/'return-brief.txt').write_text(p.stdout+f'\nEXIT={p.returncode}\n')
assert p.returncode==0,p.stdout
assert '3 outcome(s) handled by the away session (1 routine, 1 handed to Firstmate, 1 escalated above)' in p.stdout
assert 'Cost: 3 supervision outcome(s) recorded (1 routine, 1 firstmate, 1 captain)' in p.stdout
assert 'red merge remains held' in p.stdout
log.append('CONFIRMED: return brief counts every verdict and keeps the captain-only red merge in its held list.\n')
(evidence/'contract-checks.txt').write_text('\n'.join(log))
print('MIXED_QUEUE=pass ACKNOWLEDGEMENT_GUARDS=pass RETURN_ACCOUNTING=pass')
