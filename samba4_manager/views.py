import time
import pyramid.httpexceptions
from samba_server import SambaServer, SambaError
from pyramid.view import view_config, forbidden_view_config
from pyramid.security import (remember,forget,Allow,Everyone)
from samba4_manager.model import User, Computer, Group
from samba4_manager.model import UserForm, ComputerForm, GroupForm, ShareForm
from samba4_config_writer import SambaConfigWriter
#from asn1crypto._ffi import null

class SambaAdminPermissions(object):
    __acl__ = [ (Allow, Everyone, 'view'),
               (Allow, 'group:admin', 'edit') ]
    def __init__(self, request):
        pass

class SambaAdminViews(object):
    def __init__(self, request):
        self.request = request
        self.logged_in = request.authenticated_userid
        self.samba_config=SambaConfigWriter()
        # Acts with the credentials of the logged-in user (None on the login page).
        self.samba_server=request.samba_server

    @view_config(route_name='login', renderer='templates/login.jinja2')
    @forbidden_view_config(renderer='templates/login.jinja2')
    def login(self):
        print("samba4_manager: login method")
        request = self.request
        login_url = request.route_url('login')
        referrer = request.url
        if referrer == login_url:
            referrer = '/'  # never use login form itself as came_from
        came_from = request.params.get('came_from', referrer)
        message = ''
        login = ''
        password = ''
        if 'submitted' in request.params:
            print("samba4_manager: I'm in login, I received a form")
            login = request.params['inputUser']
            password = request.params['inputPassword']
            print("samba4_manager: attempting to authenticate with %s" % login)
            server=SambaServer.authenticate(login, password)
            if server is None:
                message = 'Failed login'
            elif not server.es_miembro_de_alguno(request.registry.admin_group_sids):
                print("samba4_manager: %s is not an administrator" % login)
                message = 'Only domain administrators can use this application'
            else:
                print("samba4_manager: login successful for %s" % login)
                # The password stays on the server, tied to this session only.
                headers = remember(request, login, password=password)
                return pyramid.httpexceptions.HTTPFound(location=came_from,
                                 headers=headers)
        else:
            print("samba4_manager: I still didn't receive the login form")
        return dict(
            name='Login',
            message=message,
            url=request.application_url + '/login',
            came_from=came_from,
            login=login,
            )

    @view_config(route_name='logout')
    def logout(self):
        request = self.request
        headers = forget(request)
        url = request.route_url('listar_usuarios')
        return pyramid.httpexceptions.HTTPFound(location=url,
                         headers=headers)

    @view_config(route_name='listar_usuarios',renderer='templates/listar_usuarios.jinja2',
                 permission="edit")
    def listar_usuarios(self):
        # Aca me comunico con Samba y le pido la lista de usuarios
        # actuales.
        start=time.time()
        usuarios=self.samba_server.listar_usuarios()
        end=time.time()
        intervalo=end-start
        return { 'usuarios': usuarios,'intervalo':intervalo }
    @view_config(route_name='listar_grupos',renderer='templates/listar_grupos.jinja2',
                 permission="edit")
    def listar_grupos(self):
        # Le pido la lista de grupos actuales.
        start=time.time()
        grupos=self.samba_server.listar_grupos()
        end=time.time()
        intervalo=end-start
        return { 'grupos':grupos,'intervalo':intervalo }
    @view_config(route_name='listar_computadoras',renderer='templates/listar_computadoras.jinja2',
                 permission="edit")
    def listar_computadoras(self):
        # Le pido la lista de grupos actuales.
        start=time.time()
        computadoras=self.samba_server.listar_computadoras()
        end=time.time()
        intervalo=end-start
        return { 'computadoras':computadoras,'intervalo':intervalo }
    def form_add_user(self,req_post):
        usuario=User()
        form=UserForm(req_post,usuario)
        form.enabled.data=usuario.enabled
        form.account_type.data=usuario.account_type
        return form
    def form_edit_user(self,req_post,usuario):
        # Cargo los valores en el formulario
        form=UserForm(req_post,usuario)
        form.enabled.data=usuario.enabled
        form.account_type.data=usuario.account_type
        return form
    def form_edit_group(self,req_post,grupo):
        # Cargo los valores en el formulario
        form=GroupForm(req_post,grupo)
        # Solo se pueden quitar los miembros actuales del grupo.
        form.remove_members.choices=[(dn, dn) for dn in grupo.members]
        return form
    def form_edit_computer(self,req_post,computadora):
        # Cargo los valores en el formulario
        form=ComputerForm(req_post,computadora)
        form.enabled.data=computadora.enabled
        form.account_type.data=computadora.account_type
        return form
    def form_edit_share(self,req_post,share):
        form=ShareForm(req_post,share)
        # Aqui completo algunos datos del share.
        form.path=share.path
        return form
        
    @view_config(route_name='agregar_usuario',renderer='templates/agregar_usuario.jinja2',
                 permission="edit")
    def agregar_usuario_mostrar_form(self):
        form=self.form_add_user(self.request.POST)
        if self.request.method=='POST' and form.validate():
            user=User()
            user.samaccountname=form.samaccountname.data
            user.dn=form.dn.data
            # Aqui hay que grabar
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))
        return {'form':form}
    @view_config(route_name='agregar_usuario_grabar_form',renderer='templates/agregar_usuario.jinja2',
                 permission="edit")
    def agregar_usuario_grabar_form(self):
        usuario=()
        form=self.form_add_user(self.request.POST)
        if self.request_method=='POST' and form.validate():
            form.populate(usuario)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))
        return {'form':form}
    @view_config(route_name='editar_usuario_mostrar_form',renderer='templates/editar_usuario.jinja2',
                 permission="edit")
    def editar_usuario_mostrar_form(self):
        objectguid=self.request.matchdict['objectguid']
        usuario=self.samba_server.get_object_by_objectguid(objectguid)
        form=self.form_edit_user(self.request.POST,usuario)
        if self.request.method=='POST' and form.validate():
            form.populate_obj(usuario)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))
        return {'form':form}
    @view_config(route_name='editar_usuario_grabar_form',renderer='templates/editar_usuario.jinja2',
                 permission="edit")
    def editar_usuario_grabar_form(self):
        usuario=()
        form=self.form_edit_user(self.request.POST, usuario)
        if self.request_method=='POST' and form.validate():
            form.populate(usuario)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_usuarios'))
        return {'form':form}
    @view_config(route_name='editar_computadora_mostrar_form',renderer='templates/editar_computadora.jinja2',
                 permission="edit")
    def editar_computadora_mostrar_form(self):
        objectguid=self.request.matchdict['objectguid']
        computadora=self.samba_server.get_object_by_objectguid(objectguid)
        form=self.form_edit_computer(self.request.POST,computadora)
        if self.request.method=='POST' and form.validate():
            form.populate_obj(computadora)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_computadoras'))
        return {'form':form}
    @view_config(route_name='editar_computadora_grabar_form',renderer='templates/editar_computadora.jinja2',
                 permission="edit")
    def editar_computadora_grabar_form(self):
        computadora=()
        form=self.form_edit_computer(self.request.POST, computadora)
        if self.request_method=='POST' and form.validate():
            form.populate(computadora)
            # Aca grabo el objeto en el samba
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_computadoras'))
        return {'form':form}
    @view_config(route_name='editar_grupo_mostrar_form',renderer='templates/editar_grupo.jinja2',
                 permission="edit", require_csrf=True)
    def editar_grupo_mostrar_form(self):
        """Show a group and save changes to its description and members."""
        objectguid=self.request.matchdict['objectguid']
        try:
            grupo=self.samba_server.get_group_by_objectguid(objectguid)
        except ValueError:
            raise pyramid.httpexceptions.HTTPBadRequest("Invalid id")
        if grupo is None:
            raise pyramid.httpexceptions.HTTPNotFound()
        form=self.form_edit_group(self.request.POST,grupo)
        error=None
        if self.request.method=='POST' and form.validate():
            add_member=(form.add_member.data or '').strip()
            try:
                self.samba_server.update_group(
                    objectguid,
                    description=(form.description.data or '').strip(),
                    add_member_names=[add_member] if add_member else [],
                    remove_member_dns=form.remove_members.data or [])
            except SambaError as e:
                error=str(e)
            else:
                self.request.session.flash('The group was saved.')
                # Redirect, so that reloading the page does not submit the form again.
                raise pyramid.httpexceptions.HTTPFound(self.request.route_url(
                    'editar_grupo_mostrar_form', objectguid=objectguid))
        return {'form':form, 'grupo':grupo, 'error':error,
                'saved':self.request.session.pop_flash()}
    @view_config(route_name="editar_share_mostrar_form",renderer="templates/editar_share.jinja2",
                 permission="edit")
    def editar_share_mostrar_form(self):
        #share=
        form=self.form_edit_share(self.request.POST, share)
        return {'form':form}
    def editar_share_grabar_form(self):
        share=()
        form=self.form_edit_share(self.request.POST,share)
        if self.request_method=="POST" and form.validate():
            form.populate(share)
            # Grabar la configuracion del share
            raise pyramid.httpexceptions.HTTPFound(self.request.route_url('listar_shares'))
    @view_config(route_name="listar_shares",renderer="templates/listar_shares.jinja2",
                 permission="edit")
    def listar_shares(self):
        start=time.time()
        shares=self.samba_config.listar_shares()
        end=time.time()
        intervalo=end-start
        return { 'shares':shares,'intervalo':intervalo }
    @view_config(route_name='listar_avanzado',renderer="templates/listar_avanzado.jinja2",
                 permission="edit")
    def listar_avanzado(self):
                # Tengo que pedir una lista inicial de los items de mayor nivel, para despues
        # permitir que se despliegue e invocar al resto de los elementos.
        # Asi que aca hago una lista de items sacado de una condicion de busqueda
        # directa desde el raiz
        #server=SambaServer()
        #rama=server.search_branch("")
        return {} #{'rama':rama, 'raiz':server.get_domain()}
    @view_config(route_name='listar_subrama',renderer="json",
                 permission="edit")
    def listar_subrama(self):
        #objectguid=self.request.matchdict['id'].encode(encoding='UTF-8')
        # Pido el valor del parametro id del request, y darle el valor
        # del dominio si es que vino vacio
        objectguid=self.request.params.get("id")
        if(objectguid=="#"):
            # Piden el nodo raiz. Hay que pedir el dominio y crear un nodo con eso.
            nodo_dn=self.samba_server.get_domain()
            # Si objectguid es el #, hago que el objectguid del nodo sea el nombre del dominio.
            hijos=self.samba_server.search_root()
            return self.convertir_a_json(nodo_dn,nodo_dn,hijos)
        # Al desplegar una rama, jstree espera solamente la lista de sus hijos.
        try:
            hijos=self.samba_server.search_children(objectguid)
        except (ValueError, TypeError):
            raise pyramid.httpexceptions.HTTPBadRequest("Invalid id")
        return self.convertir_a_json("",objectguid,hijos)['children']
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
                'selected':False
                },
            'children':lista_hijos
            }
        return item