import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
import {ControlPlaneClient,type AuthClient} from '@/auth/client';
import {GoogleSearchSuggestionsFrame} from '@/components/luma/google-search-suggestions-frame';
const html='<style>.chip{color:green}</style><a target="_blank" href="https://www.google.com/search?q=public">Original label</a>';
const payload=()=>({display_status:'LIVE',result:{provider:'gemini_google_search',status:'COMPLETED',provider_display_artifact:{provider:'gemini_google_search',provenance:'AUTHENTICATED_GOOGLE_PROVIDER',retention:'TRANSIENT_NON_PERSISTABLE_NON_REUSABLE',search_suggestions_html:[html]}}});
const auth={token:async()=> 'synthetic'} as AuthClient;
afterEach(()=>{cleanup();localStorage.clear();sessionStorage.clear();vi.restoreAllMocks();});
it('only authenticated research delivery admits intact opaque HTML',async()=>{
 const data=payload();const request=vi.fn(async()=>new Response(JSON.stringify(data),{status:200}));
 const api=new ControlPlaneClient(auth,'http://127.0.0.1:8770',request);
 const delivery=await api.call<ReturnType<typeof payload>>('/v1/research/'+'b'.repeat(32));
 const {container}=render(<GoogleSearchSuggestionsFrame result={delivery.result}/>);
 const frame=screen.getByTitle('Google Search Suggestions 1');expect(frame.getAttribute('srcdoc')).toBe(html);
 expect(frame.getAttribute('sandbox')).toBe('allow-popups allow-popups-to-escape-sandbox');
 expect(container.querySelector('a')).toBeNull();expect(container.querySelector('script')).toBeNull();
 expect(localStorage.length+sessionStorage.length).toBe(0);expect(request).toHaveBeenCalledTimes(1);
});
it('arbitrary user or restored database-shaped HTML has no trust',()=>{
 render(<GoogleSearchSuggestionsFrame result={payload().result}/>);expect(screen.queryByTitle('Google Search Suggestions 1')).toBeNull();
});
it('another provider cannot acquire Google trust',async()=>{
 const data=payload();data.result.provider='other';
 const api=new ControlPlaneClient(auth,'http://127.0.0.1:8770',async()=>new Response(JSON.stringify(data)));
 const delivery=await api.call<ReturnType<typeof payload>>('/v1/research/'+'b'.repeat(32));
 render(<GoogleSearchSuggestionsFrame result={delivery.result}/>);expect(screen.queryByTitle('Google Search Suggestions 1')).toBeNull();
});
it('create response cannot inject display HTML',async()=>{
 const api=new ControlPlaneClient(auth,'http://127.0.0.1:8770',async()=>new Response(JSON.stringify(payload())));
 const d=await api.call<ReturnType<typeof payload>>('/v1/research',{});
 render(<GoogleSearchSuggestionsFrame result={d.result}/>);expect(screen.queryByTitle('Google Search Suggestions 1')).toBeNull();
});
it('metadata-only refresh cannot reconstruct suggestions or trigger search',async()=>{
 const request=vi.fn(async(_input:RequestInfo|URL,_init?:RequestInit)=>new Response(JSON.stringify({display_status:'GROUNDED_RESULT_NOT_RETAINED',result:null})));
 const api=new ControlPlaneClient(auth,'http://127.0.0.1:8770',request);const d=await api.call<{result:null}>('/v1/research/'+'b'.repeat(32));
 expect(d.result).toBeNull();expect(request).toHaveBeenCalledTimes(1);expect(request.mock.calls[0][1]?.method).toBe('GET');
});
