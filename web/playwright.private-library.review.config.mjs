import {defineConfig} from '@playwright/test';
import base from './playwright.private-library.config.mjs';
export default defineConfig({...base,testMatch:'**/private-library.spec.mjs',reporter:[['list'],['json',{outputFile:'../reports/FASE_7F_D_A2_BROWSER_REVIEW.json'}]]});
