import {GoogleSearchSuggestionsFrame} from './google-search-suggestions-frame';

import {googleArtifact} from '@/lib/google-display';

import { safeSourceUrl } from '@/lib/research-links';

import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '@/auth/context';

import { ApiError } from '@/auth/client';

interface Device { device_id:string; display_name:string; status:string; web_research_approved:boolean }

interface Source {source_id:string;title:string;url:string;domain:string;source_type:string;retrieved_at:number;published_at:string|null}

interface Result {provider?:string;status?:string;provider_display_artifact?:{provider:string;provenance:string;retention:string;search_suggestions_html:string[]}|null;answer:string;project_answer:string;sources:Source[];citations:{citation_id:string;source_id:string;start_index:number;end_index:number}[];freshness_status:string;uncertainty_note:string;search_suggestions:{url:string;title:string}[];error_code:string|null}

interface Research {project_context?:{answer:string;evidence:string[]};display_status?:string;display_path?:string;display_expires_at?:number;research_id:string;project_id:string;status:string;result:Result|null;error_code:string|null;route:{route:string;freshness_required:boolean}}

const terminal=['COMPLETED','FAILED','CANCELLED'];
function researchFailure(error:unknown):string {
 if(!(error instanceof ApiError))return 'Não foi possível iniciar a pesquisa.';
 const reasons:Record<string,string>={
  PRIVATE_LIBRARY_USE_KNOWLEDGE:'Consulte os documentos privados na área Conhecimento → Biblioteca privada.',
  RESEARCH_EGRESS_BLOCKED:'A política de privacidade bloqueou a pergunta ou a pergunta pública complementar. Revise esses campos.',
  UNSAFE_URL:'A URL informada não é permitida. Utilize uma página pública sem credenciais.',
  PUBLIC_QUERY_REQUIRED:'Informe uma pergunta pública genérica para a consulta híbrida.',
  DEVICE_REVOKED:'O dispositivo selecionado foi revogado. Selecione um dispositivo ativo.',
  DEVICE_NOT_ACTIVE:'O dispositivo selecionado não está ativo.',
  DEVICE_CAPABILITY_MISMATCH:'WEB_RESEARCH não está autorizada para o dispositivo selecionado.',
  CAPABILITY_DENIED:'A permissão atual de consulta foi negada pela política.',
  ADMIN_CAPABILITY_DENIED:'A permissão atual do proprietário foi negada pela política.',
  RESEARCH_BUDGET_EXCEEDED:'O limite diário de solicitações de pesquisa foi atingido.',
  DEVICE_RATE_LIMITED:'Muitas solicitações em pouco tempo. Aguarde antes de tentar novamente.'
 };
 const message=(error.code&&reasons[error.code])||(error.status===0?'Não foi possível conectar ao servidor.':error.status===403?'A política recusou esta solicitação.':'Não foi possível iniciar a pesquisa.');
 return message+(error.code?' Código: '+error.code+'.':error.status?' HTTP '+error.status+'.':'');
}



export function ResearchAnswer({result}:{result:Result}) {

 if(result.provider==='gemini_google_search'&&result.provider_display_artifact&&!googleArtifact(result))return <p role="alert">Atribuição Google não validada. Resultado indisponível.</p>;

 return <div className="space-y-3 text-sm">

  {result.project_answer && <section><strong>Projeto · conhecimento interno</strong><p className="whitespace-pre-wrap">{result.project_answer}</p></section>}

  {result.answer && <section><strong>{result.sources.length?'Internet · fontes consultadas':'Sem pesquisa externa'}</strong><p className="whitespace-pre-wrap">{result.answer}</p></section>}

  {result.freshness_status==='UNAVAILABLE' && <p>Não foi possível verificar informação atual na internet.</p>}

  {result.sources.length>0 && <details open><summary>Fontes ({result.sources.length})</summary><ul className="space-y-2">{result.sources.map(s=><li key={s.source_id} className="break-words"><a href={safeSourceUrl(s.url)} target="_blank" rel="noopener noreferrer" className="text-primary underline">{s.title||s.domain}</a><p>{s.domain} · {s.source_type}</p><p>Consultado em {new Date(s.retrieved_at*1000).toLocaleString('pt-BR')}{s.published_at?' · Publicado em '+s.published_at:''}</p></li>)}</ul></details>}

  {result.citations.length>0 && <details><summary>Trechos com referências</summary>{result.citations.map(c=><p key={c.citation_id}>{Array.from(result.answer).slice(c.start_index,c.end_index).join('')} — {result.sources.find(s=>s.source_id===c.source_id)?.title}</p>)}</details>}

  <GoogleSearchSuggestionsFrame result={result}/>



  <p className="text-xs text-muted-foreground">{result.uncertainty_note}</p>

 </div>;

}

export function ResearchPanel(){

 const {deviceApi:api,reauthenticate}=useAuth();const [devices,setDevices]=useState<Device[]>([]);const [target,setTarget]=useState('');const [query,setQuery]=useState('');const [publicQuery,setPublicQuery]=useState('');const [url,setUrl]=useState('');const [allowWeb,setAllowWeb]=useState(true);const [research,setResearch]=useState<Research|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [mode,setMode]=useState('AUTO');const pending=useRef<{key:string;body:string}|null>(null);

 const refreshDevices=useCallback(async()=>{if(!api)return;try{setDevices(await api.call<Device[]>('/v1/research/devices'));}catch{setError('Pesquisa indisponível neste servidor.');}},[api]);

 useEffect(()=>{void refreshDevices();},[refreshDevices]);

 useEffect(()=>{if(!api)return;const id=sessionStorage.getItem('luma.research.id');if(id && /^[a-f0-9]{32}$/.test(id))void api.call<Research>('/v1/research/'+id).then(setResearch).catch(()=>sessionStorage.removeItem('luma.research.id'));},[api]);

 useEffect(()=>{if(research?.result?.provider!=='gemini_google_search')return;const timer=setTimeout(()=>setResearch(r=>r?{...r,result:null,display_status:'GROUNDED_RESULT_NOT_RETAINED'}:r),120000);return()=>clearTimeout(timer);},[research?.research_id,research?.result?.provider]);

 useEffect(()=>{if(research?.display_status!=='LIVE_WINDOW_READY'||!research.display_expires_at)return;const timer=setTimeout(()=>setResearch(r=>r?{...r,display_path:undefined,project_context:undefined,display_status:'GROUNDED_RESULT_NOT_RETAINED'}:r),Math.max(0,research.display_expires_at*1000-Date.now()));return()=>clearTimeout(timer);},[research?.display_path,research?.display_status,research?.display_expires_at]);
 useEffect(()=>{if(!api || !research || terminal.includes(research.status))return;const timer=setInterval(()=>{void api.call<Research>('/v1/research/'+research.research_id).then(setResearch).catch(()=>setError('Não foi possível atualizar a pesquisa.'));},3000);return()=>clearInterval(timer);},[api,research]);

 const submit=async()=>{if(!api||busy||!target||!query.trim())return;setBusy(true);setError('');if(research&&terminal.includes(research.status)){setResearch(null);sessionStorage.removeItem('luma.research.id');}const data={project_id:'meu-gestor',query:query.trim(),target_device_id:target,mode,allow_web:allowWeb,public_query:publicQuery.trim()||null,urls:url.trim()?[url.trim()]:[]};const body=JSON.stringify(data);if(pending.current?.body!==body)pending.current={key:crypto.randomUUID().replace(/-/g,''),body};try{const r=await api.call<Research>('/v1/research',{...data,idempotency_key:pending.current.key});setResearch(r);sessionStorage.setItem('luma.research.id',r.research_id);pending.current=null;}catch(e){setError(researchFailure(e));}finally{setBusy(false);}};

 const grant=async()=>{if(!api||!target)return;try{await api.call('/v1/research/devices/'+target+'/capability',{enabled:true});await refreshDevices();}catch{setError('Confirme sua identidade novamente para autorizar WEB_RESEARCH.');}};

 return <section aria-label="Pesquisa da LUMA" className="min-w-0 space-y-5 rounded-xl border border-hud-line bg-void/70 p-4 sm:p-6">

  <div className="grid items-center gap-3 sm:grid-cols-[1fr_minmax(200px,1fr)]"><strong className="text-sm">Pesquisa · Internet AUTO</strong><select aria-label="Computador da pesquisa" value={target} onChange={e=>setTarget(e.target.value)} className="h-11 w-full min-w-0 rounded-lg border border-hud-soft bg-void px-3 text-sm"><option value="">Selecione o computador</option>{devices.filter(d=>!['REVOKED','PENDING_ENROLLMENT'].includes(d.status)).map(d=><option key={d.device_id} value={d.device_id}>{d.display_name} · {d.status}</option>)}</select></div>

  {target && !devices.find(d=>d.device_id===target)?.web_research_approved && <div className="flex flex-wrap gap-3 rounded-lg border border-hud-soft p-3"><button onClick={()=>{if(window.confirm('Autorizar somente pesquisa pública neste dispositivo?'))void grant();}}>Autorizar WEB_RESEARCH</button><button onClick={()=>void reauthenticate()}>Confirmar identidade novamente</button></div>}

  <form onSubmit={e=>{e.preventDefault();void submit();}} className="space-y-4"><textarea rows={3} aria-label="Pergunta de pesquisa" maxLength={1200} value={query} onChange={e=>setQuery(e.target.value)} placeholder="Pergunte à LUMA sobre o projeto ou a internet" className="block min-h-28 w-full resize-y rounded-lg border border-hud-soft bg-void p-4 text-base leading-relaxed"/><details><summary className="cursor-pointer py-2 text-sm text-muted-foreground">Opções de pesquisa</summary><div className="mt-3 grid gap-4 rounded-lg border border-hud-soft p-4"><select aria-label="Modo de pesquisa" value={mode} onChange={e=>setMode(e.target.value)} className="min-h-10 rounded-lg border border-hud-soft bg-void px-3">{['AUTO','GENERAL_WEB','OFFICIAL_FIRST','SCIENTIFIC','TECHNICAL','NEWS','PROJECT_HYBRID'].map(x=><option key={x}>{x}</option>)}</select><label className="block"><input type="checkbox" checked={allowWeb} onChange={e=>setAllowWeb(e.target.checked)}/> Permitir internet</label><input aria-label="Pergunta pública para consulta híbrida" value={publicQuery} onChange={e=>setPublicQuery(e.target.value)} maxLength={500} placeholder="Pergunta pública genérica (para consulta híbrida)" className="min-h-11 w-full min-w-0 rounded-lg border border-hud-soft bg-void px-3 py-2 text-sm"/><input aria-label="URL pública opcional" value={url} onChange={e=>setUrl(e.target.value)} maxLength={2048} placeholder="URL pública opcional" className="min-h-11 w-full min-w-0 rounded-lg border border-hud-soft bg-void px-3 py-2 text-sm"/></div></details><button disabled={busy||!target||!query.trim()} className="min-h-11 w-full rounded-lg border border-primary bg-primary/10 px-6 py-2.5 text-sm font-medium transition-colors hover:bg-primary/20 disabled:opacity-40 sm:w-auto">{busy?'Enviando…':'Pesquisar'}</button></form>

  {error && <p role="alert" className="text-sm">{error}</p>}

  {research && <div className="space-y-2"><p role="status">{research.status==='WAITING_FOR_DEVICE'?'Aguardando o computador':research.status}</p>{!terminal.includes(research.status)&&<button onClick={()=>void api?.call<Research>('/v1/research/'+research.research_id+'/cancel',{}).then(setResearch).catch(()=>setError('Não foi possível cancelar.'))}>Cancelar pesquisa</button>}{research.status==='COMPLETED'&&research.display_status==='GROUNDED_RESULT_NOT_RETAINED'&&<p>Resultado Google não retido. Uma nova pesquisa exige sua solicitação.</p>}{research.project_context?.answer&&<section><strong>Projeto · conhecimento interno</strong><p className="whitespace-pre-wrap text-sm">{research.project_context.answer}</p></section>}{research.display_status==='LIVE_WINDOW_READY'&&research.display_path&&api&&<section className="space-y-2 rounded-lg border border-hud-line p-4"><a className="inline-flex min-h-11 items-center rounded-lg border border-primary px-4 text-primary" href={api.displayUrl(research.display_path)} target="_blank" rel="noopener noreferrer">Abrir resultado Google</a><p className="text-xs text-muted-foreground">Resposta e sugestões em uma aba temporária isolada. Abra em até 30 segundos; o conteúdo não fica no histórico.</p></section>}{research.result&&<ResearchAnswer result={research.result}/>} {(research.error_code||research.result?.error_code)&&<p>Pesquisa não concluída: {research.error_code||research.result?.error_code}</p>}</div>}

 </section>;

}

