"""Disabled-by-default, fixed three-case Owner acceptance. Original six are immutable."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from backend.app.errors import Fault
from .acceptance import AcceptanceLedger,validate_gate
from .policy import ExternalQueryPolicy

FINAL_GATE=Path('reports/FASE_7F_D_A_FINAL_THREE_PRECHECK.json')
LEGACY_LEDGER=Path('runtime/research-google-acceptance-usage.json')
FINAL_LEDGER=Path('runtime/research-google-final-three-usage.json')
MODEL='gemini-3.8-flash'
@dataclass(frozen=True)
class FinalCase:
    case_id:str
    query:str
    urls:tuple[str,...]
    tool:str
CASES=(FinalCase('public_scientific','O que a NASA explica sobre as causas de um eclipse lunar? Responda brevemente com fonte.',(),'google_search'),FinalCase('public_url_context','Explique brevemente a compreensão de listas da página pública selecionada e cite essa página.',('https://docs.python.org/3/tutorial/datastructures.html',),'url_context'))

CASES=(*CASES,FinalCase('public_multi_source','Pesquise como se diferenciam eclipses lunares totais e parciais segundo fontes públicas da NASA e do ESO. Cite as fontes e reconheça incertezas.',(),'google_search'))

def case_catalog():return [dict(case_id=c.case_id,query=c.query,urls=list(c.urls),tool=c.tool) for c in CASES]

def validate_final_gate():
    try:
        validate_gate(FINAL_GATE,expected_status='PASS_OWNER_AUTHORIZED')
        d=json.loads(FINAL_GATE.read_text(encoding='utf-8-sig'))
        if d.get('acceptance_profile')!='FINAL_THREE' or d.get('maximum_calls')!=3 or d.get('owner_approval_required') is not True or d.get('owner_approval_granted') is not True or d.get('cases')!=case_catalog():raise ValueError()
        superseded=Path('runtime/research-google-final-two-usage.json')
        if superseded.exists() and json.loads(superseded.read_text()).get('calls'):raise ValueError()
        raw=LEGACY_LEDGER.read_bytes();legacy=json.loads(raw)
        if legacy.get('maximum_calls')!=6 or legacy.get('halted') is not True or type(legacy.get('calls')) is not list or len(legacy['calls'])!=6 or any(c.get('status') not in ('COMPLETED','FAILED') for c in legacy['calls']):raise ValueError()
        if hashlib.sha256(raw).hexdigest()!=d['legacy_ledger_sha256']:raise ValueError()
        return d
    except (Fault,OSError,ValueError,KeyError,TypeError):raise Fault('RESEARCH_FINAL_PRECHECK_REQUIRED',403) from None

class FinalThreeLedger(AcceptanceLedger):
    maximum_calls=3
    def __init__(self,path=FINAL_LEDGER):super().__init__(path)
    def reserve(self,model):raise Fault('RESEARCH_FINAL_CASE_REQUIRED',403)
    def reserve_case(self,model,case_id):
        gate=validate_final_gate()
        if model!=MODEL or case_id not in {c.case_id for c in CASES}:raise Fault('RESEARCH_FINAL_CASE_NOT_APPROVED',403)
        def reserve(data):
            self._assert_open(data)
            if any(c.get('status') not in ('COMPLETED','FAILED') for c in data['calls']):raise Fault('RESEARCH_FINAL_ATTEMPT_UNRESOLVED',409)
            if data['calls'] and (data.get('acceptance_profile')!='FINAL_THREE' or data.get('legacy_ledger_sha256')!=gate['legacy_ledger_sha256'] or any(c.get('case_id') not in {x.case_id for x in CASES} for c in data['calls'])):raise Fault('RESEARCH_BUDGET_INVALID',409)
            if any(c.get('case_id')==case_id for c in data['calls']):raise Fault('RESEARCH_FINAL_CASE_ALREADY_ATTEMPTED',409)
            completed={c.get('case_id') for c in data['calls'] if c.get('status')=='COMPLETED'}
            if case_id=='public_multi_source' and not {'public_scientific','public_url_context'}<=completed:raise Fault('RESEARCH_FINAL_OPTIONAL_CASE_NOT_READY',403)
            n=self._reserve(data,model);data['calls'][-1]['case_id']=case_id
            data.update(acceptance_profile='FINAL_THREE',legacy_ledger_sha256=gate['legacy_ledger_sha256'])
            return n
        return self.edit(reserve)

def prepare_final_acceptance(request,tool,owner_approved,model=MODEL):
    if owner_approved is not True:raise Fault('RESEARCH_FINAL_APPROVAL_REQUIRED',403)
    validate_final_gate()
    if model!=MODEL:raise Fault('RESEARCH_FINAL_CASE_NOT_APPROVED',403)
    if request.project_id!='meu-gestor' or request.public_query is not None or request.route.route not in ('WEB_FIRST','WEB_REQUIRED'):raise Fault('RESEARCH_FINAL_CASE_NOT_APPROVED',403)
    query=ExternalQueryPolicy().check(request.query)
    for case in CASES:
        if query==case.query and tuple(request.urls)==case.urls and tool==case.tool:return FinalThreeLedger(),case.case_id
    raise Fault('RESEARCH_FINAL_CASE_NOT_APPROVED',403)

def final_status():
    validate_final_gate()
    try:d=json.loads(FINAL_LEDGER.read_text()) if FINAL_LEDGER.exists() else {'maximum_calls':3,'halted':False,'calls':[]}
    except (OSError,ValueError):raise Fault('RESEARCH_BUDGET_INVALID',409) from None
    if d.get('maximum_calls')!=3 or type(d.get('calls')) is not list or len(d['calls'])>3:raise Fault('RESEARCH_BUDGET_INVALID',409)
    unresolved=any(c.get('status') not in ('COMPLETED','FAILED') for c in d['calls'])
    return {'acceptance_profile':'FINAL_THREE','maximum_calls':3,'calls':len(d['calls']),'remaining_calls':3-len(d['calls']),'halted':d.get('halted') is not False or unresolved,'unresolved_attempt':unresolved,'owner_approval_required':True,'owner_approval_granted':True}
