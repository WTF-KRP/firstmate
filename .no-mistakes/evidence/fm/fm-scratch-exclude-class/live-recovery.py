import pathlib
p=pathlib.Path('~/.no-mistakes/evidence/01M7MY35E4WW54AP861E58C2N1/live-scratch.py')
exec(p.read_text().split('\ntry:\n')[0].replace("E/'live-scratch.log'","E/'live-recovery.log'"))
home=B/'lab-recovery';run('bash','bin/fm-lab-home.sh','create',home);env['FM_HOME']=str(home);proj=B/'project';sock='.fm-scratch/recovery.sock'
try:
 run('tmux','-S',sock,'-f','/dev/null','new-session','-d','-s','fm-lab-recovery','-x','120','-y','40','-c',R,'/bin/bash --noprofile --norc');server=True
 pid=run('tmux','-S',sock,'display-message','-p','-t','fm-lab-recovery','#{pid}').stdout.strip();env['TMUX']=f'{sock},{pid},0'
 for kind in ['scout','ship']:
  task='recovery-'+kind
  write(home/'data'/task/'brief.md',"# Task\n## Captain's intent\nVerify recovery of a synthetic worktree with unreadable Git metadata.\n\n## Firstmate spec\nNo model is launched.\n")
  flags=['--scout'] if kind=='scout' else ['--mode','local-only','--yolo','off']
  run('bash','bin/fm-spawn.sh',task,proj,*flags,'/bin/sleep 600')
  meta=home/'state'/f'{task}.meta';fields=dict(line.split('=',1) for line in meta.read_text().splitlines() if '=' in line);wt=pathlib.Path(fields['worktree'])
  write(wt/'.fm-scratch/proof','synthetic scratch\n');write(home/'data'/task/'report.md','Recovery report\n')
  write(meta,meta.read_text()+'decisions_reviewed=1\ndecision_keys=\n')
  write(wt/'.git',f'gitdir: {B}/missing-gitdir\n')
  run('git','rev-parse','--is-inside-work-tree',cwd=wt,expected=128)
  flags=['--force'] if kind=='ship' else []
  result=run('bash','bin/fm-teardown.sh',task,*flags,expected=None)
  log.write(f'S5 {kind}: teardown exit={result.returncode}; task_metadata_exists={meta.exists()}\n')
  if result.returncode: raise RuntimeError('real recovery teardown did not complete; inspect consumer failure')
  assert not meta.exists()
 log.write('RECOVERY_COMPLETED\n')
finally:
 if server:run('tmux','-S',sock,'kill-server',expected=None)
 log.close()
