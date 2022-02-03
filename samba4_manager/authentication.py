from pyramid.authentication import AuthTktCookieHelper
from pyramid.authorization import ACLHelper, Authenticated, Everyone
from samba_server import SambaServer

class SambaSecurityPolicy:
    def __init__(self, secret):
        self.helper = AuthTktCookieHelper(secret)
        self.samba_server=SambaServer.getInstance()

    def identity(self, request):
        # define our simple identity as None or a dict with userid and principals keys
        identity = self.helper.identify(request)
        if identity is None:
            return None
        userid = identity['userid']  # identical to the deprecated request.unauthenticated_userid

        # verify the userid, just like we did before with groupfinder
        principals = self.groupfinder(userid, request)

        # assuming the userid is valid, return a map with userid and principals
        if principals is not None:
            return {
                'userid': userid,
                'principals': principals,
            }
        return None
    def groupfinder(self,userid, request):
        # The View requires to create an ACL to allow
        # or refuse the access to the screen. This should
        # return a group such that it would be authorized
        # for the view. The list of groups should be
        # retrieved from Samba and check if the user
        # has the Administrators group.
        if userid is not None:
            return [ "group:admin" ]
        return None

    def authenticated_userid(self, request):
        # defer to the identity logic to determine if the user id logged in
        # and return None if they are not
        identity = request.identity
        if identity is not None:
            return identity['userid']

    def permits(self, request, context, permission):
        # use the identity to build a list of principals, and pass them
        # to the ACLHelper to determine allowed/denied
        identity = request.identity
        principals = set([Everyone])
        if identity is not None:
            principals.add(Authenticated)
            principals.add(identity['userid'])
            principals.update(identity['principals'])
        return ACLHelper().permits(context, principals, permission)

    def remember(self, request, userid, **kw):
        return self.helper.remember(request, userid, **kw)

    def forget(self, request, **kw):
        return self.helper.forget(request, **kw)
    