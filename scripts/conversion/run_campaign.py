"""Resumable, single-worker, nine-profile server campaign; fail closed."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from campaign_common import MODELS, PROFILES, environment, reference, sha, write

def now():return datetime.now(timezone.utc).isoformat()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--campaign',type=Path,required=True)
    a=p.parse_args()
    environment(a.root)
    a.campaign.mkdir(parents=True,exist_ok=True)
    lock=(a.root/'campaign.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (a.campaign/'controller.pid').write_text(str(os.getpid()))
    if shutil.disk_usage(a.campaign).free<100*1024**3:raise RuntimeError('Less than100GiB free workspace')
    state_path=a.campaign/'status.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {
        'schema_version':1,'started_utc':now(),'status':'running','board_verified':False,
        'profiles':{f'{m}/{p}':{'status':'pending'} for m in MODELS for p in PROFILES}}
    def save():
        state['updated_utc']=now();write(state_path,state)
        write(a.root/'campaign_status.json',{'status':state['status'],'current':state.get('current'),
              'updated_utc':state['updated_utc'],'canonical_status':str(state_path),
              'server_validated':sum(v['status']=='server-validated' for v in state['profiles'].values()),
              'total_profiles':9,'board_verified':False})
        from summarize_campaign import refresh
        refresh(a.campaign,state)
    def run(command,log_path,entry,stage):
        entry.update(stage=stage,updated_utc=now());save()
        log_path.parent.mkdir(parents=True,exist_ok=True)
        with log_path.open('w') as log:
            proc=subprocess.Popen(['nice','-n','10',sys.executable,*command],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            entry['worker_pid']=proc.pid;save()
            try:
                while proc.poll() is None:
                    time.sleep(5)
                    memory={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}
                    if memory['MemAvailable']<8*1024**2:
                        os.killpg(proc.pid,signal.SIGTERM)
                        try:proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                        entry['resource_stop']='System available RAM fell below8GiB'
                    save()
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            entry.pop('worker_pid',None)
            entry['last_exit_code']=proc.returncode
            entry['last_log']=str(log_path)
            if proc.returncode:raise RuntimeError(f'{stage} failed; see {log_path}')
    script=Path(__file__).parent
    # Store immutable lineage; reruns cannot silently adopt a new reference.
    frozen={m:{'path':str(reference(a.root,m)),
               'report_sha256':sha(reference(a.root,m)/'parity_report.json'),
               'fixture_sha256':sha(reference(a.root,m)/'golden_validation.npz')} for m in MODELS}
    frozen_path=a.campaign/'references.json'
    if frozen_path.exists() and json.loads(frozen_path.read_text())!=frozen:raise RuntimeError('FP32 references changed')
    write(frozen_path,frozen)
    state.pop('error',None)
    state.update(status='running',controller_pid=os.getpid());save()
    def interrupted(signum,frame):raise RuntimeError(f'Controller interrupted by signal{signum}')
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    try:
        for model in MODELS:
            policy_path=a.campaign/'integer_exclusions.json'
            policies=json.loads(policy_path.read_text()) if policy_path.exists() else {}
            raw_exclusions=policies.get(model,[])
            if not isinstance(raw_exclusions,list) or any(not isinstance(x,str) for x in raw_exclusions):raise ValueError('Invalid integer exceptions')
            half_policy_path=a.campaign/'integer_fp16_islands.json'
            half_policies=json.loads(half_policy_path.read_text()) if half_policy_path.exists() else {}
            half_paths=half_policies.get(model,[])
            if not isinstance(half_paths,list) or any(not isinstance(x,str) for x in half_paths):raise ValueError('Invalid FP16 islands')
            if any(x==y or x.startswith(y+'.') or y.startswith(x+'.') for x in raw_exclusions for y in half_paths):raise ValueError('Conflicting FP32/FP16 exception scopes')
            half_paths=sorted(set(half_paths));exclusions=sorted(set(raw_exclusions)|set(half_paths))
            policy_sha=hashlib.sha256(json.dumps({'fp32':sorted(set(raw_exclusions)),'fp16':half_paths},sort_keys=True,separators=(',',':')).encode()).hexdigest()
            policy_file=a.campaign/'policies'/model/f'{policy_sha}.json'
            write(policy_file,exclusions)
            half_policy_file=a.campaign/'policies'/model/f'{policy_sha}.fp16.json'
            write(half_policy_file,half_paths)
            coverage=a.campaign/'coverage'/model/policy_sha
            row_start=time.perf_counter()
            for profile in PROFILES:
                key=f'{model}/{profile}';entry=state['profiles'][key]
                integer=profile!='fp16'
                if integer and entry['status']=='server-validated' and entry.get('integer_policy_sha256')!=policy_sha:
                    entry.setdefault('superseded_packages',[]).append(entry.get('package'))
                    entry['status']='pending'
                    state.get('model_rows',{}).pop(model,None)
                if entry['status']=='running' and entry.get('worker_pid'):
                    # A controller killed without cleanup must not create a
                    # second worker beside its orphan. Only follow our exact
                    # artifact-path command, guarding against PID reuse.
                    procdir=Path('/proc')/str(entry['worker_pid'])
                    while procdir.exists():
                        try:
                            cmd=(procdir/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
                            stat=(procdir/'stat').read_text().split(') ',1)[1].split()[0]
                        except FileNotFoundError:break
                        if entry.get('artifacts','__missing__') not in cmd or stat=='Z':break
                        entry['stage']='recovering_previous_worker';save();time.sleep(5)
                    entry.pop('worker_pid',None)
                    prior=a.campaign/f"packages/{model}/{profile}/attempt{int(entry.get('attempt',1)):03}"
                    if (prior/'deployment.json').exists() and json.loads((prior/'deployment.json').read_text()).get('status')=='server-validated':
                        entry.update(status='server-validated',package=str(prior),completed_utc=now(),stage='complete');save()
                    elif prior.exists() or any(json.loads(f.read_text()).get('status')=='failed' for f in Path(entry['artifacts']).glob('*.report.json')):
                        entry['status']='failed'
                if entry['status']=='server-validated':
                    if entry.get('error'):
                        entry.setdefault('failure_history',[]).append({k:entry[k] for k in
                            ('attempt','error','last_log','failed_utc') if k in entry})
                        for old in ('error','failed_utc','resource_stop'):entry.pop(old,None)
                    package=Path(entry['package'])
                    d=json.loads((package/'deployment.json').read_text())
                    if d['status']!='server-validated':raise RuntimeError('Completed package state mismatch')
                    for line in (package/'SHA256SUMS').read_text().splitlines():
                        digest,rel=line.split('  ',1)
                        target=(package/rel).resolve()
                        if not target.is_relative_to(package.resolve()) or sha(target)!=digest:raise RuntimeError('Completed package checksum mismatch')
                    continue
                number=int(entry.get('attempt',0)) if entry['status']=='running' else int(entry.get('attempt',0))+1
                if not number:number=1
                # Adopt only the separately monitored initial FP16 prefix attempt.
                seeded=a.campaign/f'artifacts/{model}/{profile}/attempt001'
                if not entry.get('attempt') and seeded.exists():
                    seed_report=seeded/f'prefix_{profile}.report.json'
                    valid_seed=seed_report.exists() and json.loads(seed_report.read_text()).get('status')=='candidate_native_smoke_passed_requires_full_policy_and_device_evaluation'
                    number=1 if valid_seed else 2
                out=a.campaign/f'artifacts/{model}/{profile}/attempt{number:03}'
                out.mkdir(parents=True,exist_ok=True)
                if entry.get('error'):
                    entry.setdefault('failure_history',[]).append({k:entry[k] for k in
                        ('attempt','error','last_log','failed_utc') if k in entry})
                    for old in ('error','last_exit_code','last_log','failed_utc','resource_stop'):entry.pop(old,None)
                entry.update(status='running',attempt=number,started_utc=now(),artifacts=str(out))
                if integer:entry['integer_policy_sha256']=policy_sha
                state['current']=key;save()
                for graph in ('prefix','denoise'):
                    report_path=out/f'{graph}_{profile}.report.json'
                    if report_path.exists():
                        d=json.loads(report_path.read_text())
                        if d.get('status') in ('candidate_native_smoke_passed_requires_full_policy_and_device_evaluation','candidate_native_boundary_measured_requires_full_policy_gate') and Path(d.get('eager_export','missing')).is_file():continue
                    if integer:
                        from reuse_graph import reuse
                        if reuse(out.parent,out,graph,profile,exclusions,coverage,frozen[model]['fixture_sha256'],half_paths):
                            entry['stage']=f'reused_unchanged_{graph}';save();continue
                    extra=['--exceptions',str(policy_file),'--fp16-islands',str(half_policy_file)] if integer else []
                    run([str(script/'convert_campaign_graph.py'),'--root',str(a.root),'--model',model,
                         '--profile',profile,'--graph',graph,'--output',str(out),
                         '--coverage-dir',str(coverage),*extra],
                        out/f'{graph}.log',entry,graph)
                package=a.campaign/f'packages/{model}/{profile}/attempt{number:03}'
                run([str(script/'validate_package.py'),'--root',str(a.root),'--model',model,'--profile',profile,
                     '--artifacts',str(out),'--package',str(package)],out/'validation.log',entry,'full_policy_validation')
                d=json.loads((package/'deployment.json').read_text())
                if d.get('status')!='server-validated':raise RuntimeError('Validation did not commit completion')
                entry.update(status='server-validated',package=str(package),completed_utc=now(),stage='complete')
                blocker_path=a.campaign/'blockers.json'
                if blocker_path.exists():
                    blocker=json.loads(blocker_path.read_text())
                    if blocker.get('profile')==key and blocker.get('status')=='unresolved':
                        blocker.update(status='resolved',resolved_utc=now(),resolution_package=str(package))
                        write(blocker_path,blocker)
                save()
            state.setdefault('model_rows',{})[model]={'status':'server-validated','completed_utc':now(),
                                                      'controller_seconds_this_run':time.perf_counter()-row_start}
            save()
        state.update(status='server-validated',current=None,completed_utc=now());save()
    except Exception as exc:
        if state.get('current'):
            state['profiles'][state['current']].update(status='failed',error=f'{type(exc).__name__}: {exc}',failed_utc=now())
        state.update(status='failed',error=str(exc));save();raise

if __name__=='__main__':main()
