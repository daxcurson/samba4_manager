# Loading...
import ldb
import samba
from samba import param
from samba.samdb import SamDB
from samba.credentials import Credentials

class SambaServer(object):
#    def __init__(self):
    def conectar(self):
        lp=param.LoadParm()
        badge = Credentials()
        badge.guess(lp)
        badge.set_username('Administrator')
        badge.set_password('SuperSecret9898@')
        cx = SamDB(url='ldap://localhost',lp=lp,credentials=badge)
        return cx
    def listar_usuarios(self):
        # Aca se conectaria con el server en localhost y devolveria la lista de usuarios.
        # Search...
        cx=self.conectar()
        search_result = cx.search('DC=agusvillafane,DC=zapto,DC=org',scope=2,expression='(objectClass=user)',attrs=["samaccountname"])
        # Results...
        usuarios=[]
        for username in search_result:
            usuarios.append({'user':username.get("samaccountname",idx=0)})
        return usuarios
