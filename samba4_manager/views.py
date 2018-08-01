import time
import pyramid.httpexceptions
from samba_server import SambaServer
from pyramid.view import view_config
from samba4_manager.model import User
from samba4_manager.model import UserForm, User

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
    
    def form_edit_user(self,req):
        return UserForm(req.POST)
    @view_config(route_name='agregar_usuario',renderer='templates/agregar_usuario.jinja2')
    def agregar_usuario(self):
        form=self.form_edit_user(self.request.POST)
        if self.request.method=='POST' and form.validate():
            user=User()
            user.samaccountname=form.samaccountname.data
            user.dn=form.dn.data
            # Aqui hay que grabar
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))
        return {'form':form}
    @view_config(route_name='editar_usuario',renderer='templates/editar_usuario.jinja2')
    def editar_usuario(self):
        objectguid=self.request.matchdict['objectguid'].encode(encoding='UTF-8')
        server=SambaServer()
        usuario=server.get_object(objectguid)
        form=self.form_edit_user(self.request.POST,usuario)
        if self.request.method=='POST' and form.validate():
            form.populate_obj(usuario)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))