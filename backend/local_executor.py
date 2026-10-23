"""Outbound-only local device client. Production mutation adapters are disabled."""
import argparse,os,time
from urllib.parse import urlsplit
import httpx
from .executor_worker import FORBIDDEN_ENV
from .app import __version__

def endpoint(value):
    parsed=urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/') or not parsed.hostname:raise ValueError('INVALID_CONTROL_PLANE_URL')
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname=='127.0.0.1'):raise ValueError('HTTPS_REQUIRED')
    return value.rstrip('/')

def poll_once(client,device):
    body=dict(device_id=device,executor_version=__version__,status='ONLINE',capabilities=[],current_job_count=0)
    response=client.post('/v1/device/heartbeat',json=body);response.raise_for_status()
    response=client.post('/v1/device/poll',json={});response.raise_for_status()
    job=response.json()
    # No local side-effect adapter is installed in 7E production.
    # TestTool is exercised by the isolated test harness only.
    if job:raise RuntimeError('PRODUCTION_TOOL_ADAPTER_DISABLED')
    return {'status':'ONLINE','job_received':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    if any(os.environ.get(k) for k in FORBIDDEN_ENV):raise ValueError('EXECUTOR_PRIVILEGED_ENV_DENIED')
    device=os.environ.get('LUMA_DEVICE_ID','');credential=os.environ.get('LUMA_DEVICE_CREDENTIAL','')
    if not device or not 32<=len(credential)<=256:raise ValueError('DEVICE_CREDENTIAL_REQUIRED')
    url=endpoint(os.environ.get('LUMA_CONTROL_PLANE_URL','http://127.0.0.1:8770'))
    with httpx.Client(base_url=url,headers={'Authorization':'Bearer '+credential,'X-Luma-Device-ID':device},timeout=30,trust_env=False,follow_redirects=False) as client:
        while True:
            try:poll_once(client,device)
            except httpx.HTTPError:
                if args.once:raise RuntimeError('DEVICE_CONNECTION_FAILED') from None
            if args.once:break
            time.sleep(10)

if __name__=='__main__':main()
