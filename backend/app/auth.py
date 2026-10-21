import secrets
from .errors import Fault


class LocalAuthenticator:
    """Replaceable identity adapter; token resolves to server-owned principal."""
    def __init__(self,settings):
        self.settings=settings

    def authenticate(self,request):
        values=request.headers.getlist('authorization')
        if len(values)!=1: raise Fault('UNAUTHORIZED',401)
        parts=values[0].split(' ')
        if (len(parts)!=2 or parts[0].lower()!='bearer' or not parts[1].isascii() or
            len(parts[1])>256 or not secrets.compare_digest(parts[1],self.settings.token)):
            raise Fault('UNAUTHORIZED',401)
        return self.settings.principal
