import pathlib
p=pathlib.Path('~/.no-mistakes/evidence/01M7MY35E4WW54AP861E58C2N1/live-scratch.py')
prefix=p.read_text().split('\ntry:\n')[0].replace("E/'live-scratch.log'","E/'live-boundaries.log'")
exec(prefix)
home=B/'lab'; proj=B/'project'; origin=B/'origin.git';env['FM_HOME']=str(home)
wt=next(pathlib.Path(l[9:]) for l in run('git','worktree','list','--porcelain',cwd=proj).stdout.splitlines() if l.startswith('worktree ') and l[9:]!=str(proj))
def brief(task):
 write(home/'data'/task/'brief.md',"# Task\n## Captain's intent\nExercise reserved scratch refusal.\n\n## Firstmate spec\nUse a synthetic sleeping workload.\n")
def update_origin():
 run('git','add','-A',cwd=proj);run('git','commit','-qm','synthetic collision fixture',cwd=proj);run('git','fetch','-q',proj,'HEAD:refs/heads/main',cwd=origin)
try:
 run('tmux','-S',sock,'-f','/dev/null','new-session','-d','-s','fm-lab-scratch','-x','120','-y','40','-c',R,'/bin/bash --noprofile --norc');server=True
 pid=run('tmux','-S',sock,'display-message','-p','-t','fm-lab-scratch','#{pid}').stdout.strip();env['TMUX']=f'{sock},{pid},0'
 for variant in ['file','symlink','unignored','tracked']:
  task='collision-'+variant;brief(task)
  if variant=='file': write(wt/'.fm-scratch','preserve project bytes\n')
  if variant=='symlink':
   write(B/'symlink-target/keep','untouched\n');(wt/'.fm-scratch').symlink_to(B/'symlink-target',target_is_directory=True)
  if variant=='unignored': write(proj/'.gitignore','/cache/\n!/.fm-scratch/\n');update_origin()
  if variant=='tracked':
   write(proj/'.gitignore','/cache/\n');write(proj/'.fm-scratch/keep','tracked content\n');update_origin()
  p=run('bash','bin/fm-spawn.sh',task,proj,'--mode','local-only','--yolo','off','/bin/sleep 600',expected=1)
  assert ('refusing to reserve worker scratch' if variant!='unignored' else 'refusing to launch with visible worker scratch') in p.stdout
  assert not (home/'state'/f'{task}.meta').exists()
  if variant=='file': assert (wt/'.fm-scratch').read_text()=='preserve project bytes\n';(wt/'.fm-scratch').unlink()
  if variant=='symlink': assert (wt/'.fm-scratch').is_symlink() and (B/'symlink-target/keep').read_text()=='untouched\n';(wt/'.fm-scratch').unlink()
  if variant=='tracked': assert (wt/'.fm-scratch/keep').read_text()=='tracked content\n'
  log.write(f'S3: real spawn refused {variant} collision, preserved content and published no task metadata\n')
 log.write('COLLISIONS_COMPLETED\n')
finally:
 if server:run('tmux','-S',sock,'kill-server',expected=None)
 log.close()
