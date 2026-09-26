import os, pathlib, tempfile, subprocess, json, shutil
root=pathlib.Path.cwd()
evidence=pathlib.Path('/Users/daddy/.no-mistakes/evidence/01M3F3ECWQZ7XRPK1V9F37K068')
lab=pathlib.Path(tempfile.mkdtemp(prefix='.trust-live-',dir=root))
env=os.environ.copy()
for k in list(env):
 if k.startswith('GIT_'): env.pop(k)
env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_AUTHOR_NAME='Lab',GIT_AUTHOR_EMAIL='lab@example.invalid',GIT_COMMITTER_NAME='Lab',GIT_COMMITTER_EMAIL='lab@example.invalid')
def cmd(args, **kw): return subprocess.run(list(map(str,args)),env=kw.pop('env',env),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kw)
def ok(args):
 r=cmd(args); assert r.returncode==0,r.stdout
rows=[]
try:
 p=lab/'project'; w=lab/'worker'; linked=lab/'project-linked'; home=lab/'user'; config=lab/'config'
 for d in [p,home,config]: d.mkdir()
 ok(['git','init','-q',p]); ok(['git','-C',p,'commit','--allow-empty','-qm','fixture'])
 ok(['git','-C',p,'worktree','add','-qb','worker',w]); ok(['git','-C',p,'worktree','add','-qb','linked',linked])
 (p/'users/me').mkdir(parents=True); (p/'config').mkdir(); (w/'user').mkdir(); (w/'config').mkdir()
 (lab/'home-alias').symlink_to(p,target_is_directory=True); (lab/'project-alias').symlink_to(p,target_is_directory=True)
 (lab/'project-extra').mkdir()
 baseline=lab/'baseline-trust.sh'; baseline.write_text(cmd(['git','show','e9a6675ed188f3d77639cfe753451e07d68ab6a6:bin/fm-claude-trust.sh']).stdout); baseline.chmod(0o755)
 seed={'sentinel':{'keep':True},'projects':{'/unrelated':{'hasTrustDialogAccepted':False,'other':17}}}
 def run(name,h=home,c=config,project=p,target=w,expected=1,script=None):
  store=c/'.claude.json'; store.write_text(json.dumps(seed)+'\n'); before=store.read_bytes()
  e=env.copy(); e['HOME']=str(h); e['CLAUDE_CONFIG_DIR']=str(c)
  argv=[script or root/'bin/fm-claude-trust.sh',target,project]
  r=cmd(argv,env=e); data=json.loads(store.read_text()); unchanged=store.read_bytes()==before
  trusted=[k for k,v in data.get('projects',{}).items() if v.get('hasTrustDialogAccepted') is True]
  valid=r.returncode==expected and (unchanged if expected else set(trusted)=={str(p),str(w)} and data['sentinel']==seed['sentinel'] and data['projects']['/unrelated']==seed['projects']['/unrelated'])
  row=dict(name=name,command=list(map(str,argv)),HOME=str(h),CLAUDE_CONFIG_DIR=str(c),exit=r.returncode,output=r.stdout.strip(),store_unchanged=unchanged,trusted_paths=trusted,passed=valid)
  rows.append(row); print(json.dumps(row),flush=True)
 run('home equals primary',h=p)
 run('home below primary',h=p/'users/me')
 run('config equals primary',c=p)
 run('config below primary',c=p/'config')
 run('symlink HOME resolves to primary',h=lab/'home-alias')
 run('symlink project resolves to HOME',h=p,project=lab/'project-alias')
 run('linked project argument canonicalizes to protected primary',h=p,project=linked)
 run('target contains HOME',h=w/'user')
 run('target contains config',c=w/'config')
 run('filesystem root target',target=pathlib.Path('/'))
 run('safe sibling with shared text prefix',h=lab/'project-extra') if False else None
 run('safe sibling with shared text prefix',h=lab/'project-extra',expected=0)
 run('ordinary project outside HOME',expected=0)
 run('baseline reproduces HOME equality trust',h=p,expected=0,script=baseline)
 run('baseline reproduces HOME ancestor trust',h=p/'users/me',expected=0,script=baseline)
 (evidence/'trust-live-results.json').write_text(json.dumps(rows,indent=2)+'\n')
 assert all(r['passed'] for r in rows)
finally:
 shutil.rmtree(lab)
