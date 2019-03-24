from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import unauthenticated_userid
from samba_server import SambaServer
from .views import SambaAdminPermissions 
from .authorization import SambaAdminAuthenticationPolicy
from .model import User

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_jinja2')
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view('static', 'samba4_manager:static')
    config.add_request_method(get_user, 'user', reify=True)
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
    
    authn_policy = SambaAdminAuthenticationPolicy(
        'sosecret', callback=groupfinder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.set_root_factory(lambda request: SambaAdminPermissions(request))
    config.scan()
    return config.make_wsgi_app()

def get_user(request):
    userid = unauthenticated_userid(request)
    print("get_user: el userid es %s" % userid)
    if userid is not None:
        print("get_user: el userid no es None. Consulto Samba")
        # Consulto el servidor de Samba con el user id del request.
        server=SambaServer()
        user=server.search_user_by_userid(userid)
        # este nombre de grupo tendria que ser leido de la configuracion, pero primero probemos si 
        # anda asi.
        print("get_user: consulte el userid %s en Samba y me trajo el user %s" % (userid,user))
        if server.pertenece_grupo(user['samaccountname'], "CN=Administrators,CN=Builtin,DC=agusvillafane,DC=zapto,DC=org"):
            print("get_user: el usuario que obtuve pertenece al grupo de administradores")
            # Le impongo a user una lista de groups con el grupo admin.
            userobject=User()
            userobject.samaccountname=user['samaccountname']
            userobject.groups=["admin"]
            return userobject
def groupfinder(userid, request):
    user = request.user
    print("groupfinder: me llamaron con el userid %s y el request %s" % (userid,request))
    if user is not None:
        return [ "admin" ]
    return None