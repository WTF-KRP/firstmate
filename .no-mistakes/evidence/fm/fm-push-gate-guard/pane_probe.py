import os,sys,json,subprocess,pathlib
out,wt,fork,gate,stage=sys.argv[1:]
def run(a):
    p=subprocess.run(a,cwd=wt,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25)
    return p.returncode,p.stdout
head=run(['git','rev-parse','HEAD'])[1].strip();data={'stage':stage,'worktree':wt,'head':head,'hooksPath':run(['git','config','--get','core.hooksPath'])[1].strip()}
for key,dest in [('fork',fork),('gate',gate)]:
    ref=('refs/for/main' if stage=='review' and key=='fork' else 'refs/heads/'+pathlib.Path(fork).stem+'-'+stage)
    rc,text=run(['git','push',dest,'HEAD:'+ref]);rr,oid=run(['git','-C',dest,'rev-parse','--verify','--quiet',ref]);data[key]={'command':['git','push',dest,'HEAD:'+ref],'rc':rc,'output':text,'oid':oid.strip() if rr==0 else None}
pathlib.Path(out).write_text(json.dumps(data,indent=2)+'\n')
