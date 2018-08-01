from wtforms import Form, BooleanField, StringField, validators

class UserForm(Form):
    samaccountname     = StringField('SamAccountName', [validators.Length(min=4, max=25)])
    dn= StringField('Distinguished Name', [validators.Length(min=6, max=500)])
    enabled= BooleanField('Enabled', [validators.InputRequired()])

class User(object):
    def __init__(self,accountname,dist_name):
        self.samaccountname=accountname
        self.dn=dist_name