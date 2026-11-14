from pathlib import Path
import subprocess,os,time,signal,json,datetime,shutil
root=Path.cwd(); ev=Path('~/.no-mistakes/evidence/01M7DX6WEE2RPYFAECVX8QYV31'); runner=27812; suite=27846; group=27797
command=subprocess.check_output(['ps','-p',str(runner),'-o','command='],text=True).strip()
assert 'bin/fm-test-run.sh' in command and str(ev/'host-result.json') in command
report={'reason':'Stopped the incomplete required host subject to preserve the Test phase deadline and leave time to stop all owned children. This is not evidence of a product assertion failure.','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runner_command':command,'signals':[]}
fixtures=root/'.tools/fm8478/tmp/fm-supervision-host.JtbzNI'
if fixtures.exists():
 homes=(fixtures/'homes').read_text().splitlines(); report['last_home']=homes[-1]
 snap=ev/'host-interrupted-state'; snap.mkdir(exist_ok=True)
 for src in ['homes']:
  shutil.copyfile(fixtures/src,snap/src)
 current=Path(homes[-1])
 for src in ['host.out','host.rc','state/.supervision-host.log','state/.supervision-host-turn','state/.supervision-host-health','state/branch-outcomes.jsonl']:
  p=current/src
  if p.is_file():shutil.copyfile(p,snap/(src.replace('/','_')))
def processes():
 result={}
 for line in subprocess.check_output(['ps','-axo','pid=,ppid=,pgid=,lstart=,stat=,comm='],text=True).splitlines():
  f=line.strip().split(None,9)
  if len(f)==10:result[int(f[0])]={'parent':int(f[1]),'group':int(f[2]),'identity':f[3:8]+[f[9]],'state':f[8]}
 return result
tracked={}
def refresh():
 current=processes(); owned={runner}|{p for p,v in current.items() if v['group']==group}
 for _ in range(15):owned.update(p for p,v in current.items() if v['parent'] in owned or v['parent'] in tracked)
 for p in owned:
  if p in current:tracked.setdefault(p,current[p])
 return current
def send(pid,sig,current):
 if pid in current and pid in tracked and current[pid]['identity']==tracked[pid]['identity'] and not current[pid]['state'].startswith('Z'):
  try:os.kill(pid,sig);report['signals'].append({'pid':pid,'signal':sig})
  except ProcessLookupError:pass
current=refresh(); send(suite,signal.SIGTERM,current)
for _ in range(20):
 time.sleep(1);current=refresh()
 if runner not in current:break
# The runner and its tee must remain long enough to retain the suite's actual exit.
for pid in list(tracked):
 if pid not in [runner,group,27847]:send(pid,signal.SIGTERM,current)
time.sleep(4);current=refresh()
for pid in list(tracked):
 if pid not in [runner,group,27847]:send(pid,signal.SIGKILL,current)
time.sleep(3);current=refresh()
report['remaining_owned']={str(p):v for p,v in current.items() if p in tracked and v['identity']==tracked[p]['identity'] and not v['state'].startswith('Z')}
report['observed_processes']=tracked
(ev/'host-interruption.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'remaining_owned':report['remaining_owned'],'signals_sent':len(report['signals'])}))
