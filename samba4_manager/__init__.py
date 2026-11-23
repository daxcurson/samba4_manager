import logging
import secrets

from pyramid.config import Configurator
from pyramid.settings import asbool, aslist
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.session import SignedCookieSessionFactory
from samba_server import SambaServer, BUILTIN_ADMINISTRATORS_SID
from .views import SambaAdminPermissions 
from .authorization import SambaAdminAuthenticationPolicy
from .authentication import SambaSecurityPolicy
from .credentials import CredentialStore

log = logging.getLogger(__name__)


def _get_secret(settings, key):
    """Return the secret configured in the .ini file under ``key``.

    If it is missing, a random secret is generated for this process only, so
    sessions will not survive a restart. Production installs must set it.
    """
    secret = settings.get(key)
    if not secret:
        log.warning("%s is not set; using a random secret for this process", key)
        secret = secrets.token_hex(32)
    return secret


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # Cookies flagged "secure" are only sent over HTTPS; enable it in production.
    secure_cookies = asbool(settings.get('samba4_manager.secure_cookies', False))
    samba_session_factory=SignedCookieSessionFactory(
        _get_secret(settings, 'samba4_manager.session_secret'),
        secure=secure_cookies,
        httponly=True)
    config = Configurator(settings=settings,session_factory=samba_session_factory)
    config.include('pyramid_jinja2')
    config.add_static_view('static', 'samba4_manager:static')
    config.add_request_method(get_samba_server, 'samba_server', reify=True)
    config.add_route('login','/login')
    config.add_route('logout','/logout')
    config.add_route('listar_usuarios', '/')
    config.add_route('listar_grupos','/grupos')
    config.add_route('listar_computadoras','/computadoras')
    config.add_route('agregar_usuario','/agregar_usuario')
    config.add_route('agregar_usuario_grabar_form','/agregar_usuario_grabar')
    config.add_route('agregar_computadora','/agregar_computadora')
    config.add_route('editar_usuario_mostrar_form','/editar_usuario/{objectguid}')
    config.add_route('editar_usuario_grabar_form','/editar_usuario_grabar')
    config.add_route('editar_grupo_mostrar_form','/editar_grupo/{objectguid}')
    config.add_route('editar_grupo_grabar_form','/editar_grupo_grabar')
    config.add_route('editar_computadora_mostrar_form','/editar_computadora/{objectguid}')
    config.add_route('editar_computadora_grabar_form','/editar_computadora_grabar')
    config.add_route('editar_share_mostrar_form','/editar_share/{objectguid}')
    config.add_route('listar_shares','/listar_shares')
    config.add_route('listar_avanzado','/listar_avanzado')
    config.add_route('listar_subrama','/listar_subrama')
    
    
    #authn_policy = SambaAdminAuthenticationPolicy('sosecret')
    #authz_policy = ACLAuthorizationPolicy()
    #config.set_authentication_policy(authn_policy)
    #config.set_authorization_policy(authz_policy)
    # Credentials of the logged-in users, kept in memory per session.
    credential_store = CredentialStore(
        timeout=int(settings.get('samba4_manager.session_timeout', 1800)))
    config.registry.credential_store = credential_store
    # Only members of these groups (by SID) may log in.
    config.registry.admin_group_sids = aslist(
        settings.get('samba4_manager.admin_groups', BUILTIN_ADMINISTRATORS_SID))
    config.set_security_policy(SambaSecurityPolicy(
        _get_secret(settings, 'samba4_manager.auth_secret'),
        credential_store,
        secure=secure_cookies))
    config.set_root_factory(lambda request: SambaAdminPermissions(request))
    config.scan()
    return config.make_wsgi_app()

def get_samba_server(request):
    """Return a SambaServer that acts with the logged-in user's own
    credentials, or None if nobody is logged in."""
    identity = request.identity
    if identity is None:
        return None
    credentials = identity['credentials']
    return SambaServer(credentials.username, credentials.password)
