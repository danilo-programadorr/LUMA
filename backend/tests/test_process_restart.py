import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import httpx
from backend.migrate import migrate


def test_real_process_restart(tmp_path):
    path=tmp_path/'restart.db';url='sqlite:///'+path.as_posix();migrate(url)
    token,knowledge,confirmation=(secrets.token_urlsafe(32) for _ in range(3))
    env={k:v for k,v in os.environ.items() if k.upper() in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','PATHEXT')}
    runtime=secrets.token_urlsafe(32)
    env.update(LUMA_RUNTIME_TOKEN=runtime,LUMA_OWNER_TOKEN=token,LUMA_KNOWLEDGE_TOKEN=knowledge,LUMA_ADMIN_CONFIRM_TOKEN=confirmation,
        LUMA_DATABASE_URL=url,PYTHONDONTWRITEBYTECODE='1')
    process_ids=[]
    def launch():
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env['LUMA_PORT']=str(port)
        proc=subprocess.Popen([sys.executable,'-m','backend.tests.process_server'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        process_ids.append(proc.pid)
        client=httpx.Client(base_url=f'http://127.0.0.1:{port}',headers={'Authorization':'Bearer '+token},trust_env=False,timeout=3)
        deadline=time.monotonic()+20
        while time.monotonic()<deadline and proc.poll() is None:
            try:
                if client.get('/health').status_code==200: return proc,client
            except httpx.HTTPError: pass
            time.sleep(.05)
        proc.kill();proc.wait(timeout=5);client.close()
        raise AssertionError('process did not start')
    def stop(proc,client):
        client.close()
        try:
            proc.stdin.write(b'STOP\n');proc.stdin.flush();proc.wait(timeout=15)
        finally:
            if proc.poll() is None: proc.kill();proc.wait(timeout=5)
            proc.stdin.close()
        assert proc.returncode==0
    def post(client,path,body=None,confirm=False):
        headers={'Idempotency-Key':secrets.token_hex(16)}
        if confirm: headers['X-Admin-Confirmation']=confirmation
        response=client.post('/v1/admin/'+path,json=body,headers=headers)
        assert response.status_code==200,response.text
        return response.json()
    proc,c=launch()
    try:
        a=post(c,'actions',{'project_id':'meu-gestor','tool_id':'google_calendar','capability':'calendar.delete','intent':'synthetic','parameters':{}})
        approval=post(c,'approvals/'+a['action_id']+'/decision',{'decision':'APPROVE','scope':a['scope'],'confirmation':'HUMAN_DECISION'},True)
        session=post(c,'sessions',{'project_id':'meu-gestor'})
        learning=post(c,'learning',{'project_id':'meu-gestor','source':'synthetic','claim':'unverified','evidence':['ref'],'confidence':'LOW'})
        post(c,'revocations',{'project_id':'meu-gestor','capability':'knowledge.read','tool_id':'knowledge','reason':'restart-test'})
        post(c,'tools/knowledge/disable')
        grant_rows=c.get('/v1/admin/grants').json()
        retention=c.get('/v1/admin/retention').json()
        before_chain=c.get('/v1/admin/audit/verify').json()
        assert before_chain['verified']
        post(c,'state',{'state':'LOCKED'})
    finally: stop(proc,c)
    proc,c=launch()
    try:
        assert c.get('/v1/admin/grants').json()==grant_rows
        assert c.get('/v1/admin/retention').json()==retention
        chain=c.get('/v1/admin/audit/verify').json()
        assert chain['verified'] and chain['sequence']>before_chain['sequence']
        identity=c.get('/v1/runtime/status',headers={'Authorization':'Bearer '+runtime}).json()
        assert identity['principal_id']=='luma-runtime'
        assert c.get('/v1/admin/state').json()['state']=='LOCKED'
        assert c.get('/v1/admin/actions/'+a['action_id']).json()['status']=='APPROVED'
        assert c.get('/v1/admin/approvals').json()[0]['approval_id']==approval['approval_id']
        assert c.get('/v1/admin/sessions').json()[0]['session_id']==session['session_id']
        assert c.get('/v1/admin/learning').json()[0]['candidate_id']==learning['candidate_id']
        assert len(c.get('/v1/admin/revocations').json())==1
        assert next(t for t in c.get('/v1/admin/tools').json() if t['tool_id']=='knowledge')['enabled'] is False
        assert c.post('/v1/knowledge/query',json={'project_id':'meu-gestor','query':'test'}).status_code==403
        audit=c.get('/v1/admin/audit').json()
        assert sum(e['event_type']=='BOOTSTRAP' for e in audit)==1
        assert any(e['event_type']=='ADMIN_DECISION' for e in audit)
    finally: stop(proc,c)
    assert len(set(process_ids))==2
    (tmp_path/'restart-evidence.json').write_text(json.dumps({'distinct_processes':2,'graceful_exit_codes':[0,0],
        'preserved':['LOCKED','revocation','disabled_tool','action','approval','session','learning','audit','grants','retention_policies','audit_hash_chain','runtime_principal'],
        'bootstrap_count':1,'knowledge_blocked_after_restart':True},indent=2),encoding='utf8')
