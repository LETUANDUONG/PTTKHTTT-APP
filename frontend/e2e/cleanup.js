import { execFileSync, spawnSync } from 'node:child_process';
import path from 'node:path';

export default function cleanup() {
  spawnSync('docker', ['rm', '-f', 'hoodoo-e2e'], { stdio: 'ignore' });
  execFileSync(path.resolve('../.venv/Scripts/python.exe'), [path.resolve('../scripts/e2e_server.py'), '--cleanup'], { stdio: 'inherit' });
}
