from wtforms import Form, BooleanField, StringField, PasswordField, RadioField, SelectField, SelectMultipleField, validators, widgets

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
# Characters that AD does not allow in an account name (sAMAccountName).
ACCOUNT_NAME = validators.Regexp(r'^[^"/\\\[\]:;|=,+*?<>@]+$',
                                 message='It cannot contain any of these characters: " / \\ [ ] : ; | = , + * ? < > @')

class AddUserForm(Form):
    samaccountname = StringField('Account name', [validators.InputRequired(), validators.Length(max=20), ACCOUNT_NAME],
                                 description='Used to log in, e.g. jdoe. Up to 20 characters.')
    given_name = StringField('First name', [validators.Optional(), validators.Length(max=64)])
    surname = StringField('Last name', [validators.Optional(), validators.Length(max=64)])
    description = StringField('Description', [validators.Optional(), validators.Length(max=1024)])
    password = PasswordField('Password', [validators.InputRequired()])
    confirm_password = PasswordField('Confirm password', [validators.EqualTo('password', message='The passwords do not match.')])
    must_change_password = BooleanField('User must change password at next logon', default=True)
    enabled = BooleanField('Account enabled', default=True)
    # Choices are the containers where accounts can be created, set by the view.
    container = SelectField('Create in', choices=[])

class AddGroupForm(Form):
    samaccountname = StringField('Group name', [validators.InputRequired(), validators.Length(max=64), ACCOUNT_NAME])
    description = StringField('Description', [validators.Optional(), validators.Length(max=1024)])
    scope = RadioField('Scope', choices=[('global', 'Global'), ('domain_local', 'Domain local'), ('universal', 'Universal')],
                       default='global')
    group_type = RadioField('Type', choices=[('security', 'Security'), ('distribution', 'Distribution')],
                            default='security')
    container = SelectField('Create in', choices=[])

class AddOUForm(Form):
    name = StringField('Name', [validators.InputRequired(), validators.Length(max=64)])
    description = StringField('Description', [validators.Optional(), validators.Length(max=1024)])
    # Choices are the domain and its OUs, set by the view.
    parent = SelectField('Create in', choices=[])

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