$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path '.env')) { throw 'Run ./run.ps1 first to create .env.' }
& docker compose up -d --wait db
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed' }
& docker compose build app
if ($LASTEXITCODE -ne 0) { throw 'Docker build failed' }
& docker compose run --rm --no-deps -v "${PSScriptRoot}/docs:/reports" app python -m pytest -q --junitxml=/reports/pytest-results.xml
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
& .\.venv\Scripts\python -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
$config = Get-Content -LiteralPath '.env' -Raw | ConvertFrom-StringData
$env:PGHOST = '127.0.0.1'
$env:PGPORT = if ($config.POSTGRES_PORT) { $config.POSTGRES_PORT } else { '5432' }
$env:PGDATABASE = if ($config.POSTGRES_DB) { $config.POSTGRES_DB } else { 'hoodoo' }
$env:PGUSER = if ($config.POSTGRES_USER) { $config.POSTGRES_USER } else { 'hoodoo' }
$env:PGPASSWORD = $config.POSTGRES_PASSWORD
if (-not (Test-Path 'frontend\node_modules')) {
    & npm --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw 'Node dependency installation failed' }
}
& npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
& npm --prefix frontend run test:e2e
if ($LASTEXITCODE -ne 0) { throw 'Browser tests failed' }
Write-Host 'All PostgreSQL and browser checks passed.'
