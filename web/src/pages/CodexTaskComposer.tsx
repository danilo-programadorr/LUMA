import {useCallback,useEffect,useRef,useState} from 'react';
import {useAuth} from '../auth/context';
import {ApiError} from '../auth/client';
interface Workspace {
 workspace_id:string;project_id:string;target_device_id:string;display_name:string;
 enabled:boolean;mapping_version:number;mapping_fingerprint:string;snapshot_hash:string;
 allowed_execution_modes:string[];binary_sha256:string;model:string;
}
const button='rounded-lg border border-cyan-800 px-4 py-3 disabled:opacity-40';
export function CodexTaskComposer({onCreated}:{onCreated:()=>Promise<unknown>}){
 const {deviceApi:api,state,reauthenticate}=useAuth();
 const [rows,setRows]=useState<Workspace[]>([]);const [selected,setSelected]=useState('');
 const [confirmed,setConfirmed]=useState(false);const [mode,setMode]=useState('READ_ONLY');
 const [input,setInput]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const [recent,setRecent]=useState(false);const key=useRef(crypto.randomUUID().replace(/-/g,''));
 const run=useRef(0);const active=useRef(false);
 const load=useCallback(async()=>{
  if(!api||state!=='AUTHENTICATED')return [];
  const data=await api.call<Workspace[]>('/v1/codex/workspaces');
  return Array.isArray(data)?data.filter(w=>typeof w?.workspace_id==='string'&&typeof w?.target_device_id==='string'):[];
 },[api,state]);
 useEffect(()=>{
  const generation=++run.current;let disposed=false;setRows([]);setSelected('');setConfirmed(false);
  void load().then(data=>{if(!disposed&&run.current===generation){setRows(data);setSelected(data[0]?.workspace_id||'');}}).catch(()=>{/* Feature absent or disabled: no pretend capability. */});
  return()=>{disposed=true;};
 },[load]);
 const workspace=rows.find(w=>w.workspace_id===selected);
 function manifest(w:Workspace):Workspace {
  return {workspace_id:w.workspace_id,project_id:w.project_id,target_device_id:w.target_device_id,display_name:w.display_name,enabled:true,mapping_version:w.mapping_version,mapping_fingerprint:w.mapping_fingerprint,snapshot_hash:w.snapshot_hash,allowed_execution_modes:w.allowed_execution_modes,binary_sha256:w.binary_sha256,model:w.model};
 }
 async function mutate(fn:()=>Promise<void>){
  if(active.current)return;active.current=true;setBusy(true);setError('');setRecent(false);
  try{await fn();}
  catch(e){if(e instanceof ApiError&&e.code==='RECENT_AUTH_REQUIRED'){setRecent(true);setError('Confirme sua identidade e revise novamente. Nenhuma tarefa será aprovada automaticamente.');}else if(e instanceof ApiError&&['CODEX_WORKSPACE_CHANGED','CODEX_MAPPING_CHANGED','CODEX_BINARY_CHANGED'].includes(e.code||''))setError('O workspace ou o executor mudou. Atualize os workspaces e prepare uma nova proposta.');else setError('Não foi possível confirmar a operação. Consulte o estado antes de repetir.');}
  finally{active.current=false;setBusy(false);}
 }
 if(state!=='AUTHENTICATED'||!workspace)return null;
 return <section aria-label="Codex no PC" className="space-y-4 rounded-xl border border-cyan-900 p-5">
  <button className={button} disabled={busy} onClick={()=>void mutate(async()=>{const generation=run.current;const next=await load();if(generation===run.current)setRows(next);})}>Atualizar workspaces Codex</button>
  <h2 className="text-xl font-semibold">Codex no PC · execução autorizada</h2>
  <p>Workspace descoberto pelo dispositivo. Permitir o uso não aprova tarefas; cada execução exige proposta e decisão próprias.</p>
  <label className="block">Workspace Codex<select className="block w-full rounded border bg-background p-3" value={selected} onChange={e=>{setSelected(e.target.value);setConfirmed(false);setMode('READ_ONLY');key.current=crypto.randomUUID().replace(/-/g,'');}}>{rows.map(w=><option key={w.workspace_id} value={w.workspace_id}>{w.display_name}</option>)}</select></label>
  <p className="break-all">Dispositivo: {workspace.target_device_id} · Modelo: {workspace.model||'Não confirmado'}</p>
  <p className="break-all">Workspace: {workspace.workspace_id} · Mapeamento v{workspace.mapping_version}</p>
  {!workspace.enabled?<div className="space-y-4">
   <label className="flex gap-3"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Revisei o dispositivo, o workspace sintético e os modos permitidos: {workspace.allowed_execution_modes.join(', ')}.</label>
   <button className={button} disabled={busy||!confirmed||!workspace.model||/^0+$/.test(workspace.binary_sha256)} onClick={()=>void mutate(async()=>{
    const generation=run.current;
    await api!.call('/v1/codex/devices/'+workspace.target_device_id+'/grant',{enabled:true,confirmation:'CODEX_EXECUTION_ONE_SHOT_ONLY'});
    await api!.call('/v1/codex/workspaces',{manifest:manifest(workspace),confirmation:'APPROVE_CODEX_WORKSPACE'});
    const next=await load();if(generation===run.current){setRows(next);setConfirmed(false);}
   })}>Permitir Codex neste workspace</button>
  </div>:<form className="space-y-4" onSubmit={e=>{e.preventDefault();void mutate(async()=>{
   const profile={workspace_id:workspace.workspace_id,mapping_version:workspace.mapping_version,mapping_fingerprint:workspace.mapping_fingerprint,snapshot_hash:workspace.snapshot_hash,task_prompt:input,execution_mode:mode,read_paths:['README.md','src/calc.py','tests/test_calc.py'],allowed_paths:mode==='WORKSPACE_WRITE'?['src/calc.py']:[],denied_paths:['denied'],max_changed_files:1,max_changed_bytes:8192,max_duration:120,max_output_bytes:32768,binary_sha256:workspace.binary_sha256,model:workspace.model};
   await api!.call('/v1/tasks',{project_id:workspace.project_id,task_type:'ACTION_ORIENTED',executor:'CODEX',codex_profile:profile,input,target_device_id:workspace.target_device_id,idempotency_key:key.current});
   key.current=crypto.randomUUID().replace(/-/g,'');setInput('');await onCreated();
  });}}>
   <p>Fixture de aceitação local. Sem Git write, instalação ou rede da tarefa. O cliente Codex utiliza a conexão do provider e pode consumir a franquia da conta; custo não confirmado aqui.</p>
   <label className="block">Modo Codex<select className="block w-full rounded border bg-background p-3" value={mode} onChange={e=>{setMode(e.target.value);key.current=crypto.randomUUID().replace(/-/g,'');}}>{workspace.allowed_execution_modes.map(m=><option key={m}>{m}</option>)}</select></label>
   <p>{mode==='READ_ONLY'?'Somente leitura; zero arquivos alterados.':'Escrita permitida somente em src/calc.py; máximo 1 arquivo e 8.192 bytes antes + depois.'} Prazo de execução: até 120 segundos.</p>
   <label className="block">Tarefa técnica limitada<textarea className="block min-h-28 w-full rounded border bg-background p-3" maxLength={2000} value={input} onChange={e=>{setInput(e.target.value);key.current=crypto.randomUUID().replace(/-/g,'');}}/></label>
   <button className={button} disabled={busy||!input.trim()}>Criar proposta Codex</button>
  </form>}
  {error&&<p role="alert">{error}</p>}
  {recent&&<button className={button} disabled={busy} onClick={()=>void reauthenticate().then(()=>{setRecent(false);setError('Identidade confirmada. Revise o workspace e repita somente a operação desejada.');}).catch(()=>setError('Não foi possível confirmar a identidade.'))}>Confirmar identidade para Codex</button>}
 </section>;
}
