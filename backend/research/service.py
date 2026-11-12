import hashlib,json,time
from pydantic import ValidationError
from backend.app.errors import Fault
from backend.app.models import ident
from backend.device_protocol import SignedDeviceRequest
from .contracts import *
from .policy import *
TERMINAL=('COMPLETED','FAILED','CANCELLED')
class ResearchService:
    def __init__(self,control,devices):
        from .transient import TransientDisplay
        self.control=control;self.devices=devices;self.store=control.store;self.policy=ResearchUsagePolicy();self.display=TransientDisplay();self.windows=TransientDisplay()
    def now(self):return self.devices.seconds()
    def event(self,r,kind,row=None,result='OK'):
        self.control.event(r,None,row.get('project_id') if row else None,kind,result,row['research_id'] if row else 'research')
    def owner(self,r,owner,project,recent=False):
        p=self.devices.owner(r,owner,recent)
        self.control._check(r,p,project,'knowledge','knowledge.read');return p
    def device(self,r,did):
        d=r.get('device_identities',did)
        if not d:raise Fault('DEVICE_UNKNOWN',404)
        if d['status']=='REVOKED':raise Fault('DEVICE_REVOKED',403)
        if d['status']!='ACTIVE':raise Fault('DEVICE_NOT_ACTIVE',403)
        self.devices.binding(r,d);return d
    def grant(self,owner,did,enabled):
        with self.store.transaction() as r:
            d=self.device(r,did);self.owner(r,owner,d['project_id'],True)
            key=did;row=r.get('research_devices',key)
            values={'device_id':did,'project_id':d['project_id'],'principal_id':owner.internal_owner_id,'enabled':enabled,'reported':False,'last_seen':0}
            (r.put if row else r.add)('research_devices',key,values)
            self.event(r,'RESEARCH_DEVICE_POLICY_CHANGED')
            return {'device_id':did,'web_research_approved':enabled}
    def available_devices(self,owner):
        with self.store.read() as r:
            self.devices.owner(r,owner)
            return [{**self.devices.public(d),'web_research_approved':bool((r.get('research_devices',d['device_id']) or {}).get('enabled'))} for d in r.rows('device_identities',principal_id=owner.internal_owner_id,limit=100)]
    def online(self,r,d):
        g=r.get('research_devices',d['device_id'])
        if not g or not g['enabled']:raise Fault('DEVICE_CAPABILITY_MISMATCH',403)
        return self.devices.public(d)['online'] and g['reported'] and 0<=self.now()-g['last_seen']<=45
    def create(self,owner,data):
        self.control.safe(data);body=ResearchCreate.model_validate(data);route=KnowledgeRouter().route(body.query,body.allow_web,body.mode)
        if route.route=='PRIVATE_LIBRARY_FUTURE' and getattr(self.control.settings,'library_enabled',False):raise Fault('PRIVATE_LIBRARY_USE_KNOWLEDGE',409)
        egress=ExternalQueryPolicy();query=egress.check(body.query)
        if body.public_query:egress.check(body.public_query)
        for u in body.urls:URLPolicy().check(u)
        if route.route=='HYBRID_WEB_PROJECT' and not body.public_query:raise Fault('PUBLIC_QUERY_REQUIRED',400)
        digest=hashlib.sha256(json.dumps(body.model_dump(),sort_keys=True).encode()).hexdigest()
        key=hashlib.sha256((owner.internal_owner_id+':'+body.project_id+':'+body.idempotency_key).encode()).hexdigest()
        with self.store.transaction() as r:
            self.owner(r,owner,body.project_id)
            existing=r.get('research_requests',key)
            if existing:
                if existing['digest']!=digest:raise Fault('IDEMPOTENCY_CONFLICT',409)
                return self.view(existing)
            d=self.device(r,body.target_device_id)
            if d['principal_id']!=owner.internal_owner_id or d['project_id']!=body.project_id:raise Fault('FORBIDDEN',403)
            online=self.online(r,d)
            self.devices.rate(r,'research-owner-'+owner.internal_owner_id,6)
            day='research-day-'+owner.internal_owner_id+'-'+str(self.now()//86400)
            count=r.get('research_limits',day) or {'count':0}
            if count['count']>=30:raise Fault('RESEARCH_BUDGET_EXCEEDED',429)
            (r.put if r.get('research_limits',day) else r.add)('research_limits',day,{'count':count['count']+1})
            req=ResearchRequest(research_id=key[:32],project_id=body.project_id,query=query,public_query=body.public_query,urls=body.urls,route=route,target_device_id=d['device_id'],requested_at=self.now(),expires_at=self.now()+240,max_sources={'QUICK':3,'STANDARD':6,'DEEP':8}[body.depth],max_depth=body.depth)
            row=dict(research_id=req.research_id,key=key,principal_id=owner.internal_owner_id,project_id=body.project_id,digest=digest,request=req.model_dump(),status='ANALYZING' if online else 'WAITING_FOR_DEVICE',lease_id=None,lease_until=0,result=None,attempts=0)
            r.add('research_requests',key,row);self.event(r,'RESEARCH_REQUESTED',row);self.event(r,'RESEARCH_ROUTED',row)
            return self.view(row)
    def owned(self,r,owner,rid):
        row=self.find(r,rid)
        if not row or row['principal_id']!=owner.internal_owner_id:raise Fault('NOT_FOUND',404)
        self.owner(r,owner,row['project_id']);return row
    def find(self,r,rid):
        from sqlalchemy import select
        from .schema import TABLES
        t=TABLES['research_requests'];items=r.connection.execute(select(t.c.data).where(t.c.id.like(rid+'%')).limit(2)).scalars().all()
        return dict(items[0]) if len(items)==1 and items[0]['research_id']==rid else None
    def expire(self,r,row):
        if row['status'] not in TERMINAL and (row['request']['expires_at']<=self.now() or row['lease_id'] and row['lease_until']<=self.now()):
            row.update(status='FAILED',error_code='RESEARCH_TIMEOUT');r.put('research_requests',row['key'],row);self.event(r,'RESEARCH_FAILED',row,'RESEARCH_TIMEOUT')
        return row
    def view(self,row):return {k:row.get(k) for k in ('research_id','project_id','status','result','error_code')}|{'route':row['request']['route'],'requested_at':row['request']['requested_at']}
    def get(self,owner,rid,cancel=False,live=True):
        with self.store.transaction() as r:
            row=self.expire(r,self.owned(r,owner,rid))
            if cancel and row['status'] not in TERMINAL:
                row['status']='CANCELLED';r.put('research_requests',row['key'],row);self.event(r,'RESEARCH_CANCELLED',row)
            view=self.view(row)
            if row.get('google_ephemeral'):
                view['result']=self.display.consume(rid,owner.internal_owner_id) if live else None
                view['display_status']='LIVE' if view['result'] else 'GROUNDED_RESULT_NOT_RETAINED'
                if view['result'] and (view['result'].get('provider_display_artifact') or {}).get('presentation')=='ISOLATED_WINDOW':
                    import secrets
                    ticket=secrets.token_urlsafe(32)
                    value=view['result'];view['project_context']={'answer':value.get('project_answer',''),'evidence':value.get('project_evidence',[])}
                    self.windows.put(ticket,'DISPLAY_ONLY',{**value,'project_answer':'','project_evidence':[]})
                    view.update(result=None,display_status='LIVE_WINDOW_READY',display_path='/research-display/'+ticket,display_expires_at=self.now()+30)
                view['usage_metadata']=row.get('usage_metadata')
            return view
    def open_display(self,ticket):
        import re
        from .contracts import ResearchResult
        from .display import render_google_display
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',ticket):raise Fault('GROUNDED_RESULT_NOT_RETAINED',410)
        value=self.windows.consume(ticket,'DISPLAY_ONLY')
        if value is None:raise Fault('GROUNDED_RESULT_NOT_RETAINED',410)
        return render_google_display(ResearchResult.model_validate(value))
    def handle(self,path,data):
        error=None;response=None;transient=None
        with self.store.transaction() as r:
            try:
                self.devices.rate(r,'research-signed-global',600)
                body=SignedDeviceRequest.model_validate(data)
                principal,d=self.devices.auth.authenticate(r,path,body)
                if r.get('system_state','global')['state']!='RUNNING':raise Fault('RESEARCH_KILL_SWITCH',403)
                op=path.rsplit('/',1)[-1];g=r.get('research_devices',d['device_id'])
                if not g or not g['enabled']:raise Fault('DEVICE_CAPABILITY_MISMATCH',403)
                if op=='heartbeat':
                    ResearchHeartbeat.model_validate(body.payload);g.update(reported=True,last_seen=self.now());r.put('research_devices',d['device_id'],g);response={'status':'ACCEPTED'}
                elif op=='poll':
                    ResearchPoll.model_validate(body.payload);response=self.poll(r,d)
                elif op in ('check','progress','result'):
                    parsed=(ResearchDelivery if op=='result' else ResearchProgress if op=='progress' else ResearchLease).model_validate(body.payload)
                    row=self.find(r,parsed.research_id)
                    if not row or row['request']['target_device_id']!=d['device_id'] or row['project_id']!=d['project_id']:raise Fault('RESEARCH_SCOPE',403)
                    self.expire(r,row)
                    if row['status'] in TERMINAL or row['lease_id']!=parsed.lease_id or row['lease_until']<=self.now():raise Fault('RESEARCH_LEASE_INVALID',409)
                    p=self.control._principal(r,row['principal_id']);self.control._check(r,p,row['project_id'],'knowledge','knowledge.read')
                    if not self.online(r,d):raise Fault('DEVICE_OFFLINE',409)
                    if op=='result':
                        result=parsed.result
                        if result.research_id!=row['research_id']:raise Fault('RESEARCH_SCOPE',403)
                        self.validate_result(row,result)
                        if result.provider=='gemini_google_search':
                            row.update(status=result.status,result=None,error_code=result.error_code,google_ephemeral=True,
                                usage_metadata={'provider':result.provider,'model':result.model,'completed_at':result.completed_at,'usage':result.usage.model_dump()})
                            if result.status=='COMPLETED':transient=(row['research_id'],row['principal_id'],result.model_dump())
                        else:row.update(status=result.status,result=result.model_dump(),error_code=result.error_code)
                        self.event(r,'RESEARCH_'+result.status,row,result.error_code or 'OK')
                    elif op=='progress':row['status']=parsed.stage
                    r.put('research_requests',row['key'],row);response={'status':row['status']}
                else:raise Fault('RESEARCH_OPERATION_INVALID',400)
                response.update(request_nonce=body.nonce,device_id=d['device_id'])
            except (Fault,ValidationError) as exc:
                error=exc if isinstance(exc,Fault) else Fault('RESEARCH_REQUEST_INVALID',400)
                if error.code!='DEVICE_RATE_LIMITED':self.event(r,'RESEARCH_REJECTED',result=error.code)
        if error:raise error
        if transient:self.display.put(*transient)
        return response
    def poll(self,r,d):
        if not self.online(r,d):return {'request':None,'status':'WAITING_FOR_DEVICE'}
        for row in r.rows('research_requests',principal_id=d['principal_id'],limit=100):
            if row['request']['target_device_id']!=d['device_id'] or row['project_id']!=d['project_id']:continue
            self.expire(r,row)
            if row['status'] in TERMINAL or row['lease_id']:continue
            p=self.control._principal(r,row['principal_id']);self.control._check(r,p,row['project_id'],'knowledge','knowledge.read')
            row.update(lease_id=ident(),lease_until=self.now()+90,attempts=row['attempts']+1,status='ANALYZING')
            r.put('research_requests',row['key'],row);self.event(r,'RESEARCH_STARTED',row)
            return {'request':row['request'],'lease_id':row['lease_id']}
        return {'request':None}
    def validate_result(self,row,result):
        req=ResearchRequest.model_validate(row['request'])
        if result.status=='COMPLETED':
            if req.route.route in ('WEB_FIRST','WEB_REQUIRED','HYBRID_WEB_PROJECT') and (not result.sources or not result.citations or result.freshness_status!='EVIDENCED'):raise Fault('RESEARCH_EVIDENCE_INSUFFICIENT',400)
            if req.route.route in ('PROJECT_FIRST','HYBRID_WEB_PROJECT') and not result.project_evidence:raise Fault('PROJECT_KNOWLEDGE_UNAVAILABLE',400)
            if req.route.route=='PROJECT_FIRST' and (result.answer or result.sources):raise Fault('PROJECT_SOVEREIGNTY_VIOLATION',400)
        for source in result.sources:
            if source.origin!='WEB':raise Fault('INVALID_SOURCE_ORIGIN',400)
            expected=SourceRankingPolicy().normalize(source.url,source.title,source.retrieved_at,source.provider)
            if (source.canonical_url,source.source_id,source.source_type,source.quality_tier,source.publisher)!=(expected.canonical_url,expected.source_id,expected.source_type,expected.quality_tier,expected.publisher):raise Fault('INVALID_SOURCE_METADATA',400)
        if len(result.sources)>req.max_sources:raise Fault('RESEARCH_BUDGET_EXCEEDED',400)
        if result.provider_display_artifact:
            from .provider import validate_google_suggestions
            for html in result.provider_display_artifact.search_suggestions_html:validate_google_suggestions(html,navigation='window' if result.provider_display_artifact.presentation=='ISOLATED_WINDOW' else 'frame')
        if result.status=='COMPLETED' and result.provider=='gemini_google_search' and result.usage.search_queries and not result.provider_display_artifact:raise Fault('RESEARCH_ATTRIBUTION_UNAVAILABLE',400)
        for item in result.search_suggestions:
            if set(item)!={'url','title'} or len(item['title'])>300:raise Fault('INVALID_ATTRIBUTION',400)
            URLPolicy().check(item['url'])
