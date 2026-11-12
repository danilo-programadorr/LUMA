import {test,expect} from '@playwright/test';
import {spawn,execFileSync} from 'node:child_process';
test.setTimeout(20000);
let server;
test.beforeAll(async()=>{
 server=spawn('D:/projetos/luma/.venv/Scripts/python.exe',['-m','backend.tests.google_window_http_fixture'],{cwd:'D:/projetos/luma',windowsHide:true,stdio:'ignore'});
 for(let n=0;n<300;n++){try{if((await fetch('http://127.0.0.1:8788/fixture/default')).ok)return;}catch{}await new Promise(r=>setTimeout(r,100));}
 throw new Error('DISPLAY_FIXTURE_NOT_READY');
});
test.afterAll(()=>{if(server?.pid&&server.exitCode===null)execFileSync('taskkill',['/PID',String(server.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});});
for(const target of ['default','self','blank','unterminated'])test(`Google isolated window preserves ${target} navigation and blocks scripts`,async({page,context,request})=>{
 const fixture=await (await request.get('http://127.0.0.1:8788/fixture/'+target)).json();let served=false;let searches=0;
 await context.route('https://www.google.com/**',r=>r.fulfill({body:'Synthetic SRP',contentType:'text/html',headers:{'X-Frame-Options':'DENY','Content-Security-Policy':"frame-ancestors 'none'"}}));
 await context.route('http://127.0.0.1:8770/**',async r=>{
  const headers={'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'};
  const path=new URL(r.request().url()).pathname;
  if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers});
  if(path.startsWith('/research-display/')){if(served)return r.fulfill({status:410,body:'GROUNDED_RESULT_NOT_RETAINED'});served=true;return r.fulfill({body:fixture.body,headers:{...fixture.headers,'Content-Type':'text/html; charset=utf-8'}});}
  let data;
  if(path==='/health')data={database_status:'AVAILABLE'};
  else if(path==='/v1/owner/me')data={internal_owner_id:'synthetic-owner',provider:'google.com',status:'ACTIVE',auth_time:123};
  else if(path==='/v1/devices')data=[];
  else if(path==='/v1/research/devices')data=[{device_id:'a'.repeat(32),display_name:'Synthetic PC',status:'ACTIVE',web_research_approved:true}];
  else if(path==='/v1/research'){searches++;data={research_id:'b'.repeat(32),status:'ANALYZING',result:null,route:{route:'WEB_REQUIRED'}};}
  else data={research_id:'b'.repeat(32),status:'COMPLETED',result:null,display_status:'LIVE_WINDOW_READY',display_path:'/research-display/'+'c'.repeat(43),display_expires_at:Math.floor(Date.now()/1000)+30,route:{route:'WEB_REQUIRED'}};
  return r.fulfill({json:data,headers});
 });
 await page.goto('/e2e/harness.html?route=/devices');await page.getByRole('button',{name:'Entrar com Google'}).click();await page.getByRole('button',{name:'Abrir pesquisa da LUMA'}).click();
 const panel=page.getByRole('region',{name:'Pesquisa da LUMA'});await panel.getByLabel('Computador da pesquisa').selectOption('a'.repeat(32));await panel.getByLabel('Pergunta de pesquisa',{exact:true}).fill('Public question');await panel.getByRole('button',{name:'Pesquisar',exact:true}).click();
 const wait=page.waitForEvent('popup');await panel.getByRole('link',{name:'Abrir resultado Google'}).click();const popup=await wait;await popup.waitForLoadState();
 await expect(popup.locator('.luma-answer')).toContainText('🚀 A versão estável');expect(await popup.locator('.luma-answer sup').evaluate(node=>node.previousSibling.textContent)).toBe('🚀 A versão estável');
 expect(await popup.evaluate(()=>window.opener===null)).toBe(true);expect(await popup.evaluate(()=>window.origin)).toBe('null');expect(await popup.evaluate(()=>document.body.dataset.externalXss)).toBeUndefined();
 expect(await popup.evaluate(()=>{try{localStorage.setItem('x','x');return false;}catch{return true;}})).toBe(true);
 await expect(popup.getByText('ORIGINAL PUBLIC MOCK')).toBeVisible();expect(await popup.getByText('ORIGINAL PUBLIC MOCK').getAttribute('target')).toBe(['default','unterminated'].includes(target)?null:'_'+target);
 if(target==='unterminated'){await popup.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide')));await expect(popup.getByText('GROUNDED_RESULT_NOT_RETAINED')).toBeVisible();await popup.reload();await expect(popup.getByText('GROUNDED_RESULT_NOT_RETAINED')).toBeVisible();}
 else if(target==='blank'){const srpWait=popup.waitForEvent('popup');await popup.getByText('ORIGINAL PUBLIC MOCK').click();const srp=await srpWait;await srp.waitForLoadState();expect(srp.url()).toBe('https://www.google.com/search?q=public');await expect(srp.getByText('Synthetic SRP')).toBeVisible();await srp.close();await popup.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide')));await expect(popup.getByText('GROUNDED_RESULT_NOT_RETAINED')).toBeVisible();}
 else {await popup.getByText('ORIGINAL PUBLIC MOCK').click();await popup.waitForURL('https://www.google.com/search?q=public');expect(popup.url()).toBe('https://www.google.com/search?q=public');await expect(popup.getByText('Synthetic SRP')).toBeVisible();}
 await popup.close();expect(searches).toBe(1);expect(await page.evaluate(()=>JSON.stringify(localStorage)+JSON.stringify(sessionStorage))).not.toContain('ORIGINAL PUBLIC MOCK');
});
