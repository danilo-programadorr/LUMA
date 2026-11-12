import json,re
from backend.tests.test_research import research
from backend.tests.test_research_provider import data,req
from backend.tests.research_support import create,HEADERS
from backend.research.contracts import ResearchRequest
from backend.research.provider import normalize_interaction

def targetless(request):
    d=data();html=d['steps'][2]['result'][0]['search_suggestions'].replace(' target="_blank"','')
    d['steps'][2]['result'][0]['search_suggestions']=html
    return normalize_interaction(d,request,'gemini_google_search','gemini-3.8-flash',1,'google_search'),html

def test_targetless_google_html_is_accepted_intact_for_isolated_document():
    result,html=targetless(req())
    assert result.provider_display_artifact.presentation=='ISOLATED_WINDOW'
    assert result.provider_display_artifact.search_suggestions_html==[html]

def test_google_window_delivery_is_one_use_and_never_persisted(research):
    a,c,t,d,send=research;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json()
    result,html=targetless(ResearchRequest.model_validate(lease['request']))
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    row=c.get('/v1/research/'+rid,headers=HEADERS).json()
    assert row['display_status']=='LIVE_WINDOW_READY' and row['result'] is None
    assert re.fullmatch(r'/research-display/[A-Za-z0-9_-]{43}',row['display_path'])
    doc=c.get(row['display_path']);assert doc.status_code==200
    assert html.encode() in doc.content and result.answer.encode() in doc.content
    assert 'sandbox allow-scripts' in doc.headers['content-security-policy']
    assert 'allow-same-origin' not in doc.headers['content-security-policy']
    assert doc.headers['cache-control']=='no-store'
    assert c.get(row['display_path']).status_code==410
    again=c.get('/v1/research/'+rid,headers=HEADERS).json();assert again['display_status']=='GROUNDED_RESULT_NOT_RETAINED'
    with a.state.control.store.read() as repo:
        rows=json.dumps([repo.rows(x) for x in ('research_requests','audit_events','learning')]);assert html not in rows and row['display_path'] not in rows


def test_unknown_display_ticket_has_no_content(research):
    a,c,t,d,send=research
    response=c.get('/research-display/'+'z'*43)
    assert response.status_code==410 and 'Google' not in response.text

def test_window_validator_accepts_native_targets_without_rewriting():
    from backend.research.provider import validate_google_suggestions
    for target in ('','_self','_parent','_top','_blank'):
        html='<a href="https://www.google.com/search?q=public"'+(' target="'+target+'"' if target else '')+'>Unmodified label</a>'
        assert validate_google_suggestions(html,navigation='window')==html


def test_hybrid_private_context_stays_outside_public_display_document(research):
    a,c,t,d,send=research;rid=create(c,d).json()['research_id'];lease=send('poll',{}).json()
    result,html=targetless(ResearchRequest.model_validate(lease['request']))
    result=result.model_copy(update={'project_answer':'PRIVATE_PROJECT_CONTEXT_MARKER','project_evidence':['internal-doc:chunk']})
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    row=c.get('/v1/research/'+rid,headers=HEADERS).json()
    assert row['project_context']['answer']=='PRIVATE_PROJECT_CONTEXT_MARKER'
    assert 'PRIVATE_PROJECT_CONTEXT_MARKER' not in c.get(row['display_path']).text


def test_expired_display_ticket_cannot_replay_google_content(research):
    import time
    a,c,t,d,send=research;a.state.research.windows.ttl=.01
    rid=create(c,d).json()['research_id'];lease=send('poll',{}).json();result,html=targetless(ResearchRequest.model_validate(lease['request']))
    assert send('result',{'research_id':rid,'lease_id':lease['lease_id'],'result':result.model_dump()}).status_code==200
    row=c.get('/v1/research/'+rid,headers=HEADERS).json();time.sleep(.03)
    response=c.get(row['display_path']);assert response.status_code==410 and html not in response.text


def test_cleanup_installed_before_unterminated_provider_style():
    from html.parser import HTMLParser
    from backend.research.display import render_google_display,EXPIRY_SCRIPT
    result,_=targetless(req());opaque='<a href="https://www.google.com/search?q=public">public</a><style>'
    result=result.model_copy(update={'provider_display_artifact':result.provider_display_artifact.model_copy(update={'search_suggestions_html':[opaque]})})
    body,_=render_google_display(result)
    class Scripts(HTMLParser):
        def __init__(self):super().__init__();self.inside=False;self.values=[]
        def handle_starttag(self,tag,attrs):self.inside=tag=='script'
        def handle_endtag(self,tag):
            if tag=='script':self.inside=False
        def handle_data(self,data):
            if self.inside:self.values.append(data)
    parser=Scripts();parser.feed(body.decode())
    assert EXPIRY_SCRIPT in parser.values
    assert opaque.encode() in body
