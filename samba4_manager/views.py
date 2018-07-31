import time
from samba_server import SambaServer
from pyramid.view import view_config
from samba4_manager.model import User
import deform
from deform.exception import ValidationFailure

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
    
    @property
    def edit_user_form(self):
        schema=User()
        return deform.Form(schema,buttons=('submit',))
    @view_config(route_name='editar_usuario',renderer='templates/editar_usuario.jinja2')
    def editar_usuario(self):
        objectguid=self.request.matchdict['objectguid'].encode(encoding='UTF-8')
        server=SambaServer()
        usuario=server.get_object(objectguid)
        f=self.edit_user_form
        template_values={}
        template_values.update(f.get_widget_resources())
        if 'submit' in self.request.POST:
            controls=self.request.POST.items()
            try:
                f.validate(controls)
            except ValidationFailure as e:
                template_values['form']=e.render()
            return template_values
        template_values['form']=f.render()
        return template_values
