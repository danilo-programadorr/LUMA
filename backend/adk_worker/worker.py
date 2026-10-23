"""Credential-free ADK runtime. The only model is a host-mediated BaseLlm."""
import asyncio,json,sys,logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from google.adk import Agent,Workflow
from google.adk.runners import InMemoryRunner
from google.adk.workflow import JoinNode
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.models._capabilities import LlmCapabilities
from google.genai import types

logging.disable(logging.CRITICAL)

def send(value):
    sys.stdout.write(json.dumps(value,ensure_ascii=False)+'\n');sys.stdout.flush()

def read():
    line=sys.stdin.buffer.readline(131073)
    if not line.endswith(b'\n') or len(line)>131072:raise ValueError('FRAME_INVALID')
    return json.loads(line)

class LumaAdkLlm(BaseLlm):
    model:str='luma-controlled-provider'
    agent_id:str
    @property
    def capabilities(self):return LlmCapabilities(output_schema_and_tools=False)
    async def generate_content_async(self,llm_request,stream=False):
        if stream or llm_request.tools_dict:raise ValueError('TOOLS_OR_STREAM_DENIED')
        # ADK history/instructions never become authority or override host context.
        send({'op':'generate','agent_id':self.agent_id})
        response=read()
        if set(response)!={'decision'}:raise ValueError('HOST_RESPONSE_INVALID')
        yield LlmResponse(content=types.Content(role='model',parts=[types.Part(text=json.dumps(response['decision'],ensure_ascii=False))]),turn_complete=True)

async def run(frame):
    roles=frame['roles']
    if not 1<=len(roles)<=6:raise ValueError('BUDGET')
    agents=[]
    for index,role in enumerate(roles):
        agents.append(Agent(name=role['agent_id']+'_'+str(index),model=LumaAdkLlm(agent_id=role['agent_id']),instruction=role['instruction'],tools=[],disallow_transfer_to_parent=True,disallow_transfer_to_peers=True))
    if [x['agent_id'] for x in roles]==['luma','growth','content','luma']:
        join=JoinNode(name='synthesis_join')
        edges=[('START',agents[0],(agents[1],agents[2]),join,agents[3])]
    else:edges=[tuple(['START',*agents])]
    workflow=Workflow(name='luma',edges=edges,max_concurrency=1)
    runner=InMemoryRunner(node=workflow,app_name='luma-controlled')
    await runner.session_service.create_session(app_name='luma-controlled',user_id='luma-runtime',session_id='ephemeral')
    async for event in runner.run_async(user_id='luma-runtime',session_id='ephemeral',new_message=types.Content(role='user',parts=[types.Part(text='Execute the host-authorized workflow.')])):
        pass
    await runner.close()
    send({'op':'done'})

if __name__=='__main__':
    try:asyncio.run(run(read()))
    except Exception:send({'op':'error','code':'ADK_WORKFLOW_FAILED'});sys.exit(1)
