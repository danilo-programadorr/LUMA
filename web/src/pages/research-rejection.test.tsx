import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen,fireEvent,waitFor} from '@testing-library/react';
import {AuthContext} from '@/auth/context';
import {ApiError,ControlPlaneClient,type AuthClient} from '@/auth/client';
import {ResearchPanel} from '@/components/luma/research-panel';
const auth:AuthClient={observe:()=>()=>{},login:async()=>{},logout:async()=>{},token:async()=> 'synthetic-fixture',reauthenticate:async()=>{}};
afterEach(()=>{cleanup();sessionStorage.clear();vi.restoreAllMocks();});
it('preserves a known public rejection code without retrying 403',async()=>{
 const request=vi.fn(async()=>new Response(JSON.stringify({error:{code:'RESEARCH_EGRESS_BLOCKED'}}),{status:403}));
 await expect(new ControlPlaneClient(auth,'http://localhost:8770',request).call('/v1/research',{})).rejects.toMatchObject({status:403,code:'RESEARCH_EGRESS_BLOCKED'});
 expect(request).toHaveBeenCalledOnce();
});
it.each(['unexpected-private-value','PRIVATE_TOKEN_SECRET','A'.repeat(200)])('does not expose unknown error content: %s',async code=>{
 const request=vi.fn(async()=>new Response(JSON.stringify({error:{code,message:'private-response-body'}}),{status:403}));
 const error=await new ControlPlaneClient(auth,'http://localhost:8770',request).call('/v1/research',{}).catch(e=>e);
 expect(error).toBeInstanceOf(ApiError);if(!(error instanceof ApiError))throw new Error('Expected ApiError');
 expect(error.status).toBe(403);expect(error.code).toBeUndefined();expect(String(error)).not.toContain(code);expect(JSON.stringify(error)).not.toContain('private-response-body');expect(request).toHaveBeenCalledOnce();
});
it('clears an old completed display when a new request is rejected and shows the reason',async()=>{
 const id='b'.repeat(32);sessionStorage.setItem('luma.research.id',id);
 const row={research_id:id,project_id:'meu-gestor',status:'COMPLETED',result:null,error_code:null,display_status:'GROUNDED_RESULT_NOT_RETAINED',route:{route:'WEB_FIRST',freshness_required:false}};
 const request=vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
  if(String(input).endsWith('/devices'))return new Response(JSON.stringify([{device_id:'a'.repeat(32),display_name:'Synthetic PC',status:'ACTIVE',web_research_approved:true}]));
  if(init?.method==='POST')return new Response(JSON.stringify({error:{code:'RESEARCH_EGRESS_BLOCKED'}}),{status:403});
  return new Response(JSON.stringify(row));
 });
 const api=new ControlPlaneClient(auth,'http://localhost:8770',request);
 render(<AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:api,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><ResearchPanel/></AuthContext.Provider>);
 await screen.findByText('Resultado Google não retido. Uma nova pesquisa exige sua solicitação.');
 await screen.findByText('Synthetic PC · ACTIVE');
 fireEvent.change(screen.getByLabelText('Computador da pesquisa'),{target:{value:'a'.repeat(32)}});
 fireEvent.change(screen.getByLabelText('Pergunta de pesquisa'),{target:{value:'Pergunta pública sintética'}});
 fireEvent.click(screen.getByRole('button',{name:'Pesquisar'}));
 await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('RESEARCH_EGRESS_BLOCKED'));
 expect(screen.queryByRole('status')).toBeNull();expect(screen.queryByText('Resultado Google não retido. Uma nova pesquisa exige sua solicitação.')).toBeNull();
 expect(sessionStorage.getItem('luma.research.id')).toBeNull();expect(request.mock.calls.filter(([,init])=>init?.method==='POST')).toHaveLength(1);
});
