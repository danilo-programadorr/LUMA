from typing import Protocol
from pydantic import Field
from .models import Contract
from .model_contracts import ModelInputContext,ModelDecision

class ModelUsage(Contract):
    input_tokens:int | None=Field(default=None,ge=0,le=10000000)
    output_tokens:int | None=Field(default=None,ge=0,le=10000000)
class ModelResult(Contract):
    decision:ModelDecision
    usage:ModelUsage=Field(default_factory=ModelUsage)
    model_name:str=Field(max_length=100)
    instruction_version:str='luma-system-2'
class ModelProvider(Protocol):
    def generate(self,context:ModelInputContext,correlation_id:str)->ModelResult: ...
    def status(self)->dict: ...
    def close(self)->None: ...
