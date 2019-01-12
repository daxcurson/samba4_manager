from wtforms import Form, BooleanField, StringField, RadioField, validators

class UserForm(Form):
    samaccountname     = StringField('SamAccountName', [validators.Length(min=4, max=25)])
    dn= StringField('Distinguished Name', [validators.Length(min=6, max=500)])
    enabled= BooleanField('Enabled', validators=[validators.InputRequired()],default=True,false_values=('false',False,''))
    account_type=RadioField("Type",choices=[
        ("trust_account","Machine trust account"),
        ("server_account","Server Account"), 
        ("normal_account","Normal Account")
        ])

class ComputerForm(Form):
    samaccountname = StringField('SamAccountName', [validators.Length(min=4, max=25)])
    dn= StringField('Distinguished Name', [validators.Length(min=6, max=500)])
    enabled= BooleanField('Enabled', validators=[validators.InputRequired()],default=True,false_values=('false',False,''))
    account_type=RadioField("Type",choices=[
        ("trust_account","Machine trust account"),
        ("server_account","Server Account"), 
        ("normal_account","Normal Account")
        ])
class GroupForm(Form):
    samaccountname = StringField('SamAccountName', [validators.Length(min=4, max=25)])
    dn= StringField('Distinguished Name', [validators.Length(min=6, max=500)])
    enabled= BooleanField('Enabled', validators=[validators.InputRequired()],default=True,false_values=('false',False,''))
    account_type=RadioField("Type",choices=[
        ("trust_account","Machine trust account"),
        ("server_account","Server Account"), 
        ("normal_account","Normal Account")
        ])

class ADObject(object):
    def __init__(self,dist_name=""):
        self.dn=dist_name
class User(ADObject):
    def __init__(self,accountname="",dist_name=""):
        super(User,self).__init__(dist_name)
        self.samaccountname=accountname
        self.enabled=True
        self.account_type="normal_account"
        self.groups=[]

class Computer(ADObject):
    def __init(self,accountname="",dist_name=""):
        super(Computer,self).__init__(dist_name)
        self.samaccountname=accountname
        self.enabled=True
        self.account_type="trust_account"

class Group(ADObject):
    def __init(self,accountname="",dist_name=""):
        super(Group,self).__init__(dist_name)
        self.samaccountname=accountname
        self.enabled=True
        self.account_type="normal_account"