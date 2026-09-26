import os,pathlib,subprocess,tempfile,shutil,json,sys
mode=sys.argv[1] if len(sys.argv)>1 else "home-equal"
root=pathlib.Path.cwd(); ev=pathlib.Path('/Users/daddy/.no-mistakes/evidence/01M3F3ECWQZ7XRPK1V9F37K068')
scratch=pathlib.Path(tempfile.mkdtemp(prefix='.spawn-live-',dir=root))
lab=pathlib.Path(tempfile.mkdtemp(prefix='fm-lab.',dir='/tmp'))
env=os.environ.copy()
for key in list(env):
 if key.startswith(('FM_','GIT_','TASKS_AXI_')) or key in ['TMUX','TMUX_PANE','CLAUDE_CONFIG_DIR','HERDR_ENV','HERDR_SESSION','HERDR_PANE_ID']: env.pop(key)
proj=scratch/'project'; config=scratch/'claude-config'
for d in [proj,config,scratch/'tmp']: d.mkdir()
env.update(FM_HOME=str(lab),HOME=str(proj),CLAUDE_CONFIG_DIR=str(config),TMUX_TMPDIR=str(lab/'tmux'),TREEHOUSE_ROOT=str(scratch/'pool'),SHELL='/bin/bash',TMPDIR=str(scratch/'tmp'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_AUTHOR_NAME='Lab',GIT_AUTHOR_EMAIL='lab@example.invalid',GIT_COMMITTER_NAME='Lab',GIT_COMMITTER_EMAIL='lab@example.invalid',XDG_CONFIG_HOME=str(scratch/'xdg-config'),XDG_DATA_HOME=str(scratch/'xdg-data'),XDG_CACHE_HOME=str(scratch/'xdg-cache'))
if mode == "home-ancestor":
 (proj/"users/me").mkdir(parents=True); env["HOME"]=str(proj/"users/me")
elif mode.startswith("config-"):
 (scratch/"user").mkdir(); env["HOME"]=str(scratch/"user")
 config=proj if mode == "config-equal" else proj/"claude-config"
 config.mkdir(exist_ok=True); env["CLAUDE_CONFIG_DIR"]=str(config)
def run(args,check=True,timeout=90):
 r=subprocess.run(list(map(str,args)),env=env,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 print('$ '+ ' '.join(map(str,args))+'\n'+r.stdout+'exit='+str(r.returncode),flush=True)
 if check: assert r.returncode==0,r.stdout
 return r
try:
 run([root/'bin/fm-lab-home.sh','create',lab]); (lab/'tmux').mkdir()
 run(['git','init','-qb','main',proj]); run(['git','-C',proj,'commit','--allow-empty','-qm','fixture'])
 run([root/'bin/fm-brief.sh','trustrefused',str(proj),'--scout'])
 brief=lab/'data/trustrefused/brief.md'; brief.write_text(brief.read_text().replace('{TASK}','Validate protected HOME refusal. Do not modify any files or contact external services.').replace('{FIRSTMATE_SPEC}','This isolated lab expects spawn to refuse before Claude is started.'))
 store=config/'.claude.json'; store.write_text('{"sentinel":17,"projects":{}}\n'); before=store.read_bytes()
 run(['tmux','-L','fm-lab','-f','/dev/null','new-session','-d','-s','primary','-x','120','-y','40','-c',root,'/bin/bash --noprofile --norc'])
 run(['tmux','-L','fm-lab','set-option','-g','default-shell','/bin/bash'])
 env['TMUX']=run(['tmux','-L','fm-lab','display-message','-p','-t','primary','#{socket_path},#{pid},0']).stdout.strip()
 r=run([root/'bin/fm-spawn.sh','trustrefused',proj,'--scout','--harness','claude','--backend','tmux'],check=False)
 pane=run(['tmux','-L','fm-lab','list-panes','-a','-F','#{session_name}:#{window_name} #{pane_current_command} #{pane_current_path}'])
 (ev/('spawn-'+mode+'-panes.txt')).write_text(pane.stdout)
 state={str(p.relative_to(lab)):p.read_text() for p in (lab/'state').glob('trustrefused.*') if p.is_file()}
 result={'exit':r.returncode,'output':r.stdout,'store_unchanged':store.read_bytes()==before,'task_meta_exists':(lab/'state/trustrefused.meta').exists(),'busy_state_exists':(lab/'state/trustrefused.busy-state').exists(),'busy_gen_exists':(lab/'state/trustrefused.busy-gen').exists(),'state':state,'panes':pane.stdout}
 result['passed']=r.returncode!=0 and ('config directory' if mode.startswith('config-') else 'home directory') in r.stdout and 'workspace trust' in r.stdout and result['store_unchanged'] and not any(result[k] for k in ['task_meta_exists','busy_state_exists','busy_gen_exists'])
 (ev/('spawn-'+mode+'-results.json')).write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)
finally:
 run(['tmux','-L','fm-lab','kill-server'],check=False)
 shutil.rmtree(lab); shutil.rmtree(scratch)
