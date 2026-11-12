"""Strict data contracts. These describe scope; they never grant authority."""
import re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator

HEX=r'^[a-f0-9]{64}$'
KEY=r'^[a-zA-Z0-9_-]{1,64}$'
MODES=('READ_ONLY','WORKSPACE_WRITE')
def relative_path(value):
    if not isinstance(value,str) or len(value)>180 or '\\' in value or ':' in value or value.startswith('/'):raise ValueError('CODEX_PATH_INVALID')
    for part in value.split('/'):
        if part in ('','.','..') or part[-1:] in (' ','.') or not re.fullmatch(r'[a-zA-Z0-9_. -]+',part):raise ValueError('CODEX_PATH_INVALID')
        if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])',part.split('.')[0],re.I):raise ValueError('CODEX_PATH_INVALID')
    return value
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
class ExecutionProfile(Strict):
    profile_version:Literal['CODEX_EXECUTION_PROFILE_V1']='CODEX_EXECUTION_PROFILE_V1'
    workspace_id:str=Field(pattern=KEY)
    mapping_version:int=Field(ge=1,le=1000000)
    mapping_fingerprint:str=Field(pattern=HEX)
    snapshot_hash:str=Field(default='0'*64,pattern=HEX)
    task_prompt:str=Field(min_length=1,max_length=2000)
    execution_mode:Literal['READ_ONLY','WORKSPACE_WRITE']
    read_paths:list[str]=Field(default_factory=list,max_length=12)
    allowed_paths:list[str]=Field(default_factory=list,max_length=5)
    denied_paths:list[str]=Field(default_factory=list,max_length=8)
    network_policy:Literal['MODEL_ONLY_TASK_OFFLINE']='MODEL_ONLY_TASK_OFFLINE'
    git_policy:Literal['NO_GIT_WRITE']='NO_GIT_WRITE'
    validation_command:Literal['PYTHON_UNITTEST']='PYTHON_UNITTEST'
    max_duration:int=Field(default=120,ge=10,le=300)
    max_changed_files:int=Field(default=3,ge=1,le=5)
    max_changed_bytes:int=Field(default=8192,ge=1,le=32768)
    max_output_bytes:int=Field(default=16384,ge=1024,le=32768)
    binary_sha256:str=Field(default='0'*64,pattern=HEX)
    model:str=Field(default='',max_length=80,pattern=r'^[a-zA-Z0-9._-]*$')
    @field_validator('read_paths','allowed_paths','denied_paths')
    @classmethod
    def paths(cls,values):
        if len({v.casefold() for v in values})!=len(values):raise ValueError('CODEX_PATH_DUPLICATE')
        return [relative_path(v) for v in values]
    @model_validator(mode='after')
    def mode(self):
        if self.execution_mode=='READ_ONLY' and self.allowed_paths:raise ValueError('CODEX_READ_ONLY')
        for readable in self.read_paths:
            if readable.split('/')[0].casefold() in ('.git','.codex','.aws','.ssh','.agents','denied') or readable.casefold().endswith('.env'):raise ValueError('CODEX_PROTECTED_PATH')
            if any(readable.casefold()==x.casefold() or readable.casefold().startswith(x.casefold()+'/') for x in self.denied_paths):raise ValueError('CODEX_PATH_CONFLICT')
        for writable in self.allowed_paths:
            if writable.split('/')[0].casefold() in ('tests','.git','.codex','.agents','denied'):raise ValueError('CODEX_PROTECTED_PATH')
            if any(writable.casefold()==x.casefold() or writable.casefold().startswith(x.casefold()+'/') for x in self.denied_paths):raise ValueError('CODEX_PATH_CONFLICT')
        return self
class WorkspaceManifest(Strict):
    binary_sha256:str=Field(default='0'*64,pattern=HEX)
    model:str=Field(default='',max_length=80,pattern=r'^[a-zA-Z0-9._-]*$')
    workspace_id:str=Field(pattern=KEY)
    project_id:str=Field(pattern=KEY)
    target_device_id:str=Field(pattern=KEY)
    display_name:str=Field(min_length=1,max_length=80,pattern=r'^[^\x00-\x1f]+$')
    mapping_version:int=Field(ge=1,le=1000000)
    mapping_fingerprint:str=Field(pattern=HEX)
    snapshot_hash:str=Field(default='0'*64,pattern=HEX)
    allowed_execution_modes:list[Literal['READ_ONLY','WORKSPACE_WRITE']]=Field(min_length=1,max_length=2)
    enabled:bool=False
class ExecutionResult(Strict):
    execution_kind:Literal['CODEX_REAL','SIMULATED_TEST']='CODEX_REAL'
    execution_id:str=Field(pattern=KEY)
    job_id:str=Field(pattern=KEY)
    workspace_id:str=Field(pattern=KEY)
    status:Literal['SUCCEEDED','FAILED','CANCELLED','RECONCILIATION_REQUIRED']
    code:str=Field(max_length=80,pattern=r'^[A-Z0-9_]+$')
    binary_sha256:str=Field(pattern=HEX)
    profile_hash:str=Field(pattern=HEX)
    exit_code:int|None=None
    duration_ms:int=Field(ge=0)
    changed_files:list[str]=Field(default_factory=list,max_length=16)
    changed_bytes:int=Field(default=0,ge=0)
    validation_pass:bool=False
    summary:str=Field(default='',max_length=500)
    usage:dict=Field(default_factory=dict)
    @field_validator('usage')
    @classmethod
    def safe_usage(cls,value):
        allowed={'input_tokens','output_tokens','cached_input_tokens','reasoning_output_tokens'}
        if not set(value)<=allowed or any(type(x) is not int or x<0 for x in value.values()):raise ValueError('CODEX_USAGE_INVALID')
        return value
    @field_validator('changed_files')
    @classmethod
    def paths(cls,values):return [relative_path(v) for v in values]
