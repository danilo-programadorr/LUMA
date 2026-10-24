$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
 $env:LUMA_PG_ADMIN_PASSWORD=(Import-Clixml 'runtime/postgresql-config/admin.xml').GetNetworkCredential().Password
 $env:LUMA_PG_TEST_PASSWORD=(Import-Clixml 'runtime/postgresql-config/app.xml').GetNetworkCredential().Password
 & ./.venv/Scripts/python.exe -m pytest backend/postgres_tests -q --tb=short --junitxml=reports/FASE_7F_POSTGRES_TESTES.xml *> reports/FASE_7F_POSTGRES_TESTES.txt
 $testExit=$LASTEXITCODE
 Get-Content reports/FASE_7F_POSTGRES_TESTES.txt -Tail 30
 if ($testExit -ne 0) { throw 'POSTGRES_TESTS_FAILED' }
} finally {
 Remove-Item Env:LUMA_PG_ADMIN_PASSWORD,Env:LUMA_PG_TEST_PASSWORD -ErrorAction SilentlyContinue
 Pop-Location
}
