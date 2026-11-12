"""A refreshed token must not turn an old sign-in into recent authentication."""
import pytest
from backend.owner_auth import validate_claims, require_recent_auth, AuthenticatedOwnerPrincipal
from backend.app.errors import Fault

def test_refreshed_iat_does_not_refresh_auth_time(monkeypatch):
    current=1800000000
    monkeypatch.setattr('backend.owner_auth.time.time',lambda:current)
    claims=dict(sub='synthetic-owner',aud='synthetic-project',iss='https://securetoken.google.com/synthetic-project',iat=current,exp=current+3600,auth_time=current-600,firebase={'sign_in_provider':'google.com'})
    verified=validate_claims(claims,'synthetic-project')
    assert verified['auth_time']==current-600
    principal=AuthenticatedOwnerPrincipal('owner','google.com',verified['sub'],verified['auth_time'],'synthetic')
    with pytest.raises(Fault) as caught:require_recent_auth(principal)
    assert caught.value.code=='RECENT_AUTH_REQUIRED'
