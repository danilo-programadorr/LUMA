"""Deterministic input assembly and content-free validation evidence."""
import json
from .model_contracts import ModelInputContext
from .models import KnowledgeContext

SUMMARY_MAX=next(m.max_length for m in ModelInputContext.model_fields['session_summary'].metadata if hasattr(m,'max_length'))

def bounded_summary(history,budget):
    limit=min(SUMMARY_MAX,max(0,budget))
    turns=list(history)
    while turns and len(json.dumps(turns,ensure_ascii=False))>limit:
        turns.pop(0)
    summary=json.dumps(turns,ensure_ascii=False) if limit>=2 else ''
    return summary,len(turns)!=len(history)

def input_counts(fields,conversation_chars):
    def size(name):
        value=fields.get(name)
        return len(value) if isinstance(value,(str,list,tuple)) else 0
    knowledge=fields.get('knowledge')
    return dict(user_message_chars=size('user_message'),session_summary_chars=size('session_summary'),
        knowledge_context_chars=len(knowledge.model_dump_json()) if isinstance(knowledge,KnowledgeContext) else 0,
        conversation_context_chars=conversation_chars,tools_count=size('available_tools'),pending_actions_count=size('pending_action_ids'))

def validation_errors(exc,fields):
    # Never serialize input, ctx, messages, arbitrary extra-field names or nested keys.
    known=set(ModelInputContext.model_fields)
    allowed={'string_too_long','string_too_short','string_type','tuple_type','list_type','dict_type','model_type','missing','extra_forbidden','literal_error','string_pattern_mismatch','bool_type','int_type','float_type','too_long','too_short'}
    result=[]
    for error in exc.errors(include_input=False,include_context=False,include_url=False)[:20]:
        loc=error.get('loc',())
        field=loc[0] if loc and isinstance(loc[0],str) and loc[0] in known else 'unknown_field'
        kind=error['type'] if error['type'] in allowed else 'validation_error'
        constraint='max_length' if kind in ('string_too_long','too_long') else 'min_length' if kind in ('string_too_short','too_short') else 'required' if kind=='missing' else 'extra_forbidden' if kind=='extra_forbidden' else 'enum' if kind=='literal_error' else 'pattern' if kind=='string_pattern_mismatch' else 'type_or_structure'
        item=dict(field=field,type=kind,constraint=constraint)
        if len(loc)==1 and field in known:
            value=fields.get(field)
            if isinstance(value,(str,list,tuple,dict)):item['actual_length']=len(value)
            for metadata in ModelInputContext.model_fields[field].metadata:
                maximum=getattr(metadata,'max_length',None)
                if type(maximum) is int:item['max_length']=maximum
        result.append(item)
    return result
