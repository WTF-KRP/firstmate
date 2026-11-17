import pathlib,subprocess,shutil,os,json,hashlib
R=pathlib.Path.cwd();D=R/'.test-phase-push';E=pathlib.Path('~/.no-mistakes/evidence/01M7NWE3646DJF93YGBYAK20M8')
assert D.parent==R and D.is_dir() and not D.is_symlink()
for name in ['push_driver.py','launch_driver.py','pane_probe.py','retain_cleanup.py']:shutil.copyfile(D/name,E/name)
results={p.name:json.loads(p.read_text()) for p in sorted(E.glob('pane-*.json'))}
(E/'pane-product-probes.json').write_text(json.dumps(results,indent=2)+'\n')
revision=subprocess.run(['git','rev-parse','HEAD'],text=True,capture_output=True,check=True).stdout.strip()
token=hashlib.sha256(str(D/'lab').encode()).hexdigest();left=[]
for p in sorted((D/'lab/state').glob('*.meta')):
    m=dict(x.split('=',1) for x in p.read_text().splitlines() if '=' in x)
    for scratch in [pathlib.Path(m['tasktmp']),pathlib.Path(m['tasktmp']+'+'+token)]:
        if scratch.exists():left.append(str(scratch))
probe=subprocess.run(['tmux','-S',str(E/'tmux.sock'),'list-sessions'],text=True,capture_output=True)
assert probe.returncode!=0 and ('no server running' in probe.stderr or 'Connection refused' in probe.stderr),probe
processes=subprocess.run(['pgrep','-fl',str(D)],text=True,capture_output=True)
others=[line for line in processes.stdout.splitlines() if 'retain_cleanup.py' not in line]
assert not others,others
# Product-created /tmp files are outside the user's intentional-write boundary.
# Inventory them instead of deliberately deleting outside this worktree.
def repair(fn,p,exc):
    os.chmod(pathlib.Path(p).parent,0o700);os.chmod(p,0o700);fn(p)
shutil.rmtree(D,onexc=repair)
(E/'tmux.sock').unlink(missing_ok=True)
status=subprocess.run(['git','status','--short'],text=True,capture_output=True,check=True)
assert not status.stdout,status.stdout
(E/'cleanup.txt').write_text('Candidate: '+revision+'\nWorking copy: '+str(R)+'\nBoth live drivers exited 0. All six scenarios passed.\nPrivate tmux kill-server exited 0. Subsequent list-sessions exited '+str(probe.returncode)+': '+probe.stderr.strip()+'\nNo remaining fixture processes. Worktree fixture directory removed. git status --short exited 0 with empty output.\nNo permanent code/test edits; no lint, broad suite, pipeline, PR or remote-host operations.\nRaw-command worker launches exercised real spawn and pane environment; no vendor model session was claimed.\nProduct-created ephemeral scratch retained outside worktree because intentional deletion there is excluded by the user boundary:\n'+'\n'.join(left)+'\n')
print((E/'cleanup.txt').read_text())
