import {useCallback,useEffect,useRef,useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {useAuth} from '../auth/context';
import {ApiError} from '../auth/client';
import {CodexTaskComposer} from './CodexTaskComposer';
interface Proposal {envelope:{tool_id:string;operation:string;target_device_id?:string;parameters:Record<string,unknown>;resource?:string};risk:string}
interface Task {task_id:string;project_id:string;task_type:string;input:string;status:string;summary?:string;proposal_hash?:string;effective_risk?:string;expires_at:string;action_request_id?:string;job_id?:string;decision?:string;codex_result?:{summary?:string;code:string;changed_files:string[];validation_pass:boolean;duration_ms:number};proposal?:Proposal;timeline:{event_type:string;timestamp:string;result:string}[]}
interface Device {device_id:string;name:string;status:string;eligible:boolean;active?:boolean}
const button='rounded-lg border border-cyan-800 px-4 py-3 disabled:opacity-40';
export function RemoteTasksPanel({approvals=false}:{approvals?:boolean}){
 const {deviceApi:api,state,reauthenticate}=useAuth();const {taskId}=useParams();
 const [rows,setRows]=useState<Task[]>([]);const [devices,setDevices]=useState<Device[]>([]);const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [input,setInput]=useState('');const [type,setType]=useState('ANALYTICAL');const [target,setTarget]=useState('');const [operation,setOperation]=useState('record');const [high,setHigh]=useState<Record<string,boolean>>({});
 const [page,setPage]=useState(0);
 const [decisionErrors,setDecisionErrors]=useState<Record<string,string>>({});
 const key=useRef(crypto.randomUUID().replace(/-/g,''));const generation=useRef(0);const mutation=useRef(false);
 const refreshRunning=useRef(false);
 const refresh=useCallback(async()=>{
  if(!api||state!=='AUTHENTICATED'||refreshRunning.current)return;
  refreshRunning.current=true;
  try {
  const gen=generation.current;
  const data=taskId?[await api.call<Task>('/v1/tasks/'+encodeURIComponent(taskId))]:page?await api.call<Task[]>('/v1/task-pages',{offset:page*50,limit:50,approvals}):await api.call<Task[]>(approvals?'/v1/remote-approvals':'/v1/tasks');
  if(gen===generation.current)setRows(data);
  } finally {refreshRunning.current=false;}
 },[api,state,taskId,approvals,page]);
 useEffect(()=>{
  const run=++generation.current;setRows([]);setDevices([]);
  if(state!=='AUTHENTICATED')return;
  let alive=true;
  void refresh().catch(()=>{if(alive)setError('Não foi possível carregar o estado canônico. Tente atualizar.');});
  void api?.call<Device[]>('/v1/remote-task-devices').then(d=>{if(alive)setDevices(d);}).catch(()=>{});
  const timer=setInterval(()=>{if(mutation.current)return;void refresh().catch(()=>{if(alive)setError('Conexão indisponível. O estado mostrado pode estar desatualizado.');});},5000);
  return()=>{alive=false;generation.current=run+1;clearInterval(timer);};
 },[api,state,refresh]);
 async function mutate(fn:()=>Promise<unknown>,tid?:string){
  if(mutation.current)return;mutation.current=true;setBusy(true);setError('');
  const run=tid?++generation.current:generation.current;
  if(tid)setDecisionErrors(previous=>({...previous,[tid]:''}));
  function applyCanonical(value:unknown){
   if(run!==generation.current||!tid||!value||typeof value!=='object')return false;
   const candidate=value as Partial<Task>;
   if(candidate.task_id!==tid||typeof candidate.status!=='string'||!Array.isArray(candidate.timeline))return false;
   setRows(previous=>previous.map(t=>t.task_id===tid?candidate as Task:t));
   if(candidate.status!=='WAITING_AUTHORIZATION')setDecisionErrors(previous=>({...previous,[tid!]:''}));
   return true;
  }
  try{
   const response=await fn();const confirmed=applyCanonical(response);
   try{await refresh();}catch{if(!confirmed)setError('A solicitação foi recebida, mas a leitura do estado falhou. Atualize o estado.');}
  }
  catch(e){
   if(run!==generation.current)return;
   const message=e instanceof ApiError&&e.code==='RECENT_AUTH_REQUIRED'?'Confirme sua identidade Google antes de aprovar. A aprovação ainda não foi registrada.':e instanceof ApiError&&['CODEX_WORKSPACE_CHANGED','CODEX_MAPPING_CHANGED','CODEX_BINARY_CHANGED'].includes(e.code||'')?'O workspace ou o executor mudou. Atualize e crie uma nova proposta; nenhuma execução foi autorizada.':e instanceof ApiError&&e.status===409?'A proposta expirou ou mudou de estado. Atualize e revise uma proposta válida.':'A resposta não chegou. Consultando o estado no servidor; não repita a aprovação enquanto aguarda.';
   if(tid){setDecisionErrors(previous=>({...previous,[tid]:message}));try{applyCanonical(await api!.call<Task>('/v1/tasks/'+tid));}catch{/* Polling reconciles without retrying the mutation. */}}
   else setError(message);
   await refresh().catch(()=>{});
  }
  finally{mutation.current=false;setBusy(false);}
 }

 return <section className="space-y-6 p-4 md:p-6" aria-label={approvals?'Aprovações remotas':'Tarefas remotas'}>
  <header><h1 className="text-2xl font-semibold">{approvals?'Aprovações':'Tarefas'}</h1><p className="mt-2 text-sm text-muted-foreground">Controle local · aprovação por tarefa · {rows.filter(t=>t.status==='WAITING_AUTHORIZATION').length} proposta(s) aguardando decisão nesta página</p></header>
  <div className="flex flex-wrap gap-4"><button className={button} disabled={busy} onClick={()=>void refresh().catch(()=>setError('Falha ao atualizar.'))}>Atualizar estado</button><button className={button} onClick={()=>void reauthenticate()}>Confirmar identidade Google</button></div>
  {error&&<p role="alert">{error}</p>}
  {!approvals&&devices.some(d=>d.active&&!d.eligible)&&<details><summary>Preparar somente o TestTool sintético</summary><p>Este grant não aprova tarefas. Nenhuma operação real no computador será habilitada.</p>{devices.filter(d=>d.active&&!d.eligible).map(d=><button key={d.device_id} className={button} disabled={busy} onClick={()=>void mutate(async()=>{await api!.call('/v1/remote-task-devices/'+d.device_id+'/test-capability',{enabled:true,confirmation:'SYNTHETIC_TEST_ONLY'});setDevices(await api!.call<Device[]>('/v1/remote-task-devices'));})}>Permitir testes sintéticos em {d.name}</button>)}</details>}
  {!approvals&&!taskId&&<CodexTaskComposer onCreated={refresh}/>}
  {!approvals&&!taskId&&<form className="space-y-4 rounded-xl border p-4" onSubmit={e=>{e.preventDefault();void mutate(async()=>{await api!.call('/v1/tasks',{project_id:'meu-gestor',task_type:type,input,target_device_id:target||null,operation,idempotency_key:key.current});key.current=crypto.randomUUID().replace(/-/g,'');setInput('');});}}>
   <label className="block">Tipo de tarefa<select className="mt-2 block w-full rounded border bg-background p-3" value={type} onChange={e=>{setType(e.target.value);key.current=crypto.randomUUID().replace(/-/g,'');}}>{['ANALYTICAL','INFORMATIONAL','RESEARCH','PLANNING','ACTION_ORIENTED'].map(t=><option key={t}>{t}</option>)}</select></label>
   <label className="block">Descrição<textarea className="mt-2 block min-h-28 w-full rounded border bg-background p-3" maxLength={2000} value={input} onChange={e=>{setInput(e.target.value);key.current=crypto.randomUUID().replace(/-/g,'');}}/></label>
   {type!=='ACTION_ORIENTED'&&<label className="block">Computador do runtime<select className="block w-full bg-background p-3" value={target} onChange={e=>{setTarget(e.target.value);key.current=crypto.randomUUID().replace(/-/g,'');}}><option value="">Selecione para encaminhar ao runtime</option>{devices.filter(d=>d.active).map(d=><option key={d.device_id} value={d.device_id}>{d.name} · {d.status}</option>)}</select></label>}
   {type==='ACTION_ORIENTED'&&<><p>Efeito de teste no ledger sintético. A proposta exige aprovação separada.</p><label className="block">Dispositivo alvo<select className="block w-full bg-background p-3" value={target} onChange={e=>{setTarget(e.target.value);key.current=crypto.randomUUID().replace(/-/g,'');}}><option value="">Selecione um computador</option>{devices.filter(d=>d.eligible).map(d=><option key={d.device_id} value={d.device_id}>{d.name} · {d.status}</option>)}</select></label><label className="block">Operação sintética<select className="block w-full bg-background p-3" value={operation} onChange={e=>{setOperation(e.target.value);key.current=crypto.randomUUID().replace(/-/g,'');}}>{['record'].map(o=><option key={o}>{o}</option>)}</select></label></>}
   <button className={button} disabled={busy||!api||!input.trim()||(type==='ACTION_ORIENTED'&&!target)}>Criar tarefa</button>
  </form>}
  {!taskId&&<nav className="flex flex-wrap gap-4" aria-label="Páginas de tarefas"><button className={button} disabled={busy||page===0} onClick={()=>setPage(page-1)}>Página anterior</button><span>Página {page+1}</span><button className={button} disabled={busy||rows.length<50} onClick={()=>setPage(page+1)}>Próxima página</button></nav>}
  {!rows.length&&<p>{approvals?'Nenhuma aprovação registrada.':'Nenhuma tarefa registrada.'}</p>}
  <div className="grid gap-5">{rows.map(t=><article key={t.task_id} className="min-w-0 space-y-4 rounded-xl border p-5">
   <div className="flex flex-wrap justify-between gap-3"><Link to={'/tasks/'+t.task_id} className="break-all text-cyan-400">Tarefa {t.task_id.slice(0,8)}</Link><strong>{t.status}</strong></div><p className="whitespace-pre-wrap break-words">{t.input}</p><p>{t.summary}</p><p>Projeto: {t.project_id} · Risco: {t.effective_risk||'Sem ação proposta'}</p><p>Expira: {new Date(t.expires_at).toLocaleString('pt-BR')}</p>
   {t.proposal&&<><p>Ferramenta: {t.proposal.envelope.tool_id} · Operação: {t.proposal.envelope.operation}</p><p className="break-all">Dispositivo: {t.proposal.envelope.target_device_id}</p>{t.proposal.envelope.tool_id==='codex-executor'?<div className="space-y-2"><p>Workspace autorizado: {String(t.proposal.envelope.parameters.workspace_id)}</p><p>Efeito real limitado ao workspace. Uma execução; sem Git write, instalação ou rede da tarefa.</p><p>Limites: {String(t.proposal.envelope.parameters.max_changed_files)} arquivo(s) · {String(t.proposal.envelope.parameters.max_duration)} segundos.</p></div>:<p>Escopo: uma execução da ação exata até a expiração. Consequência prevista: registro sintético local.</p>}<details><summary>Parâmetros e detalhes técnicos</summary><pre className="whitespace-pre-wrap break-all">{JSON.stringify(t.proposal.envelope,null,2)}</pre><p className="break-all">Digest: {t.proposal_hash}</p></details></>}
   {t.status==='CANCELLING'&&<p>Aguardando confirmação de encerramento pelo PC. O processo ainda não foi confirmado como encerrado.</p>}
   {t.codex_result&&<div className="space-y-2"><p>Resultado Codex: {t.codex_result.code}</p>{t.codex_result.summary&&<p className="whitespace-pre-wrap break-words">{t.codex_result.summary}</p>}<p>Validação local: {t.codex_result.validation_pass?'PASS':'FAIL'}</p><p>Duração: {t.codex_result.duration_ms} ms</p><ul>{t.codex_result.changed_files.map(path=><li key={path}>{path}</li>)}</ul></div>}
   {t.status==='WAITING_AUTHORIZATION'&&decisionErrors[t.task_id]&&<div className="space-y-3 rounded-lg border border-amber-600 p-3"><p role="alert">{decisionErrors[t.task_id]}</p>{decisionErrors[t.task_id].startsWith('Confirme sua identidade Google')&&<><button className={button} disabled={busy} onClick={()=>{void (async()=>{await reauthenticate();await refresh();setDecisionErrors(previous=>({...previous,[t.task_id]:''}));})().catch(()=>setError('Não foi possível atualizar a identidade e o estado.'));}}>Confirmar identidade para esta proposta</button><p className="text-sm">Depois da confirmação, revise a proposta e clique novamente em aprovar. Nenhuma ação é aprovada automaticamente.</p></>}</div>}
   {t.effective_risk==='HIGH'&&t.status==='WAITING_AUTHORIZATION'&&<label className="flex gap-3"><input type="checkbox" checked={!!high[t.task_id]} onChange={e=>setHigh({...high,[t.task_id]:e.target.checked})}/>Confirmo a ação exata de risco HIGH e seu dispositivo alvo.</label>}
   <div className="flex flex-wrap gap-6">{t.status==='WAITING_AUTHORIZATION'&&<><button className={button} disabled={busy||t.effective_risk==='CRITICAL'||(t.effective_risk==='HIGH'&&!high[t.task_id])} onClick={()=>void mutate(()=>api!.call('/v1/tasks/'+t.task_id+'/decision',{decision:'APPROVE',proposal_hash:t.proposal_hash,...(high[t.task_id]?{confirmation:'AUTHORIZE_EXACT_ACTION'}:{})}),t.task_id)}>Aprovar proposta</button><button className={button} disabled={busy} onClick={()=>void mutate(()=>api!.call('/v1/tasks/'+t.task_id+'/decision',{decision:'REJECT',proposal_hash:t.proposal_hash}),t.task_id)}>Rejeitar proposta</button></>}
   {!['COMPLETED','CANCELLED','REJECTED','EXPIRED','BLOCKED','FAILED','CANCELLING'].includes(t.status)&&<button className={button} disabled={busy} onClick={()=>void mutate(()=>api!.call('/v1/tasks/'+t.task_id+'/cancel',{}),t.task_id)}>Cancelar tarefa</button>}
   {t.decision==='APPROVE'&&!['COMPLETED','CANCELLED','EXPIRED','BLOCKED','FAILED','CANCELLING'].includes(t.status)&&<button className={button} disabled={busy} onClick={()=>void mutate(()=>api!.call('/v1/tasks/'+t.task_id+'/revoke',{}),t.task_id)}>Revogar autorização</button>}</div>
   <details><summary>Histórico da tarefa</summary><ol className="space-y-2">{t.timeline.map((e,i)=><li key={i}>{e.event_type} · {e.result} · {new Date(e.timestamp).toLocaleString('pt-BR')}</li>)}</ol></details>
  </article>)}</div>
 </section>;
}
