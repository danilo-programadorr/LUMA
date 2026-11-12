import {defineConfig} from '@playwright/test';
import base from './playwright.production.config.mjs';
export default defineConfig({...base,reporter:[['list'],['json',{outputFile:'../reports/FASE_7F_D_A2_PRODUCTION.json'}]],use:{...base.use,baseURL:'http://127.0.0.1:5175'},webServer:{...base.webServer,command:'pnpm exec vite preview --host 127.0.0.1 --port 5175 --strictPort',url:'http://127.0.0.1:5175'}});
