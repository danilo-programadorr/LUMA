from fastapi import APIRouter,Request,Security
from fastapi.security import HTTPBearer
from pydantic import Field
from .models import Contract,KnowledgeRequest
from .errors import Fault

class RuntimeKnowledge(KnowledgeRequest):
    session_id:str=Field(min_length=1,max_length=64)
class RuntimeProposal(Contract):
    session_id:str=Field(min_length=1,max_length=64)
    tool_id:str=Field(min_length=1,max_length=64)
    capability:str=Field(min_length=1,max_length=100)
    intent:str=Field(min_length=1,max_length=1000)
    parameters:dict=Field(default_factory=dict)
class RuntimeLearning(Contract):
    session_id:str=Field(min_length=1,max_length=64)
    source:str=Field(min_length=1,max_length=500)
    claim:str=Field(min_length=1,max_length=2000)
    evidence:list[str]=Field(min_length=1,max_length=10)
    confidence:str=Field(pattern='^(LOW|MEDIUM|HIGH)$')
class Touch(Contract):
    session_id:str=Field(min_length=1,max_length=64)

def install_runtime(app,control,service):
    router=APIRouter(prefix='/v1/runtime',dependencies=[Security(HTTPBearer(auto_error=False))])
    def change(request,body,operation):
        keys=request.headers.getlist('idempotency-key')
        if len(keys)!=1: raise Fault('IDEMPOTENCY_KEY_REQUIRED')
        return control.runtime_change(request.state.principal,body.session_id,operation,
            body.model_dump(exclude={'session_id'}),keys[0],request.state.correlation_id)
    @router.get('/status')
    def status(request:Request):
        return {'principal_id':request.state.principal.principal_id,'principal_type':'SERVICE_RUNTIME',
            'generative_ai_enabled':False,'external_execution_enabled':False}
    @router.post('/knowledge/query')
    def knowledge(body:RuntimeKnowledge,request:Request):
        query=KnowledgeRequest(**body.model_dump(exclude={'session_id'}))
        return control.runtime_knowledge(request.state.principal,body.session_id,query,request.state.correlation_id,service)
    @router.post('/actions/propose')
    def propose(body:RuntimeProposal,request:Request): return change(request,body,'action')
    @router.get('/actions/{action_id}')
    def action(action_id:str,session_id:str,request:Request): return control.runtime_read(request.state.principal,session_id,action_id)
    @router.get('/sessions/{session_id}')
    def session(session_id:str,request:Request): return control.runtime_read(request.state.principal,session_id)
    @router.post('/sessions/touch')
    def touch(body:Touch,request:Request): return change(request,body,'touch')
    @router.post('/learning/propose')
    def learning(body:RuntimeLearning,request:Request): return change(request,body,'learning')
    app.include_router(router)
