$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$bin = Join-Path $root 'runtime/postgresql/bin'
$data = Join-Path $root 'runtime/postgresql-data'
if (-not (Test-Path (Join-Path $data 'PG_VERSION'))) { throw 'POSTGRES_NOT_INITIALIZED' }
& (Join-Path $bin 'pg_ctl.exe') -D $data status *> $null
if ($LASTEXITCODE -eq 0) { Write-Output 'ALREADY_RUNNING'; exit 0 }
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Parse('127.0.0.1'),55432)
try { $listener.Start() } finally { $listener.Stop() }
& (Join-Path $bin 'pg_ctl.exe') -D $data -l (Join-Path $root 'runtime/postgresql-logs/server.log') -o '-h 127.0.0.1 -p 55432' -w start
if ($LASTEXITCODE -ne 0) { throw 'POSTGRES_START_FAILED' }
