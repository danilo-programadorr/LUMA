import { useCallback, useEffect, useState } from 'react';
import { MonitorSmartphone, Radio, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/auth/context';
import { ApiError } from '@/auth/client';
import { PageHeader } from '@/components/luma/page-header';
import { Panel, PanelHeader } from '@/components/luma/panel';
import { ToneChip } from '@/components/luma/status-indicator';
import DevicesDemoPage from './DevicesDemoPage';
interface Device { device_id:string; display_name:string; platform:string; status:string; online:boolean; connection_status:string; enrollment_status:string; key_fingerprint:string; created_at:string; runtime_version:string|null; last_seen_at:string|null; capabilities:string[] }
interface Enrollment { challenge_id:string; code:string; expires_at:number }
export function ConnectedDevices() {
  const {deviceApi,reauthenticate}=useAuth();
  const [devices,setDevices]=useState<Device[]>([]);const [enrollment,setEnrollment]=useState<Enrollment|null>(null);
  const [name,setName]=useState('Meu PC');const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
  const [clock,setClock]=useState(Date.now());
  const refresh=useCallback(async()=>{
    if(!deviceApi)return;
    try { setDevices(await deviceApi.call<Device[]>('/v1/devices')); }
    catch { setMessage('Não foi possível consultar os dispositivos.'); }
  },[deviceApi]);
  useEffect(()=>{void refresh();const timer=setInterval(()=>{setClock(Date.now());void refresh();},5000);return()=>clearInterval(timer);},[refresh]);
  useEffect(()=>{if(enrollment && clock>=enrollment.expires_at*1000){setEnrollment(null);setMessage('Enrollment expirado. Gere um novo código.');}},[clock,enrollment]);
  const act=async(fn:()=>Promise<unknown>)=>{setBusy(true);setMessage('');try{await fn();await refresh();}catch(e){setMessage(e instanceof ApiError && e.status===403?'Operação negada. Confirme sua identidade novamente se a autenticação estiver antiga.':'Não foi possível concluir a operação.');}finally{setBusy(false);}};
  if(!deviceApi)return <p>Canal de dispositivos indisponível nesta sessão.</p>;
  const deviceCard=(d:Device)=>(<Panel key={d.device_id} className="animate-fade-up"><PanelHeader icon={Radio} title={d.display_name} hint={d.platform}/><div className="space-y-4 p-5 text-sm leading-relaxed sm:p-6">
      <ToneChip tone={d.online?'green':'slate'}>{d.status==='PENDING_ENROLLMENT'?'PENDING_ENROLLMENT':d.status==='REVOKED'?'REVOKED':d.connection_status}</ToneChip>
      <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
        <div><dt className="text-xs text-muted-foreground">Vínculo</dt><dd className="mt-1 font-medium">{d.enrollment_status}</dd></div>
        <div><dt className="text-xs text-muted-foreground">Último sinal</dt><dd className="mt-1">{d.last_seen_at?new Date(d.last_seen_at).toLocaleString('pt-BR'):'Nenhum heartbeat recebido'}</dd></div>
        <div><dt className="text-xs text-muted-foreground">Runtime</dt><dd className="mt-1">{d.runtime_version || 'Não informado'}</dd></div>
        <div><dt className="text-xs text-muted-foreground">Solicitado</dt><dd className="mt-1">{new Date(d.created_at).toLocaleString('pt-BR')}</dd></div>
      </dl>
      <details className="rounded-lg border border-hud-soft px-3 py-2.5"><summary className="cursor-pointer text-xs text-muted-foreground">Conferir fingerprint completo <span className="ml-2 hidden font-mono sm:inline">{d.key_fingerprint.slice(0,12)}…{d.key_fingerprint.slice(-8)}</span></summary><code className="mt-3 block break-all text-xs">{d.key_fingerprint}</code></details>
      <p className="break-words text-xs leading-relaxed text-muted-foreground">{d.capabilities.join(' · ')}</p>
      {d.status==='PENDING_ENROLLMENT' && <button disabled={busy} className="rounded border border-primary p-2" onClick={()=>{if(window.confirm('O fingerprint exibido corresponde ao agente no seu PC?'))void act(async()=>{await deviceApi.call('/v1/devices/'+d.device_id+'/approve',{fingerprint:d.key_fingerprint});setEnrollment(null);});}}>Aprovar dispositivo</button>}
      {d.status!=='REVOKED' && <button disabled={busy} className="mr-2 mt-2 min-h-10 rounded-lg border border-hud-soft px-3 py-2" onClick={()=>{if(window.confirm('Revogar este dispositivo e bloquear o canal?'))void act(()=>deviceApi.call('/v1/devices/'+d.device_id+'/revoke',{}));}}>Revogar</button>}
      <button disabled={busy} className="mr-2 mt-2 min-h-10 rounded-lg px-3 py-2 text-muted-foreground" onClick={()=>{const value=window.prompt('Novo nome',d.display_name);if(value?.trim())void act(()=>deviceApi.call('/v1/devices/'+d.device_id+'/rename',{display_name:value.trim()}));}}>Renomear</button>
      {d.status!=='PENDING_ENROLLMENT' && d.status!=='REVOKED' && <button disabled={busy} className="mt-3 block min-h-10 w-full rounded-lg border border-hud-soft px-3 py-2.5" onClick={()=>{if(window.confirm('Autorizar um único teste sintético, sem efeitos externos, neste PC?'))void act(()=>deviceApi.call('/v1/devices/'+d.device_id+'/test-job',{confirmation:'AUTHORIZE_SYNTHETIC_TEST_ONLY'}));}}>Autorizar teste sintético</button>}
    </div></Panel>);
  return <div className="space-y-6">
    <PageHeader eyebrow="Infraestrutura" icon={MonitorSmartphone} title="Dispositivos" description="Identidade do PC, vínculo aprovado pelo proprietário e comunicação iniciada pelo dispositivo." meta={<ToneChip tone="cyan">Execução externa desabilitada</ToneChip>}/>
    {devices.some(d=>d.status!=='REVOKED') && <section aria-label="Dispositivos atuais" className="space-y-4"><h2 className="sr-only">Seus computadores</h2><div className={devices.filter(d=>d.status!=='REVOKED').length>1?"grid items-start gap-5 md:grid-cols-2":"grid gap-5"}>{devices.filter(d=>d.status!=='REVOKED').map(deviceCard)}</div></section>}
    <details className="rounded-xl border border-hud-soft bg-void/40"><summary className="cursor-pointer px-5 py-4 text-sm font-medium text-primary">Vincular novo computador</summary><Panel><PanelHeader icon={ShieldCheck} title="Adicionar computador" hint="O vínculo exige sua confirmação do fingerprint."/>
      <div className="grid items-end gap-4 p-5 sm:grid-cols-2 lg:grid-cols-[1fr_auto_auto]"><label htmlFor="device-name">Nome do dispositivo<input id="device-name" className="mt-2 h-11 w-full rounded-lg border border-hud-soft bg-void px-3 text-sm" value={name} onChange={e=>setName(e.target.value)} maxLength={80}/></label>
        <button disabled={busy || !name.trim()} className="min-h-11 rounded-lg border border-primary bg-primary/10 px-4 py-2.5 text-sm" onClick={()=>void act(async()=>setEnrollment(await deviceApi.call<Enrollment>('/v1/devices/enrollment/start',{display_name:name.trim()})))}>Adicionar dispositivo</button>
        <button className="min-h-11 rounded-lg border border-hud-soft px-4 py-2.5 text-sm" onClick={()=>void reauthenticate()}>Confirmar identidade novamente</button>
        {enrollment && <div className="space-y-3 rounded-lg border border-primary p-4 sm:col-span-2 lg:col-span-3"><p>Execute no PowerShell do PC:</p><code className="block break-all">.\.venv\Scripts\python.exe -m device_agent enroll</code><p>Na entrada oculta, cole o código abaixo. Não envie em mensagens nem relatórios.</p><input aria-label="Código de enrollment" type="password" readOnly className="w-full bg-void p-2" value={enrollment.challenge_id+':'+enrollment.code}/><button onClick={()=>void navigator.clipboard.writeText(enrollment.challenge_id+':'+enrollment.code).then(()=>setMessage('Código copiado. Cole somente na entrada oculta do agente.')).catch(()=>setMessage('Selecione e copie o campo do código.'))}>Copiar código</button><p>Validade: {Math.max(0,Math.ceil((enrollment.expires_at*1000-clock)/1000))} segundos. Após a solicitação local, confira o fingerprint antes de aprovar.</p><button onClick={()=>setEnrollment(null)}>Ocultar código</button></div>}

      </div>
    </Panel></details>
    {message && <p role="status" className="rounded-lg border border-hud-soft p-4 text-sm">{message}</p>}
    {devices.some(d=>d.status==='REVOKED') && <details className="rounded-xl border border-hud-soft bg-void/40"><summary className="cursor-pointer px-5 py-4 text-sm text-muted-foreground">Dispositivos revogados ({devices.filter(d=>d.status==='REVOKED').length})</summary><div className="space-y-4 border-t border-hud-soft p-4 sm:p-5"><p className="text-sm text-muted-foreground">Histórico de vínculos encerrados. Estes dispositivos não recebem solicitações.</p><div className="grid items-start gap-5 md:grid-cols-2">{devices.filter(d=>d.status==='REVOKED').map(deviceCard)}</div></div></details>}

    {!devices.length && <p>Nenhum dispositivo vinculado.</p>}
  </div>;
}
export default function DevicesPage(){return import.meta.env.VITE_DATA_MODE==='DEMO'?<DevicesDemoPage/>:<ConnectedDevices/>;}
