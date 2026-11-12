import {test,expect} from '@playwright/test';
for(const width of [390,412,1440,1920])test('Codex scoped proposal and result viewport '+width,async({page})=>{
 await page.setViewportSize({width,height:width<500?915:1080});
 const workspace={workspace_id:'codex-acceptance-v1',project_id:'meu-gestor',target_device_id:'a'.repeat(32),display_name:'Fixture sintético Codex',enabled:true,mapping_version:1,mapping_fingerprint:'b'.repeat(64),snapshot_hash:'f'.repeat(64),allowed_execution_modes:['READ_ONLY','WORKSPACE_WRITE'],binary_sha256:'c'.repeat(64),model:'fixture-model'};
 const tasks=[],decisions=[];
 await page.route('http://127.0.0.1:8770/**',async route=>{
  const headers={'Access-Control-Allow-Origin':new URL(page.url()).origin,'Access-Control-Allow-Headers':'authorization,content-type,x-correlation-id','Access-Control-Allow-Methods':'GET,POST'};
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
  const path=new URL(route.request().url()).pathname;
  let data=[];
  if(path==='/health')data={mode:'CONTROL_PLANE',database_status:'AVAILABLE'};
  else if(path==='/v1/owner/me')data={internal_owner_id:'synthetic-owner',provider:'google.com',status:'ACTIVE',auth_time:123};
  else if(path==='/v1/codex/workspaces')data=[workspace];
  else if(path==='/v1/tasks'&&route.request().method()==='POST'){
   const body=route.request().postDataJSON();
   tasks.push({task_id:'d'.repeat(32),project_id:'meu-gestor',task_type:'ACTION_ORIENTED',input:body.input,status:'WAITING_AUTHORIZATION',proposal_hash:'e'.repeat(64),effective_risk:'MEDIUM',expires_at:'2099-01-01T00:00:00Z',proposal:{envelope:{tool_id:'codex-executor',operation:body.codex_profile.execution_mode,parameters:body.codex_profile,target_device_id:workspace.target_device_id}},timeline:[]});data=tasks[0];
  }else if(path.endsWith('/decision')){
   decisions.push(route.request().postDataJSON());Object.assign(tasks[0],{status:'COMPLETED',decision:'APPROVE',codex_result:{execution_kind:'SIMULATED_TEST',code:'CODEX_VERIFIED',changed_files:['src/calc.py'],validation_pass:true,duration_ms:50}});data=tasks[0];
  }else if(path==='/v1/tasks'||path==='/v1/remote-approvals')data=tasks;
  await route.fulfill({json:data,headers});
 });
 await page.goto('/e2e/harness.html?route=/tasks');await page.getByRole('button',{name:'Entrar com Google'}).click();
 const composer=page.getByRole('region',{name:'Codex no PC'});
 await expect(composer).toBeVisible();await composer.getByLabel('Modo Codex').selectOption('WORKSPACE_WRITE');
 await composer.getByLabel('Tarefa técnica limitada').fill('Corrigir soma no fixture sintético.');
 await composer.getByRole('button',{name:'Criar proposta Codex'}).click();
 await expect(page.getByText('Workspace autorizado: codex-acceptance-v1')).toBeVisible();
 expect(decisions).toHaveLength(0);
 await page.getByRole('button',{name:'Aprovar proposta',exact:true}).click();
 await expect(page.getByText('Validação local: PASS')).toBeVisible();
 expect(decisions).toHaveLength(1);expect(decisions[0].proposal_hash).toBe('e'.repeat(64));
 expect(tasks[0].proposal.envelope.parameters.allowed_paths).toEqual(['src/calc.py']);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
