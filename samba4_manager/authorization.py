from pyramid.authentication import AuthTktCookieHelper
from pyramid.security import Everyone, Authenticated

class SambaAdminAuthenticationPolicy:
    def __init__(self, secret):
        self.authtkt = AuthTktCookieHelper(secret=secret)

    def identity(self, request):
        identity = self.authtkt.identify(request)
        if identity is not None:
            return identity

    def authenticated_userid(self, request):
        identity = self.identity(request)
        if identity is not None:
            return identity['userid']

    def remember(self, request, userid, **kw):
        return self.authtkt.remember(request, userid, **kw)

    def forget(self, request, **kw):
        return self.authtkt.forget(request, **kw)
    
    def effective_principals(self, request):
        principals = [Everyone]
        userid = self.authenticated_userid(request)
        if userid:
            principals += [Authenticated, str(userid)]
            #user=request.user
            #print("El user es %s" % user)
            #if user is not None:
            #    principals.extend(('group:%s' % g for g in user.groups))
        return principals