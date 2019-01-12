from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.security import Everyone, Authenticated

class SambaAdminAuthenticationPolicy(AuthTktAuthenticationPolicy):
    def authenticated_userid(self, request):
        userid = self.unauthenticated_userid(request)
        if userid:
            return userid

    def effective_principals(self, request):
        principals = [Everyone]
        userid = self.authenticated_userid(request)
        if userid:
            principals += [Authenticated, str(userid)]
            user=request.user
            print("El user es %s" % user)
            if user is not None:
                principals.extend(('group:%s' % g for g in user.groups))
        return principals