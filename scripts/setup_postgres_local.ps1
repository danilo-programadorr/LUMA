$ErrorActionPreference = 'Stop'
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
 if (Test-Path 'runtime/postgresql-data/PG_VERSION') {
  if (-not (Test-Path 'runtime/postgresql-config/app.xml')) { throw 'MISSING_LOCAL_CREDENTIALS' }
  Write-Output 'ALREADY_INITIALIZED'; exit 0
 }
 if ((Test-Path 'runtime/postgresql-data') -or (Test-Path 'runtime/postgresql-config/admin.xml')) { throw 'PARTIAL_SETUP_REQUIRES_REVIEW' }
 $probe=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Parse('127.0.0.1'),55432)
 try { $probe.Start() } finally { $probe.Stop() }
 New-Item -ItemType Directory -Force runtime/downloads,runtime/postgresql-config,runtime/postgresql-logs | Out-Null
 if (-not (Test-Path 'runtime/postgresql/bin/initdb.exe')) {
  $zip=Join-Path $root 'runtime/downloads/postgresql-18.6-windows-x64.zip'
  if (-not (Test-Path $zip)) { Invoke-WebRequest 'https://sbp.enterprisedb.com/getfile.jsp?fileid=1260609' -OutFile $zip }
  if ((Get-FileHash $zip -Algorithm SHA256).Hash -ne 'E2246BA91D22345BC3D017586C09EDE52D9DF180B1EEB480F050445F1CAD84E2') { throw 'ARTIFACT_CHANGED_REVIEW_REQUIRED' }
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $archive=[IO.Compression.ZipFile]::OpenRead($zip)
  try {
   foreach ($entry in $archive.Entries) {
    if ($entry.FullName -notmatch '^pgsql/(bin|lib|share|include)/') { continue }
    $base=[IO.Path]::GetFullPath((Join-Path $root 'runtime/postgresql'))
    $target=[IO.Path]::GetFullPath((Join-Path $base $entry.FullName.Substring(6)))
    if (-not $target.StartsWith($base+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'UNSAFE_ARCHIVE_PATH' }
    if ($entry.FullName.EndsWith('/')) { [IO.Directory]::CreateDirectory($target) | Out-Null }
    else {
     [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
     [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$false)
    }
   }
  } finally { $archive.Dispose() }
 }
 $version=& ./runtime/postgresql/bin/postgres.exe --version
 if ($version -ne 'postgres (PostgreSQL) 18.6') { throw 'UNEXPECTED_POSTGRES_VERSION' }
 $account=[Security.Principal.WindowsIdentity]::GetCurrent().Name
 icacls runtime/postgresql-config /inheritance:r /grant:r "${account}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
 if ($LASTEXITCODE -ne 0) { throw 'ACL_FAILED' }
 $adminPassword=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
 $appPassword=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
 [pscredential]::new('luma_admin',(ConvertTo-SecureString $adminPassword -AsPlainText -Force)) | Export-Clixml runtime/postgresql-config/admin.xml
 [pscredential]::new('luma_test',(ConvertTo-SecureString $appPassword -AsPlainText -Force)) | Export-Clixml runtime/postgresql-config/app.xml
 [IO.File]::WriteAllText((Join-Path $root 'runtime/postgresql-config/init-password'),$adminPassword)
 try {
  & ./runtime/postgresql/bin/initdb.exe -D runtime/postgresql-data -U luma_admin --pwfile=runtime/postgresql-config/init-password --auth=scram-sha-256 --encoding=UTF8 --locale=C
  if ($LASTEXITCODE -ne 0) { throw 'INITDB_FAILED' }
 } finally { Remove-Item -LiteralPath runtime/postgresql-config/init-password; $adminPassword=$null; $appPassword=$null }
 @"
listen_addresses = '127.0.0.1'
port = 55432
timezone = 'UTC'
password_encryption = 'scram-sha-256'
log_statement = 'none'
log_min_error_statement = 'panic'
"@ | Add-Content runtime/postgresql-data/postgresql.conf
 'host all all 127.0.0.1/32 scram-sha-256' | Set-Content runtime/postgresql-data/pg_hba.conf
 icacls runtime/postgresql-data /inheritance:r /grant:r "${account}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
 if ($LASTEXITCODE -ne 0) { throw 'ACL_FAILED' }
 & ./scripts/start_postgres_local.ps1
 $env:LUMA_PG_ADMIN_PASSWORD=(Import-Clixml runtime/postgresql-config/admin.xml).GetNetworkCredential().Password
 $env:LUMA_PG_TEST_PASSWORD=(Import-Clixml runtime/postgresql-config/app.xml).GetNetworkCredential().Password
 @'
import os,psycopg
from psycopg import sql
with psycopg.connect(host='127.0.0.1',port=55432,user='luma_admin',password=os.environ['LUMA_PG_ADMIN_PASSWORD'],dbname='postgres',autocommit=True) as c:
 c.execute(sql.SQL("CREATE ROLE luma_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD {}").format(sql.Literal(os.environ['LUMA_PG_TEST_PASSWORD'])))
 c.execute("CREATE DATABASE luma_test OWNER luma_test ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C'")
'@ | ./.venv/Scripts/python.exe -
 if ($LASTEXITCODE -ne 0) { throw 'ROLE_SETUP_FAILED' }
 & ./scripts/check_postgres_local.ps1
} finally {
 Remove-Item Env:LUMA_PG_ADMIN_PASSWORD,Env:LUMA_PG_TEST_PASSWORD -ErrorAction SilentlyContinue
 Pop-Location
}
