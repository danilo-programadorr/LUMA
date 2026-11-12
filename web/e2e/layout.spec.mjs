import {test,expect} from '@playwright/test';
for(const viewport of [{width:1350,height:576},{width:1440,height:900},{width:390,height:844}]){
 test(`devices workspace comfortable at ${viewport.width}x${viewport.height}`,async({page})=>{
  await page.setViewportSize(viewport);
  await page.route('http://127.0.0.1:8770/**',async r=>{
   const headers={'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'};
   if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers});
   const p=new URL(r.request().url()).pathname;
   const device={device_id:'a'.repeat(32),display_name:'Computador principal',platform:'WINDOWS',status:'ACTIVE',online:false,connection_status:'OFFLINE',enrollment_status:'APPROVED',key_fingerprint:'b'.repeat(64),created_at:'2026-10-27T12:00:00Z',last_seen_at:null,runtime_version:null,capabilities:['RUNTIME_INTELLIGENCE','DEVICE_HEARTBEAT','OUTBOUND_POLLING']};
   const data=p==='/health'?{database_status:'AVAILABLE'}:p==='/v1/owner/me'?{internal_owner_id:'synthetic-owner',provider:'google.com',status:'ACTIVE',auth_time:123}:p==='/v1/devices'?[device,{...device,device_id:'c'.repeat(32),display_name:'Vínculo antigo',status:'REVOKED'}]:p==='/v1/research/devices'?[{...device,web_research_approved:true}]:{};
   return r.fulfill({json:data,headers});
  });
  await page.goto('/e2e/harness.html?route=/devices');await page.getByRole('button',{name:'Entrar com Google'}).click();
  await expect(page.getByText('Computador principal',{exact:true})).toBeVisible();
  await expect(page.getByText('Vínculo antigo',{exact:true})).not.toBeVisible();await expect(page.getByText('Dispositivos revogados (1)',{exact:true})).toBeVisible();
  const main=await page.getByRole('main').boundingBox();const footer=await page.getByRole('contentinfo').boundingBox();expect(main.height).toBeGreaterThan(viewport.height*.55);expect(footer.height).toBeLessThan(85);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  const profile=await page.locator('button[aria-haspopup="menu"]').boundingBox();expect(profile.x+profile.width).toBeLessThanOrEqual(viewport.width);
  await page.waitForTimeout(800);await page.screenshot({path:`D:/projetos/luma/runtime/layout-devices-${viewport.width}.png`});
  await page.getByRole('button',{name:'Abrir pesquisa da LUMA'}).click();
  const dialog=page.getByRole('dialog',{name:'Pesquisa da LUMA'});await expect(dialog).toBeVisible();const box=await dialog.boundingBox();expect(box.width).toBeGreaterThan(Math.min(850,viewport.width*.85));expect(box.height).toBeLessThan(viewport.height);
  await expect(dialog.getByLabel('Pergunta de pesquisa',{exact:true})).toBeVisible();await page.waitForTimeout(300);await page.screenshot({path:`D:/projetos/luma/runtime/layout-research-${viewport.width}.png`});
  await page.keyboard.press('Escape');await expect(dialog).not.toBeVisible();
 });
}
