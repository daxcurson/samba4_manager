import colander
import time
from samba_server import SambaServer
from pyramid.view import view_config

class UserEditForm(colander.MappingSchema):
    title = colander.SchemaNode(colander.String())
    body = colander.SchemaNode(colander.String())

class SambaAdminViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='listar_usuarios',renderer='templates/listar_usuarios.jinja2')
    def listar_usuarios(self):
        # Aca me comunico con Samba y le pido la lista de usuarios
        # actuales.
        start=time.time()
        server=SambaServer()
        usuarios=server.listar_usuarios()
        end=time.time()
        intervalo=end-start
        return { 'usuarios': usuarios,'intervalo':intervalo }
    @view_config(route_name='listar_grupos',renderer='templates/listar_grupos.jinja2')
    def listar_grupos(self):
        # Le pido la lista de grupos actuales.
        start=time.time()
        server=SambaServer()
        grupos=server.listar_grupos()
        end=time.time()
        intervalo=end-start
        return { 'grupos':grupos,'intervalo':intervalo }
    @view_config(route_name='editar_usuario',renderer='templates/editar_usuario.jinja2')
    def editar_usuario(self):
        objectguid=self.request.matchdict['objectguid'].encode(encoding='UTF-8')
        start=time.time()
        server=SambaServer()
        usuario=server.get_object(objectguid)
        end=time.time()
        intervalo=end-start
        return {'intervalo':intervalo,'usuario':usuario}