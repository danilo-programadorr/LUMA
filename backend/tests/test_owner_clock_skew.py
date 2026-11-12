import json,time
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from google.auth import crypt,jwt
from backend.owner_auth import GoogleTokenVerifier,AuthenticatedOwnerPrincipal,require_recent_auth
from backend.app.errors import Fault

@pytest.fixture
def signed(monkeypatch):
    current=int(time.time());monkeypatch.setattr('backend.owner_auth.time.time',lambda:current)
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    pem=private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    class Response:
        status=200
        data=json.dumps({'synthetic':public}).encode()
    monkeypatch.setattr('google.auth.transport.requests.Request',lambda:lambda *args,**kw:Response())
    def token(offset=0,expired=False,wrong_key=False):
        values=dict(sub='synthetic',aud='synthetic-project',iss='https://securetoken.google.com/synthetic-project',iat=current+offset,auth_time=current+offset,exp=current-1 if expired else current+3600,firebase={'sign_in_provider':'google.com'})
        key=pem
        if wrong_key:
            key=rsa.generate_private_key(public_exponent=65537,key_size=2048).private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        return jwt.encode(crypt.RSASigner.from_string(key,key_id='synthetic'),values).decode()
    return current,token

@pytest.mark.parametrize('offset',[0,15,30])
def test_signed_google_token_with_bounded_clock_difference(signed,offset):
    current,token=signed
    result=GoogleTokenVerifier('synthetic-project').verify(token(offset))
    assert result['auth_time']==current+offset
    require_recent_auth(AuthenticatedOwnerPrincipal('owner','google.com','synthetic',result['auth_time'],'test'))

@pytest.mark.parametrize('options',[{'offset':31},{'offset':-100,'expired':True},{'wrong_key':True}])
def test_signed_token_outside_bound_expired_or_forged_rejected(signed,options):
    with pytest.raises(Fault):GoogleTokenVerifier('synthetic-project').verify(signed[1](**options))

@pytest.mark.parametrize('age',[301,-31])
def test_recent_auth_still_rejects_old_or_far_future(signed,age):
    with pytest.raises(Fault):require_recent_auth(AuthenticatedOwnerPrincipal('owner','google.com','synthetic',signed[0]-age,'test'))
