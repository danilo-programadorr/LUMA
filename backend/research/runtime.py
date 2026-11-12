"""Research processor with no canonical database or authority-service imports."""
import time
from backend.app.errors import Fault
from .contracts import ResearchRequest,ResearchResult
from .policy import ExternalQueryPolicy,URLPolicy

class ResearchProcessor:
    def __init__(self,provider,project_reader=None):self.provider=provider;self.project_reader=project_reader;self.cache={}
    def process(self,request,progress=lambda stage:None,check=lambda:None):
        request=ResearchRequest.model_validate(request);route=request.route.route
        calls_before=getattr(self.provider,'calls',0)
        try:
            check()
            if request.expires_at<=int(time.time()):raise Fault('RESEARCH_EXPIRED',409)
            if route=='PRIVATE_LIBRARY_FUTURE':raise Fault('PRIVATE_LIBRARY_UNAVAILABLE',503)
            if route=='NO_RETRIEVAL':return ResearchResult(research_id=request.research_id,status='COMPLETED',answer='Esta solicitação não requer pesquisa. O fluxo de transformação permanece separado.',freshness_status='NOT_REQUIRED',completed_at=int(time.time()))
            project_answer='';refs=[]
            if route in ('PROJECT_FIRST','HYBRID_WEB_PROJECT'):
                if self.project_reader is None:raise Fault('PROJECT_KNOWLEDGE_UNAVAILABLE',503)
                project_answer,refs=self.project_reader(request)
                if not project_answer:raise Fault('PROJECT_KNOWLEDGE_UNAVAILABLE',503)
                if route=='PROJECT_FIRST':return ResearchResult(research_id=request.research_id,status='COMPLETED',project_answer=project_answer,project_evidence=refs,freshness_status='NOT_REQUIRED',completed_at=int(time.time()))
                # Internal snippets never become provider inputs.
                if not request.public_query:raise Fault('PUBLIC_QUERY_REQUIRED',403)
            ExternalQueryPolicy().check(request.public_query or request.query)
            for url in request.urls:URLPolicy().check(url)
            check();progress('READING_SOURCES' if request.urls else 'SEARCHING_WEB')
            import hashlib,json
            from .policy import ResearchUsagePolicy
            key=hashlib.sha256(json.dumps({'project':request.project_id,'device':request.target_device_id,'query':request.public_query or request.query,'urls':request.urls,'route':request.route.model_dump(),'depth':request.max_depth},sort_keys=True).encode()).hexdigest()
            ttl=ResearchUsagePolicy.cache_ttl[request.route.freshness_horizon]
            cached=self.cache.get(key) if getattr(self.provider,'cache_allowed',False) and getattr(self.provider,'name','')!='gemini_google_search' else None
            if cached and ttl and int(time.time())-cached.completed_at<ttl:
                result=cached.model_copy(update={'research_id':request.research_id,'usage':cached.usage.model_copy(update={'model_calls':0})})
            else:
                result=self.provider.inspect_urls(request) if request.urls else self.provider.search(request)
                if result.provider!='gemini_google_search' and getattr(self.provider,'cache_allowed',False) and ttl:
                    if len(self.cache)>=32:self.cache.pop(next(iter(self.cache)))
                    self.cache[key]=result
            check();progress('SYNTHESIZING')
            result=result.model_copy(update={'project_answer':project_answer,'project_evidence':refs})
            return ResearchResult.model_validate(result.model_dump())
        except Fault as e:
            code=e.code
            if code=='WEB_RESEARCH_UNAVAILABLE' and request.route.freshness_required:code='FRESHNESS_UNAVAILABLE'
            extra={}
            if getattr(self.provider,'name','')=='gemini_google_search' and getattr(self.provider,'calls',0)>calls_before:
                from .contracts import Usage
                u=getattr(self.provider,'last_usage',{})
                extra={'provider':'gemini_google_search','model':self.provider.settings.model,'usage':Usage(**{k:v for k,v in u.items() if k in Usage.model_fields})}
            return ResearchResult(research_id=request.research_id,status='FAILED',error_code=code,completed_at=int(time.time()),**extra)

class ProjectKnowledgeReader:
    def __init__(self,client):self.client=client
    def __call__(self,request):
        if request.project_id!='meu-gestor' or 'luma' in request.query.lower():raise Fault('PROJECT_KNOWLEDGE_UNAVAILABLE',503)
        from backend.app.models import KnowledgeRequest,Limits
        context=self.client.query(KnowledgeRequest(project_id=request.project_id,query=request.query,limits=Limits(max_chars=3500,max_chunks=4,max_documents=4)),request.research_id)
        return '\n\n'.join(x['excerpt'] for x in context.results)[:4000],[x['document_id']+':'+x['chunk_id'] for x in context.results][:8]
