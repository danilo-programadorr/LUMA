"""Compatibility adapter: existing LOCAL_DEV model calls use the same wire envelopes."""
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from pydantic import ValidationError
from .remote_protocol import RemoteTaskEnvelope,ContextEnvelope,RuntimeResultEnvelope,decode
from .runtime_processor import RuntimeTaskProcessor,LocalRuntimeTransport,IntelligenceHandler
from .app.errors import Fault
class EnvelopeModelProvider:
    def __init__(self,provider):
        self.provider=provider
        self.transport=LocalRuntimeTransport(RuntimeTaskProcessor(IntelligenceHandler(provider),device_id='local-dev',registry_version='local-dev'))
    def __getattr__(self,name):return getattr(self.provider,name)
    def generate(self,context,correlation_id):
        now=datetime.now(timezone.utc);key=uuid4().hex
        task=RemoteTaskEnvelope(task_id=key,project_id=context.project_id,session_id=context.session_id or 'local-dev',
            target_device_id='local-dev',correlation_id=correlation_id or key,created_at=now,expires_at=now+timedelta(minutes=5),
            task_type='MODEL_GENERATION',user_message=context.user_message,context_ref=ContextEnvelope(model_input=context),
            idempotency_key=key,tool_registry_version='local-dev')
        try:return decode(RuntimeResultEnvelope,self.transport.exchange(task.model_dump_json().encode())).model_result
        except ValidationError as exc:
            if context.decision_mode!='GENERAL' and any('proposed_actions' in e['loc'] for e in exc.errors(include_input=False,include_context=False,include_url=False)):
                raise Fault('PROPOSAL_SCHEMA_INVALID',503) from None
            raise Fault('MODEL_INVALID_RESPONSE',503) from None
    def close(self):self.provider.close()
    def status(self):return self.provider.status()
