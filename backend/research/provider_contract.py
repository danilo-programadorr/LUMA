"""Explicit transient provider boundary; never a persistence model."""
from pydantic import Field
from backend.app.models import Contract
from .contracts import Citation,Source,Usage,GoogleDisplayArtifact
class ProviderOutput(Contract):
    provider_answer:str=Field(max_length=6000)
    provider_citations:list[Citation]=Field(max_length=24)
    provider_sources:list[Source]=Field(max_length=8)
    provider_display_artifact:GoogleDisplayArtifact|None=None
    provider_usage:Usage
