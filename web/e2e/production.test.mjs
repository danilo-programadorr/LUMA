import { test,expect } from '@playwright/test';
test('production login and security headers without test adapter',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const response=await page.goto('/approvals');
 expect(response.headers()['x-frame-options']).toBe('DENY');
 expect(response.headers()['content-security-policy']).not.toContain('unsafe-eval');
 expect(response.headers()['content-security-policy'].split('script-src')[1].split(';')[0]).not.toContain('unsafe-inline');
 await expect(page.getByRole('button',{name:'Entrar com Google'})).toBeVisible();
 await expect(page).toHaveURL(/login/);
 await expect(page.locator('body')).not.toContainText('Piloto privado · integrações');
 expect(errors).toEqual([]);
});


test('production CSP supports isolated intact suggestion HTML without script execution',async({page,context})=>{
 const html='<style>.chip{color:green}</style><a class="chip" target="_blank" href="https://www.google.com/search?q=public">Production boundary mock</a><script>parent.window.boundaryXss=true</script>';
 await context.route('https://www.google.com/**',r=>r.fulfill({body:'Synthetic SRP',contentType:'text/html'}));
 await page.goto('/login');
 await page.evaluate(html=>{const f=document.createElement('iframe');f.title='Production attribution boundary';f.sandbox.add('allow-popups','allow-popups-to-escape-sandbox');f.referrerPolicy='no-referrer';f.srcdoc=html;document.body.append(f);},html);
 const frame=page.getByTitle('Production attribution boundary');await expect(frame.contentFrame().getByText('Production boundary mock')).toBeVisible();
 expect(await frame.getAttribute('srcdoc')).toBe(html);expect(await page.evaluate(()=>window.boundaryXss)).toBeUndefined();
 const wait=page.waitForEvent('popup');await frame.contentFrame().getByText('Production boundary mock').click();const popup=await wait;await popup.waitForLoadState();expect(popup.url()).toBe('https://www.google.com/search?q=public');await popup.close();
});
