exec((__import__('pathlib').Path('.test-phase/drive-cli.py').read_text().split('# Public CLI safety boundary')[0]).replace("'live-task-job-transcript.txt','w'","'live-recovery-transcript.txt','w'"))
import shutil
inbox=state/'recover.inbox'
shutil.rmtree(inbox/'jobs')
env=base.copy();env['FM_TASK_INBOX']=str(inbox)
out=run([str(root/'bin/fm-task-job.sh'),'start','--timeout','120','--','sleep','90'],env).stdout
job=inbox/'jobs'/next(s[5:] for s in out.splitlines() if s.startswith('job: '))
runner,child=pids(job)
os.kill(runner,signal.SIGKILL);waitfor(lambda:not active(runner))
watchenv=base.copy();watchenv.update(FM_BACKEND='herdr',FM_POLL='1',FM_SIGNAL_GRACE='1',FM_CHECK_INTERVAL='999999',FM_HEARTBEAT='999999')
watchlog=open(evidence/'live-watcher-output.txt','a')
watch=subprocess.Popen([str(root/'bin/fm-watch.sh')],env=watchenv,stdout=watchlog,stderr=subprocess.STDOUT)
try:
    rec=record(inbox)
    assert 'outcome=lost' in (job/'exit').read_text()
    waitfor(lambda:not active(child))
    rec.rename(inbox/'handled'/rec.name)
    (job/'delivered').unlink()
    time.sleep(8)
    assert not list(inbox.glob('*.msg')) and (job/'delivered').exists()
    emit('Lost exit record:\n'+(job/'exit').read_text())
    emit(f'S8 PASS: real watcher recovered killed runner {runner}, stopped child {child}, persisted one lost notice and kept acknowledgement')
finally:
    watch.terminate()
    try:watch.wait(timeout=10)
    except subprocess.TimeoutExpired:watch.kill();watch.wait()
    watchlog.close();stop('recover')
log.close()
