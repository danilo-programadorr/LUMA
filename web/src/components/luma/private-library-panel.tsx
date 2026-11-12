import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {useAuth} from '@/auth/context';
import {ApiError} from '@/auth/client';

interface LibraryDevice {device_id:string;display_name:string;status:string;private_library_approved:boolean;private_library_online:boolean}
interface Source {source_id:string;project_id:string;device_id:string;title:string;content_hash:string;extension:string;byte_count:number;page_count:number;chunk_count:number;status:string}
interface Match {source_id:string;source_hash:string;chunk_id:string;excerpt:string;page:number|null;line_start:number;line_end:number;source:Source}
interface Query {query_id:string;status:string;error_code:string|null;result:{matches:Match[]}|null;display_status?:string;target_device_id?:string}
const terminal=['COMPLETED','FAILED','CANCELLED'];
const inputClass='min-h-11 w-full min-w-0 rounded-lg border border-hud-soft bg-void px-3 py-2 text-sm';
const buttonClass='min-h-11 rounded-lg border border-primary/50 bg-primary/10 px-4 py-2 text-sm text-primary disabled:opacity-40';
const runCommand=".\\scripts\\run_private_library.ps1 -Mode run";
const command=".\\scripts\\run_private_library.ps1 -Mode import -File 'C:\\caminho\\seu-documento.pdf'";
function failure(e:unknown):string {
 if(!(e instanceof ApiError))return 'Não foi possível concluir a operação.';
 const messages:Record<string,string>={LIBRARY_CAPABILITY_REQUIRED:'Autorize a biblioteca para este computador antes de consultar.',LIBRARY_SOURCE_UNAVAILABLE:'Uma fonte selecionada não está mais disponível. Revise o escopo da consulta.',LIBRARY_NO_SOURCES:'Importe um documento para este computador antes de consultar.',LIBRARY_QUERY_EXPIRED:'A consulta expirou. Confira se o agente da biblioteca está em execução.',LIBRARY_SOURCE_ARCHIVED:'A fonte foi arquivada; ela não pode ser reativada pelo agente.',LIBRARY_QUERY_LIMIT:'Há muitas consultas pendentes. Cancele uma antes de continuar.'};
 if(e.status===404)return 'Biblioteca privada ainda não habilitada neste servidor.';
 return (e.code&&messages[e.code])||(e.status===403?'A permissão atual não permite esta operação. Confirme sua identidade ou revise a autorização do PC.':e.status===0?'Não foi possível conectar ao servidor local.':'Não foi possível concluir a operação (HTTP '+e.status+').');
}

export function PrivateLibraryPanel(){
 const {deviceApi:api,reauthenticate}=useAuth();
 const [devices,setDevices]=useState<LibraryDevice[]>([]);const [sources,setSources]=useState<Source[]>([]);
 const [target,setTarget]=useState('');const [scope,setScope]=useState('ALL');const [question,setQuestion]=useState('');
 const [task,setTask]=useState<Query|null>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(true);const [busy,setBusy]=useState(false);const [guide,setGuide]=useState(false);
 const pending=useRef<{body:string;key:string}|null>(null);
 const epoch=useRef(0);
 const refresh=useCallback(async(invalidate=false)=>{
  if(!api)return;if(invalidate)epoch.current++;setLoading(true);
  try{const [d,s]=await Promise.all([api.call<LibraryDevice[]>('/v1/library/devices'),api.call<Source[]>('/v1/library/projects/meu-gestor/sources')]);setDevices(d);setSources(s);setError('');setTask(current=>{
   if(!current?.result)return current;
   const did=current.target_device_id||current.result.matches[0]?.source.device_id;
   const allowedDevice=d.find(v=>v.device_id===did&&v.private_library_approved&&!['REVOKED','PENDING_ENROLLMENT'].includes(v.status));
   const valid=!!allowedDevice&&current.result.matches.every(m=>s.some(v=>v.source_id===m.source_id&&v.content_hash===m.source_hash&&v.device_id===did&&v.project_id==='meu-gestor'&&v.status==='ACTIVE'));
   return valid?current:{...current,result:null,status:terminal.includes(current.status)?current.status:'CANCELLED',display_status:'PRIVATE_RESULT_NOT_RETAINED'};
  });}
  catch(e){epoch.current++;setDevices([]);setSources([]);setTask(null);setError(failure(e));}
  finally{setLoading(false);}
 },[api]);
 useEffect(()=>{void refresh();},[refresh]);
 useEffect(()=>{
  if(!api)return;let current=true;const started=epoch.current;const id=sessionStorage.getItem('luma.library.query_id');
  if(id&&/^[a-f0-9]{32}$/.test(id))void api.call<Query>('/v1/library/queries/'+id).then(r=>{if(current&&started===epoch.current)setTask(r);}).catch(()=>{if(current&&started===epoch.current)sessionStorage.removeItem('luma.library.query_id');});
  return()=>{current=false;};
 },[api]);
 const queryId=task?.query_id,queryStatus=task?.status;
 useEffect(()=>{
  if(!api||!queryId||!queryStatus||terminal.includes(queryStatus))return;let current=true;
  let reading=false;const timer=setInterval(()=>{if(reading)return;reading=true;const started=epoch.current;void api.call<Query>('/v1/library/queries/'+queryId).then(r=>{if(current&&started===epoch.current)setTask(r);}).catch(e=>{if(current&&started===epoch.current){setError(failure(e));setTask(r=>r?{...r,result:null}:r);}}).finally(()=>{reading=false;});},2000);
  return()=>{current=false;clearInterval(timer);};
 },[api,queryId,queryStatus]);
 useEffect(()=>{
  if(!task?.result)return;const timer=setTimeout(()=>setTask(r=>r?{...r,result:null,display_status:'PRIVATE_RESULT_NOT_RETAINED'}:r),120000);return()=>clearTimeout(timer);
 },[task?.query_id,task?.result]);
 const device=devices.find(d=>d.device_id===target);
 const visible=useMemo(()=>sources.filter(s=>s.device_id===target),[sources,target]);
 const active=useMemo(()=>visible.filter(s=>s.status==='ACTIVE'),[visible]);
 const scopeValid=scope==='ALL'||active.some(s=>s.source_id===scope);
 const running=!!task&&!terminal.includes(task.status);
 const canSearch=!!api&&!!device?.private_library_approved&&!!question.trim()&&active.length>0&&scopeValid&&!busy&&!running;
 const submit=async()=>{
  if(!api||!canSearch)return;epoch.current++;setBusy(true);setError('');setTask(null);sessionStorage.removeItem('luma.library.query_id');
  const data={project_id:'meu-gestor',target_device_id:target,query:question.trim(),source_ids:scope==='ALL'?[]:[scope]};const body=JSON.stringify(data);
  if(pending.current?.body!==body)pending.current={body,key:crypto.randomUUID().replace(/-/g,'')};
  try{const row=await api.call<Query>('/v1/library/queries',{...data,idempotency_key:pending.current.key});setTask(row);sessionStorage.setItem('luma.library.query_id',row.query_id);pending.current=null;}
  catch(e){setError(failure(e));}finally{setBusy(false);}
 };
 const grant=async(enabled=true)=>{
  if(!api||!target||!window.confirm(enabled?'Autorizar cadastro e consulta dos arquivos selecionados neste PC para o projeto Meu Gestor?':'Suspender a biblioteca neste PC? As consultas serão interrompidas e os arquivos preservados.'))return;
  setBusy(true);try{await api.call('/v1/library/devices/'+target+'/capability',{enabled});if(!enabled){epoch.current++;setTask(null);sessionStorage.removeItem('luma.library.query_id');}await refresh(true);}catch(e){setError(failure(e));}finally{setBusy(false);}
 };
 const archive=async(source:Source)=>{
  if(!api||!window.confirm('Arquivar esta fonte na biblioteca? O arquivo original e o histórico serão preservados.'))return;
  setBusy(true);try{await api.call('/v1/library/projects/meu-gestor/sources/'+source.source_id+'/archive',{});epoch.current++;setTask(r=>r?{...r,result:null}:r);await refresh(true);}catch(e){setError(failure(e));}finally{setBusy(false);}
 };
 const cancel=async()=>{
  if(!api||!task)return;try{setTask(await api.call<Query>('/v1/library/queries/'+task.query_id+'/cancel',{}));}catch(e){setError(failure(e));}
 };
 return <section aria-label="Biblioteca privada" className="min-w-0 space-y-6">
  <div className="flex flex-wrap items-start justify-between gap-4"><div className="space-y-2"><h2 className="text-xl font-semibold">Biblioteca privada</h2><p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">Consulte seus documentos no PC, com trechos e referências. A busca usa os termos do texto; não gera interpretações com IA nem envia arquivos à pesquisa web.</p><p className="text-xs text-muted-foreground">Projeto: Meu Gestor · PDF com texto, TXT e Markdown · até 8 MiB por arquivo</p></div><button className={buttonClass} onClick={()=>void refresh(true)} disabled={loading}>Atualizar fontes</button></div>
  <div className="grid gap-4 rounded-xl border border-hud-soft bg-void/50 p-4 sm:grid-cols-2 sm:p-6"><label className="space-y-2 text-sm"><span>Computador da biblioteca</span><select aria-label="Computador da biblioteca" className={inputClass} value={target} onChange={e=>{setTarget(e.target.value);setScope('ALL');}}><option value="">Selecione o computador</option>{devices.filter(d=>!['REVOKED','PENDING_ENROLLMENT'].includes(d.status)).map(d=><option key={d.device_id} value={d.device_id}>{d.display_name} · {d.private_library_online?'Biblioteca online':d.private_library_approved?'Agente offline':'Não autorizada'}</option>)}</select></label><div className="flex flex-wrap items-end gap-3">{target&&<><span className="text-sm text-muted-foreground">{active.length} documento(s) ativo(s)</span><span className="text-sm">{device?.private_library_online?'Agente da biblioteca online':'Agente da biblioteca offline'}</span></>}</div>
   {target&&device?.private_library_approved&&<button className={buttonClass} disabled={busy} onClick={()=>void grant(false)}>Suspender biblioteca neste PC</button>}
   {target&&!device?.private_library_approved&&<div className="flex flex-wrap items-center gap-3 sm:col-span-2"><button className={buttonClass} onClick={()=>void grant()} disabled={busy}>Autorizar biblioteca neste PC</button><button className={buttonClass} onClick={()=>void reauthenticate().catch(()=>setError('Não foi possível confirmar sua identidade.'))}>Confirmar identidade</button></div>}
  </div>
  <div className="space-y-3"><button className={buttonClass} onClick={()=>setGuide(!guide)} aria-expanded={guide}>Adicionar documento deste PC</button>{guide&&<div className="space-y-3 rounded-xl border border-hud-soft p-4 text-sm leading-relaxed"><p>O agente importa somente o arquivo que você selecionar. O conteúdo permanece protegido no PC; o cadastro central recebe título, hash e contagens.</p><p>Após autorizar a biblioteca para o PC, execute no PowerShell da pasta D:\projetos\luma, substituindo o caminho do exemplo:</p><code className="block break-all rounded-lg bg-void p-3">{command}</code><p>Para responder às consultas, mantenha o agente em execução:</p><code className="block break-all rounded-lg bg-void p-3">.\scripts\run_private_library.ps1 -Mode run</code><p>PDFs digitalizados sem texto, arquivos com senha, DOCX e EPUB ainda não são suportados. Nenhum arquivo é enviado ao Gemini.</p></div>}</div>
  {error&&<p role="alert" className="rounded-lg border border-warning/40 p-4 text-sm">{error}</p>}
  {loading&&<p className="text-sm text-muted-foreground">Carregando cadastro…</p>}
  {target&&!loading&&visible.length===0&&<p className="rounded-xl border border-dashed border-hud-soft p-6 text-sm text-muted-foreground">Nenhum documento cadastrado neste computador.</p>}
  <div className="grid min-w-0 gap-4 lg:grid-cols-2">{visible.map(s=><article key={s.source_id} className="min-w-0 space-y-3 rounded-xl border border-hud-soft bg-void/50 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><h3 className="min-w-0 break-words font-semibold">{s.title}</h3><span className="text-xs text-muted-foreground">{s.status==='ACTIVE'?'Ativa':'Arquivada'} · {s.extension.toUpperCase().replace('.','')}</span></div><p className="text-sm text-muted-foreground">{s.page_count?s.page_count+' página(s) · ':''}{s.chunk_count} trecho(s) · {(s.byte_count/1024).toFixed(1)} KiB</p><details className="text-xs text-muted-foreground"><summary className="cursor-pointer">Identificação da versão</summary><p className="mt-2 break-all">SHA-256: {s.content_hash}</p></details>{s.status==='ACTIVE'&&<button className={buttonClass} disabled={busy} aria-label={'Arquivar '+s.title} onClick={()=>void archive(s)}>Arquivar fonte</button>}</article>)}</div>
  <form className="space-y-4 rounded-xl border border-hud-soft bg-void/50 p-4 sm:p-6" onSubmit={e=>{e.preventDefault();void submit();}}><h3 className="font-semibold">Consultar documentos</h3><label className="block space-y-2 text-sm"><span>Escopo da consulta</span><select aria-label="Fonte da consulta" className={inputClass} value={scope} onChange={e=>setScope(e.target.value)} disabled={!target||running}><option value="ALL">Todos os documentos ativos deste PC</option>{!scopeValid&&<option value={scope}>Fonte indisponível; escolha outra</option>}{active.map(s=><option key={s.source_id} value={s.source_id}>Somente: {s.title}</option>)}</select></label><textarea aria-label="Pergunta sobre os documentos" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={1200} rows={3} className={inputClass+' resize-y p-4 text-base leading-relaxed'} placeholder="Que informação você quer localizar nos arquivos?"/><button className={buttonClass} disabled={!canSearch}>Buscar nos documentos</button></form>
  {task&&<div className="space-y-4 rounded-xl border border-hud-soft p-4 sm:p-6"><p role="status">{task.status==='WAITING_FOR_DEVICE'?'Aguardando o agente da biblioteca':task.status==='ANALYZING'?'Preparando consulta':task.status==='READING_SOURCES'?'Consultando os arquivos':task.status==='COMPLETED'?'Consulta concluída':task.status==='CANCELLED'?'Consulta cancelada':'Consulta não concluída'}</p>{running&&<button className={buttonClass} onClick={()=>void cancel()}>Cancelar consulta</button>}{task.error_code&&<p role="alert" className="text-sm">{failure(new ApiError(400,task.error_code))} Código: {task.error_code}</p>}{task.result?.matches.length===0&&<p>Nenhum trecho compatível encontrado. Tente outros termos.</p>}{task.result?.matches.map(m=><article key={m.source_id+':'+m.chunk_id} className="space-y-3 rounded-lg border border-hud-soft p-4"><h4 className="break-words font-semibold">{m.source.title}</h4><p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{m.excerpt}</p><p className="text-xs text-muted-foreground">{m.page?'Página '+m.page:'Linhas '+m.line_start+'–'+m.line_end}</p><details className="text-xs text-muted-foreground"><summary className="cursor-pointer">Referência do trecho</summary><p className="mt-2 break-all">Documento: {m.source_id} · Trecho: {m.chunk_id} · SHA-256: {m.source_hash}</p></details></article>)}{task.status==='COMPLETED'&&!task.result&&<p className="text-sm text-muted-foreground">O resultado privado não foi mantido. Uma nova consulta exige sua solicitação.</p>}</div>}
 </section>;
}
