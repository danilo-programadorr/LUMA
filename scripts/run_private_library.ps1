param([ValidateSet('run','import','status')][string]$Mode='status',[string]$File,[string]$Title,[string]$Project='meu-gestor')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
 $arguments=@($Mode,'--project',$Project)
 if($File){$arguments+=@('--file',$File)}
 if($Title){$arguments+=@('--title',$Title)}
 $bootstrap="import os,sys; from backend.private_library.extract import parser_environment; os.execve(sys.executable,[sys.executable,'-m','library_agent',*sys.argv[1:]],parser_environment())"
 & .\.venv\Scripts\python.exe -c $bootstrap @arguments
 if($LASTEXITCODE -ne 0){throw 'PRIVATE_LIBRARY_LOCAL_OPERATION_FAILED'}
} finally {Pop-Location}
