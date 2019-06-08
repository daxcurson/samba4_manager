from reconfigure.configs import SambaConfig

class SambaConfigWriter(object):
    def __init__(self):
        self.config_file="/etc/samba/smb.conf"
        self.config=SambaConfig(path=self.config_file)
        self.config.load()
    def listar_shares(self):
        return self.config.tree.shares
    def obtener_share(self,nombre):
        # Recorramos la lista de shares y extraigamos aquella que nos sirve.
        share_encontrada=()
        encontrado=False
        cant_shares=len(self.config.tree.shares)
        share_actual=0
        while(share_actual<cant_shares and not encontrado):
            if(self.config.tree.shares[share_actual].name==nombre):
                encontrado=True
                share_encontrada=self.config.tree.shares[share_actual]
            share_actual=share_actual+1
        return share_encontrada