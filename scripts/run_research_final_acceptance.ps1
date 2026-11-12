param([switch]$OwnerApprovedFinalThree,[ValidateSet('run','status')][string]$Mode='run')
$ErrorActionPreference='Stop'
if($Mode -eq 'run' -and -not $OwnerApprovedFinalThree){throw 'OWNER_APPROVAL_REQUIRED_NO_CALLS_MADE'}
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
$prior=@{}
try {
 & .\.venv\Scripts\python.exe -c "import json; from backend.research.final_acceptance import final_status; print(json.dumps(final_status()))"
 if($LASTEXITCODE -ne 0){throw 'FINAL_THREE_PRECHECK_REQUIRED'}
 if($Mode -eq 'status'){exit 0}
 if(-not $env:LUMA_GEMINI_API_KEY){throw 'GEMINI_KEY_NOT_AVAILABLE_IN_THIS_POWERSHELL'}
 foreach($name in @('LUMA_RESEARCH_REAL_APPROVED','LUMA_RESEARCH_ATTRIBUTION_APPROVED','LUMA_RESEARCH_MAX_CALLS','LUMA_RESEARCH_ACCEPTANCE_PROFILE','LUMA_RESEARCH_FINAL_THREE_OWNER_APPROVED')){$prior[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
 $env:LUMA_RESEARCH_REAL_APPROVED='1'
 $env:LUMA_RESEARCH_ATTRIBUTION_APPROVED='1'
 $env:LUMA_RESEARCH_MAX_CALLS='3'
 $env:LUMA_RESEARCH_ACCEPTANCE_PROFILE='FINAL_THREE'
 $env:LUMA_RESEARCH_FINAL_THREE_OWNER_APPROVED='1'
 & .\.venv\Scripts\python.exe -m research_agent run
 if($LASTEXITCODE -ne 0){throw 'RESEARCH_FINAL_ACCEPTANCE_LOCAL_STEP_FAILED'}
} finally {
 foreach($name in $prior.Keys){[Environment]::SetEnvironmentVariable($name,$prior[$name],'Process')}
 Pop-Location
}
