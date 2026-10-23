"""Expected task outcomes; no permission or execution authority."""
import re,unicodedata
from enum import StrEnum

class TaskOutcome(StrEnum):
    TECHNICAL_ERROR='TECHNICAL_ERROR'
    POLICY_DENIED='POLICY_DENIED'
    NEEDS_CLARIFICATION='NEEDS_CLARIFICATION'
    WAITING_AUTHORIZATION='WAITING_AUTHORIZATION'
    COMPLETED='COMPLETED'

def requests_bypass(message):
    text=''.join(c for c in unicodedata.normalize('NFKD',message.casefold()) if not unicodedata.combining(c))
    return bool(re.search(r'\b(execute|executar|rode|rodar)\b',text) and re.search(r'\b(sem (?:aprovacao|autorizacao)|ignore (?:o control plane|a aprovacao|a autorizacao))\b',text))

def resolve(*,clarification,review,review_reason,bypass,has_candidates,ambiguous):
    if review=='reject_candidate' and review_reason=='UNSUPPORTED_OPERATION':
        return TaskOutcome.POLICY_DENIED,'PROPOSAL_DENIED_BY_POLICY'
    if clarification or (ambiguous and not has_candidates):
        return TaskOutcome.NEEDS_CLARIFICATION,clarification or 'AMBIGUOUS_REQUEST'
    if review=='reject_candidate' or bypass:
        return TaskOutcome.POLICY_DENIED,'PROPOSAL_DENIED_BY_POLICY'
    return (TaskOutcome.WAITING_AUTHORIZATION if has_candidates else TaskOutcome.COMPLETED),None
