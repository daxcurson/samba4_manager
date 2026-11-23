from pyramid.authentication import AuthTktCookieHelper
from pyramid.authorization import ACLHelper, Authenticated, Everyone
from pyramid.request import RequestLocalCache

# Key, in the Pyramid session, of the token that points to this session's
# credentials in the CredentialStore.
CREDENTIALS_SESSION_KEY = 'samba4_manager.credentials_token'


class SambaSecurityPolicy:
    """Identifies the logged-in user and the Samba credentials of their session.

    A request is authenticated only if it carries both a valid auth_tkt cookie
    and a session whose token is still in the credential store, for the same
    user name. After a restart or an idle timeout the store no longer has the
    token, so the user is sent back to the login page.

    Only members of the configured administrator groups can log in (see the
    login view), so every authenticated user gets the ``group:admin`` principal.
    """

    def __init__(self, secret, credential_store, secure=False):
        self.helper = AuthTktCookieHelper(secret, secure=secure, http_only=True)
        self.credential_store = credential_store
        # Compute the identity once per request.
        self._identity_cache = RequestLocalCache(self._load_identity)

    def identity(self, request):
        return self._identity_cache.get_or_create(request)

    def _load_identity(self, request):
        ticket = self.helper.identify(request)
        if ticket is None:
            return None
        token = request.session.get(CREDENTIALS_SESSION_KEY)
        credentials = self.credential_store.get(token)
        if credentials is None or credentials.username != ticket['userid']:
            return None
        return {
            'userid': credentials.username,
            'principals': ['group:admin'],
            'credentials': credentials,
        }

    def authenticated_userid(self, request):
        identity = request.identity
        if identity is not None:
            return identity['userid']

    def permits(self, request, context, permission):
        identity = request.identity
        principals = set([Everyone])
        if identity is not None:
            principals.add(Authenticated)
            principals.add(identity['userid'])
            principals.update(identity['principals'])
        return ACLHelper().permits(context, principals, permission)

    def remember(self, request, userid, password=None, **kw):
        """Start a session for ``userid``, keeping ``password`` server-side."""
        token = self.credential_store.add(userid, password)
        # A fresh session prevents reusing a session from before the login.
        request.session.invalidate()
        request.session[CREDENTIALS_SESSION_KEY] = token
        self._identity_cache.clear(request)
        return self.helper.remember(request, userid, **kw)

    def forget(self, request, **kw):
        self.credential_store.remove(request.session.get(CREDENTIALS_SESSION_KEY))
        request.session.invalidate()
        self._identity_cache.clear(request)
        return self.helper.forget(request, **kw)
