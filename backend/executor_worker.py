"""Independent local executor; no owner, runtime, Knowledge or Gemini credentials."""
import argparse,os,time
from types import SimpleNamespace
from .app.database import Store,DEFAULT_URL
from .app.trust import Control
from .app.execution import ExecutionService
from .app.errors import Fault

FORBIDDEN_ENV=('LUMA_OWNER_TOKEN','LUMA_TOKEN','LUMA_ADMIN_CONFIRM_TOKEN','LUMA_RUNTIME_TOKEN','GEMINI_API_KEY','LUMA_GEMINI_API_KEY','LUMA_KNOWLEDGE_TOKEN')

def service(url,*,sandbox=False):
    if any(os.environ.get(k) for k in FORBIDDEN_ENV):raise Fault('EXECUTOR_PRIVILEGED_ENV_DENIED',403)
    control=Control.__new__(Control);control.store=Store(url)
    control.settings=SimpleNamespace(token='',knowledge_token='',admin_confirmation_token='',runtime_token='')
    return ExecutionService(control,sandbox=sandbox)

def cycle(execution,worker='local-worker',device_id=None,credential=None):
    with execution.store.read() as repo:
        pending=[j['job_id'] for j in repo.rows('jobs') if j['status']=='RUNNING' and j['lease_until'] and __import__('backend.app.control',fromlist=['date']).date(j['lease_until'])<=execution.clock()]
    for jid in pending:execution.reconcile(jid)
    job=execution.claim(worker,device_id,credential)
    return execution.execute(job['job_id'],worker) if job else None

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    execution=service(os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL))
    try:
        while True:
            result=cycle(execution)
            if result:print(result['status'])
            if args.once:break
            time.sleep(1)
    finally:execution.store.close()

if __name__=='__main__':main()
