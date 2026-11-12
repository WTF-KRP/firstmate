import os,pathlib,subprocess,signal,json,time
r=pathlib.Path.cwd(); rows=[]
for mode,lib in [('baseline',r/'.test-8275/base/bin/fm-wake-lib.sh'),('candidate',r/'bin/fm-wake-lib.sh')]:
    h=r/'.test-8275'/('repro-'+mode)
    subprocess.run(['bash','bin/fm-lab-home.sh','create',str(h)],check=True,capture_output=True)
    lock=h/'state'/'.lock.acquire'
    for suffix in ('','.steal'):
        p=pathlib.Path(str(lock)+suffix); p.mkdir(); o=p/(p.name+'.owner.X'); o.mkdir(); (o/'pid').write_text('999999\n'); os.utime(o,(1,1)); os.utime(p,(1,1))
    env={k:v for k,v in os.environ.items() if not k.startswith('FM_') and k not in ('STATE',)}; env['FM_HOME']=str(h)
    p=subprocess.Popen(['bash','-c','. "$1"; fm_lock_acquire_wait "$2" || exit 10; echo "acquired dead-directory lock"; fm_lock_release "$2"','_',str(lib),str(lock)],env=env,start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    t=time.monotonic(); expired=False
    try: out,err=p.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        expired=True; os.killpg(p.pid,signal.SIGKILL); out,err=p.communicate()
    row=dict(revision='a02b089835a114844cc53d0429570155dfe4ef3a' if mode=='baseline' else 'e836fca3cf5bdba5a0b23da2e222712f7d4bd73e',mode=mode,command='source actual revision fm-wake-lib.sh; fm_lock_acquire_wait <dead real-directory primary+steal>; fm_lock_release',bounded_observation_seconds=round(time.monotonic()-t,3),timed_out=expired,exit=p.returncode,stdout=out,stderr=err,remaining_state=[str(x.relative_to(h)) for x in (h/'state').rglob('*')]); rows.append(row); print(json.dumps(row))
    assert expired if mode=='baseline' else p.returncode==0 and not expired
