$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root 'runtime/postgresql/bin/pg_isready.exe') -h 127.0.0.1 -p 55432 -U luma_test -d luma_test
if ($LASTEXITCODE -ne 0) { throw 'POSTGRES_NOT_READY' }
$env:PGPASSWORD = (Import-Clixml (Join-Path $root 'runtime/postgresql-config/app.xml')).GetNetworkCredential().Password
try {
 & (Join-Path $root 'runtime/postgresql/bin/psql.exe') -h 127.0.0.1 -p 55432 -U luma_test -d luma_test -X -v ON_ERROR_STOP=1 -c 'SELECT version(), current_database(), current_user;' -c 'SHOW listen_addresses;' -c 'SHOW port;'
 if ($LASTEXITCODE -ne 0) { throw 'POSTGRES_SQL_CHECK_FAILED' }
} finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
