import json
import pytest
from device_agent.codex_process import redact,EventFilter

@pytest.mark.parametrize('kind',['jwt','oauth','password','dsn','pem'])
def test_redactor_removes_entire_synthetic_credential(kind):
 if kind=='jwt':value='eyJ'+('a'*12)+'.'+('b'*14)+'.'+('c'*14);text=value
 elif kind=='oauth':value='GOCSPX-'+('z'*30);text=value
 elif kind=='password':value='synthetic_not_a_real_password';text='password='+value
 elif kind=='dsn':value='postgresql+psycopg'+':'+'//user:synthetic@localhost/db';text=value
 else:value='SYNTHETIC_PEM_BODY';text=('-----BEGIN '+'PRIVATE KEY-----\n')+value+('\n-----END '+'PRIVATE KEY-----')
 removed=value not in redact(text)
 assert removed,'synthetic_canary_not_redacted'

def test_event_filter_preserves_split_portuguese_utf8():
 f=EventFilter(4096)
 raw=json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps({'summary':'Validação concluída'},ensure_ascii=False)}},ensure_ascii=False).encode('utf8')+b'\n'
 split=raw.index('ç'.encode('utf8'))+1
 f.feed('stdout',raw[:split]);f.feed('stdout',raw[split:])
 assert f.summary=='Validação concluída'