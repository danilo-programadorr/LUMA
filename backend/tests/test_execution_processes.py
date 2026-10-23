import json,os,subprocess,sys
from datetime import datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.app.database import ROOT

def run(stage,env):
    p=subprocess.run([sys.executable,'-m','backend.tests.execution_process',stage],env=env,cwd=ROOT,capture_output=True,text=True,timeout=60)
    if stage=='crash':assert p.returncode==75;return {}
    assert p.returncode==0,p.stderr[-2000:]
    return json.loads(p.stdout.splitlines()[-1])

@pytest.mark.parametrize('crash',[False,True])
def test_owner_offline_restart_and_device(tmp_path,crash):
    env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR') if k in os.environ}
    env['LUMA_DATABASE_URL']='sqlite:///'+(tmp_path/'offline.db').as_posix()
    a=run('create',env);env.update(LUMA_DEVICE_CREDENTIAL=a['device_credential'],LUMA_TEST_TIME=a['time'],LUMA_TEST_JOB=a['job_id'])
    run('schedule',env);waiting=run('inspect',env)
    assert waiting['jobs']==['WAITING_FOR_DEVICE'] and waiting['sessions_closed']
    if crash:
        run('crash',env)
        env['LUMA_TEST_TIME']=(datetime.fromisoformat(a['time'])+timedelta(seconds=31)).isoformat()
        assert run('recover',env)['recovered']=='SUCCEEDED'
    else:
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:run('execute',env),range(2)))
        assert sum(r['claimed'] for r in results)==1
        assert all(not r['owner_credential_present'] for r in results)
    final=run('inspect',env)
    assert final['jobs']==['SUCCEEDED'] and final['records']==final['effects']==final['authorizations']==final['tasks']==1
    assert final['audit_verified'] and final['sessions_closed']
    name='FASE_7E_RESTART_REAL.json' if crash else 'FASE_7E_OFFLINE_EXECUTION.json'
    (ROOT/'reports'/name).write_text(json.dumps({'status':'PASSED','real_subprocesses':True,'local_sandbox_only':True,'owner_token_in_executor':False,'crash_reconciled':crash,'device_id':'pc-test',**final},indent=2)+'\n',encoding='utf8')
