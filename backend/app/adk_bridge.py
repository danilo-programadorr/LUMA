"""Bounded IPC; ADK has no model credentials, DB, control plane or tools."""
import json,os,subprocess,threading,queue,time
from pathlib import Path
from .errors import Fault
ROOT=Path(__file__).resolve().parents[2]
MAX_AGENT_HOPS=5
MAX_AGENT_INVOCATIONS=6
MAX_WORKFLOW_DURATION=180

def worker_environment():return {k:os.environ[k] for k in ('SYSTEMROOT','WINDIR') if k in os.environ}

def run_workflow(roles,generate,timeout=MAX_WORKFLOW_DURATION):
    if not 1<=len(roles)<=MAX_AGENT_INVOCATIONS:raise Fault('WORKFLOW_BUDGET_EXCEEDED',403)
    python=ROOT/'runtime/adk-venv/Scripts/python.exe'
    if not python.is_file():raise Fault('ADK_RUNTIME_UNAVAILABLE',503)
    process=subprocess.Popen([str(python),'-I',str(ROOT/'backend/adk_worker/worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=worker_environment(),cwd=ROOT,shell=False)
    messages=queue.Queue(maxsize=10);start=time.monotonic();calls=0
    def reader():
        try:
            while True:
                line=process.stdout.readline(131073);messages.put(line)
                if not line:break
        except (OSError,ValueError):pass
    thread=threading.Thread(target=reader,daemon=True);thread.start()
    def write(value):process.stdin.write(json.dumps(value,ensure_ascii=False).encode()+b'\n');process.stdin.flush()
    try:
        write({'roles':roles})
        while True:
            remaining=timeout-(time.monotonic()-start)
            if remaining<=0:raise Fault('WORKFLOW_BUDGET_EXCEEDED',503)
            try:line=messages.get(timeout=remaining)
            except queue.Empty:raise Fault('WORKFLOW_BUDGET_EXCEEDED',503) from None
            if not line or not line.endswith(b'\n') or len(line)>131072:raise Fault('ADK_PROTOCOL_INVALID',503)
            try:message=json.loads(line)
            except ValueError:raise Fault('ADK_PROTOCOL_INVALID',503) from None
            if message=={'op':'done'}:
                if calls!=len(roles):raise Fault('ADK_PROTOCOL_INVALID',503)
                return {'agent_calls':calls,'workflow_latency_ms':int((time.monotonic()-start)*1000)}
            if set(message)!={'op','agent_id'} or message['op']!='generate' or calls>=len(roles) or message['agent_id']!=roles[calls]['agent_id']:raise Fault('ADK_PROTOCOL_INVALID',503)
            decision=generate(message['agent_id'],calls);calls+=1
            if time.monotonic()-start>=timeout:raise Fault('WORKFLOW_BUDGET_EXCEEDED',503)
            write({'decision':decision})
    finally:
        if process.poll() is None:process.kill()
        process.wait(timeout=5)
        for stream in (process.stdin,process.stdout):
            try:stream.close()
            except OSError:pass
        thread.join(timeout=1)
