import hashlib
import json
from datetime import timedelta
from threading import RLock
from .errors import Fault
from .models import ActionRequest, ApprovalRecord, now
from .registry import TOOLS
from .audit import emit
from .models import ident


class Policy:
    """Local control plane. No external executor exists."""
    def __init__(self):
        self.state='RUNNING'
        self.revoked=set()
        self.disabled=set()
        self.suspended=set()
        self.approvals={}
        self.proposals={}
        self.used=set()
        self.lock=RLock()

    def set_state(self,state):
        if state not in ('RUNNING','PAUSED','LOCKED'): raise Fault('INVALID_STATE')
        with self.lock: self.state=state
        emit(None,None,'CONTROL_STATE',state,ident())

    def revoke(self,principal_id,project_id,capability):
        with self.lock: self.revoked.add((principal_id,project_id,capability))
        emit(principal_id,project_id,'CAPABILITY_REVOKED','REVOKED',ident())

    def disable(self,tool_id):
        with self.lock: self.disabled.add(tool_id)
        emit(None,None,'TOOL_DISABLED','DISABLED',ident(),tool_id=tool_id)

    def suspend(self,project_id):
        with self.lock: self.suspended.add(project_id)
        emit(None,project_id,'PROJECT_SUSPENDED','SUSPENDED',ident())

    def check(self,principal,project,tool_id,capability):
        with self.lock:
            tool=TOOLS.get(tool_id)
            if project.project_id not in principal.project_scopes: raise Fault('FORBIDDEN_SCOPE',403)
            if (project.project_id in self.suspended or not project.enabled or project.status!='ACTIVE'):
                raise Fault('PROJECT_SUSPENDED',403)
            if (capability not in principal.capabilities or capability not in project.capabilities or
                (principal.principal_id,project.project_id,capability) in self.revoked):
                raise Fault('CAPABILITY_DENIED',403)
            if not tool or not tool.enabled or tool_id in self.disabled or capability not in tool.capabilities:
                raise Fault('TOOL_DISABLED',403)
            # In this phase, no mutable tool can be admitted, even if registries are misconfigured.
            if capability!='knowledge.read' or tool_id!='knowledge': raise Fault('EXTERNAL_EXECUTION_DISABLED',403)
            # Explicit local policy: even reads are blocked when PAUSED/LOCKED.
            if self.state!='RUNNING': raise Fault('LUMA_'+self.state,403)

    @staticmethod
    def requirement(capability,explicit_owner=False,other_participants=False):
        if other_participants or capability in ('calendar.delete','calendar.invite','tasks.delete','github.write','firebase.deploy','codex.execute','ads.manage','pc.execute'):
            return 'CONFIRM'
        if capability in ('knowledge.read','calendar.read','calendar.availability','tasks.read','github.read','firebase.read','analytics.read'):
            return 'AUTO'
        if capability in ('calendar.create','calendar.update','calendar.reminders','tasks.create','tasks.update','tasks.complete','tasks.reopen','tasks.organize'):
            return 'AUTO' if explicit_owner else 'CONFIRM'
        return 'DENY'

    def propose(self,principal,project_id,tool_id,capability,intent,parameters,explicit_owner=False):
        if 'OWNER' not in principal.roles or project_id not in principal.project_scopes:
            raise Fault('FORBIDDEN_SCOPE',403)
        tool=TOOLS.get(tool_id)
        if not tool or capability not in tool.capabilities: raise Fault('UNKNOWN_CAPABILITY',403)
        requirement=self.requirement(capability,explicit_owner,bool(parameters.get('participants')))
        action=ActionRequest(principal_id=principal.principal_id,project_id=project_id,tool_id=tool_id,
            capability=capability,intent=intent,parameters=json.loads(json.dumps(parameters)),
            risk_level='LOW' if capability=='knowledge.read' else 'HIGH',approval_requirement=requirement,
            status='WAITING_APPROVAL' if requirement=='CONFIRM' else 'PROPOSED')
        with self.lock:
            if len(self.proposals)>=1000: raise Fault('LOCAL_CAPACITY',503)
            self.proposals[action.action_id]=self.scope(action)
        emit(principal.principal_id,project_id,'ACTION_PROPOSED',action.status,ident(),tool_id=tool_id,action_id=action.action_id)
        return action

    @staticmethod
    def scope(action):
        return hashlib.sha256(json.dumps(action.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def approve(self,principal,action,decision='APPROVE'):
        if self.proposals.get(action.action_id)!=self.scope(action) or principal.principal_id!=action.principal_id or 'OWNER' not in principal.roles or action.project_id not in principal.project_scopes:
            raise Fault('APPROVAL_FORBIDDEN',403)
        record=ApprovalRecord(action_id=action.action_id,principal_id=principal.principal_id,
            decision=decision,expires_at=now()+timedelta(minutes=5),scope=self.scope(action))
        with self.lock:
            if len(self.approvals)>=1000: raise Fault('LOCAL_CAPACITY',503)
            self.approvals[record.approval_id]=record
        emit(principal.principal_id,action.project_id,'APPROVAL_RECORDED',record.decision,ident(),tool_id=action.tool_id,action_id=action.action_id)
        return record

    def consume_approval(self,principal,action,approval_id):
        with self.lock:
            record=self.approvals.get(approval_id)
            if (not record or record.decision!='APPROVE' or record.action_id!=action.action_id or
                record.principal_id!=principal.principal_id or action.principal_id!=principal.principal_id or
                action.project_id not in principal.project_scopes or record.scope!=self.scope(action) or
                record.expires_at<=now() or approval_id in self.used or self.state!='RUNNING' or
                action.project_id in self.suspended or action.tool_id in self.disabled or
                (principal.principal_id,action.project_id,action.capability) in self.revoked):
                raise Fault('APPROVAL_INVALID',403)
            self.used.add(approval_id)
        emit(principal.principal_id,action.project_id,'APPROVAL_CONSUMED','CONSUMED',ident(),tool_id=action.tool_id,action_id=action.action_id)
        # Consuming approval grants no execution ability; runtime check is separate and mandatory.

    def authorize_action(self,principal,project,action,approval_id=None):
        with self.lock:
            self.check(principal,project,action.tool_id,action.capability)
            if self.proposals.get(action.action_id)!=self.scope(action) or action.principal_id!=principal.principal_id or action.project_id!=project.project_id:
                raise Fault('ACTION_SCOPE',403)
            if action.approval_requirement!='AUTO':
                if action.approval_requirement=='DENY' or not approval_id: raise Fault('APPROVAL_REQUIRED',403)
                self.consume_approval(principal,action,approval_id)
