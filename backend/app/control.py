"""Durable local control plane; all mutations include their audit in one transaction."""
import hashlib
import json
import re
from datetime import datetime,timedelta
from .database import Store
from .models import Principal,Project,now,ident
from .registry import TOOLS,AGENTS
from .policy import Policy
from .errors import Fault

ADMIN_CAPS=tuple('admin.'+x for x in ('status.read','state.manage','state.unlock','projects.read','projects.manage',
    'tools.read','tools.manage','agents.read','approvals.read','approvals.manage','actions.read','actions.manage',
    'revocations.read','revocations.manage','audit.read','sessions.read','sessions.manage','learning.read','learning.manage'))
READ_CAPS={'state':'admin.status.read','projects':'admin.projects.read','tools':'admin.tools.read','agents':'admin.agents.read',
    'actions':'admin.actions.read','approvals':'admin.approvals.read','approval_requests':'admin.approvals.read',
    'revocations':'admin.revocations.read','audit_events':'admin.audit.read','sessions':'admin.sessions.read','learning':'admin.learning.read'}
MUTATE_CAPS={'state':'admin.state.manage','project':'admin.projects.manage','tool':'admin.tools.manage',
    'revoke':'admin.revocations.manage','action':'admin.actions.manage','transition':'admin.actions.manage',
    'decision':'admin.approvals.manage','consume':'admin.approvals.manage','session':'admin.sessions.manage',
    'close_session':'admin.sessions.manage','learning':'admin.learning.manage','learning_status':'admin.learning.manage'}


def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def stamp(): return now().isoformat()
def date(value):
    try:
        d=datetime.fromisoformat(value)
        if d.tzinfo is None: raise ValueError()
        return d
    except (ValueError,TypeError): raise Fault('INVALID_EXPIRATION') from None

def action_scope(action):
    return digest({k:action[k] for k in ('action_id','principal_id','project_id','tool_id','capability','intent','parameters','risk_level','approval_requirement','created_at') } | {k:action[k] for k in ('origin_type','origin_id','session_id','correlation_id','human_principal_id') if k in action})


class Control:
    def __init__(self,settings):
        self.settings=settings
        self.store=Store(settings.database_url)
        self.bootstrap()

    def close(self): self.store.close()

    def safe(self,payload,max_chars=16384):
        raw=json.dumps(payload,ensure_ascii=False)
        if len(raw)>max_chars: raise Fault('PAYLOAD_TOO_LARGE',413)
        secrets=(self.settings.token,self.settings.knowledge_token,self.settings.admin_confirmation_token)
        if any(secret and secret in raw for secret in secrets): raise Fault('SENSITIVE_PAYLOAD')
        if re.search(r'-----BEGIN .*PRIVATE KEY|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[0-9A-Za-z]{25,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}',raw):
            raise Fault('SENSITIVE_PAYLOAD')
        def walk(x):
            if isinstance(x,dict):
                for key,value in x.items():
                    if re.search(r'token|secret|password|authorization|api.?key|cookie',key,re.I): raise Fault('SENSITIVE_PAYLOAD')
                    walk(value)
            elif isinstance(x,list):
                for value in x: walk(value)
        walk(payload)

    def event(self,repo,principal_id,project_id,event_type,result,correlation_id,tool_id=None,action_id=None):
        event=dict(event_id=ident(),timestamp=stamp(),principal_id=principal_id,project_id=project_id,event_type=event_type,
            tool_id=tool_id,action_id=action_id,result=result,correlation_id=correlation_id)
        repo.add('audit_events',event['event_id'],event)

    def bootstrap(self):
        with self.store.transaction() as repo:
            if repo.get('system_state','global'):
                if not repo.get('principals',self.settings.principal.principal_id) or not repo.get('projects','meu-gestor'):
                    raise Fault('BOOTSTRAP_INCOMPLETE',503)
                return
            if any(repo.rows(t) for t in ('principals','projects','tools','agents','actions','audit_events','approvals','sessions','learning','revocations','idempotency','approval_requests')):
                raise Fault('BOOTSTRAP_NOT_EMPTY',503)
            owner=self.settings.principal.model_dump(mode='json')
            owner.update(status='ACTIVE',created_at=stamp(),updated_at=stamp())
            owner['capabilities']=list(dict.fromkeys(owner['capabilities']+list(ADMIN_CAPS)))
            repo.add('principals',owner['principal_id'],owner)
            project=Project(project_id='meu-gestor',name='Meu Gestor',knowledge_endpoint=self.settings.knowledge_endpoint,
                metadata={'knowledge_api_version':'0.1.0','brain_version':'0.6.0','engine_version':'1.4.0'}).model_dump(mode='json')
            project.update(created_at=stamp(),updated_at=stamp())
            repo.add('projects','meu-gestor',project)
            for key,tool in TOOLS.items(): repo.add('tools',key,tool.model_dump(mode='json'))
            for agent in AGENTS: repo.add('agents',agent['agent_id'],agent)
            repo.add('system_state','global',dict(state='RUNNING',history=self.settings.history,packages=list(self.settings.packages)))
            self.event(repo,owner['principal_id'],None,'BOOTSTRAP','CREATED',ident())

    def _principal(self,repo,principal_id):
        row=repo.get('principals',principal_id)
        if not row or row['status']!='ACTIVE': raise Fault('PRINCIPAL_INACTIVE',403)
        return Principal(principal_id=row['principal_id'],principal_type=row['principal_type'],display_name=row['display_name'],
            roles=tuple(row['roles']),project_scopes=tuple(row['project_scopes']),capabilities=tuple(row['capabilities']),approval_level=row['approval_level'])

    def principal(self):
        with self.store.read() as repo: return self._principal(repo,self.settings.principal.principal_id)

    def _revoked(self,repo,p,capability,project_id=None,tool_id=None):
        for rev in repo.rows('revocations'):
            if rev.get('expires_at') and date(rev['expires_at'])<=now(): continue
            if (rev['capability']==capability and rev.get('principal_id') in (None,p.principal_id) and
                rev.get('project_id') in (None,project_id) and rev.get('tool_id') in (None,tool_id)):
                return True
        return False

    def _admin(self,repo,p,capability,project_id=None):
        actual=self._principal(repo,p.principal_id)
        if capability not in actual.capabilities or self._revoked(repo,actual,capability,project_id) or (project_id is None and any(self._revoked(repo,actual,capability,scope) for scope in actual.project_scopes)): raise Fault('ADMIN_CAPABILITY_DENIED',403)
        if project_id and project_id not in actual.project_scopes: raise Fault('FORBIDDEN_SCOPE',403)
        return actual

    def _project(self,repo,project_id,p):
        row=repo.get('projects',project_id)
        if not row: raise Fault('UNKNOWN_PROJECT',404)
        if project_id not in p.project_scopes: raise Fault('FORBIDDEN_SCOPE',403)
        if row['status']!='ACTIVE' or not row['enabled']: raise Fault('PROJECT_SUSPENDED',403)
        fields={k:row[k] for k in Project.model_fields}
        fields['capabilities']=tuple(fields['capabilities'])
        return Project(**fields)

    def resolve(self,project_id,p):
        with self.store.read() as repo: return self._project(repo,project_id,self._principal(repo,p.principal_id))

    @property
    def items(self):
        with self.store.read() as repo:
            return {r['project_id']:Project(**{**{k:r[k] for k in Project.model_fields},'capabilities':tuple(r['capabilities'])}) for r in repo.rows('projects')}

    @property
    def state(self):
        with self.store.read() as repo: return repo.get('system_state','global')['state']

    def knowledge_options(self):
        with self.store.read() as repo:
            row=repo.get('system_state','global');return row['history'],tuple(row['packages'])

    def _check(self,repo,p,project_id,tool_id,capability):
        actual=self._principal(repo,p.principal_id)
        project=self._project(repo,project_id,actual)
        if capability not in actual.capabilities or capability not in project.capabilities or self._revoked(repo,actual,capability,project_id,tool_id):
            raise Fault('CAPABILITY_DENIED',403)
        tool=repo.get('tools',tool_id)
        if not tool or not tool['enabled'] or capability not in tool['capabilities']: raise Fault('TOOL_DISABLED',403)
        if tool_id!='knowledge' or capability!='knowledge.read': raise Fault('EXTERNAL_EXECUTION_DISABLED',403)
        state=repo.get('system_state','global')['state']
        if state!='RUNNING': raise Fault('LUMA_'+state,403)

    def check(self,p,project,tool_id,capability):
        with self.store.read() as repo: self._check(repo,p,project.project_id,tool_id,capability)

    def _owned(self,repo,table,key,p):
        row=repo.get(table,key)
        if not row: raise Fault('NOT_FOUND',404)
        if row.get('principal_id') not in (None,p.principal_id) or row.get('project_id') not in (None,*p.project_scopes):
            raise Fault('OBJECT_SCOPE',403)
        return row

    def listing(self,p,kind,limit=100,offset=0,key=None):
        if kind not in READ_CAPS: raise Fault('NOT_FOUND',404)
        with self.store.read() as repo:
            p=self._admin(repo,p,READ_CAPS[kind])
            if kind=='state': return repo.get('system_state','global')
            if key: return self._owned(repo,kind,key,p)
            return repo.rows(kind,principal_id=p.principal_id,projects=p.project_scopes,limit=limit,offset=offset)

    def mutate(self,p,operation,payload,key,correlation_id,target=None,confirmed=False):
        if operation not in MUTATE_CAPS: raise Fault('NOT_FOUND',404)
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key or ''): raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        self.safe(payload)
        fingerprint=digest({'operation':operation,'target':target,'payload':payload})
        record_id=digest({'principal':p.principal_id,'key':key})
        with self.store.transaction() as repo:
            p=self._admin(repo,p,MUTATE_CAPS[operation],payload.get('project_id'))
            if operation in ('decision','consume') and not confirmed: raise Fault('HUMAN_CONFIRMATION_REQUIRED',403)
            if operation=='state' and payload.get('confirmation')=='UNLOCK_LUMA':
                self._admin(repo,p,'admin.state.unlock')
                if not confirmed: raise Fault('UNLOCK_CONFIRMATION_REQUIRED',403)
            previous=repo.get('idempotency',record_id)
            if previous:
                if previous['fingerprint']!=fingerprint: raise Fault('IDEMPOTENCY_CONFLICT',409)
                return previous['response']
            response=self._apply(repo,p,operation,payload,target,confirmed,correlation_id)
            repo.add('idempotency',record_id,{'principal_id':p.principal_id,'fingerprint':fingerprint,'response':response})
            return response

    def _apply(self,repo,p,op,data,target,confirmed,correlation):
        result=None;project_id=data.get('project_id');tool_id=data.get('tool_id');action_id=None
        if op=='state':
            result=repo.get('system_state','global');old=result['state']
            if old=='LOCKED' and data['state']!='LOCKED':
                self._admin(repo,p,'admin.state.unlock')
                if data.get('confirmation')!='UNLOCK_LUMA' or not confirmed: raise Fault('UNLOCK_CONFIRMATION_REQUIRED',403)
            result['state']=data['state'];repo.put('system_state','global',result)
        elif op=='project':
            result=repo.get('projects',target)
            if not result: raise Fault('NOT_FOUND',404)
            self._admin(repo,p,'admin.projects.manage',target)
            result.update({k:v for k,v in data.items() if v is not None});result['updated_at']=stamp()
            repo.put('projects',target,result);project_id=target
        elif op=='tool':
            result=repo.get('tools',target)
            if not result: raise Fault('NOT_FOUND',404)
            if data['enabled'] and target!='knowledge': raise Fault('EXTERNAL_TOOL_DISABLED',403)
            result['enabled']=data['enabled'];repo.put('tools',target,result);tool_id=target
        elif op=='revoke':
            self._project(repo,project_id,p)
            valid_caps=set(p.capabilities)|{c for t in TOOLS.values() for c in t.capabilities}
            if data['capability'] not in valid_caps: raise Fault('UNKNOWN_CAPABILITY')
            if tool_id and (tool_id not in TOOLS or data['capability'] not in TOOLS[tool_id].capabilities): raise Fault('UNKNOWN_CAPABILITY')
            if data.get('expires_at') and date(data['expires_at'])<=now(): raise Fault('INVALID_EXPIRATION')
            result={**data,'revocation_id':ident(),'principal_id':p.principal_id,'revoked_by':p.principal_id,'created_at':stamp()}
            repo.add('revocations',result['revocation_id'],result)
        elif op=='action':
            self._project(repo,project_id,p)
            tool=repo.get('tools',tool_id)
            if not tool or data['capability'] not in tool['capabilities']: raise Fault('UNKNOWN_CAPABILITY')
            requirement=Policy.requirement(data['capability'],False,bool(data['parameters'].get('participants')))
            result={**data,'action_id':ident(),'principal_id':p.principal_id,'risk_level':'LOW' if data['capability']=='knowledge.read' else 'HIGH',
                'approval_requirement':requirement,'status':'WAITING_APPROVAL' if requirement=='CONFIRM' else 'PROPOSED','created_at':stamp()}
            result['scope']=action_scope(result);action_id=result['action_id']
            repo.add('actions',action_id,result)
            if requirement=='CONFIRM': repo.add('approval_requests',action_id,{'action_id':action_id,'principal_id':p.principal_id,'project_id':project_id,'status':'PENDING','scope':result['scope']})
        elif op in ('decision','transition'):
            action=self._owned(repo,'actions',target,p);action_id=target;project_id=action['project_id'];tool_id=action['tool_id']
            self._admin(repo,p,MUTATE_CAPS[op],project_id)
            if op=='transition':
                if data['status']!='CANCELLED' or action['status'] not in ('PROPOSED','WAITING_APPROVAL','APPROVED'): raise Fault('INVALID_TRANSITION',409)
                action['status']='CANCELLED';result=action
            else:
                if action['status'] not in ('PROPOSED','WAITING_APPROVAL'): raise Fault('ALREADY_DECIDED',409)
                if action_scope(action)!=data['scope'] or data['scope']!=action['scope']: raise Fault('APPROVAL_SCOPE_MISMATCH',403)
                if action['approval_requirement']=='DENY' and data['decision']=='APPROVE': raise Fault('ACTION_DENIED',403)
                result=dict(approval_id=ident(),action_id=target,principal_id=p.principal_id,project_id=project_id,
                    decision=data['decision'],scope=data['scope'],created_at=stamp(),expires_at=(now()+timedelta(minutes=5)).isoformat(),consumed_at=None,reason=data.get('reason'))
                repo.add('approvals',result['approval_id'],result)
                action['status']='APPROVED' if data['decision']=='APPROVE' else 'DENIED'
            repo.put('actions',target,action)
            pending=repo.get('approval_requests',target)
            if pending: pending['status']=action['status'];repo.put('approval_requests',target,pending)
        elif op=='consume':
            approval=self._owned(repo,'approvals',target,p)
            action=self._owned(repo,'actions',approval['action_id'],p)
            action_id=action['action_id'];project_id=action['project_id'];tool_id=action['tool_id']
            self._admin(repo,p,'admin.approvals.manage',project_id)
            if (approval['decision']!='APPROVE' or approval['consumed_at'] or date(approval['expires_at'])<=now() or
                action['status']!='APPROVED' or action_scope(action)!=approval['scope']): raise Fault('APPROVAL_INVALID',409)
            if repo.get('system_state','global')['state']!='RUNNING': raise Fault('CONTROL_BLOCKED',403)
            self._project(repo,project_id,p)
            if self._revoked(repo,p,action['capability'],project_id,tool_id): raise Fault('CAPABILITY_DENIED',403)
            # Validation-only consumption: atomically retire action, never execute a tool.
            approval['consumed_at']=stamp();action['status']='CANCELLED'
            repo.put('approvals',target,approval);repo.put('actions',action_id,action)
            pending=repo.get('approval_requests',action_id)
            if pending: pending['status']='CANCELLED';repo.put('approval_requests',action_id,pending)
            result={**approval,'action_status':'CANCELLED','execution_performed':False}
        elif op=='session':
            self._project(repo,project_id,p)
            result=dict(session_id=ident(),principal_id=p.principal_id,active_project_id=project_id,project_id=project_id,
                created_at=stamp(),last_activity=stamp(),expires_at=(now()+timedelta(hours=24)).isoformat(),status='ACTIVE')
            repo.add('sessions',result['session_id'],result)
        elif op=='close_session':
            result=self._owned(repo,'sessions',target,p);project_id=result['project_id']
            if result['status']!='ACTIVE': raise Fault('INVALID_TRANSITION',409)
            result.update(status='CLOSED',last_activity=stamp());repo.put('sessions',target,result)
        elif op=='learning':
            self._project(repo,project_id,p)
            if any(not e.strip() or len(e)>1000 for e in data['evidence']): raise Fault('INVALID_EVIDENCE')
            result={**data,'candidate_id':ident(),'principal_id':p.principal_id,'status':'PROPOSED','created_at':stamp()}
            repo.add('learning',result['candidate_id'],result)
        elif op=='learning_status':
            result=self._owned(repo,'learning',target,p);project_id=result['project_id']
            if data['status'] not in ('VALIDATED','REJECTED') or result['status']!='PROPOSED': raise Fault('WRITE_BACK_DISABLED',403)
            result['status']=data['status'];repo.put('learning',target,result)
        else: raise Fault('UNKNOWN_OPERATION')
        self.event(repo,p.principal_id,project_id,'ADMIN_'+op.upper(),'COMMITTED',correlation,tool_id,action_id)
        return result

    def http_event(self,p,project,event_type,result,correlation):
        with self.store.transaction() as repo:
            self.event(repo,p.principal_id if p else None,project,event_type,result,correlation)

    def session(self,p,key):
        with self.store.read() as repo:
            p=self._principal(repo,p.principal_id);row=self._owned(repo,'sessions',key,p)
            self._project(repo,row['project_id'],p)
            if row['status']!='ACTIVE' or date(row['expires_at'])<=now(): raise Fault('SESSION_EXPIRED',403)
            return row
