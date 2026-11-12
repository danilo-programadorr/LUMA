import {defineConfig} from '@playwright/test';
import base from './playwright.production.config.mjs';
export default defineConfig({...base,reporter:[['list'],['json',{outputFile:'../reports/FASE_7F_D_B_PRODUCTION_TESTES.json'}]],use:{...base.use,baseURL:'http://127.0.0.1:5176'},webServer:{...base.webServer,command:'pnpm exec vite preview --host 127.0.0.1 --port 5176 --strictPort',url:'http://127.0.0.1:5176'}});
