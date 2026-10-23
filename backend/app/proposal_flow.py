"""Server-owned proposal validation and content-free stage diagnostics."""
import json
from pydantic import ValidationError
from .model_contracts import ToolCallProposal
from .execution_contracts import CanonicalActionEnvelope
from .models import ident
from .control import stamp,digest
from .errors import Fault
from .provider_diagnostics import valid_metadata

STAGES=('task_accepted','workflow_started','luma_generation','model_decision_parsed','proposal_detected','proposal_schema_validation','agent_tool_identity_validation','project_scope_validation','tool_registry_lookup','capability_check','parameter_normalization','risk_calculation','action_request_construction','action_request_persistence','task_state_transition','response_serialization','transaction_commit')
ERRORS={'proposal_schema_validation':'PROPOSAL_SCHEMA_INVALID','agent_tool_identity_validation':'PROPOSAL_IDENTITY_DENIED','project_scope_validation':'PROPOSAL_PROJECT_SCOPE_DENIED','tool_registry_lookup':'PROPOSAL_TOOL_UNKNOWN','capability_check':'PROPOSAL_CAPABILITY_DENIED','parameter_normalization':'PROPOSAL_PARAMETER_INVALID','risk_calculation':'PROPOSAL_RISK_INVALID','action_request_construction':'ACTION_REQUEST_BUILD_FAILED','action_request_persistence':'ACTION_REQUEST_PERSIST_FAILED','task_state_transition':'TASK_STATE_TRANSITION_FAILED','response_serialization':'RESPONSE_SERIALIZATION_FAILED','transaction_commit':'ACTION_REQUEST_COMMIT_FAILED'}
FORBIDDEN={'approved','authorized','owner','execute_now','risk','risk_level','effective_risk','requested_risk','authorization_id','approval_id','grant','kill_switch','unlock','principal_id','origin_type','permission_override','project_id','capabilities'}

def parameters(value,depth=0):
    if depth>4 or len(json.dumps(value,allow_nan=False))>4096:raise Fault('PROPOSAL_PARAMETER_INVALID',503)
    if isinstance(value,dict):
        if len(value)>16:raise Fault('PROPOSAL_PARAMETER_INVALID',503)
        for k,v in value.items():
            if len(k)>64 or k.casefold() in FORBIDDEN:raise Fault('PROPOSAL_PARAMETER_INVALID',503)
            parameters(v,depth+1)
    elif isinstance(value,list):
        if len(value)>16:raise Fault('PROPOSAL_PARAMETER_INVALID',503)
        for v in value:parameters(v,depth+1)
    elif isinstance(value,str) and len(value)>2000:raise Fault('PROPOSAL_PARAMETER_INVALID',503)

class Trace:
    def __init__(self):
        self.stage=None
        self.data=dict(failure_stage=None,last_completed_stage=None,completed_stages=[],proposal_emitted=None,proposal_count=None,proposal_schema_valid=None,tool_known=None,tool_enabled=None,capability_allowed=None,project_allowed=None,parameters_valid=None,risk_computed=None,action_request_created=False,action_request_persisted=False,authorization_created=False,execution_job_created=False,external_side_effects=False,task_status_before='PENDING',task_status_after='RUNNING',transaction_committed=False,provider_status=None,finish_reason=None,schema_validation=None,response_received=None,model_decision_valid=None)
    def enter(self,stage):
        assert stage in STAGES
        self.stage=stage
    def done(self,stage,**fields):
        self.enter(stage);self.data.update(fields);self.data['last_completed_stage']=stage
        if stage not in self.data['completed_stages']:self.data['completed_stages'].append(stage)
    def provider(self,diagnostic):
        metadata=diagnostic.get('provider') if isinstance(diagnostic,dict) else None
        if metadata and valid_metadata(metadata):
            for key in ('provider_status','finish_reason','schema_validation','response_received'):self.data[key]=metadata[key]
            if metadata['schema_validation'] is not None:self.data['model_decision_valid']=metadata['schema_validation']
            observation=metadata.get('proposal_observation')
            if observation and metadata['schema_validation'] is False:
                self.data.update({k:observation[k] for k in ('proposal_emitted','proposal_count','proposal_schema_valid')})
                self.data['schema_error_fields']=observation['schema_error_fields']
        stage=diagnostic.get('failure_stage') if isinstance(diagnostic,dict) else None
        if stage in ('schema validation','response validation','first generation','model worker startup','GeminiAdapter initialization'):
            self.data['provider_failure_stage']=stage
            if stage=='schema validation':self.enter('proposal_schema_validation' if self.data['proposal_schema_valid'] is False else 'model_decision_parsed')
    def failure(self,error):
        code=error.code if isinstance(error,Fault) else ERRORS.get(self.stage,'WORKFLOW_FAILED')
        if code=='PROPOSAL_SCHEMA_INVALID':
            self.enter('proposal_schema_validation');self.data['proposal_schema_valid']=False
        if code=='DATABASE_UNAVAILABLE':code=ERRORS.get(self.stage,code)
        if code=='MODEL_INVALID_RESPONSE' and self.stage=='proposal_schema_validation':code='PROPOSAL_SCHEMA_INVALID'
        if 'transaction_commit' in self.data['completed_stages']:
            self.data['completed_stages'].remove('transaction_commit')
            self.data['last_completed_stage']=self.data['completed_stages'][-1] if self.data['completed_stages'] else None
        self.data.update(failure_stage=self.stage,safe_error_code=code,task_status_after='FAILED',transaction_committed=False,action_request_persisted=False)
        return code

def prepare(execution,repo,p,project,role,item,trace,task,slot):
    trace.enter('proposal_schema_validation')
    try:item=ToolCallProposal.model_validate_json(json.dumps(item))
    except (ValidationError,ValueError,TypeError):
        trace.data['proposal_schema_valid']=False
        raise Fault('PROPOSAL_SCHEMA_INVALID',503) from None
    trace.done('proposal_schema_validation',proposal_schema_valid=True)
    trace.enter('agent_tool_identity_validation')
    agent=repo.get('agents',role);runtime=execution.control._principal(repo,'luma-runtime')
    if not agent or agent['status']!='ENABLED_LOCAL' or runtime.principal_type!='SERVICE_RUNTIME':raise Fault('PROPOSAL_IDENTITY_DENIED',403)
    trace.done('agent_tool_identity_validation')
    trace.enter('project_scope_validation')
    try:
        execution.owner(repo,p,project);execution.control._project(repo,project,runtime)
        if project not in agent['allowed_projects']:raise Fault('PROPOSAL_PROJECT_SCOPE_DENIED',403)
    except Fault:
        trace.data['project_allowed']=False
        raise Fault('PROPOSAL_PROJECT_SCOPE_DENIED',403) from None
    trace.done('project_scope_validation',project_allowed=True)
    trace.enter('tool_registry_lookup');tool=repo.get('tools',item.tool_id)
    if not tool:
        trace.data['tool_known']=False
        raise Fault('PROPOSAL_TOOL_UNKNOWN',503)
    trace.done('tool_registry_lookup',tool_known=True,tool_enabled=tool['enabled'])
    trace.enter('capability_check')
    if item.capability not in tool['capabilities'] or 'runtime.actions.propose' not in agent['allowed_capabilities'] or 'ACTION_REQUEST' not in agent['allowed_proposal_types'] or not execution.control.granted(repo,runtime,'runtime.actions.propose',project,item.tool_id):
        trace.data['capability_allowed']=False
        raise Fault('PROPOSAL_CAPABILITY_DENIED',403)
    trace.done('capability_check',capability_allowed=True)
    # Existing candidate policy allows a proposal for a disabled known tool;
    # authorize/execute still require enabled=True. No tool state is mutated.
    trace.enter('parameter_normalization')
    try:
        parameters(item.parameters);normalized=json.loads(json.dumps(item.parameters,sort_keys=True,allow_nan=False))
        execution.control.safe(normalized)
    except (Fault,ValueError,TypeError):
        trace.data['parameters_valid']=False
        raise Fault('PROPOSAL_PARAMETER_INVALID',503) from None
    trace.done('parameter_normalization',parameters_valid=True)
    envelope=CanonicalActionEnvelope(project_id=project,tool_id=item.tool_id,operation=item.capability,parameters=normalized).model_dump(mode='json')
    trace.enter('risk_calculation');_,risk=execution.definition(repo,envelope)
    if risk not in ('LOW','MEDIUM','HIGH','CRITICAL'):raise Fault('PROPOSAL_RISK_INVALID',503)
    trace.done('risk_calculation',risk_computed=True)
    trace.enter('action_request_construction')
    row=dict(action_id=ident(),principal_id=p.principal_id,project_id=project,envelope=envelope,risk_level=risk,origin_type='AGENT_PROPOSED',origin_id=role,status='WAITING_AUTHORIZATION',created_at=stamp(),correlation_id=task['correlation_id'],task_id=task['task_id'],workflow_run_id=task['workflow_run_id'],proposal_hash=digest(envelope),proposal_slot=slot)
    trace.done('action_request_construction',action_request_created=True)
    return row
