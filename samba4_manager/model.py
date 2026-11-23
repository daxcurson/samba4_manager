from wtforms import Form, BooleanField, StringField, RadioField, SelectMultipleField, validators, widgets

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
class MultiCheckboxField(SelectMultipleField):
    """A multiple choice rendered as a list of checkboxes."""
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class GroupForm(Form):
    """What can be changed in a group: its description and its members.

    The name, scope and type are shown but not edited here: in AD, renaming
    a group or changing its scope or type has its own rules.
    """
    description = StringField('Description', [validators.Optional(), validators.Length(max=1024)])
    # Choices are the group's current members (their DNs), set by the view.
    remove_members = MultiCheckboxField('Remove', choices=[])
    add_member = StringField('Add member', [validators.Optional(), validators.Length(max=256)],
                             description='Account name (sAMAccountName) of a user, group or computer')
class ShareForm(Form):
    path=StringField('Path',[validators.InputRequired()])
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
    def __init__(self,accountname="",dist_name=""):
        super(Group,self).__init__(dist_name)
        self.samaccountname=accountname
        self.objectguid=""
        self.description=""
        self.scope=""
        self.group_type=""
        # DNs of the members listed in the group's "member" attribute.
        self.members=[]