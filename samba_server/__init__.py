# Loading...
import ldb
import samba
import uuid
import base64
from samba import param
from samba import dsdb, dsdb_dns
from samba.samdb import SamDB
from samba.credentials import Credentials
from samba4_manager.model import User
from secureconfig.secureconfigparser import SecureConfigParser
from secureconfig import SecureString

class SambaServer(object):
    def __init__(self):
        # Read the configuration file and store its values in memory.
        config=SecureConfigParser.from_file("/etc/httpd/conf.d/key.txt")
        config.read("/etc/httpd/conf.d/secret.txt")
        self.username=SecureString(config.get('credentials','username'))
        self.password=SecureString(config.get('credentials','password'))
        self.domain=config.get('credentials','domain')
    def get_domain(self):
        # Devuelve la string del dominio
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
        guidhex=uuid.UUID(hex=objectguid)
        search_result=cx.search(base="<GUID=%s>" % cx.schema_format_value("objectGUID",guidhex.bytes),scope=ldb.SCOPE_ONELEVEL)
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
        
        badge.set_username(self.username)
        badge.set_password(self.password)
        cx = SamDB(url='ldap://localhost',lp=lp,credentials=badge)
        return cx
    def autenticar(self,usuario,password):
        # Me conecto e intento autenticar a esta persona, estaria estableciendo
        # una conexion con los datos del usuario en lugar de como server.
        lp=param.LoadParm()
        badge=Credentials()
        badge.guess(lp)
        badge.set_username(usuario)
        badge.set_password(password)
        # Intento la conexion.
        cx=SamDB(url='ldap://localhost',lp=lp,credentials=badge)
        # Listo, la gracia es que si logre autenticarme con estos datos, y hay algun
        # resultado de mis acciones, voy a devolver algo. 
        return cx
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
    def pertenece_grupo(self,username,groupname):
        pertenece=False
        # Informa si el usuario pertenece al grupo que se pide
        cx=self.conectar()
        # El resultado de esta lista es un item, con el usuario, si este pertenece al grupo,
        # o un resultado vacio.
        search_result=cx.search(self.domain,scope=2,expression="(&(sAMAccountName=%s)(memberOf=%s))" % (username,groupname))
        # Resulta que la lista vacia tiene el valor implicito false. Haciendo not search_result,
        # me aseguro que la lista tenga contenido.
        if search_result is not None and not search_result:
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
        guidhex=uuid.UUID(hex=objectg)
        # Me gustaria tomarme el credito pero no puedo, esa busqueda
        # salio del codigo fuente mismo de Samba,
        # https://download.samba.org/pub/unpacked/samba_current/source4/dsdb/tests/python/deletetest.py
        search_result=cx.search(base="<GUID=%s>" % cx.schema_format_value("objectGUID",guidhex.bytes),scope=ldb.SCOPE_BASE)
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
            userAccountFlags=int(resultado.get("userAccountControl",idx=0))
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
    def get_account_flags(self,objectg):
        # Dado el objectguid de un objeto, voy y busco sus UserAccountFlags,
        # que pueden ser Disabled, Force logon, machine trust account, etc, etc, etc.
        search_result=self.search_entry_by_objectguid(objectg)
        # Los flags vienen en el atributo userAccountControl.