"""Phase-limited real-call accounting. Never stores answers, queries, HTML or URLs."""
import json,os,time,hashlib
from pathlib import Path
from backend.app.errors import Fault
REQUIRED=('SEARCH_SUGGESTIONS_UNMODIFIED','SEARCH_SUGGESTIONS_NOT_PERSISTED','NO_CLICK_TRACKING','NO_LINK_INDEXING','TRUST_BOUNDARY','CSP','ATTRIBUTION_RENDERING')
def validate_gate(path=Path('reports/FASE_7F_D_A_ATTRIBUTION_PRECHECK.json'),*,expected_status='PASS'):
    try:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if data['status']!=expected_status or any(data['criteria'].get(k)!='PASS' for k in REQUIRED) or data['criteria'].get('AUDIT')!='VERIFIED' or data['criteria'].get('SECRET_SCAN')!='PASSED':raise ValueError()
        for name,digest in data['candidate_files'].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError()
        if not data['candidate_files']:raise ValueError()
    except (OSError,ValueError,KeyError,TypeError):raise Fault('RESEARCH_ATTRIBUTION_GATE_REQUIRED',403) from None
class AcceptanceLedger:
    maximum_calls=6
    def __init__(self,path=Path('runtime/research-google-acceptance-usage.json')):self.path=Path(path);self.lock=self.path.with_suffix('.lock')
    def edit(self,fn):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:fd=os.open(self.lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:raise Fault('RESEARCH_BUDGET_LOCKED',409) from None
        try:
            data=json.loads(self.path.read_text()) if self.path.exists() else {'maximum_calls':self.maximum_calls,'halted':False,'calls':[]}
            result=fn(data);temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2));os.replace(temp,self.path);return result
        finally:os.close(fd);self.lock.unlink(missing_ok=True)
    def _assert_open(self,data):
        if data.get('maximum_calls')!=self.maximum_calls or type(data.get('calls')) is not list:raise Fault('RESEARCH_BUDGET_INVALID',409)
        if data.get('halted') is not False:raise Fault('RESEARCH_REVALIDATION_REQUIRED',403)
        if len(data['calls'])>=self.maximum_calls:raise Fault('RESEARCH_BUDGET_EXCEEDED',429)
    def _reserve(self,data,model):
        self._assert_open(data)
        n=len(data['calls'])+1;data['calls'].append({'call':n,'model':model,'started_at':int(time.time()),'response_received':False,'search_queries':None,'input_tokens':None,'output_tokens':None,'latency_ms':None,'status':'ATTEMPT_RESERVED'})
        return n
    def reserve(self,model):return self.edit(lambda data:self._reserve(data,model))
    def finish(self,n,usage,error_code=None):
        def finish(data):
            row=data['calls'][n-1]
            if type(usage.get('response_received')) is bool:row['response_received']=usage['response_received']
            for key in ('search_queries','input_tokens','output_tokens','thought_tokens','tool_use_tokens','total_tokens','cached_tokens','latency_ms'):
                if key in usage and (usage[key] is None or type(usage[key]) is int and usage[key]>=0):row[key]=usage[key]
            for key,allowed in (('failure_stage',('REQUEST_SEND','RESPONSE_DECODE','USAGE_READ','NORMALIZATION')),('error_kind',('CONTROLLED','SCHEMA','SHAPE','TRANSPORT','OTHER'))):
                if usage.get(key) in allowed:row[key]=usage[key]
            row.update(status='FAILED' if error_code else 'COMPLETED',error_code=error_code,completed_at=int(time.time()))
            if error_code:data['halted']=True
        self.edit(finish)
