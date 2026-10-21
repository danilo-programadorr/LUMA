"""One request per process. No arbitrary environment, tools, DB or shell protocol."""
import os,sys,json,logging
logging.disable(logging.CRITICAL)
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.app.model_contracts import ModelInputContext
from backend.app.model_config import ModelSettings
from backend.app.errors import Fault
from backend.model_worker.adapter import GeminiAdapter

MAX_FRAME=262144

def main():
    correlation='';adapter=None
    try:
        raw=sys.stdin.buffer.readline(MAX_FRAME+1)
        if len(raw)>MAX_FRAME or not raw.endswith(b'\n'): raise Fault('MODEL_INVALID_RESPONSE',503)
        request=json.loads(raw)
        if set(request)!={'correlation_id','context','config'}: raise Fault('MODEL_INVALID_RESPONSE',503)
        correlation=request['correlation_id']
        if not isinstance(correlation,str) or not 1<=len(correlation)<=64: raise Fault('MODEL_INVALID_RESPONSE',503)
        config=request['config']
        if set(config)!={'model','timeout','max_output_tokens','temperature'}: raise Fault('MODEL_INVALID_RESPONSE',503)
        ModelSettings(provider='gemini',api_key=os.environ.get('GEMINI_API_KEY',''),**config)
        context=ModelInputContext.model_validate_json(json.dumps(request['context']))
        adapter=GeminiAdapter(os.environ.get('GEMINI_API_KEY',''),config)
        result=adapter.generate(context)
        reply=dict(correlation_id=correlation,result=result.model_dump(mode='json'))
    except Fault as exc: reply=dict(correlation_id=correlation,error=exc.code)
    except Exception: reply=dict(correlation_id=correlation,error='MODEL_INVALID_RESPONSE')
    finally:
        if adapter:
            try: adapter.close()
            except Exception: pass
    output=json.dumps(reply,ensure_ascii=False).encode('utf8')+b'\n'
    if len(output)>131072: output=json.dumps(dict(correlation_id=correlation,error='MODEL_INVALID_RESPONSE')).encode()+b'\n'
    sys.stdout.buffer.write(output);sys.stdout.buffer.flush()

if __name__=='__main__': main()
