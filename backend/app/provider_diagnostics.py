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
    if not isinstance(value,dict) or set(value)-{'proposal_observation'}!=set(empty_metadata()):return False
    if 'proposal_observation' in value and not valid_proposal_observation(value['proposal_observation']):return False
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

PROPOSAL_FIELDS={'tool_id','capability','parameters','reason','correlation_id','assistant_message','intent','confidence','needs_clarification','citations','requested_knowledge','learning_candidates','document_id','chunk_id'}
SCHEMA_TYPES={'missing','extra_forbidden','value_error','string_type','string_too_long','string_too_short','tuple_type','list_type','dict_type','bool_type','float_type','greater_than_equal','less_than_equal','json_invalid','OTHER'}

def proposal_observation(raw):
    items=raw.get('proposed_actions') if isinstance(raw,dict) else None
    return dict(proposal_emitted=bool(items) if isinstance(items,list) else None,proposal_count=min(len(items),1000) if isinstance(items,list) else None,proposal_schema_valid=None,schema_error_fields=[])

def schema_fields(errors):
    result=[]
    for error in errors[:12]:
        loc=error['loc'];proposal=bool(loc and loc[0]=='proposed_actions')
        field=next((x for x in reversed(loc) if isinstance(x,str) and x in PROPOSAL_FIELDS),'OTHER')
        kind=error['type'] if error['type'] in SCHEMA_TYPES else 'OTHER'
        result.append(('proposal.' if proposal else 'decision.')+field+':'+kind)
    return result

def valid_proposal_observation(value):
    if not isinstance(value,dict) or set(value)!={'proposal_emitted','proposal_count','proposal_schema_valid','schema_error_fields'}:return False
    if any(value[k] is not None and type(value[k]) is not bool for k in ('proposal_emitted','proposal_schema_valid')):return False
    if value['proposal_count'] is not None and (type(value['proposal_count']) is not int or not 0<=value['proposal_count']<=1000):return False
    fields=value['schema_error_fields']
    allowed={prefix+field+':'+kind for prefix in ('proposal.','decision.') for field in PROPOSAL_FIELDS|{'OTHER'} for kind in SCHEMA_TYPES}
    return isinstance(fields,list) and len(fields)<=12 and all(isinstance(x,str) and x in allowed for x in fields)
