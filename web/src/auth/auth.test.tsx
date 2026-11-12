import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthContext, safeRedirect, protectedPaths, type AuthState } from './context';
import { AuthScreen, AuthGuard } from './AuthScreen';
import { AuthProvider } from './AuthProvider';
import { ApiError, ControlPlaneClient, type AuthClient } from './client';
import { agents,approvals,devices,tools } from '@/data/luma-data';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const owner={ internal_owner_id:'local-owner',provider:'google.com',status:'ACTIVE',auth_time:123 };
function fixture() {
  let listener=(signed:boolean)=>{ void signed; };
  const client:AuthClient={ observe: fn=>{ listener=fn; fn(false); return ()=>{}; },login:async()=>listener(true),logout:async()=>listener(false),token:vi.fn(async()=> 'synthetic-fixture'),reauthenticate:async()=>{} };
  return client;
}
function stateView(state:AuthState, initial='/login') {
  const logout=vi.fn(async()=>{});const login=vi.fn(async()=>{});
  render(<AuthContext.Provider value={{state,owner:state==='AUTHENTICATED'?owner:null,logout,login,bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><MemoryRouter initialEntries={[initial]}><Routes><Route path="/login" element={<AuthScreen/>}/><Route path="*" element={<AuthGuard><div>Protected dashboard</div></AuthGuard>}/></Routes></MemoryRouter></AuthContext.Provider>);
  return {login,logout};
}
it('login screen',()=>{stateView('SIGNED_OUT');expect(screen.getByText('Acesso restrito ao proprietário.')).toBeTruthy();});
it.each(['INITIALIZING','AUTHENTICATING'] as AuthState[])('busy %s',(state)=>{stateView(state);expect((screen.getByRole('button',{name:'Entrar com Google'}) as HTMLButtonElement).disabled).toBe(true);expect(screen.queryByText('Protected dashboard')).toBeNull();});
it('login invokes official boundary',()=>{const {login}=stateView('SIGNED_OUT');fireEvent.click(screen.getByRole('button',{name:'Entrar com Google'}));expect(login).toHaveBeenCalledOnce();});
it('authenticated route',()=>{stateView('AUTHENTICATED','/approvals');expect(screen.getByText('Protected dashboard')).toBeTruthy();});
it('forbidden',()=>{stateView('FORBIDDEN');expect(screen.getByText('Acesso não autorizado')).toBeTruthy();});
it('session expired',()=>{stateView('SESSION_EXPIRED');expect(screen.getByText(/Sessão expirada/)).toBeTruthy();});
it('offline distinct',()=>{stateView('ERROR');expect(screen.getByText(/Verifique a configuração e a conexão/)).toBeTruthy();});
it.each(protectedPaths)('guard %s',(path)=>{stateView('SIGNED_OUT',path);expect(screen.queryByText('Protected dashboard')).toBeNull();expect(screen.getByRole('button',{name:'Entrar com Google'})).toBeTruthy();});
it('safe deep link',()=>expect(safeRedirect('/approvals')).toBe('/approvals'));
it.each(['https://evil.example','//evil.example','/\\evil.example','/login','javascript:alert(1)','/approvals?next=https://evil.example'])('unsafe redirect %s',(path)=>expect(safeRedirect(path)).toBe('/'));
it('refresh 401 only once',async()=>{const a=fixture();const request=vi.fn().mockResolvedValueOnce(new Response('',{status:401})).mockResolvedValueOnce(new Response(JSON.stringify(owner),{status:200}));const api=new ControlPlaneClient(a,'http://localhost:8770',request);expect(await api.me()).toEqual(owner);expect(a.token).toHaveBeenNthCalledWith(2,true);expect(request).toHaveBeenCalledTimes(2);});
it('persistent 401',async()=>{const request=vi.fn().mockResolvedValue(new Response('',{status:401}));await expect(new ControlPlaneClient(fixture(),'http://localhost:8770',request).me()).rejects.toMatchObject({status:401});expect(request).toHaveBeenCalledTimes(2);});
it('403 no refresh loop',async()=>{const request=vi.fn().mockResolvedValue(new Response('',{status:403}));await expect(new ControlPlaneClient(fixture(),'http://localhost:8770',request).me()).rejects.toMatchObject({status:403});expect(request).toHaveBeenCalledOnce();});
it('network error',async()=>{await expect(new ControlPlaneClient(fixture(),'http://localhost:8770',vi.fn().mockRejectedValue(new Error())).me()).rejects.toEqual(new ApiError(0));});
it('unsafe API origin',()=>expect(()=>new ControlPlaneClient(fixture(),'http://external.example')).toThrow());
it('logout clears protected page',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify(owner))));
 const a=fixture();render(<AuthProvider testClient={a}><MemoryRouter><Routes><Route path="/login" element={<AuthScreen/>}/><Route path="*" element={<AuthGuard><button onClick={()=>void a.logout()}>Logout fixture</button></AuthGuard>}/></Routes></MemoryRouter></AuthProvider>);
 await waitFor(()=>expect(screen.getByText('Entrar com Google')).toBeTruthy());fireEvent.click(screen.getByText('Entrar com Google'));
 await waitFor(()=>expect(screen.getByText('Logout fixture')).toBeTruthy());fireEvent.click(screen.getByText('Logout fixture'));
 await waitFor(()=>expect(screen.getByText('Entrar com Google')).toBeTruthy());
});
it('pilot has no fabricated activity',()=>{expect(approvals).toEqual([]);expect(agents.every(x=>x.status==='offline')).toBe(true);expect(devices.every(x=>x.status==='offline')).toBe(true);expect(tools.every(x=>x.status==='planned')).toBe(true);});

it('sanitized public health',async()=>{const request=vi.fn().mockResolvedValue(new Response(JSON.stringify({mode:'CONTROL_PLANE',version:'0.6.0rc1',database_status:'AVAILABLE',private_field:'excluded'})));const result=await new ControlPlaneClient(fixture(),'http://localhost:8770',request).health();expect(result).toEqual({mode:'CONTROL_PLANE',version:'0.6.0rc1',database_status:'AVAILABLE'});expect(request.mock.calls[0][1].headers).toBeUndefined();});

it('token refresh notification does not restart rejected session validation',async()=>{
 let listener=(signed:boolean)=>{void signed;};
 const logout=vi.fn(async()=>listener(false));
 let notifications=0;
 const a:AuthClient={observe:fn=>{listener=fn;fn(true);return()=>{};},login:async()=>{},logout,reauthenticate:async()=>{},token:async(force)=>{if(force && notifications++<3)listener(true);return 'synthetic-fixture';}};
 const request=vi.fn(async()=>new Response('',{status:401}));vi.stubGlobal('fetch',request);
 render(<AuthProvider testClient={a}><MemoryRouter><AuthScreen/></MemoryRouter></AuthProvider>);
 await waitFor(()=>expect(screen.getByText(/Sessão expirada/)).toBeTruthy());
 expect(request).toHaveBeenCalledTimes(2);expect(logout).toHaveBeenCalledOnce();
});
