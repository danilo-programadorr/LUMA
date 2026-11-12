import argparse,getpass,json,os,signal,random
from pathlib import Path
from device_agent.identity import Identity
from device_agent.client import ChannelError
from .client import ResearchClient

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['enroll','run','status']);p.add_argument('--endpoint',default='http://127.0.0.1:8770');a=p.parse_args()
    # Separate identity path: never overwrite/reactivate the revoked 7F-C identity.
    try:
        forbidden=('LUMA_OWNER_TOKEN','LUMA_TOKEN','LUMA_ADMIN_CONFIRM_TOKEN','LUMA_DATABASE_URL','LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD','DATABASE_URL','PGPASSWORD')
        if any(os.environ.get(k) for k in forbidden):raise ValueError('RUNTIME_AUTHORITY_CREDENTIAL_DENIED')
        identity=Identity(Path('runtime/research-agent/identity.db'),create=a.command=='enroll');client=ResearchClient(identity,a.endpoint)
        if a.command=='enroll':
            value=getpass.getpass('Enrollment (entrada oculta): ');cid,code=value.split(':',1);r=client.enroll(cid,code);value=code=None
            print(json.dumps({'status':r['status'],'fingerprint':identity.fingerprint()}));return
        if a.command=='status':print(json.dumps({'enrolled':bool(identity.binding()[0]),'fingerprint':identity.fingerprint()}));return
        from backend.research.runtime import ResearchProcessor,ProjectKnowledgeReader
        from backend.research.provider import GeminiGoogleSearchProvider,ResearchProviderSettings
        from backend.app.knowledge import KnowledgeClient
        from types import SimpleNamespace
        endpoint=os.environ.get('LUMA_KNOWLEDGE_ENDPOINT','http://127.0.0.1:8765')
        if endpoint!='http://127.0.0.1:8765':raise ValueError('INVALID_LOCAL_KNOWLEDGE_ENDPOINT')
        knowledge=KnowledgeClient(SimpleNamespace(knowledge_endpoint=endpoint,knowledge_token=os.environ.get('LUMA_KNOWLEDGE_TOKEN',''),timeout=3))
        profile=os.environ.get('LUMA_RESEARCH_ACCEPTANCE_PROFILE','INITIAL_SIX')
        if profile=='FINAL_THREE':
            if os.environ.get('LUMA_RESEARCH_FINAL_THREE_OWNER_APPROVED')!='1':raise ValueError('RESEARCH_FINAL_APPROVAL_REQUIRED')
            from backend.research.final_acceptance import final_status
            status=final_status()
            if status['halted'] or not status['remaining_calls']:raise ValueError('RESEARCH_FINAL_BUDGET_STOPPED')
        cfg=ResearchProviderSettings(real_calls_approved=os.environ.get('LUMA_RESEARCH_REAL_APPROVED')=='1',attribution_approved=os.environ.get('LUMA_RESEARCH_ATTRIBUTION_APPROVED')=='1',max_session_calls=min(3 if profile=='FINAL_THREE' else 6,max(0,int(os.environ.get('LUMA_RESEARCH_MAX_CALLS','0')))),acceptance_profile=profile,final_three_owner_approved=os.environ.get('LUMA_RESEARCH_FINAL_THREE_OWNER_APPROVED')=='1')
        provider=GeminiGoogleSearchProvider(os.environ.get('LUMA_GEMINI_API_KEY',''),cfg);processor=ResearchProcessor(provider,ProjectKnowledgeReader(knowledge))
        signal.signal(signal.SIGINT,lambda *_:client.stop.set());signal.signal(signal.SIGTERM,lambda *_:client.stop.set())
        failures=0
        try:
            while not client.stop.is_set():
                try:
                    client.cycle(processor);failures=0
                    if provider.acceptance_halted:
                        print(json.dumps({'status':'ACCEPTANCE_STOPPED','model_calls_this_process':provider.calls,'last_usage':provider.last_usage}));break
                except ChannelError as e:
                    if str(e) in ('DEVICE_REVOKED','OWNER_BINDING_INACTIVE','DEVICE_OWNER_MISMATCH'):raise
                    failures=min(4,failures+1)
                client.stop.wait(min(60,10*2**failures)+random.uniform(0,2))
        finally:knowledge.close()
    except (ChannelError,ValueError,RuntimeError) as e:
        code=str(e);print(code if len(code)<100 and all(c.isupper() or c=='_' for c in code) else 'RESEARCH_LOCAL_OPERATION_FAILED');raise SystemExit(1) from None
if __name__=='__main__':main()
