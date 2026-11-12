import {defineConfig} from '@playwright/test';
import base from './playwright.config.mjs';
export default defineConfig({...base,reporter:[['list'],['json',{outputFile:'../reports/FASE_7F_D_A2_BROWSER.json'}]],use:{...base.use,baseURL:'http://127.0.0.1:5174'},webServer:{...base.webServer,command:'pnpm exec vite --mode test --host 127.0.0.1 --port 5174 --strictPort',url:'http://127.0.0.1:5174/e2e/harness.html'}});
