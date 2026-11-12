import json
from pathlib import Path
import pytest
from backend.app.errors import Fault
from backend.research.acceptance import AcceptanceLedger,validate_gate,REQUIRED

def test_lifetime_budget_survives_restarts_and_stops_at_six(tmp_path):
    path=tmp_path/'usage.json'
    for n in range(1,7):
        ledger=AcceptanceLedger(path);assert ledger.reserve('synthetic')==n
        ledger.finish(n,{'response_received':True,'search_queries':2,'input_tokens':20,'output_tokens':10,'latency_ms':1})
    with pytest.raises(Fault) as e:AcceptanceLedger(path).reserve('synthetic')
    assert e.value.code=='RESEARCH_BUDGET_EXCEEDED'
    assert sum(x['search_queries'] for x in json.loads(path.read_text())['calls'])==12

def test_unknown_query_count_is_not_fabricated_and_failure_halts(tmp_path):
    p=tmp_path/'usage.json';l=AcceptanceLedger(p);n=l.reserve('synthetic');l.finish(n,{},'RESEARCH_PROVIDER_ERROR')
    d=json.loads(p.read_text());assert d['calls'][0]['search_queries'] is None
    with pytest.raises(Fault):AcceptanceLedger(p).reserve('synthetic')
    assert not any(k in d['calls'][0] for k in ('answer','html','urls','queries'))

def test_precheck_and_candidate_are_required_before_real_transport(tmp_path):
    p=tmp_path/'gate.json'
    with pytest.raises(Fault):validate_gate(p)
    p.write_text(json.dumps({'status':'PASS','criteria':{**dict.fromkeys(REQUIRED,'PASS'),'AUDIT':'VERIFIED','SECRET_SCAN':'PASSED'},'candidate_files':{}}))
    with pytest.raises(Fault):validate_gate(p)

def test_competing_reservation_fails_closed(tmp_path):
    l=AcceptanceLedger(tmp_path/'usage.json');l.lock.write_text('locked')
    with pytest.raises(Fault) as e:l.reserve('synthetic')
    assert e.value.code=='RESEARCH_BUDGET_LOCKED'
