"""Single-purpose stdio MCP broker. It never accepts an executable or command."""
import hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
if __package__ in (None,''):
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class ValidationBroker:
 def __init__(self,context,validate):
  self.context=context;self.validate=validate;self.calls=0
 def handle(self,message):
  ident=message.get('id');method=message.get('method')
  if ident is None:return None
  def result(body):return dict(jsonrpc='2.0',id=ident,result=body)
  def error():return dict(jsonrpc='2.0',id=ident,error={'code':-32602,'message':'CODEX_VALIDATION_REQUEST_DENIED'})
  if method=='initialize':
   return result({'protocolVersion':message.get('params',{}).get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'luma-validation','version':'1'}})
  if method=='ping':return result({})
  if method=='tools/list':
   return result({'tools':[{'name':'validate','description':'Run the exact pre-approved local fixture tests. No arguments, network or installation. Maximum two requests.','inputSchema':{'type':'object','properties':{},'additionalProperties':False}}]})
  if method!='tools/call':return error()
  p=message.get('params',{})
  if not isinstance(p,dict) or set(p)-{'name','arguments','_meta'} or p.get('name')!='validate' or p.get('arguments',{})!={}:return error()
  if self.calls>=2 or datetime.now(timezone.utc)>=datetime.fromisoformat(self.context['expires_at']) or (self.context.get('deadline_monotonic') is not None and time.monotonic()>=self.context['deadline_monotonic']):return error()
  self.calls+=1
  try:passed=self.validate() is True
  except Exception:passed=False
  return result({'content':[{'type':'text','text':json.dumps({'validation_pass':passed,'status':'PASS' if passed else 'FAILED'})}],'isError':not passed})
def main():
 if len(sys.argv)!=3:raise SystemExit(2)
 path=Path(sys.argv[1]);raw=path.read_bytes()
 if len(raw)>16384 or hashlib.sha256(raw).hexdigest()!=sys.argv[2]:raise SystemExit(2)
 context=json.loads(raw)
 from backend.codex.contracts import ExecutionProfile
 from device_agent.codex_invocation import validate_fixture
 profile=ExecutionProfile.model_validate(context['profile'])
 def validate():
  return validate_fixture(Path(context['binary']),Path(context['root']),profile,lambda:datetime.now(timezone.utc)<datetime.fromisoformat(context['expires_at']),deadline=context.get('deadline_monotonic'))
 broker=ValidationBroker(context,validate)
 while True:
  line=sys.stdin.buffer.readline(8193)
  if not line:break
  if len(line)>8192 or not line.endswith(b'\n'):raise SystemExit(2)
  try:
   message=json.loads(line)
   if not isinstance(message,dict):raise ValueError()
   response=broker.handle(message)
  except Exception:response=None
  if response is not None:print(json.dumps(response),flush=True)
if __name__=='__main__':main()
