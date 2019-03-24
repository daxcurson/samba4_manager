from reconfigure.configs import SambaConfig

class SambaConfigWriter(object):
    def __init__(self):
        self.config_file="/etc/samba/smb.conf"
        self.config=SambaConfig(path=self.config_file)
        self.config.load()
    def listar_shares(self):
        return self.config.tree.shares
    