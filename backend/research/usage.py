"""Numeric SDK usage only; never thoughts, summaries or provider content."""
from backend.app.errors import Fault
TOKEN_FIELDS={'input_tokens':('total_input_tokens','input_tokens'),'output_tokens':('total_output_tokens','output_tokens'),'thought_tokens':('total_thought_tokens','thoughts_tokens'),'tool_use_tokens':('total_tool_use_tokens','tool_use_input_tokens'),'total_tokens':('total_tokens',),'cached_tokens':('total_cached_tokens','cached_tokens')}

def read_token_usage(usage):
    if not isinstance(usage,dict):raise Fault('RESEARCH_PROVIDER_USAGE_INVALID',502)
    values={}
    for field,sdk_fields in TOKEN_FIELDS.items():
        available=[usage[k] for k in sdk_fields if usage.get(k) is not None]
        if any(type(v) is not int or v<0 for v in available) or len(set(available))>1:raise Fault('RESEARCH_PROVIDER_USAGE_INVALID',502)
        values[field]=available[0] if available else None
    return values
