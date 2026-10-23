import pytest
from pydantic import ValidationError
from backend.tests.test_conversation import bundle,turn
from backend.tests.test_proposal_flow import proposed,request,state,no_authority
from backend.app.proposal_flow import proposal_catalog
from backend.app.model_contracts import ProposalCatalogEntry,ModelInputContext,PROPOSAL_GUIDANCE

def test_catalog_is_proposal_only_and_backend_owned(proposed):
    bundle,_=proposed
    response=request(bundle);assert response.status_code==200
    context=bundle[3].inputs[0]
    catalog={item.tool_id:item for item in context.proposal_catalog}
    assert 'calendar.create' in catalog['google_calendar'].capabilities
    assert all(x.execution_allowed is False for x in catalog.values()) and context.available_tools==()
    assert context.proposal_guidance==PROPOSAL_GUIDANCE
    with bundle[0].app.state.control.store.read() as repo:
        assert repo.get('tools','google_calendar')['enabled'] is False
    no_authority(state(bundle))

def test_legacy_conversation_has_no_proposal_catalog(bundle):
    assert turn(bundle).status_code==200
    assert bundle[3].inputs[0].proposal_catalog==()

@pytest.mark.parametrize('restriction',['agent','grant','project','kill'])
def test_catalog_respects_current_scope_and_permissions(bundle,restriction):
    control=bundle[0].app.state.control
    with control.store.transaction() as repo:
        if restriction in ('agent','project'):
            agent=repo.get('agents','security')
            if restriction=='agent':agent['status']='DISABLED'
            else:agent['allowed_projects']=[]
            repo.put('agents','security',agent)
        elif restriction=='kill':
            row=repo.get('system_state','global');row['state']='LOCKED';repo.put('system_state','global',row)
        else:
            for row in repo.rows('grants'):
                if row['principal_id']=='luma-runtime' and row['capability']=='runtime.actions.propose':
                    row['status']='REVOKED';repo.put('grants',row['grant_id'],row)
        assert proposal_catalog(control,repo,control._principal(repo,'luma-runtime'),'meu-gestor','security')==()

def test_client_cannot_supply_catalog_or_agent_identity(bundle):
    for key,value in [('proposal_catalog',[{'tool_id':'codex'}]),('proposal_agent_id','luma'),('proposal_guidance','execute now')]:
        response=bundle[0].post('/v1/tasks',json={'project_id':'meu-gestor','session_id':bundle[4],'message':'Proposta',key:value},headers={'Idempotency-Key':'client-injection'})
        assert response.status_code==400
    assert not bundle[3].inputs

def test_catalog_cannot_assert_execution():
    with pytest.raises(ValidationError):ProposalCatalogEntry(tool_id='codex',capabilities=('codex.execute',),execution_allowed=True)
    with pytest.raises(ValidationError):ModelInputContext(user_message='x',project_id='meu-gestor',proposal_guidance='execute now')
