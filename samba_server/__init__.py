# Loading...
import logging
import ldb
import samba
import uuid
import base64
from samba import param
from samba import dsdb, dsdb_dns
from samba.samdb import SamDB
from samba.credentials import Credentials
from samba.dcerpc import security
from samba.ndr import ndr_unpack
from samba4_manager.model import User, Group

log = logging.getLogger(__name__)

# SID of the BUILTIN\Administrators group. Domain Admins and Enterprise Admins
# are members of it, so it covers every kind of domain administrator.
BUILTIN_ADMINISTRATORS_SID = security.SID_BUILTIN_ADMINISTRATORS


class SambaError(Exception):
    """An operation Samba refused, with a message that can be shown to the user."""


def _text(value):
    """Attribute values come back from ldb as bytes; return them as text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


# Bits of the groupType attribute. Builtin groups such as Administrators
# also have the domain local bit set; like Windows, show them as builtin.
GROUP_TYPE_SECURITY = 0x80000000
GROUP_SCOPES = [
    (0x1, "Builtin local"),
    (0x2, "Global"),
    (0x4, "Domain local"),
    (0x8, "Universal"),
]


def describe_group_type(group_type):
    """Return (scope, type) for a groupType value, e.g. ("Global", "Security")."""
    scope = next((name for bit, name in GROUP_SCOPES if group_type & bit), "")
    kind = "Security" if group_type & GROUP_TYPE_SECURITY else "Distribution"
    return scope, kind


# groupType for each (type, scope) chosen when creating a group.
GROUP_TYPES = {
    ("security", "global"): dsdb.GTYPE_SECURITY_GLOBAL_GROUP,
    ("security", "domain_local"): dsdb.GTYPE_SECURITY_DOMAIN_LOCAL_GROUP,
    ("security", "universal"): dsdb.GTYPE_SECURITY_UNIVERSAL_GROUP,
    ("distribution", "global"): dsdb.GTYPE_DISTRIBUTION_GLOBAL_GROUP,
    ("distribution", "domain_local"): dsdb.GTYPE_DISTRIBUTION_DOMAIN_LOCAL_GROUP,
    ("distribution", "universal"): dsdb.GTYPE_DISTRIBUTION_UNIVERSAL_GROUP,
}


def _creation_error(error, name):
    """A readable message for an LdbError raised while creating an account."""
    code = error.args[0]
    if code == ldb.ERR_ENTRY_ALREADY_EXISTS:
        return 'An account named "%s" already exists.' % name
    if code == ldb.ERR_CONSTRAINT_VIOLATION:
        return ("The password does not meet the domain's password policy "
                "(minimum length, complexity or history).")
    if code == ldb.ERR_INSUFFICIENT_ACCESS_RIGHTS:
        return "You do not have permission to create accounts there."
    return "Samba refused to create the account: %s" % error.args[-1]


def guid_base_dn(objectguid_hex):
    """Base DN that finds an object by the id the app uses for it.

    The app identifies objects by uuid.UUID(bytes=<raw objectGUID>).hex.
    The raw objectGUID is stored little-endian, so the GUID in its usual text
    form (the one "<GUID=...>" expects) is uuid.UUID(bytes_le=<raw>).
    Raises ValueError if objectguid_hex is not a valid id.
    """
    raw = uuid.UUID(hex=objectguid_hex).bytes
    return "<GUID=%s>" % uuid.UUID(bytes_le=raw)


class SambaServer(object):
    """Connection to the local Samba AD DC on behalf of one user.

    Every operation runs with the credentials given to the constructor, so
    Samba applies that user's permissions. Create one instance per request
    (see ``request.samba_server``); never share one between users.
    """
    URL = 'ldap://localhost'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.domain = ""

    def __repr__(self):
        # Never show the password, e.g. in tracebacks or debug output.
        return '<SambaServer username=%r>' % self.username

    @classmethod
    def authenticate(cls, username, password):
        """Check the credentials against Samba.

        Returns a SambaServer for that user, or None if Samba rejects them.
        """
        server = cls(username, password)
        try:
            server.conectar()
        except ldb.LdbError as error:
            log.info("Login failed for %s: %s", username, error.args[-1])
            return None
        return server

    def get_domain(self):
        # Devuelve la string del dominio
        if not self.domain:
            self.conectar()
        return self.domain

    def search_root(self):
        # Da los hijos del nodo raiz, cuyo DN se puede pedir con get_domain.
        cx=self.conectar()
        search_result = cx.search(self.domain,scope=ldb.SCOPE_ONELEVEL,expression='',attrs=["dn","objectguid"])
        hijos=[]
        for hijo in search_result:
            objectguid=hijo.get('objectguid',idx=0)
            guidhex=uuid.UUID(bytes=objectguid)
            hijos.append({"dn":hijo.get("dn",idx=0).get_casefold(),'objectguid':guidhex.hex})
        return hijos
    def search_children(self,objectguid=""):
        # Busco todo lo que este debajo del objeto informado por objectguid. 
        # Si objectguid viene vacio o es numeral, dar lo dependiente del dominio ).
        # El argumento es, o el nodo raiz, o el objectguid del nodo.
        cx=self.conectar()
        search_result=cx.search(base=guid_base_dn(objectguid),scope=ldb.SCOPE_ONELEVEL)
        hijos=[]
        for hijo in search_result:
            objectguid=hijo.get('objectguid',idx=0)
            guidhex=uuid.UUID(bytes=objectguid)
            hijos.append({"dn":hijo.get("dn",idx=0).get_casefold(),'objectguid':guidhex.hex})
        return hijos
    def conectar(self):
        lp=param.LoadParm()
        badge = Credentials()
        badge.guess(lp)
        # parse_string also accepts DOMAIN\user and user@realm.
        badge.parse_string(self.username)
        badge.set_password(self.password)
        cx = SamDB(url=self.URL,lp=lp,credentials=badge)
        self.domain=cx.domain_dn()
        return cx

    def es_miembro_de_alguno(self, group_sids):
        """True if the logged-in user belongs, directly or through nested
        groups, to any of the groups whose SIDs are given."""
        cx = self.conectar()
        # On the rootDSE, tokenGroups lists the groups of the bound user.
        result = cx.search("", scope=ldb.SCOPE_BASE, attrs=["tokenGroups"])
        user_sids = set(
            str(ndr_unpack(security.dom_sid, value))
            for value in result[0].get("tokenGroups", []))
        return bool(user_sids & set(group_sids))

    def listar_usuarios(self):
        # Aca se conectaria con el server en localhost y devolveria la lista de usuarios.
        # Search...
        cx=self.conectar()
        search_result = cx.search(self.domain,scope=2,expression='(&(objectCategory=person)(objectClass=user))',attrs=["samaccountname","description","dn","objectguid"])
        # Results...
        usuarios=[]
        for username in search_result:
            objectguid=username.get('objectguid',idx=0)
            guidhex=uuid.UUID(bytes=objectguid)
            usuarios.append({'user':username.get("samaccountname",idx=0),'description':username.get("description",idx=0),'dn':username.get("dn",idx=0),'objectguid':username.get("objectguid",idx=0),'key':guidhex.hex})
        return usuarios
    def listar_grupos(self):
        cx=self.conectar()
        search_result=cx.search(self.domain,scope=2,expression="(objectClass=group)",attrs=["samaccountname","description","dn","objectguid"])
        # Obtengo los resultados
        grupos=[]
        for grupo in search_result:
            objectguid=grupo.get('objectguid',idx=0)
            guidhex=uuid.UUID(bytes=objectguid)
            grupos.append({'group':grupo.get("samaccountname",idx=0),'description':grupo.get("description",idx=0),'dn':grupo.get("dn",idx=0),'objectguid':grupo.get("objectguid",idx=0),'key':guidhex.hex})
        return grupos
    def list_user_groups(self,username):
        # Lists the groups that the user belongs to
        cx=self.conectar()
        print("list_user_groups: obtaining the list of groups for the user %s" % username)
        search_result=cx.search(self.domain,scope=2,expression="(sAMAccountName=%s)",attrs=["memberOf"])
        groups=[]
        for group in search_result:
            print("Grupo encontrado: %s" % group)
            groups.append({'group':group.get("samaccountname",idx=0)})
        print("Grupos: %s" % groups)
    def pertenece_grupo(self,username,groupname):
        pertenece=False
        # Informa si el usuario pertenece al grupo que se pide
        cx=self.conectar()
        # El resultado de esta lista es un item, con el usuario, si este pertenece al grupo,
        # o un resultado vacio.
        print("pertenece_grupo: trato de ver si %s pertenece al grupo %s" % (username,groupname))
        search_result=cx.search(self.domain,scope=2,expression="(&(sAMAccountName=%s)(memberOf=%s))" % (username,groupname))
        # Resulta que la lista vacia tiene el valor implicito false. Haciendo not search_result,
        # me aseguro que la lista tenga contenido.
        print("pertenece_grupo: Hice la busqueda en Samba, ahora me fijo que resultado obtuve")
        print("pertenece_grupo: el resultado de la busqueda fue %s" % search_result)
        for username in search_result:
            samaccountname=username.get('samaccountname',idx=0)
            # Si ahora tengo un samaccountname, lo devuelvo.
            print("pertenece_grupo: el samaccountname es %s" % samaccountname)
            if samaccountname is not None:
                pertenece=True
        return pertenece
    def search_user_by_userid(self,userid):
        # Recibo alguna clase de id que el sistema Pyramid se guarda sobre el usuario autenticado.
        # Lo uso para alguna clase de busqueda en el LDAP
        cx=self.conectar()
        search_result=cx.search(self.domain,scope=2,expression="(sAMAccountName=%s)" % userid)
        result={}
        for item in search_result:
            result={
                'objectguid':item.get('objectguid',idx=0),
                'dn':item.get('dn',idx=0).get_casefold(),
                'samaccountname':item.get('samaccountname',idx=0)
                }
        return result
    def listar_computadoras(self):
        cx=self.conectar()
        search_result=cx.search(self.domain,scope=2,expression="(objectClass=computer)",attrs=["samaccountname","description","dn","objectguid"])
        # Obtengo resultados
        computadoras=[]
        for computadora in search_result:
            objectguid=computadora.get('objectguid',idx=0)
            guidhex=uuid.UUID(bytes=objectguid)
            computadoras.append({'samaccountname':computadora.get("samaccountname",idx=0),'description':computadora.get("description",idx=0),'dn':computadora.get("dn",idx=0),'objectguid':computadora.get("objectguid",idx=0),'key':guidhex.hex})
        return computadoras
    def search_entry_by_objectguid(self,objectg):
        search_result=self.__search_entry_private(objectg)
        # Asumo que retorno solamente un item.
        result={}
        for item in search_result:
            result={
                'objectguid':item.get('objectguid',idx=0),
                'dn':item.get('dn',idx=0).get_casefold()
                }
        return result
    def __search_entry_private(self,objectg):
        cx=self.conectar()
        # Me gustaria tomarme el credito pero no puedo, esa busqueda
        # salio del codigo fuente mismo de Samba,
        # https://download.samba.org/pub/unpacked/samba_current/source4/dsdb/tests/python/deletetest.py
        search_result=cx.search(base=guid_base_dn(objectg),scope=ldb.SCOPE_BASE)
        return search_result
    def get_object_by_objectguid(self,objectg):
        # Dado el dn de un objeto, buscar todas sus propiedades.
        # La gracia es no listar todas las propiedades sino listarlas por reflection.
        search_result=self.__search_entry_private(objectg)
        objeto=User()
        for resultado in search_result:
            objeto.dn=resultado.get("dn",idx=0)
            objeto.samaccountname=resultado.get("samaccountname",idx=0)
            objeto.enabled=True
            # Groups have no userAccountControl.
            userAccountFlags=int(resultado.get("userAccountControl",idx=0) or 0)
            print("Las accountflags de esta cuenta son: %d" % userAccountFlags)
            print("Valores de los Account Flags:")
            print("UF_SCRIPT: %d" % samba.dsdb.UF_SCRIPT)
            print("UF_ACCOUNTDISABLE: %d" % samba.dsdb.UF_ACCOUNTDISABLE)
            print("UF_HOMEDIR_REQUIRED: %d" % samba.dsdb.UF_HOMEDIR_REQUIRED)
            print("UF_LOCKOUT: %d" % samba.dsdb.UF_LOCKOUT)
            print("UF_PASSWD_NOTREQD: %d" % samba.dsdb.UF_PASSWD_NOTREQD)
            print("UF_PASSWD_CANT_CHANGE: %d" % samba.dsdb.UF_PASSWD_CANT_CHANGE)
            print("UF_ENCRYPTED_TEXT_PASSWORD_ALLOWED: %d" % samba.dsdb.UF_ENCRYPTED_TEXT_PASSWORD_ALLOWED)
            print("UF_TEMP_DUPLICATE_ACCOUNT: %d" % samba.dsdb.UF_TEMP_DUPLICATE_ACCOUNT)
            print("UF_NORMAL_ACCOUNT: %d" % samba.dsdb.UF_NORMAL_ACCOUNT)
            print("UF_INTERDOMAIN_TRUST_ACCOUNT: %d" % samba.dsdb.UF_INTERDOMAIN_TRUST_ACCOUNT)
            print("UF_WORKSTATION_TRUST_ACCOUNT: %d" % samba.dsdb.UF_WORKSTATION_TRUST_ACCOUNT)
            print("UF_SERVER_TRUST_ACCOUNT: %d" % samba.dsdb.UF_SERVER_TRUST_ACCOUNT)
            print("UF_DONT_EXPIRE_PASSWD: %d" % samba.dsdb.UF_DONT_EXPIRE_PASSWD)
            print("UF_MNS_LOGON_ACCOUNT: %d" % samba.dsdb.UF_MNS_LOGON_ACCOUNT)
            print("UF_SMARTCARD_REQUIRED: %d" % samba.dsdb.UF_SMARTCARD_REQUIRED)
            print("UF_TRUSTED_FOR_DELEGATION: %d" % samba.dsdb.UF_TRUSTED_FOR_DELEGATION)
            print("UF_NOT_DELEGATED: %d" % samba.dsdb.UF_NOT_DELEGATED)
            print("UF_USE_DES_KEY_ONLY: %d" % samba.dsdb.UF_USE_DES_KEY_ONLY)
            print("UF_DONT_REQUIRE_PREAUTH: %d" % samba.dsdb.UF_DONT_REQUIRE_PREAUTH)
            print("UF_PASSWORD_EXPIRED: %d" % samba.dsdb.UF_PASSWORD_EXPIRED)
            print("UF_TRUSTED_TO_AUTHENTICATE_FOR_DELEGATION: %d" % samba.dsdb.UF_TRUSTED_TO_AUTHENTICATE_FOR_DELEGATION)
            print("UF_NO_AUTH_DATA_REQUIRED: %d" % samba.dsdb.UF_NO_AUTH_DATA_REQUIRED)
            print("UF_PARTIAL_SECRETS_ACCOUNT: %d" % samba.dsdb.UF_PARTIAL_SECRETS_ACCOUNT)
            print("UF_USE_AES_KEYS: %d" % samba.dsdb.UF_USE_AES_KEYS)
            if( ( userAccountFlags & samba.dsdb.UF_ACCOUNTDISABLE)==samba.dsdb.UF_ACCOUNTDISABLE ):
                objeto.enabled=False
            if( (userAccountFlags & samba.dsdb.UF_NORMAL_ACCOUNT)==samba.dsdb.UF_NORMAL_ACCOUNT):
                objeto.account_type="normal_account"
            if( (userAccountFlags & samba.dsdb.UF_WORKSTATION_TRUST_ACCOUNT)==samba.dsdb.UF_WORKSTATION_TRUST_ACCOUNT):
                objeto.account_type="trust_account"
            if( (userAccountFlags & samba.dsdb.UF_SERVER_TRUST_ACCOUNT)==samba.dsdb.UF_SERVER_TRUST_ACCOUNT):
                objeto.account_type="server_account"
            print(objeto.enabled)
        return objeto
    def get_group_by_objectguid(self, objectg):
        """Return the group with that id as a Group, or None if there is no
        such object or it is not a group. Raises ValueError for invalid ids."""
        cx = self.conectar()
        result = cx.search(base=guid_base_dn(objectg), scope=ldb.SCOPE_BASE,
                           attrs=["objectClass", "sAMAccountName", "description",
                                  "groupType", "member"])
        if len(result) != 1:
            return None
        entry = result[0]
        if "group" not in [_text(c) for c in entry["objectClass"]]:
            return None
        group = Group(_text(entry.get("sAMAccountName", idx=0)), str(entry.dn))
        group.objectguid = objectg
        group.description = _text(entry.get("description", idx=0))
        group.scope, group.group_type = describe_group_type(int(entry.get("groupType", idx=0) or 0))
        if "member" in entry:
            group.members = sorted(entry["member"].text, key=str.lower)
        return group

    def update_group(self, objectg, description, add_member_names=(), remove_member_dns=()):
        """Change a group's description and members in a single LDAP modify,
        so either all the changes are applied or none.

        add_member_names are account names (sAMAccountName) of users, groups
        or computers; remove_member_dns are DNs of current members. Raises
        SambaError with a readable message if Samba refuses.
        """
        cx = self.conectar()
        result = cx.search(base=guid_base_dn(objectg), scope=ldb.SCOPE_BASE,
                           attrs=["description"])
        if len(result) != 1:
            raise SambaError("The group no longer exists.")
        message = ldb.Message()
        message.dn = result[0].dn
        if description != _text(result[0].get("description", idx=0)):
            # An empty list removes the description.
            message["description"] = ldb.MessageElement(
                [description] if description else [], ldb.FLAG_MOD_REPLACE, "description")
        add_dns = []
        for name in add_member_names:
            found = cx.search(self.get_domain(), scope=ldb.SCOPE_SUBTREE,
                              expression="(sAMAccountName=%s)" % ldb.binary_encode(name),
                              attrs=[])
            if len(found) != 1:
                raise SambaError('There is no user, group or computer named "%s".' % name)
            add_dns.append(str(found[0].dn))
        if add_dns:
            message["add_member"] = ldb.MessageElement(add_dns, ldb.FLAG_MOD_ADD, "member")
        if remove_member_dns:
            message["remove_member"] = ldb.MessageElement(
                list(remove_member_dns), ldb.FLAG_MOD_DELETE, "member")
        if len(message) == 0:
            return
        try:
            cx.modify(message)
        except ldb.LdbError as error:
            code = error.args[0]
            if code == ldb.ERR_ENTRY_ALREADY_EXISTS:
                raise SambaError("That account is already a member of the group.")
            if code == ldb.ERR_UNWILLING_TO_PERFORM and remove_member_dns:
                raise SambaError("One of the accounts to remove is no longer a member of the group.")
            if code == ldb.ERR_INSUFFICIENT_ACCESS_RIGHTS:
                raise SambaError("You do not have permission to change this group.")
            raise SambaError("Samba refused the change: %s" % error.args[-1])

    def buscar_cuentas(self, texto, limite=20):
        """Users, groups and computers whose account name, name or display name
        starts with texto (all of them if texto is empty), sorted by account
        name, at most limite. Each one is a dict with name (sAMAccountName),
        display (displayName, may be empty), type (user, group or computer)
        and dn."""
        cx = self.conectar()
        texto = texto.strip()
        if texto:
            patron = ldb.binary_encode(texto) + "*"
            nombre = "(|(sAMAccountName=%s)(cn=%s)(displayName=%s))" % (patron, patron, patron)
        else:
            nombre = "(sAMAccountName=*)"
        # Computers are also of objectClass user.
        result = cx.search(self.get_domain(), scope=ldb.SCOPE_SUBTREE,
                           expression="(&(|(objectClass=user)(objectClass=group))%s)" % nombre,
                           attrs=["sAMAccountName", "displayName", "objectClass"])
        cuentas = []
        for entry in result:
            clases = [_text(c) for c in entry["objectClass"]]
            if "computer" in clases:
                tipo = "computer"
            elif "group" in clases:
                tipo = "group"
            else:
                tipo = "user"
            cuentas.append({
                "name": _text(entry.get("sAMAccountName", idx=0)),
                "display": _text(entry.get("displayName", idx=0)),
                "type": tipo,
                "dn": str(entry.dn),
            })
        cuentas.sort(key=lambda cuenta: cuenta["name"].lower())
        return cuentas[:limite]

    def listar_contenedores(self):
        """DNs of the containers where accounts can be created: the default
        users container first, then every OU except Domain Controllers."""
        cx = self.conectar()
        dominio = cx.get_default_basedn()
        usuarios = str(cx.get_wellknown_dn(dominio, dsdb.DS_GUID_USERS_CONTAINER))
        ous = cx.search(dominio, scope=ldb.SCOPE_SUBTREE,
                        expression="(objectClass=organizationalUnit)", attrs=[])
        controladores = str(cx.get_wellknown_dn(dominio, dsdb.DS_GUID_DOMAIN_CONTROLLERS_CONTAINER)).lower()
        otros = sorted((str(ou.dn) for ou in ous if str(ou.dn).lower() != controladores), key=str.lower)
        return [usuarios] + otros

    def listar_ous(self):
        """Where an OU can be created: the domain itself and its OUs (except
        Domain Controllers and anything below it), as (dn, name, depth) in
        tree order, depth 0 being the domain."""
        cx = self.conectar()
        dominio = cx.get_default_basedn()
        controladores = cx.get_wellknown_dn(dominio, dsdb.DS_GUID_DOMAIN_CONTROLLERS_CONTAINER)
        ous = cx.search(dominio, scope=ldb.SCOPE_SUBTREE,
                        expression="(objectClass=organizationalUnit)", attrs=[])
        niveles_dominio = len(dominio)
        arbol = []
        for ou in ous:
            if ou.dn == controladores or ou.dn.is_child_of(controladores):
                continue
            profundidad = len(ou.dn) - niveles_dominio
            # Names from the top down, so that each OU sorts right after its parent.
            camino = [ou.dn.get_component_value(i).lower() for i in reversed(range(profundidad))]
            arbol.append((camino, str(ou.dn), ou.dn.get_component_value(0), profundidad))
        arbol.sort()
        return ([(str(dominio), str(dominio), 0)] +
                [(dn, nombre, profundidad) for camino, dn, nombre, profundidad in arbol])

    def crear_ou(self, name, parent, description=""):
        """Create an organizational unit called name inside parent (the domain
        or an OU) and return its DN. The name is escaped as needed, so it may
        contain commas and other special characters."""
        cx = self.conectar()
        rdn = ldb.Dn(cx, "OU=placeholder")
        rdn.set_component(0, "OU", name)
        dn = ldb.Dn(cx, parent)
        dn.add_child(rdn)
        try:
            cx.create_ou(str(dn), description=description or None)
        except ldb.LdbError as error:
            code = error.args[0]
            if code == ldb.ERR_ENTRY_ALREADY_EXISTS:
                raise SambaError('There is already an OU called "%s" there.' % name)
            if code == ldb.ERR_NAMING_VIOLATION:
                raise SambaError("An OU cannot be created there.")
            if code == ldb.ERR_INSUFFICIENT_ACCESS_RIGHTS:
                raise SambaError("You do not have permission to create an OU there.")
            raise SambaError("Samba refused to create the OU: %s" % error.args[-1])
        return str(dn)

    def _relativo_al_dominio(self, dn):
        """"OU=Sales,DC=example,DC=com" -> "OU=Sales", as newuser/newgroup expect."""
        sufijo = "," + self.get_domain()
        if not dn.lower().endswith(sufijo.lower()):
            raise SambaError("%s is not in this domain." % dn)
        return dn[:-len(sufijo)]

    def crear_usuario(self, username, password, container, given_name="", surname="",
                      description="", must_change_password=True, enabled=True):
        """Create a user account in the container (a DN from listar_contenedores).
        Raises SambaError with a readable message if Samba refuses."""
        cx = self.conectar()
        try:
            cx.newuser(username, password,
                       force_password_change_at_next_login_req=must_change_password,
                       userou=self._relativo_al_dominio(container),
                       givenname=given_name or None, surname=surname or None,
                       description=description or None)
            if not enabled:
                cx.disable_account("(sAMAccountName=%s)" % ldb.binary_encode(username))
        except ldb.LdbError as error:
            raise SambaError(_creation_error(error, username))

    def crear_grupo(self, name, container, scope="global", group_type="security", description=""):
        """Create a group in the container and return its id (as used in the
        group edit page). scope is global, domain_local or universal;
        group_type is security or distribution."""
        cx = self.conectar()
        try:
            cx.newgroup(name, groupou=self._relativo_al_dominio(container),
                        grouptype=GROUP_TYPES[(group_type, scope)],
                        description=description or None)
        except ldb.LdbError as error:
            raise SambaError(_creation_error(error, name))
        creado = cx.search(self.get_domain(), scope=ldb.SCOPE_SUBTREE,
                           expression="(sAMAccountName=%s)" % ldb.binary_encode(name),
                           attrs=["objectGUID"])
        return uuid.UUID(bytes=creado[0].get("objectGUID", idx=0)).hex

    def get_account_flags(self,objectg):
        # Dado el objectguid de un objeto, voy y busco sus UserAccountFlags,
        # que pueden ser Disabled, Force logon, machine trust account, etc, etc, etc.
        search_result=self.search_entry_by_objectguid(objectg)
        # Los flags vienen en el atributo userAccountControl.