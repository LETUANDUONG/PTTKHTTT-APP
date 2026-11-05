$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path '.env')) {
    $config = Get-Content -LiteralPath '.env.example' -Raw
    $config = $config.Replace('replace-with-a-random-password', [guid]::NewGuid().ToString('N'))
    $config = $config.Replace('replace-with-a-random-secret', [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
    Set-Content -LiteralPath '.env' -Value $config -Encoding utf8
}
& docker compose build app
if ($LASTEXITCODE -ne 0) { throw 'Docker build failed.' }
if (-not (Test-Path 'models/whisper-small/model.bin') -or -not (Test-Path 'models/clip-vit-b32/0_CLIPModel/model.safetensors')) {
    & docker compose run --rm --no-deps -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 -v "${PSScriptRoot}/models:/app/models" app python scripts/download_models.py
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed. Check internet access and retry.' }
}
& docker compose up -d --wait
if ($LASTEXITCODE -ne 0) { throw 'Docker deployment failed. Check Docker Desktop and docker compose logs.' }
Write-Host 'Hoodoo is running. Default URL: http://localhost:8080 (APP_PORT in .env).'
