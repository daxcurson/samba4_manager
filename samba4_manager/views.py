import time
import pyramid.httpexceptions
from samba_server import SambaServer
from pyramid.view import view_config
from samba4_manager.model import User, Computer
from samba4_manager.model import UserForm, ComputerForm

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
    @view_config(route_name='listar_computadoras',renderer='templates/listar_computadoras.jinja2')
    def listar_computadoras(self):
        # Le pido la lista de grupos actuales.
        start=time.time()
        server=SambaServer()
        computadoras=server.listar_computadoras()
        end=time.time()
        intervalo=end-start
        return { 'computadoras':computadoras,'intervalo':intervalo }
    
    def form_edit_user(self,req_post,usuario):
        # Cargo los valores en el formulario
        form=UserForm(req_post,usuario)
        form.enabled.data=usuario.enabled
        form.account_type.data=usuario.account_type
        return form
    def form_edit_group(self,req_post,grupo):
        # Cargo los valores en el formulario
        form=GroupForm(req_post,grupo)
        form.enabled.data=grupo.enabled
        form.account_type.data=grupo.account_type
        return form
    def form_edit_computer(self,req_post,computadora):
        # Cargo los valores en el formulario
        form=ComputerForm(req_post,computadora)
        form.enabled.data=computadora.enabled
        form.account_type.data=computadora.account_type
        return form
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
    @view_config(route_name='editar_usuario_mostrar_form',renderer='templates/editar_usuario.jinja2')
    def editar_usuario_mostrar_form(self):
        objectguid=self.request.matchdict['objectguid'].encode(encoding='UTF-8')
        server=SambaServer()
        usuario=server.get_object(objectguid)
        form=self.form_edit_user(self.request.POST,usuario)
        if self.request.method=='POST' and form.validate():
            form.populate_obj(usuario)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))
        return {'form':form}
    @view_config(route_name='editar_usuario_grabar_form',renderer='templates/editar_usuario.jinja2')
    def editar_usuario_grabar_form(self):
        usuario=()
        form=self.form_edit_user(self.request.POST, usuario)
        if self.request_method=='POST' and form.validate():
            form.populate(usuario)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))
        return {'form':form}
    @view_config(route_name='editar_computadora_mostrar_form',renderer='templates/editar_computadora.jinja2')
    def editar_computadora_mostrar_form(self):
        objectguid=self.request.matchdict['objectguid'].encode(encoding='UTF-8')
        server=SambaServer()
        computadora=server.get_object(objectguid)
        form=self.form_edit_computer(self.request.POST,computadora)
        if self.request.method=='POST' and form.validate():
            form.populate_obj(computadora)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_computadoras'))
        return {'form':form}
    @view_config(route_name='editar_computadora_grabar_form',renderer='templates/editar_computadora.jinja2')
    def editar_computadora_grabar_form(self):
        computadora=()
        form=self.form_edit_computer(self.request.POST, computadora)
        if self.request_method=='POST' and form.validate():
            form.populate(computadora)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_computadoras'))
        return {'form':form}
    @view_config(route_name='editar_grupo_mostrar_form',renderer='templates/editar_grupo.jinja2')
    def editar_grupo_mostrar_form(self):
        objectguid=self.request.matchdict['objectguid'].encode(encoding='UTF-8')
        server=SambaServer()
        grupo=server.get_object(objectguid)
        form=self.form_edit_group(self.request.POST,grupo)
        if self.request.method=='POST' and form.validate():
            form.populate_obj(grupo)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_grupos'))
        return {'form':form}
    @view_config(route_name='editar_grupo_grabar_form',renderer='templates/editar_grupo.jinja2')
    def editar_grupo_grabar_form(self):
        grupo=()
        form=self.form_edit_group(self.request.POST, grupo)
        if self.request_method=='POST' and form.validate():
            form.populate(grupo)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_grupos'))
        return {'form':form}