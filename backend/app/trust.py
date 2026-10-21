"""Owner control plane and least-privilege runtime. No executor exists here."""
from .control import Control as LegacyControl,ADMIN_CAPS,stamp,date,digest,action_scope
from .trust_data import RUNTIME_CAPS,NEW_ADMIN_CAPS,seed,grant,append,verify
from .models import Principal,now,ident
from .errors import Fault
from .registry import TOOLS

class Control(LegacyControl):
    def bootstrap(self):
        with self.store.read() as repo: existing=bool(repo.get('system_state','global'))
        super().bootstrap()
        with self.store.transaction() as repo:
            if not existing: seed(repo)
            if not repo.get('principals','luma-runtime'): raise Fault('BOOTSTRAP_INCOMPLETE',503)
            verify(repo)

    def event(self,repo,principal_id,project_id,event_type,result,correlation_id,tool_id=None,action_id=None):
        append(repo,dict(event_id=ident(),timestamp=stamp(),principal_id=principal_id,project_id=project_id,
            event_type=event_type,tool_id=tool_id,action_id=action_id,result=result,correlation_id=correlation_id))

    def safe(self,payload,max_chars=16384):
        super().safe(payload,max_chars)
        if self.settings.runtime_token and self.settings.runtime_token in str(payload): raise Fault('SENSITIVE_PAYLOAD')

    def _principal(self,repo,principal_id):
        p=super()._principal(repo,principal_id)
        # JSON capabilities are historical metadata only. Grants are authoritative.
        caps=tuple(sorted({g['capability'] for g in repo.rows('grants') if g['principal_id']==principal_id
            and g['status']=='ACTIVE' and (not g['expires_at'] or date(g['expires_at'])>now())}))
        return p.model_copy(update={'capabilities':caps})

    def principal(self,principal_id=None):
        with self.store.read() as repo: return self._principal(repo,principal_id or self.settings.principal.principal_id)

    def granted(self,repo,p,cap,project=None,tool=None):
        if self._revoked(repo,p,cap,project,tool): return False
        return any(g['principal_id']==p.principal_id and g['capability']==cap and g['status']=='ACTIVE'
            and g['project_id'] in (None,project) and g['tool_id'] in (None,tool)
            and (not g['expires_at'] or date(g['expires_at'])>now()) for g in repo.rows('grants'))

    def _admin(self,repo,p,capability,project_id=None):
        actual=self._principal(repo,p.principal_id)
        if actual.principal_type!='HUMAN_OWNER' or not self.granted(repo,actual,capability,project_id):
            raise Fault('ADMIN_CAPABILITY_DENIED',403)
        return super()._admin(repo,actual,capability,project_id)

    def _check(self,repo,p,project_id,tool_id,capability):
        p=self._principal(repo,p.principal_id)
        state=repo.get('system_state','global')['state']
        if state!='RUNNING': raise Fault('LUMA_'+state,403)
        if self._revoked(repo,p,capability,project_id,tool_id): raise Fault('CAPABILITY_DENIED',403)
        tool=repo.get('tools',tool_id)
        if not tool or not tool['enabled'] or capability not in tool['capabilities']: raise Fault('TOOL_DISABLED',403)
        project=self._project(repo,project_id,p)
        if capability not in project.capabilities or not self.granted(repo,p,capability,project_id,tool_id): raise Fault('CAPABILITY_DENIED',403)
        if tool_id!='knowledge' or capability!='knowledge.read': raise Fault('EXTERNAL_EXECUTION_DISABLED',403)

    def _owned(self,repo,table,key,p):
        row=repo.get(table,key)
        if row and row.get('human_principal_id')==p.principal_id and row.get('project_id') in p.project_scopes:
            return row
        return super()._owned(repo,table,key,p)

    def listing(self,p,kind,limit=100,offset=0,key=None):
        if kind in ('grants','retention_policies','audit_verify','retention_preview'):
            cap='admin.grants.read' if kind=='grants' else 'admin.audit.read' if kind=='audit_verify' else 'admin.retention.read'
            with self.store.read() as repo:
                p=self._admin(repo,p,cap)
                if kind=='audit_verify': return {'verified':True,**verify(repo)}
                if kind=='retention_preview':
                    result=[]
                    for row in repo.rows('retention_policies'):
                        table={'learning_candidates':'learning','audit':'audit_events'}.get(row['category'],row['category'])
                        rows=repo.rows(table,projects=p.project_scopes)
                        expired=sum(bool(x.get('expires_at') and date(x['expires_at'])<=now()) for x in rows)
                        result.append({**row,'records':len(rows),'expired_records':expired,'eligible_for_deletion':0})
                    return result
                return repo.rows(kind,projects=p.project_scopes,limit=limit,offset=offset)
        if kind in ('actions','approval_requests','sessions','learning'):
            from .control import READ_CAPS
            with self.store.read() as repo:
                p=self._admin(repo,p,READ_CAPS[kind])
                if key: return self._owned(repo,kind,key,p)
                rows=repo.rows(kind,projects=p.project_scopes)
                return [r for r in rows if r.get('principal_id')==p.principal_id or r.get('human_principal_id')==p.principal_id][offset:offset+limit]
        return super().listing(p,kind,limit,offset,key)

    def manage_grant(self,p,data,key,correlation,target=None,confirmed=False):
        import re
        self.safe(data)
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key or ''): raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        with self.store.transaction() as repo:
            p=self._admin(repo,p,'admin.grants.manage')
            fp=digest({'grant':data,'target':target});rid=digest({'principal':p.principal_id,'key':key})
            prior=repo.get('idempotency',rid)
            if prior:
                if prior['fingerprint']!=fp: raise Fault('IDEMPOTENCY_CONFLICT',409)
                if prior['response']['capability'].startswith('admin.') and not confirmed: raise Fault('HUMAN_CONFIRMATION_REQUIRED',403)
                return prior['response']
            if target:
                result=repo.get('grants',target)
                if not result: raise Fault('NOT_FOUND',404)
                if result['project_id'] and result['project_id'] not in p.project_scopes: raise Fault('FORBIDDEN_SCOPE',403)
                result['status']='REVOKED';repo.put('grants',target,result)
            else:
                subject=self._principal(repo,data['principal_id']);cap=data['capability'];project=data.get('project_id');tool=data.get('tool_id')
                allowed=set(ADMIN_CAPS+NEW_ADMIN_CAPS+RUNTIME_CAPS+('runtime.learning.propose',))|{c for t in TOOLS.values() for c in t.capabilities}
                if cap not in allowed: raise Fault('UNKNOWN_CAPABILITY')
                if subject.principal_id==p.principal_id: raise Fault('SELF_GRANT_DENIED',403)
                if cap.startswith('admin.'):
                    if subject.principal_type!='HUMAN_OWNER' or not confirmed: raise Fault('CRITICAL_GRANT_DENIED',403)
                if subject.principal_type!='HUMAN_OWNER' and cap not in (*RUNTIME_CAPS,'runtime.learning.propose'):
                    raise Fault('SERVICE_GRANT_DENIED',403)
                if not cap.startswith('admin.') and not project: raise Fault('PROJECT_SCOPE_REQUIRED',403)
                if project:
                    self._project(repo,project,p);self._project(repo,project,subject)
                if tool and (tool not in TOOLS or cap not in TOOLS[tool].capabilities): raise Fault('UNKNOWN_CAPABILITY')
                if data.get('expires_at') and date(data['expires_at'])<=now(): raise Fault('INVALID_EXPIRATION')
                result=grant(repo,subject.principal_id,cap,project,tool,p.principal_id,data.get('expires_at'))
            self.event(repo,p.principal_id,result['project_id'],'GRANT_REVOKED' if target else 'GRANT_CREATED','COMMITTED',correlation)
            repo.add('idempotency',rid,dict(principal_id=p.principal_id,fingerprint=fp,response=result))
            return result

    def _apply(self,repo,p,op,data,target,confirmed,correlation):
        result=super()._apply(repo,p,op,data,target,confirmed,correlation)
        if op=='session':
            runtime=self._principal(repo,'luma-runtime')
            self._project(repo,result['project_id'],runtime)
            result.update(human_principal_id=p.principal_id,runtime_principal_id=runtime.principal_id)
            repo.put('sessions',result['session_id'],result)
        elif op=='action':
            result.update(origin_type='HUMAN_DIRECT',origin_id=p.principal_id,session_id=None,correlation_id=correlation,human_principal_id=p.principal_id)
            result['scope']=action_scope(result)
            repo.put('actions',result['action_id'],result)
            pending=repo.get('approval_requests',result['action_id'])
            if pending:
                pending['scope']=result['scope'];repo.put('approval_requests',result['action_id'],pending)
        elif op=='learning_status' and result.get('origin_type')=='MODEL_PROPOSED':
            raise Fault('MODEL_LEARNING_WORKFLOW_DISABLED',403)
        return result

    def runtime_session(self,repo,p,session_id,cap):
        p=self._principal(repo,p.principal_id)
        if p.principal_type!='SERVICE_RUNTIME': raise Fault('RUNTIME_IDENTITY_REQUIRED',403)
        row=repo.get('sessions',session_id)
        if not row or row.get('runtime_principal_id')!=p.principal_id: raise Fault('SESSION_SCOPE',403)
        if row['status']!='ACTIVE' or date(row['expires_at'])<=now(): raise Fault('SESSION_EXPIRED',403)
        human=self._principal(repo,row['human_principal_id'])
        if human.principal_type!='HUMAN_OWNER': raise Fault('SESSION_SCOPE',403)
        project=row['active_project_id']
        if project!=row['project_id']: raise Fault('SESSION_SCOPE',403)
        self._project(repo,project,human);self._project(repo,project,p)
        if repo.get('system_state','global')['state']!='RUNNING': raise Fault('CONTROL_BLOCKED',403)
        if not self.granted(repo,p,cap,project): raise Fault('CAPABILITY_DENIED',403)
        # Human session authority must still be current; creation is not eternal consent.
        if not self.granted(repo,human,'admin.sessions.manage',project): raise Fault('HUMAN_SESSION_AUTHORITY_REVOKED',403)
        return p,human,row

    def runtime_knowledge(self,p,session_id,body,correlation,service):
        self.safe(body.model_dump(mode='json'))
        def check():
            with self.store.read() as repo:
                actual,human,row=self.runtime_session(repo,p,session_id,'runtime.session.read')
                if body.project_id!=row['active_project_id']: raise Fault('SESSION_SCOPE',403)
                self._check(repo,actual,body.project_id,'knowledge','knowledge.read')
                self._check(repo,human,body.project_id,'knowledge','knowledge.read')
        check()
        result=service.query(p,body,correlation)
        check() # Revocation/session/state changes during upstream I/O fail closed.
        self.safe(result.model_dump(mode='json'),max_chars=2*1024*1024)
        return result

    def runtime_read(self,p,session_id,action_id=None):
        with self.store.read() as repo:
            p,human,row=self.runtime_session(repo,p,session_id,'runtime.session.read')
            if not action_id: return row
            action=repo.get('actions',action_id)
            if not action or action.get('session_id')!=session_id or action['principal_id']!=p.principal_id: raise Fault('OBJECT_SCOPE',403)
            return action

    def runtime_change(self,p,session_id,operation,data,key,correlation):
        import re
        self.safe(data)
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key or ''): raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        cap={'action':'runtime.actions.propose','learning':'runtime.learning.propose','touch':'runtime.session.write'}[operation]
        with self.store.transaction() as repo:
            p,human,session=self.runtime_session(repo,p,session_id,cap)
            project=session['active_project_id']
            fp=digest(dict(op=operation,session=session_id,data=data));rid=digest(dict(principal=p.principal_id,key=key))
            prior=repo.get('idempotency',rid)
            if prior:
                if prior['fingerprint']!=fp: raise Fault('IDEMPOTENCY_CONFLICT',409)
                return prior['response']
            if operation=='action':
                tool=repo.get('tools',data['tool_id'])
                if not tool or data['capability'] not in tool['capabilities']: raise Fault('UNKNOWN_CAPABILITY')
                from .policy import Policy
                requirement=Policy.requirement(data['capability'],False,bool(data['parameters'].get('participants')))
                try:
                    self._check(repo,p,project,data['tool_id'],data['capability'])
                    self._check(repo,human,project,data['tool_id'],data['capability'])
                except Fault: requirement='DENY'
                result=dict(**data,action_id=ident(),principal_id=p.principal_id,human_principal_id=human.principal_id,
                    project_id=project,origin_type='MODEL_PROPOSED',origin_id=p.principal_id,session_id=session_id,
                    correlation_id=correlation,risk_level='LOW' if data['capability']=='knowledge.read' else 'HIGH',
                    approval_requirement=requirement,status={'AUTO':'PROPOSED','CONFIRM':'WAITING_APPROVAL','DENY':'DENIED'}[requirement],created_at=stamp())
                result['scope']=action_scope(result);repo.add('actions',result['action_id'],result)
                if requirement=='CONFIRM': repo.add('approval_requests',result['action_id'],dict(action_id=result['action_id'],principal_id=p.principal_id,
                    human_principal_id=human.principal_id,project_id=project,status='PENDING',scope=result['scope']))
            elif operation=='learning':
                result=dict(**data,candidate_id=ident(),principal_id=p.principal_id,human_principal_id=human.principal_id,
                    project_id=project,session_id=session_id,origin_type='MODEL_PROPOSED',status='PROPOSED',created_at=stamp())
                repo.add('learning',result['candidate_id'],result)
            else:
                result={**session,'last_activity':stamp()};repo.put('sessions',session_id,result)
            self.event(repo,p.principal_id,project,'RUNTIME_'+operation.upper(),'COMMITTED',correlation,result.get('tool_id'),result.get('action_id'))
            repo.add('idempotency',rid,dict(principal_id=p.principal_id,fingerprint=fp,response=result))
            return result
