import {test,expect} from '@playwright/test';

for(const viewport of [{width:1440,height:900},{width:1920,height:1080},{width:390,height:844},{width:412,height:915}]){

 test(`research sources safe and responsive ${viewport.width}`,async({page})=>{

  await page.setViewportSize(viewport);

  await page.route('http://127.0.0.1:8770/**',async r=>{

   const headers={'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'};

   if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers});

   const p=new URL(r.request().url()).pathname;

   const data=p==='/health'?{database_status:'AVAILABLE'}:p==='/v1/owner/me'?{internal_owner_id:'local-owner',provider:'google.com',status:'ACTIVE',auth_time:123}:p==='/v1/research/devices'?[{device_id:'a'.repeat(32),display_name:'Synthetic PC',status:'ACTIVE',web_research_approved:true}]:{research_id:'b'.repeat(32),project_id:'meu-gestor',status:'COMPLETED',route:{route:'WEB_REQUIRED',freshness_required:true},result:{answer:'Public evidence',project_answer:'',sources:[{source_id:'s',title:'<script>window.injected=true</script>',url:'https://react.dev/',domain:'react.dev',source_type:'OFFICIAL',retrieved_at:1,published_at:null}],citations:[{citation_id:'c',source_id:'s',start_index:0,end_index:15}],freshness_status:'EVIDENCED',uncertainty_note:'Synthetic evidence',search_suggestions:[],error_code:null}};

   return r.fulfill({json:data,headers});

  });

  await page.goto('/e2e/harness.html?route=/dashboard');await page.getByRole('button',{name:'Entrar com Google'}).click();

  await page.getByRole('button',{name:'Abrir pesquisa da LUMA',exact:true}).click();
 const panel=page.getByRole('region',{name:'Pesquisa da LUMA'}).first();

  await panel.getByLabel('Computador da pesquisa').selectOption('a'.repeat(32));await panel.getByLabel('Pergunta de pesquisa',{exact:true}).fill('React hoje?');await panel.getByRole('button',{name:'Pesquisar',exact:true}).click();

  await expect(panel.getByText('COMPLETED',{exact:true})).toBeVisible();await expect(panel.getByRole('link')).toHaveAttribute('rel','noopener noreferrer');

  expect(await page.evaluate(()=>window.injected)).toBeUndefined();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);

 });

}





test('opaque Google suggestions stay isolated, navigate unchanged and disappear on refresh',async({page,context})=>{

 const html='<style>.chip{color:green}</style><div class="chip"><a target="_blank" href="https://www.google.com/search?q=public">ORIGINAL GOOGLE MOCK</a></div>';

 let delivered=false;let creates=0;let tracking=0;

 await context.route('https://www.google.com/**',r=>r.fulfill({body:'Synthetic destination',contentType:'text/html'}));

 await page.route('http://127.0.0.1:8770/**',async r=>{

  const headers={'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'};

  if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers});

  const p=new URL(r.request().url()).pathname;let data;

  if(p==='/health')data={database_status:'AVAILABLE'};

  else if(p==='/v1/owner/me')data={internal_owner_id:'local-owner',provider:'google.com',status:'ACTIVE',auth_time:123};

  else if(p==='/v1/remote-approvals')data=[];
  else if(p==='/v1/remote-approvals/summary')data={pending:0};
  else if(p==='/v1/research/devices')data=[{device_id:'a'.repeat(32),display_name:'Synthetic PC',status:'ACTIVE',web_research_approved:true}];

  else if(p==='/v1/research'){creates++;data={research_id:'b'.repeat(32),project_id:'meu-gestor',status:'ANALYZING',result:null,route:{route:'WEB_REQUIRED',freshness_required:true}};}

  else if(p==='/v1/research/'+'b'.repeat(32)){

   data={research_id:'b'.repeat(32),project_id:'meu-gestor',status:'COMPLETED',display_status:delivered?'GROUNDED_RESULT_NOT_RETAINED':'LIVE',result:delivered?null:{provider:'gemini_google_search',status:'COMPLETED',answer:'Synthetic grounded answer',project_answer:'',sources:[],citations:[],freshness_status:'EVIDENCED',uncertainty_note:'Synthetic fixture only',search_suggestions:[],provider_display_artifact:{provider:'gemini_google_search',provenance:'AUTHENTICATED_GOOGLE_PROVIDER',retention:'TRANSIENT_NON_PERSISTABLE_NON_REUSABLE',search_suggestions_html:[html]}},route:{route:'WEB_REQUIRED',freshness_required:true}};delivered=true;

  } else {tracking++;data={};}

  return r.fulfill({json:data,headers});

 });

 await page.goto('/e2e/harness.html?route=/dashboard');await page.getByRole('button',{name:'Entrar com Google'}).click();

 await page.getByRole('button',{name:'Abrir pesquisa da LUMA',exact:true}).click();
 const panel=page.getByRole('region',{name:'Pesquisa da LUMA'}).first();

 await panel.getByLabel('Computador da pesquisa').selectOption('a'.repeat(32));await panel.getByLabel('Pergunta de pesquisa',{exact:true}).fill('Public question');await panel.getByRole('button',{name:'Pesquisar',exact:true}).click();

 const frame=panel.getByTitle('Google Search Suggestions 1');await expect(frame).toBeVisible();expect(await frame.getAttribute('srcdoc')).toBe(html);

 await expect(frame).toHaveAttribute('sandbox','allow-popups allow-popups-to-escape-sandbox');

 const popupPromise=page.waitForEvent('popup');await frame.contentFrame().getByText('ORIGINAL GOOGLE MOCK').click();const popup=await popupPromise;

 await popup.waitForLoadState();expect(popup.url()).toBe('https://www.google.com/search?q=public');expect(await popup.evaluate(()=>window.opener===null)).toBe(true);await popup.close();

 await frame.evaluate(el=>{el.srcdoc='<script>parent.window.externalXss=true;fetch("http://127.0.0.1:8770/exfil")</script><p>Blocked script fixture</p>';});

 await expect(frame.contentFrame().getByText('Blocked script fixture')).toBeVisible();expect(await page.evaluate(()=>window.externalXss)).toBeUndefined();

 expect(tracking).toBe(0);expect(creates).toBe(1);expect(await page.evaluate(()=>JSON.stringify(localStorage)+JSON.stringify(sessionStorage))).not.toContain('ORIGINAL GOOGLE MOCK');

 await page.goto('/e2e/harness.html?route=/dashboard');await page.getByRole('button',{name:'Entrar com Google'}).click();

 await page.getByRole('button',{name:'Abrir pesquisa da LUMA',exact:true}).click();
 await expect(page.getByText('Resultado Google não retido. Uma nova pesquisa exige sua solicitação.').first()).toBeVisible();await expect(page.getByTitle('Google Search Suggestions 1')).toHaveCount(0);expect(creates).toBe(1);

});

