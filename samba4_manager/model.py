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

class User(object):
    def __init__(self,accountname="",dist_name=""):
        self.samaccountname=accountname
        self.dn=dist_name
        self.enabled=True
        self.account_type="Normal"