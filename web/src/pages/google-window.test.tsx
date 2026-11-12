import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {ControlPlaneClient,type AuthClient} from '@/auth/client';
import {AuthContext} from '@/auth/context';
import {ResearchPanel} from '@/components/luma/research-panel';
const auth={token:async()=> 'synthetic'} as AuthClient;
const id='b'.repeat(32);const path='/research-display/'+'c'.repeat(43);
afterEach(()=>{cleanup();sessionStorage.clear();vi.restoreAllMocks();});
it('resolves only exact local ephemeral display paths',()=>{
 const api=new ControlPlaneClient(auth,'http://127.0.0.1:8770');
 expect(api.displayUrl(path)).toBe('http://127.0.0.1:8770'+path);
 for(const bad of ['https://evil.example/','//evil.example/','/research-display/short',path+'?x=1',path+'#x'])expect(()=>api.displayUrl(bad)).toThrow();
});
it('shows metadata-only isolated result link without displaying or retaining Google HTML',async()=>{
 sessionStorage.setItem('luma.research.id',id);
 const request=vi.fn(async(input:RequestInfo|URL,_init?:RequestInit)=>new Response(JSON.stringify(String(input).endsWith('/devices')?[]:{research_id:id,status:'COMPLETED',result:null,display_status:'LIVE_WINDOW_READY',display_path:path,display_expires_at:Math.floor(Date.now()/1000)+30,error_code:null,route:{route:'WEB_REQUIRED',freshness_required:true}})));
 const api=new ControlPlaneClient(auth,'http://127.0.0.1:8770',request);
 const {container}=render(<AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:api,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><ResearchPanel/></AuthContext.Provider>);
 const link=await screen.findByRole('link',{name:'Abrir resultado Google'});expect(link.getAttribute('href')).toBe('http://127.0.0.1:8770'+path);expect(link.getAttribute('rel')).toBe('noopener noreferrer');
 expect(container.querySelector('iframe')).toBeNull();expect(request.mock.calls.every(([,init])=>!init||init.method==='GET')).toBe(true);
 expect(sessionStorage.length).toBe(1);
});
