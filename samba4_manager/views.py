import time
import pyramid.httpexceptions
from samba_server import SambaServer
from pyramid.view import view_config
from samba4_manager.model import User, Computer, Group
from samba4_manager.model import UserForm, ComputerForm, GroupForm

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
        usuario=server.get_object_by_objectguid(objectguid)
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
        computadora=server.get_object_by_objectguid(objectguid)
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
        grupo=server.get_object_by_objectguid(objectguid)
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
    @view_config(route_name='listar_avanzado',renderer="templates/listar_avanzado.jinja2")
    def listar_avanzado(self):
                # Tengo que pedir una lista inicial de los items de mayor nivel, para despues
        # permitir que se despliegue e invocar al resto de los elementos.
        # Asi que aca hago una lista de items sacado de una condicion de busqueda
        # directa desde el raiz
        #server=SambaServer()
        #rama=server.search_branch("")
        return {} #{'rama':rama, 'raiz':server.get_domain()}
    @view_config(route_name='listar_subrama',renderer="json")
    def listar_subrama(self):
        #objectguid=self.request.matchdict['id'].encode(encoding='UTF-8')
        # Pido el valor del parametro id del request, y darle el valor
        # del dominio si es que vino vacio
        server=SambaServer()
        objectguid=self.request.params.get("id")
        nodo_dn=""
        if(objectguid=="#"):
            # Piden el nodo raiz. Hay que pedir el dominio y crear un nodo con eso.
            nodo_dn=server.get_domain()
            # Si objectguid es el #, hago que el objectguid del nodo sea el nombre del dominio.
            objectguid=nodo_dn
            hijos=server.search_root()
        else:
            padre=server.search_entry_by_objectguid(objectguid)
            nodo_dn=padre['dn']
            hijos=server.search_children(objectguid)
        # Ahora bien, hay que devolver un formato esperado por esta cosa. 
        json_return=self.convertir_a_json(nodo_dn,objectguid,hijos)
        return json_return
    def convertir_a_json(self,nodo_dn,objectguid,hijos):
        # Pasamos a Json con el formato que requiere el jstree.
        lista_hijos=[]
        for hijo in hijos:
            item_hijo={
                'id':hijo['objectguid'],
                'text':hijo['dn'],
                'state':{
                    'opened':False,
                    'disabled':False,
                    'selected':False
                    },
                'children':True
                }
            lista_hijos.append(item_hijo)
        item={
            'id':objectguid,
            'text':nodo_dn,
            'state':{
                'opened':True,
                'disabled':False,
                'selected':True
                },
            'children':lista_hijos
            }
        return item