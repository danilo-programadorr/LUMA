import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen,fireEvent,waitFor,act} from '@testing-library/react';
import {AuthContext} from '@/auth/context';
import {ApiError,type ControlPlaneClient} from '@/auth/client';
import {PrivateLibraryPanel} from '@/components/luma/private-library-panel';
afterEach(()=>{cleanup();sessionStorage.clear();vi.restoreAllMocks();});
const device={device_id:'a'.repeat(32),display_name:'Synthetic PC',status:'ACTIVE',private_library_approved:true,private_library_online:true};
const source={source_id:'b'.repeat(32),project_id:'meu-gestor',device_id:device.device_id,title:'Synthetic source',content_hash:'c'.repeat(64),extension:'.txt',byte_count:40,page_count:0,chunk_count:1,status:'ACTIVE'};
const row={query_id:'d'.repeat(32),target_device_id:device.device_id,project_id:'meu-gestor',status:'COMPLETED',error_code:null,result:{matches:[{source_id:source.source_id,source_hash:source.content_hash,chunk_id:'e'.repeat(24),excerpt:'Synthetic quoted evidence',page:null,line_start:2,line_end:3,score:1,source}]}};
function setup(options:{sources?:typeof source[];devices?:typeof device[];error?:ApiError;result?:unknown}={}){
 const call=vi.fn(async(path:string,body?:object)=>{
  if(options.error)throw options.error;
  if(path==='/v1/library/devices')return (options.devices||[device]).map(d=>({...d}));
  if(path.endsWith('/sources'))return (options.sources||[source]).map(s=>({...s}));
  if(path.endsWith('/capability'))return {private_library_approved:true};
  if(path.endsWith('/archive'))return {...source,status:'ARCHIVED'};
  if(path==='/v1/library/queries')return {...row,status:'ANALYZING',result:null};
  void body;return options.result||row;
 });
 render(<AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:{call} as unknown as ControlPlaneClient,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><PrivateLibraryPanel/></AuthContext.Provider>);return call;
}
async function selectDevice(){await screen.findByText(/Synthetic PC/);fireEvent.change(screen.getByLabelText('Computador da biblioteca'),{target:{value:device.device_id}});}
it('shows an honest empty local library without semantic or active-index claims',async()=>{setup({sources:[]});await selectDevice();await screen.findByText('Nenhum documento cadastrado neste computador.');expect(screen.queryByText(/busca semântica|indexação ativa/i)).toBeNull();});
it('does not pretend feature exists on disabled backend',async()=>{setup({error:new ApiError(404)});await screen.findByText(/Biblioteca privada ainda não habilitada neste servidor/);expect(screen.queryByText('Synthetic source')).toBeNull();});
it('shows metadata and local import instructions',async()=>{setup();await selectDevice();await screen.findByText('Synthetic source');fireEvent.click(screen.getByText('Adicionar documento deste PC'));expect(screen.getAllByText(/run_private_library.ps1/)).toHaveLength(2);});
it('requires explicit target, current grant and nonempty question',async()=>{setup({devices:[{...device,private_library_approved:false}]});await selectDevice();expect(screen.getByRole('button',{name:'Buscar nos documentos'})).toHaveProperty('disabled',true);expect(screen.getByRole('button',{name:'Autorizar biblioteca neste PC'})).toBeTruthy();});
it('queries only after Owner submit and keeps only opaque identifier',async()=>{const call=setup();await selectDevice();await screen.findByText('Synthetic source');expect(call.mock.calls.some(([p])=>p==='/v1/library/queries')).toBe(false);fireEvent.change(screen.getByLabelText('Pergunta sobre os documentos'),{target:{value:'Pergunta privada sintética'}});fireEvent.click(screen.getByRole('button',{name:'Buscar nos documentos'}));await waitFor(()=>expect(sessionStorage.getItem('luma.library.query_id')).toBe(row.query_id));expect(JSON.stringify(sessionStorage)).not.toContain('Pergunta privada');expect(call).toHaveBeenCalledWith('/v1/library/queries',expect.objectContaining({target_device_id:device.device_id,project_id:'meu-gestor',query:'Pergunta privada sintética'}));});
it('restores result with provenance without new work',async()=>{sessionStorage.setItem('luma.library.query_id',row.query_id);const call=setup();await screen.findByText('Synthetic quoted evidence');expect(screen.getByText('Linhas 2–3')).toBeTruthy();expect(call.mock.calls.some(([p])=>p==='/v1/library/queries')).toBe(false);});
it('renders private content as text, without executable markup',async()=>{sessionStorage.setItem('luma.library.query_id',row.query_id);const bad={...row,result:{matches:[{...row.result.matches[0],excerpt:'<script>window.pwned=1</script>'}]}};setup({result:bad});await screen.findByText('<script>window.pwned=1</script>');expect(document.querySelector('script')).toBeNull();});
it('empty match result gives no fabricated answer',async()=>{sessionStorage.setItem('luma.library.query_id',row.query_id);setup({result:{...row,result:{matches:[]}}});await screen.findByText('Nenhum trecho compatível encontrado. Tente outros termos.');});
it('marks private agent offline independently of PC status',async()=>{setup({devices:[{...device,private_library_online:false}]});await selectDevice();await screen.findByText(/Agente da biblioteca offline/);});
it('archive is explicit and does not imply deleting original',async()=>{const call=setup();await selectDevice();await screen.findByText('Synthetic source');vi.spyOn(window,'confirm').mockReturnValue(true);fireEvent.click(screen.getByRole('button',{name:'Arquivar Synthetic source'}));await waitFor(()=>expect(call.mock.calls.some(([p])=>p.endsWith('/archive'))).toBe(true));expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('original'));});

it('suspends only the library and clears the displayed private result',async()=>{
 sessionStorage.setItem('luma.library.query_id',row.query_id);const call=setup();await screen.findByText('Synthetic quoted evidence');await selectDevice();vi.spyOn(window,'confirm').mockReturnValue(true);
 fireEvent.click(screen.getByRole('button',{name:'Suspender biblioteca neste PC'}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith('/v1/library/devices/'+device.device_id+'/capability',{enabled:false}));
 await waitFor(()=>expect(screen.queryByText('Synthetic quoted evidence')).toBeNull());expect(sessionStorage.getItem('luma.library.query_id')).toBeNull();
});
it('a late restoration response cannot replace a new query',async()=>{
 sessionStorage.setItem('luma.library.query_id',row.query_id);let restore:(value:unknown)=>void=()=>{};const delayed=new Promise(resolve=>{restore=resolve;});
 const newer={...row,query_id:'f'.repeat(32),status:'ANALYZING',result:null};
 const call=vi.fn(async(path:string)=>path==='/v1/library/devices'?[device]:path.endsWith('/sources')?[source]:path==='/v1/library/queries'?newer:delayed);
 render(<AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:{call} as unknown as ControlPlaneClient,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><PrivateLibraryPanel/></AuthContext.Provider>);
 await selectDevice();await screen.findByText('Synthetic source');fireEvent.change(screen.getByLabelText('Pergunta sobre os documentos'),{target:{value:'Nova pergunta'}});fireEvent.click(screen.getByRole('button',{name:'Buscar nos documentos'}));
 await waitFor(()=>expect(sessionStorage.getItem('luma.library.query_id')).toBe(newer.query_id));await act(async()=>{restore(row);});
 expect(screen.queryByText('Synthetic quoted evidence')).toBeNull();expect(screen.getByRole('status').textContent).toBe('Preparando consulta');
});

it.each(['suspend','archive'])('refresh invalidates a completed excerpt after external %s',async change=>{
 const devices=[{...device}],sources=[{...source}];sessionStorage.setItem('luma.library.query_id',row.query_id);setup({devices,sources});await screen.findByText('Synthetic quoted evidence');
 if(change==='suspend')devices[0].private_library_approved=false;else sources[0].status='ARCHIVED';
 fireEvent.click(screen.getByRole('button',{name:'Atualizar fontes'}));
 await waitFor(()=>expect(screen.queryByText('Synthetic quoted evidence')).toBeNull());
});
