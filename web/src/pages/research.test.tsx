import {safeSourceUrl} from '@/lib/research-links';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen,fireEvent,waitFor} from '@testing-library/react';
import {ResearchAnswer,ResearchPanel} from '@/components/luma/research-panel';
import {AuthContext} from '@/auth/context';
import {ControlPlaneClient} from '@/auth/client';
afterEach(()=>{cleanup();sessionStorage.clear();vi.restoreAllMocks();});
const result={answer:'Public claim',project_answer:'Internal version',sources:[{source_id:'s',title:'<script>alert(1)</script>',url:'https://react.dev/',domain:'react.dev',source_type:'OFFICIAL',retrieved_at:1,published_at:null}],citations:[{citation_id:'c',source_id:'s',start_index:0,end_index:12}],freshness_status:'EVIDENCED',uncertainty_note:'Limited evidence',search_suggestions:[],error_code:null};
it('renders untrusted title as text and external links safely',()=>{const {container}=render(<ResearchAnswer result={result}/>);expect(container.querySelector('script')).toBeNull();expect(screen.getByText('<script>alert(1)</script>').getAttribute('rel')).toBe('noopener noreferrer');});
it.each(['javascript:alert(1)','file:///secret','data:text/html,x','https://user:pass@example.com'])('rejects unsafe link %s',url=>expect(safeSourceUrl(url)).toBeUndefined());
it('separates project and web evidence',()=>{render(<ResearchAnswer result={result}/>);expect(screen.getByText('Projeto · conhecimento interno')).toBeTruthy();expect(screen.getByText('Internet · fontes consultadas')).toBeTruthy();});
it('shows unavailable freshness without inventing answer',()=>{render(<ResearchAnswer result={{...result,answer:'',sources:[],citations:[],freshness_status:'UNAVAILABLE'}}/>);expect(screen.getByText('Não foi possível verificar informação atual na internet.')).toBeTruthy();});
function setup(status='WAITING_FOR_DEVICE'){
 const row={research_id:'b'.repeat(32),project_id:'meu-gestor',status,result:null,error_code:null,route:{route:'WEB_REQUIRED',freshness_required:true}};
 const call=vi.fn(async(path:string)=>path==='/v1/research/devices'?[{device_id:'a'.repeat(32),display_name:'Synthetic PC',status:'ACTIVE',web_research_approved:true}]:path.endsWith('/cancel')?{...row,status:'CANCELLED'}:row);
 render(<AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:{call} as unknown as ControlPlaneClient,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><ResearchPanel/></AuthContext.Provider>);return call;
}
it('requires explicit target and persists only research identifier',async()=>{const call=setup();await screen.findByText('Synthetic PC · ACTIVE');fireEvent.change(screen.getByLabelText('Computador da pesquisa'),{target:{value:'a'.repeat(32)}});fireEvent.change(screen.getByLabelText('Pergunta de pesquisa'),{target:{value:'React hoje?'}});fireEvent.click(screen.getByRole('button',{name:'Pesquisar'}));await screen.findByText('Aguardando o computador');expect(sessionStorage.getItem('luma.research.id')).toBe('b'.repeat(32));expect(JSON.stringify(sessionStorage)).not.toContain('React hoje');expect(call).toHaveBeenCalledWith('/v1/research',expect.objectContaining({mode:'AUTO',target_device_id:'a'.repeat(32)}));});
it('restores existing request without creating new work and cancels',async()=>{sessionStorage.setItem('luma.research.id','b'.repeat(32));const call=setup();await screen.findByText('Aguardando o computador');expect(call.mock.calls.some(([p])=>p==='/v1/research')).toBe(false);fireEvent.click(screen.getByText('Cancelar pesquisa'));await screen.findByText('CANCELLED');});
it('terminal failure is visible',async()=>{sessionStorage.setItem('luma.research.id','b'.repeat(32));setup('FAILED');await waitFor(()=>expect(screen.getByRole('status').textContent).toBe('FAILED'));});

it('uses code-point citation offsets when emoji precedes the cited text',()=>{const answer='🚀 A versão estável.';const start=4;render(<ResearchAnswer result={{...result,answer,project_answer:'',sources:[{...result.sources[0],title:'Synthetic source'}],citations:[{citation_id:'unicode',source_id:'s',start_index:start,end_index:start+Array.from('versão estável').length}]}}/>);expect(screen.getByText('versão estável — Synthetic source')).toBeTruthy();});
