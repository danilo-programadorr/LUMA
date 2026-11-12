param([ValidateSet('enroll','run','status')][string]$Mode='status')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
$prior=@{}
try {
 if($Mode -eq 'run') {
  if(-not $env:LUMA_GEMINI_API_KEY){throw 'GEMINI_KEY_NOT_AVAILABLE_IN_THIS_POWERSHELL'}
  & .\.venv\Scripts\python.exe -c "from backend.research.acceptance import validate_gate; validate_gate(); print('PRECHECK_VALID')"
  if($LASTEXITCODE -ne 0){throw 'ATTRIBUTION_PRECHECK_REQUIRED'}
  foreach($name in @('LUMA_RESEARCH_REAL_APPROVED','LUMA_RESEARCH_ATTRIBUTION_APPROVED','LUMA_RESEARCH_MAX_CALLS')){$prior[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
  $env:LUMA_RESEARCH_REAL_APPROVED='1'
  $env:LUMA_RESEARCH_ATTRIBUTION_APPROVED='1'
  $env:LUMA_RESEARCH_MAX_CALLS='6'
 }
 & .\.venv\Scripts\python.exe -m research_agent $Mode
 if($LASTEXITCODE -ne 0){throw 'RESEARCH_ACCEPTANCE_LOCAL_STEP_FAILED'}
} finally {
 foreach($name in $prior.Keys){[Environment]::SetEnvironmentVariable($name,$prior[$name],'Process')}
 Pop-Location
}
