import {test,expect} from '@playwright/test';
const did='a'.repeat(32),sid='b'.repeat(32),qid='d'.repeat(32);
const source={source_id:sid,project_id:'meu-gestor',device_id:did,title:'Documento sintético de referência privada com título longo para leitura confortável',content_hash:'c'.repeat(64),extension:'.txt',byte_count:80,page_count:0,chunk_count:1,status:'ACTIVE'};
const quote='Trecho privado sintético: <script>window.privateInjected=true</script> cancelamento controlado.';
async function fixture(page){
 const state={enabled:true,requests:[],deliveries:0};
 await page.route('http://127.0.0.1:8770/**',async route=>{
  const headers={'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'};
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
  const path=new URL(route.request().url()).pathname;
  if(path==='/health')return route.fulfill({json:{mode:'CONTROL_PLANE',database_status:'AVAILABLE'},headers});
  if(path==='/v1/owner/me')return route.fulfill({json:{internal_owner_id:'synthetic-owner',provider:'google.com',status:'ACTIVE',auth_time:123},headers});
  if(path==='/v1/library/devices')return route.fulfill({json:[{device_id:did,display_name:'PC sintético',status:'ACTIVE',private_library_approved:state.enabled,private_library_online:state.enabled}],headers});
  if(path.endsWith('/sources'))return route.fulfill({json:[source],headers});
  if(path.endsWith('/capability')){state.enabled=route.request().postDataJSON().enabled;return route.fulfill({json:{private_library_approved:state.enabled},headers});}
  if(path==='/v1/library/queries'){state.requests.push(route.request().postDataJSON());return route.fulfill({json:{query_id:qid,target_device_id:did,status:'ANALYZING',result:null,error_code:null},headers});}
  if(path==='/v1/library/queries/'+qid){state.deliveries++;return route.fulfill({json:{query_id:qid,target_device_id:did,status:'COMPLETED',error_code:null,result:{matches:[{source_id:sid,source_hash:source.content_hash,chunk_id:'e'.repeat(24),excerpt:quote,page:null,line_start:2,line_end:3,score:1,source}]}},headers});}
  return route.fulfill({status:404,json:{error:{code:'NOT_FOUND'}},headers});
 });
 await page.goto('/e2e/harness.html?route=/knowledge');await page.getByRole('button',{name:'Entrar com Google'}).click();return state;
}
for(const viewport of [{width:1440,height:900},{width:1920,height:1080},{width:390,height:844},{width:412,height:915}]){
 test(`private library cited retrieval responsive ${viewport.width}`,async({page})=>{
  await page.setViewportSize(viewport);const errors=[];page.on('pageerror',e=>errors.push(e.message));const state=await fixture(page);const panel=page.getByRole('region',{name:'Biblioteca privada'});
  await panel.getByLabel('Computador da biblioteca').selectOption(did);await expect(panel.getByRole('heading',{name:source.title})).toBeVisible();
  await panel.getByLabel('Fonte da consulta').selectOption(sid);await panel.getByLabel('Pergunta sobre os documentos').fill('cancelamento');await panel.getByRole('button',{name:'Buscar nos documentos'}).click();
  await expect(panel.getByText(quote,{exact:true})).toBeVisible();await expect(panel.getByText('Linhas 2–3')).toBeVisible();
  expect(state.requests).toHaveLength(1);expect(state.requests[0].source_ids).toEqual([sid]);expect(state.deliveries).toBe(1);
  expect(await page.evaluate(()=>window.privateInjected)).toBeUndefined();expect(await page.evaluate(()=>JSON.stringify(sessionStorage))).not.toContain(quote);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
  await page.screenshot({path:`D:/projetos/luma/reports/7fda2-ui/private-library-${viewport.width}.png`,fullPage:true});
 });
}
test('private library suspension clears excerpts without revoking the device',async({page})=>{
 const state=await fixture(page);const panel=page.getByRole('region',{name:'Biblioteca privada'});await panel.getByLabel('Computador da biblioteca').selectOption(did);await panel.getByLabel('Pergunta sobre os documentos').fill('cancelamento');await panel.getByRole('button',{name:'Buscar nos documentos'}).click();await expect(panel.getByText(quote,{exact:true})).toBeVisible();
 page.on('dialog',d=>d.accept());await panel.getByRole('button',{name:'Suspender biblioteca neste PC'}).click();await expect(panel.getByRole('button',{name:'Autorizar biblioteca neste PC'})).toBeVisible();await expect(panel.getByText(quote,{exact:true})).not.toBeVisible();expect(state.enabled).toBe(false);expect(await page.evaluate(()=>sessionStorage.getItem('luma.library.query_id'))).toBeNull();
});
