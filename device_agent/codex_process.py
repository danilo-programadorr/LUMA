"""Bounded process IO and process-tree lifetime. No model authority lives here."""
import ctypes,json,os,queue,re,signal,subprocess,threading,time,codecs
from ctypes import wintypes as W
def redact(text):
    text=str(text)
    patterns=[r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)',r'(?i)Bearer\s+\S+',r'(?:sk-|AIza|GOCSPX-)[A-Za-z0-9_-]{12,}',r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b',r'(?i)postgres(?:ql)?(?:\+[A-Za-z0-9_]+)?://[^\s<>()]+',r'(?i)\b(?:password|token|secret|api[_-]?key)\s*[=:]\s*[^\s,;]+']
    for pattern in patterns:text=re.sub(pattern,'[REDACTED]',text)
    return text[:500]

class EventFilter:
    def __init__(self,limit):
        self.decoder=codecs.getincrementaldecoder('utf8')(errors='replace');self.limit=limit;self.total=0;self.buffer='';self.summary='';self.usage={};self.interaction=False;self.failed=False;self.final_schema_valid=False;self.turn_completed=False
    def feed(self,source,raw):
        self.total+=len(raw)
        if self.total>self.limit:raise ValueError('CODEX_OUTPUT_TRUNCATED')
        if source!='stdout':return
        self.buffer+=self.decoder.decode(raw)
        while '\n' in self.buffer:
            line,self.buffer=self.buffer.split('\n',1)
            try:event=json.loads(line)
            except (ValueError,TypeError):continue
            if not isinstance(event,dict):continue
            kind=event.get('type')
            if kind in ('approval.requested','permission.requested','interaction.required'):self.interaction=True
            if kind in ('turn.failed','error'):self.failed=True
            if kind=='turn.completed':
                self.turn_completed=True
                usage=event.get('usage',{})
                if isinstance(usage,dict):self.usage={k:v for k,v in usage.items() if k in ('input_tokens','output_tokens','cached_input_tokens','reasoning_output_tokens') and type(v) is int and v>=0}
            item=event.get('item',{})
            if kind=='item.completed' and isinstance(item,dict) and item.get('type')=='agent_message':
                self.final_schema_valid=False
                try:message=json.loads(item.get('text',''))
                except (ValueError,TypeError):continue
                if isinstance(message,dict) and set(message)=={'summary'} and isinstance(message['summary'],str) and message['summary'].strip():self.summary=redact(message['summary']);self.final_schema_valid=True
            # No reasoning/raw item/event is retained.
class WinJob:
    def __init__(self):
        k=ctypes.WinDLL('kernel32',use_last_error=True);self.k=k;self.lock=threading.Lock()
        k.CreateJobObjectW.argtypes=(ctypes.c_void_p,W.LPCWSTR);k.CreateJobObjectW.restype=W.HANDLE
        k.SetInformationJobObject.argtypes=(W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD);k.SetInformationJobObject.restype=W.BOOL
        k.AssignProcessToJobObject.argtypes=(W.HANDLE,W.HANDLE);k.AssignProcessToJobObject.restype=W.BOOL
        k.CloseHandle.argtypes=(W.HANDLE,);k.CloseHandle.restype=W.BOOL
        k.CreateToolhelp32Snapshot.argtypes=(W.DWORD,W.DWORD);k.CreateToolhelp32Snapshot.restype=W.HANDLE
        k.OpenThread.argtypes=(W.DWORD,W.BOOL,W.DWORD);k.OpenThread.restype=W.HANDLE
        k.ResumeThread.argtypes=(W.HANDLE,);k.ResumeThread.restype=W.DWORD
        class Basic(ctypes.Structure):
            _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',W.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',W.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',W.DWORD),('SchedulingClass',W.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_ulonglong) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class Extended(ctypes.Structure):
            _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        self.handle=k.CreateJobObjectW(None,None)
        if not self.handle:raise ValueError('CODEX_PROCESS_CONTAINMENT_UNAVAILABLE')
        limit=Extended();limit.BasicLimitInformation.LimitFlags=0x2000|0x8;limit.BasicLimitInformation.ActiveProcessLimit=32
        if not k.SetInformationJobObject(self.handle,9,ctypes.byref(limit),ctypes.sizeof(limit)):
            self.close();raise ValueError('CODEX_PROCESS_CONTAINMENT_UNAVAILABLE')
    def attach_and_resume(self,process,check,before_resume):
        if not self.k.AssignProcessToJobObject(self.handle,W.HANDLE(int(process._handle))):raise ValueError('CODEX_PROCESS_CONTAINMENT_UNAVAILABLE')
        before_resume()
        permit=check()
        if permit is not True:raise ValueError(permit if isinstance(permit,str) else 'CODEX_AUTHORIZATION_REVOKED')
        class ThreadEntry(ctypes.Structure):
            _fields_=[('dwSize',W.DWORD),('cntUsage',W.DWORD),('th32ThreadID',W.DWORD),('th32OwnerProcessID',W.DWORD),('tpBasePri',W.LONG),('tpDeltaPri',W.LONG),('dwFlags',W.DWORD)]
        self.k.Thread32First.argtypes=(W.HANDLE,ctypes.POINTER(ThreadEntry));self.k.Thread32First.restype=W.BOOL
        self.k.Thread32Next.argtypes=(W.HANDLE,ctypes.POINTER(ThreadEntry));self.k.Thread32Next.restype=W.BOOL
        snap=self.k.CreateToolhelp32Snapshot(4,0)
        if snap==ctypes.c_void_p(-1).value:raise ValueError('CODEX_PROCESS_CONTAINMENT_UNAVAILABLE')
        entry=ThreadEntry();entry.dwSize=ctypes.sizeof(entry);resumed=False
        try:
            more=self.k.Thread32First(snap,ctypes.byref(entry))
            while more:
                if entry.th32OwnerProcessID==process.pid:
                    thread=self.k.OpenThread(2,False,entry.th32ThreadID)
                    if not thread:raise ValueError('CODEX_PROCESS_CONTAINMENT_UNAVAILABLE')
                    try:
                        if self.k.ResumeThread(thread)==0xffffffff:raise ValueError('CODEX_PROCESS_CONTAINMENT_UNAVAILABLE')
                        resumed=True
                    finally:self.k.CloseHandle(thread)
                more=self.k.Thread32Next(snap,ctypes.byref(entry))
        finally:self.k.CloseHandle(snap)
        if not resumed:raise ValueError('CODEX_PROCESS_CONTAINMENT_UNAVAILABLE')
    def close(self):
        with self.lock:
            if getattr(self,'handle',None):self.k.CloseHandle(self.handle);self.handle=None
class ProcessRunner:
    def run(self,argv,stdin,*,check,timeout,max_output,cwd=None,env=None,on_started=None):
        start=time.monotonic();permit=check()
        if permit is not True or time.monotonic()-start>=timeout:
            code='CODEX_TIMEOUT' if time.monotonic()-start>=timeout else permit if isinstance(permit,str) else 'CODEX_AUTHORIZATION_REVOKED'
            return dict(exit_code=None,code=code,summary='',usage={},tree_closed=True,process_started=False,final_schema_valid=False)
        events=EventFilter(max_output);last_check=time.monotonic();stream=queue.Queue(maxsize=64);done=threading.Event();timed_out=threading.Event();job=WinJob() if os.name=='nt' else None;process=None;started=False;code='CODEX_EXITED'
        def reader(source,pipe):
            try:
                while not done.is_set():
                    raw=pipe.read(512)
                    if not raw:break
                    while not done.is_set():
                        try:stream.put((source,raw),timeout=.1);break
                        except queue.Full:pass
            finally:
                while not done.is_set():
                    try:stream.put((source,None),timeout=.1);break
                    except queue.Full:pass
        def watchdog():
            if not done.wait(max(0,timeout-(time.monotonic()-start))):
                timed_out.set()
                if job:job.close()
                else:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
        def start_watchdog():threading.Thread(target=watchdog,daemon=True).start()
        try:
            process=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,creationflags=0x4|0x08000000 if os.name=='nt' else 0,start_new_session=os.name!='nt')
            if job:job.attach_and_resume(process,check,start_watchdog)
            else:start_watchdog()
            started=True
            if on_started:on_started(process.pid)
            last_check=time.monotonic()
            def write_input():
                try:process.stdin.write(stdin.encode('utf8'));process.stdin.close()
                except (BrokenPipeError,OSError,ValueError):pass
            threads=[threading.Thread(target=reader,args=(name,pipe),daemon=True) for name,pipe in (('stdout',process.stdout),('stderr',process.stderr))]
            for t in threads:t.start()
            threading.Thread(target=write_input,daemon=True).start();closed=0
            while closed<2 or process.poll() is None:
                now=time.monotonic()
                if now-start>=timeout:code='CODEX_TIMEOUT';break
                if now-last_check>=2:
                    permit=check();last_check=time.monotonic()
                    if permit is not True:code=permit if isinstance(permit,str) and re.fullmatch(r'[A-Z0-9_]{1,80}',permit) else 'CODEX_AUTHORIZATION_REVOKED';break
                try:source,raw=stream.get(timeout=.1)
                except queue.Empty:continue
                if raw is None:closed+=1;continue
                try:events.feed(source,raw)
                except ValueError:code='CODEX_OUTPUT_TRUNCATED';break
                if events.interaction:code='CODEX_INTERACTION_REQUIRED';break
            if events.failed and code=='CODEX_EXITED':code='CODEX_PROVIDER_FAILED'
        except ValueError as exc:
            value=str(exc);code=value if re.fullmatch(r'CODEX_[A-Z_]+',value) else 'CODEX_LOCAL_OPERATION_FAILED'
        finally:
            done.set()
            if timed_out.is_set():code='CODEX_TIMEOUT'
            if job:job.close()
            if process:
                if os.name!='nt':
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                if process.poll() is None:process.kill()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:raise ValueError('CODEX_PROCESS_TERMINATION_UNCONFIRMED')
        return dict(exit_code=process.returncode if process else None,code=code,summary=events.summary,usage=events.usage,tree_closed=True,process_started=started,final_schema_valid=events.final_schema_valid and events.turn_completed)
