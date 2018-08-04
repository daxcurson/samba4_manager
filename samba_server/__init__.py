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
        
    def conectar(self):
        lp=param.LoadParm()
        badge = Credentials()
        badge.guess(lp)
        
        badge.set_username(self.username)
        badge.set_password(self.password)
        cx = SamDB(url='ldap://localhost',lp=lp,credentials=badge)
        return cx
    def listar_usuarios(self):
        # Aca se conectaria con el server en localhost y devolveria la lista de usuarios.
        # Search...
        cx=self.conectar()
        search_result = cx.search(self.domain,scope=2,expression='(objectClass=user)',attrs=["samaccountname","description","dn","objectguid"])
        # Results...
        usuarios=[]
        for username in search_result:
            objectguid=username.get('objectguid',idx=0)
            guidhex=uuid.UUID(bytes=objectguid)
            assert guidhex.bytes==objectguid
            usuarios.append({'user':username.get("samaccountname",idx=0),'description':username.get("description",idx=0),'dn':username.get("dn",idx=0),'objectguid':username.get("objectguid",idx=0),'key':guidhex.hex})
        return usuarios
    def listar_grupos(self):
        cx=self.conectar()
        search_result=cx.search(self.domain,scope=2,expression="(objectClass=group)",attrs=["samaccountname","description","dn","objectguid"])
        # Obtengo los resultados
        grupos=[]
        for grupo in search_result:
            grupos.append({'group':grupo.get("samaccountname",idx=0),'description':grupo.get("description",idx=0),'dn':grupo.get("dn",idx=0),'objectguid':grupo.get("objectguid",idx=0)})
        return grupos
    def search_entry(self,objectg):
        cx=self.conectar()
        guidhex=uuid.UUID(hex=objectg)
        # Me gustaria tomarme el credito pero no puedo, esa busqueda
        # salio del codigo fuente mismo de Samba,
        # https://download.samba.org/pub/unpacked/samba_current/source4/dsdb/tests/python/deletetest.py
        search_result=cx.search(base="<GUID=%s>" % cx.schema_format_value("objectGUID",guidhex.bytes),scope=ldb.SCOPE_BASE)
        return search_result
    def get_object(self,objectg):
        # Dado el dn de un objeto, buscar todas sus propiedades.
        # La gracia es no listar todas las propiedades sino listarlas por reflection.
        search_result=self.search_entry(objectg)
        objeto=User()
        for resultado in search_result:
            objeto.dn=resultado.get("dn",idx=0)
            objeto.samaccountname=resultado.get("samaccountname",idx=0)
            objeto.enabled=True
            userAccountFlags=int(resultado.get("userAccountControl",idx=0))
            print(userAccountFlags)
            print(samba.dsdb.UF_ACCOUNTDISABLE)
            print(samba.dsdb.UF_NORMAL_ACCOUNT)
            if( ( userAccountFlags & samba.dsdb.UF_ACCOUNTDISABLE)==samba.dsdb.UF_ACCOUNTDISABLE ):
                objeto.enabled=False
            if( (userAccountFlags & samba.dsdb.UF_NORMAL_ACCOUNT)==samba.dsdb.UF_NORMAL_ACCOUNT):
                objeto.account_type="Normal"
            print(objeto.enabled)
        return objeto
    def get_account_flags(self,objectg):
        # Dado el objectguid de un objeto, voy y busco sus UserAccountFlags,
        # que pueden ser Disabled, Force logon, machine trust account, etc, etc, etc.
        search_result=self.search_entry(objectg)
        # Los flags vienen en el atributo userAccountControl.