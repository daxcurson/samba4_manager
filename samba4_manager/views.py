import colander
from samba_server import SambaServer
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

class UserEditForm(colander.MappingSchema):
    title = colander.SchemaNode(colander.String())
    body = colander.SchemaNode(colander.String())

class SambaAdminViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='listar_usuarios',renderer='templates/listar.jinja2')
    def listar_usuarios(self):
        # Aca me comunico con Samba y le pido la lista de usuarios
        # actuales.
        server=SambaServer()
        usuarios=server.listar_usuarios()
        return { 'usuarios': usuarios }