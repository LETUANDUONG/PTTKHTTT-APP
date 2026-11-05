import { defineConfig,devices } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const runtime=path.resolve('../.test-runtime');
fs.mkdirSync(runtime,{recursive:true});
export default defineConfig({
  testDir:'./e2e',fullyParallel:false,workers:1,timeout:45000,
  globalTeardown:'./e2e/cleanup.js',
  reporter:[['list'],['json',{outputFile:'../docs/playwright-results.json'}]],
  use:{baseURL:'http://127.0.0.1:5099',screenshot:'only-on-failure',trace:'retain-on-failure'},
  projects:[{name:'desktop',use:{...devices['Desktop Chrome'],channel:'msedge',viewport:{width:1440,height:1000}}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium',channel:'msedge'}}],
  webServer:{command:`docker compose -f ../compose.yaml --env-file ../.env run --rm --no-deps --name hoodoo-e2e -p 127.0.0.1:5099:5099 -v "${runtime}:/app/.test-runtime" app python scripts/e2e_server.py`,url:'http://127.0.0.1:5099/api/session',reuseExistingServer:false,timeout:120000}
});
