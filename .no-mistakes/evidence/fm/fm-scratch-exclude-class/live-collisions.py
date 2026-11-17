import pathlib
p=pathlib.Path('~/.no-mistakes/evidence/01M7MY35E4WW54AP861E58C2N1/live-scratch.py')
exec(p.read_text().split('\ntry:\n')[0].replace("E/'live-scratch.log'","E/'live-collisions.log'"))
home=B/'lab';env['FM_HOME']=str(home)
try:
 run('tmux','-S',sock,'-f','/dev/null','new-session','-d','-s','fm-lab-scratch','-x','120','-y','40','-c',R,'/bin/bash --noprofile --norc');server=True
 pid=run('tmux','-S',sock,'display-message','-p','-t','fm-lab-scratch','#{pid}').stdout.strip();env['TMUX']=f'{sock},{pid},0'
 for variant in ['file','symlink','unignored','tracked']:
  task='seeded-'+variant;proj=B/task;run('git','init','-q','-b','main',proj)
  write(proj/'tracked.txt','baseline\n')
  if variant in ['file','symlink']:
   write(proj/'.gitignore','/.fm-scratch\n');write(proj/'.worktreeinclude','.fm-scratch\n')
  if variant=='unignored':write(proj/'.gitignore','!/.fm-scratch/\n')
  if variant=='tracked':write(proj/'.fm-scratch/keep','tracked content\n')
  run('git','add','-A',cwd=proj);run('git','commit','-qm','collision fixture',cwd=proj)
  origin=B/(task+'.git');run('git','clone','-q','--bare',proj,origin);run('git','remote','add','origin',origin,cwd=proj);run('git','fetch','-q','origin',cwd=proj);run('git','remote','set-head','origin','main',cwd=proj)
  if variant=='file':write(proj/'.fm-scratch','preserve project bytes\n')
  if variant=='symlink':
   write(B/'symlink-target/keep','untouched\n');(proj/'.fm-scratch').symlink_to(B/'symlink-target',target_is_directory=True)
  write(home/'data'/task/'brief.md',"# Task\n## Captain's intent\nExercise reserved scratch refusal.\n\n## Firstmate spec\nUse a synthetic sleeping workload.\n")
  p=run('bash','bin/fm-spawn.sh',task,proj,'--mode','local-only','--yolo','off','/bin/sleep 600',expected=1)
  assert ('refusing to reserve worker scratch' if variant!='unignored' else 'refusing to launch with visible worker scratch') in p.stdout
  assert not (home/'state'/f'{task}.meta').exists()
  if variant=='file':assert (proj/'.fm-scratch').read_text()=='preserve project bytes\n'
  if variant=='symlink':assert (proj/'.fm-scratch').is_symlink() and (B/'symlink-target/keep').read_text()=='untouched\n'
  if variant=='tracked':assert (proj/'.fm-scratch/keep').read_text()=='tracked content\n'
  log.write(f'S3: real spawn refused {variant} collision; no metadata published and project content preserved\n')
 log.write('COLLISIONS_COMPLETED\n')
finally:
 if server:run('tmux','-S',sock,'kill-server',expected=None)
 log.close()
