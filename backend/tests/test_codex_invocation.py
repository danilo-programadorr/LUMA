"""Invocation policy and validation broker: no model calls."""
import json,sys
from pathlib import Path
import pytest
from backend.tests.test_codex_adapter import context

def test_invocation_has_no_general_shell_or_inherited_integrations(tmp_path):
 from device_agent.codex_invocation import prepare_invocation
 r,w,b,j=context(tmp_path)
 from backend.codex.contracts import ExecutionProfile
 p=ExecutionProfile.model_validate(j['profile'])
 argv,prompt,options=prepare_invocation(b,tmp_path/'state',w,p,'[]',j)
 assert '--ignore-user-config' in argv and '--ephemeral' in argv
 assert any('features.shell_tool=false'==v for v in argv)
 assert any('windows.sandbox="mxc"'==v for v in argv)
 assert not any('bypass' in v or 'danger-full' in v or '--ignore-rules'==v for v in argv)
 assert 'UNTRUSTED' in prompt and len(prompt)<40000
 assert options=={}

def test_broker_rejects_arbitrary_arguments_and_unknown_tool(tmp_path):
 from device_agent.codex_broker import ValidationBroker
 r,w,b,j=context(tmp_path);calls=[]
 broker=ValidationBroker({'expires_at':'2099-01-01T00:00:00+00:00'},lambda: calls.append(True) or True)
 bad=broker.handle({'id':1,'method':'tools/call','params':{'name':'validate','arguments':{'command':'anything'}}})
 assert 'error' in bad and not calls
 bad=broker.handle({'id':2,'method':'tools/call','params':{'name':'shell','arguments':{}}})
 assert 'error' in bad and not calls
 good=broker.handle({'id':3,'method':'tools/call','params':{'name':'validate','arguments':{}}})
 assert good['result']['isError'] is False and calls==[True]
 broker.handle({'id':4,'method':'tools/call','params':{'name':'validate','arguments':{}}})
 third=broker.handle({'id':5,'method':'tools/call','params':{'name':'validate','arguments':{}}})
 assert 'error' in third and len(calls)==2

def test_native_validation_args_cannot_take_model_commands(tmp_path):
 from device_agent.codex_invocation import sandbox_args
 from backend.codex.contracts import ExecutionProfile
 r,w,b,j=context(tmp_path);p=ExecutionProfile.model_validate(j['profile'])
 argv=sandbox_args(b,w,p,validator=True)
 assert '--permission-profile' in argv and '--include-managed-config' in argv
 assert any('network.enabled=false' in x for x in argv)
 assert 'cmd.exe' not in argv and 'powershell.exe' not in argv

def test_usage_contract_rejects_untrusted_fields():
 from backend.codex.contracts import ExecutionResult
 from pydantic import ValidationError
 with pytest.raises(ValidationError):
  ExecutionResult(execution_id='x',job_id='x',workspace_id='fixture',status='FAILED',code='CODEX_FAILED',binary_sha256='a'*64,profile_hash='a'*64,duration_ms=1,usage={'secret':'not permitted'})