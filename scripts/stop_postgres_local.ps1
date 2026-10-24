$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$ctl = Join-Path $root 'runtime/postgresql/bin/pg_ctl.exe'
$data = Join-Path $root 'runtime/postgresql-data'
& $ctl -D $data status *> $null
if ($LASTEXITCODE -ne 0) { Write-Output 'ALREADY_STOPPED'; exit 0 }
& $ctl -D $data -m fast -w stop
if ($LASTEXITCODE -ne 0) { throw 'POSTGRES_STOP_FAILED' }
