import React from 'react';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {AuthContext} from '../auth/context';
import {MemoryRouter} from 'react-router-dom';
import {type ControlPlaneClient} from '../auth/client';
import {CodexTaskComposer} from './CodexTaskComposer';
import {RemoteTasksPanel} from './RemoteTasksPanel';
afterEach(cleanup);
const workspace={workspace_id:'codex-acceptance-v1',project_id:'meu-gestor',target_device_id:'a'.repeat(32),display_name:'Fixture sintético Codex',enabled:false,mapping_version:1,mapping_fingerprint:'b'.repeat(64),snapshot_hash:'f'.repeat(64),allowed_execution_modes:['READ_ONLY','WORKSPACE_WRITE'],binary_sha256:'c'.repeat(64),model:'fixture-model'};
function mount(enabled=false){
 let current={...workspace,enabled};
 const call=vi.fn(async(path:string,body?:unknown)=>{
  if(path==='/v1/codex/workspaces'&&body){current={...current,enabled:true};return current;}
  if(path==='/v1/codex/workspaces')return [current];
  return {};
 });
 render(<AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:{call} as unknown as ControlPlaneClient,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><CodexTaskComposer onCreated={()=>Promise.resolve()}/></AuthContext.Provider>);
 return call;
}
it('requires explicit workspace permission and never approves a task while enabling',async()=>{
 const call=mount();await screen.findByText('Fixture sintético Codex');
 fireEvent.click(screen.getByLabelText(/Revisei o dispositivo/));
 fireEvent.click(screen.getByRole('button',{name:'Permitir Codex neste workspace'}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith('/v1/codex/devices/'+workspace.target_device_id+'/grant',{enabled:true,confirmation:'CODEX_EXECUTION_ONE_SHOT_ONLY'}));
 expect(call.mock.calls.some(([p])=>p.includes('/decision')||p==='/v1/tasks')).toBe(false);
 const registration=call.mock.calls.find(([p,b])=>p==='/v1/codex/workspaces'&&b);
 expect(registration?.[1]).toMatchObject({manifest:{enabled:true,workspace_id:workspace.workspace_id}});
});
it('creates an exact Codex proposal without automatic approval',async()=>{
 const call=mount(true);
 await screen.findByRole('button',{name:'Criar proposta Codex'});
 fireEvent.change(screen.getByLabelText('Tarefa técnica limitada'),{target:{value:'Analise add sem editar.'}});
 fireEvent.click(screen.getByRole('button',{name:'Criar proposta Codex'}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith('/v1/tasks',expect.objectContaining({executor:'CODEX',target_device_id:workspace.target_device_id,codex_profile:expect.objectContaining({execution_mode:'READ_ONLY',allowed_paths:[],binary_sha256:workspace.binary_sha256,model:workspace.model})})));
 expect(call.mock.calls.some(([p])=>p.includes('/decision'))).toBe(false);
 expect(screen.queryByLabelText('Caminho livre')).toBeNull();
});
it('workspace-write proposal lists a single exact fixture path',async()=>{
 const call=mount(true);await screen.findByRole('button',{name:'Criar proposta Codex'});
 fireEvent.change(screen.getByLabelText('Modo Codex'),{target:{value:'WORKSPACE_WRITE'}});
 fireEvent.change(screen.getByLabelText('Tarefa técnica limitada'),{target:{value:'Corrigir soma.'}});
 fireEvent.click(screen.getByRole('button',{name:'Criar proposta Codex'}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith('/v1/tasks',expect.objectContaining({codex_profile:expect.objectContaining({execution_mode:'WORKSPACE_WRITE',allowed_paths:['src/calc.py'],max_changed_files:1})})));
});
it('labels real scope and verified result without claiming a synthetic effect',async()=>{
 const t={task_id:'d'.repeat(32),project_id:'meu-gestor',task_type:'ACTION_ORIENTED',input:'Corrigir fixture',status:'COMPLETED',expires_at:'2099-01-01T00:00:00Z',proposal:{envelope:{tool_id:'codex-executor',operation:'WORKSPACE_WRITE',parameters:{workspace_id:'codex-acceptance-v1',max_changed_files:1,max_duration:120}}},codex_result:{summary:'Soma do fixture conferida.',code:'CODEX_VERIFIED',changed_files:['src/calc.py'],validation_pass:true,duration_ms:700},timeline:[]};
 const call=vi.fn(async(path:string)=>path.includes('codex')||path.includes('devices')?[]:[t]);
 render(<MemoryRouter><AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:{call} as unknown as ControlPlaneClient,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><RemoteTasksPanel approvals/></AuthContext.Provider></MemoryRouter>);
 await screen.findByText(/Workspace autorizado: codex-acceptance-v1/);
 expect(screen.getByText(/Validação local: PASS/)).toBeTruthy();
 expect(screen.getByText('Soma do fixture conferida.')).toBeTruthy();
 expect(screen.queryByText(/Consequência prevista: registro sintético/)).toBeNull();
 expect(screen.queryByRole('button',{name:'Aprovar proposta'})).toBeNull();
});