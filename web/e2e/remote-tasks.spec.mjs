import {test,expect} from '@playwright/test';
const tid='a'.repeat(32),hash='b'.repeat(64);
async function fixture(page){
 const t={task_id:tid,project_id:'meu-gestor',task_type:'ACTION_ORIENTED',input:'Proposta sintética <script>window.taskInjected=true</script>',status:'WAITING_AUTHORIZATION',proposal_hash:hash,effective_risk:'LOW',expires_at:'2099-01-01T00:00:00Z',action_request_id:'c'.repeat(32),proposal:{envelope:{tool_id:'sandbox-test',operation:'record',target_device_id:'d'.repeat(32),parameters:{}},risk:'LOW'},timeline:[]};
 const decisions=[];
 await page.route('http://127.0.0.1:8770/**',async route=>{
  const headers={'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'};
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
  const path=new URL(route.request().url()).pathname;
  if(path==='/health')return route.fulfill({json:{mode:'CONTROL_PLANE',database_status:'AVAILABLE'},headers});
  if(path==='/v1/owner/me')return route.fulfill({json:{internal_owner_id:'synthetic-owner',provider:'google.com',status:'ACTIVE',auth_time:123},headers});
  if(path==='/v1/tasks/'+tid+'/decision'){const d=route.request().postDataJSON();decisions.push(d);t.status=d.decision==='APPROVE'?'WAITING_FOR_DEVICE':'REJECTED';return route.fulfill({json:t,headers});}
  if(path==='/v1/tasks/'+tid)return route.fulfill({json:t,headers});
  if(path==='/v1/remote-approvals'||path==='/v1/tasks')return route.fulfill({json:[t],headers});
  return route.fulfill({json:[],headers});
 });return {t,decisions};
}
for(const size of [{width:390,height:844},{width:412,height:915}])test('remote approval exact snapshot mobile '+size.width,async({page})=>{
 await page.setViewportSize(size);const state=await fixture(page);await page.goto('/e2e/harness.html?route=/approvals');await page.getByRole('button',{name:'Entrar com Google'}).click();const panel=page.getByRole('region',{name:'Aprovações remotas'});await expect(panel.getByText(state.t.input,{exact:true})).toBeVisible();await panel.getByRole('button',{name:'Aprovar proposta'}).click();await expect(panel.getByText('WAITING_FOR_DEVICE',{exact:true})).toBeVisible();expect(state.decisions).toHaveLength(1);expect(state.decisions[0].proposal_hash).toBe(hash);expect(await page.evaluate(()=>window.taskInjected)).toBeUndefined();await page.goto('/e2e/harness.html?route=/approvals');await page.getByRole('button',{name:'Entrar com Google'}).click();await expect(panel.getByText('WAITING_FOR_DEVICE',{exact:true})).toBeVisible();
});
