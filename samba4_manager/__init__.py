from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_jinja2')
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view('static', 'samba4_manager:static')
    config.add_route('listar_usuarios', '/')
    config.add_route('listar_grupos','/grupos')
    config.add_route('agregar_usuario','/agregar_usuario')
    config.add_route('editar_usuario_mostrar_form','/editar_usuario/{objectguid}')
    config.add_route('editar_usuario_grabar_form','/editar_usuario_grabar')
    config.scan()
    return config.make_wsgi_app()
