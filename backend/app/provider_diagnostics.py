"""Closed vocabulary for vendor diagnostics; never accept vendor text."""
FINISH={'STOP','MAX_TOKENS','SAFETY','RECITATION','LANGUAGE','BLOCKLIST','PROHIBITED_CONTENT','SPII','MALFORMED_FUNCTION_CALL','OTHER','JAILBREAK','UNEXPECTED_TOOL_CALL','NO_IMAGE','IMAGE_SAFETY','IMAGE_PROHIBITED_CONTENT','IMAGE_RECITATION'}
BLOCK={'BLOCK_REASON_UNSPECIFIED','SAFETY','OTHER','BLOCKLIST','PROHIBITED_CONTENT','IMAGE_SAFETY','JAILBREAK'}
CODES={'INVALID_ARGUMENT','UNAUTHENTICATED','PERMISSION_DENIED','DEADLINE_EXCEEDED','RESOURCE_EXHAUSTED','INTERNAL','UNAVAILABLE','NOT_FOUND','FAILED_PRECONDITION','CANCELLED','UNKNOWN','OTHER'}
CATEGORIES={'HARM_CATEGORY_HARASSMENT','HARM_CATEGORY_HATE_SPEECH','HARM_CATEGORY_SEXUALLY_EXPLICIT','HARM_CATEGORY_DANGEROUS_CONTENT','HARM_CATEGORY_CIVIC_INTEGRITY','OTHER'}

def enum_value(value,allowed):
    if value is None:return None
    raw=getattr(value,'value',value)
    return raw if isinstance(raw,str) and raw in allowed else 'OTHER'

def empty_metadata():
    return dict(provider_status=None,provider_code=None,provider_error_type=None,finish_reason=None,block_reason=None,
        usage=dict(input_tokens=None,output_tokens=None,thought_tokens=None),usage_alerts=[],blocked=False,safety_categories=[],retryable=False,response_received=False,schema_validation=None,safe_schema_error=None)

def valid_metadata(value):
    if not isinstance(value,dict) or set(value)!=set(empty_metadata()):return False
    if value['provider_status'] is not None and (type(value['provider_status']) is not int or not 100<=value['provider_status']<=599):return False
    for name,allowed in [('provider_code',CODES),('provider_error_type',{'ClientError','ServerError','APIError','OTHER'}),('finish_reason',FINISH),('block_reason',BLOCK),('safe_schema_error',{'INVALID_JSON','SCHEMA_VALIDATION'})]:
        item=value[name]
        if item is not None and (not isinstance(item,str) or item not in allowed):return False
    if any(type(value[k]) is not bool for k in ('blocked','retryable','response_received')):return False
    if value['schema_validation'] is not None and type(value['schema_validation']) is not bool:return False
    usage=value['usage']
    if not isinstance(usage,dict) or set(usage)!={'input_tokens','output_tokens','thought_tokens'}:return False
    if any(v is not None and (type(v) is not int or not 0<=v<=10000000) for v in usage.values()):return False
    if value['usage_alerts'] not in ([],['HIGH_MODEL_TOKEN_USAGE']):return False
    cats=value['safety_categories']
    return isinstance(cats,list) and len(cats)<=len(CATEGORIES) and all(isinstance(c,str) and c in CATEGORIES for c in cats)
