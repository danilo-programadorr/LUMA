import secrets
from .errors import Fault


class LocalAuthenticator:
    """Replaceable identity adapter; token resolves to server-owned principal."""
    def __init__(self,settings,control=None):
        self.settings=settings
        self.control=control

    def authenticate(self,request):
        values=request.headers.getlist('authorization')
        if len(values)!=1: raise Fault('UNAUTHORIZED',401)
        parts=values[0].split(' ')
        if len(parts)!=2 or parts[0].lower()!='bearer' or not parts[1].isascii() or len(parts[1])>256:
            raise Fault('UNAUTHORIZED',401)
        identity=None
        if secrets.compare_digest(parts[1],self.settings.token): identity=self.settings.principal.principal_id
        if self.settings.runtime_token and secrets.compare_digest(parts[1],self.settings.runtime_token): identity='luma-runtime'
        if identity is None: raise Fault('UNAUTHORIZED',401)
        principal=self.control.principal(identity) if self.control else self.settings.principal
        runtime_path=request.url.path.startswith('/v1/runtime/')
        expected='SERVICE_RUNTIME' if runtime_path else 'HUMAN_OWNER'
        if principal.principal_type!=expected: raise Fault('PLANE_IDENTITY_DENIED',403)
        return principal
