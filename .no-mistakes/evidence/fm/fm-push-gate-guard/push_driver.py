import os, pathlib, subprocess, json, shutil
R=pathlib.Path.cwd(); D=R/'.test-phase-push'; E=pathlib.Path('~/.no-mistakes/evidence/01M7NWE3646DJF93YGBYAK20M8')
log=(E/'push-product-transcript.txt').open('w')
env=os.environ.copy()
for k in list(env):
    if k.startswith('GIT_CONFIG_') or k in ('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE'): env.pop(k,None)
env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_AUTHOR_NAME='Local Test',GIT_AUTHOR_EMAIL='test@example.invalid',GIT_COMMITTER_NAME='Local Test',GIT_COMMITTER_EMAIL='test@example.invalid')
def run(args,cwd=R,e=None,ok=True):
    p=subprocess.run(list(map(str,args)),cwd=cwd,env=e or env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    log.write('$ '+subprocess.list2cmdline(list(map(str,args)))+'\n'+p.stdout+f'EXIT={p.returncode}\n');log.flush()
    if ok: assert p.returncode==0,p.stdout
    return p
def git(*a,cwd=R,e=None,ok=True):return run(['git',*a],cwd,e,ok)
def bare(p,stamp=False):
    git('init','-q','--bare',p)
    if stamp:(p/'no-mistakes-gate-config').write_text('v2:disposable-local-test\n')
def ref(p,r):return git('-C',p,'rev-parse','--verify','--quiet',r,ok=False)
def push(args,target,r,allowed,e=None,cwd=None):
    p=run(args,cwd or src,e or guarded,False)
    if allowed:
        assert p.returncode==0,p.stdout
        assert ref(target,r).stdout.strip()==head
    else:
        assert p.returncode!=0 and 'fm-git-push-guard: refused:' in p.stdout,p.stdout
        assert ref(target,r).returncode!=0
    return p
src=D/'source';fork=D/'fork.git';gate=D/'gate.git';hooks=D/'hooks';guard=D/'guard'
git('init','-q','-b','main',src);git('-C',src,'commit','-q','--allow-empty','-m','Synthetic task change')
head=git('-C',src,'rev-parse','HEAD').stdout.strip();bare(fork);bare(gate,True)
git('-C',src,'remote','add','fork',fork);git('-C',src,'remote','add','no-mistakes',gate)
run(['bash',R/'bin/fm-git-push-guard.sh','write-gate',guard]);run(['bash',R/'bin/fm-git-strip-ai-trailers.sh','install','--push-guard',guard,hooks,src])
guarded=env.copy();guarded.update(GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.hooksPath',GIT_CONFIG_VALUE_0=str(hooks))
clone=D/'delivery';git('clone','-q',src,clone);git('-C',clone,'remote','add','fork',fork)
forms=[(['git','-C',src,'push',fork.as_uri()],'url-C',R),(['git','push','fork'],'named',src),(['git','-C',clone,'push','fork'],'clone',R),(['git','push',fork.as_uri()],'changed-dir',src),(['git','-c','push.default=current','push','fork'],'config',src),(['env','git','push','fork'],'env',src)]
for cmd,name,cwd in forms:
    r='refs/heads/baseline-'+name;push([*cmd,'HEAD:'+r],fork,r,True,env,cwd)
    r='refs/heads/guarded-'+name;push([*cmd,'HEAD:'+r],fork,r,False,guarded,cwd)
log.write('SCENARIO 1 PASS: all baseline forms delivered HEAD; guarded forms refused and created no refs.\n')
for dest,name in [('no-mistakes','named'),(gate.as_uri(),'file'),(str(gate),'absolute'),('../gate.git','relative')]:
    r='refs/heads/gate-'+name;push(['git','push',dest,'HEAD:'+r],gate,r,True)
git('-C',src,'remote','set-url','no-mistakes',fork)
push(['git','push','no-mistakes','HEAD:refs/heads/misleading'],fork,'refs/heads/misleading',False)
for kind in ['bare','nonbare']:
    other=D/('sibling-'+kind)
    if kind=='bare':bare(other)
    else:git('init','-q',other)
    bare(pathlib.Path(str(other)+'.git'),True)
    push(['git','push',other,'HEAD:refs/heads/sibling'],other,'refs/heads/sibling',False)
log.write('SCENARIO 2 PASS: stamped gate accepts all resolved local forms; misleading remote and stamped siblings refused.\n')
gwt=D/'gate-worktree';git('-C',gate,'worktree','add','-q',gwt,'gate-named')
push(['git','push',fork.as_uri(),'HEAD:refs/heads/publication'],fork,'refs/heads/publication',True,cwd=gwt)
push(['git','-C',gate,'push',fork,'refs/heads/gate-named:refs/heads/bare-publication'],fork,'refs/heads/bare-publication',True,cwd=R)
log.write('SCENARIO 3 PASS: gate linked worktree and bare common directory publish through inherited worker hooks.\n')
marker=D/'hook-input';block=D/'block';chain=src/'.git/hooks/pre-push'
chain.write_text('#!/bin/bash\ncat >'+str(marker)+'\n[ ! -e '+str(block)+' ]\n');chain.chmod(0o755)
push(['git','push',gate,'HEAD:refs/heads/chained'],gate,'refs/heads/chained',True)
assert 'refs/heads/chained' in marker.read_text();log.write('Repository hook input: '+marker.read_text())
block.touch();marker.unlink()
p=run(['git','push',gate,'HEAD:refs/heads/chain-reject'],src,guarded,False)
assert p.returncode!=0 and marker.exists() and ref(gate,'refs/heads/chain-reject').returncode!=0
marker.unlink();push(['git','push','fork','HEAD:refs/heads/guard-first'],fork,'refs/heads/guard-first',False)
assert not marker.exists()
log.write('SCENARIO 4 PASS: original hook receives ref input, rejects stamped-gate push, and never runs after guard refusal.\n')
log.close();print('Live real-Git scenarios 1-4 passed; transcript:',E/'push-product-transcript.txt')
