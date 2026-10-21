"""Durable grants and tamper evidence, shared by explicit migration and bootstrap."""
import hashlib
import json
from .models import now,ident
from .errors import Fault

RUNTIME_CAPS=('knowledge.read','runtime.session.read','runtime.session.write','runtime.actions.propose')
NEW_ADMIN_CAPS=('admin.grants.read','admin.grants.manage','admin.retention.read')

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def grant(repo,principal,capability,project=None,tool=None,by='MIGRATION_0002',expires=None):
    gid=ident()
    row=dict(grant_id=gid,principal_id=principal,capability=capability,project_id=project,tool_id=tool,
        scope='PROJECT' if project else 'GLOBAL',granted_by=by,created_at=now().isoformat(),expires_at=expires,status='ACTIVE')
    repo.add('grants',gid,row)
    return row

def seed(repo):
    # Called once: migration for populated v1; bootstrap for a fresh empty schema.
    owner=repo.get('principals','local-owner')
    if not owner: return
    for principal in repo.rows('principals'):
        if principal['principal_id']!='local-owner':
            raise ValueError('UNSUPPORTED_LEGACY_PRINCIPAL')
        principal['principal_type']='HUMAN_OWNER'
        repo.put('principals',principal['principal_id'],principal)
        for cap in principal['capabilities']:
            if cap.startswith('admin.'): grant(repo,principal['principal_id'],cap)
            else:
                for project in principal['project_scopes']: grant(repo,principal['principal_id'],cap,project)
    for cap in NEW_ADMIN_CAPS: grant(repo,'local-owner',cap)
    runtime=dict(principal_id='luma-runtime',principal_type='SERVICE_RUNTIME',display_name='LUMA runtime',roles=[],
        project_scopes=list(owner['project_scopes']),capabilities=[],approval_level='OWNER_SCOPED',status='ACTIVE',created_at=now().isoformat())
    repo.add('principals','luma-runtime',runtime)
    for project in runtime['project_scopes']:
        for cap in RUNTIME_CAPS: grant(repo,'luma-runtime',cap,project,'knowledge' if cap=='knowledge.read' else None)
    for category in ('sessions','actions','approvals','learning_candidates','audit'):
        repo.add('retention_policies',category,dict(category=category,mode='NO_AUTO_DELETE',purge_enabled=False,
            expiration_is_deletion=False,created_at=now().isoformat()))
    for session in repo.rows('sessions'):
        session.update(human_principal_id=session['principal_id'],runtime_principal_id=None)
        repo.put('sessions',session['session_id'],session)

def verify(repo):
    events=sorted(repo.rows('audit_events'),key=lambda r:r.get('sequence',-1))
    previous='0'*64
    for seq,event in enumerate(events,1):
        content={k:v for k,v in event.items() if k!='event_hash'}
        if event.get('sequence')!=seq or event.get('previous_hash')!=previous or event.get('event_hash')!=digest(content):
            raise Fault('AUDIT_INTEGRITY_FAILURE',503)
        previous=event['event_hash']
    anchor=repo.get('audit_chain','head')
    if anchor != dict(sequence=len(events),event_hash=previous): raise Fault('AUDIT_INTEGRITY_FAILURE',503)
    return anchor

def append(repo,event):
    anchor=verify(repo)
    event={**event,'sequence':anchor['sequence']+1,'previous_hash':anchor['event_hash'],
        'visibility':'ADMIN'}
    event['event_hash']=digest(event)
    repo.add('audit_events',event['event_id'],event)
    repo.put('audit_chain','head',dict(sequence=event['sequence'],event_hash=event['event_hash']))
