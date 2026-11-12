"""Managed search only. No scraper, browser, executable tools or private context."""
import json,time,os,re
from typing import Protocol
from dataclasses import dataclass
from pydantic import ValidationError
from backend.app.errors import Fault
from .contracts import ResearchResult,Citation,Usage,GoogleDisplayArtifact
from .policy import ExternalQueryPolicy,URLPolicy,SourceRankingPolicy,ResearchUsagePolicy
from .usage import read_token_usage
from .instructions import research_instruction

class WebResearchProvider(Protocol):
    def search(self,request):...
    def inspect_urls(self,request):...
    def capabilities(self):...
    def usage(self):...
    def health(self):...

@dataclass(frozen=True)
class ResearchProviderSettings:
    model:str='gemini-3.8-flash'
    real_calls_approved:bool=False
    attribution_approved:bool=False
    max_session_calls:int=0
    acceptance_profile:str='INITIAL_SIX'
    final_three_owner_approved:bool=False

class GeminiGoogleSearchProvider:
    cache_allowed=False
    name='gemini_google_search'
    def __init__(self,api_key,settings=None,client=None):
        self.settings=settings or ResearchProviderSettings();self.api_key=api_key;self.client=client;self.calls=0;self._real_transport=client is None;self.last_usage={};self.acceptance_halted=False
        self.egress=ExternalQueryPolicy((api_key,*(os.environ.get(k,'') for k in ('LUMA_KNOWLEDGE_TOKEN','LUMA_RUNTIME_TOKEN','LUMA_OWNER_TOKEN','LUMA_ADMIN_CONFIRM_TOKEN'))));self.url=URLPolicy()
    def capabilities(self):return {'search':True,'inspect_urls':True,'cache':False,'model':self.settings.model}
    def health(self):return {'configured':bool(self.api_key),'real_enabled':self.settings.real_calls_approved and self.settings.attribution_approved}
    def usage(self):return {'model_calls':self.calls,'incremental_cost_usd':None}
    def search(self,request):return self._call(request,'google_search')
    def inspect_urls(self,request):return self._call(request,'url_context')
    def _call(self,request,tool):
        cfg=self.settings
        if not cfg.real_calls_approved:raise Fault('RESEARCH_COST_GATE_REQUIRED',403)
        if not cfg.attribution_approved:raise Fault('RESEARCH_ATTRIBUTION_GATE_REQUIRED',403)
        if not self.api_key:raise Fault('WEB_RESEARCH_UNAVAILABLE',503)
        if self.calls>=cfg.max_session_calls:raise Fault('RESEARCH_BUDGET_EXCEEDED',429)
        ledger=None;reservation=None;final_case=None
        if cfg.acceptance_profile not in ('INITIAL_SIX','FINAL_THREE'):raise Fault('RESEARCH_ACCEPTANCE_PROFILE_INVALID',403)
        if cfg.acceptance_profile=='FINAL_THREE' and cfg.final_three_owner_approved is not True:raise Fault('RESEARCH_FINAL_APPROVAL_REQUIRED',403)
        if self._real_transport:
            if cfg.acceptance_profile=='FINAL_THREE':
                from .final_acceptance import prepare_final_acceptance
                ledger,final_case=prepare_final_acceptance(request,tool,cfg.final_three_owner_approved,cfg.model)
            else:
                from .acceptance import validate_gate,AcceptanceLedger
                validate_gate();ledger=AcceptanceLedger()
        query=self.egress.check(request.public_query or request.query)
        urls=[self.url.check(u,resolve=True) for u in request.urls]
        if tool=='url_context' and not urls:raise Fault('UNSAFE_URL',400)
        if self.client is None:
            from google import genai
            from google.genai import types
            self.client=genai.Client(api_key=self.api_key,http_options=types.HttpOptions(timeout=60000,retry_options=types.HttpRetryOptions(attempts=1)))
        if ledger:reservation=ledger.reserve_case(cfg.model,final_case) if final_case else ledger.reserve(cfg.model)
        self.calls+=1;started=time.monotonic();self.last_usage={'model_calls':1,'response_received':False,'search_queries':None,**read_token_usage({}),'latency_ms':0}
        stage='REQUEST_SEND'
        try:
            response=self.client.interactions.create(model=cfg.model,input=json.dumps({'public_question':query,'selected_public_urls':urls},ensure_ascii=False),tools=[{'type':tool}],store=False,
                system_instruction=research_instruction(request),
                generation_config={'max_output_tokens':2000,'thinking_level':'low','thinking_summaries':'none'})
            self.last_usage['response_received']=True
            stage='RESPONSE_DECODE'
            data=response.model_dump(mode='json',exclude_none=True)
            stage='USAGE_READ'
            u=data.get('usage',{}) or {}
            self.last_usage.update(read_token_usage(u),latency_ms=int((time.monotonic()-started)*1000))
            steps=data.get('steps',[])
            calls=[s for s in steps if s.get('type')=='google_search_call']
            self.last_usage['search_queries']=sum(len(s.get('arguments',{}).get('queries',[])) for s in calls) if calls else (0 if tool=='url_context' else None)
            if len(json.dumps(data))>262144:raise Fault('RESEARCH_PROVIDER_ERROR',502)
            stage='NORMALIZATION'
            result=normalize_interaction(data,request,self.name,cfg.model,int((time.monotonic()-started)*1000),tool)
            if ledger:ledger.finish(reservation,self.last_usage)
            self.acceptance_halted=bool(ledger and reservation>=ledger.maximum_calls)
            return result
        except Exception as exc:
            kind='CONTROLLED' if isinstance(exc,Fault) else 'SCHEMA' if isinstance(exc,ValidationError) else 'SHAPE' if isinstance(exc,(TypeError,KeyError,AttributeError,IndexError)) else 'TRANSPORT' if stage=='REQUEST_SEND' else 'OTHER'
            code=exc.code if isinstance(exc,Fault) else 'RESEARCH_PROVIDER_SCHEMA_INVALID' if kind=='SCHEMA' else 'RESEARCH_PROVIDER_RESPONSE_INVALID' if kind=='SHAPE' else 'RESEARCH_PROVIDER_ERROR'
            # Only fixed operational labels, never exception text, provider content or URLs.
            self.last_usage.update(latency_ms=int((time.monotonic()-started)*1000),failure_stage=stage,error_kind=kind)
            self.acceptance_halted=True
            if ledger:ledger.finish(reservation,self.last_usage,code)
            if isinstance(exc,Fault):raise
            raise Fault(code,502) from None


def citation_character_range(text,annotation):
    # Interactions API/SDK defines offsets in UTF-8 bytes; our contract uses code points.
    start=annotation.get('start_index');end=annotation.get('end_index')
    if start is None or end is None:raise Fault('RESEARCH_CITATION_OFFSETS_MISSING',502)
    raw=text.encode('utf-8')
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(raw):raise Fault('RESEARCH_CITATION_RANGE_INVALID',502)
    try:return len(raw[:start].decode('utf-8')),len(raw[:end].decode('utf-8'))
    except UnicodeDecodeError:raise Fault('RESEARCH_CITATION_RANGE_INVALID',502) from None


def normalize_interaction(data,request,provider,model,latency,tool):
    # Only final text, URL annotations, tool-use metadata and usage enter the result.
    answer='';sources={};citations=[];queries=[];suggestions=[];used=False;url_count=0;presentation='SANDBOXED_FRAME'
    stamp=int(time.time());ranking=SourceRankingPolicy();egress=ExternalQueryPolicy()
    successful_urls=set()
    if tool=='url_context':
        for step in data.get('steps',[]):
            if step.get('type')=='url_context_result':
                for item in step.get('result',[]):
                    if item.get('status')=='success':
                        successful_urls.add(ranking.normalize(item['url'],'',stamp,provider).canonical_url)
        if not successful_urls:raise Fault('RESEARCH_EVIDENCE_INSUFFICIENT',502)
    for step in data.get('steps',[]):
        kind=step.get('type')
        if kind=='google_search_call':
            queries.extend(egress.check(q) for q in step.get('arguments',{}).get('queries',[]))
        if kind=='google_search_result':
            used=True
            # Opaque authenticated-provider artifact; do not extract/rewrite links or labels.
            for item in step.get('result',[])[:5]:
                if item.get('search_suggestions'):
                    try:html=validate_google_suggestions(item['search_suggestions'])
                    except Fault as e:
                        if e.code!='RESEARCH_ATTRIBUTION_NAVIGATION_UNSUPPORTED':raise
                        html=validate_google_suggestions(item['search_suggestions'],navigation='window');presentation='ISOLATED_WINDOW'
                    suggestions.append(html)
        if kind=='url_context_result' and tool=='url_context':used=bool(successful_urls);url_count=len(successful_urls)
        if kind!='model_output':continue
        for block in step.get('content',[]):
            if block.get('type')!='text':continue
            text=block.get('text','');offset=len(answer);answer+=text
            if len(answer)>6000:raise Fault('RESEARCH_PROVIDER_ERROR',502)
            for a in block.get('annotations',[]):
                if a.get('type')!='url_citation':continue
                source=ranking.normalize(a['url'],a.get('title') or '',stamp,provider)
                if tool=='url_context' and source.canonical_url not in successful_urls:raise Fault('RESEARCH_EVIDENCE_INSUFFICIENT',502)
                sources[source.source_id]=source
                start,end=citation_character_range(text,a)
                citations.append(Citation(citation_id='citation-'+str(len(citations)),source_id=source.source_id,start_index=offset+start,end_index=offset+end))
    if not used or not sources or not citations or not answer:raise Fault('RESEARCH_EVIDENCE_INSUFFICIENT',502)
    if len(sources)>request.max_sources or len(citations)>24:raise Fault('RESEARCH_PROVIDER_ERROR',502)
    if tool=='google_search' and not queries:raise Fault('RESEARCH_QUERY_COUNT_UNAVAILABLE',502)
    if tool=='google_search' and not suggestions:raise Fault('RESEARCH_ATTRIBUTION_UNAVAILABLE',502)
    u=data.get('usage',{}) or {}
    from .provider_contract import ProviderOutput
    payload=ProviderOutput(provider_answer=answer,provider_citations=citations,provider_sources=ranking.rank(list(sources.values())),provider_display_artifact=GoogleDisplayArtifact(search_suggestions_html=suggestions,presentation=presentation) if suggestions else None,provider_usage=Usage(model_calls=1,search_queries=len(queries) if queries else (0 if tool=='url_context' else None),url_context_urls=url_count,**read_token_usage(u),latency_ms=latency))
    result=ResearchResult(research_id=request.research_id,status='COMPLETED',answer=payload.provider_answer,sources=payload.provider_sources,citations=payload.provider_citations,completed_at=stamp,freshness_status='EVIDENCED',provider=provider,model=model,
        usage=payload.provider_usage,provider_display_artifact=payload.provider_display_artifact)
    if len(sources)>1 and re.search(r'discord|divergen|conflit|conflicting',answer,re.I):
        result=result.model_copy(update={'agreement_status':'CONFLICTING','conflicting_sources':list(sources),'uncertainty_note':'Provider text reports disagreement; independence and truth are not established.'})
    return result

def validate_google_suggestions(html,*,navigation='frame'):
    """Accept or reject whole artifact, never sanitize or reconstruct it.

    Navigation must already escape the isolated iframe, without changing targets.
    Reject active/external-resource HTML; sandbox remains mandatory defense in depth.
    """
    from html.parser import HTMLParser
    class Validate(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=False);self.links=0
        def handle_starttag(self,tag,attrs):
            if tag not in ('style','div','span','a','svg','path','g','circle','rect','p','br'):raise Fault('RESEARCH_ATTRIBUTION_UNSAFE',502)
            a=dict(attrs)
            if any(k.startswith('on') for k in a) or any(k in a for k in ('src','srcdoc','formaction')):raise Fault('RESEARCH_ATTRIBUTION_UNSAFE',502)
            if tag=='a':
                target=a.get('target','').lower()
                if target not in ('','_self','_parent','_top','_blank') or navigation=='frame' and target!='_blank':raise Fault('RESEARCH_ATTRIBUTION_NAVIGATION_UNSUPPORTED',502)
                URLPolicy().check(a.get('href',''));self.links+=1
        def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
    if not isinstance(html,str) or len(html.encode('utf-8'))>20000:raise Fault('RESEARCH_ATTRIBUTION_UNAVAILABLE',502)
    if re.search(r'@import|url\s*\(|expression\s*\(',html,re.I):raise Fault('RESEARCH_ATTRIBUTION_UNSAFE',502)
    parser=Validate();parser.feed(html);parser.close()
    if not parser.links:raise Fault('RESEARCH_ATTRIBUTION_UNAVAILABLE',502)
    return html

class MockWebResearchProvider:
    name='synthetic';cache_allowed=True
    def __init__(self):self.calls=0
    def capabilities(self):return {'search':True,'inspect_urls':True,'cache':True}
    def health(self):return {'configured':True,'synthetic':True}
    def usage(self):return {'model_calls':self.calls,'incremental_cost_usd':0}
    def search(self,request):
        self.calls+=1;stamp=int(time.time());source=SourceRankingPolicy().normalize('https://react.dev/','React',stamp,self.name)
        return ResearchResult(research_id=request.research_id,status='COMPLETED',answer='Synthetic public evidence.',sources=[source],citations=[Citation(citation_id='synthetic',source_id=source.source_id,start_index=0,end_index=26)],freshness_status='EVIDENCED',provider=self.name,model='synthetic',usage=Usage(model_calls=1,search_queries=1),completed_at=stamp)
    def inspect_urls(self,request):return self.search(request)
