import { test,expect } from '@playwright/test';
for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
 test(`devices approval and revocation ${viewport.width}`,async({page})=>{
  await page.setViewportSize(viewport);
  let row={device_id:'a'.repeat(32),display_name:'Synthetic PC',platform:'WINDOWS',status:'PENDING_ENROLLMENT',online:false,connection_status:'OFFLINE',enrollment_status:'AWAITING_OWNER',key_fingerprint:'b'.repeat(64),created_at:new Date().toISOString(),last_seen_at:null,runtime_version:null,capabilities:['DEVICE_HEARTBEAT','OUTBOUND_POLLING']};
  await page.route('http://127.0.0.1:8770/health',r=>r.fulfill({json:{database_status:'AVAILABLE'}}));
  await page.route('http://127.0.0.1:8770/v1/owner/me',r=>r.fulfill({json:{internal_owner_id:'local-owner',provider:'google.com',status:'ACTIVE',auth_time:123}}));
  await page.route('http://127.0.0.1:8770/v1/devices**',async r=>{
    if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers:{'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'}});
    const path=new URL(r.request().url()).pathname;
    if(path.endsWith('/approve'))row={...row,status:'ACTIVE',online:true,connection_status:'ONLINE',enrollment_status:'APPROVED'};
    if(path.endsWith('/revoke'))row={...row,status:'REVOKED',online:false,connection_status:'OFFLINE'};
    return r.fulfill({json:path==='/v1/devices'?[row]:row,headers:{'Access-Control-Allow-Origin':new URL(page.url()).origin}});
  });
  await page.goto('/e2e/harness.html?route=/devices');await page.getByRole('button',{name:'Entrar com Google'}).click();
  await expect(page.getByText('Synthetic PC')).toBeVisible();await expect(page.getByText('PENDING_ENROLLMENT',{exact:true})).toBeVisible();
  page.on('dialog',d=>d.accept());await page.getByRole('button',{name:'Aprovar dispositivo'}).click();await expect(page.getByText('ONLINE',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Revogar',exact:true}).click();await page.getByText('Dispositivos revogados (1)',{exact:true}).click();await expect(page.getByText('REVOKED',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 });
}
