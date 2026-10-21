import json
import time
import httpx
from .errors import Fault
from .models import KnowledgeContext


class KnowledgeClient:
    """HTTP-only consumer. No corpus paths, subprocesses or retrieval implementation."""
    def __init__(self,settings,transport=None):
        self.settings=settings
        self.http=httpx.Client(base_url=settings.knowledge_endpoint,timeout=settings.timeout,
            headers={'Authorization':'Bearer '+settings.knowledge_token},trust_env=False,
            follow_redirects=False,transport=transport)

    def close(self):
        self.http.close()

    def _request(self,method,path,correlation_id,payload=None):
        attempts=2 if method=='GET' else 1
        for attempt in range(attempts):
            try:
                with self.http.stream(method,path,json=payload,headers={'X-Luma-Correlation-ID':correlation_id}) as response:
                    if response.status_code!=200:
                        code='KNOWLEDGE_UNAVAILABLE' if response.status_code>=500 else 'KNOWLEDGE_REJECTED'
                        raise Fault(code,503 if response.status_code>=500 else 502)
                    if 'application/json' not in response.headers.get('content-type',''):
                        raise Fault('KNOWLEDGE_PROTOCOL',502)
                    data=bytearray()
                    for part in response.iter_bytes():
                        data.extend(part)
                        if len(data)>2097152: raise Fault('KNOWLEDGE_PROTOCOL',502)
                    parsed=json.loads(data)
                    if not isinstance(parsed,dict): raise Fault('KNOWLEDGE_PROTOCOL',502)
                    return parsed
            except (httpx.TimeoutException,httpx.ConnectError):
                if attempt+1==attempts: raise Fault('KNOWLEDGE_UNAVAILABLE',503) from None
                time.sleep(.02)
            except (httpx.HTTPError,ValueError,UnicodeError):
                raise Fault('KNOWLEDGE_PROTOCOL',502) from None

    def health(self,correlation_id):
        data=self._request('GET','/health',correlation_id)
        if data.get('engine_available') is not True or data.get('status')!='ok' or data.get('service_version')!='0.1.0':
            raise Fault('KNOWLEDGE_UNAVAILABLE',503)
        return {'status':'AVAILABLE','service_version':'0.1.0'}

    def status(self,project_id,correlation_id):
        data=self._request('GET','/v1/knowledge/status',correlation_id)
        if (data.get('project_id')!=project_id or data.get('brain_version')!='0.6.0' or
            data.get('engine_version')!='1.4.0' or data.get('retrieval_mode')!='lexical' or
            data.get('production_verified') is not False):
            raise Fault('KNOWLEDGE_CONTRACT_MISMATCH',502)
        return data

    def query(self,request,correlation_id):
        status=self.status(request.project_id,correlation_id)
        data=self._request('POST','/v1/knowledge/query',correlation_id,request.model_dump(mode='json'))
        if (data.get('project_id')!=request.project_id or data.get('mode')!='lexical' or
            data.get('permission_status')!='NOT_DETERMINED_BY_RETRIEVAL' or
            not isinstance(data.get('request_id'),str) or not data['request_id'] or
            not isinstance(data.get('results'),list) or not isinstance(data.get('sources'),list) or
            not isinstance(data.get('warnings'),list) or
            not all(isinstance(w,str) for w in data['warnings'])):
            raise Fault('KNOWLEDGE_PROTOCOL',502)
        results,sources=data['results'],data['sources']
        required={'rank','score','document_id','chunk_id','title','section','excerpt','status','confidence','freshness','last_verified','source_commit','sensitivity','path','source_spans'}
        if len(results)!=len(sources) or len(results)>request.limits.max_chunks:
            raise Fault('KNOWLEDGE_PROTOCOL',502)
        chars=0
        documents=set()
        for i,(r,s) in enumerate(zip(results,sources)):
            if (not isinstance(r,dict) or not isinstance(s,dict) or not required<=r.keys() or
                not isinstance(r['excerpt'],str) or r['rank']!=i+1 or
                s.get('project_id')!=request.project_id or s.get('chunk_id')!=r['chunk_id'] or
                s.get('document_id')!=r['document_id'] or s.get('source_spans')!=r['source_spans'] or
                s.get('source_commit')!=r['source_commit'] or s.get('path')!=r['path'] or
                s.get('evidence_ref')!=f'results[{i}].excerpt'):
                raise Fault('KNOWLEDGE_PROTOCOL',502)
            chars+=len(r['excerpt']); documents.add(r['document_id'])
        if chars>request.limits.max_chars or len(documents)>request.limits.max_documents:
            raise Fault('KNOWLEDGE_PROTOCOL',502)
        try:
            return KnowledgeContext(project_id=request.project_id,brain_version=status['brain_version'],
                engine_version=status['engine_version'],query=request.query,results=results,sources=sources,
                warnings=data['warnings'],permission_status=data['permission_status'],request_id=data['request_id'],
                correlation_id=correlation_id,status=data['status'],confidence=data['confidence'])
        except (ValueError,KeyError,TypeError):
            raise Fault('KNOWLEDGE_PROTOCOL',502) from None


class KnowledgeService:
    def __init__(self,settings,projects,policy,client):
        self.settings,self.projects,self.policy=settings,projects,policy
        self.clients={'meu-gestor':client}

    def resolve_client(self,project):
        client=self.clients.get(project.project_id)
        if client is None or client.settings.knowledge_endpoint!=project.knowledge_endpoint:
            raise Fault('KNOWLEDGE_ROUTE_UNAVAILABLE',503)
        return client

    def query(self,principal,request,correlation_id):
        project=self.projects.resolve(request.project_id,principal)
        self.policy.check(principal,project,'knowledge','knowledge.read')
        history,packages=self.policy.knowledge_options() if hasattr(self.policy,'knowledge_options') else (self.settings.history,self.settings.packages)
        if request.include_history and not history: raise Fault('HISTORY_DENIED',403)
        if request.package and request.package not in packages: raise Fault('PACKAGE_DENIED',403)
        context=self.resolve_client(project).query(request,correlation_id)
        # Recheck revocation after I/O; do not release context if control state changed meanwhile.
        project=self.projects.resolve(request.project_id,principal)
        self.policy.check(principal,project,'knowledge','knowledge.read')
        return context
