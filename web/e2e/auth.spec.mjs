import { test,expect } from '@playwright/test';
test.beforeEach(async({page})=>{ await page.route('http://127.0.0.1:8770/health',route=>route.fulfill({json:{mode:'CONTROL_PLANE',version:'0.6.0rc1',database_status:'AVAILABLE'}})); });
for (const [width,height] of [[1440,900],[1920,1080],[390,844],[412,915]]) {
 test(`auth and dashboard ${width}x${height}`,async({page})=>{
  await page.setViewportSize({width,height});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://127.0.0.1:8770/v1/owner/me',route=>route.fulfill({json:{internal_owner_id:'local-owner',provider:'google.com',status:'ACTIVE',auth_time:123},headers:{'Access-Control-Allow-Origin':new URL(page.url()).origin}}));
  await page.goto('/e2e/harness.html?route=/');
  await expect(page.getByRole('button',{name:'Entrar com Google'})).toBeVisible();
  await expect(page.locator('body')).not.toContainText('Piloto privado · integrações');
  await page.screenshot({path:`../runtime/layout-e2e/login-${width}.png`,fullPage:true});
  await page.getByRole('button',{name:'Entrar com Google'}).click();
  await expect(page.getByText('Piloto privado · integrações não conectadas · execução indisponível')).toBeVisible();
  await expect(page.getByRole('heading',{name:'LUMA CORE'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Executar no PC Principal'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Abrir pesquisa da LUMA'})).toBeVisible();
  await expect(page.locator('body')).not.toContainText('9 agentes online');
  await page.waitForTimeout(900); // Let approved entrance animations settle before visual evidence.
  await page.screenshot({path:`../runtime/layout-e2e/dashboard-${width}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  if(width<1024)await page.getByRole('button',{name:'Abrir menu de módulos'}).click();
  await page.getByRole('link',{name:/Aprovações/}).filter({visible:true}).first().click();
  await expect(page).toHaveURL(/approvals/);
  await page.locator('button[aria-haspopup="menu"]').click();
  await page.getByRole('menuitem',{name:'Encerrar sessão'}).click();
  await expect(page.getByRole('button',{name:'Entrar com Google'})).toBeVisible();
  expect(errors).toEqual([]);
 });
}
test('all protected pages and safe deep link',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://127.0.0.1:8770/v1/owner/me',route=>route.fulfill({json:{internal_owner_id:'local-owner',provider:'google.com',status:'ACTIVE',auth_time:123}}));
 await page.goto('/e2e/harness.html?route=/approvals');await page.getByRole('button',{name:'Entrar com Google'}).click();await expect(page).toHaveURL(/approvals$/);
 for(const path of ['/','/core','/agents','/projects','/tasks','/calendar','/memory','/conversations','/knowledge','/tools','/workflows','/devices','/approvals']){
  await page.locator(`a[href="${path}"]`).filter({visible:true}).first().click();
  await expect(page.getByText('Piloto privado · integrações não conectadas · execução indisponível')).toBeVisible();
  await expect(page.locator('body')).not.toContainText('Algo deu errado');
 }
 expect(errors).toEqual([]);
});
