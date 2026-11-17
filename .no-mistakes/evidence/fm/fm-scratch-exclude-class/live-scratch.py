import os, pathlib, subprocess, json, time, shutil, sys
R=pathlib.Path.cwd(); E=pathlib.Path('~/.no-mistakes/evidence/01M7MY35E4WW54AP861E58C2N1'); B=R/'.fm-scratch/live'; B.mkdir(parents=True,exist_ok=True)
log=(E/'live-scratch.log').open('w',buffering=1)
env=os.environ.copy()
for k in list(env):
 if k.startswith('FM_') or k.startswith('HERDR_') or k in ['TMUX','TASKS_AXI_FILE','TASKS_AXI_BACKEND','REX_SESSION','REX_BLOCK','TERM_PROGRAM']: env.pop(k,None)
for n in ['tmp','os-home','pool']: (B/n).mkdir(exist_ok=True)
env.update(HOME=str(B/'os-home'),TMPDIR=str(B/'tmp'),TREEHOUSE_ROOT=str(B/'pool'),SHELL='/bin/bash',GIT_CONFIG_GLOBAL='/dev/null',GIT_AUTHOR_NAME='Scratch validation',GIT_AUTHOR_EMAIL='scratch@example.invalid',GIT_COMMITTER_NAME='Scratch validation',GIT_COMMITTER_EMAIL='scratch@example.invalid')
def run(*args,cwd=R,expected=0):
 log.write('$ '+ ' '.join(map(str,args))+'\n')
 p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=100)
 log.write(p.stdout+f'[exit {p.returncode}]\n')
 if expected is not None and p.returncode!=expected: raise RuntimeError(f'{args}: expected {expected}, got {p.returncode}')
 return p

def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s)
sock='.fm-scratch/live.sock'; server=False
try:
 # Drive actual Git in this gate worktree; no staged mutations.
 write(R/'.fm-scratch/random name/.fm-lab-home','synthetic marker\n')
 run('git','init','-q',R/'.fm-scratch/nested-repo')
 write(R/'.fm-scratch/nested-repo/output','synthetic output\n')
 run('git','check-ignore','-v','.fm-scratch/random name/.fm-lab-home','.fm-scratch/nested-repo/output')
 p=run('git','status','--porcelain','--untracked-files=all'); assert '.fm-scratch' not in p.stdout
 p=run('git','add','--dry-run','-A'); assert '.fm-scratch' not in p.stdout
 log.write('S1: actual gate worktree scratch excluded from status and broad add dry-run\n')
 # Local synthetic project, real Treehouse pool and tmux, no harness/model substitutions.
 home=B/'lab'; run('bash','bin/fm-lab-home.sh','create',home); env['FM_HOME']=str(home)
 proj=B/'project'; run('git','init','-q','-b','main',proj)
 write(proj/'tracked.txt','deliverable\n'); write(proj/'.gitignore','/cache/\n')
 run('git','add','-A',cwd=proj); run('git','commit','-qm','baseline',cwd=proj)
 origin=B/'origin.git'; run('git','clone','-q','--bare',proj,origin)
 run('git','remote','add','origin',origin,cwd=proj);run('git','fetch','-q','origin',cwd=proj);run('git','remote','set-head','origin','main',cwd=proj)
 run('tmux','-S',sock,'-f','/dev/null','new-session','-d','-s','fm-lab-scratch','-x','120','-y','40','-c',R,'/bin/bash --noprofile --norc'); server=True
 pid=run('tmux','-S',sock,'display-message','-p','-t','fm-lab-scratch','#{pid}').stdout.strip(); env['TMUX']=f'{sock},{pid},0'
 for kind in ['ship','scout']:
  task='scratch-'+kind
  write(home/'data'/task/'brief.md',f"# Task\n## Captain's intent\nVerify disposable scratch with a synthetic sleeping shell.\n\n## Firstmate spec\nNo model is launched. Retain deliverables and isolate disposable files.\n")
  flags=['--mode','local-only','--yolo','off'] if kind=='ship' else ['--scout']
  run('bash','bin/fm-spawn.sh',task,proj,*flags,'/bin/sleep 600')
  meta=home/'state'/f'{task}.meta'; fields=dict(line.split('=',1) for line in meta.read_text().splitlines() if '=' in line); wt=pathlib.Path(fields['worktree'])
  assert (wt/'.fm-scratch').is_dir()
  write(wt/'.fm-scratch/arbitrary name/lab/.fm-lab-home','synthetic lab\n'); run('git','init','-q',wt/'.fm-scratch/nested-repo'); write(wt/'.fm-scratch/nested-repo/result','proof\n')
  p=run('git','status','--porcelain','--untracked-files=all',cwd=wt); assert '.fm-scratch' not in p.stdout
  run('git','add','-A',cwd=wt); p=run('git','diff','--cached','--name-only',cwd=wt); assert '.fm-scratch' not in p.stdout
  write(wt/'src/.fm-scratch/keep.txt','project-owned deliverable\n'); run('git','add','-A',cwd=wt); p=run('git','diff','--cached','--name-only',cwd=wt); assert 'src/.fm-scratch/keep.txt' in p.stdout
  run('git','reset','-q',cwd=wt); shutil.rmtree(wt/'src')
  write(wt/'cache/result','unrelated ignored cache\n')
  if kind=='ship':
   write(wt/'unadded.txt','important uncommitted deliverable\n'); p=run('bash','bin/fm-teardown.sh',task,expected=1); assert 'uncommitted' in p.stdout; assert meta.exists() and (wt/'.fm-scratch').exists() and (wt/'unadded.txt').exists()
   (wt/'unadded.txt').unlink(); log.write('S4: dirty deliverable refuses teardown and retains scratch/task state\n')
  else:
   write(home/'data'/task/'report.md','Synthetic scout complete.\n'); write(home/'state'/f'{task}.meta',meta.read_text()+'decisions_reviewed=1\ndecision_keys=\n')
  run('bash','bin/fm-teardown.sh',task)
  assert not meta.exists() and not (wt/'.fm-scratch').exists()
  assert (wt/'cache/result').read_text()=='unrelated ignored cache\n'
  log.write(f'S2/S3: real {kind} spawn excludes arbitrary scratch, keeps nested deliverable visible; teardown removes only reserved scratch\n')
 log.write('LIVE_COMPLETED\n')
finally:
 if server:
  run('tmux','-S',sock,'kill-server',expected=None)
 log.close()
