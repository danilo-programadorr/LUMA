import { afterEach, expect, it, vi } from 'vitest';
import { cleanup,fireEvent,render,screen,waitFor } from '@testing-library/react';
import { AuthContext } from '@/auth/context';
import { ControlPlaneClient } from '@/auth/client';
import { ConnectedDevices } from './DevicesPage';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
const device={device_id:'a'.repeat(32),display_name:'Synthetic PC',platform:'WINDOWS',status:'PENDING_ENROLLMENT',online:false,connection_status:'OFFLINE',enrollment_status:'AWAITING_OWNER',key_fingerprint:'b'.repeat(64),created_at:new Date().toISOString(),last_seen_at:null,runtime_version:null,capabilities:['DEVICE_HEARTBEAT','OUTBOUND_POLLING']};
function setup(rows:object[]=[device],response:object={}){
 const call=vi.fn(async(path:string)=>path==='/v1/devices'?rows:response);
 const api={call} as unknown as ControlPlaneClient;
 render(<AuthContext.Provider value={{state:'AUTHENTICATED',owner:null,deviceApi:api,login:async()=>{},logout:async()=>{},bootstrap:async()=>{},refresh:async()=>{},reauthenticate:async()=>{}}}><ConnectedDevices/></AuthContext.Provider>);return call;
}
it('lists real pending device and fingerprint without private key',async()=>{setup();await screen.findByText('Synthetic PC');expect(screen.getByText('PENDING_ENROLLMENT')).toBeTruthy();expect(screen.getByText('b'.repeat(64))).toBeTruthy();expect(screen.queryByText('private_key')).toBeNull();});
it('requires explicit confirmation before approval',async()=>{const call=setup();vi.spyOn(window,'confirm').mockReturnValue(false);fireEvent.click(await screen.findByRole('button',{name:'Aprovar dispositivo'}));expect(call).toHaveBeenCalledTimes(1);});
it('approves exact fingerprint after confirmation',async()=>{const call=setup();vi.spyOn(window,'confirm').mockReturnValue(true);fireEvent.click(await screen.findByRole('button',{name:'Aprovar dispositivo'}));await waitFor(()=>expect(call).toHaveBeenCalledWith('/v1/devices/'+device.device_id+'/approve',{fingerprint:device.key_fingerprint}));});
it('revokes explicitly',async()=>{const call=setup();vi.spyOn(window,'confirm').mockReturnValue(true);fireEvent.click(await screen.findByRole('button',{name:'Revogar'}));await waitFor(()=>expect(call).toHaveBeenCalledWith('/v1/devices/'+device.device_id+'/revoke',{}));});
it.each([true,false])('renders server online state %s',async online=>{setup([{...device,status:online?'ACTIVE':'OFFLINE',online,connection_status:online?'ONLINE':'OFFLINE',enrollment_status:'APPROVED'}]);expect(await screen.findByText(online?'ONLINE':'OFFLINE')).toBeTruthy();});
it('expires enrollment without persisting code',async()=>{setup([],{challenge_id:'c'.repeat(32),code:'synthetic',expires_at:1});fireEvent.click(screen.getByText('Vincular novo computador'));fireEvent.click(screen.getByRole('button',{name:'Adicionar dispositivo'}));await screen.findByText('Enrollment expirado. Gere um novo código.');expect(screen.queryByLabelText('Código de enrollment')).toBeNull();});
it('empty device list',async()=>{setup([]);expect(await screen.findByText('Nenhum dispositivo vinculado.')).toBeTruthy();});
