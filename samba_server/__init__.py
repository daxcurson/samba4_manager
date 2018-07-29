# Loading...
import ldb
import samba
from samba import param
from samba.samdb import SamDB
from samba.credentials import Credentials
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
        search_result = cx.search(self.domain,scope=2,expression='(objectClass=user)',attrs=["samaccountname"])
        # Results...
        usuarios=[]
        for username in search_result:
            usuarios.append({'user':username.get("samaccountname",idx=0)})
        return usuarios
