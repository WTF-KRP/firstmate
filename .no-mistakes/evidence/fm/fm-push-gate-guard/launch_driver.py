import os, pathlib, subprocess, time, json, shlex
R=pathlib.Path.cwd(); D=R/'.test-phase-push'; E=pathlib.Path('~/.no-mistakes/evidence/01M7NWE3646DJF93YGBYAK20M8'); L=D/'lab'
log=(E/'launch-product-transcript.txt').open('w'); sock=E/'tmux.sock'
env=os.environ.copy()
for k in list(env):
    if k.startswith(('GIT_CONFIG_','HERDR_','REX_')) or k in ('TMUX','FM_HOME','FM_ROOT_OVERRIDE','FM_STATE_OVERRIDE','FM_DATA_OVERRIDE','FM_CONFIG_OVERRIDE','FM_PROJECTS_OVERRIDE','FM_GATE_REFUSE_BYPASS','FM_TEST_SEAM','FM_TASK_ID','GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','FM_BACKEND','TASKS_AXI_FILE','TASKS_AXI_BACKEND'):env.pop(k,None)
env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_AUTHOR_NAME='Local Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Local Test',GIT_COMMITTER_EMAIL='test@example.invalid',SHELL='/bin/bash',BASH_ENV='/dev/null',ENV='/dev/null',TREEHOUSE_ROOT=str(D/'treehouse'),DISABLE_AUTOUPDATER='1')
def run(args,cwd=R,e=None,ok=True,timeout=100):
    p=subprocess.run(list(map(str,args)),cwd=cwd,env=e or env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    log.write('$ '+shlex.join(list(map(str,args)))+'\n'+p.stdout+f'EXIT={p.returncode}\n');log.flush()
    if ok:assert p.returncode==0,p.stdout
    return p
def tm(*args,**kw):return run(['tmux','-S',sock,*args],**kw)
def git(*args,**kw):return run(['git',*args],**kw)
def meta(id):return dict(line.split('=',1) for line in (L/'state'/f'{id}.meta').read_text().splitlines() if '=' in line)
def waitfile(p,seconds=30):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if p.exists():return json.loads(p.read_text())
        time.sleep(.2)
    raise RuntimeError('no pane evidence '+str(p))
def probe(id,stage):
    m=meta(id);target=m['window'];out=E/f'pane-{id}-{stage}.json'
    cmd=shlex.join(['python3',str(D/'pane_probe.py'),str(out),str(m['worktree']),str(D/(id+'.git')),str(D/'launch-gate.git'),stage])
    tm('send-keys','-t',target,'-l',cmd);tm('send-keys','-t',target,'Enter')
    data=waitfile(out);log.write(json.dumps(data,indent=2)+'\n');log.flush();return data
def expect(data,guarded):
    assert data['gate']['rc']==0,data
    assert data['gate']['oid']==data['head'],data
    if guarded:
        assert data['fork']['rc']!=0 and 'not a no-mistakes gate' in data['fork']['output'],data
        assert data['fork']['oid'] is None,data
    else:assert data['fork']['rc']==0 and data['fork']['oid']==data['head'],data
def setup(id,mode='no-mistakes',forge='none',keep=False,scout=False):
    project=D/id;origin=D/(id+'.git');git('init','-q','-b','main',project);git('-C',project,'commit','-q','--allow-empty','-m','Synthetic local project');git('init','-q','--bare',origin);git('-C',origin,'symbolic-ref','HEAD','refs/heads/main');git('-C',project,'remote','add','origin',origin);git('-C',project,'push','-q','-u','origin','main');git('-C',project,'remote','set-head','origin','main')
    (L/'config'/'keep-ai-trailers').unlink(missing_ok=True)
    if keep:(L/'config'/'keep-ai-trailers').touch()
    words='' if forge=='none' else ' forge='+forge
    with (L/'data'/'projects.md').open('a') as f:f.write(f'- {id} [{mode}{words}] - disposable local project\n')
    b=L/'data'/id;b.mkdir();text='# Task\n## Captain\'s intent\nVerify local push behavior.\n\n## Firstmate spec\nRun only disposable local probes.\n'
    if not scout:text+=f'\n# Definition of done\nDelivery contract: mode={mode}{words}\nShip branch: fm/{id}\n'
    (b/'brief.md').write_text(text)
    args=['bash',R/'bin/fm-spawn.sh',id,project,'--backend','tmux']
    if scout:args+=['--scout']
    else:args+=['--mode',mode,'--yolo','off']
    # Public raw-launch interface: a real shell command, not a fake vendor CLI.
    args+=['/bin/bash --noprofile --norc']
    run(args,e=env,timeout=110)
    time.sleep(1)
    return project
try:
    run(['bash',R/'bin/fm-lab-home.sh','create',L]);env['FM_HOME']=str(L)
    (L/'config'/'backend').write_text('tmux\n');(L/'config'/'backlog-backend').write_text('manual\n');(L/'config'/'supervision-host-off').touch()
    # Explicit private socket, no host tmux configuration or plugins.
    tm('-f','/dev/null','new-session','-d','-s','fm-lab','-x','140','-y','45','-c',R,'/bin/bash --noprofile --norc')
    tm('set-option','-g','default-shell','/bin/bash');tm('set-option','-g','default-command','/bin/bash --noprofile --norc')
    ident=tm('display-message','-p','-t','fm-lab','#{socket_path},#{pid},#{session_id}').stdout.strip();env['TMUX']=ident.replace(',$',',')
    git('init','-q','--bare',D/'launch-gate.git');(D/'launch-gate.git/no-mistakes-gate-config').write_text('v2:disposable-local-test\n')
    for name,mode,forge,keep in [('nm','no-mistakes','none',False),('nmkeep','no-mistakes','none',True),('forgejo','no-mistakes','forgejo',False),('gerrit','no-mistakes','gerrit',False),('gerritkeep','no-mistakes','gerrit',True),('direct','direct-PR','none',False),('directkeep','direct-PR','none',True),('local','local-only','none',False)]:
        id='labpush-'+name;setup(id,mode,forge,keep);data=probe(id,'ship');expect(data,mode=='no-mistakes' and forge!='gerrit')
        if forge=='gerrit':
            m=meta(id);out=E/f'pane-{id}-review.json';cmd=shlex.join(['python3',str(D/'pane_probe.py'),str(out),m['worktree'],str(D/(id+'.git')),str(D/'launch-gate.git'),'review']);tm('send-keys','-t',m['window'],'-l',cmd);tm('send-keys','-t',m['window'],'Enter');review=waitfile(out);expect(review,False)
        log.write('SPAWN POLICY PASS '+id+'\n');log.flush()
    log.write('SCENARIO 5 PASS: real fm-spawn, tmux, Treehouse, pane environment and Git enforce selected policy for local fixtures.\n')
    for forge,keep in [('none',False),('none',True),('forgejo',False),('forgejo',True),('gerrit',False),('gerrit',True)]:
        id='labprom-'+forge+('-keep' if keep else '');setup(id,forge=forge,keep=keep,scout=True);expect(probe(id,'scout'),False)
        brief=L/'data'/id/'brief.md';before=brief.read_bytes();p=run(['bash',R/'bin/fm-promote.sh',id,'--mode','no-mistakes','--yolo','off'],e=env,ok=False)
        if keep and forge!='gerrit':
            assert p.returncode!=0 and 'launched without the per-task Git hooksPath' in p.stdout,p.stdout
            assert meta(id)['kind']=='scout' and brief.read_bytes()==before and not (L/'data'/id/'ship-instructions.md').exists()
            expect(probe(id,'refused-promotion'),False)
        else:
            assert p.returncode==0,p.stdout
            assert meta(id)['kind']=='ship';expect(probe(id,'promoted'),forge!='gerrit')
        log.write('PROMOTION POLICY PASS '+id+'\n');log.flush()
    log.write('SCENARIO 6 PASS: existing pane gains protection in place, missing hooks refuse without changing scout contract, Gerrit remains publishable.\n');log.flush()
finally:
    if sock.exists():tm('kill-server',ok=False)
    log.close()
