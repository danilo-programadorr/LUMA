"""Dedicated, bounded process adapter; no SDK import in backend process."""
import json,os,sys,subprocess,threading,queue
from pathlib import Path
from .errors import Fault
from .generation import ModelResult

ERRORS={'MODEL_TIMEOUT','MODEL_UNAVAILABLE','MODEL_AUTH_ERROR','MODEL_RATE_LIMIT','MODEL_INVALID_RESPONSE','MODEL_ERROR','MODEL_SAFETY_REJECTION'}

def worker_environment(key):
    result={'GEMINI_API_KEY':key}
    for name in ('SYSTEMROOT','WINDIR'):
        if os.environ.get(name): result[name]=os.environ[name]
    return result

class GeminiModelProvider:
    def __init__(self,settings):
        self.diagnostic={};self.config=settings;self.guard=threading.Lock();self.slots=threading.BoundedSemaphore(2)
        self.active=set();self.closed=False;self.last='NOT_PROBED' if settings.configured else 'MODEL_UNAVAILABLE'
        self.worker=Path(__file__).resolve().parents[1]/'model_worker/worker.py'
    def status(self):
        return dict(provider=self.config.provider,configured=self.config.configured,available=self.last=='READY',status=self.last)
    def close(self):
        with self.guard:
            self.closed=True;processes=list(self.active)
        for process in processes:
            if process.poll() is None: process.kill()
            process.wait(timeout=5)
    def generate(self,context,correlation_id):
        self.diagnostic=dict(failure_stage='model worker startup',generation_attempted=False)
        if not self.config.configured or self.closed: raise Fault('MODEL_UNAVAILABLE',503)
        frame=json.dumps(dict(correlation_id=correlation_id,context=context.model_dump(mode='json'),config=dict(model=self.config.model,
            timeout=self.config.timeout,max_output_tokens=self.config.max_output_tokens,temperature=self.config.temperature)),ensure_ascii=False).encode('utf8')+b'\n'
        if len(frame)>262144: raise Fault('MODEL_INPUT_TOO_LARGE',413)
        if not self.slots.acquire(timeout=1): raise Fault('MODEL_BUSY',503)
        process=None;threads=[]
        try:
            with self.guard:
                if self.closed: raise Fault('MODEL_UNAVAILABLE',503)
                process=subprocess.Popen([sys.executable,'-I',str(self.worker)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,shell=False,env=worker_environment(self.config.api_key),cwd=str(self.worker.parent),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                self.active.add(process)
            responses=queue.Queue(maxsize=1)
            def write():
                try: process.stdin.write(frame);process.stdin.flush()
                except (OSError,ValueError): pass
                finally:
                    try: process.stdin.close()
                    except (OSError,ValueError): pass
            def read():
                try: responses.put(process.stdout.readline(131073))
                except (OSError,ValueError): responses.put(b'')
            for target in (write,read):
                thread=threading.Thread(target=target,daemon=True);thread.start();threads.append(thread)
            try: raw=responses.get(timeout=self.config.timeout)
            except queue.Empty: raise Fault('MODEL_TIMEOUT',504) from None
            if not raw.endswith(b'\n') or len(raw)>131072: raise Fault('MODEL_INVALID_RESPONSE',503)
            response=json.loads(raw)
            if response.get('correlation_id')!=correlation_id: raise Fault('MODEL_INVALID_RESPONSE',503)
            if set(response)=={'correlation_id','error','diagnostic'}:
                diagnostic=response.pop('diagnostic')
                if not isinstance(diagnostic,dict) or set(diagnostic)!={'failure_stage','credential_present','generation_attempted','safe_error_type','safe_detail'} or diagnostic['failure_stage'] not in {'model worker startup','GeminiAdapter initialization','first generation','schema validation','response validation'} or type(diagnostic['credential_present']) is not bool or type(diagnostic['generation_attempted']) is not bool:
                    raise Fault('MODEL_INVALID_RESPONSE',503)
                if diagnostic['safe_error_type'] not in {'Fault','InternalError','APIError','ValidationError','ValueError'} or diagnostic['safe_detail'] not in {'NONE','MAX_TOKENS','NON_STOP_FINISH','HTTP_OTHER',*(f'HTTP_{c}' for c in (400,401,403,404,429,500,502,503,504))}:
                    raise Fault('MODEL_INVALID_RESPONSE',503)
                self.diagnostic=diagnostic
            if set(response)=={'correlation_id','error'}:
                code=response['error']
                if code not in ERRORS: code='MODEL_INVALID_RESPONSE'
                raise Fault(code,504 if code=='MODEL_TIMEOUT' else 503)
            if set(response)!={'correlation_id','result'}: raise Fault('MODEL_INVALID_RESPONSE',503)
            result=ModelResult.model_validate_json(json.dumps(response['result']))
            if result.model_name!=self.config.model or result.instruction_version!='luma-system-2': raise Fault('MODEL_INVALID_RESPONSE',503)
            self.diagnostic=dict(failure_stage=None,generation_attempted=True,credential_present=True)
            self.last='READY'
            return result
        except Fault as exc: self.last=exc.code;raise
        except Exception: self.last='MODEL_INVALID_RESPONSE';raise Fault('MODEL_INVALID_RESPONSE',503) from None
        finally:
            if process:
                try:
                    if process.poll() is None:
                        try: process.wait(timeout=.2)
                        except subprocess.TimeoutExpired: process.kill();process.wait(timeout=5)
                finally:
                    for thread in threads: thread.join(timeout=2)
                    for stream in (process.stdin,process.stdout):
                        try: stream.close()
                        except (OSError,ValueError): pass
                    with self.guard: self.active.discard(process)
            self.slots.release()
