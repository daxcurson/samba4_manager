import colander

class User(colander.MappingSchema):
    username=colander.SchemaNode(colander.String())
    password=colander.SchemaNode(colander.String())
    password_confirm=colander.SchemaNode(colander.String())
    description=colander.SchemaNode(colander.String())
    active=colander.SchemaNode(colander.Boolean())
    
class Group(colander.MappingSchema):
    groupname=colander.SchemaNode(colander.String())
    description=colander.SchemaNode(colander.String())