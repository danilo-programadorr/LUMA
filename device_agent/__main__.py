import argparse,getpass,json,signal,os
from .identity import Identity
from .client import DeviceClient,ChannelError

def main():
    for key in ('LUMA_OWNER_TOKEN','LUMA_RUNTIME_TOKEN','LUMA_ADMIN_CONFIRM_TOKEN','LUMA_GEMINI_API_KEY','LUMA_DATABASE_URL','LUMA_PG_ADMIN_PASSWORD','LUMA_PG_TEST_PASSWORD','GOOGLE_APPLICATION_CREDENTIALS'):
        os.environ.pop(key,None)
    p=argparse.ArgumentParser();p.add_argument('command',choices=['enroll','run','once','status']);p.add_argument('--endpoint',default='http://127.0.0.1:8770');a=p.parse_args()
    try:
        identity=Identity(create=a.command=='enroll');client=DeviceClient(identity,a.endpoint)
        if a.command=='enroll':
            value=getpass.getpass('Enrollment (challenge_id:code, entrada oculta): ')
            cid,code=value.split(':',1);result=client.enroll(cid,code);value=code=None
            print(json.dumps({'status':result['status'],'fingerprint':result['key_fingerprint']}))
        elif a.command=='status':print(json.dumps({'enrolled':bool(identity.binding()[0]),'fingerprint':identity.fingerprint()}))
        elif a.command=='once':print(json.dumps(client.once()))
        else:
            signal.signal(signal.SIGINT,lambda *_:client.stop.set());signal.signal(signal.SIGTERM,lambda *_:client.stop.set());client.run()
    except (ChannelError,RuntimeError,ValueError) as e:
        code=str(e)
        print(code if len(code)<100 and all(c.isupper() or c=='_' for c in code) else 'DEVICE_LOCAL_OPERATION_FAILED')
        raise SystemExit(1) from None
if __name__=='__main__':main()
